"""Run one or more port forwarders as a group."""

from __future__ import annotations

import threading
from collections.abc import Sequence
from types import TracebackType

from .forwarder import PortForwarder


class PortForwarderGroup:
    """Start and stop several :class:`PortForwarder` instances together."""

    def __init__(self, forwarders: Sequence[PortForwarder]) -> None:
        """Create a group. ``start()`` has not been called yet.

        Parameters
        ----------
        forwarders
            One or more listeners to run together.

        Raises
        ------
        ValueError
            If ``forwarders`` is empty.
        """
        if not forwarders:
            raise ValueError("at least one forwarder is required")
        self.forwarders = list(forwarders)
        self._error: OSError | None = None
        self._error_lock = threading.Lock()

    def __enter__(self) -> PortForwarderGroup:
        """Return this group for ``with`` blocks."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Stop every forwarder."""
        self.stop()

    def start(self) -> None:
        """Run all listeners until :meth:`stop` is called.

        A single mapping stays on the calling thread. Several mappings
        each get a thread. If one listener fails to bind, the others
        are stopped and the bind error is raised.
        """
        if len(self.forwarders) == 1:
            self.forwarders[0].start()
            return

        workers = [
            threading.Thread(target=self._run, args=(forwarder,), daemon=True)
            for forwarder in self.forwarders
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        with self._error_lock:
            error = self._error
        if isinstance(error, OSError):
            raise error

    def stop(self) -> None:
        """Stop every forwarder in the group."""
        for forwarder in self.forwarders:
            forwarder.stop()

    def _run(self, forwarder: PortForwarder) -> None:
        try:
            forwarder.start()
        except OSError as exc:
            with self._error_lock:
                if self._error is None:
                    self._error = exc
            self.stop()
