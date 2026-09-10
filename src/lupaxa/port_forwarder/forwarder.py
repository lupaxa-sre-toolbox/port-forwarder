"""TCP port-forwarding service."""

from __future__ import annotations

import contextlib
import ipaddress
import logging
import socket
import threading
import time
from collections.abc import Callable, Sequence
from types import TracebackType

from .mapping import address_allowed, parse_allow

LOGGER = logging.getLogger(__name__)
_BUFFER_SIZE = 4096
_ACCEPT_TIMEOUT = 0.5
_IDLE_POLL = 0.5
_SESSION_JOIN_TIMEOUT = 30.0
DEFAULT_BACKLOG = 128
DEFAULT_CONNECT_TIMEOUT = 10.0


def _listen_family(host: str) -> socket.AddressFamily:
    if ":" in host:
        return socket.AF_INET6
    return socket.AF_INET


def _set_tcp_nodelay(sock: socket.socket) -> None:
    with contextlib.suppress(OSError):
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)


class _Activity:
    """Shared last-byte time for both directions of one session."""

    def __init__(self) -> None:
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def touch(self) -> None:
        with self._lock:
            self._last = time.monotonic()

    def idle_for(self) -> float:
        with self._lock:
            return time.monotonic() - self._last


class PortForwarder:
    """Listen on a local TCP port and relay bytes to a remote host."""

    def __init__(
        self,
        local_port: int,
        remote_host: str,
        remote_port: int,
        *,
        bind_host: str = "127.0.0.1",
        backlog: int = DEFAULT_BACKLOG,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
        max_connections: int | None = None,
        allow: Sequence[str] | None = None,
        idle_timeout: float | None = None,
    ) -> None:
        """Create a forwarder that is not yet listening.

        Parameters
        ----------
        local_port
            Local TCP port to bind. ``0`` asks the OS for an ephemeral port.
        remote_host
            Hostname or address to connect to for each accepted client.
        remote_port
            Remote TCP port to connect to.
        bind_host
            Local address to bind. Defaults to loopback.
        backlog
            ``listen`` backlog for the server socket.
        connect_timeout
            Seconds to wait when opening the remote side.
        max_connections
            Maximum concurrent sessions on this listener. ``None`` is unlimited.
        allow
            Source host addresses or CIDR networks. ``None`` or empty allows all.
        idle_timeout
            Close a session after this many seconds without bytes. ``None`` is off.

        Raises
        ------
        ValueError
            If ``max_connections`` or ``idle_timeout`` is not positive, or an
            allow entry is not an IP address or CIDR.
        """
        if max_connections is not None and max_connections < 1:
            raise ValueError("max_connections must be at least 1")
        if idle_timeout is not None and idle_timeout <= 0:
            raise ValueError("idle_timeout must be greater than 0")
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.bind_host = bind_host
        self.backlog = backlog
        self.connect_timeout = connect_timeout
        self.max_connections = max_connections
        self.idle_timeout = idle_timeout
        self._allow: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = (
            parse_allow(list(allow)) if allow else []
        )
        self.server_socket: socket.socket | None = None
        self._bound_port: int | None = None
        self._stop = threading.Event()
        self._live_sockets: set[socket.socket] = set()
        self._sockets_lock = threading.Lock()
        self._sessions: list[threading.Thread] = []
        self._sessions_lock = threading.Lock()
        self._active = 0
        self._active_lock = threading.Lock()

    def __enter__(self) -> PortForwarder:
        """Return this forwarder for ``with`` blocks."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Stop accepting and close in-flight sockets."""
        self.stop()

    @property
    def bound_port(self) -> int:
        """Return the port the server socket is bound to.

        Raises
        ------
        RuntimeError
            If :meth:`start` has not bound a socket yet.
        """
        if self._bound_port is None:
            raise RuntimeError("port forwarder has not started")
        return self._bound_port

    @property
    def session_threads(self) -> tuple[threading.Thread, ...]:
        """Return a snapshot of session threads, including finished ones."""
        with self._sessions_lock:
            return tuple(self._sessions)

    def prune_sessions(self) -> None:
        """Drop finished session threads from the tracked list."""
        with self._sessions_lock:
            self._sessions = [worker for worker in self._sessions if worker.is_alive()]

    def start(self, on_ready: Callable[[], None] | None = None) -> None:
        """Bind, listen, and accept clients until :meth:`stop` is called."""
        self._stop.clear()
        server = socket.create_server(
            (self.bind_host, self.local_port),
            family=_listen_family(self.bind_host),
            backlog=self.backlog,
        )
        server.settimeout(_ACCEPT_TIMEOUT)
        self.server_socket = server
        self._bound_port = int(server.getsockname()[1])
        LOGGER.info(
            "Listening on %s:%s and forwarding to %s:%s",
            self.bind_host,
            self._bound_port,
            self.remote_host,
            self.remote_port,
        )
        if on_ready is not None:
            on_ready()

        try:
            while not self._stop.is_set():
                self.prune_sessions()
                try:
                    client_socket, client_address = server.accept()
                except TimeoutError:
                    continue
                except OSError:
                    if self._stop.is_set():
                        break
                    raise
                if not self._client_allowed(client_address):
                    LOGGER.warning("Rejected connection from %s", client_address[0])
                    client_socket.close()
                    continue
                if not self._try_begin_session():
                    LOGGER.warning(
                        "Rejected connection from %s: max connections reached",
                        client_address[0],
                    )
                    client_socket.close()
                    continue
                LOGGER.info("Connection from %s", client_address)
                worker = threading.Thread(
                    target=self.handle_connection,
                    args=(client_socket,),
                    daemon=True,
                )
                with self._sessions_lock:
                    self._sessions.append(worker)
                worker.start()
        finally:
            self._close_server()

    def stop(self) -> None:
        """Stop accepting, close live sockets, and wait for session threads."""
        self._stop.set()
        self._close_server()
        with self._sockets_lock:
            live = list(self._live_sockets)
        for sock in live:
            self._close_socket(sock)
        with self._sessions_lock:
            sessions = list(self._sessions)
            self._sessions.clear()
        for worker in sessions:
            worker.join(timeout=_SESSION_JOIN_TIMEOUT)
            if worker.is_alive():
                LOGGER.warning("Session thread %s still running after stop", worker.name)

    def handle_connection(self, client_socket: socket.socket) -> None:
        """Open the remote side and relay bytes in both directions."""
        try:
            self._register_socket(client_socket)
            _set_tcp_nodelay(client_socket)
            try:
                remote_socket = socket.create_connection(
                    (self.remote_host, self.remote_port),
                    timeout=self.connect_timeout,
                )
            except OSError:
                LOGGER.exception("Error connecting to remote host")
                self._close_socket(client_socket)
                return

            remote_socket.settimeout(None)
            self._register_socket(remote_socket)
            _set_tcp_nodelay(remote_socket)
            try:
                self._relay(client_socket, remote_socket)
            finally:
                self._close_socket(remote_socket)
                self._close_socket(client_socket)
        finally:
            self._end_session()

    def forward(
        self,
        source: socket.socket,
        destination: socket.socket,
        activity: _Activity | None = None,
    ) -> None:
        """Copy bytes from ``source`` to ``destination`` until the stream ends."""
        idle = self.idle_timeout
        if idle is not None:
            source.settimeout(min(_IDLE_POLL, idle))
        expired = False
        try:
            while True:
                try:
                    data = source.recv(_BUFFER_SIZE)
                except TimeoutError:
                    if idle is not None and activity is not None and activity.idle_for() >= idle:
                        expired = True
                        break
                    continue
                if not data:
                    break
                if activity is not None:
                    activity.touch()
                destination.sendall(data)
        except OSError:
            LOGGER.debug("Connection closed", exc_info=True)
        finally:
            if expired:
                for sock in (source, destination):
                    with contextlib.suppress(OSError):
                        sock.shutdown(socket.SHUT_RDWR)
            else:
                with contextlib.suppress(OSError):
                    destination.shutdown(socket.SHUT_WR)

    def _relay(self, left: socket.socket, right: socket.socket) -> None:
        activity = _Activity()
        outgoing = threading.Thread(
            target=self.forward,
            args=(left, right, activity),
            daemon=True,
        )
        incoming = threading.Thread(
            target=self.forward,
            args=(right, left, activity),
            daemon=True,
        )
        outgoing.start()
        incoming.start()
        outgoing.join()
        incoming.join()

    def _client_allowed(self, client_address: object) -> bool:
        if not isinstance(client_address, tuple) or not client_address:
            return False
        return address_allowed(str(client_address[0]), self._allow)

    def _try_begin_session(self) -> bool:
        if self.max_connections is None:
            return True
        with self._active_lock:
            if self._active >= self.max_connections:
                return False
            self._active += 1
            return True

    def _end_session(self) -> None:
        if self.max_connections is None:
            return
        with self._active_lock:
            if self._active > 0:
                self._active -= 1

    def _register_socket(self, sock: socket.socket) -> None:
        with self._sockets_lock:
            self._live_sockets.add(sock)

    def _close_socket(self, sock: socket.socket) -> None:
        with self._sockets_lock:
            self._live_sockets.discard(sock)
        with contextlib.suppress(OSError):
            sock.shutdown(socket.SHUT_RDWR)
        with contextlib.suppress(OSError):
            sock.close()

    def _close_server(self) -> None:
        server = self.server_socket
        self.server_socket = None
        if server is None:
            return
        try:
            server.close()
        except OSError:
            LOGGER.debug("Listen socket already closed", exc_info=True)
