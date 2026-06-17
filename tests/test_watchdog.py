"""Tests for the agentdeck watchdog helper and torture script."""

from __future__ import annotations

import importlib.util
import socket
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"


def _load(name: str):
    """Import a script from scripts/ without making scripts/ a package."""
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
    assert spec is not None and spec.loader is not None, f"Could not load {name}.py"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


watchdog = _load("agentdeck_watchdog")
torture = _load("terminal_torture")


def test_port_alive_returns_true_for_listening_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        port = s.getsockname()[1]
        assert watchdog.port_alive(port) is True
    finally:
        s.close()


def test_port_alive_returns_false_for_closed_port():
    """Pick a port we can be confident is free, then assert it's reported as dead."""
    candidate = 39000
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", candidate))
            except OSError:
                candidate += 1
                continue
            break
    assert watchdog.port_alive(candidate) is False


def test_read_pid_file_returns_none_for_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(watchdog, "PID_FILE", tmp_path / "nope.pid")
    assert watchdog.read_pid_file() == (None, None, None)


def test_read_pid_file_parses_pid_port_token(tmp_path, monkeypatch):
    pid_file = tmp_path / "server.pid"
    pid_file.write_text("12345:8888:abc-def\n", encoding="utf-8")
    monkeypatch.setattr(watchdog, "PID_FILE", pid_file)
    assert watchdog.read_pid_file() == (12345, 8888, "abc-def")


def test_read_pid_file_handles_garbage(tmp_path, monkeypatch):
    pid_file = tmp_path / "server.pid"
    pid_file.write_text("not-a-pid:also-bad:\n", encoding="utf-8")
    monkeypatch.setattr(watchdog, "PID_FILE", pid_file)
    pid, port, _ = watchdog.read_pid_file()
    assert pid is None
    assert port is None


def test_build_torture_sequence_returns_strings():
    """The torture sequence should always be a non-empty list of strings."""
    seq = torture.build_torture_sequence()
    assert isinstance(seq, list)
    assert len(seq) > 0
    assert all(isinstance(chunk, str) for chunk in seq)
    # At least one chunk should be a non-empty escape sequence
    assert any(chunk for chunk in seq)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
