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


def test_underpromotion_brilliant_and_categories():
    import chess
    import classify as C

    # Stalemate-avoidance rook underpromotion:
    # White king a6, pawn c7, Black king a8.
    # c8=Q is stalemate; c8=R! avoids stalemate and wins!
    b = chess.Board("k7/2P5/K7/8/8/8/8/8 w - - 0 1")
    mv_r = chess.Move.from_uci("c7c8r")
    assert C.is_underpromotion(mv_r)
    assert C.is_brilliant_underpromotion(b, mv_r, is_best=False, loss=0.5, max_loss=2.0)
    assert C.brilliant_category(b, mv_r) == "underpromotion"
    sym = C.classify(
        0.5, False, 98.0, 98.5, 50.0, False, 98.5,
        lenient=False, underpromo_brilliant=True,
    )
    assert sym == "!!"


def test_library_username_tracks_both_colors_and_breakdown(tmp_path):
    db_file = str(tmp_path / "test_user_bril.db")
    lib = LIB.GameLibrary(db_file)

    # Game 1: Holly is White (1 Queen sacrifice + 1 Underpromotion)
    pgn1 = '[White "Holly"]\n[Black "OpponentA"]\n[Result "1-0"]\n\n1. e4 e5 1-0\n'
    g1 = chess.pgn.read_game(io.StringIO(pgn1))
    res1 = [
        A.MoveResult(ply=1, color=True, san="Qxe5", uci="d1e5", fen_before="", fen_after="", symbol="!!", brilliant_type="queen", analysed=True),
        A.MoveResult(ply=2, color=True, san="c8=N+", uci="c7c8n", fen_before="", fen_after="", symbol="!!", brilliant_type="underpromotion", analysed=True),
        A.MoveResult(ply=3, color=False, san="Rxe4", uci="a8e4", fen_before="", fen_after="", symbol="!!", brilliant_type="rook", analysed=True),
    ]
    lib.save(g1, res1, A.Settings(depth=12))  # saved without player_name initially

    # Game 2: Holly is Black (1 Rook sacrifice + 1 Knight sacrifice)
    pgn2 = '[White "OpponentB"]\n[Black "Holly"]\n[Result "0-1"]\n\n1. d4 d5 0-1\n'
    g2 = chess.pgn.read_game(io.StringIO(pgn2))
    res2 = [
        A.MoveResult(ply=1, color=True, san="Bxh7+", uci="d3h7", fen_before="", fen_after="", symbol="!!", brilliant_type="bishop", analysed=True),
        A.MoveResult(ply=2, color=False, san="Rxd4", uci="d8d4", fen_before="", fen_after="", symbol="!!", brilliant_type="rook", analysed=True),
        A.MoveResult(ply=3, color=False, san="Nxf2", uci="g4f2", fen_before="", fen_after="", symbol="!!", brilliant_type="knight", analysed=True),
    ]
    lib.save(g2, res2, A.Settings(depth=12))  # saved with default user_color='white'

    # Query with player_name="Holly" — should match White in Game 1 and Black in Game 2!
    rows = lib.list(player_name="holly")
    by_white = {r["white"]: r for r in rows}

    r_g1 = by_white["Holly"]
    assert r_g1["user_color"] == "white"
    assert r_g1["matched_by_name"] is True
    assert r_g1["brilliant_yours"] == 2
    assert r_g1["brilliant_breakdown_yours"] == {
        "queen": 1, "rook": 0, "bishop": 0, "knight": 0, "underpromotion": 1,
    }

    r_g2 = by_white["OpponentB"]
    assert r_g2["user_color"] == "black"
    assert r_g2["matched_by_name"] is True
    assert r_g2["brilliant_yours"] == 2
    assert r_g2["brilliant_breakdown_yours"] == {
        "queen": 0, "rook": 1, "bishop": 0, "knight": 1, "underpromotion": 0,
    }

    # Total across library for Holly: 4 brilliants (1 queen, 1 rook, 1 knight, 1 underpromotion)
    total_yours = sum(r["brilliant_yours"] for r in rows)
    assert total_yours == 4


def test_deadlocked_eval_and_sounds():
    import chess
    import classify as C
    from openings import resource_path

    # Locked pawn chain where neither player can progress without a bad sacrifice
    locked_fen = "4k3/8/1p1p1p1p/p1p1p1p1/P1P1P1P1/1P1P1P1P/8/4K2B w - - 0 30"
    b_locked = chess.Board(locked_fen)
    assert C.is_deadlocked_position(b_locked, ["e1d2", "e8d7", "d2e1", "d7e8"]) is True

    # Open starting position is NOT deadlocked
    assert C.is_deadlocked_position(chess.Board(), ["e2e4", "e7e5"]) is False

    # Verify all 8 Default sounds exist and have no ID3 headers
    for name in ("brilliant", "Capture", "Castle", "Check", "Checkmate", "draw", "Game_load", "Move"):
        mp3_p = resource_path(os.path.join("assets", "sounds", f"{name}.mp3"))
        wav_p = resource_path(os.path.join("assets", "sounds", f"{name}.wav"))
        assert os.path.exists(mp3_p), f"Missing {mp3_p}"
        assert os.path.exists(wav_p), f"Missing {wav_p}"
        with open(mp3_p, "rb") as f:
            raw = f.read()
        assert not raw.startswith(b"ID3")
        assert raw[-128:-125] != b"TAG"
