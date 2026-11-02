"""Win-probability conversion and move classification."""
import math
import chess

PIECE_VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
MATE_CP = 1000


def cp_of(score):
    """chess.engine.PovScore (already from a POV) -> centipawns."""
    return score.score(mate_score=MATE_CP * 10) if score is not None else 0


def win_pct(cp):
    cp = max(-MATE_CP * 10, min(MATE_CP * 10, cp))
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)


def material(board, color):
    return sum(PIECE_VAL[p.piece_type] for p in board.piece_map().values() if p.color == color)


def is_sacrifice(board_before, move, threshold=2):
    """True if the mover gives up >= threshold pawns of material net after the best
    reply by the opponent (simple 1-ply capture search)."""
    color = board_before.turn
    b = board_before.copy()
    start = material(b, color) - material(b, not color)
    b.push(move)
    worst = start
    # opponent's best capture reply
    for reply in b.legal_moves:
        if b.is_capture(reply):
            b2 = b.copy()
            b2.push(reply)
            # allow our recapture (best of ours)
            best = material(b2, color) - material(b2, not color)
            for rec in b2.legal_moves:
                if b2.is_capture(rec):
                    b3 = b2.copy()
                    b3.push(rec)
                    best = max(best, material(b3, color) - material(b3, not color))
            worst = min(worst, best)
    # also the immediate state if no capture reply
    if not any(b.is_capture(m) for m in b.legal_moves):
        worst = min(worst, material(b, color) - material(b, not color))
    return start - worst >= threshold


def classify(loss, is_best, played_wp_after, best_wp, second_wp, sacrifice, wp_before, lenient=False):
    """Return a symbol. All win percentages are from the mover's point of view."""
    # Miss: a winning move was available (>=70% win chance) but the move played threw most of it away
    # without being an outright losing blunder.
    if loss > 5 and best_wp >= 70 and 30 <= played_wp_after < 60:
        return "miss"
    if loss > 20:
        return "??"
    if loss > 10:
        return "?"
    if loss > 5:
        return "?!"
    # good-or-better territory
    max_loss, min_after, max_before = (5, 35, 95) if lenient else (2, 45, 90)
    if sacrifice and loss <= max_loss and played_wp_after >= min_after and wp_before < max_before:
        return "!!"
    if is_best and second_wp is not None and best_wp - second_wp >= 15 and wp_before < 90:
        return "!"
    if is_best:
        return "+++"
    if loss <= 2:
        return "++"
    return "+"


SYMBOL_NAMES = {
    "??": "Blunder", "miss": "Miss", "?": "Mistake", "?!": "Inaccuracy", "+": "Good", "++": "Excellent",
    "+++": "Best", "!": "Great", "!!": "Brilliant", "/": "Book", "": "",
}
SYMBOL_COLORS = {
    "??": "#ca3431", "?": "#e58f2a", "?!": "#e6c619", "+": "#8fa86a", "++": "#6fa84d",
    "+++": "#4caf50", "!": "#5c8bb0", "!!": "#1baca6", "/": "#a58d6d",
}
