"""Smoke tests for agentdeck."""

from __future__ import annotations

import socket

from agentdeck.__main__ import _find_free_port
from agentdeck.server import _default_shell, make_app


def test_make_app_returns_aiohttp_app():
    app = make_app()
    assert app is not None
    assert hasattr(app, "router")


def test_default_shell_returns_a_nonempty_string():
    shell = _default_shell()
    assert isinstance(shell, str)
    assert len(shell) > 0


def test_index_route_is_registered():
    app = make_app()
    routes = [r.resource.canonical for r in app.router.routes()]
    assert "/" in routes


def test_ws_route_is_registered():
    app = make_app()
    routes = [r.resource.canonical for r in app.router.routes()]
    assert "/ws/{tab_id}" in routes


def test_find_free_port_returns_a_usable_port():
    """_find_free_port should hand back a port we can immediately bind to."""
    port = _find_free_port(30000, 30100)
    assert 30000 <= port <= 30100
    # And it really is free right now
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", port))  # would raise if not


def test_find_free_port_skips_taken_ports():
    """If the first candidate is occupied, _find_free_port moves on."""
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        blocker.bind(("127.0.0.1", 0))
        taken = blocker.getsockname()[1]
        port = _find_free_port(taken, taken + 50)
        assert port != taken
    finally:
        blocker.close()
