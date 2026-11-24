"""Expected-points conversion, evaluation bar scaling, and move classification."""
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
    """Convert raw NNUE centipawns to normalized calibrated centipawns.

    Modern NNUE engines normalize internal scores asymmetrically at higher
    advantages (~1.25x-1.45x in +2..+6 positions); this restores a classical scale.
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
    """Legacy logistic win-probability formula (0..100%)."""
    if cp is None:
        return 50.0
    cp = max(-MATE_CP * 10, min(MATE_CP * 10, cp))
    return 50.0 + 50.0 * (2.0 / (1.0 + math.exp(-0.00368208 * cp)) - 1.0)


def expected_points(cp, elo: float = 2000.0) -> float:
    """Rating-aware piecewise expected-points curve (0.0..1.0)."""
    if cp is None:
        return 0.5
    cp_val = float(cp)
    if abs(cp_val) >= 9000.0:
        return 1.0 if cp_val > 0.0 else 0.0
    elo_c = max(1000.0, min(3000.0, float(elo if elo is not None else 2000.0)))
    elo_scale = 1.0 + 0.000548 * (elo_c - 2000.0)
    x = abs(cp_val)
    if x <= 80.0:
        fx = 0.0054375 * x
    elif x <= 200.0:
        fx = 0.435 + 0.0085 * (x - 80.0)
    elif x <= 500.0:
        fx = 1.455 + (1.78 / 300.0) * (x - 200.0)
    else:
        fx = 3.235 + 0.0099 * (x - 500.0)
    z = max(-40.0, min(40.0, math.copysign(elo_scale * fx, cp_val)))
    return 1.0 / (1.0 + math.exp(-z))


def expected_points_pct(cp, elo: float = 2000.0) -> float:
    """Rating-aware piecewise expected points as a percentage (0.0..100.0)."""
    return 100.0 * expected_points(cp, elo=elo)


def wdl_probabilities(cp, elo: float = 2000.0):
    """Return (win, draw, loss) probabilities summing to 1.0 with W + 0.5*D == expected_points."""
    if cp is not None and abs(float(cp)) >= 9000.0:
        return (1.0, 0.0, 0.0) if float(cp) > 0.0 else (0.0, 0.0, 1.0)
    ep = expected_points(cp, elo=elo)
    elo_c = max(1000.0, min(3000.0, float(elo if elo is not None else 2000.0)))
    draw_peak = 0.30 + 0.25 * (elo_c - 1000.0) / 2000.0
    abs_cp = abs(float(cp)) if cp is not None else 0.0
    d = draw_peak * math.exp(-((abs_cp / 160.0) ** 1.4))
    d = max(0.0, min(d, 2.0 * ep, 2.0 * (1.0 - ep)))
    w = max(0.0, ep - 0.5 * d)
    l = max(0.0, 1.0 - w - d)
    return (w, d, l)


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
      near 0.00, maps [-4.0, +4.0] pawns linearly to [5.0%, 95.0%], and reserves 0% / 100%
      exclusively for forced checkmate.
    - 'win_prob': Legacy win-probability logistic curve (`win_pct(cp)`).
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
        eff_pawns = 0.0
    elif abs_cp < 40.0:
        t = (abs_cp - 15.0) / 25.0
        eff_pawns = math.copysign((abs_cp / 100.0) * (t * t), float(cp))
    else:
        eff_pawns = max(-4.0, min(4.0, float(cp) / 100.0))

    pct = 50.0 + eff_pawns * (45.0 / 4.0)
    return max(5.0, min(95.0, pct))


def material(board, color):
    return sum(PIECE_VAL[p.piece_type] for p in board.piece_map().values() if p.color == color)


def is_underpromotion(move: chess.Move) -> bool:
    """True if the move promotes a pawn to a Knight, Bishop, or Rook."""
    return move is not None and move.promotion in (chess.KNIGHT, chess.BISHOP, chess.ROOK)


def is_brilliant_underpromotion(board_before: chess.Board, move: chess.Move, is_best: bool = True,
                                loss: float = 0.0, max_loss: float = 2.5,
                                second_wp: float = None, best_wp: float = None) -> bool:
    """True if an underpromotion (N, B, R) is objectively sound and tactically critical
    (e.g., avoids stalemate/draw when Queen promotion fails, or delivers a Knight check/fork/mate)."""
    if not is_underpromotion(move) or loss > max_loss:
        return False
    color = board_before.turn
    b_after = board_before.copy()
    b_after.push(move)

    # Check what would happen if promoted to Queen instead
    queen_move = chess.Move(move.from_square, move.to_square, promotion=chess.QUEEN)
    queen_draws = False
    queen_gives_check = False
    queen_mates = False
    if queen_move in board_before.legal_moves:
        b_queen = board_before.copy()
        b_queen.push(queen_move)
        queen_draws = b_queen.is_stalemate() or b_queen.is_insufficient_material()
        queen_gives_check = b_queen.is_check()
        queen_mates = b_queen.is_checkmate()

    # 1. Avoiding immediate stalemate / insufficient material when Queen promotion draws
    if queen_draws:
        return True

    # 2. Knight underpromotion: unique L-shaped geometry (checkmate, royal/major fork, check, or best move)
    if move.promotion == chess.KNIGHT:
        if b_after.is_checkmate() and not queen_mates:
            return True
        if b_after.is_check() and not queen_gives_check:
            return True
        attacked_valuable = sum(
            1 for sq in b_after.attacks(move.to_square)
            if b_after.piece_at(sq) is not None
            and b_after.piece_at(sq).color != color
            and (b_after.piece_at(sq).piece_type == chess.KING or PIECE_VAL.get(b_after.piece_at(sq).piece_type, 0) >= 5)
        )
        if attacked_valuable >= 2:
            return True
        if is_best and (second_wp is None or best_wp is None or (best_wp - second_wp) >= 2.0):
            return True
        return False

    # 3. Rook / Bishop underpromotion: since a Queen has all Rook & Bishop moves,
    # it is only tactical (not decorative) if it is the engine's best move and Queen promotion
    # is significantly worse (e.g. allows a stalemate/perpetual tactic on the next ply).
    if second_wp is not None and best_wp is not None:
        return bool(is_best and (best_wp - second_wp) >= 3.0)
    if is_best or b_after.is_check():
        return True
    return False


def _non_pawn_material(board, color) -> int:
    return sum(
        PIECE_VAL[p.piece_type]
        for p in board.piece_map().values()
        if p.color == color and p.piece_type not in (chess.PAWN, chess.KING)
    )


def _recapture_adjusted_net(board_after_reply: chess.Board, color: bool):
    """Best `(total_net, piece_net)` for `color` from `board_after_reply` considering 1 recapture
    while accounting for immediate opponent re-recapture on the same target square."""
    best_tot = material(board_after_reply, color) - material(board_after_reply, not color)
    best_pc = _non_pawn_material(board_after_reply, color) - _non_pawn_material(board_after_reply, not color)
    for rec in board_after_reply.legal_moves:
        if not board_after_reply.is_capture(rec):
            continue
        b3 = board_after_reply.copy()
        b3.push(rec)
        rec_net = material(b3, color) - material(b3, not color)
        rec_pc_net = _non_pawn_material(b3, color) - _non_pawn_material(b3, not color)
        if not b3.is_checkmate():
            opp_recaps = [
                m4 for m4 in b3.legal_moves
                if m4.to_square == rec.to_square and b3.is_capture(m4)
            ]
            if opp_recaps:
                rec_pt = b3.piece_type_at(rec.to_square)
                val = PIECE_VAL.get(rec_pt, 0)
                rec_net -= val
                if rec_pt not in (chess.PAWN, chess.KING, None):
                    rec_pc_net -= val
        if rec_net > best_tot or (rec_net == best_tot and rec_pc_net > best_pc):
            best_tot = rec_net
            best_pc = rec_pc_net
    return best_tot, best_pc


def is_sacrifice(board_before, move, threshold=2):
    """True if the mover willingly leaves a piece/rook/queen undefended or sacrifices
    an exchange/piece (including a minor piece for two pawns) after opponent's best reply."""
    color = board_before.turn
    b = board_before.copy()
    start = material(b, color) - material(b, not color)
    piece_start = _non_pawn_material(b, color) - _non_pawn_material(b, not color)
    moved_pt = b.piece_type_at(move.from_square)
    b.push(move)
    if b.is_checkmate():
        return False
    worst = start
    worst_piece_loss = 0
    piece_involved = (moved_pt is not None and moved_pt != chess.PAWN)
    # opponent's best capture reply (SEE-aware so unrelated suicide captures elsewhere don't mask sacrifices)
    for reply in b.legal_moves:
        if b.is_capture(reply):
            victim = b.piece_at(reply.to_square)
            b2 = b.copy()
            b2.push(reply)
            best, best_pc = _recapture_adjusted_net(b2, color)
            if best < worst:
                worst = best
            pc_loss = piece_start - best_pc
            if best <= start - 1 and pc_loss > worst_piece_loss:
                worst_piece_loss = pc_loss
            if (start - best >= threshold or (start - best >= 1 and pc_loss >= 3)) and (
                victim is not None and victim.color == color and victim.piece_type != chess.PAWN
            ):
                piece_involved = True
    # also the immediate state if no capture reply
    if not any(b.is_capture(m) for m in b.legal_moves):
        worst = min(worst, material(b, color) - material(b, not color))
    # Recognize minor-piece-for-two-pawns sacrifices (net -1 total, net >= -3 non-pawn piece material)
    if start - worst < threshold:
        if not (threshold == 2 and (start - worst) >= 1 and worst_piece_loss >= 3 and piece_involved):
            return False
    return True if threshold < 2 else piece_involved


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
            best, _best_pc = _recapture_adjusted_net(b2, color)
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
                    phase="middlegame", repeats_position=False,
                    is_capture=False, pre_attacked_free_piece=False,
                    pendulum_return=False, attacks_piece=False,
                    prev_critical=False, already_overwhelming=False):
    """Modern expected-points context-aware move classification.

    All expected-points percentages (0..100) and centipawn values are from the mover's point of view.
    """
    eff_loss = max(0.0, float(loss))

    # 1. Brilliant (!!): A Sound Piece/Exchange Sacrifice or Tactical Underpromotion
    max_bril_loss = 5.0 if lenient else 2.5
    min_bril_after = 38.0 if lenient else 46.5
    min_bril_cp = -100 if lenient else -35
    max_bril_before = 95.0 if lenient else 90.0
    max_bril_cp_before = 900 if lenient else 600

    if (sacrifice or underpromo_brilliant) and eff_loss <= max_bril_loss:
        not_worse_after = (
            played_wp_after >= min_bril_after
            and (cp_after is None or cp_after >= min_bril_cp)
        )
        only_winning_try = (
            second_wp is not None
            and (best_wp - second_wp) >= 15.0
            and second_wp < 65.0
        )
        not_overwhelmingly_winning = (
            (
                wp_before < max_bril_before
                and (cp_before is None or cp_before < max_bril_cp_before)
                and not already_overwhelming
            )
            or only_winning_try
        )
        is_critical_moment = (
            wp_before < 75.0
            or (cp_before is not None and cp_before < 250)
            or second_wp is None
            or second_wp < 82.0
            or (best_wp - second_wp) >= 5.0
        )
        if not_worse_after and not_overwhelmingly_winning and is_critical_moment:
            return "!!"

    # 2. Already-decided Winning Position Protection:
    # If a player is overwhelmingly winning before and after the move (>= +4.00 and >= 82% expected points),
    # minor engine depth fluctuations should not be flagged as Inaccuracy/Mistake/Blunder — unless
    # a forced checkmate was on the board and missed into a non-trivial position.
    missed_forced_mate = (
        best_cp is not None
        and best_cp >= 9000
        and (cp_after is None or cp_after < 650)
    )
    if (
        not missed_forced_mate
        and played_wp_after >= 82.0
        and best_wp >= 86.0
        and (cp_after is None or cp_after >= 400)
        and eff_loss < 12.0
    ):
        eff_loss = min(eff_loss, 3.5)

    # 3. Forced-mate blunder check: allowing forced checkmate from a playable position
    if cp_after is not None and cp_after <= -9000 and best_wp >= 22.0 and (best_cp is None or best_cp > -8000):
        return "??"

    # 4. Miss (miss):
    # Case A: Missed forced checkmate while remaining in a playable/advantageous position
    if missed_forced_mate and eff_loss >= 3.5 and played_wp_after >= 42.0:
        return "miss"
    # Case B: Opponent's previous move gifted mover a significant jump in expected points
    # (best_wp - wp_before >= 11%), and mover failed to capitalize (eff_loss >= 8%) without
    # dropping well below their pre-gift standing.
    opp_gift = (best_wp - wp_before) >= 11.0 and best_wp >= 42.0
    if opp_gift and eff_loss >= 8.0 and (played_wp_after >= wp_before - 8.0 or played_wp_after >= 32.0):
        return "miss"
    # Case C: Missed clear tactical conversion in a sharp position
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

    if eff_loss > 10.0:
        return "?"

    # 6. Inaccuracy (?!):
    cp_drop = (best_cp - cp_after) if (best_cp is not None and cp_after is not None) else 0
    opp_mistake_check = (best_wp - wp_before) >= 7.0 and gives_check and eff_loss >= 1.45
    if eff_loss > 5.0:
        return "?!"
    if phase != "opening" and (
        (eff_loss >= 2.5 and cp_drop >= 38 and best_wp < 49.5)
        or opp_mistake_check
    ):
        return "?!"

    # 7. Great Move (!): Finding the critical best move in a sharp or game-changing position
    # Routine recaptures on the same square (is_recapture), cashing in on pre-attacked
    # undefended pieces, pendulum retreats, or mating in 1 are Best (+++), not Great (!).
    if (
        is_best
        and not is_recapture
        and not repeats_position
        and not pre_attacked_free_piece
        and not pendulum_return
        and (best_cp is None or best_cp < 9000)
    ):
        # Holding a difficult defense where every alternative loses on the spot
        only_drawing_hold = (
            38.0 <= played_wp_after < 52.0
            and wp_before <= 46.0
            and second_wp is not None
            and second_wp <= 22.0
            and (best_wp - second_wp) >= 16.0
        )
        if only_drawing_hold:
            return "!"

        if 45.5 <= played_wp_after < 99.0:
            only_good_move = (
                second_wp is not None
                and (best_wp - second_wp) >= 15.0
                and 45.5 <= best_wp <= 95.0
                and wp_before < 88.0
            )
            sharp_conversion = (
                second_wp is not None
                and (best_wp - second_wp) >= 11.5
                and second_wp < 56.0
                and 50.0 <= best_wp <= 92.0
                and wp_before < 76.0
            )
            if only_good_move or sharp_conversion:
                return "!"
            if (
                wp_before < 62.0
                and (second_wp is None or second_wp < 62.0 or (wp_before <= 53.0 and not is_capture))
            ):
                punished_error = (
                    (best_wp - wp_before) >= 11.0
                    and second_wp is not None
                    and (best_wp - second_wp) >= 3.0
                )
                saved_lost_position = (
                    wp_before < 32.0
                    and (best_wp - wp_before) >= 20.0
                    and played_wp_after >= 48.0
                )
                defender_kick = (
                    attacks_piece
                    and (best_wp - wp_before) >= 7.0
                    and played_wp_after >= 56.0
                    and (second_wp is None or second_wp <= best_wp)
                )
                critical_followup = (
                    prev_critical
                    and not is_capture
                    and (best_cp is not None and best_cp >= 0)
                    and (second_wp is not None and (best_wp - second_wp) >= 3.0 and second_wp < 47.5)
                )
                escaped_danger = (
                    wp_before < 44.0
                    and played_wp_after >= 51.0
                    and second_wp is not None
                    and (best_wp - second_wp) >= 3.0
                )
                if (
                    punished_error
                    or saved_lost_position
                    or defender_kick
                    or critical_followup
                    or escaped_danger
                ):
                    return "!"

    # 8. Best / Excellent / Good:
    # Moves that repeat a prior board position in an equal/non-losing state are Excellent (++), not Best (+++).
    if is_best and not repeats_position:
        return "+++"
    if eff_loss <= 2.0:
        return "++"
    return "+"


def classify(loss, is_best, played_wp_after, best_wp, second_wp, sacrifice, wp_before,
             lenient=False, underpromo_brilliant=False, system: str = "modern",
             cp_before=None, cp_after=None, best_cp=None,
             is_recapture=False, in_check=False, gives_check=False,
             phase="middlegame", repeats_position=False,
             is_capture=False, pre_attacked_free_piece=False,
             pendulum_return=False, attacks_piece=False,
             prev_critical=False, already_overwhelming=False):
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
        is_capture=is_capture, pre_attacked_free_piece=pre_attacked_free_piece,
        pendulum_return=pendulum_return, attacks_piece=attacks_piece,
        prev_critical=prev_critical, already_overwhelming=already_overwhelming,
    )


SYMBOL_NAMES = {
    "??": "Blunder", "miss": "Miss", "?": "Mistake", "?!": "Inaccuracy", "+": "Good", "++": "Excellent",
    "+++": "Best", "!": "Great", "!!": "Brilliant", "/": "Book", "": "",
}
SYMBOL_COLORS = {
    "??": "#ca3431", "?": "#e58f2a", "?!": "#e6c619", "+": "#8fa86a", "++": "#6fa84d",
    "+++": "#4caf50", "!": "#5c8bb0", "!!": "#1baca6", "/": "#a58d6d",
}
