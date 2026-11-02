"""Customizable annotation symbols and colours (persisted in QSettings as JSON)."""
import json

# key -> (name, default symbol, default colour)
DEFAULTS = {
    "!!": ("Brilliant", "!!", "#1baca6"),
    "!": ("Great", "!", "#5c8bb0"),
    "+++": ("Best", "★", "#4caf50"),
    "++": ("Excellent", "👍", "#6fa84d"),
    "+": ("Good", "✓", "#8fa86a"),
    "/": ("Book", "/", "#a58d6d"),
    "miss": ("Miss", "✗", "#ee6b6e"),
    "?!": ("Inaccuracy", "?!", "#e6c619"),
    "?": ("Mistake", "?", "#e58f2a"),
    "??": ("Blunder", "??", "#ca3431"),
    "forced": ("Forced", "→", "#7aa06a"),
    "alt": ("Best alternative", "↗", "#6ba36b"),
}

_current = {k: [v[1], v[2]] for k, v in DEFAULTS.items()}
mode = "icons"   # "icons" (image assets) or "legacy" (symbols + colours)


def load(qs):
    global mode
    mode = qs.value("anno_mode", "icons")
    if mode not in ("icons", "legacy"):
        mode = "icons"
    try:
        data = json.loads(qs.value("styles", "{}"))
    except Exception:
        data = {}
    for k, v in data.items():
        if k in _current and isinstance(v, list) and len(v) == 2:
            _current[k] = v


def save(qs):
    qs.setValue("anno_mode", mode)
    qs.setValue("styles", json.dumps(_current))


def get_all():
    return {k: tuple(v) for k, v in _current.items()}


def set_all(d):
    for k, v in d.items():
        if k in _current:
            _current[k] = [v[0], v[1]]


def reset():
    for k, v in DEFAULTS.items():
        _current[k] = [v[1], v[2]]


def symbol(key):
    return _current[key][0] if key in _current else key


def color(key):
    return _current[key][1] if key in _current else "#888888"


def name(key):
    return DEFAULTS[key][0] if key in DEFAULTS else ""

