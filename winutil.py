"""Windows helpers: keep analysis at full speed while the window is in the background."""
import ctypes
import sys

_k32 = ctypes.windll.kernel32 if sys.platform == "win32" else None


class _PPT(ctypes.Structure):
    _fields_ = [("Version", ctypes.c_ulong), ("ControlMask", ctypes.c_ulong), ("StateMask", ctypes.c_ulong)]


def disable_throttle(pid=None):
    """Opt a process out of Windows' background/efficiency (EcoQoS) execution-speed throttling."""
    if _k32 is None:
        return False
    try:
        owned = False
        if pid is None:
            handle = _k32.GetCurrentProcess()
        else:
            handle = _k32.OpenProcess(0x0200, False, int(pid))   # PROCESS_SET_INFORMATION
            owned = True
            if not handle:
                return False
        st = _PPT(1, 0x1, 0x0)    # ControlMask=EXECUTION_SPEED, StateMask=0 -> throttling off
        ok = _k32.SetProcessInformation(handle, 4, ctypes.byref(st), ctypes.sizeof(st))
        if owned:
            _k32.CloseHandle(handle)
        return bool(ok)
    except Exception:
        return False


def keep_awake(on):
    """Stop the PC from sleeping while analysis runs (call from the GUI thread)."""
    if _k32 is None:
        return
    try:
        _k32.SetThreadExecutionState(0x80000000 | 0x00000001 if on else 0x80000000)
    except Exception:
        pass

