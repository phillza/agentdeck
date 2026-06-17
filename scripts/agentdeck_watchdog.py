"""Restart agentdeck if the saved server port is no longer reachable.

Designed for Windows. On other platforms the watchdog still works for
detection, but the scheduled-task installer is Windows-only.

Usage:
    python scripts/agentdeck_watchdog.py --check           # one-shot health check
    python scripts/agentdeck_watchdog.py --install-task     # install Task Scheduler entry
    python scripts/agentdeck_watchdog.py --force-start     # start agentdeck even with no pid file

When the watchdog can't find a live server, no pid file, and no clean
shutdown marker, it spawns ``run.py`` (or the current executable) detached
so the agentdeck server comes back up automatically.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import os
import socket
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = Path(
    os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
) / "AgentDeck"
PID_FILE = APP_DIR / "server.pid"
LOG_FILE = APP_DIR / "watchdog.log"
RESTART_MARKER = APP_DIR / "watchdog_last_restart.txt"
CLEAN_SHUTDOWN_MARKER = APP_DIR / "clean_shutdown.txt"
TASK_NAME = r"AgentDeck\Server Watchdog"
RESTART_COOLDOWN_SECONDS = 45
DEFAULT_PORT_RANGE = range(8700, 8801)


def log(message: str) -> None:
    """Append a timestamped line to the watchdog log and stdout."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} {message}"
    print(line)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def read_pid_file() -> tuple[int | None, int | None, str | None]:
    """Read ``pid:port:token`` from the pid file. Missing pieces are None."""
    try:
        raw = PID_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return None, None, None
    parts = raw.split(":", 2)
    try:
        pid = int(parts[0]) if len(parts) >= 1 and parts[0] else None
    except ValueError:
        pid = None
    try:
        port = int(parts[1]) if len(parts) >= 2 and parts[1] else None
    except ValueError:
        port = None
    token = parts[2] if len(parts) >= 3 else None
    return pid, port, token


def port_alive(port: int) -> bool:
    """Return True if any host on the loopback range accepts a TCP connect on ``port``."""
    for host in ("127.0.0.1", "::1"):
        family = socket.AF_INET6 if ":" in host else socket.AF_INET
        try:
            with socket.socket(family, socket.SOCK_STREAM) as sock:
                sock.settimeout(1.5)
                sock.connect((host, port))
                return True
        except OSError:
            continue
    return False


def pythonw_path() -> Path:
    """Prefer ``pythonw.exe`` (no console) on Windows; fall back to the current interpreter."""
    exe = Path(sys.executable)
    candidate = exe.with_name("pythonw.exe")
    return candidate if candidate.exists() else exe


def start_agentdeck() -> None:
    """Spawn the agentdeck launcher detached so the watchdog can return immediately."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        last_restart = float(RESTART_MARKER.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        last_restart = 0.0
    now = dt.datetime.now().timestamp()
    if now - last_restart < RESTART_COOLDOWN_SECONDS:
        log("Restart skipped because another watchdog restart was just requested")
        return
    RESTART_MARKER.write_text(str(now), encoding="utf-8")
    with contextlib.suppress(OSError):
        CLEAN_SHUTDOWN_MARKER.unlink(missing_ok=True)

    cmd = [str(pythonw_path()), str(REPO_ROOT / "run.py")]
    subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        | getattr(subprocess, "DETACHED_PROCESS", 0),
    )
    log(f"Started agentdeck launcher with {cmd[0]}")


def check_once(force_start: bool = False) -> int:
    """Run one watchdog pass. Returns 0 on success (including a no-op healthy check)."""
    pid, port, _token = read_pid_file()
    if port and port_alive(port):
        log(f"Server healthy on port {port} (pid file pid={pid})")
        return 0

    if not PID_FILE.exists() and not force_start:
        for candidate in DEFAULT_PORT_RANGE:
            if port_alive(candidate):
                log(f"Server healthy on port {candidate} but pid file is missing")
                return 0
        if CLEAN_SHUTDOWN_MARKER.exists():
            log("No pid file found and clean shutdown marker exists; assuming agentdeck was intentionally closed")
            return 0
        log("No pid file found, no clean shutdown marker, and no server port is alive; restarting agentdeck")
        start_agentdeck()
        return 0

    if port:
        log(f"Server not reachable on stale pid file port {port}; restarting agentdeck")
    elif force_start:
        log("Force-start requested; starting agentdeck")
    else:
        log("Pid file exists but has no valid port; restarting agentdeck")

    start_agentdeck()
    return 0


def install_task() -> int:
    """Install a Windows Task Scheduler entry that runs ``--check`` once per minute."""
    task_cmd = f'"{sys.executable}" "{Path(__file__).resolve()}" --check'
    subprocess.run(
        ["schtasks", "/Create", "/TN", TASK_NAME, "/SC", "MINUTE", "/MO", "1", "/TR", task_cmd, "/F"],
        check=True,
    )
    log(f"Installed scheduled task {TASK_NAME} to check every 1 minute")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Restart agentdeck if the saved server port is no longer reachable."
    )
    parser.add_argument("--check", action="store_true", help="Run one watchdog check.")
    parser.add_argument(
        "--install-task",
        action="store_true",
        help="Install the Windows scheduled watchdog task.",
    )
    parser.add_argument(
        "--force-start",
        action="store_true",
        help="Start agentdeck even when no pid file exists.",
    )
    args = parser.parse_args()

    if args.install_task:
        return install_task()
    return check_once(force_start=args.force_start)


if __name__ == "__main__":
    raise SystemExit(main())
