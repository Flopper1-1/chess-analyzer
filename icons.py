"""Annotation icon assets: bundled defaults + user overrides editable in Microsoft Paint."""
import os
import shutil
import subprocess
import sys

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap

from openings import resource_path

# annotation key -> icon file stem
KEY_TO_STEM = {
    "!!": "brilliant", "!": "great_find", "+++": "best", "++": "excellent", "+": "good",
    "/": "book", "miss": "incorrect", "?!": "inaccuracy", "?": "mistake", "??": "blunder",
    "forced": "forced", "alt": "alternative",
}
# (stem, label) in display order for the Settings dialog
ICON_LIST = [
    ("brilliant", "Brilliant  !!"), ("great_find", "Great  !"), ("best", "Best"),
    ("excellent", "Excellent"), ("good", "Good"), ("book", "Book"),
    ("incorrect", "Miss (missed win)"), ("inaccuracy", "Inaccuracy  ?!"), ("mistake", "Mistake  ?"), ("blunder", "Blunder  ??"),
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


def profile_avatar_path() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    folder = os.path.join(base, "ChessAnalyzer")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "profile_avatar.png")


def has_custom_profile_avatar(custom_path: str = "") -> bool:
    p = custom_path or profile_avatar_path()
    return os.path.exists(p)


def crop_to_square_pixmap(src: QPixmap, target_size: int = 256) -> QPixmap:
    """Center-crop any QPixmap to a 1:1 square and scale smoothly to target_size x target_size."""
    if src.isNull():
        return QPixmap()
    w, h = src.width(), src.height()
    side = min(w, h)
    x = (w - side) // 2
    y = (h - side) // 2
    sq = src.copy(x, y, side, side)
    return sq.scaled(target_size, target_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)


def save_profile_avatar(source_path: str, dest_path: str = "") -> bool:
    """Load an image from source_path, crop it to a 1:1 square, and save to profile_avatar.png."""
    src = QPixmap(source_path)
    if src.isNull():
        return False
    sq = crop_to_square_pixmap(src, 256)
    if sq.isNull():
        return False
    out = dest_path or profile_avatar_path()
    ok = sq.save(out, "PNG")
    _cache.clear()
    return bool(ok)


def reset_profile_avatar(dest_path: str = "") -> None:
    p = dest_path or profile_avatar_path()
    try:
        os.remove(p)
    except FileNotFoundError:
        pass
    _cache.clear()


def _default_profile_pixmap(size: int) -> QPixmap:
    """Render a uniform dark-themed square default profile picture (size x size)."""
    pm = QPixmap(size, size)
    pm.fill(QColor("#262626"))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    # Subtle square border
    p.setPen(QPen(QColor("#4a4a4a"), max(1, size // 24)))
    p.setBrush(QColor("#232323"))
    p.drawRect(0, 0, size - 1, size - 1)
    # Chess knight glyph in theme accent/neutral color
    f = QFont("Segoe UI Symbol", max(8, int(size * 0.56)))
    p.setFont(f)
    p.setPen(QColor("#26c6da"))
    p.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, "\u265e")
    p.end()
    return pm


def profile_pixmap(size: int = 32, custom_path: str = "") -> QPixmap:
    """Return a strictly square (size x size) QPixmap for the user's profile picture."""
    p = custom_path or profile_avatar_path()
    if os.path.exists(p):
        try:
            mt = os.path.getmtime(p)
            key = ("profile", p, mt, size)
            cached = _cache.get(key)
            if cached is not None:
                return cached
            src = QPixmap(p)
            if not src.isNull():
                sq = crop_to_square_pixmap(src, size)
                _cache[key] = sq
                return sq
        except OSError:
            pass
    key = ("profile_default", size)
    cached = _cache.get(key)
    if cached is None:
        cached = _default_profile_pixmap(size)
        _cache[key] = cached
    return cached


