# MAA Task Bar Hero

"""
Single-instance guard: a named Windows mutex held for the life of the process.
Windows releases it when the process ends, even after a crash, so a lock is
never left behind.
"""

import ctypes
import os
from ctypes import wintypes

# One GUI window and one bot at a time. Two GUIs fight over the emergency stop
# hotkey; two bots fight over the mouse.
GUI_LOCK_NAME = "Local\\MAA-Task-Bar-Hero-GUI"
BOT_LOCK_NAME = "Local\\MAA-Task-Bar-Hero-Bot"
ERROR_ALREADY_EXISTS = 183

_held_locks = {}


def acquire_instance_lock(name):
    """
    Take the named lock for this process. Returns False when another process
    already holds it, and True when it is taken (or cannot be checked, so the
    app is never blocked by the guard itself).
    """
    if os.name != "nt":
        return True

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    ctypes.set_last_error(0)
    handle = kernel32.CreateMutexW(None, False, name)

    if not handle:
        return True

    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return False

    _held_locks[name] = handle
    return True
