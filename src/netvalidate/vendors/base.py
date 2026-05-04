"""Base protocol for vendor-specific validators."""
from abc import ABC, abstractmethod
from typing import Any

from netvalidate.models.schemas import CheckResult


class BaseValidator(ABC):
    """Abstract base for vendor validators (Strategy pattern)."""

    vendor: str = "base"

    @abstractmethod
    async def collect(self, device_ip: str, pivot_host: str | None) -> dict[str, Any]:
        """Connect to the device and collect raw command outputs."""
        ...

    @abstractmethod
    def evaluate(self, raw_output: dict[str, Any], profile: dict[str, Any]) -> list[CheckResult]:
        """Evaluate collected output against the profile rules."""
        ...

    async def run(
        self,
        device_ip: str,
        pivot_host: str | None,
        profile: dict[str, Any],
    ) -> list[CheckResult]:
        raw = await self.collect(device_ip, pivot_host)
        return self.evaluate(raw, profile)
