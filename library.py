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
             user_color: Optional[str] = None) -> int:
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

        bw = sum(1 for r in results if r.symbol == "!!" and r.color == chess.WHITE)
        bb = sum(1 for r in results if r.symbol == "!!" and r.color == chess.BLACK)

        if user_color not in ("white", "black"):
            user_color = None
            if settings is not None:
                mc = settings.matched_color(h)
                if mc == chess.WHITE:
                    user_color = "white"
                elif mc == chess.BLACK:
                    user_color = "black"
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

        with self._conn() as conn:
            with conn:
                existing = conn.execute(
                    "SELECT title, user_color FROM games WHERE key = ?", (key,)
                ).fetchone()
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
                        brilliant_white, brilliant_black, user_color,
                        pgn, analysis, engine
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        pgn=excluded.pgn,
                        analysis=excluded.analysis,
                        engine=excluded.engine
                    """,
                    (
                        key, now, resolved_title, white, black, result, date, event,
                        eco, opening, (len(results) + 1) // 2,
                        w_acc, b_acc, w_rat, b_rat,
                        bw, bb, user_color,
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

    def list(self, search: str = "") -> List[dict]:
        q = (search or "").strip().lower()
        sql = """
            SELECT id, saved_at, title, white, black, result, date, event,
                   eco, opening, moves, white_acc, black_acc, white_rating, black_rating,
                   brilliant_white, brilliant_black, user_color, engine
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
                bw = int(d.get("brilliant_white") or 0)
                bb = int(d.get("brilliant_black") or 0)
                uc = (d.get("user_color") or "white").lower()
                d["title"] = (d.get("title") or "").strip() or f"{d.get('white', '?')} vs {d.get('black', '?')}"
                d["brilliant_total"] = bw + bb
                d["brilliant_yours"] = bb if uc == "black" else bw
                d["user_color"] = "black" if uc == "black" else "white"
                out.append(d)
            return out

    def load(self, game_id: int) -> Tuple[chess.pgn.Game, List[A.MoveResult]]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT title, pgn, analysis FROM games WHERE id = ?", (game_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"Game id {game_id} not found")
        game = chess.pgn.read_game(io.StringIO(row["pgn"]))
        raw = json.loads(row["analysis"])
        items = raw.get("results", []) if isinstance(raw, dict) else raw
        fields = set(A.MoveResult.__dataclass_fields__.keys())
        results = [
            A.MoveResult(**{k: v for k, v in item.items() if k in fields})
            for item in items
        ]
        return game, results

    def delete(self, game_id: int) -> None:
        with self._conn() as conn:
            with conn:
                conn.execute("DELETE FROM games WHERE id = ?", (game_id,))
