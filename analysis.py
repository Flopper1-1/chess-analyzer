"""Game analysis pipeline (GUI independent)."""
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

import chess
import chess.engine

import classify as C
from openings import OpeningBook, resource_path
from accuracy import phase_of

_CLK_RE = re.compile(r"\[%clk\s+(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)\]", re.IGNORECASE)
_EMT_RE = re.compile(r"\[%emt\s+(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)\]", re.IGNORECASE)


def _hms_to_seconds(h_str: Optional[str], m_str: str, s_str: str) -> float:
    h = int(h_str) if h_str else 0
    m = int(m_str)
    s = float(s_str)
    return h * 3600.0 + m * 60.0 + s


def parse_time_control(tc_str: str) -> Tuple[Optional[float], float]:
    """Parse a PGN TimeControl header (e.g. '600', '180+2', '300+0') -> (initial_sec, increment_sec)."""
    raw = (tc_str or "").strip()
    if not raw or raw in ("-", "?"):
        return None, 0.0
    first_stage = raw.split(":")[0].strip()
    if "/" in first_stage:
        parts = first_stage.split("/", 1)
        first_stage = parts[1].strip()
    inc = 0.0
    if "+" in first_stage:
        base_s, inc_s = first_stage.split("+", 1)
        try:
            inc = max(0.0, float(inc_s.strip()))
        except ValueError:
            inc = 0.0
    else:
        base_s = first_stage
    try:
        init = float(base_s.strip())
        if init <= 0:
            return None, inc
        return init, inc
    except ValueError:
        return None, 0.0


def parse_clk_comment(comment: str) -> Tuple[Optional[float], Optional[float]]:
    """Extract (%clk seconds, %emt seconds) from a PGN move comment."""
    text = comment or ""
    clk_sec = None
    emt_sec = None
    m_clk = _CLK_RE.search(text)
    if m_clk:
        try:
            clk_sec = _hms_to_seconds(m_clk.group(1), m_clk.group(2), m_clk.group(3))
        except ValueError:
            clk_sec = None
    m_emt = _EMT_RE.search(text)
    if m_emt:
        try:
            emt_sec = _hms_to_seconds(m_emt.group(1), m_emt.group(2), m_emt.group(3))
        except ValueError:
            emt_sec = None
    return clk_sec, emt_sec


def format_clock(seconds: Optional[float]) -> str:
    """Format a remaining clock time (e.g. 600 -> '10:00', 27.4 -> '0:27', 8.4 -> '0:08.4')."""
    if seconds is None:
        return ""
    sec = max(0.0, float(seconds))
    if sec >= 3600.0:
        total = int(round(sec))
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        return f"{h}:{m:02d}:{s:02d}"
    if 0.0 < sec < 20.0 and abs(sec - round(sec)) >= 0.05:
        m = int(sec // 60)
        rem = sec - m * 60
        return f"{m}:{rem:04.1f}"
    total = int(round(sec))
    m = total // 60
    s = total % 60
    return f"{m}:{s:02d}"


def format_move_time(seconds: Optional[float]) -> str:
    """Format elapsed move time for the sidebar (e.g. '0.4s', '2.1s', '1m 05s')."""
    if seconds is None:
        return ""
    sec = max(0.0, float(seconds))
    if sec < 60.0:
        return f"{sec:.1f}s"
    m = int(sec // 60)
    s = int(round(sec % 60))
    if s == 60:
        m += 1
        s = 0
    return f"{m}m {s:02d}s"


def extract_game_clocks(game) -> dict:
    """Extract per-ply clock and move-time information from a chess.pgn.Game.

    Returns a dict with:
      - 'has_clocks': bool
      - 'initial_white': str
      - 'initial_black': str
      - 'plies': list of dicts (index 0 = ply 1) with:
            'clock_seconds', 'clock_text', 'move_time', 'move_time_text',
            'white_clock', 'black_clock'
      - 'positions': list of (white_clock_str, black_clock_str) for ply 0..N
    """
    if game is None:
        return {
            "has_clocks": False,
            "initial_white": "--:--",
            "initial_black": "--:--",
            "plies": [],
            "positions": [("--:--", "--:--")],
        }
    headers = getattr(game, "headers", {}) or {}
    init_sec, inc_sec = parse_time_control(headers.get("TimeControl", ""))

    node = game
    b = game.board()
    raw_nodes = []
    has_any_clk = False
    first_clk = {chess.WHITE: None, chess.BLACK: None}
    while node.variations:
        nxt = node.variations[0]
        mover = b.turn
        clk_sec, emt_sec = parse_clk_comment(nxt.comment or "")
        if clk_sec is not None or emt_sec is not None:
            has_any_clk = True
        if clk_sec is not None and first_clk[mover] is None:
            first_clk[mover] = clk_sec
        raw_nodes.append((mover, clk_sec, emt_sec))
        b.push(nxt.move)
        node = nxt

    init_w = init_sec if init_sec is not None else first_clk[chess.WHITE]
    init_b = init_sec if init_sec is not None else first_clk[chess.BLACK]
    has_clocks = bool(has_any_clk or init_sec is not None)

    w_str = format_clock(init_w) if init_w is not None else ("--:--" if not has_clocks else "--:--")
    b_str = format_clock(init_b) if init_b is not None else ("--:--" if not has_clocks else "--:--")
    if init_w is None and first_clk[chess.WHITE] is not None:
        w_str = format_clock(first_clk[chess.WHITE])
    if init_b is None and first_clk[chess.BLACK] is not None:
        b_str = format_clock(first_clk[chess.BLACK])

    prev_clk = {chess.WHITE: init_w, chess.BLACK: init_b}
    cur_w_str = w_str
    cur_b_str = b_str
    positions = [(cur_w_str, cur_b_str)]
    plies = []

    for idx, (mover, clk_sec, emt_sec) in enumerate(raw_nodes):
        ply = idx + 1
        spent = None
        if emt_sec is not None:
            spent = max(0.0, emt_sec)
        elif clk_sec is not None and prev_clk[mover] is not None:
            prev = prev_clk[mover]
            if ply <= 2 and init_sec is None:
                spent = 0.0
            elif ply <= 2 and abs(clk_sec - prev) < 1e-6:
                spent = 0.0
            else:
                eff_inc = inc_sec if (ply > 2 or clk_sec > prev) else 0.0
                spent = max(0.0, prev + eff_inc - clk_sec)
        if clk_sec is not None:
            prev_clk[mover] = clk_sec
            c_txt = format_clock(clk_sec)
            if mover == chess.WHITE:
                cur_w_str = c_txt
            else:
                cur_b_str = c_txt
        else:
            c_txt = ""
        m_txt = format_move_time(spent) if spent is not None else ""
        plies.append({
            "clock_seconds": clk_sec,
            "clock_text": c_txt,
            "move_time": spent,
            "move_time_text": m_txt,
            "white_clock": cur_w_str,
            "black_clock": cur_b_str,
        })
        positions.append((cur_w_str, cur_b_str))

    return {
        "has_clocks": has_clocks,
        "initial_white": w_str,
        "initial_black": b_str,
        "plies": plies,
        "positions": positions,
    }


@dataclass
class Settings:
    scope: str = "all"                  # all | mine | mine_brilliant
    side: str = "both"                  # white | black | both
    player_name: str = ""
    depth: int = 16
    threads: int = 1
    hash_mb: int = 128
    engine_path: str = ""
    preset: str = "custom"
    lenient_brilliant: bool = False
    eval_formula: str = "improved"      # improved | win_prob
    annotation_system: str = "modern"   # modern | legacy
    auto_update: bool = True            # check GitHub newest stable release on startup
    auto_install_prereleases: bool = True  # auto-install newer pre-releases when running a pre-release build
    app_icon: str = "fluent"
    sound_template: str = "original"
    board_template: str = "brown_tan"
    background_template: str = "dark"
    piece_template: str = "default"
    annotation_template: str = "default"
    disable_holiday_events: bool = False
    last_holiday_event: str = ""
    pre_event_app_icon: str = "fluent"
    pre_event_board_template: str = "brown_tan"

    def matched_color(self, headers):
        """Colour matching the configured player name in the PGN headers, else None."""
        name = (self.player_name or "").strip().lower()
        if not name or not headers:
            return None
        w = name in headers.get("White", "").lower()
        b = name in headers.get("Black", "").lower()
        if w and not b:
            return chess.WHITE
        if b and not w:
            return chess.BLACK
        return None

    def tracked_colors(self, headers=None):
        side = self.side
        name = (self.player_name or "").strip().lower()
        if name and headers:
            w = name in headers.get("White", "").lower()
            b = name in headers.get("Black", "").lower()
            if w and not b:
                side = "white"
            elif b and not w:
                side = "black"
        return {"white": {chess.WHITE}, "black": {chess.BLACK}, "both": {chess.WHITE, chess.BLACK}}[side]


@dataclass
class MoveResult:
    ply: int
    color: bool
    san: str
    uci: str
    fen_before: str
    fen_after: str
    symbol: str = ""            # annotation symbol ("" = not analysed)
    analysed: bool = False
    book: bool = False
    opening: str = ""
    eco: str = ""
    loss: float = 0.0
    eval_before: Optional[int] = None   # white POV centipawns
    eval_after: Optional[int] = None
    eval_after_text: str = ""
    best_san: str = ""
    phase: str = "middlegame"
    brilliant_type: str = ""    # "" | "queen" | "rook" | "bishop" | "knight" | "underpromotion"
    second_cp: Optional[int] = None     # mover POV centipawns for 2nd best MultiPV line
    clock_seconds: Optional[float] = None
    clock_text: str = ""
    move_time: Optional[float] = None
    move_time_text: str = ""
    pv: List[str] = field(default_factory=list)   # SAN of best line from fen_before
    pv_uci: List[str] = field(default_factory=list)


def format_cp_text(cp: Optional[int], score: Optional[chess.engine.PovScore] = None) -> str:
    if score is not None:
        w = score.white()
        if w.is_mate():
            m = w.mate()
            return ("#%d" % m) if m > 0 else ("-#%d" % -m)
    if cp is None:
        return ""
    if abs(cp) >= 9000:
        return "#1" if cp > 0 else "-#1"
    if cp == 0:
        return "0.0"
    return "%+.2f" % (cp / 100.0)


def eval_text(score: Optional[chess.engine.PovScore], calibrate: bool = True) -> str:
    if score is None:
        return ""
    w = score.white()
    if w.is_mate():
        m = w.mate()
        return ("#%d" % m) if m > 0 else ("-#%d" % -m)
    raw = w.score()
    cp = C.calibrate_cp(raw) if calibrate else raw
    if cp == 0:
        return "0.0"
    return "%+.2f" % (cp / 100.0)


def find_engine(settings: Settings) -> str:
    if settings.engine_path and os.path.exists(settings.engine_path):
        return settings.engine_path
    p = resource_path(os.path.join("assets", "stockfish.exe"))
    if os.path.exists(p):
        return p
    raise FileNotFoundError("Stockfish not found")


def open_engine(settings: Settings):
    kw = {}
    if sys.platform == "win32":
        kw["creationflags"] = subprocess.CREATE_NO_WINDOW
    eng = chess.engine.SimpleEngine.popen_uci(find_engine(settings), **kw)
    try:
        eng.configure({"Threads": settings.threads, "Hash": settings.hash_mb})
    except Exception:
        pass
    return eng


def pv_to_san(board: chess.Board, pv, n=10):
    b = board.copy()
    out, ucis = [], []
    for m in pv[:n]:
        if m not in b.legal_moves:
            break
        out.append(b.san(m))
        ucis.append(m.uci())
        b.push(m)
    return out, ucis


def analyse_position(engine, board, depth, multipv=1):
    """-> list of infos (sorted best first). For terminal positions returns []."""
    if board.is_game_over(claim_draw=False):
        return []
    # Only strip move stack when a 2-fold repetition has occurred so Stockfish doesn't
    # score non-terminal 2-fold repetitions as 0.00 draws prematurely.
    fen_board = board.copy(stack=False) if board.is_repetition(2) else board.copy()
    info = engine.analyse(fen_board, chess.engine.Limit(depth=depth), multipv=multipv)
    if isinstance(info, dict):
        info = [info]
    return info


def terminal_score(board):
    """PovScore for a finished position (from white POV)."""
    if board.is_checkmate():
        return chess.engine.PovScore(chess.engine.Mate(0), board.turn)
    return chess.engine.PovScore(chess.engine.Cp(0), chess.WHITE)


def get_pov(info_or_none, board):
    if info_or_none is None:
        return terminal_score(board)
    return info_or_none["score"]


def analyse_game(game, settings: Settings, engine, book: Optional[OpeningBook] = None,
                 progress: Callable[[int, int], None] = None,
                 cancelled: Callable[[], bool] = lambda: False,
                 on_move: Callable[[MoveResult], None] = None) -> List[MoveResult]:
    """Analyse a chess.pgn.Game, streaming each finished MoveResult through on_move."""
    board = game.board()
    boards = [board.copy()]
    moves = list(game.mainline_moves())
    for m in moves:
        board.push(m)
        boards.append(board.copy())
    n = len(moves)
    tracked = settings.tracked_colors(game.headers)
    full_depth = settings.depth
    fast_depth = max(8, full_depth - 4)
    all_scope = settings.scope == "all"
    sac_threshold = 1 if settings.lenient_brilliant else 2
    use_cal = (settings.annotation_system == "modern") or (settings.eval_formula == "improved")

    def _norm_cp(raw_cp: Optional[int]) -> Optional[int]:
        if raw_cp is None:
            return None
        return C.calibrate_cp(raw_cp) if use_cal else int(raw_cp)

    def tracked_mover(i):
        return all_scope or boards[i].turn in tracked

    full_cache = {}

    def is_full(i):
        if i >= n:
            return False
        if i not in full_cache:
            full_cache[i] = tracked_mover(i) or (
                settings.scope == "mine_brilliant" and (
                    C.is_sacrifice(boards[i], moves[i], sac_threshold)
                    or C.is_underpromotion(moves[i])
                ))
        return full_cache[i]

    results: List[MoveResult] = []
    infos = {}
    total = n + 1
    book_active = True
    clock_data = extract_game_clocks(game)
    ply_clocks = clock_data.get("plies", [])

    def finalize(i):
        nonlocal book_active
        mv, b, mover = moves[i], boards[i], boards[i].turn
        c_info = ply_clocks[i] if i < len(ply_clocks) else {}
        r = MoveResult(
            ply=i + 1,
            color=mover,
            san=b.san(mv),
            uci=mv.uci(),
            fen_before=b.fen(),
            fen_after=boards[i + 1].fen(),
            clock_seconds=c_info.get("clock_seconds"),
            clock_text=c_info.get("clock_text", ""),
            move_time=c_info.get("move_time"),
            move_time_text=c_info.get("move_time_text", ""),
        )
        entry = book.lookup(boards[i + 1]) if book else None
        if book_active and entry:
            r.book = True
            r.eco, r.opening = entry
        elif book_active:
            book_active = False
        r.phase = phase_of(b, r.book)
        before = infos.get(i) or []
        after = infos.get(i + 1)
        if before:
            raw_before_pv = before[0].get("pv", [])
            if i == 0 and C.is_standard_start(b):
                r.eval_before = 0
            elif C.is_deadlocked_position(b, raw_before_pv):
                r.eval_before = 0
            else:
                r.eval_before = _norm_cp(before[0]["score"].white().score(mate_score=10000))
            r.pv, r.pv_uci = pv_to_san(b, raw_before_pv)
            if r.pv:
                r.best_san = r.pv[0]
        elif i == 0 and C.is_standard_start(b):
            r.eval_before = 0

        is_best = bool(before and before[0].get("pv") and before[0]["pv"][0] == mv)
        played_info = None
        for inf in before:
            pv = inf.get("pv") or []
            if pv and pv[0] == mv:
                played_info = inf

        after_pv = []
        # Prefer the direct evaluation of boards[i + 1] (`after[0]`) so every position has a
        # single consistent score across consecutive plies, matching Chess.com Game Review.
        if after:
            after_score = after[0]["score"]
            after_pv = after[0].get("pv") or []
        elif played_info is not None:
            after_score = played_info["score"]
            after_pv = (played_info.get("pv") or [])[1:]
        elif boards[i + 1].is_game_over():
            after_score = terminal_score(boards[i + 1])
        else:
            after_score = None

        if after_score is not None:
            if C.is_deadlocked_position(boards[i + 1], after_pv):
                r.eval_after = 0
                r.eval_after_text = "0.0"
            else:
                r.eval_after = _norm_cp(after_score.white().score(mate_score=10000))
                r.eval_after_text = format_cp_text(r.eval_after, after_score)

        if b.legal_moves.count() == 1 and not r.book:
            # only one legal move: forced, never judged
            r.symbol, r.analysed = "forced", tracked_mover(i)
        elif before and is_full(i) and after_score is not None:
            best_cp = _norm_cp(C.cp_of(before[0]["score"].pov(mover)))
            after_cp = _norm_cp(C.cp_of(after_score.pov(mover)))
            is_capture = b.is_capture(mv)
            attacks_piece = bool(
                b.piece_type_at(mv.from_square) == chess.PAWN
                and not is_capture
                and any(
                    boards[i + 1].piece_at(sq) is not None
                    and boards[i + 1].piece_at(sq).color != mover
                    and boards[i + 1].piece_at(sq).piece_type in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)
                    for sq in boards[i + 1].attacks(mv.to_square)
                )
            )
            repeats_pos = bool(
                boards[i + 1].is_repetition(2)
                or (b.halfmove_clock >= 5 and abs(best_cp) <= 25)
                or (
                    b.halfmove_clock >= 4
                    and i >= 4
                    and (mv.to_square == moves[i - 2].from_square or mv.to_square == moves[i - 4].to_square)
                )
            )
            if is_best:
                after_cp = best_cp
            elif (
                after_cp >= best_cp
                and not repeats_pos
                and (
                    r.phase == "opening"
                    or attacks_piece
                    or (
                        b.halfmove_clock < 5
                        and b.piece_type_at(mv.from_square) in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)
                        and chess.square_rank(mv.to_square) not in (0, 7)
                    )
                )
            ):
                is_best = True
                after_cp = best_cp
            best_wp, after_wp = C.win_pct(best_cp), C.win_pct(after_cp)
            loss = 0.0 if is_best else max(0.0, best_wp - after_wp)
            second_cp = _norm_cp(C.cp_of(before[1]["score"].pov(mover))) if len(before) > 1 else None
            r.second_cp = second_cp
            second_wp = C.win_pct(second_cp) if second_cp is not None else None

            if i == 0 and C.is_standard_start(b):
                before_cp = 0
                wp_before = 50.0
            elif i > 0 and results[i - 1].eval_before is not None:
                prev_w = results[i - 1].eval_before
                before_cp = prev_w if mover == chess.WHITE else -prev_w
                wp_before = C.win_pct(before_cp)
            else:
                before_cp = best_cp
                wp_before = best_wp

            is_recapture = bool(
                i > 0
                and boards[i - 1].is_capture(moves[i - 1])
                and mv.to_square == moves[i - 1].to_square
            )
            victim = b.piece_at(mv.to_square) if is_capture else None
            pre_attacked_free_piece = bool(
                is_capture
                and victim is not None
                and victim.piece_type in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)
                and not b.is_attacked_by(not mover, mv.to_square)
                and i >= 2
                and boards[i - 1].piece_at(mv.to_square) == victim
                and boards[i - 1].is_attacked_by(mover, mv.to_square)
            )
            pendulum_return = bool(
                i >= 2
                and not is_capture
                and mv.from_square == moves[i - 2].to_square
                and mv.to_square == moves[i - 2].from_square
            )
            prev_critical = bool(i > 0 and results[i - 1].symbol in ("!!", "!"))
            mat_diff_before = C.material(b, mover) - C.material(b, not mover)
            already_overwhelming = bool(
                mat_diff_before >= 7
                and wp_before >= 80.0
                and (second_wp is None or second_wp >= 75.0)
            )
            in_check = b.is_check()
            gives_check = boards[i + 1].is_check()
            sac = C.is_sacrifice(b, mv, sac_threshold)
            max_loss = 5.0 if settings.lenient_brilliant else 2.5
            underpromo = C.is_brilliant_underpromotion(
                b, mv, is_best, loss, max_loss, second_wp=second_wp, best_wp=best_wp
            )
            sym = C.classify(
                loss, is_best, after_wp, best_wp, second_wp, sac, wp_before,
                lenient=settings.lenient_brilliant,
                underpromo_brilliant=underpromo,
                system=settings.annotation_system,
                cp_before=before_cp,
                cp_after=after_cp,
                best_cp=best_cp,
                is_recapture=is_recapture,
                in_check=in_check,
                gives_check=gives_check,
                phase=r.phase,
                repeats_position=repeats_pos,
                is_capture=is_capture,
                pre_attacked_free_piece=pre_attacked_free_piece,
                pendulum_return=pendulum_return,
                attacks_piece=attacks_piece,
                prev_critical=prev_critical,
                already_overwhelming=already_overwhelming,
            )
            if mover not in tracked and not all_scope and sym != "!!":
                pass  # untracked opponent move: only brilliants are reported
            else:
                r.symbol, r.loss, r.analysed = sym, loss, True
                r.brilliant_type = ""
                if r.book:
                    r.symbol = "/"
                elif r.symbol == "!!":
                    r.brilliant_type = C.brilliant_category(b, mv)

                # Chess.com Game Review continuity: when a non-book move is the engine's top move
                # (Best, Great, or Brilliant), the position's evaluation remains unchanged from the
                # evaluation entering the move.
                if (
                    (is_best or r.symbol == "!!")
                    and not r.book
                    and r.symbol in ("+++", "!", "!!")
                    and i > 0
                    and results[i - 1].eval_after is not None
                    and not C.is_deadlocked_position(boards[i + 1], after_pv)
                ):
                    r.eval_before = results[i - 1].eval_after
                    r.eval_after = results[i - 1].eval_after
                    r.eval_after_text = results[i - 1].eval_after_text
        elif r.book and tracked_mover(i):
            r.symbol, r.analysed = "/", True
        return r

    for i in range(n + 1):
        if cancelled():
            return results
        b = boards[i]
        if is_full(i) or (i == n and all_scope):
            infos[i] = analyse_position(engine, b, full_depth, 2)
        elif i > 0 and tracked_mover(i - 1):
            infos[i] = analyse_position(engine, b, fast_depth, 1)
        else:
            infos[i] = []
        if i >= 1:
            r = finalize(i - 1)
            results.append(r)
            infos.pop(i - 2, None)
            if on_move:
                on_move(r)
        if progress:
            progress(i + 1, total)
    return results


def reclassify_results(game, results: List[MoveResult], settings: Settings) -> None:
    """Re-evaluate move symbols in-place when switching between 'modern' and 'legacy'
    annotation systems or toggling 'lenient_brilliant', without re-running Stockfish."""
    if not game or not results:
        return
    sac_threshold = 1 if settings.lenient_brilliant else 2
    max_loss = 5.0 if settings.lenient_brilliant else 2.5
    tracked = settings.tracked_colors(game.headers)
    all_scope = settings.scope == "all"

    b = game.board()
    boards_hist = [b.copy()]
    moves_hist = []
    prev_move = None
    prev_was_capture = False
    for i, r in enumerate(results):
        try:
            mv = chess.Move.from_uci(r.uci) if r.uci else b.parse_san(r.san)
        except Exception:
            break
        mover = b.turn
        b_next = b.copy()
        b_next.push(mv)
        if i == 0 and C.is_standard_start(b):
            r.eval_before = 0
        if b.legal_moves.count() == 1 and not r.book:
            r.symbol = "forced"
            r.brilliant_type = ""
        elif r.book:
            if all_scope or mover in tracked:
                r.symbol = "/"
                r.brilliant_type = ""
        elif r.analysed and r.eval_after is not None:
            raw_best_w = r.eval_before if r.eval_before is not None else r.eval_after
            best_cp = raw_best_w if mover == chess.WHITE else -raw_best_w
            after_cp = r.eval_after if mover == chess.WHITE else -r.eval_after
            is_capture = b.is_capture(mv)
            attacks_piece = bool(
                b.piece_type_at(mv.from_square) == chess.PAWN
                and not is_capture
                and any(
                    b_next.piece_at(sq) is not None
                    and b_next.piece_at(sq).color != mover
                    and b_next.piece_at(sq).piece_type in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)
                    for sq in b_next.attacks(mv.to_square)
                )
            )
            repeats_pos = bool(
                b_next.is_repetition(2)
                or (b.halfmove_clock >= 5 and abs(best_cp) <= 25)
            )
            is_best = (
                (r.best_san == r.san)
                or (bool(r.pv_uci) and r.pv_uci[0] == r.uci)
                or (r.loss == 0.0 and not r.best_san)
                or (r.loss == 0.0 and attacks_piece and not repeats_pos)
            )
            if is_best:
                after_cp = best_cp
            after_wp = C.win_pct(after_cp)
            best_wp = max(after_wp + r.loss, C.win_pct(best_cp))
            second_wp = C.win_pct(r.second_cp) if r.second_cp is not None else None
            if i == 0 and C.is_standard_start(b):
                before_cp = 0
                wp_before = 50.0
            elif i > 0 and results[i - 1].eval_before is not None:
                prev_w = results[i - 1].eval_before
                before_cp = prev_w if mover == chess.WHITE else -prev_w
                wp_before = C.win_pct(before_cp)
            else:
                before_cp = best_cp
                wp_before = best_wp

            is_recapture = bool(prev_move is not None and prev_was_capture and mv.to_square == prev_move.to_square)
            victim = b.piece_at(mv.to_square) if is_capture else None
            pre_attacked_free_piece = bool(
                is_capture
                and victim is not None
                and victim.piece_type in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)
                and not b.is_attacked_by(not mover, mv.to_square)
                and i >= 2
                and boards_hist[i - 1].piece_at(mv.to_square) == victim
                and boards_hist[i - 1].is_attacked_by(mover, mv.to_square)
            )
            pendulum_return = bool(
                i >= 2
                and not is_capture
                and mv.from_square == moves_hist[i - 2].to_square
                and mv.to_square == moves_hist[i - 2].from_square
            )
            prev_critical = bool(i > 0 and results[i - 1].symbol in ("!!", "!"))
            mat_diff_before = C.material(b, mover) - C.material(b, not mover)
            already_overwhelming = bool(
                mat_diff_before >= 7
                and wp_before >= 80.0
                and (second_wp is None or second_wp >= 75.0)
            )
            in_check = b.is_check()
            gives_check = b_next.is_check()
            sac = C.is_sacrifice(b, mv, sac_threshold)
            underpromo = C.is_brilliant_underpromotion(
                b, mv, is_best, r.loss, max_loss, second_wp=second_wp, best_wp=best_wp
            )
            sym = C.classify(
                r.loss, is_best, after_wp, best_wp, second_wp, sac, wp_before,
                lenient=settings.lenient_brilliant,
                underpromo_brilliant=underpromo,
                system=settings.annotation_system,
                cp_before=before_cp,
                cp_after=after_cp,
                best_cp=best_cp,
                is_recapture=is_recapture,
                in_check=in_check,
                gives_check=gives_check,
                phase=r.phase,
                repeats_position=repeats_pos,
                is_capture=is_capture,
                pre_attacked_free_piece=pre_attacked_free_piece,
                pendulum_return=pendulum_return,
                attacks_piece=attacks_piece,
                prev_critical=prev_critical,
                already_overwhelming=already_overwhelming,
            )
            r.symbol = sym
            r.brilliant_type = C.brilliant_category(b, mv) if sym == "!!" else ""
        prev_was_capture = b.is_capture(mv)
        prev_move = mv
        moves_hist.append(mv)
        b.push(mv)
        boards_hist.append(b.copy())


def best_line(engine, fen: str, depth: int, multipv=3):
    """On-demand: list of (eval_text, [SAN...], [uci...]) lines for a position."""
    b = chess.Board(fen)
    out = []
    for inf in analyse_position(engine, b, depth, multipv):
        san, ucis = pv_to_san(b, inf.get("pv", []), 12)
        out.append((eval_text(inf["score"]), san, ucis))
    return out


def preset_values(name):
    """(depth, threads, hash_mb) for a preset name, tuned to this machine."""
    cpu = os.cpu_count() or 2
    if name == "low":
        return 10, 1, 64
    if name == "medium":
        return 16, max(1, min(4, cpu // 2)), 256
    if name == "high":
        return 22, max(1, min(16, cpu - 1)), 1024
    return None


def auto_resources(depth):
    """(threads, hash_mb) scaled to a search depth and this machine."""
    cpu = os.cpu_count() or 2
    frac = max(0.0, min(1.0, (depth - 6) / 24.0))
    max_threads = max(1, min(16, cpu - 1))
    threads = max(1, round(1 + frac * (max_threads - 1)))
    h = 32 * 2 ** ((depth - 6) / 4.8)          # 32 MB at depth 6 .. 1 GB at depth 30
    hash_mb = 1 << max(4, min(10, round(__import__("math").log2(h))))
    hash_mb = max(16, min(1024, hash_mb))
    return threads, hash_mb
