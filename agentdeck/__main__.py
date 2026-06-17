"""CLI entry point: agentdeck [--host HOST] [--port PORT] [--open]"""

from __future__ import annotations

import argparse
import socket
import sys
import webbrowser

from .server import make_app


def _find_free_port(start: int, end: int) -> int:
    """Return the first port in ``[start, end]`` we can claim with ``bind()``.

    Using ``bind()`` (rather than ``connect_ex()``) is deliberate: it asks the
    OS whether the port is free, regardless of TIME_WAIT state or a half-closed
    socket. ``connect_ex`` can be flaky in those edge cases.
    """
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No free port found in {start}-{end}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agentdeck",
        description="Multi-terminal workspace in your browser",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=0, help="Bind port (default: auto-pick 8765-8864)")
    parser.add_argument("--open", action="store_true", help="Open the UI in your default browser")
    args = parser.parse_args(argv)

    port = args.port or _find_free_port(8765, 8864)
    app = make_app()

    from aiohttp import web
    print(f"agentdeck: http://{args.host}:{port}", file=sys.stderr)
    if args.open:
        webbrowser.open(f"http://{args.host}:{port}")
    web.run_app(app, host=args.host, port=port, print=lambda *a, **kw: None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
