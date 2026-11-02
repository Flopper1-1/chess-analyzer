"""Game analysis pipeline (GUI independent)."""
import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import chess
import chess.engine

import classify as C
from openings import OpeningBook, resource_path
from accuracy import phase_of


@dataclass
class Settings:
    scope: str = "all"          # all | mine | mine_brilliant
    side: str = "both"          # white | black | both
    player_name: str = ""
    depth: int = 16
    threads: int = 2
    hash_mb: int = 128
    engine_path: str = ""
    preset: str = "custom"
    lenient_brilliant: bool = False

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
    pv: List[str] = field(default_factory=list)   # SAN of best line from fen_before
    pv_uci: List[str] = field(default_factory=list)


def eval_text(score: Optional[chess.engine.PovScore]) -> str:
    if score is None:
        return ""
    w = score.white()
    if w.is_mate():
        m = w.mate()
        return ("#%d" % m) if m > 0 else ("-#%d" % -m)
    return "%+.2f" % (w.score() / 100.0)


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
    info = engine.analyse(board, chess.engine.Limit(depth=depth), multipv=multipv)
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

    def tracked_mover(i):
        return all_scope or boards[i].turn in tracked

    full_cache = {}

    def is_full(i):
        if i >= n:
            return False
        if i not in full_cache:
            full_cache[i] = tracked_mover(i) or (
                settings.scope == "mine_brilliant" and C.is_sacrifice(boards[i], moves[i], sac_threshold))
        return full_cache[i]

    results: List[MoveResult] = []
    infos = {}
    total = n + 1
    book_active = True

    def finalize(i):
        nonlocal book_active
        mv, b, mover = moves[i], boards[i], boards[i].turn
        r = MoveResult(ply=i + 1, color=mover, san=b.san(mv), uci=mv.uci(),
                       fen_before=b.fen(), fen_after=boards[i + 1].fen())
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
            r.eval_before = before[0]["score"].white().score(mate_score=10000)
            r.pv, r.pv_uci = pv_to_san(b, before[0].get("pv", []))
            if r.pv:
                r.best_san = r.pv[0]
        played_info = None
        for inf in before:
            pv = inf.get("pv") or []
            if pv and pv[0] == mv:
                played_info = inf
        if played_info is not None:
            after_score = played_info["score"]
        elif after:
            after_score = after[0]["score"]
        elif boards[i + 1].is_game_over():
            after_score = terminal_score(boards[i + 1])
        else:
            after_score = None
        if after_score is not None:
            r.eval_after = after_score.white().score(mate_score=10000)
            r.eval_after_text = eval_text(after_score)
        if b.legal_moves.count() == 1 and not r.book:
            # only one legal move: forced, never judged
            r.symbol, r.analysed = "forced", tracked_mover(i)
        elif before and is_full(i) and after_score is not None:
            best_cp = C.cp_of(before[0]["score"].pov(mover))
            after_cp = C.cp_of(after_score.pov(mover))
            best_wp, after_wp = C.win_pct(best_cp), C.win_pct(after_cp)
            is_best = bool(before[0].get("pv")) and before[0]["pv"][0] == mv
            loss = 0.0 if is_best else max(0.0, best_wp - after_wp)
            second_wp = C.win_pct(C.cp_of(before[1]["score"].pov(mover))) if len(before) > 1 else None
            sac = C.is_sacrifice(b, mv, sac_threshold)
            sym = C.classify(loss, is_best, after_wp, best_wp, second_wp, sac, best_wp, settings.lenient_brilliant)
            if mover not in tracked and not all_scope and sym != "!!":
                pass  # untracked opponent move: only brilliants are reported
            else:
                r.symbol, r.loss, r.analysed = sym, loss, True
                if r.book:
                    r.symbol = "/"
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
