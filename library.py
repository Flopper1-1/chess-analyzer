"""In-app SQLite game library stored in %APPDATA%\\ChessAnalyzer\\library.db."""
from contextlib import closing
from dataclasses import asdict
from datetime import datetime
import hashlib
import io
import json
import os
import sqlite3
from typing import List, Optional, Tuple

import chess
import chess.pgn

import accuracy as ACC
import analysis as A
import classify as C

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE,
    saved_at TEXT,
    title TEXT DEFAULT '',
    white TEXT,
    black TEXT,
    result TEXT,
    date TEXT,
    event TEXT,
    eco TEXT,
    opening TEXT,
    moves INTEGER,
    white_acc REAL,
    black_acc REAL,
    white_rating INTEGER,
    black_rating INTEGER,
    brilliant_white INTEGER DEFAULT 0,
    brilliant_black INTEGER DEFAULT 0,
    user_color TEXT DEFAULT 'white',
    favorite INTEGER DEFAULT 0,
    new_years_colors TEXT DEFAULT '',
    pgn TEXT,
    analysis TEXT,
    engine TEXT
);
"""


def default_db_path() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    folder = os.path.join(base, "ChessAnalyzer")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "library.db")


def game_key(game: chess.pgn.Game) -> str:
    h = game.headers
    exporter = chess.pgn.StringExporter(headers=False, variations=False, comments=False)
    movetext = game.accept(exporter).strip()
    ident = "|".join([
        h.get("White", "?").strip(),
        h.get("Black", "?").strip(),
        h.get("Date", "").strip(),
        h.get("FEN", "").strip(),
        movetext,
    ])
    return hashlib.sha1(ident.encode("utf-8")).hexdigest()


def resolve_user_color(white: str, black: str, player_name: str = "",
                       fallback_color: str = "white") -> Tuple[str, bool]:
    """Resolve which color ('white' or 'black') belongs to the user.

    If `player_name` matches either `white` or `black` (case-insensitive exact match
    first, then substring match), returns that color and `True`. Otherwise returns
    `(fallback_color, False)`.
    """
    fb = "black" if (fallback_color or "").strip().lower() == "black" else "white"
    pname = (player_name or "").strip().lower()
    w = (white or "").strip().lower()
    b = (black or "").strip().lower()
    if pname:
        # 1. Exact case-insensitive match
        w_exact = (w == pname)
        b_exact = (b == pname)
        if w_exact and not b_exact:
            return "white", True
        if b_exact and not w_exact:
            return "black", True
        # 2. Substring match
        w_sub = pname in w
        b_sub = pname in b
        if w_sub and not b_sub:
            return "white", True
        if b_sub and not w_sub:
            return "black", True
    return fb, False


def _empty_breakdown() -> dict:
    return {cat: 0 for cat in C.BRILLIANT_CATEGORIES}


def _extract_brilliants(analysis_json: str) -> dict:
    """Parse serialized analysis JSON and return brilliant counts & category breakdowns."""
    bd_white = _empty_breakdown()
    bd_black = _empty_breakdown()
    bw = 0
    bb = 0
    try:
        raw = json.loads(analysis_json or "{}")
        items = raw.get("results", []) if isinstance(raw, dict) else raw
        for it in items:
            if it.get("symbol") != "!!":
                continue
            is_white = bool(it.get("color"))
            cat = (it.get("brilliant_type") or "").strip().lower()
            if cat not in C.BRILLIANT_CATEGORIES:
                fen_before = it.get("fen_before") or ""
                uci = it.get("uci") or ""
                if fen_before and uci:
                    try:
                        cat = C.brilliant_category(chess.Board(fen_before), chess.Move.from_uci(uci))
                    except Exception:
                        cat = "knight"
                else:
                    cat = "knight"
            if is_white:
                bw += 1
                bd_white[cat] = bd_white.get(cat, 0) + 1
            else:
                bb += 1
                bd_black[cat] = bd_black.get(cat, 0) + 1
    except Exception:
        pass
    return {
        "bw": bw,
        "bb": bb,
        "white": bd_white,
        "black": bd_black,
    }


class GameLibrary:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or default_db_path()
        with self._conn() as conn:
            with conn:
                conn.executescript(SCHEMA)
                self._migrate(conn)

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(games)").fetchall()}
        migrations = [
            ("title", "TEXT DEFAULT ''"),
            ("brilliant_white", "INTEGER DEFAULT 0"),
            ("brilliant_black", "INTEGER DEFAULT 0"),
            ("user_color", "TEXT DEFAULT 'white'"),
            ("favorite", "INTEGER DEFAULT 0"),
            ("new_years_colors", "TEXT DEFAULT ''"),
        ]
        added = False
        for col, spec in migrations:
            if col not in cols:
                conn.execute(f"ALTER TABLE games ADD COLUMN {col} {spec}")
                added = True
        if added:
            rows = conn.execute("SELECT id, white, black, title, analysis FROM games").fetchall()
            for row in rows:
                title = (row["title"] or "").strip() or f"{row['white'] or '?'} vs {row['black'] or '?'}"
                bw, bb = 0, 0
                try:
                    raw = json.loads(row["analysis"] or "{}")
                    items = raw.get("results", []) if isinstance(raw, dict) else raw
                    for it in items:
                        if it.get("symbol") == "!!":
                            if it.get("color"):
                                bw += 1
                            else:
                                bb += 1
                except Exception:
                    pass
                conn.execute(
                    "UPDATE games SET title = ?, brilliant_white = ?, brilliant_black = ? WHERE id = ?",
                    (title, bw, bb, row["id"]),
                )

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return closing(conn)

    def save(self, game: chess.pgn.Game, results: List[A.MoveResult],
             settings: Optional[A.Settings] = None,
             title: Optional[str] = None,
             user_color: Optional[str] = None,
             new_years_colors: Optional[List[str]] = None) -> int:
        key = game_key(game)
        h = game.headers
        white = h.get("White", "?") or "?"
        black = h.get("Black", "?") or "?"
        result = h.get("Result", "*") or "*"
        date = h.get("Date", "") or ""
        event = h.get("Event", "") or ""

        eco, opening = h.get("ECO", ""), h.get("Opening", "")
        for r in results:
            if r.opening:
                eco, opening = r.eco, r.opening

        summ = ACC.summarize(results) if results else {
            chess.WHITE: {"overall": None, "rating": None},
            chess.BLACK: {"overall": None, "rating": None},
        }
        w_acc = summ[chess.WHITE]["overall"]
        b_acc = summ[chess.BLACK]["overall"]
        w_rat = summ[chess.WHITE]["rating"]
        b_rat = summ[chess.BLACK]["rating"]

        for r in results:
            if r.symbol == "!!" and not r.brilliant_type:
                try:
                    r.brilliant_type = C.brilliant_category(
                        chess.Board(r.fen_before), chess.Move.from_uci(r.uci)
                    )
                except Exception:
                    r.brilliant_type = "knight"

        bw = sum(1 for r in results if r.symbol == "!!" and r.color == chess.WHITE)
        bb = sum(1 for r in results if r.symbol == "!!" and r.color == chess.BLACK)

        if user_color not in ("white", "black"):
            user_color = None
            if settings is not None:
                resolved_uc, matched = resolve_user_color(white, black, settings.player_name, "")
                if matched:
                    user_color = resolved_uc
                elif settings.side in ("white", "black"):
                    user_color = settings.side
            user_color = user_color or "white"

        exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
        pgn_text = game.accept(exporter)
        payload = json.dumps({"version": 1, "results": [asdict(r) for r in results]})
        engine_desc = (
            f"Stockfish 19, depth {settings.depth}, scope {settings.scope}"
            if settings else "Stockfish 19"
        )
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        ny_json = json.dumps(new_years_colors) if new_years_colors else ""

        with self._conn() as conn:
            with conn:
                existing = conn.execute(
                    "SELECT title, user_color, new_years_colors FROM games WHERE key = ?", (key,)
                ).fetchone()
                if not ny_json and existing and (existing["new_years_colors"] or "").strip():
                    ny_json = existing["new_years_colors"]
                resolved_title = (title or "").strip()
                if not resolved_title:
                    if existing and (existing["title"] or "").strip():
                        resolved_title = existing["title"].strip()
                    else:
                        resolved_title = f"{white} vs {black}"
                conn.execute(
                    """
                    INSERT INTO games (
                        key, saved_at, title, white, black, result, date, event,
                        eco, opening, moves, white_acc, black_acc, white_rating, black_rating,
                        brilliant_white, brilliant_black, user_color, new_years_colors,
                        pgn, analysis, engine
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        saved_at=excluded.saved_at,
                        title=excluded.title,
                        white=excluded.white,
                        black=excluded.black,
                        result=excluded.result,
                        date=excluded.date,
                        event=excluded.event,
                        eco=excluded.eco,
                        opening=excluded.opening,
                        moves=excluded.moves,
                        white_acc=excluded.white_acc,
                        black_acc=excluded.black_acc,
                        white_rating=excluded.white_rating,
                        black_rating=excluded.black_rating,
                        brilliant_white=excluded.brilliant_white,
                        brilliant_black=excluded.brilliant_black,
                        user_color=excluded.user_color,
                        new_years_colors=excluded.new_years_colors,
                        pgn=excluded.pgn,
                        analysis=excluded.analysis,
                        engine=excluded.engine
                    """,
                    (
                        key, now, resolved_title, white, black, result, date, event,
                        eco, opening, (len(results) + 1) // 2,
                        w_acc, b_acc, w_rat, b_rat,
                        bw, bb, user_color, ny_json,
                        pgn_text, payload, engine_desc,
                    ),
                )
            row = conn.execute("SELECT id FROM games WHERE key = ?", (key,)).fetchone()
            return int(row["id"])

    def rename(self, game_id: int, new_title: str) -> None:
        clean = (new_title or "").strip()
        if not clean:
            return
        with self._conn() as conn:
            with conn:
                conn.execute("UPDATE games SET title = ? WHERE id = ?", (clean, game_id))

    def set_user_color(self, game_id: int, color: str) -> None:
        if color not in ("white", "black"):
            return
        with self._conn() as conn:
            with conn:
                conn.execute("UPDATE games SET user_color = ? WHERE id = ?", (color, game_id))

    def set_favorite(self, game_id: int, favorite: bool) -> None:
        val = 1 if favorite else 0
        with self._conn() as conn:
            with conn:
                conn.execute("UPDATE games SET favorite = ? WHERE id = ?", (val, game_id))

    def toggle_favorite(self, game_id: int) -> bool:
        with self._conn() as conn:
            with conn:
                row = conn.execute("SELECT favorite FROM games WHERE id = ?", (game_id,)).fetchone()
                if row is None:
                    return False
                new_val = 0 if bool(row["favorite"]) else 1
                conn.execute("UPDATE games SET favorite = ? WHERE id = ?", (new_val, game_id))
                return bool(new_val)

    def list(
        self,
        search: str = "",
        player_name: str = "",
        favorites_only: bool = False,
        sort_by: str = "recent",
    ) -> List[dict]:
        q = (search or "").strip().lower()
        sql = """
            SELECT id, saved_at, title, white, black, result, date, event,
                   eco, opening, moves, white_acc, black_acc, white_rating, black_rating,
                   brilliant_white, brilliant_black, user_color, favorite, analysis, engine
            FROM games
        """
        params: tuple = ()
        if q:
            like = f"%{q}%"
            sql += """
                WHERE lower(title) LIKE ? OR lower(white) LIKE ? OR lower(black) LIKE ?
                   OR lower(opening) LIKE ? OR lower(eco) LIKE ? OR lower(event) LIKE ?
            """
            params = (like, like, like, like, like, like)
        sql += " ORDER BY saved_at DESC, id DESC"
        with self._conn() as conn:
            out = []
            for r in conn.execute(sql, params).fetchall():
                d = dict(r)
                analysis_raw = d.pop("analysis", None) or "{}"
                binfo = _extract_brilliants(analysis_raw)
                bw = binfo["bw"]
                bb = binfo["bb"]
                # Fallback to stored columns only if analysis JSON had no items
                if bw == 0 and bb == 0:
                    bw = int(d.get("brilliant_white") or 0)
                    bb = int(d.get("brilliant_black") or 0)
                d["brilliant_white"] = bw
                d["brilliant_black"] = bb
                uc, matched_by_name = resolve_user_color(
                    d.get("white", ""),
                    d.get("black", ""),
                    player_name,
                    d.get("user_color") or "white",
                )
                d["title"] = (d.get("title") or "").strip() or f"{d.get('white', '?')} vs {d.get('black', '?')}"
                d["favorite"] = bool(d.get("favorite"))
                d["brilliant_total"] = bw + bb
                d["brilliant_yours"] = bb if uc == "black" else bw
                d["brilliant_opponent"] = bw if uc == "black" else bb
                d["user_color"] = uc
                d["matched_by_name"] = matched_by_name
                d["brilliant_breakdown_white"] = binfo["white"]
                d["brilliant_breakdown_black"] = binfo["black"]
                d["brilliant_breakdown_yours"] = binfo["black"] if uc == "black" else binfo["white"]
                d["brilliant_breakdown_opponent"] = binfo["white"] if uc == "black" else binfo["black"]
                d["brilliant_breakdown_total"] = {
                    cat: binfo["white"][cat] + binfo["black"][cat]
                    for cat in C.BRILLIANT_CATEGORIES
                }
                if favorites_only and not d["favorite"]:
                    continue
                out.append(d)

            mode = (sort_by or "recent").strip().lower()
            if mode == "most_brilliant":
                out.sort(
                    key=lambda x: (x["brilliant_yours"], x["brilliant_total"], x["id"]),
                    reverse=True,
                )
            elif mode == "least_brilliant":
                out.sort(
                    key=lambda x: (x["brilliant_yours"], x["brilliant_total"], -x["id"]),
                )
            elif mode == "opponent_brilliant":
                out.sort(
                    key=lambda x: (x["brilliant_opponent"], x["brilliant_total"], x["id"]),
                    reverse=True,
                )
            return out

    def load(self, game_id: int) -> Tuple[chess.pgn.Game, List[A.MoveResult]]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT title, pgn, analysis FROM games WHERE id = ?", (game_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"Game id {game_id} not found")
        game = chess.pgn.read_game(io.StringIO(row["pgn"]))
        clk_data = A.extract_game_clocks(game)
        ply_clocks = clk_data.get("plies", [])
        raw = json.loads(row["analysis"])
        items = raw.get("results", []) if isinstance(raw, dict) else raw
        fields = set(A.MoveResult.__dataclass_fields__.keys())
        results = []
        for idx, item in enumerate(items):
            mr = A.MoveResult(**{k: v for k, v in item.items() if k in fields})
            if mr.symbol == "!!" and not mr.brilliant_type:
                try:
                    mr.brilliant_type = C.brilliant_category(
                        chess.Board(mr.fen_before), chess.Move.from_uci(mr.uci)
                    )
                except Exception:
                    mr.brilliant_type = "knight"
            if idx < len(ply_clocks):
                ci = ply_clocks[idx]
                if mr.clock_seconds is None and ci.get("clock_seconds") is not None:
                    mr.clock_seconds = ci["clock_seconds"]
                if not mr.clock_text and ci.get("clock_text"):
                    mr.clock_text = ci["clock_text"]
                if mr.move_time is None and ci.get("move_time") is not None:
                    mr.move_time = ci["move_time"]
                if not mr.move_time_text and ci.get("move_time_text"):
                    mr.move_time_text = ci["move_time_text"]
            results.append(mr)
        return game, results

    def get_new_years_colors(self, game_id: int) -> List[str]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT new_years_colors FROM games WHERE id = ?", (game_id,)
            ).fetchone()
        if row is None or not (row["new_years_colors"] or "").strip():
            return []
        try:
            vals = json.loads(row["new_years_colors"])
            return [str(v) for v in vals] if isinstance(vals, list) else []
        except Exception:
            return []

    def set_new_years_colors(self, game_id: int, colors: List[str]) -> None:
        with self._conn() as conn:
            with conn:
                conn.execute(
                    "UPDATE games SET new_years_colors = ? WHERE id = ?",
                    (json.dumps(list(colors)), game_id),
                )

    def delete(self, game_id: int) -> None:
        with self._conn() as conn:
            with conn:
                conn.execute("DELETE FROM games WHERE id = ?", (game_id,))
