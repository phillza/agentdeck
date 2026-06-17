# agentdeck

> A minimal multi-terminal desktop workspace that runs in your browser.

A tiny, no-frills multiplexer: open a tab, get a shell. Each tab is its own OS process. Bytes go in and out over WebSockets; the UI is xterm.js. No auth, no session save, no swarms, no fancy features. Just terminals.

![agentdeck tabs: terminal 1, terminal 2, plus, connected](https://placehold.co/640x320/0d1117/c9d1d9?text=agentdeck+screenshot+coming+soon)

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

# Or use the watchdog-friendly launcher (writes PID file, drops
# clean_shutdown marker on graceful exit, picks a free port 8765-8864)
python run.py
```

Then visit http://127.0.0.1:8765 (or whatever port it picked).

> Use `python run.py` when the watchdog is going to manage the process.
> Use the `agentdeck` console script for a one-shot interactive run.

## How it works

```
+-------------+    WebSocket     +-----------+    pipe    +--------+
|  Browser    | <--------------> |  aiohttp  | <--------> |  shell |
|  (xterm.js) |   binary bytes   |  server   |            | (bash, |
+-------------+                  +-----------+            |  cmd)  |
                                                            +--------+
```

- **One HTTP route** serves a single `index.html` page
- **One WebSocket route per tab** upgrades to a shell
- Each tab spawns a real OS process; bytes flow both ways
- Disconnect = process terminated

## Why I built this

I wanted a tiny, readable reference for "browser-based terminal multiplexer." Most projects in this space are thousands of lines with elaborate session management, persistence, and complex UIs. This is the opposite: ~150 lines of Python and ~100 lines of HTML, easy to read, easy to fork.

## Production tips

For long-running installations (e.g. dev machines, kiosk setups), agentdeck ships a small watchdog helper that restarts the server if the listening port goes dead:

```bash
# Start the server (writes pid:port:token to %LOCALAPPDATA%\AgentDeck\server.pid)
python run.py

# In a separate shell, one-shot health check (uses ~8700-8800 port range)
python scripts/agentdeck_watchdog.py --check

# Windows-only: install a Task Scheduler entry that runs --check every minute
python scripts/agentdeck_watchdog.py --install-task
.\scripts\install_watchdog_task.bat
```

The watchdog distinguishes "agentdeck was intentionally closed" from "agentdeck crashed" via a `clean_shutdown.txt` marker in `%LOCALAPPDATA%\AgentDeck\`. The launcher (`run.py`) writes that marker via an `atexit` handler on a clean Python exit (Ctrl+C, `sys.exit`, normal shutdown), and removes the marker on the next start. If the watchdog finds a stale PID file or a dead port with **no** marker, it respawns `run.py` detached.

For debugging, `python run.py --no-marker` skips the `clean_shutdown` write so the watchdog will try to restart on the next check — useful for testing the auto-recovery loop.

To smoke-test rendering from inside a running agentdeck tab:

```bash
python scripts/terminal_torture.py            # 120 ms between chunks
python scripts/terminal_torture.py --no-delay # all chunks back-to-back
```

That script emits a fixed sequence of colour, truecolour, wide-Unicode, line-wrap, progress-bar (`\r`), alternate-screen (`\x1b[?1049h`), and mouse-mode (`\x1b[?1000h`) escape sequences. If something looks wrong in your terminal, this is the easiest way to reproduce it.

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

A GitHub Actions workflow under `.github/workflows/ci.yml` runs the test matrix on Python 3.10-3.12 for every push and PR.

## Architecture

```
agentdeck/
  __init__.py     # package metadata
  __main__.py     # CLI entry point (argparse + auto-port)
  server.py       # aiohttp app: serves /, handles /ws/{tab_id}
  static/
    index.html    # xterm.js UI with tab bar
run.py            # Watchdog-aware launcher (PID file + clean_shutdown marker)
scripts/
  agentdeck_watchdog.py     # auto-restart helper (Windows-friendly)
  terminal_torture.py       # smoke-test escape sequences
  install_watchdog_task.bat # Windows Task Scheduler installer
tests/
  test_server.py   # smoke tests for make_app + find_free_port
  test_watchdog.py # watchdog helpers
  test_run.py      # run.py launcher lifecycle
```

Total: ~250 lines of Python + ~100 lines of HTML. Read it end-to-end in 10 minutes.

## License

MIT — see [LICENSE](LICENSE).
