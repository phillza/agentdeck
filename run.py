"""Launcher: start the agentdeck server and manage the watchdog PID file.

The watchdog helper at ``scripts/agentdeck_watchdog.py`` looks for a PID file
at ``%LOCALAPPDATA%\\AgentDeck\\server.pid`` in the form ``pid:port:token``.
This launcher writes that file on start, removes it on clean exit, and drops a
``clean_shutdown.txt`` marker so the watchdog knows the close was intentional
(versus a crash).

Usage::

    python run.py                 # auto-pick port, bind 127.0.0.1
    python run.py --port 9000     # specific port
    python run.py --open          # open the UI in your default browser
    python run.py --host 0.0.0.0  # bind all interfaces (NOT recommended without auth)

The server is the same one the ``agentdeck`` console script runs; this
launcher just adds the lifecycle files the watchdog depends on.
"""

from __future__ import annotations

import argparse
import atexit
import contextlib
import datetime as dt
import os
import signal
import socket
import sys
import webbrowser
from pathlib import Path

APP_DIR = Path(
    os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
) / "AgentDeck"
PID_FILE = APP_DIR / "server.pid"
CLEAN_SHUTDOWN_MARKER = APP_DIR / "clean_shutdown.txt"
START_PORT = 8765
END_PORT = 8864


def find_free_port(start: int, end: int) -> int:
    """Return the first port in ``[start, end]`` we can claim with ``bind()``."""
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No free port found in {start}-{end}")


def write_pid_file(port: int, token: str) -> None:
    """Write ``pid:port:token`` so the watchdog can find us."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(f"{os.getpid()}:{port}:{token}", encoding="utf-8")


def drop_clean_shutdown_marker() -> None:
    """Drop a marker that tells the watchdog this close was intentional."""
    with contextlib.suppress(OSError):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        CLEAN_SHUTDOWN_MARKER.write_text(
            dt.datetime.now().isoformat(timespec="seconds"),
            encoding="utf-8",
        )


def remove_pid_file() -> None:
    """Remove the PID file. Safe to call even if the file is missing."""
    with contextlib.suppress(OSError):
        PID_FILE.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agentdeck-run",
        description="Run agentdeck as a managed server with PID file + clean-shutdown marker.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="Bind port (0 = auto-pick from 8765-8864)",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the UI in your default browser after start",
    )
    parser.add_argument(
        "--no-marker",
        action="store_true",
        help="Skip writing the clean_shutdown marker (debug / watchdog testing only)",
    )
    args = parser.parse_args(argv)

    # atexit fires on normal Python exit (and after the signal handlers below
    # call sys.exit). The marker tells the watchdog we closed cleanly.
    atexit.register(drop_clean_shutdown_marker)
    atexit.register(remove_pid_file)

    def _on_signal(signum: int, _frame: object) -> None:
        # Raising SystemExit lets atexit fire and aiohttp shut down cleanly.
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    # Remove any leftover marker from a previous intentional close.
    CLEAN_SHUTDOWN_MARKER.unlink(missing_ok=True)

    port = args.port or find_free_port(START_PORT, END_PORT)
    token = os.urandom(8).hex()
    write_pid_file(port, token)
    print(
        f"agentdeck: http://{args.host}:{port}  pid={os.getpid()}  token={token[:6]}...",
        file=sys.stderr,
    )

    if args.open:
        webbrowser.open(f"http://{args.host}:{port}")

    from aiohttp import web

    from agentdeck.server import make_app

    app = make_app()
    if args.no_marker:
        # Debug: simulate a crash-like exit so the watchdog will try to restart
        atexit.unregister(drop_clean_shutdown_marker)
    web.run_app(app, host=args.host, port=port, print=lambda *a, **kw: None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
