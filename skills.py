"""Board-aware chess skill detection (72 skills across 5 categories) and progression tracking."""
from dataclasses import dataclass
import json
import os
from typing import Dict, List, Optional, Set, Tuple

import chess

import classify as C
import themes

SKILL_CATEGORIES = ("Fundamentals", "Openings", "Tactics", "Strategy", "Endgames")
UNSOUND_SYMBOLS = {"?!", "?", "??", "miss"}

_MAT_VAL = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 100,
}

_CENTER_SQUARES = (chess.D4, chess.E4, chess.D5, chess.E5)
_SLIDER_DIRS = {
    chess.BISHOP: ((-1, -1), (-1, 1), (1, -1), (1, 1)),
    chess.ROOK: ((-1, 0), (1, 0), (0, -1), (0, 1)),
    chess.QUEEN: (
        (-1, -1), (-1, 1), (1, -1), (1, 1),
        (-1, 0), (1, 0), (0, -1), (0, 1),
    ),
}


@dataclass(frozen=True)
class SkillDef:
    id: str
    name: str
    category: str
    description: str
    points_to_master: int
    unlocked_by: Tuple[str, ...] = ()


SKILLS: Tuple[SkillDef, ...] = (
    # ---- Fundamentals (7)
    SkillDef("capture", "Capture", "Fundamentals", "Capture an opponent's piece or pawn soundly.", 3),
    SkillDef("check", "Check", "Fundamentals", "Give check with a sound tactical or positional purpose.", 3),
    SkillDef("castle", "Castling", "Fundamentals", "Castle your king to safety and activate a rook.", 3),
    SkillDef("checkmate", "Checkmate", "Fundamentals", "Deliver checkmate to end the game.", 3),
    SkillDef("free_piece", "Capture Free Piece", "Fundamentals", "Win an undefended opponent piece.", 3, ("capture",)),
    SkillDef("defend_piece", "Defend Piece", "Fundamentals", "Defend an attacked friendly piece so it stays safe.", 3, ("capture",)),
    SkillDef("retreat", "Safe Retreat", "Fundamentals", "Move an attacked piece to a safe square.", 3, ("defend_piece",)),

    # ---- Openings (10)
    SkillDef("develops_piece", "Develop Piece", "Openings", "Bring a knight or bishop off the back rank in the opening.", 4),
    SkillDef("pawns_in_center", "Pawns in the Center", "Openings", "Occupy a central square (d4, e4, d5, e5) with a pawn.", 4),
    SkillDef("one_book_move", "1 Book Move", "Openings", "Play a sound opening theory move.", 3),
    SkillDef("two_book_moves", "2 Book Moves", "Openings", "Follow opening theory to at least move 2.", 3, ("one_book_move",)),
    SkillDef("three_book_moves", "3 Book Moves", "Openings", "Follow opening theory to at least move 3.", 4, ("two_book_moves",)),
    SkillDef("four_book_moves", "4 Book Moves", "Openings", "Follow opening theory to at least move 4.", 4, ("three_book_moves",)),
    SkillDef("fianchetto", "Fianchetto", "Openings", "Fianchetto a bishop onto b2/g2 or b7/g7.", 3, ("develops_piece",)),
    SkillDef("strikes_at_center", "Strike at the Center", "Openings", "Challenge an opponent's central pawn or piece.", 4, ("pawns_in_center",)),
    SkillDef("connect_rooks", "Connect the Rooks", "Openings", "Clear the back rank so your two rooks defend each other.", 4, ("develops_piece",)),
    SkillDef("complete_development", "Complete Development", "Openings", "Develop all minor pieces and coordinate your rooks.", 4, ("connect_rooks",)),

    # ---- Tactics (21)
    SkillDef("recapture", "Recapture", "Tactics", "Recapture cleanly on the same square.", 3),
    SkillDef("winning_capture", "Winning Capture", "Tactics", "Capture a higher-value opponent piece.", 4),
    SkillDef("blocks_attack", "Block an Attack", "Tactics", "Interpose a piece or pawn to block a check or sliding attack.", 3),
    SkillDef("defend_checkmate", "Defend Checkmate", "Tactics", "Spot and neutralize an opponent's mate-in-one threat.", 3),
    SkillDef("fork", "Fork", "Tactics", "Attack two or more opponent targets at the same time.", 4, ("winning_capture",)),
    SkillDef("pin", "Pin", "Tactics", "Pin an opponent piece against a more valuable target behind it.", 4, ("winning_capture",)),
    SkillDef("absolute_pin", "Absolute Pin", "Tactics", "Pin an opponent piece directly to their king.", 4, ("pin",)),
    SkillDef("attacking_pinned_piece", "Attack Pinned Piece", "Tactics", "Pile extra pressure onto an already pinned piece.", 3, ("pin",)),
    SkillDef("exploits_pin", "Exploit a Pin", "Tactics", "Capitalize tactically on a pinned defender.", 4, ("absolute_pin",)),
    SkillDef("skewer", "Skewer", "Tactics", "Attack a high-value piece to win a target behind it.", 4, ("pin",)),
    SkillDef("knight_fork", "Knight Fork", "Tactics", "Use a knight to fork two valuable targets.", 4, ("fork",)),
    SkillDef("royal_fork", "Royal Fork", "Tactics", "Fork the opponent's king and queen simultaneously.", 3, ("knight_fork",)),
    SkillDef("discovered_attack", "Discovered Attack", "Tactics", "Unleash a hidden attack from a slider behind your moving piece.", 4, ("winning_capture",)),
    SkillDef("discovered_check", "Discovered Check", "Tactics", "Reveal a check from a slider behind your moving piece.", 4, ("discovered_attack",)),
    SkillDef("double_check", "Double Check", "Tactics", "Give check with two pieces at the exact same time.", 3, ("discovered_check",)),
    SkillDef("trapped_piece", "Trap a Piece", "Tactics", "Leave an opponent piece with no safe escape square.", 4, ("winning_capture",)),
    SkillDef("removes_defender", "Remove the Defender", "Tactics", "Eliminate the piece guarding a key target.", 4, ("winning_capture",)),
    SkillDef("counter_threat", "Counter-Threat", "Tactics", "Answer an attack on your piece by creating a stronger threat.", 4, ("blocks_attack",)),
    SkillDef("defend_tactic", "Defend a Tactic", "Tactics", "Neutralize an opponent's immediate material threat.", 4, ("defend_checkmate",)),
    SkillDef("brilliant_sacrifice", "Brilliant Sacrifice", "Tactics", "Execute a sound tactical sacrifice (!!).", 3, ("discovered_attack",)),
    SkillDef("queen_sacrifice", "Queen Sacrifice", "Tactics", "Pull off a brilliant queen sacrifice (!!).", 3, ("brilliant_sacrifice",)),

    # ---- Strategy (16)
    SkillDef("equal_trade", "Equal Trade", "Strategy", "Trade pieces of equal material value.", 3),
    SkillDef("kick", "Kick a Piece", "Strategy", "Advance a pawn to drive back an opponent piece.", 4),
    SkillDef("powerful_bishop", "Active Bishop", "Strategy", "Post a bishop on a long, open diagonal.", 4),
    SkillDef("rook_to_open_file", "Rook on Open File", "Strategy", "Claim an open file with no pawns using a rook.", 4),
    SkillDef("outpost", "Establish an Outpost", "Strategy", "Plant a knight or bishop on a pawn-supported outpost.", 4, ("kick",)),
    SkillDef("trading_to_simplify", "Trade When Ahead", "Strategy", "Exchange pieces cleanly when ahead in material.", 4, ("equal_trade",)),
    SkillDef("double_rooks", "Double Rooks", "Strategy", "Align both rooks on the same file or rank.", 4, ("rook_to_open_file",)),
    SkillDef("creates_battery", "Create a Battery", "Strategy", "Coordinate your queen with a bishop or rook along one line.", 4, ("double_rooks",)),
    SkillDef("prevent_castling", "Prevent Castling", "Strategy", "Strip the opponent of castling rights before they castle.", 3, ("powerful_bishop",)),
    SkillDef("wins_tempo", "Gain a Tempo", "Strategy", "Move an active piece while immediately threatening a target.", 4, ("kick",)),
    SkillDef("avoids_trade", "Avoid Trade", "Strategy", "Keep your piece on the board instead of accepting a trade.", 4, ("trading_to_simplify",)),
    SkillDef("develop_with_tempo", "Develop with Tempo", "Strategy", "Develop an opening minor piece while creating a threat.", 4, ("wins_tempo",)),
    SkillDef("damages_opponent_pawn_structure", "Damage Pawn Structure", "Strategy", "Create doubled or isolated pawns in the enemy camp.", 4, ("outpost",)),
    SkillDef("en_passant", "En Passant", "Strategy", "Capture an enemy pawn with the special en passant rule.", 3),
    SkillDef("improves_pawn_structure", "Improve Pawn Structure", "Strategy", "Repair doubled or isolated pawns in your structure.", 4, ("equal_trade",)),
    SkillDef("pawn_storm", "Pawn Storm", "Strategy", "Push wing pawns toward the opponent's castled king.", 4, ("damages_opponent_pawn_structure",)),

    # ---- Endgames (18)
    SkillDef("promotion", "Pawn Promotion", "Endgames", "Promote a pawn to a new piece.", 3),
    SkillDef("pushes_passed_pawn", "Push Passed Pawn", "Endgames", "Advance a passed pawn with no enemy pawns blocking it.", 4),
    SkillDef("activate_king", "Activate the King", "Endgames", "Bring your king toward the center or active squares in the endgame.", 4),
    SkillDef("backrank_mate", "Back-Rank Mate", "Endgames", "Checkmate a king trapped behind its own pawns on the back rank.", 3),
    SkillDef("ladder_mate", "Ladder Mate", "Endgames", "Coordinate two major pieces to deliver a ladder checkmate.", 3, ("backrank_mate",)),
    SkillDef("queen_checkmate", "Queen Endgame Mate", "Endgames", "Deliver checkmate with a queen in the endgame.", 3, ("backrank_mate",)),
    SkillDef("rook_checkmate", "Rook Endgame Mate", "Endgames", "Deliver checkmate in a rook endgame.", 3, ("ladder_mate",)),
    SkillDef("makes_passed_pawn", "Create a Passed Pawn", "Endgames", "Break through to create a new passed pawn.", 4, ("pushes_passed_pawn",)),
    SkillDef("makes_protected_passed_pawn", "Protected Passed Pawn", "Endgames", "Create or reinforce a pawn-protected passed pawn.", 3, ("makes_passed_pawn",)),
    SkillDef("rook_to_seventh", "Rook to the 7th Rank", "Endgames", "Infiltrate onto the opponent's second rank with a rook.", 4, ("activate_king",)),
    SkillDef("doubled_rooks_on_the_seventh", "Pigs on the 7th", "Endgames", "Place both rooks together on the opponent's second rank.", 3, ("rook_to_seventh",)),
    SkillDef("rook_behind_own_passed_pawn", "Rook Behind Passed Pawn", "Endgames", "Support your passed pawn from behind with a rook.", 3, ("rook_to_seventh",)),
    SkillDef("rook_behind_opposing_passed_pawn", "Rook Behind Enemy Pawn", "Endgames", "Place your rook behind an opponent's passed pawn.", 3, ("rook_to_seventh",)),
    SkillDef("opposition", "King Opposition", "Endgames", "Seize direct king opposition in an endgame.", 4, ("activate_king",)),
    SkillDef("king_and_pawn_endgames", "King & Pawn Endgame", "Endgames", "Play an accurate move in a king and pawn endgame.", 4, ("opposition",)),
    SkillDef("queen_endgames", "Queen Endgame Technique", "Endgames", "Play an accurate move in a queen endgame.", 4, ("promotion",)),
    SkillDef("rook_endgames", "Rook Endgame Technique", "Endgames", "Play an accurate move in a rook endgame.", 4, ("rook_to_seventh",)),
    SkillDef("knight_and_bishop_endgames", "Minor Piece Endgame", "Endgames", "Play an accurate move in a knight or bishop endgame.", 4, ("activate_king",)),
)

SKILL_BY_ID: Dict[str, SkillDef] = {s.id: s for s in SKILLS}
SKILLS_BY_CATEGORY: Dict[str, List[SkillDef]] = {
    cat: [s for s in SKILLS if s.category == cat] for cat in SKILL_CATEGORIES
}

# Display order: highest tactical/endgame specificity first so summaries highlight the sharpest skill
_DISPLAY_PRIORITY_ORDER = [
    "queen_sacrifice", "brilliant_sacrifice",
    "double_check", "backrank_mate", "ladder_mate", "queen_checkmate", "rook_checkmate", "checkmate",
    "royal_fork", "knight_fork", "fork",
    "discovered_check", "discovered_attack",
    "absolute_pin", "pin", "skewer", "trapped_piece", "removes_defender",
    "exploits_pin", "attacking_pinned_piece", "defend_checkmate", "defend_tactic",
    "counter_threat", "blocks_attack",
    "doubled_rooks_on_the_seventh", "rook_behind_own_passed_pawn",
    "rook_behind_opposing_passed_pawn", "rook_to_seventh",
    "makes_protected_passed_pawn", "makes_passed_pawn", "pushes_passed_pawn",
    "promotion", "opposition", "activate_king",
    "free_piece", "winning_capture", "en_passant", "castle",
    "complete_development", "connect_rooks", "fianchetto",
    "four_book_moves", "three_book_moves", "two_book_moves", "one_book_move",
    "develop_with_tempo", "double_rooks", "creates_battery", "outpost",
    "rook_to_open_file", "prevent_castling", "trading_to_simplify",
    "damages_opponent_pawn_structure", "improves_pawn_structure", "pawn_storm",
    "powerful_bishop", "wins_tempo", "avoids_trade", "kick",
    "strikes_at_center", "pawns_in_center", "develops_piece",
    "recapture", "equal_trade", "retreat", "defend_piece", "capture", "check",
    "king_and_pawn_endgames", "queen_endgames", "rook_endgames", "knight_and_bishop_endgames",
]
SKILL_PRIORITY: Dict[str, int] = {sid: idx for idx, sid in enumerate(_DISPLAY_PRIORITY_ORDER)}


# ---------------------------------------------------------------------------
# Board geometry helpers
# ---------------------------------------------------------------------------

def _mat_val(pt: Optional[int]) -> int:
    return _MAT_VAL.get(pt, 0) if pt is not None else 0


def _ray_between_clear(board: chess.Board, sq1: int, sq2: int) -> bool:
    between = chess.SquareSet.between(sq1, sq2)
    return not any(board.piece_at(s) is not None for s in between)


def _is_passed_pawn(board: chess.Board, sq: int, color: bool) -> bool:
    pc = board.piece_at(sq)
    if pc is None or pc.piece_type != chess.PAWN or pc.color != color:
        return False
    f0 = chess.square_file(sq)
    r0 = chess.square_rank(sq)
    opp = not color
    for df in (-1, 0, 1):
        nf = f0 + df
        if not (0 <= nf <= 7):
            continue
        rng = range(r0 + 1, 8) if color == chess.WHITE else range(0, r0)
        for nr in rng:
            epc = board.piece_at(chess.square(nf, nr))
            if epc is not None and epc.piece_type == chess.PAWN and epc.color == opp:
                return False
    return True


def _is_protected_passed_pawn(board: chess.Board, sq: int, color: bool) -> bool:
    if not _is_passed_pawn(board, sq, color):
        return False
    f0 = chess.square_file(sq)
    r0 = chess.square_rank(sq)
    def_r = r0 - 1 if color == chess.WHITE else r0 + 1
    if not (0 <= def_r <= 7):
        return False
    for df in (-1, 1):
        nf = f0 + df
        if 0 <= nf <= 7:
            pc = board.piece_at(chess.square(nf, def_r))
            if pc is not None and pc.piece_type == chess.PAWN and pc.color == color:
                return True
    return False


def _count_passed_pawns(board: chess.Board, color: bool) -> Tuple[int, int]:
    total = 0
    protected = 0
    for sq in board.pieces(chess.PAWN, color):
        if _is_passed_pawn(board, sq, color):
            total += 1
            if _is_protected_passed_pawn(board, sq, color):
                protected += 1
    return total, protected


def _doubled_and_isolated_pawns(board: chess.Board, color: bool) -> Tuple[int, int]:
    by_file: Dict[int, int] = {}
    for sq in board.pieces(chess.PAWN, color):
        f = chess.square_file(sq)
        by_file[f] = by_file.get(f, 0) + 1
    doubled = sum(max(0, c - 1) for c in by_file.values())
    isolated = 0
    for f, cnt in by_file.items():
        if (f - 1) not in by_file and (f + 1) not in by_file:
            isolated += cnt
    return doubled, isolated


def _has_mate_in_one(board: chess.Board, side: bool) -> bool:
    """True when `side` would have a mate-in-one if it were their turn cleanly."""
    if board.turn == side:
        probe = board
    else:
        if board.is_check():
            return False
        probe = board.copy(stack=False)
        probe.turn = side
    for mv in probe.legal_moves:
        if "#" in probe.san(mv):
            return True
    return False


def _has_winning_capture_threat(board: chess.Board, attacker_side: bool) -> bool:
    probe = board if board.turn == attacker_side else board.copy(stack=False)
    if probe.turn != attacker_side:
        if probe.is_check():
            return False
        probe.turn = attacker_side
    defender_side = not attacker_side
    for mv in probe.legal_moves:
        if not probe.is_capture(mv):
            continue
        victim = probe.piece_at(mv.to_square)
        att = probe.piece_at(mv.from_square)
        if victim is None or att is None:
            continue
        vv = _mat_val(victim.piece_type)
        av = _mat_val(att.piece_type)
        if vv >= 3 and (not probe.is_attacked_by(defender_side, mv.to_square) or av < vv):
            return True
    return False


def _scan_pins_and_skewers(board: chess.Board, sq: int, mover: bool) -> Tuple[bool, bool, bool]:
    """Inspect sliding rays from `sq` belonging to `mover`: -> (is_pin, is_abs_pin, is_skewer)."""
    pc = board.piece_at(sq)
    if pc is None or pc.color != mover or pc.piece_type not in _SLIDER_DIRS:
        return False, False, False
    opp = not mover
    f0, r0 = chess.square_file(sq), chess.square_rank(sq)
    found_pin = False
    found_abs = False
    found_skewer = False
    for df, dr in _SLIDER_DIRS[pc.piece_type]:
        f, r = f0 + df, r0 + dr
        first_sq = None
        first_pc = None
        while 0 <= f <= 7 and 0 <= r <= 7:
            cur_sq = chess.square(f, r)
            cur_pc = board.piece_at(cur_sq)
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
            cur_pc = board.piece_at(cur_sq)
            if cur_pc is not None:
                second_sq = cur_sq
                second_pc = cur_pc
                break
            f += df
            r += dr
        if second_pc is None or second_pc.color != opp:
            continue

        # Pin: front piece is not King, back piece is King or higher value than front piece
        if first_pc.piece_type != chess.KING:
            if second_pc.piece_type == chess.KING:
                found_pin = True
                found_abs = True
            elif _mat_val(second_pc.piece_type) > _mat_val(first_pc.piece_type):
                found_pin = True
        # Skewer: front piece is King or high-value major (>=5) in front of piece >= 3
        if first_pc.piece_type == chess.KING:
            if _mat_val(second_pc.piece_type) >= 5 or (
                _mat_val(second_pc.piece_type) >= 3 and not board.is_attacked_by(opp, second_sq)
            ):
                found_skewer = True
        elif (
            _mat_val(first_pc.piece_type) >= 5
            and _mat_val(first_pc.piece_type) > _mat_val(second_pc.piece_type)
            and _mat_val(second_pc.piece_type) >= 3
        ):
            found_skewer = True
    return found_pin, found_abs, found_skewer


def _piece_is_trapped(board_after: chess.Board, target_sq: int, mover: bool) -> bool:
    opp = not mover
    victim = board_after.piece_at(target_sq)
    if victim is None or victim.color != opp or victim.piece_type not in (
        chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN
    ):
        return False
    v_val = _mat_val(victim.piece_type)
    # Must currently be under immediate threat
    attackers = board_after.attackers(mover, target_sq)
    if not attackers:
        return False
    min_att_val = min(_mat_val(board_after.piece_type_at(a)) for a in attackers)
    is_undefended = not board_after.is_attacked_by(opp, target_sq)
    if not (is_undefended or min_att_val < v_val):
        return False

    probe = board_after.copy(stack=False)
    probe.turn = opp
    if probe.is_check():
        return False
    for reply in probe.legal_moves:
        if reply.from_square != target_sq:
            continue
        b_esc = probe.copy(stack=False)
        cap_val = _mat_val(probe.piece_type_at(reply.to_square)) if probe.is_capture(reply) else 0
        b_esc.push(reply)
        if b_esc.is_checkmate():
            return False
        if not b_esc.is_attacked_by(mover, reply.to_square):
            return False
        esc_att_val = min(_mat_val(b_esc.piece_type_at(a)) for a in b_esc.attackers(mover, reply.to_square))
        if (not b_esc.is_attacked_by(opp, reply.to_square) and cap_val >= v_val) or (
            b_esc.is_attacked_by(opp, reply.to_square) and esc_att_val >= v_val and cap_val >= 1
        ):
            return False
    return True


def _is_outpost(board: chess.Board, sq: int, color: bool) -> bool:
    pc = board.piece_at(sq)
    if pc is None or pc.color != color or pc.piece_type not in (chess.KNIGHT, chess.BISHOP):
        return False
    f = chess.square_file(sq)
    r = chess.square_rank(sq)
    if color == chess.WHITE and r not in (4, 5):
        return False
    if color == chess.BLACK and r not in (2, 3):
        return False
    # Must be defended by a friendly pawn
    def_r = r - 1 if color == chess.WHITE else r + 1
    pawn_def = any(
        0 <= f + df <= 7
        and board.piece_at(chess.square(f + df, def_r)) == chess.Piece(chess.PAWN, color)
        for df in (-1, 1)
    )
    if not pawn_def:
        return False
    # No enemy pawn on adjacent files can push to attack it
    opp = not color
    ahead_rng = range(r + 1, 8) if color == chess.WHITE else range(0, r)
    for df in (-1, 1):
        nf = f + df
        if not (0 <= nf <= 7):
            continue
        for nr in ahead_rng:
            epc = board.piece_at(chess.square(nf, nr))
            if epc is not None and epc.piece_type == chess.PAWN and epc.color == opp:
                return False
    return True


def _connected_rooks_on_backrank(board: chess.Board, color: bool) -> bool:
    back_r = 0 if color == chess.WHITE else 7
    rooks = [sq for sq in board.pieces(chess.ROOK, color) if chess.square_rank(sq) == back_r]
    if len(rooks) < 2:
        return False
    return _ray_between_clear(board, rooks[0], rooks[1])


def _all_minors_developed(board: chess.Board, color: bool) -> bool:
    home_r = 0 if color == chess.WHITE else 7
    for sq in list(board.pieces(chess.KNIGHT, color)) + list(board.pieces(chess.BISHOP, color)):
        if chess.square_rank(sq) == home_r:
            return False
    return True


def _is_battery_pair(board: chess.Board, color: bool) -> int:
    """Count aligned Q+B or Q+R battery pairs with clear squares between."""
    queens = list(board.pieces(chess.QUEEN, color))
    if not queens:
        return 0
    cnt = 0
    q_sq = queens[0]
    qf, qr = chess.square_file(q_sq), chess.square_rank(q_sq)
    for b_sq in board.pieces(chess.BISHOP, color):
        bf, br = chess.square_file(b_sq), chess.square_rank(b_sq)
        if abs(qf - bf) == abs(qr - br) and _ray_between_clear(board, q_sq, b_sq):
            cnt += 1
    for r_sq in board.pieces(chess.ROOK, color):
        rf, rr = chess.square_file(r_sq), chess.square_rank(r_sq)
        if (qf == rf or qr == rr) and _ray_between_clear(board, q_sq, r_sq):
            cnt += 1
    return cnt


def _doubled_rooks_count(board: chess.Board, color: bool) -> int:
    rooks = list(board.pieces(chess.ROOK, color))
    if len(rooks) < 2:
        return 0
    r1, r2 = rooks[0], rooks[1]
    if (
        chess.square_file(r1) == chess.square_file(r2)
        or chess.square_rank(r1) == chess.square_rank(r2)
    ) and _ray_between_clear(board, r1, r2):
        back_r = 0 if color == chess.WHITE else 7
        if chess.square_rank(r1) == back_r and chess.square_rank(r2) == back_r and board.fullmove_number <= 16:
            return 0
        return 1
    return 0


def _endgame_class_skill(board_before: chess.Board, symbol: str) -> Optional[str]:
    if symbol not in ("+++", "!", "!!", "++"):
        return None
    non_pawn = [
        p.piece_type for p in board_before.piece_map().values()
        if p.piece_type not in (chess.PAWN, chess.KING)
    ]
    if not non_pawn:
        return "king_and_pawn_endgames"
    if all(pt == chess.QUEEN for pt in non_pawn):
        return "queen_endgames"
    if all(pt == chess.ROOK for pt in non_pawn):
        return "rook_endgames"
    if all(pt in (chess.KNIGHT, chess.BISHOP) for pt in non_pawn):
        return "knight_and_bishop_endgames"
    return None


# ---------------------------------------------------------------------------
# Move & Game Skill Detection
# ---------------------------------------------------------------------------

def detect_move_skills(
    board_before: chess.Board,
    move: chess.Move,
    symbol: str = "",
    phase: str = "middlegame",
    is_book: bool = False,
    book_count_for_side: int = 0,
    prev_move: Optional[chess.Move] = None,
    prev_was_capture: bool = False,
    brilliant_type: str = "",
    second_cp: Optional[int] = None,
    best_cp: Optional[int] = None,
    eval_before_mover: Optional[int] = None,
    eval_after_mover: Optional[int] = None,
) -> List[str]:
    """Detect all sound chess skills demonstrated by `move` on `board_before`."""
    if board_before is None or move is None or move not in board_before.legal_moves:
        return []
    if symbol in UNSOUND_SYMBOLS:
        return []

    mover = board_before.turn
    opp = not mover
    moved_pc = board_before.piece_at(move.from_square)
    moved_pt = moved_pc.piece_type if moved_pc else chess.PAWN
    moved_val = _mat_val(moved_pt)
    is_cap = board_before.is_capture(move)
    is_ep = board_before.is_en_passant(move)
    victim = (
        chess.Piece(chess.PAWN, opp)
        if is_ep
        else (board_before.piece_at(move.to_square) if is_cap else None)
    )
    v_pt = victim.piece_type if victim else None
    v_val = _mat_val(v_pt)

    board_after = board_before.copy(stack=False)
    board_after.push(move)

    detected: Set[str] = set()
    gives_check = board_after.is_check()
    is_mate = board_after.is_checkmate()

    # ---- Book Streak Skills (Openings)
    if is_book or symbol == "/":
        cnt = max(1, int(book_count_for_side or 1))
        if cnt >= 1:
            detected.add("one_book_move")
        if cnt >= 2:
            detected.add("two_book_moves")
        if cnt >= 3:
            detected.add("three_book_moves")
        if cnt >= 4:
            detected.add("four_book_moves")

    # ---- Fundamentals
    if is_cap:
        detected.add("capture")
    if is_mate:
        detected.add("checkmate")
    elif gives_check:
        detected.add("check")
    if board_before.is_castling(move):
        detected.add("castle")

    is_recap = bool(
        is_cap and prev_move is not None and prev_was_capture and move.to_square == prev_move.to_square
    )
    if is_cap and victim is not None and not is_ep:
        if v_val >= 3 and not board_before.is_attacked_by(opp, move.to_square):
            detected.add("free_piece")
        if is_recap:
            detected.add("recapture")
        if (v_val > moved_val and v_val >= 3) or (
            v_val >= 3 and not board_before.is_attacked_by(opp, move.to_square)
        ):
            detected.add("winning_capture")
        if v_val == moved_val and v_val >= 3:
            detected.add("equal_trade")
            mat_diff = C.material(board_before, mover) - C.material(board_before, opp)
            if mat_diff >= 2:
                detected.add("trading_to_simplify")

    # Defend piece (moving defender protects an attacked friendly valuable piece, or blocking)
    if not is_mate:
        for sq, pc in board_before.piece_map().items():
            if sq == move.from_square or pc.color != mover or _mat_val(pc.piece_type) < 3:
                continue
            if board_before.is_attacked_by(opp, sq):
                def_before = len(board_before.attackers(mover, sq))
                def_after = len(board_after.attackers(mover, sq))
                att_after = len(board_after.attackers(opp, sq))
                if (sq in board_after.attacks(move.to_square) and def_after > def_before) or (
                    def_before == 0 and def_after >= 1 and att_after <= def_after
                ):
                    detected.add("defend_piece")
                    break

    # Retreat / Avoids trade
    if not is_cap and moved_val >= 3:
        was_attacked = board_before.is_attacked_by(opp, move.from_square)
        safe_now = not board_after.is_attacked_by(opp, move.to_square)
        if was_attacked and safe_now:
            detected.add("retreat")
            # Avoids trade if an equal-value opponent piece could capture it before
            for a_sq in board_before.attackers(opp, move.from_square):
                apc = board_before.piece_at(a_sq)
                if apc is not None and _mat_val(apc.piece_type) == moved_val:
                    detected.add("avoids_trade")
                    break

    # ---- Openings (non-book geometric opening habits)
    fm = board_before.fullmove_number
    home_r = 0 if mover == chess.WHITE else 7
    if fm <= 15 and moved_pt in (chess.KNIGHT, chess.BISHOP):
        if chess.square_rank(move.from_square) == home_r and chess.square_rank(move.to_square) != home_r:
            detected.add("develops_piece")
    if fm <= 12 and moved_pt == chess.PAWN and not is_cap and move.to_square in _CENTER_SQUARES:
        detected.add("pawns_in_center")
    if fm <= 16 and moved_pt == chess.PAWN:
        for tsq in board_after.attacks(move.to_square):
            if tsq in _CENTER_SQUARES and board_before.piece_at(tsq) is not None and board_before.piece_at(tsq).color == opp:
                detected.add("strikes_at_center")
                break
    fian_targets = (chess.B2, chess.G2) if mover == chess.WHITE else (chess.B7, chess.G7)
    if fm <= 16 and moved_pt == chess.BISHOP and move.to_square in fian_targets:
        if chess.square_rank(move.from_square) == home_r:
            detected.add("fianchetto")
    if fm <= 22:
        if _connected_rooks_on_backrank(board_after, mover) and not _connected_rooks_on_backrank(board_before, mover):
            detected.add("connect_rooks")
        if _all_minors_developed(board_after, mover) and not _all_minors_developed(board_before, mover):
            if _connected_rooks_on_backrank(board_after, mover) or board_before.is_castling(move):
                detected.add("complete_development")

    # ---- Tactics
    # Blocking a check or sliding attack on a valuable friendly piece
    if not is_cap and not is_ep:
        if board_before.is_check():
            detected.add("blocks_attack")
        else:
            for att_sq in chess.SQUARES:
                apc = board_before.piece_at(att_sq)
                if apc is None or apc.color != opp or apc.piece_type not in (chess.BISHOP, chess.ROOK, chess.QUEEN):
                    continue
                for target_sq in board_before.attacks(att_sq):
                    tpc = board_before.piece_at(target_sq)
                    if tpc is not None and tpc.color == mover and tpc.piece_type in (
                        chess.KING, chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT
                    ):
                        if move.to_square in chess.SquareSet.between(att_sq, target_sq):
                            detected.add("blocks_attack")
                            break

    # Defend checkmate / defend tactic / counter-threat
    if not is_mate and not board_before.is_check():
        if _has_mate_in_one(board_before, opp) and not _has_mate_in_one(board_after, opp):
            detected.add("defend_checkmate")
            detected.add("defend_tactic")
        elif _has_winning_capture_threat(board_before, opp) and not _has_winning_capture_threat(board_after, opp):
            detected.add("defend_tactic")

    # Counter-threat: friendly non-pawn was attacked and stays unmoved, while our move checks or hits >=piece
    threatened_elsewhere = any(
        sq != move.from_square
        and pc.color == mover
        and _mat_val(pc.piece_type) >= 3
        and board_before.is_attacked_by(opp, sq)
        for sq, pc in board_before.piece_map().items()
    )
    if threatened_elsewhere:
        creates_strong_threat = gives_check or any(
            board_after.piece_at(tsq) is not None
            and board_after.piece_at(tsq).color == opp
            and _mat_val(board_after.piece_at(tsq).piece_type) >= 5
            for tsq in board_after.attacks(move.to_square)
        )
        if creates_strong_threat:
            detected.add("counter_threat")

    # Fork / Knight Fork / Royal Fork
    fork_targets: List[int] = []
    for tsq in board_after.attacks(move.to_square):
        tpc = board_after.piece_at(tsq)
        if tpc is None or tpc.color != opp:
            continue
        if tpc.piece_type == chess.KING:
            fork_targets.append(chess.KING)
        elif _mat_val(tpc.piece_type) >= 3:
            if (
                _mat_val(tpc.piece_type) > moved_val
                or not board_after.is_attacked_by(opp, tsq)
                or (moved_pt == chess.KNIGHT and _mat_val(tpc.piece_type) >= 5)
            ):
                fork_targets.append(tpc.piece_type)
    if len(fork_targets) >= 2:
        detected.add("fork")
        if moved_pt == chess.KNIGHT:
            detected.add("knight_fork")
        if chess.KING in fork_targets and chess.QUEEN in fork_targets:
            detected.add("royal_fork")

    # Pin / Absolute Pin / Skewer along moved slider rays
    moved_pt_after = board_after.piece_type_at(move.to_square)
    if moved_pt_after in _SLIDER_DIRS:
        p_pin, p_abs, p_skew = _scan_pins_and_skewers(board_after, move.to_square, mover)
        if p_pin:
            detected.add("pin")
        if p_abs:
            detected.add("absolute_pin")
        if p_skew:
            detected.add("skewer")

    # Discovered Attack / Discovered Check / Double Check
    opp_king_sq = board_after.king(opp)
    checkers = board_after.checkers() if gives_check else chess.SquareSet()
    if gives_check and len(checkers) >= 2:
        detected.add("double_check")
        detected.add("discovered_check")
        detected.add("discovered_attack")

    if not board_before.is_castling(move):
        for s_sq, s_pc in board_before.piece_map().items():
            if s_sq == move.from_square or s_pc.color != mover or s_pc.piece_type not in _SLIDER_DIRS:
                continue
            before_att = board_before.attacks(s_sq)
            after_att = board_after.attacks(s_sq)
            for tsq in after_att:
                if tsq in before_att or move.from_square not in chess.SquareSet.between(s_sq, tsq):
                    continue
                tpc = board_after.piece_at(tsq)
                if tpc is None or tpc.color != opp:
                    continue
                if opp_king_sq is not None and tsq == opp_king_sq:
                    detected.add("discovered_check")
                    detected.add("discovered_attack")
                elif (
                    tpc.piece_type in (chess.QUEEN, chess.ROOK)
                    or not board_after.is_attacked_by(opp, tsq)
                    or _mat_val(tpc.piece_type) > _mat_val(s_pc.piece_type)
                ):
                    detected.add("discovered_attack")

    # Attacking pinned piece / Exploiting a pin
    for tsq in board_after.attacks(move.to_square):
        tpc = board_after.piece_at(tsq)
        if tpc is not None and tpc.color == opp and tpc.piece_type not in (chess.PAWN, chess.KING):
            if board_after.is_pinned(opp, tsq):
                detected.add("attacking_pinned_piece")

    if is_cap:
        if board_before.is_pinned(opp, move.to_square):
            detected.add("exploits_pin")
        elif any(board_before.is_pinned(opp, d_sq) for d_sq in board_before.attackers(opp, move.to_square)):
            detected.add("exploits_pin")

    # Removes defender: captured victim guarded a valuable enemy target now attacked cleanly by mover
    if is_cap:
        b_rem = board_before.copy(stack=False)
        b_rem.turn = opp
        victim_defended = set()
        for tsq, tpc in board_before.piece_map().items():
            if tsq != move.to_square and tpc.color == opp and _mat_val(tpc.piece_type) >= 3:
                if move.to_square in board_before.attacks(tsq):
                    victim_defended.add(tsq)
                else:
                    # Check slider/knight reach from victim on board_before
                    vpc = board_before.piece_at(move.to_square)
                    if vpc and move.to_square in board_before.attacks(move.to_square):
                        pass
        # Use attacks mask of victim's square on board_before
        b_opp_probe = board_before.copy(stack=False)
        b_opp_probe.remove_piece_at(move.from_square)
        v_attacks = b_opp_probe.attacks(move.to_square)
        for u_sq in v_attacks:
            u_pc = board_after.piece_at(u_sq)
            if (
                u_pc is not None
                and u_pc.color == opp
                and u_pc.piece_type != chess.KING
                and _mat_val(u_pc.piece_type) >= 3
                and not board_after.is_attacked_by(opp, u_sq)
                and board_after.is_attacked_by(mover, u_sq)
            ):
                detected.add("removes_defender")
                break

    # Trapped piece
    for tsq, tpc in board_after.piece_map().items():
        if tpc.color != opp or tpc.piece_type not in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
            continue
        if _piece_is_trapped(board_after, tsq, mover):
            # Credit move if it attacks the piece or seals an adjacent escape square
            to_attacks = board_after.attacks(move.to_square)
            adj_king_dist = max(
                abs(chess.square_file(move.to_square) - chess.square_file(tsq)),
                abs(chess.square_rank(move.to_square) - chess.square_rank(tsq)),
            )
            if tsq in to_attacks or adj_king_dist <= 2 or not board_before.is_attacked_by(mover, tsq):
                detected.add("trapped_piece")
                break

    # Brilliant sacrifice / Queen sacrifice
    if symbol == "!!":
        detected.add("brilliant_sacrifice")
        if brilliant_type == "queen":
            detected.add("queen_sacrifice")

    # ---- Strategy
    if moved_pt == chess.PAWN and not is_cap:
        kicked = any(
            board_after.piece_at(tsq) is not None
            and board_after.piece_at(tsq).color == opp
            and board_after.piece_at(tsq).piece_type in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)
            for tsq in board_after.attacks(move.to_square)
        )
        if kicked:
            detected.add("kick")

    if moved_pt == chess.BISHOP:
        ray_span = len(board_after.attacks(move.to_square))
        if ray_span >= 7:
            detected.add("powerful_bishop")

    if moved_pt == chess.ROOK:
        tf = chess.square_file(move.to_square)
        of = chess.square_file(move.from_square)
        pawns_on_target_file = sum(
            1 for sq in board_after.pieces(chess.PAWN, chess.WHITE) | board_after.pieces(chess.PAWN, chess.BLACK)
            if chess.square_file(sq) == tf
        )
        pawns_on_orig_file = sum(
            1 for sq in board_before.pieces(chess.PAWN, chess.WHITE) | board_before.pieces(chess.PAWN, chess.BLACK)
            if chess.square_file(sq) == of
        )
        if pawns_on_target_file == 0 and (tf != of or pawns_on_orig_file > 0):
            detected.add("rook_to_open_file")

    if moved_pt in (chess.KNIGHT, chess.BISHOP) and _is_outpost(board_after, move.to_square, mover):
        detected.add("outpost")

    if _doubled_rooks_count(board_after, mover) > _doubled_rooks_count(board_before, mover):
        detected.add("double_rooks")

    if _is_battery_pair(board_after, mover) > _is_battery_pair(board_before, mover):
        detected.add("creates_battery")

    opp_castle_mask = chess.BB_RANK_8 if opp == chess.BLACK else chess.BB_RANK_1
    if (board_before.castling_rights & opp_castle_mask) and not (board_after.castling_rights & opp_castle_mask):
        if opp_king_sq is not None and opp_king_sq in (chess.E8 if opp == chess.BLACK else chess.E1,):
            detected.add("prevent_castling")

    # Wins tempo / Develop with tempo
    hits_tempo = False
    if not is_cap and moved_pt in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
        safe_sq = not board_after.is_attacked_by(opp, move.to_square) or len(board_after.attackers(mover, move.to_square)) >= len(board_after.attackers(opp, move.to_square))
        if safe_sq:
            for tsq in board_after.attacks(move.to_square):
                tpc = board_after.piece_at(tsq)
                if tpc is None or tpc.color != opp or tpc.piece_type == chess.PAWN:
                    continue
                if _mat_val(tpc.piece_type) > moved_val or not board_after.is_attacked_by(opp, tsq):
                    hits_tempo = True
                    break
    if hits_tempo:
        detected.add("wins_tempo")
        if "develops_piece" in detected:
            detected.add("develop_with_tempo")

    # Pawn structure skills & En Passant & Pawn Storm
    d_opp_b, i_opp_b = _doubled_and_isolated_pawns(board_before, opp)
    d_opp_a, i_opp_a = _doubled_and_isolated_pawns(board_after, opp)
    if d_opp_a > d_opp_b or i_opp_a > i_opp_b:
        detected.add("damages_opponent_pawn_structure")

    d_own_b, i_own_b = _doubled_and_isolated_pawns(board_before, mover)
    d_own_a, i_own_a = _doubled_and_isolated_pawns(board_after, mover)
    if d_own_a < d_own_b or i_own_a < i_own_b:
        detected.add("improves_pawn_structure")

    if is_ep:
        detected.add("en_passant")

    if (
        moved_pt == chess.PAWN
        and not is_cap
        and phase != "endgame"
        and fm >= 10
        and opp_king_sq is not None
    ):
        to_f, to_r = chess.square_file(move.to_square), chess.square_rank(move.to_square)
        kf = chess.square_file(opp_king_sq)
        if abs(to_f - kf) <= 2 and (to_f <= 2 or to_f >= 5):
            if (mover == chess.WHITE and to_r >= 4) or (mover == chess.BLACK and to_r <= 3):
                detected.add("pawn_storm")

    # ---- Endgames
    if move.promotion:
        detected.add("promotion")

    if is_mate:
        opp_back_r = 7 if mover == chess.WHITE else 0
        front_r = 6 if mover == chess.WHITE else 1
        mover_pt_a = board_after.piece_type_at(move.to_square)
        if opp_king_sq is not None:
            kf, kr = chess.square_file(opp_king_sq), chess.square_rank(opp_king_sq)
            # Back-rank mate
            if (
                kr == opp_back_r
                and mover_pt_a in (chess.ROOK, chess.QUEEN)
                and chess.square_rank(move.to_square) == opp_back_r
            ):
                blocked_front = sum(
                    1 for df in (-1, 0, 1)
                    if 0 <= kf + df <= 7
                    and board_after.piece_at(chess.square(kf + df, front_r)) is not None
                    and board_after.piece_at(chess.square(kf + df, front_r)).color == opp
                )
                if blocked_front >= 2:
                    detected.add("backrank_mate")
            # Ladder mate
            majors = list(board_after.pieces(chess.ROOK, mover)) + list(board_after.pieces(chess.QUEEN, mover))
            if (
                len(majors) >= 2
                and mover_pt_a in (chess.ROOK, chess.QUEEN)
                and "backrank_mate" not in detected
            ):
                edge_rank = kr in (0, 7) and chess.square_rank(move.to_square) == kr
                edge_file = kf in (0, 7) and chess.square_file(move.to_square) == kf
                adj_r = (kr - 1) if kr == 7 else ((kr + 1) if kr == 0 else -1)
                adj_f = (kf - 1) if kf == 7 else ((kf + 1) if kf == 0 else -1)
                if edge_rank and any(s != move.to_square and chess.square_rank(s) == adj_r for s in majors):
                    detected.add("ladder_mate")
                elif edge_file and any(s != move.to_square and chess.square_file(s) == adj_f for s in majors):
                    detected.add("ladder_mate")

        # Queen / Rook checkmate
        if phase == "endgame":
            if mover_pt_a == chess.QUEEN:
                detected.add("queen_checkmate")
            elif mover_pt_a == chess.ROOK and not (board_after.pieces(chess.QUEEN, chess.WHITE) | board_after.pieces(chess.QUEEN, chess.BLACK)):
                detected.add("rook_checkmate")

    # Passed pawn skills
    if moved_pt == chess.PAWN and not move.promotion:
        if _is_passed_pawn(board_after, move.to_square, mover):
            detected.add("pushes_passed_pawn")

    pp_b, prot_b = _count_passed_pawns(board_before, mover)
    pp_a, prot_a = _count_passed_pawns(board_after, mover)
    if pp_a > pp_b:
        detected.add("makes_passed_pawn")
    if prot_a > prot_b:
        detected.add("makes_protected_passed_pawn")

    # King activation & Opposition
    if phase == "endgame" and moved_pt == chess.KING:
        f_b, r_b = chess.square_file(move.from_square), chess.square_rank(move.from_square)
        f_a, r_a = chess.square_file(move.to_square), chess.square_rank(move.to_square)
        dist_b = abs(f_b - 3.5) + abs(r_b - 3.5)
        dist_a = abs(f_a - 3.5) + abs(r_a - 3.5)
        if dist_a < dist_b and not board_before.is_check():
            detected.add("activate_king")
        if opp_king_sq is not None:
            okf, okr = chess.square_file(opp_king_sq), chess.square_rank(opp_king_sq)
            if (f_a == okf and abs(r_a - okr) == 2) or (r_a == okr and abs(f_a - okf) == 2):
                detected.add("opposition")

    # Rook 7th rank & Rook behind passed pawns
    seventh_r = 6 if mover == chess.WHITE else 1
    if moved_pt == chess.ROOK:
        if chess.square_rank(move.to_square) == seventh_r and chess.square_rank(move.from_square) != seventh_r:
            detected.add("rook_to_seventh")
            other_on_7th = any(
                s != move.to_square and chess.square_rank(s) == seventh_r
                for s in board_after.pieces(chess.ROOK, mover)
            )
            if other_on_7th:
                detected.add("doubled_rooks_on_the_seventh")

        tf = chess.square_file(move.to_square)
        tr = chess.square_rank(move.to_square)
        for p_sq in board_after.pieces(chess.PAWN, mover):
            if chess.square_file(p_sq) == tf and _is_passed_pawn(board_after, p_sq, mover):
                pr = chess.square_rank(p_sq)
                if ((mover == chess.WHITE and tr < pr) or (mover == chess.BLACK and tr > pr)) and _ray_between_clear(board_after, move.to_square, p_sq):
                    detected.add("rook_behind_own_passed_pawn")
                    break
        for ep_sq in board_after.pieces(chess.PAWN, opp):
            if chess.square_file(ep_sq) == tf and _is_passed_pawn(board_after, ep_sq, opp):
                epr = chess.square_rank(ep_sq)
                # Behind opposing passed pawn (opposite of its advance direction)
                if ((opp == chess.WHITE and tr < epr) or (opp == chess.BLACK and tr > epr)) and _ray_between_clear(board_after, move.to_square, ep_sq):
                    detected.add("rook_behind_opposing_passed_pawn")
                    break

    # Specific Endgame Types
    if phase == "endgame":
        eg_skill = _endgame_class_skill(board_before, symbol)
        if eg_skill:
            detected.add(eg_skill)

    return sorted(detected, key=lambda sid: (SKILL_PRIORITY.get(sid, 999), sid))


def detect_game_skills(game, results) -> List[List[str]]:
    """Populate `r.skills` for every move result in a game and return per-ply skill lists."""
    if not game or not results:
        return []
    b = game.board()
    book_counts = {chess.WHITE: 0, chess.BLACK: 0}
    prev_move = None
    prev_was_cap = False
    out: List[List[str]] = []

    for r in results:
        try:
            mv = chess.Move.from_uci(r.uci) if r.uci else b.parse_san(r.san)
        except Exception:
            out.append([])
            continue
        if mv not in b.legal_moves:
            out.append([])
            continue

        mover = b.turn
        if r.book:
            book_counts[mover] += 1

        if not (getattr(r, "analysed", False) or r.book or r.symbol):
            r.skills = []
        else:
            eb = None
            ea = None
            if r.eval_before is not None:
                eb = r.eval_before if mover == chess.WHITE else -r.eval_before
            if r.eval_after is not None:
                ea = r.eval_after if mover == chess.WHITE else -r.eval_after
            r.skills = detect_move_skills(
                b,
                mv,
                symbol=r.symbol or "",
                phase=r.phase or "middlegame",
                is_book=bool(r.book or r.symbol == "/"),
                book_count_for_side=book_counts[mover],
                prev_move=prev_move,
                prev_was_capture=prev_was_cap,
                brilliant_type=getattr(r, "brilliant_type", "") or "",
                second_cp=getattr(r, "second_cp", None),
                eval_before_mover=eb,
                eval_after_mover=ea,
            )
        out.append(list(r.skills))
        prev_was_cap = b.is_capture(mv)
        prev_move = mv
        b.push(mv)

    return out


# ---------------------------------------------------------------------------
# Persistent Skills Progress Store
# ---------------------------------------------------------------------------

def default_skills_path() -> str:
    return os.path.join(themes.data_root(), "skills_progress.json")


class SkillsStore:
    """Tracks skill mastery points, prerequisite unlocks, and claimed game moves."""

    _STATE_ORDER = {"unlocked": 0, "mastered": 1, "locked": 2}

    def __init__(self, path: Optional[str] = None):
        self.path = path or default_skills_path()
        self.points: Dict[str, int] = {}
        self.claimed_games: Dict[str, List[str]] = {}
        self.load()

    def load(self) -> None:
        self.points = {}
        self.claimed_games = {}
        if not self.path or not os.path.isfile(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                raw_pts = data.get("points") or {}
                if isinstance(raw_pts, dict):
                    for k, v in raw_pts.items():
                        if k in SKILL_BY_ID:
                            try:
                                self.points[k] = max(0, int(v))
                            except (TypeError, ValueError):
                                pass
                raw_claimed = data.get("claimed_games") or {}
                if isinstance(raw_claimed, dict):
                    for gkey, items in raw_claimed.items():
                        if isinstance(items, list):
                            self.claimed_games[str(gkey)] = [str(x) for x in items]
        except Exception:
            pass

    def save(self) -> None:
        if not self.path:
            return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
            # Keep claimed_games bounded cleanly so file stays lightweight
            if len(self.claimed_games) > 500:
                keys = list(self.claimed_games.keys())[-500:]
                self.claimed_games = {k: self.claimed_games[k] for k in keys}
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "version": 1,
                        "points": self.points,
                        "claimed_games": self.claimed_games,
                    },
                    f,
                    indent=2,
                )
        except Exception:
            pass

    def is_mastered(self, skill_id: str) -> bool:
        sd = SKILL_BY_ID.get(skill_id)
        if sd is None:
            return False
        return int(self.points.get(skill_id, 0)) >= sd.points_to_master

    def is_unlocked(self, skill_id: str) -> bool:
        sd = SKILL_BY_ID.get(skill_id)
        if sd is None:
            return False
        if not sd.unlocked_by:
            return True
        return all(self.is_mastered(parent_id) for parent_id in sd.unlocked_by)

    def get_skill_state(self, skill_id: str) -> dict:
        sd = SKILL_BY_ID[skill_id]
        raw_pts = int(self.points.get(sd.id, 0))
        mastered = raw_pts >= sd.points_to_master
        unlocked = self.is_unlocked(sd.id)
        if mastered:
            state = "mastered"
        elif unlocked:
            state = "unlocked"
        else:
            state = "locked"
        return {
            "id": sd.id,
            "name": sd.name,
            "category": sd.category,
            "description": sd.description,
            "points": min(sd.points_to_master, raw_pts),
            "raw_points": raw_pts,
            "target": sd.points_to_master,
            "state": state,
            "is_unlocked": bool(unlocked or mastered),
            "is_mastered": mastered,
            "unlocked_by": list(sd.unlocked_by),
            "unlocked_by_names": [
                SKILL_BY_ID[p].name for p in sd.unlocked_by if p in SKILL_BY_ID
            ],
        }

    def list_skills(self, category: Optional[str] = None) -> List[dict]:
        """Return skill state dicts sorted Unlocked -> Mastered -> Locked."""
        pool = SKILLS_BY_CATEGORY.get(category, []) if (category and category != "All") else SKILLS
        items = [self.get_skill_state(s.id) for s in pool]
        items.sort(key=lambda d: self._STATE_ORDER.get(d["state"], 9))
        return items

    def summary(self) -> dict:
        all_states = [self.get_skill_state(s.id) for s in SKILLS]
        mastered = sum(1 for d in all_states if d["state"] == "mastered")
        unlocked = sum(1 for d in all_states if d["state"] == "unlocked")
        locked = sum(1 for d in all_states if d["state"] == "locked")
        total_pts = sum(int(self.points.get(s.id, 0)) for s in SKILLS)
        by_cat = {}
        for cat in SKILL_CATEGORIES:
            cat_states = [d for d in all_states if d["category"] == cat]
            by_cat[cat] = {
                "total": len(cat_states),
                "mastered": sum(1 for d in cat_states if d["state"] == "mastered"),
                "unlocked": sum(1 for d in cat_states if d["state"] == "unlocked"),
                "locked": sum(1 for d in cat_states if d["state"] == "locked"),
            }
        return {
            "total": len(SKILLS),
            "mastered": mastered,
            "unlocked": unlocked,
            "locked": locked,
            "total_points": total_pts,
            "by_category": by_cat,
        }

    def claim_move_skills(
        self,
        game_key: str,
        ply: int,
        skill_ids: List[str],
        save: bool = True,
    ) -> dict:
        """Award +1 progress point for each newly-claimed Unlocked skill on `(game_key, ply)`."""
        gkey = str(game_key or "")
        if not gkey or not skill_ids:
            return {"awarded": [], "newly_mastered": [], "newly_unlocked": []}

        claimed_list = self.claimed_games.setdefault(gkey, [])
        claimed_set = set(claimed_list)
        before_unlocked = {s.id for s in SKILLS if self.is_unlocked(s.id)}

        awarded: List[str] = []
        newly_mastered: List[str] = []

        for sid in skill_ids:
            sd = SKILL_BY_ID.get(sid)
            if sd is None:
                continue
            token = f"{ply}:{sid}"
            if token in claimed_set:
                continue
            # Only advance skills that are currently Unlocked (and not yet Mastered)
            was_unlocked = sid in before_unlocked
            was_mastered = self.is_mastered(sid)
            claimed_list.append(token)
            claimed_set.add(token)
            if was_unlocked and not was_mastered:
                self.points[sid] = int(self.points.get(sid, 0)) + 1
                awarded.append(sid)
                if self.is_mastered(sid):
                    newly_mastered.append(sid)

        after_unlocked = {s.id for s in SKILLS if self.is_unlocked(s.id)}
        newly_unlocked = [s.id for s in SKILLS if s.id in after_unlocked and s.id not in before_unlocked]

        if save and (awarded or newly_mastered or newly_unlocked):
            self.save()
        elif save and claimed_list:
            self.save()
        return {
            "awarded": awarded,
            "newly_mastered": newly_mastered,
            "newly_unlocked": newly_unlocked,
        }

    def claim_game_skills(
        self,
        game_key: str,
        results,
        tracked_colors: Optional[set] = None,
    ) -> dict:
        """Claim skill points for all sound analysed moves belonging to `tracked_colors`."""
        gkey = str(game_key or "")
        if not gkey or not results:
            return {"awarded": [], "newly_mastered": [], "newly_unlocked": []}
        allowed_colors = tracked_colors if tracked_colors is not None else {chess.WHITE, chess.BLACK}

        all_awarded: List[str] = []
        all_mastered: List[str] = []
        all_unlocked: List[str] = []

        for r in results:
            if r.color not in allowed_colors:
                continue
            if not (getattr(r, "analysed", False) or getattr(r, "book", False) or getattr(r, "symbol", "")):
                continue
            if getattr(r, "symbol", "") in UNSOUND_SYMBOLS:
                continue
            sids = getattr(r, "skills", None) or []
            if not sids:
                continue
            res = self.claim_move_skills(gkey, r.ply, sids, save=False)
            all_awarded.extend(res["awarded"])
            all_mastered.extend(res["newly_mastered"])
            all_unlocked.extend(res["newly_unlocked"])

        if all_awarded or all_mastered or all_unlocked:
            self.save()
        return {
            "awarded": all_awarded,
            "newly_mastered": list(dict.fromkeys(all_mastered)),
            "newly_unlocked": list(dict.fromkeys(all_unlocked)),
        }

    def reset(self) -> None:
        self.points = {}
        self.claimed_games = {}
        self.save()
