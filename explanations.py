"""Human-readable, board-aware chess move explanations."""
from typing import List, Optional, Tuple

import chess

import classify as C
import skills as SK

PIECE_NAMES = {
    chess.PAWN: "pawn",
    chess.KNIGHT: "knight",
    chess.BISHOP: "bishop",
    chess.ROOK: "rook",
    chess.QUEEN: "queen",
    chess.KING: "king",
}

_CENTER_SQUARES = (chess.D4, chess.E4, chess.D5, chess.E5)
_EXT_CENTER_SQUARES = (chess.C4, chess.C5, chess.D4, chess.E4, chess.D5, chess.E5, chess.F4, chess.F5)
_SLIDER_DIRS = {
    chess.BISHOP: ((-1, -1), (-1, 1), (1, -1), (1, 1)),
    chess.ROOK: ((-1, 0), (1, 0), (0, -1), (0, 1)),
    chess.QUEEN: ((-1, -1), (-1, 1), (1, -1), (1, 1), (-1, 0), (1, 0), (0, -1), (0, 1)),
}


def _mover_cp(white_cp: Optional[int], color: bool) -> Optional[int]:
    if white_cp is None:
        return None
    return int(white_cp) if color == chess.WHITE else -int(white_cp)


def _sq_name(sq: int) -> str:
    return chess.square_name(sq)


def _piece_name(pt: Optional[int]) -> str:
    return PIECE_NAMES.get(pt, "piece")


def _fmt_pawns(cp: Optional[int]) -> str:
    if cp is None:
        return ""
    if abs(cp) >= 9000:
        return "Mate" if cp > 0 else "-Mate"
    return f"{cp / 100.0:+.1f}"


def _find_fork(board_after: chess.Board, sq: int, mover: bool) -> Optional[Tuple[str, str]]:
    """Return top two enemy piece names forked from `sq`, or None."""
    attacker = board_after.piece_at(sq)
    if attacker is None or attacker.color != mover:
        return None
    opp = not mover
    att_val = C.PIECE_VAL.get(attacker.piece_type, 0)
    targets = []
    for tsq in board_after.attacks(sq):
        pc = board_after.piece_at(tsq)
        if pc is None or pc.color != opp:
            continue
        tval = C.PIECE_VAL.get(pc.piece_type, 0)
        is_king = pc.piece_type == chess.KING
        undefended = not board_after.is_attacked_by(opp, tsq)
        if is_king or (tval >= 5 and (att_val < tval or undefended or attacker.piece_type == chess.KNIGHT)) or (
            tval >= 3 and (undefended or attacker.piece_type == chess.PAWN)
        ):
            prio = 100 if is_king else tval * 10 + (1 if undefended else 0)
            targets.append((prio, pc.piece_type))
    if len(targets) < 2:
        return None
    targets.sort(reverse=True)
    return _piece_name(targets[0][1]), _piece_name(targets[1][1])


def _find_pin_or_skewer_detail(board_after: chess.Board, sq: int, mover: bool) -> Optional[Tuple[str, str]]:
    """Inspect sliding rays from `sq`: return (kind, phrase) for absolute pin, relative pin, or skewer."""
    pc = board_after.piece_at(sq)
    if pc is None or pc.color != mover or pc.piece_type not in _SLIDER_DIRS:
        return None
    opp = not mover
    f0, r0 = chess.square_file(sq), chess.square_rank(sq)
    best_item = None
    best_prio = -1
    for df, dr in _SLIDER_DIRS[pc.piece_type]:
        f, r = f0 + df, r0 + dr
        first_sq = None
        first_pc = None
        while 0 <= f <= 7 and 0 <= r <= 7:
            cur_sq = chess.square(f, r)
            cur_pc = board_after.piece_at(cur_sq)
            if cur_pc is not None:
                first_sq = cur_sq
                first_pc = cur_pc
                break
            f += df
            r += dr
        if first_pc is None or first_pc.color != opp:
            continue
        f += df
        r += dr
        second_sq = None
        second_pc = None
        while 0 <= f <= 7 and 0 <= r <= 7:
            cur_sq = chess.square(f, r)
            cur_pc = board_after.piece_at(cur_sq)
            if cur_pc is not None:
                second_sq = cur_sq
                second_pc = cur_pc
                break
            f += df
            r += dr
        if second_pc is None or second_pc.color != opp:
            continue

        v1 = C.PIECE_VAL.get(first_pc.piece_type, 0)
        v2 = C.PIECE_VAL.get(second_pc.piece_type, 0)
        n1 = _piece_name(first_pc.piece_type)
        n2 = _piece_name(second_pc.piece_type)
        s1 = _sq_name(first_sq)
        s2 = _sq_name(second_sq)

        # Absolute pin (only highlight if front piece is minor/major >= 3, or undefended)
        if first_pc.piece_type != chess.KING and second_pc.piece_type == chess.KING and v1 >= 3:
            prio = 90 + v1
            if prio > best_prio:
                best_prio = prio
                best_item = ("abs_pin", f"pins the {n1} on {s1} to the king")
        # Relative pin (front piece >= 3 pinned to more valuable piece behind)
        elif first_pc.piece_type != chess.KING and v1 >= 3 and v2 > v1:
            prio = 70 + v2
            if prio > best_prio:
                best_prio = prio
                best_item = ("pin", f"pins the {n1} on {s1} to the {n2} on {s2}")
        # Skewer
        elif first_pc.piece_type == chess.KING and (
            v2 >= 5 or (v2 >= 3 and not board_after.is_attacked_by(opp, second_sq))
        ):
            prio = 95 + v2
            if prio > best_prio:
                best_prio = prio
                best_item = ("skewer", f"skewers the king on {s1} and the {n2} on {s2}")
        elif v1 >= 5 and v1 > v2 and v2 >= 3:
            prio = 75 + v1
            if prio > best_prio:
                best_prio = prio
                best_item = ("skewer", f"skewers the {n1} on {s1} and the {n2} on {s2}")
    return best_item


def _find_discovered_attack(
    board_before: chess.Board, move: chess.Move, board_after: chess.Board
) -> Optional[Tuple[int, int]]:
    """Return `(target_pt, target_sq)` if vacating `move.from_square` uncovered a friendly slider attack."""
    mover = board_before.turn
    opp = not mover
    best = None
    best_val = 0
    for s_sq in chess.SQUARES:
        if s_sq == move.to_square:
            continue
        spc = board_after.piece_at(s_sq)
        if spc is None or spc.color != mover or spc.piece_type not in (chess.BISHOP, chess.ROOK, chess.QUEEN):
            continue
        before_att = board_before.attacks(s_sq)
        after_att = board_after.attacks(s_sq)
        s_val = C.PIECE_VAL.get(spc.piece_type, 0)
        for t_sq in after_att & ~before_att:
            if move.from_square not in chess.SquareSet.between(s_sq, t_sq):
                continue
            tpc = board_after.piece_at(t_sq)
            if tpc is None or tpc.color != opp or tpc.piece_type in (chess.PAWN, chess.KING):
                continue
            t_val = C.PIECE_VAL.get(tpc.piece_type, 0)
            undefended = not board_after.is_attacked_by(opp, t_sq)
            if t_val >= 3 and (undefended or t_val > s_val):
                score = t_val * 10 + (4 if undefended else 0)
                if score > best_val:
                    best_val = score
                    best = (tpc.piece_type, t_sq)
    return best


def _find_newly_trapped_piece(
    board_before: chess.Board, board_after: chess.Board, mover: bool
) -> Optional[Tuple[int, int]]:
    opp = not mover
    best = None
    best_val = 0
    for sq, pc in board_after.piece_map().items():
        if pc.color != opp or pc.piece_type not in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
            continue
        if SK._piece_is_trapped(board_after, sq, mover) and not SK._piece_is_trapped(board_before, sq, mover):
            val = C.PIECE_VAL.get(pc.piece_type, 0)
            if val > best_val:
                best_val = val
                best = (pc.piece_type, sq)
    return best


def _find_removed_defender_target(
    board_before: chess.Board, move: chess.Move, board_after: chess.Board
) -> Optional[Tuple[int, int]]:
    """When `move` captures an enemy defender, return `(other_pt, other_sq)` left undefended and attacked."""
    if not board_before.is_capture(move) or board_before.is_en_passant(move):
        return None
    mover = board_before.turn
    opp = not mover
    cap_sq = move.to_square
    victim = board_before.piece_at(cap_sq)
    if victim is None or victim.color != opp:
        return None
    defended_before = board_before.attacks(cap_sq)
    best = None
    best_val = 0
    for other_sq in defended_before:
        if other_sq == cap_sq:
            continue
        opc = board_after.piece_at(other_sq)
        if opc is None or opc.color != opp or opc.piece_type in (chess.PAWN, chess.KING):
            continue
        oval = C.PIECE_VAL.get(opc.piece_type, 0)
        if oval >= 3 and board_after.is_attacked_by(mover, other_sq) and not board_after.is_attacked_by(opp, other_sq):
            if oval > best_val:
                best_val = oval
                best = (opc.piece_type, other_sq)
    return best


def _find_hanging_pieces(board_after: chess.Board, side: bool) -> List[Tuple[int, int]]:
    """Return [(piece_type, sq), ...] of `side` pieces that can be profitably captured on `board_after`."""
    opp = not side
    if board_after.turn != opp:
        return []
    found = {}
    for mv in board_after.legal_moves:
        if not board_after.is_capture(mv):
            continue
        victim = board_after.piece_at(mv.to_square)
        attacker = board_after.piece_at(mv.from_square)
        if victim is None or attacker is None or victim.color != side:
            continue
        v_val = C.PIECE_VAL.get(victim.piece_type, 0)
        a_val = C.PIECE_VAL.get(attacker.piece_type, 0)
        if v_val < 3:
            continue
        undefended = not board_after.is_attacked_by(side, mv.to_square)
        if undefended or a_val < v_val:
            prev = found.get(mv.to_square)
            if prev is None or v_val > C.PIECE_VAL.get(prev, 0):
                found[mv.to_square] = victim.piece_type
    out = [(pt, sq) for sq, pt in found.items()]
    out.sort(key=lambda item: C.PIECE_VAL.get(item[0], 0), reverse=True)
    return out


def _newly_attacked_target(
    board_before: chess.Board, move: chess.Move, board_after: chess.Board
) -> Optional[Tuple[int, int]]:
    mover = board_before.turn
    opp = not mover
    moved = board_before.piece_at(move.from_square)
    moved_val = C.PIECE_VAL.get(moved.piece_type, 0) if moved else 0
    best = None
    best_prio = -1
    for tsq in board_after.attacks(move.to_square):
        pc = board_after.piece_at(tsq)
        if pc is None or pc.color != opp or pc.piece_type in (chess.PAWN, chess.KING):
            continue
        tval = C.PIECE_VAL.get(pc.piece_type, 0)
        undefended = not board_after.is_attacked_by(opp, tsq)
        if tval > moved_val or undefended or moved_val == 1:
            prio = tval * 10 + (3 if undefended else 0)
            if prio > best_prio:
                best_prio = prio
                best = (pc.piece_type, tsq)
    return best


def _newly_defended_piece(
    board_before: chess.Board, move: chess.Move, board_after: chess.Board
) -> Optional[Tuple[int, int]]:
    mover = board_before.turn
    opp = not mover
    best = None
    best_val = 0
    for sq, pc in board_before.piece_map().items():
        if sq == move.from_square or pc.color != mover:
            continue
        val = C.PIECE_VAL.get(pc.piece_type, 0)
        if val < 3 or not board_before.is_attacked_by(opp, sq):
            continue
        def_b = len(board_before.attackers(mover, sq))
        def_a = len(board_after.attackers(mover, sq))
        if def_b == 0 and def_a >= 1 and sq in board_after.attacks(move.to_square):
            if val > best_val:
                best_val = val
                best = (pc.piece_type, sq)
    return best


def _file_pawn_status(board: chess.Board, file_idx: int, mover: bool) -> str:
    """Return 'open', 'semi_open', or 'closed' for `file_idx` from `mover` POV."""
    own_p = False
    opp_p = False
    for r in range(8):
        pc = board.piece_at(chess.square(file_idx, r))
        if pc is not None and pc.piece_type == chess.PAWN:
            if pc.color == mover:
                own_p = True
            else:
                opp_p = True
    if not own_p and not opp_p:
        return "open"
    if not own_p and opp_p:
        return "semi_open"
    return "closed"


def _checkmate_flavor(board_after: chess.Board, move: chess.Move, mover: bool) -> str:
    opp = not mover
    opp_king = board_after.king(opp)
    moved_pt = board_after.piece_type_at(move.to_square)
    if opp_king is not None:
        kf, kr = chess.square_file(opp_king), chess.square_rank(opp_king)
        if moved_pt == chess.KNIGHT:
            # Smothered mate: all king-adjacent squares occupied by opponent's own pieces
            adj_own = 0
            adj_tot = 0
            for df in (-1, 0, 1):
                for dr in (-1, 0, 1):
                    if df == 0 and dr == 0:
                        continue
                    nf, nr = kf + df, kr + dr
                    if 0 <= nf <= 7 and 0 <= nr <= 7:
                        adj_tot += 1
                        apc = board_after.piece_at(chess.square(nf, nr))
                        if apc is not None and apc.color == opp:
                            adj_own += 1
            if adj_tot > 0 and adj_own == adj_tot:
                return "delivers a smothered checkmate"
        back_r = 7 if mover == chess.WHITE else 0
        front_r = 6 if mover == chess.WHITE else 1
        if kr == back_r and moved_pt in (chess.ROOK, chess.QUEEN) and chess.square_rank(move.to_square) == back_r:
            blocked = sum(
                1 for df in (-1, 0, 1)
                if 0 <= kf + df <= 7
                and board_after.piece_at(chess.square(kf + df, front_r)) is not None
                and board_after.piece_at(chess.square(kf + df, front_r)).color == opp
            )
            if blocked >= 2:
                return "delivers a back-rank checkmate"
    return "delivers checkmate"


def _move_motif_phrase(board_before: chess.Board, move: chess.Move, board_after: chess.Board) -> str:
    """Return a concise, insightful verb phrase describing what `move` achieves on the board."""
    mover = board_before.turn
    opp = not mover
    moved_pc = board_before.piece_at(move.from_square)
    moved_pt = moved_pc.piece_type if moved_pc else chess.PAWN
    moved_val = C.PIECE_VAL.get(moved_pt, 0)
    to_s = _sq_name(move.to_square)
    to_f = chess.square_file(move.to_square)
    to_r = chess.square_rank(move.to_square)
    file_letter = chess.FILE_NAMES[to_f]
    gives_check = board_after.is_check()

    if board_after.is_checkmate():
        return _checkmate_flavor(board_after, move, mover)

    if move.promotion:
        promo_name = _piece_name(move.promotion)
        fork = _find_fork(board_after, move.to_square, mover)
        if fork:
            return f"promotes to a {promo_name}, forking the {fork[0]} and {fork[1]}"
        return f"promotes the pawn to a {promo_name}" + (" with check" if gives_check else "")

    if board_before.is_castling(move):
        if board_before.is_kingside_castling(move):
            return "castles kingside, securing the king and activating the rook"
        return "castles queenside, tucking the king to safety and centralizing the rook"

    # Double check
    if gives_check and len(board_after.checkers()) >= 2:
        return f"unleashes a double check with the {_piece_name(moved_pt)} on {to_s}"

    # Tactical fork
    fork = _find_fork(board_after, move.to_square, mover)
    if fork:
        t1, t2 = fork
        chk_tail = " with check" if (gives_check and "king" not in (t1, t2)) else ""
        return f"forks the opponent's {t1} and {t2}{chk_tail}"

    # Discovered check
    if gives_check and board_after.king(opp) not in board_after.attacks(move.to_square):
        if board_before.is_capture(move):
            victim = board_before.piece_at(move.to_square)
            v_name = _piece_name(victim.piece_type if victim else chess.PAWN)
            return f"captures the {v_name} on {to_s} with a discovered check"
        target = _newly_attacked_target(board_before, move, board_after)
        if target:
            return (
                f"unleashes a discovered check while attacking the "
                f"{_piece_name(target[0])} on {_sq_name(target[1])}"
            )
        return f"unleashes a discovered check by moving the {_piece_name(moved_pt)} to {to_s}"

    # Captures (including removing defender, simplifying trades, pawn structure damage)
    if board_before.is_capture(move):
        if board_before.is_en_passant(move):
            phrase = f"captures the pawn en passant on {to_s}"
        else:
            victim = board_before.piece_at(move.to_square)
            v_pt = victim.piece_type if victim else chess.PAWN
            v_val = C.PIECE_VAL.get(v_pt, 0)
            v_name = _piece_name(v_pt)
            rem_def = _find_removed_defender_target(board_before, move, board_after)
            if rem_def and not gives_check:
                phrase = (
                    f"captures the {v_name} on {to_s}, removing the defender of the "
                    f"{_piece_name(rem_def[0])} on {_sq_name(rem_def[1])}"
                )
            elif v_val >= 3 and not board_before.is_attacked_by(opp, move.to_square):
                phrase = f"wins an undefended {v_name} on {to_s}"
            elif v_pt == chess.ROOK and moved_pt in (chess.KNIGHT, chess.BISHOP):
                phrase = f"wins the exchange on {to_s}"
            elif v_val > moved_val and moved_val >= 1:
                phrase = f"wins the {v_name} on {to_s}"
            elif v_val == moved_val and v_val >= 3:
                mat_lead = C.material(board_before, mover) - C.material(board_before, opp)
                if mat_lead >= 3:
                    phrase = f"trades {v_name}s on {to_s} to simplify while ahead in material"
                else:
                    phrase = f"trades {v_name}s on {to_s}"
            else:
                pp_b, _ = SK._count_passed_pawns(board_before, mover)
                pp_a, _ = SK._count_passed_pawns(board_after, mover)
                if pp_a > pp_b:
                    phrase = f"captures the {v_name} on {to_s} and creates a passed pawn"
                else:
                    phrase = f"captures the {v_name} on {to_s}"
        return phrase + (" with check" if gives_check else "")

    # Skewer or Pin created by moved slider
    pin_skewer = _find_pin_or_skewer_detail(board_after, move.to_square, mover)
    if pin_skewer:
        _kind, ps_phrase = pin_skewer
        if gives_check and "king on" not in ps_phrase:
            return f"{ps_phrase} with check"
        return ps_phrase

    chk_suffix = " with check" if gives_check else ""

    # Discovered attack (non-check)
    disc = _find_discovered_attack(board_before, move, board_after)
    if disc:
        return f"uncovers a discovered attack on the {_piece_name(disc[0])} on {_sq_name(disc[1])}{chk_suffix}"

    # Trapped piece
    trapped = _find_newly_trapped_piece(board_before, board_after, mover)
    if trapped:
        return f"traps the opponent's {_piece_name(trapped[0])} on {_sq_name(trapped[1])}{chk_suffix}"

    # Evading an attack on our piece
    if (
        moved_val >= 3
        and board_before.is_attacked_by(opp, move.from_square)
        and not board_after.is_attacked_by(opp, move.to_square)
        and not gives_check
    ):
        return f"moves the attacked {_piece_name(moved_pt)} to safety on {to_s}"

    # Pawn kick with tempo vs generic piece attack
    target = _newly_attacked_target(board_before, move, board_after)
    if target and not gives_check:
        t_pt, t_sq = target
        if moved_pt == chess.PAWN:
            return f"kicks the opponent's {_piece_name(t_pt)} on {_sq_name(t_sq)} with tempo"
        if SK._has_mate_in_one(board_after, mover) and not SK._has_mate_in_one(board_before, mover):
            return f"attacks the {_piece_name(t_pt)} on {_sq_name(t_sq)} while threatening checkmate"
        return f"attacks the opponent's {_piece_name(t_pt)} on {_sq_name(t_sq)}"

    # Direct mate-in-1 threat
    if not gives_check and SK._has_mate_in_one(board_after, mover) and not SK._has_mate_in_one(board_before, mover):
        return f"places the {_piece_name(moved_pt)} on {to_s}, creating a checkmate threat"

    # Defending an undefended friendly piece
    defended = _newly_defended_piece(board_before, move, board_after)
    if defended and not gives_check:
        return f"defends the attacked {_piece_name(defended[0])} on {_sq_name(defended[1])}"

    # Outpost (Knight or Bishop)
    if SK._is_outpost(board_after, move.to_square, mover):
        return f"plants the {_piece_name(moved_pt)} on a strong pawn-supported outpost at {to_s}{chk_suffix}"

    # Rook strategic & endgame motifs
    if moved_pt == chess.ROOK:
        seventh_r = 6 if mover == chess.WHITE else 1
        if to_r == seventh_r and chess.square_rank(move.from_square) != seventh_r:
            other_7th = any(
                s != move.to_square and chess.square_rank(s) == seventh_r
                for s in board_after.pieces(chess.ROOK, mover)
            )
            if other_7th:
                return f"doubles rooks on the seventh rank at {to_s}{chk_suffix}"
            return f"infiltrates the seventh rank with the rook on {to_s}{chk_suffix}"
        for p_sq in board_after.pieces(chess.PAWN, mover):
            if chess.square_file(p_sq) == to_f and SK._is_passed_pawn(board_after, p_sq, mover):
                pr = chess.square_rank(p_sq)
                if ((mover == chess.WHITE and to_r < pr) or (mover == chess.BLACK and to_r > pr)) and SK._ray_between_clear(board_after, move.to_square, p_sq):
                    return f"places the rook behind the passed {file_letter}-pawn{chk_suffix}"
        if SK._doubled_rooks_count(board_after, mover) > SK._doubled_rooks_count(board_before, mover):
            if any(s != move.to_square and chess.square_file(s) == to_f for s in board_after.pieces(chess.ROOK, mover)):
                return f"doubles rooks on the {file_letter}-file{chk_suffix}"
            return f"doubles rooks along the {to_r + 1}th rank{chk_suffix}"
        f_stat = _file_pawn_status(board_after, to_f, mover)
        if f_stat == "open" and chess.square_file(move.from_square) != to_f:
            return f"activates the rook on the open {file_letter}-file{chk_suffix}"
        if f_stat == "semi_open" and chess.square_file(move.from_square) != to_f:
            return f"places the rook on the semi-open {file_letter}-file{chk_suffix}"

    if gives_check:
        return f"gives check from {to_s}"

    # Battery formation (Q+B or Q+R)
    if moved_pt in (chess.QUEEN, chess.BISHOP, chess.ROOK):
        if SK._is_battery_pair(board_after, mover) > SK._is_battery_pair(board_before, mover):
            return f"places the {_piece_name(moved_pt)} on {to_s} to form an attacking battery"

    # Fianchetto & piece development / connecting rooks
    home_rank = 0 if mover == chess.WHITE else 7
    fian_sqs = (chess.B2, chess.G2) if mover == chess.WHITE else (chess.B7, chess.G7)
    if moved_pt == chess.BISHOP and chess.square_rank(move.from_square) == home_rank and move.to_square in fian_sqs:
        return f"fianchettos the bishop on {to_s} to control the long diagonal"

    connected_now = (
        board_before.fullmove_number <= 22
        and SK._connected_rooks_on_backrank(board_after, mover)
        and not SK._connected_rooks_on_backrank(board_before, mover)
    )
    if moved_pt in (chess.KNIGHT, chess.BISHOP):
        if chess.square_rank(move.from_square) == home_rank and to_r != home_rank:
            tail = " and connects the rooks" if connected_now else ""
            return f"develops the {_piece_name(moved_pt)} to {to_s}{tail}"
    if connected_now and moved_pt == chess.QUEEN:
        return f"develops the queen to {to_s} and connects the rooks"

    # Passed pawn & central pawn pushes
    if moved_pt == chess.PAWN:
        if SK._is_passed_pawn(board_after, move.to_square, mover):
            penult_r = 6 if mover == chess.WHITE else 1
            if to_r == penult_r:
                return f"pushes the passed {file_letter}-pawn to {to_s}, one step from promotion"
            return f"advances the passed {file_letter}-pawn to {to_s}"
        if move.to_square in _EXT_CENTER_SQUARES and board_before.fullmove_number <= 14:
            return f"contests the center on {to_s}"
        return f"advances the pawn to {to_s}"

    # Endgame king opposition & centralization
    if moved_pt == chess.KING:
        non_pk = sum(
            1 for p in board_after.piece_map().values()
            if p.piece_type not in (chess.PAWN, chess.KING)
        )
        if non_pk <= 2:
            opp_k = board_after.king(opp)
            if opp_k is not None:
                okf, okr = chess.square_file(opp_k), chess.square_rank(opp_k)
                if (to_f == okf and abs(to_r - okr) == 2) or (to_r == okr and abs(to_f - okf) == 2):
                    return f"steps the king to {to_s}, taking direct opposition"
            dist_b = abs(chess.square_file(move.from_square) - 3.5) + abs(chess.square_rank(move.from_square) - 3.5)
            dist_a = abs(to_f - 3.5) + abs(to_r - 3.5)
            if dist_a < dist_b:
                return f"centralizes the king on {to_s} for the endgame"
        return f"steps the king to {to_s}"

    return f"places the {_piece_name(moved_pt)} on {to_s}"


def _parse_move(board: chess.Board, uci: str = "", san: str = "") -> Optional[chess.Move]:
    if uci:
        try:
            mv = chess.Move.from_uci(uci.strip())
            if mv in board.legal_moves:
                return mv
        except Exception:
            pass
    if san:
        try:
            return board.parse_san(san.strip())
        except Exception:
            pass
    return None


def _best_move_clause(board_before: chess.Board, best_san: str, best_uci: str) -> str:
    mv_best = _parse_move(board_before, best_uci, best_san)
    if mv_best is None:
        return f" {best_san} was stronger." if best_san else ""
    san_b = best_san or board_before.san(mv_best)
    b_best = board_before.copy()
    b_best.push(mv_best)
    hint = _move_motif_phrase(board_before, mv_best, b_best)
    return f" Playing {san_b} ({hint}) was stronger."


def _refutation_clause(board_after: chess.Board, after_pv_uci: Optional[List[str]]) -> str:
    """Explain the concrete opponent refutation across up to 3 plies of `after_pv_uci`."""
    if not after_pv_uci:
        return ""
    opp = board_after.turn
    mover = not opp
    ref_mv = _parse_move(board_after, after_pv_uci[0])
    if ref_mv is None:
        return ""
    ref_san = board_after.san(ref_mv)
    b_ref = board_after.copy()
    b_ref.push(ref_mv)

    if b_ref.is_checkmate():
        return f", allowing forced checkmate starting with {ref_san}"
    if ref_mv.promotion:
        return f", allowing {ref_san} to promote a pawn"
    if board_after.is_capture(ref_mv):
        v = board_after.piece_at(ref_mv.to_square)
        if v and C.PIECE_VAL.get(v.piece_type, 0) >= 3:
            v_val = C.PIECE_VAL.get(v.piece_type, 0)
            a_pt = board_after.piece_type_at(ref_mv.from_square)
            a_val = C.PIECE_VAL.get(a_pt, 0)
            if v.piece_type == chess.ROOK and a_pt in (chess.KNIGHT, chess.BISHOP):
                return f", allowing {ref_san} to win the exchange"
            if not board_after.is_attacked_by(mover, ref_mv.to_square) or a_val < v_val:
                return f", allowing {ref_san} to win the {_piece_name(v.piece_type)}"

    fork = _find_fork(b_ref, ref_mv.to_square, opp)
    if fork:
        return f", walking into {ref_san} (forking the {fork[0]} and {fork[1]})"

    pin_skewer = _find_pin_or_skewer_detail(b_ref, ref_mv.to_square, opp)
    if pin_skewer:
        return f", walking into {ref_san} ({pin_skewer[1]})"

    trapped = _find_newly_trapped_piece(board_after, b_ref, opp)
    if trapped:
        return f", allowing {ref_san} to trap the {_piece_name(trapped[0])} on {_sq_name(trapped[1])}"

    # Look 2 plies deeper (mover reply -> opponent follow-up) for forced tactical gain or mate
    if len(after_pv_uci) >= 3:
        mv2 = _parse_move(b_ref, after_pv_uci[1])
        if mv2 is not None:
            san2 = b_ref.san(mv2)
            b2 = b_ref.copy()
            b2.push(mv2)
            mv3 = _parse_move(b2, after_pv_uci[2])
            if mv3 is not None:
                san3 = b2.san(mv3)
                b3 = b2.copy()
                b3.push(mv3)
                if b3.is_checkmate():
                    return f", allowing forced checkmate after {ref_san} {san2} {san3}"
                if b2.is_capture(mv3):
                    v3 = b2.piece_at(mv3.to_square)
                    a3_val = C.PIECE_VAL.get(b2.piece_type_at(mv3.from_square), 0)
                    v3_val = C.PIECE_VAL.get(v3.piece_type, 0) if v3 else 0
                    if v3 and v3.color == mover and v3_val >= 3 and (not b2.is_attacked_by(mover, mv3.to_square) or a3_val < v3_val):
                        return f", allowing {ref_san} followed by {san3} to win the {_piece_name(v3.piece_type)}"

    if b_ref.is_check():
        return f", allowing {ref_san} with check"
    return f", letting the opponent seize the initiative with {ref_san}"


def explain_move(
    fen_before: str,
    move_uci: str,
    symbol: str,
    eval_before: Optional[int] = None,
    eval_after: Optional[int] = None,
    best_san: str = "",
    best_uci: str = "",
    pv_san: Optional[List[str]] = None,
    pv_uci: Optional[List[str]] = None,
    after_pv_uci: Optional[List[str]] = None,
    opening: str = "",
    eco: str = "",
    brilliant_type: str = "",
    eval_after_text: str = "",
    second_cp: Optional[int] = None,
) -> str:
    """Build a concise, coach-grade chess explanation for a single move."""
    best_u = best_uci or (pv_uci[0] if pv_uci else "")
    best_s = best_san or (pv_san[0] if pv_san else "")
    sym = symbol or ""

    if not fen_before or not move_uci:
        title = C.SYMBOL_NAMES.get(sym, "")
        if sym == "/" and opening:
            return f"Standard opening theory in the {opening}."
        if best_s and sym in ("?!", "?", "??", "miss") and best_s != best_uci:
            return f"{title} move — playing {best_s} was stronger."
        return f"{title} move." if title else ""

    try:
        b_before = chess.Board(fen_before)
        mv = chess.Move.from_uci(move_uci)
        if mv not in b_before.legal_moves:
            raise ValueError("illegal move for FEN")
        san = b_before.san(mv)
        b_after = b_before.copy()
        b_after.push(mv)
    except Exception:
        title = C.SYMBOL_NAMES.get(sym, "")
        return f"{title} move." if title else ""

    mover = b_before.turn
    motif = _move_motif_phrase(b_before, mv, b_after)
    cp_b = _mover_cp(eval_before, mover)
    cp_a = _mover_cp(eval_after, mover)
    differs_from_best = bool(best_s and best_s != san)

    # 1. Terminal outcomes first
    if b_after.is_checkmate():
        return f"{san} {motif} and wins the game."
    if b_after.is_stalemate():
        if sym in ("?!", "?", "??", "miss") and cp_b is not None and cp_b >= 150:
            return (
                f"{san} accidentally causes stalemate from a winning position, throwing away the win."
                f"{_best_move_clause(b_before, best_s, best_u)}"
            )
        return f"{san} results in stalemate, ending the game in a draw."
    if b_after.is_insufficient_material():
        return f"{san} leaves insufficient mating material — the game is drawn."

    # 2. Book / Forced
    if sym == "/":
        if opening:
            eco_part = f" ({eco})" if eco else ""
            return f"{san} is standard opening theory in the {opening}{eco_part}, as it {motif}."
        return f"{san} is an established book move that {motif}."

    if sym == "forced":
        if b_before.is_check():
            return f"{san} is the only legal move to escape check."
        return f"{san} is the only legal move available in this position."

    # 3. Brilliant (!!)
    if sym == "!!":
        bt = (brilliant_type or "").strip().lower()
        if bt == "underpromotion" or C.is_underpromotion(mv):
            promo_name = _piece_name(mv.promotion)
            q_mv = chess.Move(mv.from_square, mv.to_square, promotion=chess.QUEEN)
            if q_mv in b_before.legal_moves:
                bq = b_before.copy()
                bq.push(q_mv)
                if bq.is_stalemate():
                    return (
                        f"Brilliant underpromotion! {san} promotes to a {promo_name} "
                        f"to avoid stalemate after queen promotion."
                    )
            return f"Brilliant tactical underpromotion! {san} {motif} and secures a decisive edge."
        sac_name = bt if bt in ("queen", "rook", "bishop", "knight") else C.brilliant_category(b_before, mv)
        cont = ""
        if pv_san and len(pv_san) >= 3 and pv_san[0] == san:
            cont = f" (e.g. after {pv_san[1]}, {pv_san[2]} follows)"
        if cp_a is not None and abs(cp_a) <= 45 and (cp_b is None or cp_b <= 45):
            return (
                f"Brilliant {sac_name} sacrifice! {san} {motif}, offering material for "
                f"dynamic compensation that holds the balance{cont}."
            )
        return (
            f"Brilliant {sac_name} sacrifice! {san} {motif} while leaving material en prise "
            f"for a powerful initiative{cont}."
        )

    # 4. Great (!)
    if sym == "!":
        unique = (second_cp is not None and cp_a is not None and (cp_a - second_cp) >= 120)
        if unique:
            return f"Great find! {san} is the only strong move here — it {motif} and keeps full control."
        if cp_b is not None and cp_b <= -80 and cp_a is not None and cp_a >= -35:
            return f"Great defensive resource! {san} {motif} and saves a difficult position."
        return f"Great move! {san} {motif} at a critical moment."

    # 5. Best (+++)
    if sym == "+++":
        if cp_a is not None and cp_a >= 9000:
            return f"{san} is the best move — it {motif} and forces checkmate."
        return f"{san} is the best move; it {motif}."

    # 6. Excellent (++)
    if sym == "++":
        if b_after.is_repetition(2):
            return f"{san} {motif}, repeating the position to maintain the balance."
        return f"{san} is an excellent move that {motif}."

    # 7. Good (+)
    if sym == "+":
        extra = ""
        if differs_from_best and len(best_s) <= 8:
            mv_b = _parse_move(b_before, best_u, best_s)
            if mv_b is not None:
                bb = b_before.copy()
                bb.push(mv_b)
                bh = _move_motif_phrase(b_before, mv_b, bb)
                extra = f" ({best_s}, which {bh}, was slightly more accurate.)"
            else:
                extra = f" ({best_s} was slightly sharper.)"
        return f"{san} is a solid move that {motif}.{extra}"

    # 8. Diagnose bad-move concrete reason (for ?!, ?, ??, miss)
    hanging = _find_hanging_pieces(b_after, mover)
    moved_sq_hanging = any(hsq == mv.to_square for _pt, hsq in hanging)
    allows_mate = (cp_a is not None and cp_a <= -9000 and (cp_b is None or cp_b > -8000))
    ref_clause = _refutation_clause(b_after, after_pv_uci)
    best_clause = _best_move_clause(b_before, best_s, best_u) if differs_from_best else ""
    swing_tag = ""
    if cp_b is not None and cp_a is not None and abs(cp_b) < 9000 and abs(cp_a) < 9000 and abs(cp_b - cp_a) >= 90:
        swing_tag = f" ({_fmt_pawns(cp_b)} → {_fmt_pawns(cp_a)})"

    if sym == "?!":
        if hanging:
            hpt, hsq = hanging[0]
            issue = f"leaves the {_piece_name(hpt)} on {_sq_name(hsq)} vulnerable"
        elif cp_b is not None and cp_a is not None and (cp_b - cp_a) >= 40:
            issue = f"concedes part of your advantage{swing_tag}"
        else:
            issue = f"{motif}, though it loses a bit of precision"
        return f"{san} is a slight inaccuracy that {issue}{ref_clause}.{best_clause}"

    if sym == "miss":
        mv_best = _parse_move(b_before, best_u, best_s)
        if mv_best is not None:
            b_best = b_before.copy()
            b_best.push(mv_best)
            best_hint = _move_motif_phrase(b_before, mv_best, b_best)
            b_san_disp = best_s or b_before.san(mv_best)
            if cp_b is not None and cp_b >= 9000:
                return (
                    f"{san} misses a forced checkmate — playing {b_san_disp} "
                    f"({best_hint}) would have forced mate."
                )
            return (
                f"{san} misses a key opportunity — playing {b_san_disp} "
                f"({best_hint}) would have seized a clear advantage."
            )
        return f"{san} misses a much stronger tactical continuation.{best_clause}"

    if sym in ("?", "??"):
        severity = "blunder" if sym == "??" else "mistake"
        if allows_mate:
            return f"{san} is a {severity} that walks into forced checkmate{ref_clause}.{best_clause}"
        if moved_sq_hanging:
            mpc = b_after.piece_at(mv.to_square)
            mname = _piece_name(mpc.piece_type if mpc else None)
            return f"{san} is a {severity} that hangs the {mname} on {_sq_name(mv.to_square)}{ref_clause}{swing_tag}.{best_clause}"
        if hanging:
            hpt, hsq = hanging[0]
            return f"{san} is a {severity} that leaves the {_piece_name(hpt)} on {_sq_name(hsq)} undefended{ref_clause}{swing_tag}.{best_clause}"
        if ref_clause:
            return f"{san} is a {severity}{ref_clause}{swing_tag}.{best_clause}"
        if cp_b is not None and cp_a is not None:
            if cp_b >= 150 and cp_a <= -150:
                return f"{san} is a {severity} that swings a winning position into a losing one{swing_tag}.{best_clause}"
            if cp_b >= 150 and abs(cp_a) < 80:
                return f"{san} is a {severity} that gives away a clear winning advantage{swing_tag}.{best_clause}"
            if sym == "??":
                return f"{san} is a serious blunder that severely damages the position{swing_tag}.{best_clause}"
        return f"{san} is a {severity} that worsens the position.{best_clause}"

    return f"{san} {motif}."


def explain_result(r) -> str:
    """Return `r.explanation` if already populated, or derive it on the fly from `MoveResult`."""
    if r is None:
        return ""
    existing = (getattr(r, "explanation", "") or "").strip()
    if existing:
        return existing
    pv_u = getattr(r, "pv_uci", None) or []
    pv_s = getattr(r, "pv", None) or []
    after_pv_u = getattr(r, "after_pv_uci", None) or None
    return explain_move(
        fen_before=getattr(r, "fen_before", "") or "",
        move_uci=getattr(r, "uci", "") or "",
        symbol=getattr(r, "symbol", "") or "",
        eval_before=getattr(r, "eval_before", None),
        eval_after=getattr(r, "eval_after", None),
        best_san=getattr(r, "best_san", "") or "",
        best_uci=pv_u[0] if pv_u else "",
        pv_san=pv_s,
        pv_uci=pv_u,
        after_pv_uci=after_pv_u,
        opening=getattr(r, "opening", "") or "",
        eco=getattr(r, "eco", "") or "",
        brilliant_type=getattr(r, "brilliant_type", "") or "",
        eval_after_text=getattr(r, "eval_after_text", "") or "",
        second_cp=getattr(r, "second_cp", None),
    )
