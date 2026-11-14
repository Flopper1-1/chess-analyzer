"""Customization & theme manager: app icons, holiday events, sound templates,
board templates, background themes, and piece templates.
"""
from datetime import datetime
import colorsys
import json
import math
import os
import random
import re
import shutil
import struct
from typing import Dict, List, Optional

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QColor, QImage, QPixmap

from openings import resource_path

HOLIDAY_IDS = ("halloween", "christmas", "new_year")

SOUND_EVENT_SLOTS = [
    ("Move", "Normal Move"),
    ("Capture", "Capture"),
    ("Castle", "Castling"),
    ("Check", "Check"),
    ("Checkmate", "Checkmate"),
    ("draw", "Draw"),
    ("Game_load", "Game Load"),
    ("brilliant", "Brilliant Move (!!) Event"),
]

ANNOTATION_SLOTS = [
    ("!!", "Brilliant (!!)"),
    ("!", "Great (!)"),
    ("+++", "Best"),
    ("++", "Excellent"),
    ("+", "Good"),
    ("/", "Book"),
    ("miss", "Miss"),
    ("?!", "Inaccuracy (?!)"),
    ("?", "Mistake (?)"),
    ("??", "Blunder (??)"),
    ("forced", "Forced Move"),
]

PIECE_SLOTS = [
    ("wK", "White King"),
    ("wQ", "White Queen"),
    ("wR", "White Rook"),
    ("wB", "White Bishop"),
    ("wN", "White Knight"),
    ("wP", "White Pawn"),
    ("bK", "Black King"),
    ("bQ", "Black Queen"),
    ("bR", "Black Rook"),
    ("bB", "Black Bishop"),
    ("bN", "Black Knight"),
    ("bP", "Black Pawn"),
]

BUILTIN_BOARDS = [
    {
        "id": "brown_tan",
        "name": "Brown & Tan",
        "light_hex": "#f0d9b5",
        "dark_hex": "#b58863",
        "light_img": "",
        "dark_img": "",
        "locked": True,
    },
    {
        "id": "black_white",
        "name": "Black & White",
        "light_hex": "#f0f0f0",
        "dark_hex": "#262626",
        "light_img": "",
        "dark_img": "",
        "locked": True,
    },
    {
        "id": "red_white",
        "name": "Red & White",
        "light_hex": "#f4f4f4",
        "dark_hex": "#b83a3a",
        "light_img": "",
        "dark_img": "",
        "locked": True,
    },
    {
        "id": "blue_white",
        "name": "Blue & White",
        "light_hex": "#eef3f8",
        "dark_hex": "#4b7399",
        "light_img": "",
        "dark_img": "",
        "locked": True,
    },
]

HOLIDAY_BOARDS = {
    "halloween": {
        "id": "halloween",
        "name": "Halloween (Orange & Black)",
        "light_hex": "#f28c28",
        "dark_hex": "#1c1c1c",
        "light_img": "",
        "dark_img": "",
        "locked": True,
        "holiday": True,
    },
    "christmas": {
        "id": "christmas",
        "name": "Christmas (Green & White)",
        "light_hex": "#ffffff",
        "dark_hex": "#1b7a3d",
        "light_img": "",
        "dark_img": "",
        "locked": True,
        "holiday": True,
    },
    "new_year": {
        "id": "new_year",
        "name": "New Year (Black & Random Light)",
        "light_hex": "#ffd54f",
        "dark_hex": "#181818",
        "light_img": "",
        "dark_img": "",
        "locked": True,
        "holiday": True,
        "random_light": True,
    },
}

BUILTIN_BACKGROUNDS = [
    {
        "id": "dark",
        "name": "Dark",
        "window_bg": "#2b2b2b",
        "panel_bg": "#1f1f1f",
        "button_bg": "#444444",
        "button_border": "#555555",
        "header_bg": "#333333",
        "text_fg": "#dddddd",
        "grid_fg": "#333333",
        "image_path": "",
        "locked": True,
    },
    {
        "id": "light",
        "name": "Light",
        "window_bg": "#f2f2f2",
        "panel_bg": "#ffffff",
        "button_bg": "#e0e0e0",
        "button_border": "#b8b8b8",
        "header_bg": "#e4e4e4",
        "text_fg": "#1e1e1e",
        "grid_fg": "#d0d0d0",
        "image_path": "",
        "locked": True,
    },
    {
        "id": "high_contrast",
        "name": "High Contrast",
        "window_bg": "#000000",
        "panel_bg": "#0a0a0a",
        "button_bg": "#111111",
        "button_border": "#ffff00",
        "header_bg": "#141414",
        "text_fg": "#ffffff",
        "grid_fg": "#00ffff",
        "image_path": "",
        "locked": True,
    },
    {
        "id": "aqua_blue",
        "name": "Aqua Blue",
        "window_bg": "#0d222e",
        "panel_bg": "#132f3f",
        "button_bg": "#1a465c",
        "button_border": "#26c6da",
        "header_bg": "#16394c",
        "text_fg": "#e4f7fa",
        "grid_fg": "#21536b",
        "image_path": "",
        "locked": True,
    },
]

HOLIDAY_BACKGROUNDS = {
    "halloween": {
        "id": "halloween",
        "name": "Halloween (Orange)",
        "window_bg": "#b54500",
        "panel_bg": "#963800",
        "button_bg": "#c9540a",
        "button_border": "#ffa347",
        "header_bg": "#8f3200",
        "text_fg": "#fff4e6",
        "grid_fg": "#c9540a",
        "accent_bg": "#ff8f1f",
        "image_path": "",
        "locked": True,
        "holiday": True,
    },
    "christmas": {
        "id": "christmas",
        "name": "Christmas (Red & Green Shift)",
        "window_bg": "#7c1414",
        "panel_bg": "#115928",
        "button_bg": "#941b1b",
        "button_border": "#22c55e",
        "header_bg": "#5e1010",
        "text_fg": "#ffffff",
        "grid_fg": "#1e6e36",
        "accent_bg": "#16a34a",
        "image_path": "",
        "locked": True,
        "holiday": True,
        "animated": "christmas_shift",
    },
    "new_year": {
        "id": "new_year",
        "name": "New Year's (Dark Fireworks)",
        "window_bg": "#0b0e17",
        "panel_bg": "#141827",
        "button_bg": "#1e2438",
        "button_border": "#334155",
        "header_bg": "#141827",
        "text_fg": "#eef2ff",
        "grid_fg": "#232b42",
        "accent_bg": "#fbbf24",
        "image_path": "",
        "locked": True,
        "holiday": True,
        "animated": "fireworks",
    },
}

_NEW_YEAR_LIGHT_CHOICES = [
    "#ffd54f", "#ff8a65", "#4dd0e1", "#aed581", "#ba68c8",
    "#f06292", "#64b5f6", "#fff176", "#81c784", "#ffb74d",
]


def data_root() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "ChessAnalyzer")
    os.makedirs(d, exist_ok=True)
    return d


def _slugify(name: str, fallback: str = "custom") -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (name or "").strip().lower()).strip("_")
    return s or fallback


def capitalize_asset_name(filename: str) -> str:
    """Turn a filename like 'fluent.png' or 'midnight_gold.png' into 'Fluent' / 'Midnight Gold'."""
    stem = os.path.splitext(os.path.basename(filename))[0]
    words = [w for w in re.split(r"[_\-\s]+", stem) if w]
    return " ".join(w.capitalize() for w in words) if words else stem.capitalize()


def active_holiday_event(now: Optional[datetime] = None, disabled: bool = False) -> Optional[str]:
    """Determine active holiday event using ONLY the local operating system clock."""
    if disabled:
        return None
    dt = now or datetime.now()
    if dt.month == 10:
        return "halloween"
    if dt.month == 12 and 1 <= dt.day <= 30:
        return "christmas"
    if (dt.month == 12 and dt.day == 31) or (dt.month == 1 and dt.day == 1):
        return "new_year"
    return None


def generate_new_years_palette(seed: Optional[int] = None) -> List[str]:
    """Generate 32 festive light-square hex colors for New Year boards (1 per light square)."""
    rng = random.Random(seed) if seed is not None else random.Random()
    return [rng.choice(_NEW_YEAR_LIGHT_CHOICES) for _ in range(32)]


# ---------------------------------------------------------------- App Icons
def crop_square_image(img: QImage, target_size: int = 256) -> QImage:
    """Trim uniform transparent margins if present, center-crop to 1:1 square, and scale."""
    if img.isNull():
        return QImage()
    if img.hasAlphaChannel():
        img = img.convertToFormat(QImage.Format_RGBA8888)
        w, h = img.width(), img.height()
        min_x, min_y, max_x, max_y = w, h, -1, -1
        for y in range(0, h, max(1, h // 128)):
            for x in range(0, w, max(1, w // 128)):
                if img.pixelColor(x, y).alpha() > 8:
                    if x < min_x:
                        min_x = x
                    if y < min_y:
                        min_y = y
                    if x > max_x:
                        max_x = x
                    if y > max_y:
                        max_y = y
        if max_x > min_x and max_y > min_y:
            pad_x = max(0, (max_x - min_x) // 40)
            pad_y = max(0, (max_y - min_y) // 40)
            x0 = max(0, min_x - pad_x)
            y0 = max(0, min_y - pad_y)
            x1 = min(w - 1, max_x + pad_x)
            y1 = min(h - 1, max_y + pad_y)
            if (x1 - x0 + 1) >= 16 and (y1 - y0 + 1) >= 16:
                img = img.copy(x0, y0, x1 - x0 + 1, y1 - y0 + 1)
    w, h = img.width(), img.height()
    side = min(w, h)
    x = (w - side) // 2
    y = (h - side) // 2
    sq = img.copy(x, y, side, side)
    return sq.scaled(target_size, target_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)


def custom_app_icons_dir() -> str:
    d = os.path.join(data_root(), "app_icons")
    os.makedirs(d, exist_ok=True)
    return d


def _bundled_app_icon_paths() -> Dict[str, str]:
    """Scan assets/ and assets/app_icons/ for bundled app icons."""
    found: Dict[str, str] = {}
    assets_dir = resource_path("assets")
    app_icons_dir = resource_path(os.path.join("assets", "app_icons"))
    for folder in (assets_dir, app_icons_dir):
        if not os.path.isdir(folder):
            continue
        for fname in sorted(os.listdir(folder)):
            low = fname.lower()
            if not low.endswith((".png", ".ico")):
                continue
            if folder == assets_dir and low in ("icon.png", "showcase.png", "showcase_preview.png"):
                continue
            stem = os.path.splitext(low)[0]
            if stem not in found:
                found[stem] = os.path.join(folder, fname)
    if "fluent" not in found:
        fallback = resource_path(os.path.join("assets", "icon.png"))
        if os.path.exists(fallback):
            found["fluent"] = fallback
    return found


def list_selectable_app_icons(
    disable_holidays: bool = False,
    now: Optional[datetime] = None,
) -> List[dict]:
    """Return user-selectable app icons, including the active holiday icon only during its event window."""
    out: List[dict] = []
    bundled = _bundled_app_icon_paths()
    # Put Fluent first as the default
    ordered_keys = ["fluent"] + sorted(k for k in bundled if k != "fluent" and k not in HOLIDAY_IDS)
    for k in ordered_keys:
        if k in bundled and k not in HOLIDAY_IDS:
            out.append({
                "id": k,
                "name": capitalize_asset_name(k),
                "path": bundled[k],
                "locked": True,
                "holiday": False,
            })

    holiday = active_holiday_event(now=now, disabled=disable_holidays)
    if holiday and holiday in bundled:
        out.append({
            "id": holiday,
            "name": capitalize_asset_name(holiday),
            "path": bundled[holiday],
            "locked": True,
            "holiday": True,
        })

    cdir = custom_app_icons_dir()
    for fname in sorted(os.listdir(cdir)):
        if fname.lower().endswith(".png"):
            stem = os.path.splitext(fname)[0]
            out.append({
                "id": f"custom:{stem}",
                "name": capitalize_asset_name(fname),
                "path": os.path.join(cdir, fname),
                "locked": False,
                "holiday": False,
            })
    return out


def add_custom_app_icon(source_path: str, display_name: str = "") -> Optional[dict]:
    img = QImage(source_path)
    if img.isNull():
        return None
    sq = crop_square_image(img, 256)
    if sq.isNull():
        return None
    base_name = display_name.strip() or os.path.splitext(os.path.basename(source_path))[0]
    slug = _slugify(base_name, "custom_icon")
    cdir = custom_app_icons_dir()
    dest = os.path.join(cdir, f"{slug}.png")
    idx = 2
    while os.path.exists(dest):
        dest = os.path.join(cdir, f"{slug}_{idx}.png")
        idx += 1
    if not sq.save(dest, "PNG"):
        return None
    final_stem = os.path.splitext(os.path.basename(dest))[0]
    return {
        "id": f"custom:{final_stem}",
        "name": capitalize_asset_name(final_stem),
        "path": dest,
        "locked": False,
    }


def delete_custom_app_icon(icon_id: str) -> bool:
    if not icon_id.startswith("custom:"):
        return False
    stem = icon_id.split(":", 1)[1]
    p = os.path.join(custom_app_icons_dir(), f"{stem}.png")
    if os.path.exists(p):
        os.remove(p)
        return True
    return False


def resolve_active_app_icon(
    selected_id: str = "fluent",
    disable_holidays: bool = False,
    now: Optional[datetime] = None,
) -> dict:
    """Resolve the active app icon; holiday icons are only selectable during their active window."""
    for item in list_selectable_app_icons(disable_holidays=disable_holidays, now=now):
        if item["id"] == selected_id:
            return dict(item)
    bundled = _bundled_app_icon_paths()
    fluent_path = bundled.get("fluent") or resource_path("icon.ico")
    return {"id": "fluent", "name": "Fluent", "path": fluent_path, "locked": True, "holiday": False}


def cropped_icon_pixmap(path: str, size: int = 64) -> QPixmap:
    if not path or not os.path.exists(path):
        return QPixmap()
    img = QImage(path)
    if img.isNull():
        return QPixmap()
    sq = crop_square_image(img, size)
    return QPixmap.fromImage(sq)


# ---------------------------------------------------------------- Sound Templates
def sound_templates_dir() -> str:
    d = os.path.join(data_root(), "sound_templates")
    os.makedirs(d, exist_ok=True)
    return d


def _builtin_sound_templates() -> List[dict]:
    orig_events = {}
    for key, _lbl in SOUND_EVENT_SLOTS:
        wav = resource_path(os.path.join("assets", "sounds", f"{key}.wav"))
        if os.path.exists(wav):
            orig_events[key] = wav
    leg_events = {}
    for key, _lbl in SOUND_EVENT_SLOTS:
        mp3 = resource_path(os.path.join("assets", "sounds", "legacy", f"{key}.mp3"))
        if os.path.exists(mp3):
            leg_events[key] = mp3
    return [
        {
            "id": "original",
            "name": "Original (Default)",
            "locked": True,
            "events": orig_events,
            "annotations": {},
        },
        {
            "id": "legacy",
            "name": "Legacy",
            "locked": True,
            "events": leg_events,
            "annotations": {},
        },
    ]


def list_sound_templates() -> List[dict]:
    out = _builtin_sound_templates()
    root = sound_templates_dir()
    for folder in sorted(os.listdir(root)):
        manifest = os.path.join(root, folder, "template.json")
        if os.path.isfile(manifest):
            try:
                with open(manifest, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["id"] = f"custom:{folder}"
                data["locked"] = False
                data.setdefault("events", {})
                data.setdefault("annotations", {})
                out.append(data)
            except Exception:
                pass
    return out


def get_sound_template(template_id: str) -> dict:
    for tpl in list_sound_templates():
        if tpl["id"] == template_id:
            return tpl
    return _builtin_sound_templates()[0]


def create_sound_template(name: str, copy_from_id: str = "original") -> dict:
    clean = (name or "").strip() or "Custom Sounds"
    slug = _slugify(clean, "sound_tpl")
    root = sound_templates_dir()
    folder = slug
    idx = 2
    while os.path.exists(os.path.join(root, folder)):
        folder = f"{slug}_{idx}"
        idx += 1
    tdir = os.path.join(root, folder)
    os.makedirs(tdir, exist_ok=True)
    src = get_sound_template(copy_from_id) if copy_from_id else {"events": {}, "annotations": {}}
    events = {}
    for k, p in (src.get("events") or {}).items():
        if p and os.path.exists(p):
            ext = os.path.splitext(p)[1] or ".wav"
            dest = os.path.join(tdir, f"evt_{k}{ext}")
            shutil.copyfile(p, dest)
            events[k] = dest
    anns = {}
    for k, p in (src.get("annotations") or {}).items():
        if p and os.path.exists(p):
            ext = os.path.splitext(p)[1] or ".wav"
            safe_k = _slugify(k, "ann")
            dest = os.path.join(tdir, f"ann_{safe_k}{ext}")
            shutil.copyfile(p, dest)
            anns[k] = dest
    data = {
        "id": f"custom:{folder}",
        "name": clean,
        "locked": False,
        "events": events,
        "annotations": anns,
    }
    with open(os.path.join(tdir, "template.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data


def _save_custom_sound_manifest(template_id: str, data: dict) -> None:
    folder = template_id.split(":", 1)[1]
    manifest = os.path.join(sound_templates_dir(), folder, "template.json")
    with open(manifest, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def set_sound_slot(template_id: str, category: str, slot_key: str, source_path: str) -> bool:
    """Replace or add a sound in a user-created template. Built-in templates cannot be edited."""
    if not template_id.startswith("custom:") or not os.path.exists(source_path):
        return False
    tpl = get_sound_template(template_id)
    if tpl.get("locked"):
        return False
    folder = template_id.split(":", 1)[1]
    tdir = os.path.join(sound_templates_dir(), folder)
    ext = os.path.splitext(source_path)[1].lower() or ".wav"
    prefix = "evt" if category == "events" else "ann"
    safe_k = re.sub(r"[^a-zA-Z0-9_]", lambda m: f"_{ord(m.group(0))}_", slot_key)
    dest = os.path.join(tdir, f"{prefix}_{safe_k}{ext}")
    shutil.copyfile(source_path, dest)
    tpl.setdefault(category, {})[slot_key] = dest
    _save_custom_sound_manifest(template_id, tpl)
    return True


def clear_sound_slot(template_id: str, category: str, slot_key: str) -> bool:
    """Remove a sound from a slot in a user-created template."""
    if not template_id.startswith("custom:"):
        return False
    tpl = get_sound_template(template_id)
    if tpl.get("locked"):
        return False
    mapping = tpl.get(category) or {}
    old_path = mapping.pop(slot_key, "")
    if old_path and os.path.exists(old_path):
        try:
            os.remove(old_path)
        except OSError:
            pass
    _save_custom_sound_manifest(template_id, tpl)
    return True


def delete_sound_template(template_id: str) -> bool:
    if not template_id.startswith("custom:"):
        return False
    folder = template_id.split(":", 1)[1]
    tdir = os.path.join(sound_templates_dir(), folder)
    if os.path.isdir(tdir):
        shutil.rmtree(tdir, ignore_errors=True)
        return True
    return False


# ---------------------------------------------------------------- Board Templates
def board_templates_dir() -> str:
    d = os.path.join(data_root(), "board_templates")
    os.makedirs(d, exist_ok=True)
    return d


def list_selectable_board_templates(
    disable_holidays: bool = False,
    now: Optional[datetime] = None,
) -> List[dict]:
    """Return user-selectable board templates, including the active holiday board only during its event window."""
    out = [dict(b) for b in BUILTIN_BOARDS]
    holiday = active_holiday_event(now=now, disabled=disable_holidays)
    if holiday and holiday in HOLIDAY_BOARDS:
        hb = dict(HOLIDAY_BOARDS[holiday])
        hb["holiday"] = True
        out.append(hb)
    root = board_templates_dir()
    for folder in sorted(os.listdir(root)):
        manifest = os.path.join(root, folder, "template.json")
        if os.path.isfile(manifest):
            try:
                with open(manifest, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["id"] = f"custom:{folder}"
                data["locked"] = False
                out.append(data)
            except Exception:
                pass
    return out


def resolve_active_board_template(
    selected_id: str = "brown_tan",
    disable_holidays: bool = False,
    now: Optional[datetime] = None,
) -> dict:
    """Resolve the active board template; holiday boards are only selectable during their active window."""
    for b in list_selectable_board_templates(disable_holidays=disable_holidays, now=now):
        if b["id"] == selected_id:
            return b
    return dict(BUILTIN_BOARDS[0])


def save_custom_board_template(
    name: str,
    light_hex: str = "#f0d9b5",
    dark_hex: str = "#b58863",
    light_png: str = "",
    dark_png: str = "",
    template_id: str = "",
) -> dict:
    clean = (name or "").strip() or "Custom Board"
    root = board_templates_dir()
    if template_id.startswith("custom:"):
        folder = template_id.split(":", 1)[1]
        tdir = os.path.join(root, folder)
        os.makedirs(tdir, exist_ok=True)
    else:
        slug = _slugify(clean, "board")
        folder = slug
        idx = 2
        while os.path.exists(os.path.join(root, folder)):
            folder = f"{slug}_{idx}"
            idx += 1
        tdir = os.path.join(root, folder)
        os.makedirs(tdir, exist_ok=True)

    l_img = ""
    if light_png and os.path.exists(light_png):
        dest_l = os.path.join(tdir, "white_tile.png")
        if os.path.abspath(light_png) != os.path.abspath(dest_l):
            shutil.copyfile(light_png, dest_l)
        l_img = dest_l

    d_img = ""
    if dark_png and os.path.exists(dark_png):
        dest_d = os.path.join(tdir, "black_tile.png")
        if os.path.abspath(dark_png) != os.path.abspath(dest_d):
            shutil.copyfile(dark_png, dest_d)
        d_img = dest_d

    data = {
        "id": f"custom:{folder}",
        "name": clean,
        "light_hex": light_hex if QColor(light_hex).isValid() else "#f0d9b5",
        "dark_hex": dark_hex if QColor(dark_hex).isValid() else "#b58863",
        "light_img": l_img,
        "dark_img": d_img,
        "locked": False,
    }
    with open(os.path.join(tdir, "template.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data


def delete_custom_board_template(template_id: str) -> bool:
    if not template_id.startswith("custom:"):
        return False
    folder = template_id.split(":", 1)[1]
    tdir = os.path.join(board_templates_dir(), folder)
    if os.path.isdir(tdir):
        shutil.rmtree(tdir, ignore_errors=True)
        return True
    return False


# ---------------------------------------------------------------- Backgrounds
def backgrounds_dir() -> str:
    d = os.path.join(data_root(), "backgrounds")
    os.makedirs(d, exist_ok=True)
    return d


def list_background_templates(disable_holidays: bool = False) -> List[dict]:
    out = [dict(b) for b in BUILTIN_BACKGROUNDS]
    if not disable_holidays:
        for hid in HOLIDAY_IDS:
            hb = HOLIDAY_BACKGROUNDS.get(hid)
            if hb:
                out.append(dict(hb))
    root = backgrounds_dir()
    for folder in sorted(os.listdir(root)):
        manifest = os.path.join(root, folder, "template.json")
        if os.path.isfile(manifest):
            try:
                with open(manifest, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["id"] = f"custom:{folder}"
                data["locked"] = False
                out.append(data)
            except Exception:
                pass
    return out


def get_background_template(bg_id: str, disable_holidays: bool = False) -> dict:
    for bg in list_background_templates(disable_holidays=disable_holidays):
        if bg["id"] == bg_id:
            return bg
    return dict(BUILTIN_BACKGROUNDS[0])


def create_custom_color_background(name: str, ui_color: str, accent_color: str = "") -> Optional[dict]:
    ui_hex = normalize_hex(ui_color)
    if not ui_hex:
        return None
    acc_hex = normalize_hex(accent_color)
    clean = (name or "").strip() or f"Custom {ui_hex}"
    slug = _slugify(clean, "bg_color")
    root = backgrounds_dir()
    folder = slug
    idx = 2
    while os.path.exists(os.path.join(root, folder)):
        folder = f"{slug}_{idx}"
        idx += 1
    bdir = os.path.join(root, folder)
    os.makedirs(bdir, exist_ok=True)
    pal = get_theme_palette({"id": "dark"}, ui_color=ui_hex, accent_color=acc_hex)
    data = {
        "id": f"custom:{folder}",
        "name": clean,
        "window_bg": pal["bg"],
        "panel_bg": pal["panel"],
        "button_bg": pal["btn_bg"],
        "button_border": pal["border"],
        "header_bg": pal["panel"],
        "text_fg": pal["fg"],
        "grid_fg": pal["border"],
        "ui_color": ui_hex,
        "accent_color": acc_hex or pal["accent"],
        "image_path": "",
        "locked": False,
    }
    with open(os.path.join(bdir, "template.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data


def create_custom_background(name: str, image_path: str) -> Optional[dict]:
    if not image_path or not os.path.exists(image_path):
        return None
    clean = (name or "").strip() or os.path.splitext(os.path.basename(image_path))[0]
    slug = _slugify(clean, "bg")
    root = backgrounds_dir()
    folder = slug
    idx = 2
    while os.path.exists(os.path.join(root, folder)):
        folder = f"{slug}_{idx}"
        idx += 1
    bdir = os.path.join(root, folder)
    os.makedirs(bdir, exist_ok=True)
    ext = os.path.splitext(image_path)[1].lower() or ".png"
    dest = os.path.join(bdir, f"background{ext}")
    shutil.copyfile(image_path, dest)
    data = {
        "id": f"custom:{folder}",
        "name": clean,
        "window_bg": "#1e1e1e",
        "panel_bg": "rgba(24,24,24,215)",
        "button_bg": "#3c3c3c",
        "button_border": "#555555",
        "header_bg": "#2b2b2b",
        "text_fg": "#eeeeee",
        "grid_fg": "#383838",
        "image_path": dest,
        "locked": False,
    }
    with open(os.path.join(bdir, "template.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data


def delete_custom_background(bg_id: str) -> bool:
    if not bg_id.startswith("custom:"):
        return False
    folder = bg_id.split(":", 1)[1]
    bdir = os.path.join(backgrounds_dir(), folder)
    if os.path.isdir(bdir):
        shutil.rmtree(bdir, ignore_errors=True)
        return True
    return False


# ---------------------------------------------------------------- Piece Templates
def piece_templates_dir() -> str:
    d = os.path.join(data_root(), "piece_templates")
    os.makedirs(d, exist_ok=True)
    return d


def list_piece_templates() -> List[dict]:
    out = [{"id": "default", "name": "Default", "locked": True, "pieces": {}}]
    root = piece_templates_dir()
    for folder in sorted(os.listdir(root)):
        manifest = os.path.join(root, folder, "template.json")
        if os.path.isfile(manifest):
            try:
                with open(manifest, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["id"] = f"custom:{folder}"
                data["locked"] = False
                data.setdefault("pieces", {})
                out.append(data)
            except Exception:
                pass
    return out


def get_piece_template(piece_id: str) -> dict:
    for tpl in list_piece_templates():
        if tpl["id"] == piece_id:
            return tpl
    return {"id": "default", "name": "Default", "locked": True, "pieces": {}}


def create_piece_template(name: str) -> dict:
    clean = (name or "").strip() or "Custom Pieces"
    slug = _slugify(clean, "pieces")
    root = piece_templates_dir()
    folder = slug
    idx = 2
    while os.path.exists(os.path.join(root, folder)):
        folder = f"{slug}_{idx}"
        idx += 1
    pdir = os.path.join(root, folder)
    os.makedirs(pdir, exist_ok=True)
    data = {"id": f"custom:{folder}", "name": clean, "locked": False, "pieces": {}}
    with open(os.path.join(pdir, "template.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data


def set_piece_slot(template_id: str, piece_key: str, source_path: str) -> bool:
    if not template_id.startswith("custom:") or not os.path.exists(source_path):
        return False
    tpl = get_piece_template(template_id)
    if tpl.get("locked"):
        return False
    folder = template_id.split(":", 1)[1]
    pdir = os.path.join(piece_templates_dir(), folder)
    dest = os.path.join(pdir, f"{piece_key}.png")
    img = QImage(source_path)
    if img.isNull():
        return False
    if not img.save(dest, "PNG"):
        return False
    tpl.setdefault("pieces", {})[piece_key] = dest
    with open(os.path.join(pdir, "template.json"), "w", encoding="utf-8") as f:
        json.dump(tpl, f, indent=2)
    return True


def clear_piece_slot(template_id: str, piece_key: str) -> bool:
    if not template_id.startswith("custom:"):
        return False
    tpl = get_piece_template(template_id)
    if tpl.get("locked"):
        return False
    folder = template_id.split(":", 1)[1]
    pdir = os.path.join(piece_templates_dir(), folder)
    old = (tpl.get("pieces") or {}).pop(piece_key, "")
    if old and os.path.exists(old):
        try:
            os.remove(old)
        except OSError:
            pass
    with open(os.path.join(pdir, "template.json"), "w", encoding="utf-8") as f:
        json.dump(tpl, f, indent=2)
    return True


def delete_piece_template(template_id: str) -> bool:
    if not template_id.startswith("custom:"):
        return False
    folder = template_id.split(":", 1)[1]
    pdir = os.path.join(piece_templates_dir(), folder)
    if os.path.isdir(pdir):
        shutil.rmtree(pdir, ignore_errors=True)
        return True
    return False


# ---------------------------------------------------------------- Annotation Templates
def annotation_templates_dir() -> str:
    d = os.path.join(data_root(), "annotation_templates")
    os.makedirs(d, exist_ok=True)
    return d


def _default_annotation_template() -> dict:
    return {
        "id": "default",
        "name": "Default",
        "locked": True,
        "mode": "icons",
        "icons": {},
        "styles": {},
    }


def list_annotation_templates() -> List[dict]:
    out = [_default_annotation_template()]
    root = annotation_templates_dir()
    for folder in sorted(os.listdir(root)):
        manifest = os.path.join(root, folder, "template.json")
        if os.path.isfile(manifest):
            try:
                with open(manifest, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["id"] = f"custom:{folder}"
                data["locked"] = False
                data.setdefault("mode", "icons")
                data.setdefault("icons", {})
                data.setdefault("styles", {})
                out.append(data)
            except Exception:
                pass
    return out


def get_annotation_template(tpl_id: str) -> dict:
    for tpl in list_annotation_templates():
        if tpl["id"] == tpl_id:
            return tpl
    return _default_annotation_template()


def _save_annotation_manifest(template_id: str, tpl: dict) -> None:
    folder = template_id.split(":", 1)[1]
    adir = os.path.join(annotation_templates_dir(), folder)
    os.makedirs(adir, exist_ok=True)
    with open(os.path.join(adir, "template.json"), "w", encoding="utf-8") as f:
        json.dump(tpl, f, indent=2)


def create_annotation_template(name: str) -> dict:
    clean = (name or "").strip() or "Custom Annotations"
    slug = _slugify(clean, "annotations")
    root = annotation_templates_dir()
    folder = slug
    idx = 2
    while os.path.exists(os.path.join(root, folder)):
        folder = f"{slug}_{idx}"
        idx += 1
    adir = os.path.join(root, folder)
    os.makedirs(adir, exist_ok=True)
    data = {
        "id": f"custom:{folder}",
        "name": clean,
        "locked": False,
        "mode": "icons",
        "icons": {},
        "styles": {},
    }
    _save_annotation_manifest(data["id"], data)
    return data


def ensure_annotation_icon_copy(template_id: str, stem: str, default_png_path: str) -> str:
    if not template_id.startswith("custom:"):
        return ""
    tpl = get_annotation_template(template_id)
    if tpl.get("locked"):
        return ""
    folder = template_id.split(":", 1)[1]
    adir = os.path.join(annotation_templates_dir(), folder)
    dest = os.path.join(adir, f"{stem}.png")
    if not os.path.exists(dest) and default_png_path and os.path.exists(default_png_path):
        shutil.copyfile(default_png_path, dest)
    tpl.setdefault("icons", {})[stem] = dest
    _save_annotation_manifest(template_id, tpl)
    return dest


def reset_annotation_icon_slot(template_id: str, stem: str) -> bool:
    if not template_id.startswith("custom:"):
        return False
    tpl = get_annotation_template(template_id)
    if tpl.get("locked"):
        return False
    old = (tpl.get("icons") or {}).pop(stem, "")
    if old and os.path.exists(old):
        try:
            os.remove(old)
        except OSError:
            pass
    _save_annotation_manifest(template_id, tpl)
    return True


def reset_all_annotation_icon_slots(template_id: str) -> bool:
    if not template_id.startswith("custom:"):
        return False
    tpl = get_annotation_template(template_id)
    if tpl.get("locked"):
        return False
    for path in list((tpl.get("icons") or {}).values()):
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
    tpl["icons"] = {}
    _save_annotation_manifest(template_id, tpl)
    return True


def update_annotation_template_styles(template_id: str, mode: str, styles_dict: dict) -> bool:
    if not template_id.startswith("custom:"):
        return False
    tpl = get_annotation_template(template_id)
    if tpl.get("locked"):
        return False
    tpl["mode"] = mode if mode in ("icons", "legacy") else "icons"
    tpl["styles"] = {k: [v[0], v[1]] for k, v in (styles_dict or {}).items()}
    _save_annotation_manifest(template_id, tpl)
    return True


def delete_annotation_template(template_id: str) -> bool:
    if not template_id.startswith("custom:"):
        return False
    folder = template_id.split(":", 1)[1]
    adir = os.path.join(annotation_templates_dir(), folder)
    if os.path.isdir(adir):
        shutil.rmtree(adir, ignore_errors=True)
        return True
    return False


# ---------------------------------------------------------------- Theme Palette & Stylesheet
def normalize_hex(color: str) -> str:
    """Validate and normalize a CSS hex color string to '#rrggbb', else ''."""
    s = (color or "").strip()
    if not s:
        return ""
    qc = QColor(s)
    if not qc.isValid():
        return ""
    return qc.name(QColor.HexRgb).lower()


def _hex_rgb(hex_color: str) -> tuple:
    qc = QColor(normalize_hex(hex_color) or "#1e1e1e")
    return qc.red(), qc.green(), qc.blue()


def relative_luminance(hex_color: str) -> float:
    """Compute WCAG relative luminance [0.0..1.0] for an opaque hex color."""
    r, g, b = _hex_rgb(hex_color)
    def _lin(c: int) -> float:
        x = c / 255.0
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast_fg(bg_hex: str) -> str:
    """Choose crisp black or white foreground text for a given background color."""
    return "#111827" if relative_luminance(bg_hex) > 0.26 else "#ffffff"


def shift_lightness(hex_color: str, delta: float) -> str:
    """Adjust HLS lightness of hex_color by delta cleanly."""
    r, g, b = _hex_rgb(hex_color)
    h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    l2 = max(0.0, min(1.0, l + delta))
    r2, g2, b2 = colorsys.hls_to_rgb(h, l2, s)
    return "#{:02x}{:02x}{:02x}".format(
        max(0, min(255, int(round(r2 * 255)))),
        max(0, min(255, int(round(g2 * 255)))),
        max(0, min(255, int(round(b2 * 255)))),
    )


def blend_hex(c1: str, c2: str, t: float) -> str:
    """Linearly interpolate between two hex colors at ratio t in [0.0, 1.0]."""
    ratio = max(0.0, min(1.0, float(t)))
    r1, g1, b1 = _hex_rgb(c1)
    r2, g2, b2 = _hex_rgb(c2)
    return "#{:02x}{:02x}{:02x}".format(
        int(round(r1 + (r2 - r1) * ratio)),
        int(round(g1 + (g2 - g1) * ratio)),
        int(round(b1 + (b2 - b1) * ratio)),
    )


def rgba_css(hex_color: str, alpha: int = 215) -> str:
    """Format hex_color as CSS 'rgba(r, g, b, a)'."""
    r, g, b = _hex_rgb(hex_color)
    a = max(0, min(255, int(alpha)))
    return f"rgba({r}, {g}, {b}, {a})"


def christmas_palette(phase: float = 0.0) -> dict:
    """Return a Christmas UI palette slowly shifting between crimson red and pine green."""
    w = 0.5 - 0.5 * math.cos(2.0 * math.pi * (phase % 1.0))
    w = w * w * (3.0 - 2.0 * w)
    if w <= 0.5:
        u = w * 2.0
        bg = blend_hex("#7c1414", "#6e4e10", u)
        accent = blend_hex("#16a34a", "#eab308", u)
        border = blend_hex("#f87171", "#fbbf24", u)
    else:
        u = (w - 0.5) * 2.0
        bg = blend_hex("#6e4e10", "#115928", u)
        accent = blend_hex("#eab308", "#dc2626", u)
        border = blend_hex("#fbbf24", "#4ade80", u)
    panel = shift_lightness(bg, -0.05)
    surface = shift_lightness(bg, -0.08)
    surface_alt = shift_lightness(bg, -0.02)
    btn_bg = shift_lightness(bg, 0.05)
    btn_hover = shift_lightness(bg, 0.13)
    fg = "#ffffff"
    return {
        "bg": bg,
        "panel": panel,
        "surface": surface,
        "surface_alt": surface_alt,
        "fg": fg,
        "muted": "#fde68a",
        "border": border,
        "accent": accent,
        "accent_fg": contrast_fg(accent),
        "btn_bg": btn_bg,
        "btn_hover": btn_hover,
        "btn_hover_fg": fg,
        "graph_bg": surface,
        "graph_fill": "#f8fafc",
        "graph_mid": accent,
        "bar_bg": panel,
        "bar_border": border,
        "bar_fg": fg,
    }


def apply_color_overrides(pal: dict, ui_color: str = "", accent_color: str = "") -> dict:
    """Derive a full cohesive palette when custom UI or accent colors are set."""
    p = dict(pal)
    ui_hex = normalize_hex(ui_color)
    acc_hex = normalize_hex(accent_color)
    if ui_hex:
        is_light = relative_luminance(ui_hex) > 0.42
        fg = "#111827" if is_light else "#f3f4f6"
        muted = "#4b5563" if is_light else "#cbd5e1"
        panel = shift_lightness(ui_hex, -0.05 if is_light else 0.05)
        surface = shift_lightness(ui_hex, 0.06 if is_light else 0.06)
        surface_alt = shift_lightness(ui_hex, -0.03 if is_light else 0.11)
        btn_bg = shift_lightness(ui_hex, 0.05 if is_light else 0.10)
        btn_hover = shift_lightness(ui_hex, -0.09 if is_light else 0.18)
        border = shift_lightness(ui_hex, -0.20 if is_light else 0.22)
        p.update({
            "bg": ui_hex,
            "panel": panel,
            "surface": surface,
            "surface_alt": surface_alt,
            "fg": fg,
            "muted": muted,
            "border": border,
            "btn_bg": btn_bg,
            "btn_hover": btn_hover,
            "btn_hover_fg": fg,
            "graph_bg": panel if is_light else surface,
            "graph_fill": "#ffffff" if is_light else "#e5e7eb",
            "bar_bg": panel,
            "bar_border": border,
            "bar_fg": fg,
        })
    if acc_hex:
        p["accent"] = acc_hex
        p["accent_fg"] = contrast_fg(acc_hex)
        p["graph_mid"] = acc_hex
    acc_lum = relative_luminance(p["accent"])
    p["accent_hover"] = shift_lightness(p["accent"], -0.08 if acc_lum > 0.4 else 0.09)
    return p


def get_theme_palette(bg: dict, ui_color: str = "", accent_color: str = "", phase: float = 0.0) -> dict:
    """Return UI palette tokens derived from a background template and optional color overrides."""
    bg_id = bg.get("id", "dark")
    if bg_id == "light":
        base = {
            "bg": "#f3f4f6",
            "panel": "#e5e7eb",
            "surface": "#ffffff",
            "surface_alt": "#f9fafb",
            "fg": "#111827",
            "muted": "#4b5563",
            "border": "#cbd5e1",
            "accent": "#2563eb",
            "accent_fg": "#ffffff",
            "btn_bg": "#ffffff",
            "btn_hover": "#e5e7eb",
            "btn_hover_fg": "#111827",
            "graph_bg": "#e5e7eb",
            "graph_fill": "#ffffff",
            "graph_mid": "#9ca3af",
            "bar_bg": "#e5e7eb",
            "bar_border": "#cbd5e1",
            "bar_fg": "#111827",
        }
    elif bg_id == "high_contrast":
        base = {
            "bg": "#000000",
            "panel": "#000000",
            "surface": "#0a0a0a",
            "surface_alt": "#141414",
            "fg": "#ffffff",
            "muted": "#ffff00",
            "border": "#ffffff",
            "accent": "#ffff00",
            "accent_fg": "#000000",
            "btn_bg": "#000000",
            "btn_hover": "#ffff00",
            "btn_hover_fg": "#000000",
            "graph_bg": "#000000",
            "graph_fill": "#ffffff",
            "graph_mid": "#ffff00",
            "bar_bg": "#000000",
            "bar_border": "#ffffff",
            "bar_fg": "#ffffff",
        }
    elif bg_id == "aqua_blue":
        base = {
            "bg": "#0b2230",
            "panel": "#102d3e",
            "surface": "#123447",
            "surface_alt": "#174057",
            "fg": "#e6f7ff",
            "muted": "#8be9fd",
            "border": "#26c6da",
            "accent": "#26c6da",
            "accent_fg": "#041620",
            "btn_bg": "#153d52",
            "btn_hover": "#1d526e",
            "btn_hover_fg": "#e6f7ff",
            "graph_bg": "#102d3e",
            "graph_fill": "#d8f3f8",
            "graph_mid": "#26c6da",
            "bar_bg": "#102d3e",
            "bar_border": "#26c6da",
            "bar_fg": "#e6f7ff",
        }
    elif bg_id == "halloween":
        base = {
            "bg": "#b54500",
            "panel": "#963800",
            "surface": "#853000",
            "surface_alt": "#9c3c02",
            "fg": "#fff4e6",
            "muted": "#ffd1a3",
            "border": "#ffa347",
            "accent": "#ff8f1f",
            "accent_fg": "#1a0900",
            "btn_bg": "#c9540a",
            "btn_hover": "#e86917",
            "btn_hover_fg": "#ffffff",
            "graph_bg": "#853000",
            "graph_fill": "#ffe8cc",
            "graph_mid": "#ff8f1f",
            "bar_bg": "#963800",
            "bar_border": "#ffa347",
            "bar_fg": "#fff4e6",
        }
    elif bg_id == "christmas":
        base = christmas_palette(phase)
    elif bg_id == "new_year":
        base = {
            "bg": "#0b0e17",
            "panel": "#141827",
            "surface": "#141827",
            "surface_alt": "#1c2236",
            "fg": "#eef2ff",
            "muted": "#94a3b8",
            "border": "#334155",
            "accent": "#fbbf24",
            "accent_fg": "#111827",
            "btn_bg": "#1e2438",
            "btn_hover": "#2c3552",
            "btn_hover_fg": "#ffffff",
            "graph_bg": "#111522",
            "graph_fill": "#e2e8f0",
            "graph_mid": "#fbbf24",
            "bar_bg": "#141827",
            "bar_border": "#334155",
            "bar_fg": "#eef2ff",
        }
    else:
        base = {
            "bg": "#1e1e1e",
            "panel": "#252526",
            "surface": "#252526",
            "surface_alt": "#2d2d30",
            "fg": "#e6e6e6",
            "muted": "#aaaaaa",
            "border": "#3f3f46",
            "accent": "#2b6cb0",
            "accent_fg": "#ffffff",
            "btn_bg": "#2d2d30",
            "btn_hover": "#3e3e42",
            "btn_hover_fg": "#e6e6e6",
            "graph_bg": "#262626",
            "graph_fill": "#d9d9d9",
            "graph_mid": "#777777",
            "bar_bg": "#232323",
            "bar_border": "#3a3a3a",
            "bar_fg": "#e6e6e6",
        }
    eff_ui = normalize_hex(ui_color) or normalize_hex(bg.get("ui_color", ""))
    eff_acc = normalize_hex(accent_color) or normalize_hex(bg.get("accent_color", ""))
    return apply_color_overrides(base, ui_color=eff_ui, accent_color=eff_acc)


def build_app_stylesheet(
    bg: dict,
    is_custom_image: bool = False,
    ui_color: str = "",
    accent_color: str = "",
    phase: float = 0.0,
) -> str:
    """Build a complete Qt stylesheet covering MainWindow, Dialogs, Tabs, and Inputs."""
    p = get_theme_palette(bg, ui_color=ui_color, accent_color=accent_color, phase=phase)
    animated_bg = bg.get("animated") or ""
    is_fireworks = animated_bg == "fireworks"
    main_bg = "transparent" if (is_custom_image or is_fireworks) else p["bg"]
    toolbar_bg = rgba_css(p["panel"], 165) if is_fireworks else p["panel"]
    pane_bg = rgba_css(p["surface"], 145) if is_fireworks else p["surface"]
    border_w = "2px" if bg.get("id") == "high_contrast" else "1px"
    return f"""
        QMainWindow {{
            background-color: {main_bg};
            color: {p['fg']};
        }}
        QDialog {{
            background-color: {p['bg']};
            color: {p['fg']};
        }}
        QWidget {{
            color: {p['fg']};
        }}
        QToolBar {{
            background-color: {toolbar_bg};
            border-bottom: {border_w} solid {p['border']};
            spacing: 4px;
            padding: 2px 4px;
        }}
        QToolButton, QPushButton {{
            background-color: {p['btn_bg']};
            color: {p['fg']};
            border: {border_w} solid {p['border']};
            border-radius: 4px;
            padding: 4px 10px;
        }}
        QToolButton:hover, QPushButton:hover {{
            background-color: {p['btn_hover']};
            color: {p['btn_hover_fg']};
            border-color: {p['accent']};
        }}
        QToolButton:pressed, QPushButton:pressed {{
            background-color: {p['accent']};
            color: {p['accent_fg']};
        }}
        QTabWidget::pane {{
            background-color: {p['surface']};
            border: {border_w} solid {p['border']};
            border-radius: 4px;
            padding: 4px;
        }}
        QTabBar::tab {{
            background-color: {p['panel']};
            color: {p['fg']};
            border: {border_w} solid {p['border']};
            border-bottom: none;
            padding: 6px 12px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }}
        QTabBar::tab:hover {{
            background-color: {p['btn_hover']};
            color: {p['btn_hover_fg']};
            border-color: {p['accent']};
        }}
        QTabBar::tab:selected {{
            background-color: {p['accent']};
            color: {p['accent_fg']};
            border-color: {p['accent']};
            font-weight: bold;
        }}
        QTabBar::tab:selected:hover {{
            background-color: {p['accent_hover']};
            color: {p['accent_fg']};
            border-color: {p['fg']};
        }}
        QGroupBox {{
            border: {border_w} solid {p['border']};
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 8px;
            color: {p['fg']};
            font-weight: bold;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 4px;
        }}
        QLabel {{
            color: {p['fg']};
            background: transparent;
        }}
        QCheckBox, QRadioButton {{
            color: {p['fg']};
            background: transparent;
            spacing: 6px;
        }}
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit {{
            background-color: {p['surface']};
            color: {p['fg']};
            border: {border_w} solid {p['border']};
            border-radius: 4px;
            padding: 4px 6px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {p['surface']};
            color: {p['fg']};
            selection-background-color: {p['accent']};
            selection-color: {p['accent_fg']};
        }}
        QTableWidget, QListWidget, QTreeWidget {{
            background-color: {pane_bg};
            color: {p['fg']};
            border: {border_w} solid {p['border']};
            gridline-color: {p['border']};
            alternate-background-color: {p['surface_alt']};
            outline: 0;
        }}
        QListWidget::item {{
            padding: 4px 6px;
            border-radius: 4px;
            border: 1px solid transparent;
        }}
        QListWidget::item:hover {{
            background-color: {p['surface_alt']};
            border: 1px solid {p['border']};
        }}
        QListWidget::item:selected, QListWidget::item:selected:active, QListWidget::item:selected:!active,
        QTableWidget::item:selected {{
            background-color: {p['accent']};
            color: {p['accent_fg']};
            border: 1px solid {p['accent']};
        }}
        QHeaderView::section {{
            background-color: {p['panel']};
            color: {p['fg']};
            border: {border_w} solid {p['border']};
            padding: 4px 6px;
        }}
        QScrollArea {{
            background-color: {p['surface']};
            border: {border_w} solid {p['border']};
        }}
        QScrollArea QWidget#qt_scrollarea_viewport,
        QScrollArea > QWidget > QWidget {{
            background-color: {p['surface']};
            color: {p['fg']};
        }}
    """


def image_to_ico_bytes(path: str) -> bytes:
    """Convert an image file into a multi-size PNG-in-ICO byte stream for Windows PE icon updates."""
    if not path or not os.path.exists(path):
        return b""
    img = QImage(path)
    if img.isNull():
        return b""
    sizes = (16, 24, 32, 48, 64, 128, 256)
    png_blobs = []
    for sz in sizes:
        sq = crop_square_image(img, sz).convertToFormat(QImage.Format_RGBA8888)
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.WriteOnly)
        ok = sq.save(buf, "PNG")
        buf.close()
        if ok and ba.size() > 0:
            png_blobs.append((sz, bytes(ba)))
    if not png_blobs:
        return b""
    count = len(png_blobs)
    header = bytearray(struct.pack("<HHH", 0, 1, count))
    offset = 6 + 16 * count
    payloads = bytearray()
    for sz, blob in png_blobs:
        dim = 0 if sz >= 256 else sz
        header.extend(struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(blob), offset))
        offset += len(blob)
        payloads.extend(blob)
    return bytes(header) + bytes(payloads)


def sync_holiday_event_state(settings, now: Optional[datetime] = None) -> bool:
    """Auto-select event templates when a holiday starts and restore prior templates when it ends."""
    disabled = bool(getattr(settings, "disable_holiday_events", False))
    cur = active_holiday_event(now=now, disabled=disabled)
    last = getattr(settings, "last_holiday_event", "") or ""
    changed = False

    if cur:
        if last != cur:
            cur_icon = getattr(settings, "app_icon", "fluent") or "fluent"
            cur_board = getattr(settings, "board_template", "brown_tan") or "brown_tan"
            cur_bg = getattr(settings, "background_template", "dark") or "dark"
            if cur_icon not in HOLIDAY_IDS:
                settings.pre_event_app_icon = cur_icon
            if cur_board not in HOLIDAY_IDS:
                settings.pre_event_board_template = cur_board
            if cur_bg not in HOLIDAY_IDS:
                settings.pre_event_background_template = cur_bg
            settings.app_icon = cur
            if cur in HOLIDAY_BOARDS:
                settings.board_template = cur
            if cur in HOLIDAY_BACKGROUNDS:
                settings.background_template = cur
            settings.last_holiday_event = cur
            changed = True
    else:
        cur_icon = getattr(settings, "app_icon", "fluent") or "fluent"
        cur_board = getattr(settings, "board_template", "brown_tan") or "brown_tan"
        cur_bg = getattr(settings, "background_template", "dark") or "dark"
        if last or disabled or cur_icon in HOLIDAY_IDS or cur_board in HOLIDAY_IDS:
            pre_icon = getattr(settings, "pre_event_app_icon", "fluent") or "fluent"
            pre_board = getattr(settings, "pre_event_board_template", "brown_tan") or "brown_tan"
            pre_bg = getattr(settings, "pre_event_background_template", "dark") or "dark"
            if cur_icon in HOLIDAY_IDS or last:
                settings.app_icon = pre_icon if pre_icon not in HOLIDAY_IDS else "fluent"
                changed = True
            if cur_board in HOLIDAY_IDS or last:
                settings.board_template = pre_board if pre_board not in HOLIDAY_IDS else "brown_tan"
                changed = True
            if (last or disabled) and cur_bg in HOLIDAY_IDS:
                settings.background_template = pre_bg if pre_bg not in HOLIDAY_IDS else "dark"
                changed = True
            if last:
                settings.last_holiday_event = ""
                changed = True
    return changed
