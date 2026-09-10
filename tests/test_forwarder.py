"""Local TCP forwarding behaviour."""

from __future__ import annotations

import socket
import threading
import time

import pytest

from lupaxa.port_forwarder import PortForwarder


def _closed_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _serve_once(host: str, port: int, payload: bytes, started: threading.Event) -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(1)
    started.set()
    conn, _addr = server.accept()
    with conn:
        data = conn.recv(4096)
        conn.sendall(payload + data)
    server.close()


def _serve_until_eof_then_reply(
    host: str,
    port: int,
    payload: bytes,
    started: threading.Event,
) -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(1)
    started.set()
    conn, _addr = server.accept()
    with conn:
        data = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
        conn.sendall(payload + data)
    server.close()


def _recv_until_close(sock: socket.socket, timeout: float = 2.0) -> bytes:
    sock.settimeout(timeout)
    chunks = b""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            chunk = sock.recv(4096)
        except TimeoutError:
            break
        if not chunk:
            break
        chunks += chunk
    return chunks


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


def test_rejects_non_positive_limits() -> None:
    with pytest.raises(ValueError, match="max_connections"):
        PortForwarder(8080, "127.0.0.1", 80, max_connections=0)
    with pytest.raises(ValueError, match="idle_timeout"):
        PortForwarder(8080, "127.0.0.1", 80, idle_timeout=0)


def test_bound_port_before_start_raises() -> None:
    forwarder = PortForwarder(0, "127.0.0.1", 9)
    with pytest.raises(RuntimeError, match="has not started"):
        _ = forwarder.bound_port


def test_forwards_bytes_to_local_echo() -> None:
    remote_port = _closed_port()
    remote_ready = threading.Event()
    remote = threading.Thread(
        target=_serve_once,
        args=("127.0.0.1", remote_port, b"ack:", remote_ready),
        daemon=True,
    )
    remote.start()
    assert remote_ready.wait(timeout=2)

    forwarder = PortForwarder(0, "127.0.0.1", remote_port)
    worker = _start_forwarder(forwarder)

    client = socket.create_connection(("127.0.0.1", forwarder.bound_port), timeout=2)
    client.sendall(b"ping")
    reply = _recv_until_close(client)
    client.close()
    forwarder.stop()
    worker.join(timeout=2)
    remote.join(timeout=2)

    assert reply == b"ack:ping"


def test_half_close_still_receives_reply() -> None:
    remote_port = _closed_port()
    remote_ready = threading.Event()
    remote = threading.Thread(
        target=_serve_until_eof_then_reply,
        args=("127.0.0.1", remote_port, b"ack:", remote_ready),
        daemon=True,
    )
    remote.start()
    assert remote_ready.wait(timeout=2)

    forwarder = PortForwarder(0, "127.0.0.1", remote_port)
    worker = _start_forwarder(forwarder)

    client = socket.create_connection(("127.0.0.1", forwarder.bound_port), timeout=2)
    client.sendall(b"ping")
    client.shutdown(socket.SHUT_WR)
    reply = _recv_until_close(client)
    client.close()
    forwarder.stop()
    worker.join(timeout=2)
    remote.join(timeout=2)

    assert reply == b"ack:ping"


def test_remote_connect_failure_closes_client() -> None:
    forwarder = PortForwarder(0, "127.0.0.1", _closed_port())
    worker = _start_forwarder(forwarder)

    client = socket.create_connection(("127.0.0.1", forwarder.bound_port), timeout=2)
    data = _recv_until_close(client)
    client.close()
    forwarder.stop()
    worker.join(timeout=2)

    assert data == b""


def test_remote_connect_timeout_closes_client() -> None:
    # TEST-NET-1 is not routed; connect should time out or fail quickly.
    forwarder = PortForwarder(0, "192.0.2.1", 80, connect_timeout=0.2)
    worker = _start_forwarder(forwarder)

    client = socket.create_connection(("127.0.0.1", forwarder.bound_port), timeout=2)
    data = _recv_until_close(client, timeout=2.0)
    client.close()
    forwarder.stop()
    worker.join(timeout=2)

    assert data == b""


def test_context_manager_stop_closes_listener() -> None:
    remote_port = _closed_port()
    with PortForwarder(0, "127.0.0.1", remote_port) as forwarder:
        worker = _start_forwarder(forwarder)
        bound = forwarder.bound_port

    worker.join(timeout=2)
    with pytest.raises(ConnectionRefusedError):
        socket.create_connection(("127.0.0.1", bound), timeout=0.5)


def _hold_one_connection(
    host: str,
    port: int,
    started: threading.Event,
    release: threading.Event,
) -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)
    started.set()
    conn, _addr = server.accept()
    release.wait(timeout=5)
    conn.close()
    server.close()


def test_max_connections_rejects_extra_client() -> None:
    remote_port = _closed_port()
    remote_ready = threading.Event()
    release = threading.Event()
    remote = threading.Thread(
        target=_hold_one_connection,
        args=("127.0.0.1", remote_port, remote_ready, release),
        daemon=True,
    )
    remote.start()
    assert remote_ready.wait(timeout=2)

    forwarder = PortForwarder(0, "127.0.0.1", remote_port, max_connections=1)
    worker = _start_forwarder(forwarder)
    first = socket.create_connection(("127.0.0.1", forwarder.bound_port), timeout=2)
    time.sleep(0.2)
    extra = socket.create_connection(("127.0.0.1", forwarder.bound_port), timeout=2)
    dropped = _recv_until_close(extra, timeout=1.0)
    extra.close()
    release.set()
    first.close()
    forwarder.stop()
    worker.join(timeout=2)
    remote.join(timeout=2)

    assert dropped == b""


def test_allowlist_rejects_non_matching_client() -> None:
    forwarder = PortForwarder(0, "127.0.0.1", _closed_port(), allow=["10.0.0.0/8"])
    worker = _start_forwarder(forwarder)
    client = socket.create_connection(("127.0.0.1", forwarder.bound_port), timeout=2)
    data = _recv_until_close(client, timeout=1.0)
    client.close()
    forwarder.stop()
    worker.join(timeout=2)

    assert data == b""


def test_allowlist_accepts_matching_client() -> None:
    remote_port = _closed_port()
    remote_ready = threading.Event()
    remote = threading.Thread(
        target=_serve_once,
        args=("127.0.0.1", remote_port, b"ack:", remote_ready),
        daemon=True,
    )
    remote.start()
    assert remote_ready.wait(timeout=2)

    forwarder = PortForwarder(0, "127.0.0.1", remote_port, allow=["127.0.0.1"])
    worker = _start_forwarder(forwarder)
    client = socket.create_connection(("127.0.0.1", forwarder.bound_port), timeout=2)
    client.sendall(b"ping")
    reply = _recv_until_close(client)
    client.close()
    forwarder.stop()
    worker.join(timeout=2)
    remote.join(timeout=2)

    assert reply == b"ack:ping"


def test_idle_timeout_closes_quiet_session() -> None:
    remote_port = _closed_port()
    remote_ready = threading.Event()
    release = threading.Event()
    remote = threading.Thread(
        target=_hold_one_connection,
        args=("127.0.0.1", remote_port, remote_ready, release),
        daemon=True,
    )
    remote.start()
    assert remote_ready.wait(timeout=2)

    forwarder = PortForwarder(0, "127.0.0.1", remote_port, idle_timeout=0.3)
    worker = _start_forwarder(forwarder)
    client = socket.create_connection(("127.0.0.1", forwarder.bound_port), timeout=2)
    data = _recv_until_close(client, timeout=2.0)
    client.close()
    release.set()
    forwarder.stop()
    worker.join(timeout=2)
    remote.join(timeout=2)

    assert data == b""


def test_finished_sessions_are_pruned() -> None:
    remote_port = _closed_port()
    remote_ready = threading.Event()
    remote = threading.Thread(
        target=_serve_once,
        args=("127.0.0.1", remote_port, b"ack:", remote_ready),
        daemon=True,
    )
    remote.start()
    assert remote_ready.wait(timeout=2)

    forwarder = PortForwarder(0, "127.0.0.1", remote_port)
    worker = _start_forwarder(forwarder)
    client = socket.create_connection(("127.0.0.1", forwarder.bound_port), timeout=2)
    client.sendall(b"ping")
    _recv_until_close(client)
    client.close()
    time.sleep(0.2)
    forwarder.prune_sessions()
    leftover = list(forwarder.session_threads)
    forwarder.stop()
    worker.join(timeout=2)
    remote.join(timeout=2)

    assert leftover == []
