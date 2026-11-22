"""Move accuracy, piece-type accuracy, and rating estimation."""
from typing import Dict, List, Optional
import chess

import classify as C

PHASES = ("opening", "middlegame", "endgame")
PIECE_TYPES = (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN, chess.KING)
PIECE_LABELS = {
    chess.PAWN: "P",
    chess.KNIGHT: "N",
    chess.BISHOP: "B",
    chess.ROOK: "R",
    chess.QUEEN: "Q",
    chess.KING: "K",
}

# accuracy% -> estimated game rating
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

# Calibrated expected-points loss (%) -> raw per-move accuracy score (can go negative on major blunders)
_RAW_ACC_ANCHORS = [
    (0.0, 100.0),
    (2.0, 94.3),
    (5.0, 84.5),
    (10.0, 63.0),
    (15.0, 41.0),
    (20.0, 18.0),
    (30.0, -15.0),
    (45.0, -60.0),
    (100.0, -150.0),
]


def raw_move_accuracy(
    loss_pct: float,
    ep_before: Optional[float] = None,
    ep_after: Optional[float] = None,
    is_book: bool = False,
) -> float:
    """Compute raw per-move accuracy from expected-points loss (0..100).

    Book moves receive 100.0; already-decided winning positions apply an 80.0 floor.
    Severe blunders return a negative score so game-level averaging properly penalizes
    large mistakes before clamping the final mean to [0.0, 100.0].
    """
    if is_book:
        return 100.0
    loss = max(0.0, min(100.0, float(loss_pct)))
    score = _RAW_ACC_ANCHORS[-1][1]
    for (x0, y0), (x1, y1) in zip(_RAW_ACC_ANCHORS, _RAW_ACC_ANCHORS[1:]):
        if loss <= x1:
            t = (loss - x0) / max(1e-9, x1 - x0)
            score = y0 + (y1 - y0) * t
            break

    already_won = (ep_after is not None and ep_after >= 95.0) or (
        ep_before is not None and ep_before >= 95.0 and ep_after is not None and ep_after >= 85.0
    )
    if already_won:
        score = max(80.0, score)
    return float(score)


def move_accuracy(loss: float) -> float:
    """Clamped per-move accuracy percentage (0.0..100.0)."""
    return max(0.0, min(100.0, raw_move_accuracy(loss)))


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


def _mean_clamped(scores: List[float]) -> Optional[float]:
    if not scores:
        return None
    return max(0.0, min(100.0, sum(scores) / len(scores)))


def _result_piece_type(r) -> int:
    fen = getattr(r, "fen_before", "") or ""
    uci = getattr(r, "uci", "") or ""
    if fen and uci:
        try:
            b = chess.Board(fen)
            mv = chess.Move.from_uci(uci)
            pt = b.piece_type_at(mv.from_square)
            if pt is not None:
                return pt
        except Exception:
            pass
    san = (getattr(r, "san", "") or "").lstrip()
    if san.startswith("O-O"):
        return chess.KING
    if san.startswith("K"):
        return chess.KING
    if san.startswith("Q"):
        return chess.QUEEN
    if san.startswith("R"):
        return chess.ROOK
    if san.startswith("B"):
        return chess.BISHOP
    if san.startswith("N"):
        return chess.KNIGHT
    return chess.PAWN


def summarize(results, elo: int = 2000) -> Dict[bool, dict]:
    """-> {color: {'opening':acc|None, ..., 'overall':acc|None, 'rating':int|None, 'by_piece': {...}}}"""
    out = {}
    for color in (chess.WHITE, chess.BLACK):
        mine = [r for r in results if r.color == color and r.symbol != "forced"]
        done = [r for r in mine if r.analysed]
        d = {p: None for p in PHASES}
        d["overall"] = None
        d["rating"] = None
        d["by_piece"] = {PIECE_LABELS[pt]: None for pt in PIECE_TYPES}
        if mine and len(done) >= 0.8 * len(mine):
            scored = []
            for r in done:
                is_book = bool(getattr(r, "book", False) or getattr(r, "symbol", "") == "/")
                eb = getattr(r, "eval_before", None)
                ea = getattr(r, "eval_after", None)
                ep_before = None
                ep_after = None
                if eb is not None:
                    cp_b = eb if color == chess.WHITE else -eb
                    ep_before = C.expected_points_pct(cp_b, elo)
                if ea is not None:
                    cp_a = ea if color == chess.WHITE else -ea
                    ep_after = C.expected_points_pct(cp_a, elo)
                sc = raw_move_accuracy(r.loss, ep_before=ep_before, ep_after=ep_after, is_book=is_book)
                rpt = _result_piece_type(r)
                scored.append((r, sc, rpt))

            for p in PHASES:
                d[p] = _mean_clamped([sc for r, sc, _rpt in scored if r.phase == p])
            d["overall"] = _mean_clamped([sc for _r, sc, _rpt in scored])
            d["by_piece"] = {
                PIECE_LABELS[pt]: _mean_clamped([sc for _r, sc, rpt in scored if rpt == pt])
                for pt in PIECE_TYPES
            }
            if d["overall"] is not None:
                d["rating"] = rating_from_accuracy(d["overall"])
        out[color] = d
    return out
