"""Human-readable, board-aware chess move explanations."""
from typing import List, Optional, Tuple

import chess

import classify as C

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


def _mover_cp(white_cp: Optional[int], color: bool) -> Optional[int]:
    if white_cp is None:
        return None
    return int(white_cp) if color == chess.WHITE else -int(white_cp)


def _sq_name(sq: int) -> str:
    return chess.square_name(sq)


def _piece_name(pt: Optional[int]) -> str:
    return PIECE_NAMES.get(pt, "piece")


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


def _newly_attacked_target(board_before: chess.Board, move: chess.Move, board_after: chess.Board) -> Optional[Tuple[int, int]]:
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


def _move_motif_phrase(board_before: chess.Board, move: chess.Move, board_after: chess.Board) -> str:
    """Return a concise verb phrase describing what `move` achieves on the board."""
    mover = board_before.turn
    opp = not mover
    moved_pc = board_before.piece_at(move.from_square)
    moved_pt = moved_pc.piece_type if moved_pc else chess.PAWN
    moved_val = C.PIECE_VAL.get(moved_pt, 0)
    to_s = _sq_name(move.to_square)
    gives_check = board_after.is_check()

    if board_after.is_checkmate():
        return "delivers checkmate"

    if move.promotion:
        promo_name = _piece_name(move.promotion)
        return f"promotes the pawn to a {promo_name}" + (" with check" if gives_check else "")

    if board_before.is_castling(move):
        if board_before.is_kingside_castling(move):
            return "castles kingside, securing the king and activating the rook"
        return "castles queenside, tucking the king to safety and centralizing the rook"

    fork = _find_fork(board_after, move.to_square, mover)
    if fork:
        t1, t2 = fork
        return f"forks the opponent's {t1} and {t2}"

    if gives_check and board_after.king(opp) not in board_after.attacks(move.to_square):
        return f"unleashes a discovered check by moving the {_piece_name(moved_pt)} to {to_s}"

    if board_before.is_capture(move):
        if board_before.is_en_passant(move):
            phrase = f"captures the pawn en passant on {to_s}"
        else:
            victim = board_before.piece_at(move.to_square)
            v_pt = victim.piece_type if victim else chess.PAWN
            v_val = C.PIECE_VAL.get(v_pt, 0)
            v_name = _piece_name(v_pt)
            if v_val >= 3 and not board_before.is_attacked_by(opp, move.to_square):
                phrase = f"wins an undefended {v_name} on {to_s}"
            elif v_pt == chess.ROOK and moved_pt in (chess.KNIGHT, chess.BISHOP):
                phrase = f"wins the exchange on {to_s}"
            elif v_val > moved_val and moved_val >= 1:
                phrase = f"wins the {v_name} on {to_s}"
            elif v_val == moved_val and v_val >= 3:
                phrase = f"trades {v_name}s on {to_s}"
            else:
                phrase = f"captures the {v_name} on {to_s}"
        return phrase + (" with check" if gives_check else "")

    if gives_check:
        return f"gives check from {to_s}"

    if moved_val >= 3 and board_before.is_attacked_by(opp, move.from_square) and not board_after.is_attacked_by(opp, move.to_square):
        return f"moves the attacked {_piece_name(moved_pt)} to safety on {to_s}"

    target = _newly_attacked_target(board_before, move, board_after)
    if target:
        t_pt, t_sq = target
        return f"attacks the opponent's {_piece_name(t_pt)} on {_sq_name(t_sq)}"

    if moved_pt in (chess.KNIGHT, chess.BISHOP):
        home_rank = 0 if mover == chess.WHITE else 7
        if chess.square_rank(move.from_square) == home_rank and chess.square_rank(move.to_square) != home_rank:
            return f"develops the {_piece_name(moved_pt)} to {to_s}"

    if moved_pt == chess.PAWN and move.to_square in _EXT_CENTER_SQUARES and board_before.fullmove_number <= 14:
        return f"contests the center on {to_s}"

    if moved_pt == chess.PAWN:
        return f"advances the pawn to {to_s}"
    if moved_pt == chess.KING:
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
    if not after_pv_uci:
        return ""
    ref_mv = _parse_move(board_after, after_pv_uci[0])
    if ref_mv is None:
        return ""
    ref_san = board_after.san(ref_mv)
    b_ref = board_after.copy()
    b_ref.push(ref_mv)
    if b_ref.is_checkmate():
        return f", allowing forced checkmate starting with {ref_san}"
    if board_after.is_capture(ref_mv):
        v = board_after.piece_at(ref_mv.to_square)
        if v and C.PIECE_VAL.get(v.piece_type, 0) >= 3:
            return f", allowing {ref_san} to win the {_piece_name(v.piece_type)}"
    if b_ref.is_check():
        return f", allowing {ref_san} with check"
    fork = _find_fork(b_ref, ref_mv.to_square, not b_ref.turn)
    if fork:
        return f", walking into {ref_san} (forking the {fork[0]} and {fork[1]})"
    return f", letting the opponent reply {ref_san}"


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
    """Build a concise, chess-accurate explanation for a single move."""
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
        return f"{san} delivers checkmate and wins the game."
    if b_after.is_stalemate():
        if sym in ("?!", "?", "??", "miss") and cp_b is not None and cp_b >= 150:
            return f"{san} accidentally causes stalemate from a winning position, throwing away the win.{_best_move_clause(b_before, best_s, best_u)}"
        return f"{san} results in stalemate, ending the game in a draw."
    if b_after.is_insufficient_material():
        return f"{san} leaves insufficient mating material — the game is drawn."

    # 2. Book / Forced
    if sym == "/":
        if opening:
            eco_part = f" ({eco})" if eco else ""
            return f"{san} is standard opening theory in the {opening}{eco_part}."
        return f"{san} is an established book move from opening theory."

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
                    return f"Brilliant underpromotion! {san} promotes to a {promo_name} to avoid stalemate after queen promotion."
            return f"Brilliant tactical underpromotion! {san} {motif} and secures a decisive edge."
        sac_name = bt if bt in ("queen", "rook", "bishop", "knight") else C.brilliant_category(b_before, mv)
        return f"Brilliant {sac_name} sacrifice! {san} {motif} while leaving material en prise for a strong attack."

    # 4. Great (!)
    if sym == "!":
        unique = (second_cp is not None and cp_a is not None and (cp_a - second_cp) >= 120)
        if unique:
            return f"Great find! {san} is the only strong move here — it {motif} and keeps full control."
        if cp_b is not None and cp_b <= -80 and cp_a is not None and cp_a >= -20:
            return f"Great defensive resource! {san} {motif} and saves the position."
        return f"Great move! {san} {motif} in a critical position."

    # 5. Best (+++)
    if sym == "+++":
        if cp_a is not None and cp_a >= 9000:
            return f"{san} is the best move — it {motif} and forces checkmate."
        return f"{san} is the best move; it {motif}."

    # 6. Excellent (++)
    if sym == "++":
        return f"{san} is an excellent move that {motif}."

    # 7. Good (+)
    if sym == "+":
        extra = f" ({best_s} was slightly sharper.)" if differs_from_best and len(best_s) <= 8 else ""
        return f"{san} is a solid move that {motif}.{extra}"

    # 8. Diagnose bad-move concrete reason (for ?!, ?, ??, miss)
    hanging = _find_hanging_pieces(b_after, mover)
    moved_sq_hanging = any(hsq == mv.to_square for _pt, hsq in hanging)
    allows_mate = (cp_a is not None and cp_a <= -9000 and (cp_b is None or cp_b > -8000))
    ref_clause = _refutation_clause(b_after, after_pv_uci)
    best_clause = _best_move_clause(b_before, best_s, best_u) if differs_from_best else ""

    if sym == "?!":
        if hanging:
            hpt, hsq = hanging[0]
            issue = f"leaves the {_piece_name(hpt)} on {_sq_name(hsq)} vulnerable"
        elif cp_b is not None and cp_a is not None and (cp_b - cp_a) >= 40:
            issue = "concedes part of your advantage"
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
            return f"{san} misses a key opportunity — playing {b_san_disp} ({best_hint}) would have seized a clear advantage."
        return f"{san} misses a much stronger tactical continuation.{best_clause}"

    if sym in ("?", "??"):
        severity = "blunder" if sym == "??" else "mistake"
        if allows_mate:
            return f"{san} is a {severity} that walks into forced checkmate{ref_clause}.{best_clause}"
        if moved_sq_hanging:
            mpc = b_after.piece_at(mv.to_square)
            mname = _piece_name(mpc.piece_type if mpc else None)
            return f"{san} is a {severity} that hangs the {mname} on {_sq_name(mv.to_square)}{ref_clause}.{best_clause}"
        if hanging:
            hpt, hsq = hanging[0]
            return f"{san} is a {severity} that leaves the {_piece_name(hpt)} on {_sq_name(hsq)} undefended{ref_clause}.{best_clause}"
        if ref_clause:
            return f"{san} is a {severity}{ref_clause}.{best_clause}"
        if cp_b is not None and cp_a is not None:
            if cp_b >= 150 and cp_a <= -150:
                return f"{san} is a {severity} that swings a winning position into a losing one.{best_clause}"
            if cp_b >= 150 and abs(cp_a) < 80:
                return f"{san} is a {severity} that gives away a clear winning advantage.{best_clause}"
            if sym == "??":
                return f"{san} is a serious blunder that severely damages the position.{best_clause}"
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
        after_pv_uci=None,
        opening=getattr(r, "opening", "") or "",
        eco=getattr(r, "eco", "") or "",
        brilliant_type=getattr(r, "brilliant_type", "") or "",
        eval_after_text=getattr(r, "eval_after_text", "") or "",
        second_cp=getattr(r, "second_cp", None),
    )
