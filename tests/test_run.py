"""Tests for the run.py launcher."""

from __future__ import annotations

import importlib.util
import os
import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_run():
    spec = importlib.util.spec_from_file_location("run", ROOT / "run.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["run"] = mod
    spec.loader.exec_module(mod)
    return mod


run = _load_run()


@pytest.fixture
def isolated_app_dir(tmp_path, monkeypatch):
    """Point APP_DIR at a temp directory so tests don't touch the user's real %LOCALAPPDATA%."""
    monkeypatch.setattr(run, "APP_DIR", tmp_path)
    monkeypatch.setattr(run, "PID_FILE", tmp_path / "server.pid")
    monkeypatch.setattr(run, "CLEAN_SHUTDOWN_MARKER", tmp_path / "clean_shutdown.txt")
    return tmp_path


def test_find_free_port_returns_a_usable_port():
    port = run.find_free_port(31000, 31100)
    assert 31000 <= port <= 31100
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", port))  # would raise if not free


def test_find_free_port_skips_taken_ports():
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        blocker.bind(("127.0.0.1", 0))
        taken = blocker.getsockname()[1]
        port = run.find_free_port(taken, taken + 50)
        assert port != taken
    finally:
        blocker.close()


def test_write_pid_file_writes_pid_port_token(isolated_app_dir):
    run.write_pid_file(8888, "deadbeef")
    content = (isolated_app_dir / "server.pid").read_text(encoding="utf-8")
    assert str(os.getpid()) in content
    assert ":8888:" in content
    assert content.endswith("deadbeef")


def test_drop_clean_shutdown_marker_creates_file(isolated_app_dir):
    assert not (isolated_app_dir / "clean_shutdown.txt").exists()
    run.drop_clean_shutdown_marker()
    assert (isolated_app_dir / "clean_shutdown.txt").exists()
    # Contains an ISO-8601 timestamp
    body = (isolated_app_dir / "clean_shutdown.txt").read_text(encoding="utf-8")
    assert "T" in body  # crude ISO-8601 check


def test_remove_pid_file_is_idempotent(isolated_app_dir):
    # Removing a missing file should not raise
    run.remove_pid_file()
    # And a real file should go away
    (isolated_app_dir / "server.pid").write_text("test", encoding="utf-8")
    run.remove_pid_file()
    assert not (isolated_app_dir / "server.pid").exists()


def test_main_creates_app_dir_and_pid_file(isolated_app_dir, monkeypatch):
    """End-to-end-ish: run ``main()`` with a pre-bound port and verify lifecycle."""
    import atexit
    import socket as _socket

    # Pick a port that is free right now
    with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        forced_port = s.getsockname()[1]

    # Patch web.run_app so we don't actually start a server
    from aiohttp import web

    started = {"called": False, "host": None, "port": None}

    def fake_run_app(app, host=None, port=None, print=None):
        started["called"] = True
        started["host"] = host
        started["port"] = port

    monkeypatch.setattr(web, "run_app", fake_run_app)

    # Capture the atexit handlers main() registers so we can fire them
    # explicitly. (atexit doesn't fire on a normal return from main(); it
    # only fires on interpreter shutdown / sys.exit.)
    registered = []

    real_register = atexit.register

    def capturing_register(fn, *args, **kwargs):
        registered.append((fn, args, kwargs))
        return real_register(fn, *args, **kwargs)

    monkeypatch.setattr(atexit, "register", capturing_register)

    rc = run.main(["--port", str(forced_port)])
    assert rc == 0
    assert started["called"] is True
    assert started["port"] == forced_port

    # Now manually fire the captured handlers and confirm cleanup state.
    for fn, args, kwargs in registered:
        fn(*args, **kwargs)

    assert not (isolated_app_dir / "server.pid").exists()
    assert (isolated_app_dir / "clean_shutdown.txt").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
