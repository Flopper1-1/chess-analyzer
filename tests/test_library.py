import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import chess.pgn

import analysis as A
import icons
import library as LIB


def _sample_game_and_results():
    pgn = '[White "Magnus"]\n[Black "Hikaru"]\n[Result "1-0"]\n\n1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0\n'
    game = chess.pgn.read_game(io.StringIO(pgn))
    results = [
        A.MoveResult(ply=1, color=True, san="e4", uci="e2e4", fen_before="", fen_after="", symbol="/", analysed=True, book=True, eco="C20", opening="King's Pawn"),
        A.MoveResult(ply=2, color=False, san="e5", uci="e7e5", fen_before="", fen_after="", symbol="/", analysed=True, book=True, eco="C20", opening="King's Pawn"),
        A.MoveResult(ply=3, color=True, san="Qh5", uci="d1h5", fen_before="", fen_after="", symbol="!!", analysed=True, loss=0.0, eval_after=20, eval_after_text="+0.20"),
        A.MoveResult(ply=4, color=False, san="Nc6", uci="b8c6", fen_before="", fen_after="", symbol="!!", analysed=True, loss=0.0, eval_after=20, eval_after_text="+0.20"),
        A.MoveResult(ply=5, color=True, san="Bc4", uci="f1c4", fen_before="", fen_after="", symbol="!!", analysed=True, loss=0.0, eval_after=30, eval_after_text="+0.30"),
        A.MoveResult(ply=6, color=False, san="Nf6", uci="g8f6", fen_before="", fen_after="", symbol="??", analysed=True, loss=48.0, eval_after=10000, eval_after_text="#1", best_san="g6", pv=["g6"], pv_uci=["g7g6"]),
        A.MoveResult(ply=7, color=True, san="Qxf7#", uci="h5f7", fen_before="", fen_after="", symbol="+++", analysed=True, loss=0.0, eval_after=10000, eval_after_text="#1"),
    ]
    return game, results


def test_library_roundtrip_rename_and_brilliants(tmp_path):
    db_file = str(tmp_path / "test_lib.db")
    lib = LIB.GameLibrary(db_file)
    game, results = _sample_game_and_results()

    gid1 = lib.save(game, results, A.Settings(depth=12, player_name="Magnus"))
    rows = lib.list()
    assert len(rows) == 1
    assert rows[0]["white"] == "Magnus"
    assert rows[0]["black"] == "Hikaru"
    assert rows[0]["title"] == "Magnus vs Hikaru"
    assert rows[0]["opening"] == "King's Pawn"
    assert rows[0]["brilliant_white"] == 2
    assert rows[0]["brilliant_black"] == 1
    assert rows[0]["brilliant_total"] == 3
    assert rows[0]["user_color"] == "white"
    assert rows[0]["brilliant_yours"] == 2

    # Rename game and verify search by custom name
    lib.rename(gid1, "My Favorite Trap")
    assert lib.list()[0]["title"] == "My Favorite Trap"
    assert len(lib.list("favorite trap")) == 1

    # Switch user side to Black and check brilliant_yours
    lib.set_user_color(gid1, "black")
    row_after = lib.list()[0]
    assert row_after["user_color"] == "black"
    assert row_after["brilliant_yours"] == 1

    # Saving duplicate preserves custom title and updates existing row
    results[2].symbol = "++"
    gid2 = lib.save(game, results, A.Settings(depth=16, player_name="Magnus"))
    assert gid1 == gid2
    assert len(lib.list()) == 1
    assert lib.list()[0]["title"] == "My Favorite Trap"
    assert lib.list()[0]["brilliant_total"] == 2
    assert lib.list()[0]["brilliant_yours"] == 1

    # Search filter
    assert len(lib.list("magnus")) == 1
    assert len(lib.list("caruana")) == 0

    # Load back
    loaded_game, loaded_res = lib.load(gid1)
    assert loaded_game.headers["White"] == "Magnus"
    assert [r.symbol for r in loaded_res] == [r.symbol for r in results]
    assert loaded_res[5].best_san == "g6"

    # Delete
    lib.delete(gid1)
    assert len(lib.list()) == 0


def test_mistake_and_miss_icon_mapping():
    assert icons.KEY_TO_STEM["?"] == "mistake"
    assert icons.KEY_TO_STEM["miss"] == "incorrect"
    assert os.path.exists(icons.default_path("mistake"))
    assert os.path.exists(icons.default_path("incorrect"))
    assert not os.path.exists(icons.default_path("miss"))
