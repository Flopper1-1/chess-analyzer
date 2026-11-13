"""GitHub release auto-updater for Holly's Chess Analyzer (stable releases only)."""
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from typing import Callable, Optional, Tuple

APP_VERSION = "v1.10.0-beta.4"
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
    timeout: float = 30.0,
) -> str:
    """Download the release asset to dest_path, invoking progress_cb(downloaded, total)."""
    req = urllib.request.Request(
        download_url,
        headers={"User-Agent": f"HollysChessAnalyzer/{APP_VERSION.lstrip('v')}"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        downloaded = 0
        chunk_size = 65536
        with open(dest_path, "wb") as out:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                out.write(chunk)
                downloaded += len(chunk)
                if progress_cb:
                    progress_cb(downloaded, total)
    return dest_path


def apply_windows_exe_update(downloaded_exe: str, target_exe: Optional[str] = None) -> bool:
    """Launch a background batch script on Windows to replace the running .exe and restart it."""
    if sys.platform != "win32":
        return False
    target = target_exe or (sys.executable if getattr(sys, "frozen", False) else None)
    if not target or not os.path.exists(downloaded_exe):
        return False

    pid = os.getpid()
    bat_fd, bat_path = tempfile.mkstemp(suffix=".bat", prefix="hca_update_")
    os.close(bat_fd)
    # Note: use `ping` instead of `timeout` because `timeout` fails immediately under
    # CREATE_NO_WINDOW / DETACHED_PROCESS when stdin is redirected. Also retry `copy /Y`
    # so PyInstaller's outer onefile bootloader has time to release the target .exe lock.
    script = (
        "@echo off\r\n"
        "set /a tries=0\r\n"
        ":waitloop\r\n"
        f'tasklist /FI "PID eq {pid}" /NH 2>NUL | findstr /R "\\<{pid}\\>" >NUL\r\n'
        'if "%ERRORLEVEL%"=="0" (\r\n'
        "    set /a tries+=1\r\n"
        "    if %tries% GEQ 40 goto replaceloop\r\n"
        "    ping -n 2 127.0.0.1 >NUL\r\n"
        "    goto waitloop\r\n"
        ")\r\n"
        ":replaceloop\r\n"
        "set /a r=0\r\n"
        ":trycopy\r\n"
        "ping -n 2 127.0.0.1 >NUL\r\n"
        f'copy /Y "{downloaded_exe}" "{target}" >NUL 2>&1\r\n'
        'if "%ERRORLEVEL%"=="0" goto copied\r\n'
        "set /a r+=1\r\n"
        "if %r% LSS 25 goto trycopy\r\n"
        "goto cleanup\r\n"
        ":copied\r\n"
        f'del /F /Q "{downloaded_exe}" >NUL 2>&1\r\n'
        f'start "" "{target}"\r\n'
        ":cleanup\r\n"
        'del /F /Q "%~f0" >NUL 2>&1\r\n'
    )
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(script)

    subprocess.Popen(
        ["cmd.exe", "/c", bat_path],
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
        close_fds=True,
    )
    return True
