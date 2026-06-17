"""Emit terminal control sequences that stress agentdeck/xterm rendering.

Run inside an agentdeck terminal::

    python scripts/terminal_torture.py

Use ``--no-delay`` for tests or quick manual checks.
"""

from __future__ import annotations

import argparse
import sys
import time

ESC = "\x1b"


def build_torture_sequence() -> list[str]:
    """Return a list of escape-sequence chunks that exercise the xterm renderer."""
    long_line = "WRAP " + ("0123456789 " * 24)
    return [
        f"{ESC}[2J{ESC}[H",
        "agentdeck terminal torture start\r\n",
        f"{ESC}[31mred{ESC}[0m {ESC}[32mgreen{ESC}[0m {ESC}[38;2;80;160;255mtruecolour{ESC}[0m\r\n",
        "Unicode width: cafe\u0301 | box \u2502\u2500\u2518 | emoji \U0001f680\r\n",
        long_line + "\r\n",
        "progress 000%",
        "\rprogress 050%",
        "\rprogress 100%\r\n",
        f"{ESC}[?1049h{ESC}[H{ESC}[2J",
        "alternate screen active\r\n",
        f"{ESC}[?1000hmouse mode on\r\n",
        f"{ESC}[?1000lmouse mode off\r\n",
        f"{ESC}[?1049l",
        "returned from alternate screen\r\n",
        f"{ESC}[2Kline cleared then replaced\r\n",
        "agentdeck terminal torture done\r\n",
    ]


def emit(delay: float) -> None:
    """Write the torture sequence to stdout in chunks, sleeping ``delay`` between them."""
    for chunk in build_torture_sequence():
        try:
            sys.stdout.write(chunk)
            sys.stdout.flush()
        except UnicodeEncodeError:
            sys.stdout.buffer.write(chunk.encode("utf-8", errors="replace"))
            sys.stdout.buffer.flush()
        if delay > 0:
            time.sleep(delay)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-delay", action="store_true", help="emit all chunks without sleeping")
    args = parser.parse_args()
    emit(0.0 if args.no_delay else 0.12)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
