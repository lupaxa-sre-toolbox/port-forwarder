"""Forwarder group stop behaviour."""

from __future__ import annotations

import socket
import threading
import time

import pytest

from lupaxa.port_forwarder import PortForwarder, PortForwarderGroup


def _closed_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _start_forwarder(forwarder: PortForwarder) -> threading.Thread:
    ready = threading.Event()
    worker = threading.Thread(
        target=forwarder.start,
        kwargs={"on_ready": ready.set},
        daemon=True,
    )
    worker.start()
    assert ready.wait(timeout=2)
    return worker


def test_group_stop_stops_all_listeners() -> None:
    first = PortForwarder(0, "127.0.0.1", _closed_port())
    second = PortForwarder(0, "127.0.0.1", _closed_port())
    worker_one = _start_forwarder(first)
    worker_two = _start_forwarder(second)
    port_one = first.bound_port
    port_two = second.bound_port

    PortForwarderGroup([first, second]).stop()
    worker_one.join(timeout=2)
    worker_two.join(timeout=2)

    with pytest.raises(ConnectionRefusedError):
        socket.create_connection(("127.0.0.1", port_one), timeout=0.5)
    with pytest.raises(ConnectionRefusedError):
        socket.create_connection(("127.0.0.1", port_two), timeout=0.5)


def test_group_requires_a_forwarder() -> None:
    with pytest.raises(ValueError, match="at least one"):
        PortForwarderGroup([])


def test_group_context_manager_stops() -> None:
    forwarder = PortForwarder(0, "127.0.0.1", _closed_port())
    worker = _start_forwarder(forwarder)
    port = forwarder.bound_port
    with PortForwarderGroup([forwarder]):
        pass
    worker.join(timeout=2)
    with pytest.raises(ConnectionRefusedError):
        socket.create_connection(("127.0.0.1", port), timeout=0.5)


def test_group_starts_two_listeners() -> None:
    first = PortForwarder(0, "127.0.0.1", _closed_port())
    second = PortForwarder(0, "127.0.0.1", _closed_port())
    group = PortForwarderGroup([first, second])
    worker = threading.Thread(target=group.start, daemon=True)
    worker.start()
    deadline = time.time() + 2
    port_one = 0
    port_two = 0
    while time.time() < deadline:
        try:
            port_one = first.bound_port
            port_two = second.bound_port
            break
        except RuntimeError:
            time.sleep(0.05)
    else:
        group.stop()
        pytest.fail("group did not bind both listeners")

    group.stop()
    worker.join(timeout=2)
    with pytest.raises(ConnectionRefusedError):
        socket.create_connection(("127.0.0.1", port_one), timeout=0.5)
    with pytest.raises(ConnectionRefusedError):
        socket.create_connection(("127.0.0.1", port_two), timeout=0.5)


def test_group_bind_failure_stops_the_rest() -> None:
    good = PortForwarder(0, "127.0.0.1", _closed_port())
    bad = PortForwarder(0, "127.0.0.1", _closed_port(), bind_host="256.256.256.256")
    group = PortForwarderGroup([good, bad])
    with pytest.raises(OSError, match="256"):
        group.start()
    try:
        port = good.bound_port
    except RuntimeError:
        return
    with pytest.raises(ConnectionRefusedError):
        socket.create_connection(("127.0.0.1", port), timeout=0.5)
