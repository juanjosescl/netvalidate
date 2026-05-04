"""Connection manager: direct SSH or SSH-pivot-then-telnet via Netmiko.

Supports two modes selected per request:

- "direct": Netmiko connects straight to the device (SSH or telnet).
- "pivot":  Netmiko SSHs into a pivot host (Linux), launches `telnet <ip>`
            from there, then redispatches the session to the vendor's
            device type. Useful when devices are reachable only from a
            management bastion.
"""
from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from typing import Any

try:
    from netmiko import ConnectHandler, redispatch
except ImportError:  # pragma: no cover - allow tests to monkeypatch
    ConnectHandler = None  # type: ignore[assignment]
    redispatch = None  # type: ignore[assignment]


# Netmiko device_type per vendor for telnet (used inside a pivot session).
VENDOR_DEVICE_TYPE_TELNET: dict[str, str] = {
    "cisco": "cisco_ios_telnet",
    "huawei": "huawei_telnet",
    "raisecom": "cisco_ios_telnet",
}

# Netmiko device_type per vendor for direct SSH.
VENDOR_DEVICE_TYPE_SSH: dict[str, str] = {
    "cisco": "cisco_ios",
    "huawei": "huawei",
    "raisecom": "cisco_ios",
}

# Vendors that require enable mode after login.
VENDORS_NEED_ENABLE: set[str] = {"cisco", "raisecom"}


@dataclass
class DeviceCredentials:
    """Credentials and parameters for connecting to a device.

    Passwords are passed in here, never stored in API payloads.
    Resolution from a `credentials_ref` happens out-of-band.
    """

    username: str
    password: str
    enable_password: str | None = None
    ssh_timeout: int = 30


@dataclass
class PivotConfig:
    """Configuration for a pivot/bastion host."""

    host: str
    port: int = 22
    username: str = ""
    password: str = ""


def _get_device_type(vendor: str, *, use_ssh: bool) -> str:
    registry = VENDOR_DEVICE_TYPE_SSH if use_ssh else VENDOR_DEVICE_TYPE_TELNET
    device_type = registry.get(vendor.lower().strip())
    if not device_type:
        raise ValueError(f"Unsupported vendor: {vendor}")
    return device_type


@contextmanager
def open_session(
    *,
    device_ip: str,
    vendor: str,
    credentials: DeviceCredentials,
    pivot: PivotConfig | None = None,
) -> Generator[Any, None, None]:
    """Open a Netmiko session to a device, optionally via a pivot.

    Yields a ready Netmiko connection object. Closes it on exit.

    Examples
    --------
    Direct SSH:
        with open_session(
            device_ip="192.0.2.10",
            vendor="cisco",
            credentials=creds,
        ) as conn:
            output = conn.send_command("show version")

    Via pivot:
        with open_session(
            device_ip="192.0.2.10",
            vendor="cisco",
            credentials=creds,
            pivot=pivot_cfg,
        ) as conn:
            output = conn.send_command("show version")
    """
    if ConnectHandler is None:  # pragma: no cover
        raise RuntimeError("Netmiko is not installed")

    conn = None
    try:
        if pivot is not None:
            conn = _connect_via_pivot(device_ip, vendor, credentials, pivot)
        else:
            conn = _connect_direct(device_ip, vendor, credentials)
        yield conn
    finally:
        if conn is not None:
            with suppress(Exception):
                conn.disconnect()


def _connect_direct(
    device_ip: str,
    vendor: str,
    credentials: DeviceCredentials,
) -> Any:
    """Direct SSH connection to the device."""
    device_type = _get_device_type(vendor, use_ssh=True)
    vendor_key = vendor.lower().strip()

    params: dict[str, Any] = {
        "device_type": device_type,
        "host": device_ip,
        "username": credentials.username,
        "password": credentials.password,
        "timeout": credentials.ssh_timeout,
        "global_delay_factor": 2,
    }
    if vendor_key in VENDORS_NEED_ENABLE and credentials.enable_password:
        params["secret"] = credentials.enable_password

    conn = ConnectHandler(**params)

    if vendor_key in VENDORS_NEED_ENABLE and credentials.enable_password:
        conn.enable()

    return conn


def _connect_via_pivot(
    device_ip: str,
    vendor: str,
    credentials: DeviceCredentials,
    pivot: PivotConfig,
) -> Any:
    """SSH to a pivot host, then telnet to the target device, then redispatch."""
    device_type_telnet = _get_device_type(vendor, use_ssh=False)
    vendor_key = vendor.lower().strip()

    # Step 1: SSH to the pivot as a Linux host.
    pivot_conn = ConnectHandler(
        device_type="linux",
        host=pivot.host,
        port=pivot.port,
        username=pivot.username,
        password=pivot.password,
        timeout=credentials.ssh_timeout,
    )

    # Step 2: launch telnet from the pivot to the device.
    pivot_conn.write_channel(f"telnet {device_ip}\n")

    # Step 3: handle login prompts with polling.
    output = ""
    login_sent = False
    password_sent = False
    max_wait = 15
    elapsed = 0

    while elapsed < max_wait:
        time.sleep(1)
        elapsed += 1
        output += pivot_conn.read_channel()

        if "Connection refused" in output or "Connection timed out" in output:
            raise ConnectionError(f"Telnet refused/timeout to {device_ip}")

        login_prompts = ("Username:", "Login:", "login:", "User name:")
        if not login_sent and any(p in output for p in login_prompts):
            pivot_conn.write_channel(f"{credentials.username}\n")
            login_sent = True
            output = ""
            continue

        if not password_sent and ("Password:" in output or "password:" in output):
            pivot_conn.write_channel(f"{credentials.password}\n")
            password_sent = True
            output = ""
            continue

        if password_sent and (">" in output or "#" in output):
            break

    # Step 4: redispatch the session to the vendor's telnet type.
    redispatch(pivot_conn, device_type=device_type_telnet)

    # Step 5: enable mode if needed.
    if vendor_key in VENDORS_NEED_ENABLE and credentials.enable_password:
        pivot_conn.secret = credentials.enable_password
        pivot_conn.enable()

    return pivot_conn
