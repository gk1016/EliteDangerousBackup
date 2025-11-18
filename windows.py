import ctypes
import os
import sys
from ctypes import wintypes

# DPI
def enable_high_dpi():
    if sys.platform != "win32":
        return
    try:
        user32 = ctypes.windll.user32
        DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)
        if hasattr(user32, "SetProcessDpiAwarenessContext"):
            if user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2):
                return
    except Exception:
        pass
    try:
        shcore = getattr(ctypes.windll, "shcore", None)
        if shcore and hasattr(shcore, "SetProcessDpiAwareness"):
            shcore.SetProcessDpiAwareness(2)
            return
    except Exception:
        pass
    try:
        user32 = ctypes.windll.user32
        if hasattr(user32, "SetProcessDPIAware"):
            user32.SetProcessDPIAware()
    except Exception:
        pass

# Drives
DRIVE_REMOVABLE = 2
if sys.platform == "win32":
    GetLogicalDrives = ctypes.windll.kernel32.GetLogicalDrives
    GetDriveTypeW = ctypes.windll.kernel32.GetDriveTypeW
    GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
    GetDriveTypeW.restype = wintypes.UINT

def list_drives():
    if sys.platform != "win32":
        return []
    drives = []
    bitmask = GetLogicalDrives()
    for i in range(26):
        if bitmask & (1 << i):
            letter = f"{chr(ord('A') + i)}:\\"
            dtype = GetDriveTypeW(letter)
            drives.append((letter, dtype))
    return drives

def list_removable_drives():
    if sys.platform != "win32":
        return []
    return [d for d, t in list_drives() if t == DRIVE_REMOVABLE]

# Long path helper
def win_longpath(p: str) -> str:
    if sys.platform != "win32":
        return p
    if p.startswith("\\\\?\\") or p.startswith("\\\\"):
        return p
    if len(p) >= 240:
        return "\\\\?\\" + os.path.abspath(p)
    return p
