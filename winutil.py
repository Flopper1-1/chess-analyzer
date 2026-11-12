"""Windows helpers: keep analysis at full speed, update exe icon resources."""
import ctypes
import os
import shutil
import struct
import subprocess
import sys
import tempfile

_k32 = ctypes.windll.kernel32 if sys.platform == "win32" else None
_shell32 = ctypes.windll.shell32 if sys.platform == "win32" else None


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


def notify_shell_icon_change():
    """Ask Windows Explorer / taskbar to refresh cached executable icons."""
    if _shell32 is None:
        return
    try:
        _shell32.SHChangeNotify(0x08000000, 0x0000, None, None)  # SHCNE_ASSOCCHANGED | SHCNF_IDLIST
    except Exception:
        pass


def _read_pe_overlay(exe_path: str) -> bytes:
    """Return any trailing overlay bytes (e.g. PyInstaller PKG archive) after the last PE section."""
    with open(exe_path, "rb") as f:
        data = f.read()
    if len(data) < 0x40 or data[:2] != b"MZ":
        return b""
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if e_lfanew + 24 > len(data) or data[e_lfanew:e_lfanew + 4] != b"PE\x00\x00":
        return b""
    num_sections = struct.unpack_from("<H", data, e_lfanew + 6)[0]
    opt_hdr_size = struct.unpack_from("<H", data, e_lfanew + 20)[0]
    sec_table = e_lfanew + 24 + opt_hdr_size
    if sec_table + num_sections * 40 > len(data):
        return b""
    pe_end = 0
    for i in range(num_sections):
        sec_off = sec_table + i * 40
        size_raw, ptr_raw = struct.unpack_from("<II", data, sec_off + 16)
        if size_raw > 0 and ptr_raw + size_raw > pe_end:
            pe_end = ptr_raw + size_raw
    if pe_end <= 0 or pe_end >= len(data):
        return b""
    return data[pe_end:]


def update_exe_icon(exe_path: str, ico_bytes: bytes) -> bool:
    """Replace the primary RT_GROUP_ICON (id=1) and RT_ICON resources in a Windows PE executable,
    preserving any PyInstaller PKG overlay appended after the PE sections."""
    if _k32 is None or not exe_path or not os.path.isfile(exe_path) or len(ico_bytes) < 22:
        return False
    try:
        overlay = _read_pe_overlay(exe_path)

        reserved, img_type, count = struct.unpack_from("<HHH", ico_bytes, 0)
        if reserved != 0 or img_type != 1 or count <= 0:
            return False
        entries = []
        offset = 6
        for idx in range(count):
            w, h, cc, res, planes, bpp, size, img_off = struct.unpack_from("<BBBBHHII", ico_bytes, offset)
            offset += 16
            payload = ico_bytes[img_off:img_off + size]
            if len(payload) != size:
                return False
            entries.append((w, h, cc, res, planes, bpp, size, idx + 1, payload))

        grp_data = bytearray(struct.pack("<HHH", 0, 1, count))
        for w, h, cc, res, planes, bpp, size, icon_id, _ in entries:
            grp_data.extend(struct.pack("<BBBBHHIH", w, h, cc, res, planes, bpp, size, icon_id))

        _k32.BeginUpdateResourceW.argtypes = [ctypes.c_wchar_p, ctypes.c_bool]
        _k32.BeginUpdateResourceW.restype = ctypes.c_void_p
        _k32.UpdateResourceW.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.c_ushort, ctypes.c_void_p, ctypes.c_ulong,
        ]
        _k32.UpdateResourceW.restype = ctypes.c_bool
        _k32.EndUpdateResourceW.argtypes = [ctypes.c_void_p, ctypes.c_bool]
        _k32.EndUpdateResourceW.restype = ctypes.c_bool

        h_upd = _k32.BeginUpdateResourceW(exe_path, False)
        if not h_upd:
            return False

        rt_icon = ctypes.c_void_p(3)
        rt_group_icon = ctypes.c_void_p(14)
        ok = True
        for _, _, _, _, _, _, _, icon_id, payload in entries:
            buf = ctypes.create_string_buffer(payload, len(payload))
            if not _k32.UpdateResourceW(h_upd, rt_icon, ctypes.c_void_p(icon_id), 0, buf, len(payload)):
                ok = False
                break
        if ok:
            gbuf = ctypes.create_string_buffer(bytes(grp_data), len(grp_data))
            if not _k32.UpdateResourceW(h_upd, rt_group_icon, ctypes.c_void_p(1), 0, gbuf, len(grp_data)):
                ok = False
        if not _k32.EndUpdateResourceW(h_upd, not ok):
            return False
        if ok and overlay:
            with open(exe_path, "ab") as f:
                f.write(overlay)
        return ok
    except Exception:
        return False


def apply_icon_to_running_exe(ico_bytes: bytes, target_exe: str = None) -> str:
    """Update the executable's embedded icon on disk.

    Returns 'updated' if replaced immediately, 'deferred' if staged for exit, or 'failed'.
    """
    if sys.platform != "win32" or not ico_bytes:
        return "failed"
    exe_path = target_exe or (sys.executable if getattr(sys, "frozen", False) else "")
    if not exe_path or not os.path.isfile(exe_path):
        return "failed"

    exe_dir = os.path.dirname(exe_path)
    orig_size = os.path.getsize(exe_path)
    staged = os.path.join(tempfile.gettempdir(), f"hca_icon_{os.getpid()}.exe")
    try:
        shutil.copyfile(exe_path, staged)
        if not update_exe_icon(staged, ico_bytes):
            return "failed"
        if os.path.getsize(staged) < int(orig_size * 0.9):
            return "failed"
    except Exception:
        return "failed"

    # Try immediate rename-and-swap (Windows allows renaming a running .exe in the same directory)
    new_in_dir = os.path.join(exe_dir, f".hca_new_{os.getpid()}.exe")
    old_in_dir = exe_path + ".old"
    moved_orig = False
    try:
        if os.path.exists(old_in_dir):
            try:
                os.remove(old_in_dir)
            except OSError:
                old_in_dir = os.path.join(exe_dir, f".hca_old_{os.getpid()}.exe")
        shutil.copyfile(staged, new_in_dir)
        os.replace(exe_path, old_in_dir)
        moved_orig = True
        os.replace(new_in_dir, exe_path)
        try:
            os.remove(staged)
        except OSError:
            pass
        notify_shell_icon_change()
        return "updated"
    except Exception:
        if moved_orig and not os.path.exists(exe_path) and os.path.exists(old_in_dir):
            try:
                os.replace(old_in_dir, exe_path)
            except OSError:
                pass
        try:
            if os.path.exists(new_in_dir):
                os.remove(new_in_dir)
        except OSError:
            pass

    # Fallback: replace on process exit via a detached batch script
    try:
        bat = os.path.join(tempfile.gettempdir(), f"hca_icon_swap_{os.getpid()}.bat")
        pid = os.getpid()
        with open(bat, "w", encoding="utf-8") as f:
            f.write(
                "@echo off\r\n"
                ":wait\r\n"
                f"tasklist /FI \"PID eq {pid}\" 2>NUL | find /I \"{pid}\" >NUL\r\n"
                "if not errorlevel 1 (\r\n"
                "  timeout /t 1 /nobreak >NUL\r\n"
                "  goto wait\r\n"
                ")\r\n"
                f"copy /y \"{staged}\" \"{exe_path}\" >NUL 2>&1\r\n"
                f"del /f /q \"{staged}\" >NUL 2>&1\r\n"
                "del \"%~f0\" >NUL 2>&1\r\n"
            )
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) | getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
        subprocess.Popen(["cmd", "/c", bat], creationflags=flags, close_fds=True)
        return "deferred"
    except Exception:
        return "failed"


def cleanup_old_exe_files(target_exe: str = None) -> None:
    """Remove leftover .old/.hca_old_* executable backups from previous icon swaps."""
    if sys.platform != "win32":
        return
    exe_path = target_exe or (sys.executable if getattr(sys, "frozen", False) else "")
    if not exe_path:
        return
    exe_dir = os.path.dirname(exe_path)
    base = os.path.basename(exe_path)
    try:
        for fn in os.listdir(exe_dir):
            if fn == base + ".old" or (fn.startswith(".hca_old_") and fn.endswith(".exe")):
                try:
                    os.remove(os.path.join(exe_dir, fn))
                except OSError:
                    pass
    except OSError:
        pass

