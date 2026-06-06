"""Smoke tests for agentdeck."""

from __future__ import annotations

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
