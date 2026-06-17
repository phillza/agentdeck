"""Minimal WebSocket + PTY server for agentdeck.

The server:
- Serves a single static index.html at /
- Upgrades WebSocket connections at /ws/{tab_id} to a PTY
- Each tab is its own shell process; pipes bytes between the browser and the shell
- On disconnect, the process is terminated

This is intentionally simple: no auth, no session resume, no reconnection logic.
The point is a tiny, readable example of a browser-based terminal multiplexer.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import sys
from pathlib import Path

from aiohttp import WSMsgType, web

STATIC_DIR = Path(__file__).parent / "static"

# Per-platform default shell.
DEFAULT_SHELL: dict[str, str] = {
    "win32": os.environ.get("COMSPEC", "cmd.exe"),
    "linux": os.environ.get("SHELL", "/bin/bash"),
    "darwin": os.environ.get("SHELL", "/bin/zsh"),
}


def _default_shell() -> str:
    return DEFAULT_SHELL.get(sys.platform, "/bin/sh")


async def handle_index(_request: web.Request) -> web.Response:
    """Serve the single-page UI."""
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return web.Response(text=html, content_type="text/html")


async def handle_terminal(request: web.Request) -> web.WebSocketResponse:
    """One WebSocket per tab. Spawns a shell, pipes bytes both ways."""
    ws = web.WebSocketResponse(heartbeat=30)
    await ws.prepare(request)
    tab_id = request.match_info.get("tab_id", "default")

    # Spawn shell. We use pipes (not a real PTY) for simplicity.
    # That means features like password prompts and terminal-size queries
    # will not work — this is a known limitation, not a bug.
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["COLUMNS"] = "120"
    env["LINES"] = "30"
    env["AGENTDECK_TAB"] = tab_id

    proc = await asyncio.create_subprocess_exec(
        _default_shell(),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
    )

    async def pump_output() -> None:
        """Read from process stdout, write to WebSocket."""
        assert proc.stdout is not None
        try:
            while True:
                chunk = await proc.stdout.read(4096)
                if not chunk:
                    break
                await ws.send_bytes(chunk)
        except (ConnectionResetError, asyncio.CancelledError):
            pass

    pump_task = asyncio.create_task(pump_output())

    try:
        async for msg in ws:
            if msg.type == WSMsgType.BINARY:
                # Raw bytes from the terminal emulator go straight to the shell
                if proc.stdin is None:
                    break
                proc.stdin.write(msg.data)
                await proc.stdin.drain()
            elif msg.type == WSMsgType.TEXT:
                # Reserved for future control messages (resize, signal, etc.)
                pass
            elif msg.type == WSMsgType.ERROR:
                break
    finally:
        pump_task.cancel()
        try:
            proc.terminate()
            await asyncio.wait_for(proc.wait(), timeout=2.0)
        except (ProcessLookupError, asyncio.TimeoutError):
            with contextlib.suppress(ProcessLookupError):
                proc.kill()

    return ws


def make_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/ws/{tab_id}", handle_terminal)
    return app
