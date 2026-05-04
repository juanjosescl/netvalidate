"""Cisco IOS validator.

`collect()` connects to a device via Netmiko (direct SSH or via a pivot host),
runs a fixed set of `show` commands, and parses each into structured data.
The output dict is shaped to match what `evaluate()` expects from a profile.

If no credentials are provided, `collect()` falls back to a deterministic
mock so the service stays runnable end-to-end without real devices — useful
for demos, smoke tests, and CI.
"""
from __future__ import annotations

import asyncio
import os
from typing import Any

from netvalidate.connectivity.manager import (
    DeviceCredentials,
    PivotConfig,
    open_session,
)
from netvalidate.models.schemas import CheckResult
from netvalidate.vendors.base import BaseValidator
from netvalidate.vendors.parsers.cisco_parsers import (
    parse_interface_description,
    parse_ntp_status,
    parse_ospf_neighbor,
    parse_version,
)

# Commands executed during collect(). Keep the list short and focused —
# adding more commands means more time per device and more parsing surface.
CISCO_COMMANDS = (
    "show version",
    "show ip ospf neighbor",
    "show ntp status",
    "show interface description",
)


class CiscoValidator(BaseValidator):
    vendor = "cisco"

    async def collect(
        self,
        device_ip: str,
        pivot_host: str | None,
    ) -> dict[str, Any]:
        """Collect raw operational data from a Cisco IOS device.

        When `NETVALIDATE_CISCO_USERNAME` is not set, returns mock data so
        the pipeline runs without devices. In production deployments,
        credentials come from environment variables (or a future secrets
        backend referenced by `credentials_ref`).
        """
        username = os.getenv("NETVALIDATE_CISCO_USERNAME")
        if not username:
            return _mock_collect()

        password = os.getenv("NETVALIDATE_CISCO_PASSWORD", "")
        enable_password = os.getenv("NETVALIDATE_CISCO_ENABLE", "")
        creds = DeviceCredentials(
            username=username,
            password=password,
            enable_password=enable_password or None,
        )

        pivot = None
        if pivot_host:
            pivot = PivotConfig(
                host=pivot_host,
                port=int(os.getenv("NETVALIDATE_PIVOT_PORT", "22")),
                username=os.getenv("NETVALIDATE_PIVOT_USERNAME", username),
                password=os.getenv("NETVALIDATE_PIVOT_PASSWORD", password),
            )

        # Netmiko is sync; run it in a worker thread so we don't block the loop.
        return await asyncio.to_thread(
            _collect_sync,
            device_ip=device_ip,
            credentials=creds,
            pivot=pivot,
        )

    def evaluate(
        self,
        raw: dict[str, Any],
        profile: dict[str, Any],
    ) -> list[CheckResult]:
        results: list[CheckResult] = []
        for check in profile.get("checks", []):
            name = check["name"]
            kind = check["kind"]
            severity = check.get("severity", "warning")

            if kind == "ospf_neighbors_full":
                expected = check["expected_min"]
                full = sum(1 for n in raw["ospf_neighbors"] if n["state"] == "FULL")
                passed = full >= expected
                results.append(
                    CheckResult(
                        check_name=name,
                        passed=passed,
                        expected=f">= {expected} neighbors in FULL",
                        actual=f"{full} in FULL",
                        severity=severity,
                        message="OK" if passed else "Insufficient OSPF FULL adjacencies",
                    )
                )
            elif kind == "ntp_synced":
                passed = bool(raw.get("ntp_synced"))
                results.append(
                    CheckResult(
                        check_name=name,
                        passed=passed,
                        expected=True,
                        actual=raw.get("ntp_synced"),
                        severity=severity,
                        message="OK" if passed else "NTP not synchronized",
                    )
                )
            elif kind == "min_interfaces_up":
                expected = check["expected_min"]
                actual = raw.get("interfaces_up", 0)
                passed = actual >= expected
                results.append(
                    CheckResult(
                        check_name=name,
                        passed=passed,
                        expected=f">= {expected}",
                        actual=actual,
                        severity=severity,
                        message="OK" if passed else "Too few interfaces up",
                    )
                )
            elif kind == "min_uptime_days":
                expected = check["expected_min"]
                actual = raw.get("uptime_days", 0)
                passed = actual >= expected
                results.append(
                    CheckResult(
                        check_name=name,
                        passed=passed,
                        expected=f">= {expected} days",
                        actual=f"{actual} days",
                        severity=severity,
                        message="OK" if passed else "Recent reboot detected",
                    )
                )
        return results


def _collect_sync(
    *,
    device_ip: str,
    credentials: DeviceCredentials,
    pivot: PivotConfig | None,
) -> dict[str, Any]:
    """Synchronous collection: open a session, run commands, parse outputs."""
    outputs: dict[str, str] = {}
    with open_session(
        device_ip=device_ip,
        vendor="cisco",
        credentials=credentials,
        pivot=pivot,
    ) as conn:
        for cmd in CISCO_COMMANDS:
            outputs[cmd] = conn.send_command(cmd)

    return _shape_raw(outputs)


def _shape_raw(outputs: dict[str, str]) -> dict[str, Any]:
    """Transform raw command outputs into the shape evaluate() expects.

    Kept as a pure function so it can be unit tested with canned strings.
    """
    version = parse_version(outputs.get("show version", ""))
    ospf = parse_ospf_neighbor(outputs.get("show ip ospf neighbor", ""))
    ntp = parse_ntp_status(outputs.get("show ntp status", ""))
    ifaces = parse_interface_description(outputs.get("show interface description", ""))

    interfaces_up = sum(1 for i in ifaces if i["oper_status"] == "UP")

    return {
        "version": version.get("software_version"),
        "model": version.get("model"),
        "uptime_days": version.get("uptime_days", 0),
        "ospf_neighbors": [
            {
                "neighbor_id": n["neighbor_id"],
                "state": n["state"],
                "interface": n["interface"],
            }
            for n in ospf
        ],
        "interfaces_up": interfaces_up,
        "interfaces_total": len(ifaces),
        "ntp_synced": ntp["synced"],
        "ntp_stratum": ntp["stratum"],
    }


def _mock_collect() -> dict[str, Any]:
    """Deterministic mock data so the pipeline runs without real devices."""
    return {
        "version": "17.9.1",
        "model": "C9300-48P",
        "uptime_days": 120,
        "ospf_neighbors": [
            {"neighbor_id": "10.0.0.2", "state": "FULL", "interface": "Gi0/1"},
            {"neighbor_id": "10.0.0.3", "state": "FULL", "interface": "Gi0/2"},
        ],
        "interfaces_up": 12,
        "interfaces_total": 48,
        "ntp_synced": True,
        "ntp_stratum": 3,
    }
