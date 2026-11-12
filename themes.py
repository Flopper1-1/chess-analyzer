"""Customization & theme manager: app icons, holiday events, sound templates,
board templates, background themes, and piece templates.
"""
from datetime import datetime
import json
import os
import random
import re
import shutil
from typing import Dict, List, Optional

from PySide6.QtCore import Qt
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
        "name": "Christmas (Red & Green)",
        "light_hex": "#3a8f4d",
        "dark_hex": "#b83232",
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


def list_background_templates() -> List[dict]:
    out = [dict(b) for b in BUILTIN_BACKGROUNDS]
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


def get_background_template(bg_id: str) -> dict:
    for bg in list_background_templates():
        if bg["id"] == bg_id:
            return bg
    return dict(BUILTIN_BACKGROUNDS[0])


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


# ---------------------------------------------------------------- Theme Palette & Stylesheet
def get_theme_palette(bg: dict) -> dict:
    """Return UI palette tokens derived from a background template."""
    bg_id = bg.get("id", "dark")
    if bg_id == "light":
        return {
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
            "graph_bg": "#e5e7eb",
            "graph_fill": "#ffffff",
            "graph_mid": "#9ca3af",
            "bar_bg": "#e5e7eb",
            "bar_border": "#cbd5e1",
            "bar_fg": "#111827",
        }
    if bg_id == "high_contrast":
        return {
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
            "btn_hover": "#222222",
            "graph_bg": "#000000",
            "graph_fill": "#ffffff",
            "graph_mid": "#ffff00",
            "bar_bg": "#000000",
            "bar_border": "#ffffff",
            "bar_fg": "#ffffff",
        }
    if bg_id == "aqua_blue":
        return {
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
            "graph_bg": "#102d3e",
            "graph_fill": "#d8f3f8",
            "graph_mid": "#26c6da",
            "bar_bg": "#102d3e",
            "bar_border": "#26c6da",
            "bar_fg": "#e6f7ff",
        }
    return {
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
        "graph_bg": "#262626",
        "graph_fill": "#d9d9d9",
        "graph_mid": "#777777",
        "bar_bg": "#232323",
        "bar_border": "#3a3a3a",
        "bar_fg": "#e6e6e6",
    }


def build_app_stylesheet(bg: dict, is_custom_image: bool = False) -> str:
    """Build a complete Qt stylesheet covering MainWindow, Dialogs, Tabs, and Inputs."""
    p = get_theme_palette(bg)
    main_bg = "transparent" if is_custom_image else p["bg"]
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
            background-color: {p['panel']};
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
        QTabBar::tab:selected {{
            background-color: {p['accent']};
            color: {p['accent_fg']};
            font-weight: bold;
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
            background-color: {p['surface']};
            color: {p['fg']};
            border: {border_w} solid {p['border']};
            gridline-color: {p['border']};
            alternate-background-color: {p['surface_alt']};
        }}
        QListWidget::item:selected, QTableWidget::item:selected {{
            background-color: {p['accent']};
            color: {p['accent_fg']};
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
    """
