"""Command-line interface for Port Forwarder."""

from __future__ import annotations

import argparse
import logging
import math
import signal
import sys
from collections.abc import Callable

from .forwarder import DEFAULT_CONNECT_TIMEOUT, PortForwarder
from .group import PortForwarderGroup
from .mapping import parse_targets
from .version import get_version


def _positive_timeout(value: str) -> float:
    try:
        timeout = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timeout must be a number") from exc
    if not math.isfinite(timeout) or timeout <= 0:
        raise argparse.ArgumentTypeError("timeout must be greater than 0")
    return timeout


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def _log_level(verbose: bool, quiet: bool) -> int:
    if verbose:
        return logging.DEBUG
    if quiet:
        return logging.WARNING
    return logging.INFO


def install_signal_handlers(on_stop: Callable[[], None]) -> None:
    """Stop the process on SIGINT and SIGTERM."""

    def handler(signum: int, frame: object | None) -> None:
        on_stop()

    signal.signal(signal.SIGINT, handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handler)


def build_parser() -> argparse.ArgumentParser:
    """Build the ``port-forwarder`` argument parser."""
    parser = argparse.ArgumentParser(
        description="Forward local TCP traffic to a remote host and port.",
    )
    parser.add_argument(
        "targets",
        nargs="+",
        metavar="TARGET",
        help="LOCAL HOST REMOTE, or one or more LOCAL:HOST:REMOTE mappings",
    )
    parser.add_argument(
        "--bind",
        default="127.0.0.1",
        metavar="HOST",
        help="Local address to bind (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--timeout",
        dest="connect_timeout",
        type=_positive_timeout,
        default=DEFAULT_CONNECT_TIMEOUT,
        metavar="SECONDS",
        help=f"Remote connect timeout in seconds (default: {DEFAULT_CONNECT_TIMEOUT:g})",
    )
    parser.add_argument(
        "--max-connections",
        dest="max_connections",
        type=_positive_int,
        default=None,
        metavar="N",
        help="Maximum concurrent sessions per listener (default: unlimited)",
    )
    parser.add_argument(
        "--allow",
        action="append",
        default=[],
        metavar="IP|CIDR",
        help="Allow connections from this address or CIDR (repeatable)",
    )
    parser.add_argument(
        "--idle-timeout",
        dest="idle_timeout",
        type=_positive_timeout,
        default=None,
        metavar="SECONDS",
        help="Close a session after this many idle seconds (default: off)",
    )
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Log debug detail",
    )
    verbosity.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Log warnings and errors only",
    )
    parser.add_argument("--version", action="version", version=get_version())
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        return code if isinstance(code, int) else 1

    try:
        mappings = parse_targets(args.targets)
    except ValueError as exc:
        print(f"port-forwarder: {exc}", file=sys.stderr)
        return 1

    logging.basicConfig(level=_log_level(args.verbose, args.quiet), format="%(message)s")
    allow = args.allow or None
    forwarders = [
        PortForwarder(
            mapping.local_port,
            mapping.remote_host,
            mapping.remote_port,
            bind_host=args.bind,
            connect_timeout=args.connect_timeout,
            max_connections=args.max_connections,
            allow=allow,
            idle_timeout=args.idle_timeout,
        )
        for mapping in mappings
    ]
    group = PortForwarderGroup(forwarders)
    install_signal_handlers(group.stop)
    try:
        group.start()
    except KeyboardInterrupt:
        group.stop()
        return 0
    except OSError as exc:
        print(f"port-forwarder: {exc}", file=sys.stderr)
        return 1
    return 0
