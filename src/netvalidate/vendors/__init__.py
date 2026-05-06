"""Vendor validators and factory."""
from netvalidate.vendors.base import BaseValidator
from netvalidate.vendors.cisco import CiscoValidator
from netvalidate.vendors.huawei import HuaweiValidator
from netvalidate.vendors.raisecom import RaisecomValidator

_VALIDATORS: dict[str, type[BaseValidator]] = {
    "cisco": CiscoValidator,
    "huawei": HuaweiValidator,
    "raisecom": RaisecomValidator,
}


def get_validator(vendor: str) -> BaseValidator:
    """Return the validator instance for a given vendor."""
    cls = _VALIDATORS.get(vendor)
    if cls is None:
        raise ValueError(f"Unsupported vendor: {vendor}")
    return cls()


__all__ = ["BaseValidator", "get_validator"]
