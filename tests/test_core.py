import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import chess
import chess.pgn

import classify as C
from openings import OpeningBook
import analysis as A

ROOT = os.path.join(os.path.dirname(__file__), "..")


def test_win_pct():
    assert abs(C.win_pct(0) - 50) < 1e-6
    assert C.win_pct(300) > 70 > 30 > C.win_pct(-300)


def test_thresholds():
    f = lambda loss, best=False, sac=False, second=None: C.classify(loss, best, 50, 50, second, sac, 50)
    assert f(25) == "??"
    assert f(15) == "?"
    assert f(7) == "?!"
    assert f(3) == "+"
    assert f(1) == "++"
    assert f(0, best=True) == "+++"
    assert f(0, best=True, second=20) == "!"
    assert f(0, best=True, sac=True) == "!!"


def test_book():
    book = OpeningBook(os.path.join(ROOT, "assets", "openings"))
    b = chess.Board()
    for san in ["e4", "e5", "Nf3", "Nc6", "Bb5"]:
        b.push_san(san)
    assert "Ruy Lopez" in book.lookup(b)[1]


def test_sacrifice():
    b = chess.Board("6k1/5ppp/8/8/8/8/5PPP/3Q2K1 w - - 0 1")
    assert not C.is_sacrifice(b, chess.Move.from_uci("d1d8"))  # Qd8# no loss
    b = chess.Board("r5k1/5ppp/8/8/8/8/5PPP/3Q2K1 w - - 0 1")
    assert C.is_sacrifice(b, chess.Move.from_uci("d1d8"))  # queen hangs to rook


def test_engine_game():
    pgn = "1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0"
    # 3...Nf6?? allows mate
    game = chess.pgn.read_game(io.StringIO(pgn))
    s = A.Settings(depth=10)
    eng = A.open_engine(s)
    try:
        res = A.analyse_game(game, s, eng, OpeningBook(os.path.join(ROOT, "assets", "openings")))
    finally:
        eng.quit()
    assert len(res) == 7
    assert res[0].symbol == "/" and res[0].book
    nf6 = [r for r in res if r.san == "Nf6"][0]
    assert nf6.symbol == "??"
    assert nf6.pv


def test_scope_mine():
    pgn = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 *"
    game = chess.pgn.read_game(io.StringIO(pgn))
    s = A.Settings(depth=8, scope="mine", side="white")
    eng = A.open_engine(s)
    try:
        res = A.analyse_game(game, s, eng, None)
    finally:
        eng.quit()
    assert all(r.analysed for r in res if r.color == chess.WHITE)
    assert not any(r.analysed for r in res if r.color == chess.BLACK)


def test_accuracy():
    import accuracy as ACC
    assert ACC.move_accuracy(0) > 99
    assert ACC.move_accuracy(30) < 30
    assert ACC.rating_from_accuracy(100) == 3000
    assert 1200 < ACC.rating_from_accuracy(78) < 1400



def test_miss():
    # winning move available (75%) but played move leaves ~55%: a miss
    assert C.classify(20, False, 55, 75, None, False, 75) == 'miss'
    # throwing a win into a lost position stays a blunder
    assert C.classify(65, False, 20, 85, None, False, 85) == '??'
    # equal position, big drop: mistake not miss
    assert C.classify(15, False, 35, 50, None, False, 50) == '?'

