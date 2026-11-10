"""Accuracy and rating estimation."""
import math
import chess

PHASES = ("opening", "middlegame", "endgame")

# accuracy% -> estimated game rating (calibrated to Chess.com Game Review scale)
_ANCHORS = [
    (0, 100),
    (40, 250),
    (50, 400),
    (60, 550),
    (68.0, 650),
    (70.7, 700),
    (71.4, 750),
    (75, 1100),
    (80, 1350),
    (85, 1550),
    (90, 1900),
    (93, 2200),
    (95, 2400),
    (98, 2800),
    (100, 3000),
]


def move_accuracy(loss):
    """Chess.com-calibrated move accuracy from win% lost (0-100)."""
    return max(0.0, min(100.0, 103.1668 * math.exp(-0.0735 * loss) - 3.1669))


def rating_from_accuracy(acc):
    for (a0, r0), (a1, r1) in zip(_ANCHORS, _ANCHORS[1:]):
        if acc <= a1:
            raw = r0 + (r1 - r0) * (acc - a0) / (a1 - a0)
            return int(round(raw / 50.0) * 50)
    return _ANCHORS[-1][1]


def phase_of(board_before, is_book):
    pieces = sum(1 for p in board_before.piece_map().values() if p.piece_type not in (chess.PAWN, chess.KING))
    if pieces <= 4 or (pieces <= 5 and board_before.fullmove_number > 20):
        return "endgame"
    if is_book or board_before.fullmove_number <= 8:
        return "opening"
    return "middlegame"


def _combine(accs):
    if not accs:
        return None
    mean = sum(accs) / len(accs)
    harm = len(accs) / sum(1.0 / max(a, 14.5) for a in accs)
    return (mean + harm) / 2


def summarize(results):
    """-> {color: {'opening':acc|None, ..., 'overall':acc|None, 'rating':int|None}}"""
    out = {}
    for color in (chess.WHITE, chess.BLACK):
        mine = [r for r in results if r.color == color and r.symbol != "forced"]
        done = [r for r in mine if r.analysed]
        d = {p: None for p in PHASES}
        d["overall"] = None
        d["rating"] = None
        if mine and len(done) >= 0.8 * len(mine):
            for p in PHASES:
                d[p] = _combine([move_accuracy(r.loss) for r in done if r.phase == p])
            d["overall"] = _combine([move_accuracy(r.loss) for r in done])
            if d["overall"] is not None:
                d["rating"] = rating_from_accuracy(d["overall"])
        out[color] = d
    return out
