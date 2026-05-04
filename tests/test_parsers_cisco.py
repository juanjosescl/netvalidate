"""Tests for Cisco IOS output parsers."""
from netvalidate.vendors.parsers.cisco_parsers import (
    parse_cpu,
    parse_interface_description,
    parse_memory,
    parse_ntp_status,
    parse_ospf_neighbor,
    parse_version,
)

# -----------------------------------------------------------------------------
# parse_version
# -----------------------------------------------------------------------------

def test_parse_version_basic():
    output = """
    Cisco IOS Software, C3560 Software (C3560-IPSERVICESK9-M), Version 12.2(55)SE12, RELEASE SOFTWARE
    cisco WS-C3560-24PS (PowerPC405) processor (revision F0) with 122880K/8184K bytes of memory.
    Switch uptime is 2 years, 15 weeks, 3 days, 4 hours, 22 minutes
    System serial number          : FOC1234ABCD
    Model number                  : WS-C3560-24PS-S
    """
    result = parse_version(output)

    assert result["model"] == "WS-C3560-24PS-S"
    assert result["software_version"] == "12.2(55)SE12"
    assert result["serial_number"] == "FOC1234ABCD"
    assert result["uptime_days"] == 2 * 365 + 15 * 7 + 3
    assert "2y" in result["uptime"]


def test_parse_version_short_uptime():
    output = """
    cisco WS-C2960X (PowerPC) processor with 524288K bytes of memory.
    Switch uptime is 5 hours, 30 minutes
    """
    result = parse_version(output)
    assert result["uptime_days"] == 0
    assert "5h" in result["uptime"]


def test_parse_version_empty_returns_empty_dict():
    assert parse_version("") == {}


# -----------------------------------------------------------------------------
# parse_interface_description
# -----------------------------------------------------------------------------

def test_parse_interface_description_typical():
    output = """Interface                      Status         Protocol Description
Gi0/1                          up             up       UPLINK_TO_CORE
Gi0/2                          admin down     down
Gi0/3                          up             down     CUSTOMER_PORT
Gi0/4                          up             up
"""
    interfaces = parse_interface_description(output)

    assert len(interfaces) == 4
    assert interfaces[0]["name"] == "Gi0/1"
    assert interfaces[0]["oper_status"] == "UP"
    assert interfaces[0]["description"] == "UPLINK_TO_CORE"
    assert interfaces[1]["admin_status"] == "admin down"
    assert interfaces[2]["oper_status"] == "DOWN"


def test_parse_interface_description_empty():
    assert parse_interface_description("") == []


# -----------------------------------------------------------------------------
# parse_ospf_neighbor
# -----------------------------------------------------------------------------

def test_parse_ospf_neighbor_full_states():
    output = """Neighbor ID     Pri   State           Dead Time   Address         Interface
10.0.0.2          1   FULL/DR         00:00:39    10.1.1.2        GigabitEthernet0/1
10.0.0.3          1   FULL/BDR        00:00:38    10.1.1.3        GigabitEthernet0/2
"""
    neighbors = parse_ospf_neighbor(output)

    assert len(neighbors) == 2
    assert neighbors[0]["neighbor_id"] == "10.0.0.2"
    assert neighbors[0]["state"] == "FULL"
    assert neighbors[0]["state_raw"] == "FULL/DR"
    assert neighbors[0]["interface"] == "GigabitEthernet0/1"
    assert neighbors[1]["state"] == "FULL"


def test_parse_ospf_neighbor_mixed_states():
    output = """Neighbor ID     Pri   State           Dead Time   Address         Interface
10.0.0.2          1   FULL/DR         00:00:39    10.1.1.2        Gi0/1
10.0.0.4          1   2-WAY/DROTHER   00:00:35    10.1.1.4        Gi0/3
10.0.0.5          0   INIT/-          00:00:30    10.1.1.5        Gi0/4
"""
    neighbors = parse_ospf_neighbor(output)

    assert len(neighbors) == 3
    states = [n["state"] for n in neighbors]
    assert states == ["FULL", "2-WAY", "INIT"]


def test_parse_ospf_neighbor_empty():
    assert parse_ospf_neighbor("") == []


def test_parse_ospf_neighbor_only_header_returns_empty():
    output = "Neighbor ID     Pri   State           Dead Time   Address         Interface\n"
    assert parse_ospf_neighbor(output) == []


# -----------------------------------------------------------------------------
# parse_ntp_status
# -----------------------------------------------------------------------------

def test_parse_ntp_status_synced():
    output = """Clock is synchronized, stratum 3, reference is 10.0.0.1
nominal freq is 250.0000 Hz, actual freq is 249.9990 Hz, precision is 2**18
"""
    result = parse_ntp_status(output)
    assert result["synced"] is True
    assert result["stratum"] == 3
    assert result["reference"] == "10.0.0.1"


def test_parse_ntp_status_unsynced():
    output = """Clock is unsynchronized, stratum 16, no reference clock
nominal freq is 250.0000 Hz
"""
    result = parse_ntp_status(output)
    assert result["synced"] is False
    assert result["stratum"] == 16


def test_parse_ntp_status_empty():
    result = parse_ntp_status("")
    assert result["synced"] is False
    assert result["stratum"] is None
    assert result["reference"] is None


# -----------------------------------------------------------------------------
# parse_cpu
# -----------------------------------------------------------------------------

def test_parse_cpu_typical():
    output = "CPU utilization for five seconds: 12%/3%; one minute: 15%; five minutes: 10%\n"
    result = parse_cpu(output)
    assert result["5_seconds"] == 12
    assert result["1_minute"] == 15
    assert result["5_minutes"] == 10


def test_parse_cpu_empty():
    assert parse_cpu("") == {}


# -----------------------------------------------------------------------------
# parse_memory
# -----------------------------------------------------------------------------

def test_parse_memory_typical():
    output = """                Head    Total(b)     Used(b)     Free(b)   Lowest(b)  Largest(b)
Processor   12345678    524288000   314572800   209715200   180000000  150000000
      I/O   87654321     67108864    33554432    33554432    30000000   20000000
"""
    result = parse_memory(output)
    assert result["total_bytes"] == 524288000
    assert result["used_bytes"] == 314572800
    assert result["free_bytes"] == 209715200
    # 314572800 / 524288000 = 0.6 → 60.0%
    assert result["utilization_pct"] == 60.0


def test_parse_memory_empty():
    assert parse_memory("") == {}
