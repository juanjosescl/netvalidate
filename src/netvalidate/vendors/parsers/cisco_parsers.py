"""Parsers for Cisco IOS command outputs.

Pure functions: take a raw string, return a structured dict/list. No I/O,
no network. Easy to test against canned fixtures.
"""
from __future__ import annotations

import re


def parse_version(output: str) -> dict:
    """Parse `show version` output.

    Returns a dict with keys: model, software_version, serial_number,
    uptime (human string), uptime_days (int).
    """
    data: dict = {}

    model_match = re.search(r"Model number\s*:\s*(\S+)", output)
    if model_match:
        data["model"] = model_match.group(1).strip()
    else:
        cisco_match = re.search(r"cisco\s+(\S+)\s+\(", output)
        if cisco_match:
            data["model"] = cisco_match.group(1).strip()

    sw_match = re.search(r"Version\s+([\S]+),", output)
    if sw_match:
        data["software_version"] = sw_match.group(1).strip()

    serial_match = re.search(r"System serial number\s*:\s*(\S+)", output)
    if not serial_match:
        serial_match = re.search(r"Processor board ID\s+(\S+)", output)
    if serial_match:
        data["serial_number"] = serial_match.group(1).strip()

    uptime_match = re.search(r"uptime is\s+(.+)", output)
    if uptime_match:
        uptime_str = uptime_match.group(1).strip()
        total_days = 0
        years = re.search(r"(\d+)\s+years?", uptime_str)
        weeks = re.search(r"(\d+)\s+weeks?", uptime_str)
        days = re.search(r"(\d+)\s+days?", uptime_str)
        hours = re.search(r"(\d+)\s+hours?", uptime_str)
        minutes = re.search(r"(\d+)\s+minutes?", uptime_str)

        if years:
            total_days += int(years.group(1)) * 365
        if weeks:
            total_days += int(weeks.group(1)) * 7
        if days:
            total_days += int(days.group(1))

        data["uptime_days"] = total_days

        parts = []
        if years:
            parts.append(f"{years.group(1)}y")
        if weeks:
            parts.append(f"{weeks.group(1)}w")
        if days:
            parts.append(f"{days.group(1)}d")
        if hours:
            parts.append(f"{hours.group(1)}h")
        if minutes:
            parts.append(f"{minutes.group(1)}m")
        data["uptime"] = " ".join(parts) if parts else uptime_str

    return data


def parse_interface_description(output: str) -> list[dict]:
    """Parse `show interface description` output.

    Returns a list of dicts: name, admin_status, oper_status, description.
    """
    interfaces = []
    for line in output.strip().split("\n"):
        if not line.strip() or line.startswith("Interface"):
            continue
        match = re.match(
            r"(\S+)\s+(admin down|up|down)\s+(up|down)\s*(.*)",
            line,
            re.IGNORECASE,
        )
        if match:
            name = match.group(1)
            admin_status = match.group(2).lower()
            protocol = match.group(3).lower()
            description = match.group(4).strip()
            oper_status = "UP" if protocol == "up" else "DOWN"
            interfaces.append(
                {
                    "name": name,
                    "admin_status": admin_status,
                    "oper_status": oper_status,
                    "description": description,
                }
            )
    return interfaces


def parse_ospf_neighbor(output: str) -> list[dict]:
    """Parse `show ip ospf neighbor` output.

    Standard Cisco IOS format:

        Neighbor ID     Pri   State           Dead Time   Address         Interface
        10.0.0.2          1   FULL/DR         00:00:39    10.1.1.2        GigabitEthernet0/1
        10.0.0.3          1   FULL/BDR        00:00:38    10.1.1.3        GigabitEthernet0/2
        10.0.0.4          1   2-WAY/DROTHER   00:00:35    10.1.1.4        GigabitEthernet0/3

    The state column may include a role suffix after a slash (FULL/DR,
    FULL/BDR, FULL/-). We normalize the state to the part before the slash.

    Returns a list of dicts: neighbor_id, priority, state, dead_time,
    address, interface.
    """
    neighbors: list[dict] = []
    for line in output.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("Neighbor"):
            continue
        # Match: id  pri  state  deadtime  address  interface
        match = re.match(
            r"(\S+)\s+(\d+)\s+([A-Z0-9-]+(?:/[A-Z-]+)?)\s+(\S+)\s+(\S+)\s+(\S+)",
            line,
        )
        if not match:
            continue
        full_state = match.group(3)
        normalized = full_state.split("/")[0]  # FULL/DR -> FULL
        neighbors.append(
            {
                "neighbor_id": match.group(1),
                "priority": int(match.group(2)),
                "state": normalized,
                "state_raw": full_state,
                "dead_time": match.group(4),
                "address": match.group(5),
                "interface": match.group(6),
            }
        )
    return neighbors


def parse_ntp_status(output: str) -> dict:
    """Parse `show ntp status` output.

    Standard Cisco IOS first line:

        Clock is synchronized, stratum 3, reference is 10.0.0.1
        Clock is unsynchronized, stratum 16, no reference clock

    Returns a dict with: synced (bool), stratum (int|None),
    reference (str|None).
    """
    data: dict = {"synced": False, "stratum": None, "reference": None}

    if re.search(r"Clock is synchronized", output, re.IGNORECASE):
        data["synced"] = True
    elif re.search(r"Clock is unsynchronized", output, re.IGNORECASE):
        data["synced"] = False

    stratum_match = re.search(r"stratum\s+(\d+)", output, re.IGNORECASE)
    if stratum_match:
        data["stratum"] = int(stratum_match.group(1))

    ref_match = re.search(r"reference is\s+(\S+)", output, re.IGNORECASE)
    if ref_match:
        data["reference"] = ref_match.group(1).rstrip(",")

    return data


def parse_cpu(output: str) -> dict:
    """Parse `show processes cpu` first line.

    Returns dict with keys: 5_seconds, 1_minute, 5_minutes (all int %).
    """
    data: dict = {}
    match = re.search(
        r"five seconds:\s+(\d+)%/\d+%;\s+one minute:\s+(\d+)%;\s+five minutes:\s+(\d+)%",
        output,
    )
    if match:
        data["5_seconds"] = int(match.group(1))
        data["1_minute"] = int(match.group(2))
        data["5_minutes"] = int(match.group(3))
    return data


def parse_memory(output: str) -> dict:
    """Parse `show memory statistics` Processor row.

    Returns dict with: total_bytes, used_bytes, free_bytes, utilization_pct.
    """
    data: dict = {}
    match = re.search(r"Processor\s+\S+\s+(\d+)\s+(\d+)\s+(\d+)", output)
    if match:
        total = int(match.group(1))
        used = int(match.group(2))
        free = int(match.group(3))
        data["total_bytes"] = total
        data["used_bytes"] = used
        data["free_bytes"] = free
        if total > 0:
            data["utilization_pct"] = round(used / total * 100, 2)
    return data
