"""Win-probability conversion and move classification."""
import math
import chess

PIECE_VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
PIECE_CATEGORY = {
    chess.QUEEN: "queen",
    chess.ROOK: "rook",
    chess.BISHOP: "bishop",
    chess.KNIGHT: "knight",
}
BRILLIANT_CATEGORIES = ("queen", "rook", "bishop", "knight", "underpromotion")
MATE_CP = 1000


def cp_of(score):
    """chess.engine.PovScore (already from a POV) -> centipawns."""
    return score.score(mate_score=MATE_CP * 10) if score is not None else 0


def win_pct(cp):
    cp = max(-MATE_CP * 10, min(MATE_CP * 10, cp))
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)


def material(board, color):
    return sum(PIECE_VAL[p.piece_type] for p in board.piece_map().values() if p.color == color)


def is_underpromotion(move: chess.Move) -> bool:
    """True if the move promotes a pawn to a Knight, Bishop, or Rook."""
    return move is not None and move.promotion in (chess.KNIGHT, chess.BISHOP, chess.ROOK)


def is_brilliant_underpromotion(board_before: chess.Board, move: chess.Move, is_best: bool = True,
                                loss: float = 0.0, max_loss: float = 2.0) -> bool:
    """True if an underpromotion avoids stalemate, delivers checkmate/check, or is the best move."""
    if not is_underpromotion(move) or loss > max_loss:
        return False
    b_after = board_before.copy()
    b_after.push(move)
    if b_after.is_checkmate():
        return True
    # Check what would happen if promoted to Queen instead
    queen_move = chess.Move(move.from_square, move.to_square, promotion=chess.QUEEN)
    if queen_move in board_before.legal_moves:
        b_queen = board_before.copy()
        b_queen.push(queen_move)
        if b_queen.is_stalemate() or b_queen.is_insufficient_material():
            return True
    if is_best or b_after.is_check():
        return True
    return False


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


def brilliant_category(board_before: chess.Board, move: chess.Move) -> str:
    """Determine the specific type of Brilliant (!!) move:
    'underpromotion', 'queen', 'rook', 'bishop', or 'knight'."""
    if is_underpromotion(move):
        return "underpromotion"

    color = board_before.turn
    moved_piece = board_before.piece_at(move.from_square)
    b = board_before.copy()
    start = material(b, color) - material(b, not color)
    b.push(move)

    worst_net = start
    sacrificed_pt = None

    for reply in b.legal_moves:
        if b.is_capture(reply):
            victim = b.piece_at(reply.to_square)
            b2 = b.copy()
            b2.push(reply)
            best = material(b2, color) - material(b2, not color)
            for rec in b2.legal_moves:
                if b2.is_capture(rec):
                    b3 = b2.copy()
                    b3.push(rec)
                    best = max(best, material(b3, color) - material(b3, not color))
            if best < worst_net and victim is not None and victim.color == color:
                worst_net = best
                sacrificed_pt = victim.piece_type
            elif best == worst_net and victim is not None and victim.color == color:
                if sacrificed_pt is None or PIECE_VAL.get(victim.piece_type, 0) > PIECE_VAL.get(sacrificed_pt, 0):
                    sacrificed_pt = victim.piece_type

    if sacrificed_pt in PIECE_CATEGORY:
        return PIECE_CATEGORY[sacrificed_pt]

    # Check if any of mover's major/minor pieces is left attacked on the board
    hanging_candidates = []
    for sq, pc in b.piece_map().items():
        if pc.color == color and pc.piece_type in PIECE_CATEGORY:
            if b.is_attacked_by(not color, sq):
                hanging_candidates.append(pc.piece_type)
    if hanging_candidates:
        hanging_candidates.sort(key=lambda pt: PIECE_VAL.get(pt, 0), reverse=True)
        return PIECE_CATEGORY[hanging_candidates[0]]

    if moved_piece and moved_piece.piece_type in PIECE_CATEGORY:
        return PIECE_CATEGORY[moved_piece.piece_type]

    return "knight"


def is_deadlocked_position(board: chess.Board, pv=None) -> bool:
    """Return True when neither player can make progress without committing a bad move
    (e.g., PV repeats/shuffles, locked pawn fortress with no safe break, or draw state)."""
    if board is None:
        return False
    if board.is_checkmate():
        return False
    if (
        board.is_stalemate()
        or board.is_insufficient_material()
        or board.is_fifty_moves()
        or board.is_repetition(2)
        or board.halfmove_clock >= 20
    ):
        return True

    # Normalize pv into a list of chess.Move
    pv_moves = []
    if pv:
        sim_parse = board.copy()
        for item in pv:
            try:
                mv = chess.Move.from_uci(item) if isinstance(item, str) else item
                if mv in sim_parse.legal_moves:
                    pv_moves.append(mv)
                    sim_parse.push(mv)
                else:
                    break
            except Exception:
                break

    # Check if the engine's best line (PV) repeats positions or shuffles pieces back and forth
    if pv_moves:
        sim = board.copy()
        seen_fens = {sim.board_fen()}
        quiet_streak = 0
        origin_squares = {chess.WHITE: set(), chess.BLACK: set()}
        returned_to_origin = {chess.WHITE: False, chess.BLACK: False}
        for mv in pv_moves:
            mover = sim.turn
            is_cap = sim.is_capture(mv)
            is_pawn = sim.piece_type_at(mv.from_square) == chess.PAWN
            if not is_cap and not is_pawn and not mv.promotion:
                quiet_streak += 1
                if mv.to_square in origin_squares[mover]:
                    returned_to_origin[mover] = True
                origin_squares[mover].add(mv.from_square)
            else:
                quiet_streak = 0
            sim.push(mv)
            if sim.is_checkmate():
                return False
            if sim.is_stalemate() or sim.is_insufficient_material() or sim.is_repetition(2):
                return True
            bfen = sim.board_fen()
            if bfen in seen_fens:
                return True
            seen_fens.add(bfen)
        # If the top engine line makes 6+ quiet non-pawn moves and shuffles pieces back
        if len(pv_moves) >= 6 and quiet_streak >= len(pv_moves) and (
            returned_to_origin[chess.WHITE] or returned_to_origin[chess.BLACK]
        ):
            return True

    # Check for locked pawn structure / fortress where neither side has a safe pawn advance or winning capture
    if not board.is_check() and board.pawns:
        any_safe_progress = False
        for side in (chess.WHITE, chess.BLACK):
            tb = board.copy(stack=False)
            tb.turn = side
            for m in tb.legal_moves:
                pt = tb.piece_type_at(m.from_square)
                if pt == chess.PAWN:
                    # A pawn move is safe progress if it doesn't immediately lose material
                    if not is_sacrifice(tb, m, threshold=1):
                        any_safe_progress = True
                        break
                elif tb.is_capture(m):
                    victim = tb.piece_at(m.to_square)
                    if victim is not None:
                        # Winning capture or safe capture of undefended piece
                        if PIECE_VAL.get(victim.piece_type, 0) > PIECE_VAL.get(pt, 0) or not tb.is_attacked_by(not side, m.to_square):
                            if not is_sacrifice(tb, m, threshold=1):
                                any_safe_progress = True
                                break
            if any_safe_progress:
                break
        if not any_safe_progress:
            # Confirm PV also doesn't find a forced tactical breakthrough in the first 4 plies
            if not pv_moves:
                return True
            sim2 = board.copy()
            pv_breaks = False
            for mv in pv_moves[:4]:
                if sim2.is_capture(mv) or sim2.piece_type_at(mv.from_square) == chess.PAWN or mv.promotion:
                    pv_breaks = True
                    break
                sim2.push(mv)
            if not pv_breaks:
                return True

    return False


def classify(loss, is_best, played_wp_after, best_wp, second_wp, sacrifice, wp_before,
             lenient=False, underpromo_brilliant=False):
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
    if (sacrifice and loss <= max_loss and played_wp_after >= min_after and wp_before < max_before) or (
        underpromo_brilliant and loss <= max_loss and played_wp_after >= min_after
    ):
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
