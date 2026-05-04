"""Tests for CiscoValidator.collect() and the raw shaping function.

The real Netmiko connection is mocked so these tests run without devices.
"""
import os
from unittest.mock import MagicMock, patch

import pytest

from netvalidate.vendors.cisco import (
    CISCO_COMMANDS,
    CiscoValidator,
    _mock_collect,
    _shape_raw,
)

# -----------------------------------------------------------------------------
# _shape_raw: integration of all parsers into the expected dict
# -----------------------------------------------------------------------------

def test_shape_raw_combines_all_parsers():
    outputs = {
        "show version": (
            "Cisco IOS Software, Version 15.2(4)E10, RELEASE\n"
            "cisco WS-C3560X (PowerPC) processor\n"
            "Switch uptime is 1 year, 2 weeks, 3 days\n"
            "Model number                  : WS-C3560X-48P-S\n"
        ),
        "show ip ospf neighbor": (
            "Neighbor ID     Pri   State           Dead Time   Address      Interface\n"
            "10.0.0.2          1   FULL/DR         00:00:39    10.1.1.2     Gi0/1\n"
            "10.0.0.3          1   FULL/BDR        00:00:38    10.1.1.3     Gi0/2\n"
        ),
        "show ntp status": (
            "Clock is synchronized, stratum 3, reference is 10.0.0.1\n"
        ),
        "show interface description": (
            "Interface                      Status         Protocol Description\n"
            "Gi0/1                          up             up       UPLINK\n"
            "Gi0/2                          up             up\n"
            "Gi0/3                          admin down     down\n"
        ),
    }

    result = _shape_raw(outputs)

    assert result["version"] == "15.2(4)E10"
    assert result["model"] == "WS-C3560X-48P-S"
    assert result["uptime_days"] == 365 + 14 + 3
    assert len(result["ospf_neighbors"]) == 2
    assert all(n["state"] == "FULL" for n in result["ospf_neighbors"])
    assert result["interfaces_up"] == 2
    assert result["interfaces_total"] == 3
    assert result["ntp_synced"] is True
    assert result["ntp_stratum"] == 3


def test_shape_raw_handles_empty_outputs():
    outputs = {cmd: "" for cmd in CISCO_COMMANDS}
    result = _shape_raw(outputs)

    assert result["ospf_neighbors"] == []
    assert result["interfaces_up"] == 0
    assert result["ntp_synced"] is False


# -----------------------------------------------------------------------------
# collect(): mock fallback when no credentials are set
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_collect_falls_back_to_mock_without_credentials(monkeypatch):
    monkeypatch.delenv("NETVALIDATE_CISCO_USERNAME", raising=False)
    validator = CiscoValidator()

    result = await validator.collect("192.0.2.10", None)

    assert result["ntp_synced"] is True
    assert len(result["ospf_neighbors"]) == 2
    assert result == _mock_collect()


# -----------------------------------------------------------------------------
# collect(): real path with Netmiko mocked
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_collect_uses_netmiko_when_credentials_present(monkeypatch):
    monkeypatch.setenv("NETVALIDATE_CISCO_USERNAME", "testuser")
    monkeypatch.setenv("NETVALIDATE_CISCO_PASSWORD", "testpass")

    fake_outputs = {
        "show version": "Cisco IOS Version 15.2(4)E10,\nSwitch uptime is 5 days\n",
        "show ip ospf neighbor": (
            "Neighbor ID     Pri   State           Dead Time   Address      Interface\n"
            "10.0.0.2          1   FULL/DR         00:00:39    10.1.1.2     Gi0/1\n"
        ),
        "show ntp status": "Clock is synchronized, stratum 4, reference is 10.0.0.5\n",
        "show interface description": (
            "Interface                      Status         Protocol Description\n"
            "Gi0/1                          up             up       UP1\n"
        ),
    }

    fake_conn = MagicMock()
    fake_conn.send_command.side_effect = lambda cmd: fake_outputs.get(cmd, "")

    fake_session_cm = MagicMock()
    fake_session_cm.__enter__ = MagicMock(return_value=fake_conn)
    fake_session_cm.__exit__ = MagicMock(return_value=False)

    with patch(
        "netvalidate.vendors.cisco.open_session",
        return_value=fake_session_cm,
    ) as mock_open:
        validator = CiscoValidator()
        result = await validator.collect("192.0.2.10", None)

    assert mock_open.called
    assert result["version"] == "15.2(4)E10"
    assert result["uptime_days"] == 5
    assert len(result["ospf_neighbors"]) == 1
    assert result["ospf_neighbors"][0]["state"] == "FULL"
    assert result["ntp_synced"] is True
    assert result["ntp_stratum"] == 4
    assert result["interfaces_up"] == 1


@pytest.mark.asyncio
async def test_collect_with_pivot_passes_pivot_config(monkeypatch):
    monkeypatch.setenv("NETVALIDATE_CISCO_USERNAME", "testuser")
    monkeypatch.setenv("NETVALIDATE_CISCO_PASSWORD", "testpass")
    monkeypatch.setenv("NETVALIDATE_PIVOT_USERNAME", "pivotuser")
    monkeypatch.setenv("NETVALIDATE_PIVOT_PASSWORD", "pivotpass")

    fake_conn = MagicMock()
    fake_conn.send_command.return_value = ""

    fake_cm = MagicMock()
    fake_cm.__enter__ = MagicMock(return_value=fake_conn)
    fake_cm.__exit__ = MagicMock(return_value=False)

    with patch(
        "netvalidate.vendors.cisco.open_session",
        return_value=fake_cm,
    ) as mock_open:
        validator = CiscoValidator()
        await validator.collect("192.0.2.10", "192.0.2.1")

    call_kwargs = mock_open.call_args.kwargs
    assert call_kwargs["device_ip"] == "192.0.2.10"
    assert call_kwargs["pivot"] is not None
    assert call_kwargs["pivot"].host == "192.0.2.1"
    assert call_kwargs["pivot"].username == "pivotuser"


# -----------------------------------------------------------------------------
# Cleanup: ensure env vars don't leak between tests
# -----------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_env():
    keys = [
        "NETVALIDATE_CISCO_USERNAME",
        "NETVALIDATE_CISCO_PASSWORD",
        "NETVALIDATE_CISCO_ENABLE",
        "NETVALIDATE_PIVOT_USERNAME",
        "NETVALIDATE_PIVOT_PASSWORD",
        "NETVALIDATE_PIVOT_PORT",
    ]
    saved = {k: os.environ.get(k) for k in keys}
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
