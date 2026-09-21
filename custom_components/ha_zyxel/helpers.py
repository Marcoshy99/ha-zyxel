"""Shared helpers for the Zyxel integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import format_mac


def lan_hosts(coordinator) -> dict[str, dict]:
    """Return {formatted_mac: host_record} from the coordinator's lanhosts data."""
    block = (coordinator.data or {}).get("lanhosts")
    hosts = block.get("lanhosts") if isinstance(block, dict) else None
    result: dict[str, dict] = {}
    if isinstance(hosts, list):
        for host in hosts:
            mac = host.get("PhysAddress")
            if mac:
                result[format_mac(mac)] = host
    return result


def lan_host_name(host: dict, mac: str) -> str:
    """Return a useful display name for a LAN host, falling back to its MAC."""
    for key in ("curHostName", "HostName", "DeviceName"):
        value = host.get(key)
        if isinstance(value, str) and value.strip() and value.strip().lower() != "unknown":
            return value.strip()
    return mac
