"""Raisecom validator stub. Replace collect() with real implementation."""
from typing import Any

from netvalidate.models.schemas import CheckResult
from netvalidate.vendors.base import BaseValidator


class RaisecomValidator(BaseValidator):
    vendor = "raisecom"

    async def collect(self, device_ip: str, pivot_host: str | None) -> dict[str, Any]:
        return {
            "version": "ROS_5.4.x",
            "uplink_state": "up",
            "loop_detection": "enabled",
        }

    def evaluate(self, raw: dict[str, Any], profile: dict[str, Any]) -> list[CheckResult]:
        results: list[CheckResult] = []
        for check in profile.get("checks", []):
            name = check["name"]
            kind = check["kind"]
            severity = check.get("severity", "warning")

            if kind == "uplink_up":
                passed = raw.get("uplink_state") == "up"
                results.append(
                    CheckResult(
                        check_name=name,
                        passed=passed,
                        expected="up",
                        actual=raw.get("uplink_state"),
                        severity=severity,
                        message="OK" if passed else "Uplink is not up",
                    )
                )
            elif kind == "loop_detection_enabled":
                passed = raw.get("loop_detection") == "enabled"
                results.append(
                    CheckResult(
                        check_name=name,
                        passed=passed,
                        expected="enabled",
                        actual=raw.get("loop_detection"),
                        severity=severity,
                        message="OK" if passed else "Loop detection is disabled",
                    )
                )
        return results
