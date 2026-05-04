"""Unit tests for vendor validators - logic only, no network."""
import pytest

from netvalidate.vendors.cisco import CiscoValidator
from netvalidate.vendors.huawei import HuaweiValidator
from netvalidate.vendors.raisecom import RaisecomValidator


# -----------------------------------------------------------------------------
# Cisco
# -----------------------------------------------------------------------------

def test_cisco_evaluate_all_passing():
    """When raw output meets all profile rules, all checks pass."""
    validator = CiscoValidator()
    raw = {
        "version": "Cisco IOS XE 17.9.1",
        "ospf_neighbors": [
            {"neighbor_id": "10.0.0.2", "state": "FULL", "area": "0"},
            {"neighbor_id": "10.0.0.3", "state": "FULL", "area": "0"},
        ],
        "interfaces_up": 12,
        "ntp_synced": True,
    }
    profile = {
        "checks": [
            {"name": "ospf_check", "kind": "ospf_neighbors_full",
             "expected_min": 2, "severity": "critical"},
            {"name": "ntp_check", "kind": "ntp_synced", "severity": "warning"},
        ]
    }

    results = validator.evaluate(raw, profile)

    assert len(results) == 2
    assert all(r.passed for r in results)


def test_cisco_evaluate_ospf_insufficient():
    """When OSPF FULL count is below the threshold, the check fails."""
    validator = CiscoValidator()
    raw = {
        "ospf_neighbors": [
            {"neighbor_id": "10.0.0.2", "state": "FULL", "area": "0"},
            {"neighbor_id": "10.0.0.3", "state": "INIT", "area": "0"},
        ],
        "interfaces_up": 12,
        "ntp_synced": True,
    }
    profile = {
        "checks": [
            {"name": "ospf_check", "kind": "ospf_neighbors_full",
             "expected_min": 2, "severity": "critical"},
        ]
    }

    results = validator.evaluate(raw, profile)

    assert len(results) == 1
    assert results[0].passed is False
    assert results[0].severity == "critical"


def test_cisco_evaluate_ntp_not_synced():
    validator = CiscoValidator()
    raw = {"ospf_neighbors": [], "interfaces_up": 5, "ntp_synced": False}
    profile = {
        "checks": [
            {"name": "ntp", "kind": "ntp_synced", "severity": "warning"},
        ]
    }

    results = validator.evaluate(raw, profile)

    assert results[0].passed is False
    assert results[0].actual is False


def test_cisco_evaluate_min_interfaces():
    validator = CiscoValidator()
    raw = {"ospf_neighbors": [], "interfaces_up": 2, "ntp_synced": True}
    profile = {
        "checks": [
            {"name": "ifaces", "kind": "min_interfaces_up",
             "expected_min": 4, "severity": "warning"},
        ]
    }

    results = validator.evaluate(raw, profile)

    assert results[0].passed is False
    assert results[0].actual == 2


# -----------------------------------------------------------------------------
# Huawei
# -----------------------------------------------------------------------------

def test_huawei_eth_trunks_healthy():
    validator = HuaweiValidator()
    raw = {
        "eth_trunks": [
            {"name": "Eth-Trunk1", "members_up": 2, "members_total": 2},
            {"name": "Eth-Trunk2", "members_up": 4, "members_total": 4},
        ],
        "ospf_neighbors": [],
    }
    profile = {
        "checks": [
            {"name": "trunks", "kind": "eth_trunks_healthy", "severity": "critical"},
        ]
    }

    results = validator.evaluate(raw, profile)

    assert results[0].passed is True


def test_huawei_eth_trunks_degraded():
    validator = HuaweiValidator()
    raw = {
        "eth_trunks": [
            {"name": "Eth-Trunk1", "members_up": 1, "members_total": 2},
        ],
        "ospf_neighbors": [],
    }
    profile = {
        "checks": [
            {"name": "trunks", "kind": "eth_trunks_healthy", "severity": "critical"},
        ]
    }

    results = validator.evaluate(raw, profile)

    assert results[0].passed is False
    assert "Eth-Trunk1" in results[0].message


# -----------------------------------------------------------------------------
# Raisecom
# -----------------------------------------------------------------------------

def test_raisecom_uplink_up():
    validator = RaisecomValidator()
    raw = {"uplink_state": "up", "loop_detection": "enabled"}
    profile = {
        "checks": [
            {"name": "uplink", "kind": "uplink_up", "severity": "critical"},
        ]
    }

    results = validator.evaluate(raw, profile)

    assert results[0].passed is True


def test_raisecom_uplink_down():
    validator = RaisecomValidator()
    raw = {"uplink_state": "down", "loop_detection": "enabled"}
    profile = {
        "checks": [
            {"name": "uplink", "kind": "uplink_up", "severity": "critical"},
        ]
    }

    results = validator.evaluate(raw, profile)

    assert results[0].passed is False


def test_raisecom_loop_detection_disabled():
    validator = RaisecomValidator()
    raw = {"uplink_state": "up", "loop_detection": "disabled"}
    profile = {
        "checks": [
            {"name": "loop", "kind": "loop_detection_enabled", "severity": "warning"},
        ]
    }

    results = validator.evaluate(raw, profile)

    assert results[0].passed is False