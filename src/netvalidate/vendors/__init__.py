"""Vendor-specific validators."""
from netvalidate.vendors.base import BaseValidator
from netvalidate.vendors.cisco import CiscoValidator
from netvalidate.vendors.huawei import HuaweiValidator
from netvalidate.vendors.raisecom import RaisecomValidator


def get_validator(vendor: str) -> BaseValidator:
    """Return the validator instance for a given vendor.

    Raises ValueError if the vendor is not supported.
    """
    mapping: dict[str, BaseValidator] = {
        "cisco": CiscoValidator(),
        "huawei": HuaweiValidator(),
        "raisecom": RaisecomValidator(),
    }
    if vendor not in mapping:
        raise ValueError(f"Unsupported vendor: {vendor}")
    return mapping[vendor]


__all__ = ["BaseValidator", "CiscoValidator", "HuaweiValidator", "RaisecomValidator", "get_validator"]