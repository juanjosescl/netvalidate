"""Cisco validator implementation.

The collect() method is a stub by default — it returns mock data so the
service runs end-to-end without real devices. Replace with real Netmiko/
Paramiko logic when wiring against a lab.
"""
from typing import Any

from netvalidate.models.schemas import CheckResult
from netvalidate.vendors.base import BaseValidator


class CiscoValidator(BaseValidator):
    vendor = "cisco"

    async def collect(self, device_ip: str, pivot_host: str | None) -> dict[str, Any]:
        # TODO: replace with Netmiko SSH/telnet via pivot.
        return {
            "version": "Cisco IOS XE Software, Version 17.9.1",
            "ospf_neighbors": [
                {"neighbor_id": "10.0.0.2", "state": "FULL", "area": "0"},
                {"neighbor_id": "10.0.0.3", "state": "FULL", "area": "0"},
            ],
            "interfaces_up": 12,
            "ntp_synced": True,
        }

    def evaluate(self, raw: dict[str, Any], profile: dict[str, Any]) -> list[CheckResult]:
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
        return results
