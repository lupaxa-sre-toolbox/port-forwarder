"""Mapping and allowlist parsing."""

from __future__ import annotations

import ipaddress

import pytest

from lupaxa.port_forwarder import (
    Mapping,
    address_allowed,
    parse_allow,
    parse_mapping,
    parse_targets,
)


def test_parse_mapping_host() -> None:
    assert parse_mapping("8080:db.internal:5432") == Mapping(8080, "db.internal", 5432)


def test_parse_mapping_ipv6() -> None:
    assert parse_mapping("8080:[::1]:80") == Mapping(8080, "::1", 80)


def test_parse_targets_legacy_three_args() -> None:
    assert parse_targets(["8080", "db.internal", "5432"]) == [
        Mapping(8080, "db.internal", 5432),
    ]


def test_parse_targets_two_mappings() -> None:
    assert parse_targets(["8080:host:80", "5432:db:5432"]) == [
        Mapping(8080, "host", 80),
        Mapping(5432, "db", 5432),
    ]


def test_parse_mapping_rejects_bad_shape() -> None:
    with pytest.raises(ValueError, match="LOCAL:HOST:REMOTE"):
        parse_mapping("8080:80")


def test_parse_targets_rejects_mixed_forms() -> None:
    with pytest.raises(ValueError, match="mapping"):
        parse_targets(["8080:host:80", "5432"])


def test_parse_targets_rejects_empty() -> None:
    with pytest.raises(ValueError, match="at least one"):
        parse_targets([])


def test_parse_allow_host_and_cidr() -> None:
    networks = parse_allow(["127.0.0.1", "10.0.0.0/8"])
    assert ipaddress.ip_address("127.0.0.1") in networks[0]
    assert ipaddress.ip_address("10.1.2.3") in networks[1]
    assert ipaddress.ip_address("11.0.0.1") not in networks[1]


def test_parse_allow_rejects_junk() -> None:
    with pytest.raises(ValueError, match="allow"):
        parse_allow(["not-an-ip"])


def test_address_allowed_normalizes_ipv4_mapped() -> None:
    networks = parse_allow(["127.0.0.1"])
    assert address_allowed("::ffff:127.0.0.1", networks)
    assert not address_allowed("::ffff:10.0.0.1", networks)
    assert address_allowed("8.8.8.8", [])
    assert not address_allowed("not-an-ip", networks)
    assert not address_allowed("::1", networks)
