"""Opening book lookup using the lichess chess-openings TSV files."""
import csv
import io
import os
import sys
import chess
import chess.pgn


def resource_path(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def _key(board):
    # position key independent of move counters
    return board.epd()


class OpeningBook:
    def __init__(self, folder=None):
        self.table = {}
        folder = folder or resource_path(os.path.join("assets", "openings"))
        for letter in "abcde":
            path = os.path.join(folder, letter + ".tsv")
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as f:
                for row in csv.DictReader(f, delimiter="\t"):
                    try:
                        game = chess.pgn.read_game(io.StringIO(row["pgn"]))
                        b = game.board()
                        for m in game.mainline_moves():
                            b.push(m)
                    except Exception:
                        continue
                    self.table[_key(b)] = (row["eco"], row["name"])

    def lookup(self, board):
        """(eco, name) if the position is a known opening position else None."""
        return self.table.get(_key(board))
