"""GitHub release auto-updater for Holly's Chess Analyzer (stable releases only)."""
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from typing import Callable, Optional, Tuple

APP_VERSION = "v1.10.0-beta.11"
GITHUB_REPO = "Flopper1-1/chess-analyzer"
RELEASES_LATEST_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_LIST_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases"


def parse_version(tag: str) -> Tuple[int, ...]:
    """Parse a version tag like 'v1.9.0' into a comparable integer tuple (1, 9, 0)."""
    clean = (tag or "").strip().lstrip("vV")
    clean = clean.split("-")[0].split("+")[0]
    parts = re.findall(r"\d+", clean)
    if not parts:
        return (0,)
    return tuple(int(p) for p in parts)


def _version_sort_key(tag: str) -> Tuple[Tuple[int, ...], int, Tuple[int, ...]]:
    """Return a sortable key ((major, minor, patch, ...), is_stable, (pre_nums...))."""
    clean = (tag or "").strip().lstrip("vV")
    base, _, pre = clean.partition("-")
    base = base.split("+")[0]
    base_nums = tuple(int(p) for p in re.findall(r"\d+", base)) or (0,)
    if not pre:
        return (base_nums, 1, ())
    pre_nums = tuple(int(p) for p in re.findall(r"\d+", pre)) or (0,)
    return (base_nums, 0, pre_nums)


def is_newer_version(remote_tag: str, local_tag: str = APP_VERSION) -> bool:
    """Return True if remote_tag is strictly newer than local_tag (supports pre-release tags)."""
    rb, r_stab, rp = _version_sort_key(remote_tag)
    lb, l_stab, lp = _version_sort_key(local_tag)
    max_len = max(len(rb), len(lb))
    rb_pad = rb + (0,) * (max_len - len(rb))
    lb_pad = lb + (0,) * (max_len - len(lb))
    if rb_pad != lb_pad:
        return rb_pad > lb_pad
    if r_stab != l_stab:
        return r_stab > l_stab
    p_len = max(len(rp), len(lp))
    return (rp + (0,) * (p_len - len(rp))) > (lp + (0,) * (p_len - len(lp)))


def is_prerelease_version(tag: str = APP_VERSION) -> bool:
    """Return True if a version tag denotes a pre-release (e.g. 'v1.10.0-beta.1')."""
    return "-" in (tag or "").strip()


def select_latest_stable_release(data) -> Optional[dict]:
    """Select the newest non-prerelease, non-draft release from GitHub API data."""
    if isinstance(data, dict):
        candidates = [data]
    elif isinstance(data, list):
        candidates = [r for r in data if isinstance(r, dict)]
    else:
        return None

    stable = [
        r for r in candidates
        if not bool(r.get("prerelease", False))
        and not bool(r.get("draft", False))
        and (r.get("tag_name") or "").strip()
    ]
    if not stable:
        return None
    stable.sort(key=lambda r: _version_sort_key(r.get("tag_name", "")), reverse=True)
    return stable[0]


def select_latest_prerelease(data) -> Optional[dict]:
    """Select the newest non-draft pre-release from GitHub API data."""
    if isinstance(data, dict):
        candidates = [data]
    elif isinstance(data, list):
        candidates = [r for r in data if isinstance(r, dict)]
    else:
        return None

    pres = [
        r for r in candidates
        if bool(r.get("prerelease", False))
        and not bool(r.get("draft", False))
        and (r.get("tag_name") or "").strip()
    ]
    if not pres:
        return None
    pres.sort(key=lambda r: _version_sort_key(r.get("tag_name", "")), reverse=True)
    return pres[0]


def extract_release_info(release: dict, current_version: str = APP_VERSION) -> dict:
    """Build normalized update info dict from a GitHub release object."""
    tag = (release.get("tag_name") or "").strip()
    assets = release.get("assets") or []
    download_url = ""
    asset_name = ""
    for a in assets:
        name = (a.get("name") or "").strip()
        url = (a.get("browser_download_url") or "").strip()
        if name.lower().endswith(".exe") and url:
            download_url = url
            asset_name = name
            break
    if not download_url and assets:
        first = assets[0]
        download_url = (first.get("browser_download_url") or "").strip()
        asset_name = (first.get("name") or "").strip()

    return {
        "update_available": is_newer_version(tag, current_version),
        "current_version": current_version,
        "latest_version": tag,
        "name": (release.get("name") or tag).strip(),
        "body": (release.get("body") or "").strip(),
        "html_url": (release.get("html_url") or f"https://github.com/{GITHUB_REPO}/releases").strip(),
        "download_url": download_url,
        "asset_name": asset_name,
        "prerelease": bool(release.get("prerelease", False)),
    }


def _fetch_json(url: str, timeout: float = 8.0):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"HollysChessAnalyzer/{APP_VERSION.lstrip('v')}",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def check_for_updates(
    current_version: str = APP_VERSION,
    timeout: float = 8.0,
    include_prereleases: Optional[bool] = None,
) -> dict:
    """Check GitHub for the newest update (pre-releases included when running a pre-release)."""
    if include_prereleases is None:
        include_prereleases = is_prerelease_version(current_version)

    release = None
    if include_prereleases:
        all_data = _fetch_json(RELEASES_LIST_URL, timeout=timeout)
        pre_rel = select_latest_prerelease(all_data)
        stable_rel = select_latest_stable_release(all_data)
        if pre_rel and stable_rel:
            pre_tag = pre_rel.get("tag_name", "")
            st_tag = stable_rel.get("tag_name", "")
            release = pre_rel if _version_sort_key(pre_tag) >= _version_sort_key(st_tag) else stable_rel
        else:
            release = pre_rel or stable_rel
    else:
        try:
            latest_data = _fetch_json(RELEASES_LATEST_URL, timeout=timeout)
            release = select_latest_stable_release(latest_data)
        except Exception:
            release = None

        if release is None:
            all_data = _fetch_json(RELEASES_LIST_URL, timeout=timeout)
            release = select_latest_stable_release(all_data)

    if release is None:
        return {
            "update_available": False,
            "current_version": current_version,
            "latest_version": current_version,
            "name": current_version,
            "body": "",
            "html_url": f"https://github.com/{GITHUB_REPO}/releases",
            "download_url": "",
            "asset_name": "",
            "prerelease": False,
        }
    return extract_release_info(release, current_version=current_version)


def check_release_channels(current_version: str = APP_VERSION, timeout: float = 8.0) -> dict:
    """Return the newest stable release and newest pre-release (if any) from GitHub."""
    all_data = _fetch_json(RELEASES_LIST_URL, timeout=timeout)
    stable_rel = select_latest_stable_release(all_data)
    pre_rel = select_latest_prerelease(all_data)
    return {
        "current_version": current_version,
        "current_is_prerelease": is_prerelease_version(current_version),
        "stable": extract_release_info(stable_rel, current_version=current_version) if stable_rel else None,
        "prerelease": extract_release_info(pre_rel, current_version=current_version) if pre_rel else None,
    }


def download_update(
    download_url: str,
    dest_path: str,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    timeout: float = 45.0,
) -> str:
    """Download the release asset to dest_path, invoking progress_cb(downloaded, total)."""
    req = urllib.request.Request(
        download_url,
        headers={"User-Agent": f"HollysChessAnalyzer/{APP_VERSION.lstrip('v')}"},
    )
    part_path = f"{dest_path}.{os.getpid()}.part"
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            downloaded = 0
            chunk_size = 65536
            with open(part_path, "wb") as out:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    out.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb:
                        progress_cb(downloaded, total)
        if total > 0 and downloaded != total:
            raise IOError(f"Incomplete download: got {downloaded} of {total} bytes")
        if dest_path.lower().endswith(".exe"):
            with open(part_path, "rb") as f:
                if f.read(2) != b"MZ":
                    raise IOError("Downloaded file is not a valid Windows executable")
        os.replace(part_path, dest_path)
    except Exception:
        try:
            if os.path.exists(part_path):
                os.remove(part_path)
        except OSError:
            pass
        raise
    return dest_path


def _clean_relaunch_env() -> dict:
    """Return a copy of os.environ stripped of PyInstaller bootloader variables."""
    env = os.environ.copy()
    for key in (
        "_MEIPASS2",
        "_PYI_ARCHIVE_FILE",
        "_PYI_APPLICATION_HOME_DIR",
        "_PYI_PARENT_PROCESS_LEVEL",
        "_PYI_SPLASH_IPC",
        "TCL_LIBRARY",
        "TK_LIBRARY",
    ):
        env.pop(key, None)
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


def _wait_pids_for_update(target: str) -> list:
    """Return current PID plus PyInstaller outer bootloader PPID (if matching `target`)."""
    pid = os.getpid()
    pids = [pid]
    try:
        ppid = os.getppid()
        if ppid and ppid != pid:
            import winutil
            pimg = winutil.get_process_image_path(ppid)
            if pimg and os.path.normcase(os.path.abspath(pimg)) == os.path.normcase(os.path.abspath(target)):
                pids.append(ppid)
    except Exception:
        pass
    return pids


def apply_windows_exe_update(downloaded_exe: str, target_exe: Optional[str] = None) -> bool:
    """Launch a background batch script on Windows to replace the running .exe and restart it."""
    if sys.platform != "win32":
        return False
    target_raw = target_exe or (sys.executable if getattr(sys, "frozen", False) else None)
    if not target_raw or not downloaded_exe or not os.path.isfile(downloaded_exe):
        return False
    target = os.path.abspath(target_raw)
    downloaded = os.path.abspath(downloaded_exe)
    if target.lower().endswith(".exe"):
        try:
            with open(downloaded, "rb") as f:
                if f.read(2) != b"MZ":
                    return False
        except OSError:
            return False

    pid = os.getpid()
    wait_pids = _wait_pids_for_update(target)
    target_dir = os.path.dirname(target) or tempfile.gettempdir()
    staged = f"{target}.new.{pid}"
    backup = f"{target}.old.{pid}"

    bat_fd, bat_path = tempfile.mkstemp(suffix=".bat", prefix="hca_update_")
    os.close(bat_fd)

    lines = [
        "@echo off",
        "chcp 65001 >NUL",
    ]
    for wp in wait_pids:
        lines.extend([
            "set /a tries=0",
            f":wait_{wp}",
            f'tasklist /FI "PID eq {wp}" /FO CSV /NH 2>NUL | find ",""{wp}""," >NUL',
            f"if errorlevel 1 goto wait_done_{wp}",
            "set /a tries+=1",
            f"if %tries% GEQ 45 goto wait_done_{wp}",
            "ping -n 2 127.0.0.1 >NUL",
            f"goto wait_{wp}",
            f":wait_done_{wp}",
        ])

    lines.extend([
        "set /a r=0",
        ":tryreplace",
        f'copy /Y "{downloaded}" "{staged}" >NUL 2>&1',
        f'if not exist "{staged}" goto try_direct',
        f'del /F /Q "{backup}" >NUL 2>&1',
        f'if exist "{target}" move /Y "{target}" "{backup}" >NUL 2>&1',
        f'move /Y "{staged}" "{target}" >NUL 2>&1 && if exist "{target}" goto replaced',
        f'if not exist "{target}" if exist "{backup}" move /Y "{backup}" "{target}" >NUL 2>&1',
        f'del /F /Q "{staged}" >NUL 2>&1',
        ":try_direct",
        f'copy /Y "{downloaded}" "{target}" >NUL 2>&1 && if exist "{target}" goto replaced',
        "set /a r+=1",
        "if %r% LSS 60 ping -n 2 127.0.0.1 >NUL",
        "if %r% LSS 60 goto tryreplace",
        f'echo Failed to replace "{target}" with "{downloaded}" > "%TEMP%\\hca_update_error.log"',
        "goto cleanup",
        ":replaced",
        f'del /F /Q "{downloaded}" >NUL 2>&1',
        f'del /F /Q "{backup}" >NUL 2>&1',
        'set "_MEIPASS2="',
        'set "_PYI_ARCHIVE_FILE="',
        'set "_PYI_APPLICATION_HOME_DIR="',
        'set "_PYI_PARENT_PROCESS_LEVEL="',
        'set "_PYI_SPLASH_IPC="',
        'set "PYINSTALLER_RESET_ENVIRONMENT=1"',
        f'start "" /D "{target_dir}" "{target}"',
        ":cleanup",
        'del /F /Q "%~f0" >NUL 2>&1',
    ])
    script = "\r\n".join(lines) + "\r\n"
    with open(bat_path, "w", encoding="utf-8", newline="") as f:
        f.write(script)

    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
    subprocess.Popen(
        ["cmd.exe", "/c", bat_path],
        env=_clean_relaunch_env(),
        cwd=tempfile.gettempdir(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
        close_fds=True,
    )
    return True
