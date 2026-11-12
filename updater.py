"""GitHub release auto-updater for Holly's Chess Analyzer (stable releases only)."""
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from typing import Callable, Optional, Tuple

APP_VERSION = "v1.10.0-beta.1"
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


def is_newer_version(remote_tag: str, local_tag: str = APP_VERSION) -> bool:
    """Return True if remote_tag is strictly newer than local_tag."""
    r = list(parse_version(remote_tag))
    l = list(parse_version(local_tag))
    max_len = max(len(r), len(l))
    r.extend([0] * (max_len - len(r)))
    l.extend([0] * (max_len - len(l)))
    return tuple(r) > tuple(l)


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
    stable.sort(key=lambda r: parse_version(r.get("tag_name", "")), reverse=True)
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
    pres.sort(key=lambda r: parse_version(r.get("tag_name", "")), reverse=True)
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


def check_for_updates(current_version: str = APP_VERSION, timeout: float = 8.0) -> dict:
    """Check GitHub for the newest non-prerelease release."""
    release = None
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
    script = (
        "@echo off\r\n"
        f":waitloop\r\n"
        f'tasklist /FI "PID eq {pid}" 2>NUL | find /I "{pid}" >NUL\r\n'
        f'if "%ERRORLEVEL%"=="0" (\r\n'
        f"    timeout /t 1 /nobreak >NUL\r\n"
        f"    goto waitloop\r\n"
        f")\r\n"
        f'move /Y "{downloaded_exe}" "{target}" >NUL\r\n'
        f'start "" "{target}"\r\n'
        f'del "%~f0"\r\n'
    )
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(script)

    subprocess.Popen(
        ["cmd.exe", "/c", bat_path],
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
        close_fds=True,
    )
    return True
