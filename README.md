# agentdeck

> A minimal multi-terminal desktop workspace that runs in your browser.

A tiny, no-frills multiplexer: open a tab, get a shell. Each tab is its own OS process. Bytes go in and out over WebSockets; the UI is xterm.js. No auth, no session save, no swarms, no fancy features. Just terminals.

## What it looks like

```
+-----------------------------------------------+
|  tab 1   tab 2   +              connected     |
+-----------------------------------------------+
|                                               |
|  $ ls                                         |
|  LICENSE  pyproject.toml  agentdeck/  ...     |
|  $ _                                         |
|                                               |
+-----------------------------------------------+
```

## Quick start

```bash
git clone https://github.com/phillza/agentdeck
cd agentdeck
pip install -e ".[dev]"

# Run the server
agentdeck

# Or open the UI in your default browser
agentdeck --open
```

Then visit http://127.0.0.1:8765 (or whatever port it picked).

## How it works

```
+-------------+    WebSocket     +-----------+    pipe    +--------+
|  Browser    | <--------------> |  aiohttp  | <--------> |  shell |
|  (xterm.js) |   binary bytes   |  server   |            | (bash, |
+-------------+                  +-----------+            |  cmd)  |
                                                            +--------+
```

- **One HTTP route** serves a single `index.html` page
- **One WebSocket route per tab** upgrades to a PTY-backed shell
- Each tab spawns a real OS process; bytes flow both ways
- Disconnect = process terminated

## Why I built this

I wanted a tiny, readable reference for "browser-based terminal multiplexer." Most projects in this space are thousands of lines with elaborate session management, persistence, and complex UIs. This is the opposite: ~150 lines of Python and ~100 lines of HTML, easy to read, easy to fork.

## Known limitations

This is a teaching/toy project, not production-grade:

- **No PTY** — uses plain pipes. Password prompts and terminal-size queries don't work.
- **No auth** — anyone who can reach the port gets a shell. Bind to `127.0.0.1` only.
- **No session resume** — disconnect = shell dies. Reconnect spawns a new one.
- **No resize** — terminal size is fixed at 120x30.
- **Windows quirks** — `cmd.exe` works but lacks the ANSI features of a real PTY. Use `wt.exe` or Windows Terminal + WSL for a better experience on Windows.

If you need a production-grade terminal-in-browser, look at [ttyd](https://github.com/tsl0922/ttyd) or [gotty](https://github.com/yudai/gotty) instead.

## Development

```bash
git clone https://github.com/phillza/agentdeck
cd agentdeck
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check .
```

## Architecture

```
agentdeck/
  __init__.py     # package metadata
  __main__.py     # CLI entry point (argparse + auto-port)
  server.py       # aiohttp app: serves /, handles /ws/{tab_id}
  static/
    index.html    # xterm.js UI with tab bar
tests/
  test_server.py  # smoke tests
```

Total: ~250 lines of Python + ~100 lines of HTML. Read it end-to-end in 10 minutes.

## License

MIT — see [LICENSE](LICENSE).
