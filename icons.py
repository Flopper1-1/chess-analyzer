"""Annotation icon assets: bundled defaults + user overrides editable in Microsoft Paint."""
import os
import shutil
import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from openings import resource_path

# annotation key -> icon file stem
KEY_TO_STEM = {
    "!!": "brilliant", "!": "great_find", "+++": "best", "++": "excellent", "+": "good",
    "/": "book", "miss": "miss", "?!": "inaccuracy", "?": "incorrect", "??": "blunder",
    "forced": "forced", "alt": "alternative",
}
# (stem, label) in display order for the Settings dialog
ICON_LIST = [
    ("brilliant", "Brilliant  !!"), ("great_find", "Great  !"), ("best", "Best"),
    ("excellent", "Excellent"), ("good", "Good"), ("book", "Book"),
    ("miss", "Miss (missed win)"), ("inaccuracy", "Inaccuracy  ?!"), ("incorrect", "Mistake  ?"), ("blunder", "Blunder  ??"),
    ("forced", "Forced move"), ("alternative", "Best alternative"),
    ("checkmate_white", "Checkmate (white king)"), ("checkmate_black", "Checkmate (black king)"),
    ("draw_white", "Draw (white king)"), ("draw_black", "Draw (black king)"),
    ("resign_white", "Resigned (white)"), ("resign_black", "Resigned (black)"),
]

_cache = {}


def user_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "ChessAnalyzer", "icons")
    os.makedirs(d, exist_ok=True)
    return d


def default_path(stem):
    return resource_path(os.path.join("assets", "icons", stem + ".png"))


def user_path(stem):
    return os.path.join(user_dir(), stem + ".png")


def path_for(stem):
    up = user_path(stem)
    return up if os.path.exists(up) else default_path(stem)


def is_custom(stem):
    return os.path.exists(user_path(stem))


def ensure_user_copy(stem):
    """Copy the default into the user folder (if needed) so it can be edited; returns its path."""
    up = user_path(stem)
    if not os.path.exists(up):
        shutil.copyfile(default_path(stem), up)
    return up


def edit_in_paint(stem):
    path = ensure_user_copy(stem)
    try:
        subprocess.Popen(["mspaint", path])
    except Exception:
        os.startfile(path, "edit")
    return path


def reset(stem):
    try:
        os.remove(user_path(stem))
    except FileNotFoundError:
        pass
    _cache.clear()


def reset_all():
    for stem, _ in ICON_LIST:
        reset(stem)


def pixmap(stem, size):
    """Smoothly scaled pixmap (cached by file mtime and size)."""
    p = path_for(stem)
    try:
        mt = os.path.getmtime(p)
    except OSError:
        return None
    key = (p, mt, size)
    pm = _cache.get(key)
    if pm is None:
        src = QPixmap(p)
        if src.isNull():
            return None
        pm = src.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        _cache[key] = pm
    return pm


def pixmap_for_key(key, size):
    stem = KEY_TO_STEM.get(key, key)
    return pixmap(stem, size)

