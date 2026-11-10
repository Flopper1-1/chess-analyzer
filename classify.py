"""Win-probability conversion, evaluation bar formulas, and move classification."""
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
EVAL_FORMULAS = ("improved", "win_prob")
ANNOTATION_SYSTEMS = ("modern", "legacy")
MATE_CP = 1000


def cp_of(score):
    """chess.engine.PovScore (already from a POV) -> centipawns."""
    return score.score(mate_score=MATE_CP * 10) if score is not None else 0


def calibrate_cp(raw_cp) -> int:
    """Convert raw Stockfish 19 NNUE centipawns to Chess.com-calibrated centipawns.

    Stockfish 19 normalizes internal scores so 100 cp = 50% win probability at move 32,
    which inflates classical pawn evaluations by ~1.25x-1.45x in +2..+6 positions.
    """
    if raw_cp is None:
        return 0
    if abs(raw_cp) >= 9000:
        return int(raw_cp)
    sign = 1 if raw_cp >= 0 else -1
    a = abs(float(raw_cp))
    scaled = a * 0.82 / (1.0 + a / 2400.0)
    return int(round(sign * scaled))


def win_pct(cp):
    """Lichess/Chess.com logistic win-probability formula (0..100%)."""
    if cp is None:
        return 50.0
    cp = max(-MATE_CP * 10, min(MATE_CP * 10, cp))
    return 50.0 + 50.0 * (2.0 / (1.0 + math.exp(-0.00368208 * cp)) - 1.0)


def is_standard_start(board: chess.Board) -> bool:
    """True when the board is at the standard chess starting position with no moves played."""
    if board is None:
        return False
    return (
        board.board_fen() == chess.STARTING_BOARD_FEN
        and board.turn == chess.WHITE
        and board.fullmove_number == 1
        and board.halfmove_clock == 0
    )


def eval_bar_pct(cp, mode: str = "improved", board: chess.Board = None, pv=None, is_start: bool = False) -> float:
    """Convert White-POV centipawns to White's evaluation bar fill percentage (0.0..100.0).

    Modes:
    - 'improved' (default): Starts at 50% (0.0) on move 0, dampens tiny engine tempo noise
      near 0.00, uses a calibrated WDL/tanh curve matching Chess.com's visual bar scaling,
      and reserves 0% / 100% exclusively for forced checkmate.
    - 'win_prob': Legacy Lichess win-probability logistic curve (`win_pct(cp)`).
    """
    if is_start or cp is None or cp == 0:
        return 50.0
    if board is not None and (is_standard_start(board) or is_deadlocked_position(board, pv)):
        return 50.0
    if mode == "win_prob":
        return win_pct(cp)

    # Improved Eval Determination (default)
    if abs(cp) >= 9000:
        return 100.0 if cp > 0 else 0.0

    abs_cp = float(abs(cp))
    # Contempt / tempo deadzone dampening near 0.00 so tiny engine noise
    # (<= 15 cp) in dead-even positions stays visually centered at 50%.
    if abs_cp <= 15.0:
        eff_cp = 0.0
    elif abs_cp < 40.0:
        t = (abs_cp - 15.0) / 25.0
        eff_cp = math.copysign(abs_cp * (t * t), cp)
    else:
        eff_cp = float(cp)

    # Smooth WDL-calibrated hyperbolic tangent curve; non-mate advantages clamp to [2.5%, 97.5%]
    pct = 50.0 + 50.0 * math.tanh(eff_cp / 410.0)
    return max(2.5, min(97.5, pct))


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
    reply by the opponent (1-ply capture + recapture search)."""
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


def _has_unblocked_pawn(board: chess.Board) -> bool:
    """Return True if at least one pawn on the board is not rammed by an enemy pawn directly ahead."""
    for sq, pc in board.piece_map().items():
        if pc.piece_type != chess.PAWN:
            continue
        f = chess.square_file(sq)
        r = chess.square_rank(sq)
        ahead_r = r + 1 if pc.color == chess.WHITE else r - 1
        if 0 <= ahead_r <= 7:
            ahead_sq = chess.square(f, ahead_r)
            blocker = board.piece_at(ahead_sq)
            if blocker is None:
                return True
    return False


def is_deadlocked_position(board: chess.Board, pv=None) -> bool:
    """Return True when neither player can make progress without committing a bad move
    (e.g., 3-fold repetition, 50-move draw, or locked pawn fortress with no safe break)."""
    if board is None:
        return False
    if board.is_checkmate():
        return False
    if (
        board.is_stalemate()
        or board.is_insufficient_material()
        or board.is_fifty_moves()
        or board.is_repetition(3)
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

    # Check for locked pawn structure / fortress where neither side has a safe pawn advance or winning capture
    if not board.is_check() and chess.popcount(board.pawns) >= 4:
        any_safe_progress = False
        for side in (chess.WHITE, chess.BLACK):
            tb = board.copy(stack=False)
            tb.turn = side
            for m in tb.legal_moves:
                pt = tb.piece_type_at(m.from_square)
                if pt == chess.PAWN:
                    if not is_sacrifice(tb, m, threshold=1):
                        any_safe_progress = True
                        break
                elif tb.is_capture(m):
                    victim = tb.piece_at(m.to_square)
                    if victim is not None:
                        if PIECE_VAL.get(victim.piece_type, 0) > PIECE_VAL.get(pt, 0) or not tb.is_attacked_by(not side, m.to_square):
                            if not is_sacrifice(tb, m, threshold=1):
                                any_safe_progress = True
                                break
            if any_safe_progress:
                break
        if not any_safe_progress:
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


def classify_legacy(loss, is_best, played_wp_after, best_wp, second_wp, sacrifice, wp_before,
                    lenient=False, underpromo_brilliant=False):
    """Legacy win-probability threshold classification."""
    if loss > 5 and best_wp >= 70 and 30 <= played_wp_after < 60:
        return "miss"
    if loss > 20:
        return "??"
    if loss > 10:
        return "?"
    if loss > 5:
        return "?!"
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


def classify_modern(loss, is_best, played_wp_after, best_wp, second_wp, sacrifice, wp_before,
                    lenient=False, underpromo_brilliant=False,
                    cp_before=None, cp_after=None, best_cp=None,
                    is_recapture=False, in_check=False, gives_check=False,
                    phase="middlegame", repeats_position=False):
    """Modern Expected-Points (Chess.com Game Review calibrated) context-aware move classification.

    All win percentages (0..100) and centipawn values are from the mover's point of view.
    """
    eff_loss = max(0.0, float(loss))

    # 1. Brilliant (!!): Sound piece sacrifice or tactical/stalemate-avoiding underpromotion
    max_bril_loss = 5.0 if lenient else 2.5
    min_bril_after = 38.0 if lenient else 45.0
    max_bril_before = 95.0 if lenient else 90.0
    if underpromo_brilliant and eff_loss <= max_bril_loss and played_wp_after >= min_bril_after:
        return "!!"
    if sacrifice and eff_loss <= max_bril_loss:
        if (played_wp_after >= min_bril_after and wp_before < max_bril_before) or (
            wp_before < min_bril_after and played_wp_after >= wp_before - 1.0 and played_wp_after >= 35.0
        ):
            return "!!"

    # 2. Already-decided Winning Position Protection:
    # If a player is overwhelmingly winning before and after the move (>= +4.00 and >= 82% win prob),
    # minor engine depth fluctuations should not be flagged as Inaccuracy/Mistake/Blunder.
    if (
        played_wp_after >= 82.0
        and best_wp >= 86.0
        and (cp_after is None or cp_after >= 400)
        and eff_loss < 12.0
    ):
        eff_loss = min(eff_loss, 3.5)

    # 3. Forced-mate blunder check: allowing forced checkmate from a playable position
    if cp_after is not None and cp_after <= -9000 and best_wp >= 22.0 and (best_cp is None or best_cp > -8000):
        return "??"

    # 4. Miss (miss):
    # Case A: Opponent's previous move was an error that gifted mover a significant jump in win%
    # (best_wp - wp_before >= 11%), and mover failed to capitalize (eff_loss >= 8%) without
    # dropping well below their pre-gift standing.
    opp_gift = (best_wp - wp_before) >= 11.0 and best_wp >= 42.0
    if opp_gift and eff_loss >= 8.0 and (played_wp_after >= wp_before - 8.0 or played_wp_after >= 32.0):
        return "miss"
    # Case B: Missed clear tactical conversion in a sharp position
    if eff_loss > 5.5 and eff_loss <= 22.0 and 30.0 <= played_wp_after < 60.0 and best_wp >= 68.0:
        return "miss"

    # 5. Blunder (??) vs Mistake (?):
    if eff_loss > 20.0:
        still_ahead_mid = (
            played_wp_after >= 50.8
            and (cp_after is None or cp_after >= 10)
            and phase != "endgame"
            and eff_loss <= 28.0
        )
        already_worse_evasion = in_check and best_wp < 43.0 and eff_loss <= 26.0
        moderate_concession = eff_loss <= 22.8 and played_wp_after >= 20.0 and not sacrifice
        if still_ahead_mid or already_worse_evasion or moderate_concession:
            return "?"
        return "??"

    if eff_loss > 7.2:
        return "?"

    # 6. Inaccuracy (?!):
    cp_drop = (best_cp - cp_after) if (best_cp is not None and cp_after is not None) else 0
    opp_mistake_check = (best_wp - wp_before) >= 7.0 and gives_check and eff_loss >= 1.45
    if phase == "opening":
        if eff_loss > 6.2:
            return "?!"
    else:
        if (
            eff_loss > 5.0
            or (eff_loss >= 2.5 and cp_drop >= 38 and best_wp < 49.5)
            or opp_mistake_check
        ):
            return "?!"

    # 7. Great Move (!): Finding the critical best move in a sharp or game-changing position
    # Routine recaptures on the same square (is_recapture) are Best (+++), not Great (!).
    if is_best and not is_recapture and not repeats_position and played_wp_after >= 44.0:
        punished_error = (
            (best_wp - wp_before) >= 11.0
            and second_wp is not None
            and (best_wp - second_wp) >= 3.0
        )
        escaped_danger = (
            wp_before < 44.0
            and played_wp_after >= 51.0
            and second_wp is not None
            and (best_wp - second_wp) >= 3.0
        )
        only_good_move = (
            second_wp is not None
            and (best_wp - second_wp) >= 12.0
            and 45.0 <= best_wp <= 92.0
        )
        if punished_error or escaped_danger or only_good_move:
            return "!"

    # 8. Best / Excellent / Good:
    # Moves that repeat a prior board position in an equal/non-losing state are Excellent (++), not Best (+++).
    if is_best and not repeats_position:
        return "+++"
    exc_thresh = 2.0 if repeats_position else (1.40 if phase == "opening" else 1.05)
    if eff_loss <= exc_thresh:
        return "++"
    return "+"


def classify(loss, is_best, played_wp_after, best_wp, second_wp, sacrifice, wp_before,
             lenient=False, underpromo_brilliant=False, system: str = "modern",
             cp_before=None, cp_after=None, best_cp=None,
             is_recapture=False, in_check=False, gives_check=False,
             phase="middlegame", repeats_position=False):
    """Return an annotation symbol using the selected classification system ('modern' or 'legacy')."""
    if system == "legacy":
        return classify_legacy(
            loss, is_best, played_wp_after, best_wp, second_wp, sacrifice, wp_before,
            lenient=lenient, underpromo_brilliant=underpromo_brilliant,
        )
    return classify_modern(
        loss, is_best, played_wp_after, best_wp, second_wp, sacrifice, wp_before,
        lenient=lenient, underpromo_brilliant=underpromo_brilliant,
        cp_before=cp_before, cp_after=cp_after, best_cp=best_cp,
        is_recapture=is_recapture, in_check=in_check, gives_check=gives_check,
        phase=phase, repeats_position=repeats_position,
    )


SYMBOL_NAMES = {
    "??": "Blunder", "miss": "Miss", "?": "Mistake", "?!": "Inaccuracy", "+": "Good", "++": "Excellent",
    "+++": "Best", "!": "Great", "!!": "Brilliant", "/": "Book", "": "",
}
SYMBOL_COLORS = {
    "??": "#ca3431", "?": "#e58f2a", "?!": "#e6c619", "+": "#8fa86a", "++": "#6fa84d",
    "+++": "#4caf50", "!": "#5c8bb0", "!!": "#1baca6", "/": "#a58d6d",
}
