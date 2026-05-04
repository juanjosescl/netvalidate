"""Huawei validator stub. Replace collect() with real implementation."""
from typing import Any

from netvalidate.models.schemas import CheckResult
from netvalidate.vendors.base import BaseValidator


class HuaweiValidator(BaseValidator):
    vendor = "huawei"

    async def collect(self, device_ip: str, pivot_host: str | None) -> dict[str, Any]:
        return {
            "version": "VRP (R) software, Version 8.180",
            "eth_trunks": [{"name": "Eth-Trunk1", "members_up": 2, "members_total": 2}],
            "ospf_neighbors": [{"neighbor_id": "10.0.0.5", "state": "Full"}],
        }

    def evaluate(self, raw: dict[str, Any], profile: dict[str, Any]) -> list[CheckResult]:
        results: list[CheckResult] = []
        for check in profile.get("checks", []):
            name = check["name"]
            kind = check["kind"]
            severity = check.get("severity", "warning")

            if kind == "eth_trunks_healthy":
                bad = [t for t in raw["eth_trunks"] if t["members_up"] < t["members_total"]]
                passed = len(bad) == 0
                results.append(
                    CheckResult(
                        check_name=name,
                        passed=passed,
                        expected="all trunks fully up",
                        actual=f"{len(bad)} degraded",
                        severity=severity,
                        message="OK" if passed else f"Degraded trunks: {[t['name'] for t in bad]}",
                    )
                )
            elif kind == "ospf_neighbors_full":
                expected = check["expected_min"]
                full = sum(1 for n in raw["ospf_neighbors"] if n["state"] == "Full")
                passed = full >= expected
                results.append(
                    CheckResult(
                        check_name=name,
                        passed=passed,
                        expected=f">= {expected}",
                        actual=full,
                        severity=severity,
                        message="OK" if passed else "Insufficient OSPF Full adjacencies",
                    )
                )
        return results
