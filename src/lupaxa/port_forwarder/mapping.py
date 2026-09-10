"""Parse forward mappings and source allowlists."""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Sequence
from dataclasses import dataclass

_MIN_PORT = 1
_MAX_PORT = 65535
_BRACKETED = re.compile(r"^(\d+):\[([^\]]+)\]:(\d+)$")


@dataclass(frozen=True)
class Mapping:
    """One local listen port forwarded to a remote host and port."""

    local_port: int
    remote_host: str
    remote_port: int


def _tcp_port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise ValueError(f"port must be an integer, got {value!r}") from exc
    if port < _MIN_PORT or port > _MAX_PORT:
        raise ValueError(f"port must be between {_MIN_PORT} and {_MAX_PORT}")
    return port


def parse_mapping(value: str) -> Mapping:
    """Parse ``LOCAL:HOST:REMOTE`` or ``LOCAL:[IPv6]:REMOTE``."""
    match = _BRACKETED.fullmatch(value)
    if match is not None:
        return Mapping(
            _tcp_port(match.group(1)),
            match.group(2),
            _tcp_port(match.group(3)),
        )
    parts = value.rsplit(":", 2)
    if len(parts) != 3 or not parts[1]:
        raise ValueError("mapping must be LOCAL:HOST:REMOTE or LOCAL:[IPv6]:REMOTE")
    return Mapping(_tcp_port(parts[0]), parts[1], _tcp_port(parts[2]))


def parse_targets(targets: list[str]) -> list[Mapping]:
    """Parse legacy ``LOCAL HOST REMOTE`` or one or more ``LOCAL:HOST:REMOTE`` mappings."""
    if len(targets) == 3 and ":" not in targets[0]:
        return [Mapping(_tcp_port(targets[0]), targets[1], _tcp_port(targets[2]))]
    mappings: list[Mapping] = []
    for item in targets:
        if ":" not in item:
            raise ValueError("each extra target must be a LOCAL:HOST:REMOTE mapping")
        mappings.append(parse_mapping(item))
    if not mappings:
        raise ValueError("at least one mapping is required")
    return mappings


def parse_allow(values: list[str]) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """Parse host addresses or CIDR networks for a source allowlist."""
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for value in values:
        try:
            networks.append(ipaddress.ip_network(value, strict=False))
        except ValueError as exc:
            raise ValueError(f"allow must be an IP address or CIDR: {value!r}") from exc
    return networks


def address_allowed(
    host: str,
    networks: Sequence[ipaddress.IPv4Network | ipaddress.IPv6Network],
) -> bool:
    """Return whether ``host`` is in any allowlist network.

    IPv4-mapped IPv6 addresses are compared as IPv4.
    An empty ``networks`` list allows every source.
    """
    if not networks:
        return True
    try:
        address: ipaddress.IPv4Address | ipaddress.IPv6Address = ipaddress.ip_address(host)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    for network in networks:
        try:
            if address in network:
                return True
        except TypeError:
            continue
    return False
