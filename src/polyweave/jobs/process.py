"""Asking the OS whether a worker is still there, and ending one that is.

`docs/specs/tool-surface.md` §1 turns two things into OS questions: a poll that finds no
live process reports a failure rather than waiting, and `cancel` is not advisory. Both
have to work on Windows and on POSIX without a third-party dependency, because the
plugin runs wherever the renderer does.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

WINDOWS = sys.platform == "win32"

if WINDOWS:  # pragma: no cover - platform-specific
    import ctypes
    from ctypes import wintypes

    _SYNCHRONIZE = 0x00100000
    _PROCESS_TERMINATE = 0x0001
    _WAIT_TIMEOUT = 0x00000102
    _ERROR_ACCESS_DENIED = 5

    # Declared rather than called off `windll`: the default int return type truncates a
    # 64-bit HANDLE, which turns a live process into a closed one at random.
    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _k32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    _k32.OpenProcess.restype = wintypes.HANDLE
    _k32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    _k32.WaitForSingleObject.restype = wintypes.DWORD
    _k32.TerminateProcess.argtypes = (wintypes.HANDLE, wintypes.UINT)
    _k32.TerminateProcess.restype = wintypes.BOOL
    _k32.CloseHandle.argtypes = (wintypes.HANDLE,)
    _k32.CloseHandle.restype = wintypes.BOOL


def alive(pid: int | None) -> bool:
    """Whether `pid` names a process that has not exited.

    A pid outlives the process that held it, so this is never the whole answer: the
    heartbeat in `runner` is what separates a live worker from a reused number.
    """
    if not pid or pid <= 0:
        return False
    if WINDOWS:  # pragma: no cover - platform-specific
        handle = _k32.OpenProcess(_SYNCHRONIZE, False, pid)
        if not handle:
            # Access denied means the process exists and is not ours; anything else
            # means the OS has no such process.
            return ctypes.get_last_error() == _ERROR_ACCESS_DENIED
        try:
            # WaitForSingleObject is unambiguous where an exit code is not: a process
            # may legitimately exit with 259, which is also STILL_ACTIVE.
            return _k32.WaitForSingleObject(handle, 0) == _WAIT_TIMEOUT
        finally:
            _k32.CloseHandle(handle)

    # A detached worker is still this process's child until someone reaps it, and an
    # unreaped zombie answers `kill(pid, 0)` as though it were running. Reaping it here
    # costs nothing and makes the answer below immediate rather than heartbeat-slow.
    try:
        reaped, _ = os.waitpid(pid, os.WNOHANG)
        if reaped == pid:
            return False
    except OSError:
        pass  # not our child, which is the usual case across sessions
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def kill_tree(pid: int | None, *, grace_s: float = 2.0) -> bool:
    """End `pid` and everything it started. Returns whether anything was signalled.

    The descendants are the point: a worker driving Blender that is killed on its own
    leaves the renderer running, which is the leak §1 calls collectable.
    """
    if not alive(pid):
        return False
    if WINDOWS:  # pragma: no cover - platform-specific
        return _kill_tree_windows(pid)

    # The worker was spawned into its own session, so its process group id is its pid
    # and the group is exactly the tree.
    for sig, grace in ((signal.SIGTERM, grace_s), (signal.SIGKILL, 0.0)):
        _signal_group(pid, sig)
        if wait_gone(pid, grace):
            return True
    return True


def _signal_group(pid: int, sig: int) -> None:
    try:
        os.killpg(pid, sig)
    except OSError:
        with contextlib.suppress(OSError):
            os.kill(pid, sig)


def _kill_tree_windows(pid: int) -> bool:  # pragma: no cover - platform-specific
    try:
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(pid)],
            capture_output=True,
            check=False,
        )
    except OSError:
        # No taskkill on PATH, so the tree cannot be walked from here and only the
        # worker itself goes.
        handle = _k32.OpenProcess(_PROCESS_TERMINATE, False, pid)
        if handle:
            _k32.TerminateProcess(handle, 1)
            _k32.CloseHandle(handle)
    return True


def wait_gone(pid: int | None, timeout_s: float = 5.0) -> bool:
    """Block until `pid` has exited, or until `timeout_s` runs out."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if not alive(pid):
            return True
        time.sleep(0.02)
    return not alive(pid)


def spawn_detached(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    log_path: Path,
) -> int:
    """Start `argv` so that it outlives this session, and return its pid.

    Detaching is what makes the handle worth having: a session that ends mid-render has
    not cancelled the render, and the next session can still be told what happened.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    # Closed in the `finally` below, once the child has inherited it.
    handle = open(log_path, "wb")  # noqa: SIM115
    try:
        kwargs: dict = {
            "cwd": str(cwd),
            "env": env,
            "stdin": subprocess.DEVNULL,
            "stdout": handle,
            "stderr": subprocess.STDOUT,
            "close_fds": True,
        }
        if WINDOWS:  # pragma: no cover - platform-specific
            kwargs["creationflags"] = (
                subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            # Its own session, so `kill_tree` can take the whole group at once.
            kwargs["start_new_session"] = True
        return subprocess.Popen(argv, **kwargs).pid
    finally:
        handle.close()
