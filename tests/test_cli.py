"""CLI entrypoint."""

from __future__ import annotations

import signal
import socket
import subprocess
import sys
import time

import pytest

from lupaxa.port_forwarder.cli import build_parser, main
from lupaxa.port_forwarder.version import get_version


def test_help_exits_zero() -> None:
    assert main(["--help"]) == 0


def test_version_flag(capsys) -> None:
    assert main(["--version"]) == 0
    assert get_version() in capsys.readouterr().out


def test_parser_defaults() -> None:
    args = build_parser().parse_args(["8080", "db.internal", "5432"])
    assert args.targets == ["8080", "db.internal", "5432"]
    assert args.bind == "127.0.0.1"
    assert args.connect_timeout == 10.0
    assert args.max_connections is None
    assert args.allow == []
    assert args.idle_timeout is None
    assert args.verbose is False
    assert args.quiet is False


def test_parser_bind_override() -> None:
    args = build_parser().parse_args(["8080", "10.0.0.8", "80", "--bind", "0.0.0.0"])
    assert args.bind == "0.0.0.0"


def test_parser_timeout_and_verbose() -> None:
    args = build_parser().parse_args(
        ["8080", "db.internal", "5432", "--timeout", "2.5", "--verbose"],
    )
    assert args.connect_timeout == 2.5
    assert args.verbose is True


def test_parser_quiet() -> None:
    args = build_parser().parse_args(["8080", "db.internal", "5432", "--quiet"])
    assert args.quiet is True


def test_parser_rejects_verbose_and_quiet_together() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["8080", "db.internal", "5432", "--verbose", "--quiet"])


def test_parser_rejects_non_positive_timeout() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["8080", "127.0.0.1", "80", "--timeout", "0"])


def test_main_rejects_invalid_port() -> None:
    assert main(["0", "127.0.0.1", "80"]) == 1


def test_main_rejects_non_integer_port() -> None:
    assert main(["abc", "127.0.0.1", "80"]) == 1


def test_main_rejects_out_of_range_port() -> None:
    assert main(["70000", "127.0.0.1", "80"]) == 1


def test_main_bind_failure() -> None:
    assert main(["8080", "127.0.0.1", "80", "--bind", "256.256.256.256"]) == 1


def test_parser_mappings_and_limits() -> None:
    args = build_parser().parse_args(
        [
            "8080:host:80",
            "5432:db:5432",
            "--max-connections",
            "4",
            "--allow",
            "10.0.0.0/8",
            "--allow",
            "127.0.0.1",
            "--idle-timeout",
            "30",
        ],
    )
    assert args.targets == ["8080:host:80", "5432:db:5432"]
    assert args.max_connections == 4
    assert args.allow == ["10.0.0.0/8", "127.0.0.1"]
    assert args.idle_timeout == 30.0


def test_parser_rejects_non_positive_idle_timeout() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["8080", "127.0.0.1", "80", "--idle-timeout", "0"])


def test_parser_rejects_non_positive_max_connections() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["8080", "127.0.0.1", "80", "--max-connections", "0"])


def test_main_rejects_bad_mapping() -> None:
    assert main(["8080:80"]) == 1


def test_sigterm_exits_cleanly() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        local_port = int(sock.getsockname()[1])
    proc = subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            "-u",
            "-m",
            "lupaxa.port_forwarder",
            str(local_port),
            "127.0.0.1",
            "9",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert proc.stdout is not None
    heard = ""
    deadline = time.time() + 5
    while time.time() < deadline:
        line = proc.stdout.readline()
        heard += line
        if "Listening" in line:
            break
    else:
        proc.kill()
        pytest.fail(f"forwarder did not log listen: {heard!r}")
    proc.send_signal(signal.SIGTERM)
    assert proc.wait(timeout=5) == 0
