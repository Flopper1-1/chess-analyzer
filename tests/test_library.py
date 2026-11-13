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


def test_eval_bar_formulas_and_start_of_game_zero():
    import chess
    import classify as C

    s = A.Settings()
    assert s.eval_formula == "improved"
    assert s.annotation_system == "modern"

    # Standard starting position is strictly 50.0% (0.0) even if engine gives +28 cp
    start_b = chess.Board()
    assert C.is_standard_start(start_b) is True
    assert C.eval_bar_pct(28, mode="improved", board=start_b) == 50.0
    assert C.eval_bar_pct(28, mode="improved", is_start=True) == 50.0
    assert C.eval_bar_pct(28, mode="win_prob", is_start=True) == 50.0

    # After a move, board is no longer the start board
    b_after = start_b.copy()
    b_after.push_san("e4")
    assert C.is_standard_start(b_after) is False

    # Improved formula dampens tiny engine noise (<=15cp -> 50.0%) and clamps non-mate to [2.5, 97.5]
    assert C.eval_bar_pct(12, mode="improved", board=b_after) == 50.0
    assert C.eval_bar_pct(-12, mode="improved", board=b_after) == 50.0
    assert C.eval_bar_pct(12, mode="win_prob", board=b_after) > 50.5
    assert 50.0 < C.eval_bar_pct(200, mode="improved", board=b_after) < 97.5
    assert C.eval_bar_pct(2500, mode="improved", board=b_after) == 97.5
    assert C.eval_bar_pct(-2500, mode="improved", board=b_after) == 2.5

    # Mate scores reach 100% / 0%
    assert C.eval_bar_pct(10000, mode="improved", board=b_after) == 100.0
    assert C.eval_bar_pct(-10000, mode="improved", board=b_after) == 0.0


def test_modern_vs_legacy_annotations_and_reclassify():
    import classify as C

    # 1. A decisive sacrifice (best_wp=93%) from a balanced position (wp_before=52%)
    # was falsely rejected by legacy when best_wp was passed as wp_before, but succeeds now:
    sym_mod = C.classify(
        0.0, True, 93.0, 93.0, 52.0, True, 52.0,
        lenient=False, system="modern",
    )
    assert sym_mod == "!!"

    # 2. Already-decided winning position (+7.00 -> +5.20):
    # Modern system avoids flagging minor garbage-time CP drift as a Mistake/Inaccuracy,
    # whereas legacy flags 6.5% win-prob drop as '?'.
    sym_mod_win = C.classify(
        6.5, False, 91.0, 97.5, 95.0, False, 96.0,
        lenient=False, system="modern", cp_before=700, cp_after=520, best_cp=700,
    )
    sym_leg_win = C.classify(
        6.5, False, 91.0, 97.5, 95.0, False, 96.0,
        lenient=False, system="legacy",
    )
    assert sym_mod_win == "+"
    assert sym_leg_win == "?!"

    # 3. Great move (!) when escaping danger (wp_before=38% -> played_wp_after=55% with unique best move)
    sym_great = C.classify(
        0.0, True, 55.0, 55.0, 44.0, False, 38.0,
        lenient=False, system="modern",
    )
    sym_leg_great = C.classify(
        0.0, True, 55.0, 55.0, 44.0, False, 38.0,
        lenient=False, system="legacy",
    )
    assert sym_great == "!"
    assert sym_leg_great == "+++"

    # 4. In-place reclassification between modern and legacy systems without Stockfish
    pgn = '[White "A"]\n[Black "B"]\n\n1. e4 e5 2. Nf3 Nc6 *\n'
    g = chess.pgn.read_game(io.StringIO(pgn))
    b0 = g.board()
    b1 = b0.copy(); b1.push_san("e4")
    b2 = b1.copy(); b2.push_san("e5")
    res = [
        A.MoveResult(
            ply=1, color=True, san="e4", uci="e2e4",
            fen_before=b0.fen(), fen_after=b1.fen(),
            symbol="+++", analysed=True, loss=0.0,
            eval_before=30, eval_after=520, eval_after_text="+5.20",
            best_san="e4", pv=["e4"], pv_uci=["e2e4"],
        ),
        A.MoveResult(
            ply=2, color=False, san="e5", uci="e7e5",
            fen_before=b1.fen(), fen_after=b2.fen(),
            symbol="?!", analysed=True, loss=6.5,
            eval_before=-700, eval_after=-520, eval_after_text="-5.20",
            best_san="c5", second_cp=650, pv=["c5"], pv_uci=["c7c5"],
        ),
    ]
    A.reclassify_results(g, res, A.Settings(annotation_system="modern"))
    assert res[0].eval_before == 0
    assert res[1].symbol == "+"
    A.reclassify_results(g, res, A.Settings(annotation_system="legacy"))
    assert res[1].symbol == "?!"


def test_chesscom_game_review_parity():
    import chess
    import classify as C
    import accuracy as ACC

    # 1. Stockfish 19 NNUE centipawn calibration matches Chess.com displayed evaluation scale
    assert C.calibrate_cp(0) == 0
    assert 360 <= C.calibrate_cp(550) <= 395
    assert C.calibrate_cp(10000) == 10000

    # 2. Routine recapture on the same square is Best (+++), never Great (!)
    sym_recap = C.classify(
        0.0, True, 42.0, 42.0, 10.0, False, 42.0,
        system="modern", is_recapture=True,
    )
    assert sym_recap == "+++"

    # 3. Punishing an opponent's non-capture blunder/mistake with the best move is Great (!)
    sym_punish = C.classify(
        0.0, True, 55.0, 55.0, 44.0, False, 41.0,
        system="modern", is_recapture=False,
    )
    assert sym_punish == "!"

    # 4. Failing to capitalize on an opponent's gift while staying near pre-gift standing is Miss
    sym_miss = C.classify(
        39.5, False, 40.5, 80.0, 41.0, False, 35.0,
        system="modern",
    )
    assert sym_miss == "miss"

    # 5. Middlegame concession that still leaves mover ahead (e.g. 15. O-O) is Mistake (?),
    # whereas throwing away a won endgame (23. Kh1) is Blunder (??)
    sym_mid_concession = C.classify(
        24.2, False, 53.3, 77.5, 55.0, False, 77.5,
        system="modern", cp_before=329, cp_after=36, best_cp=329, phase="middlegame",
    )
    sym_end_blunder = C.classify(
        25.2, False, 51.4, 76.6, 52.0, False, 76.6,
        system="modern", cp_before=322, cp_after=15, best_cp=322, phase="endgame",
    )
    assert sym_mid_concession == "?"
    assert sym_end_blunder == "??"

    # 6. Repeating a position / shuffling in a drawn endgame is Excellent (++), not Best (+++)
    sym_repeat = C.classify(
        0.0, True, 50.0, 50.0, 50.0, False, 50.0,
        system="modern", repeats_position=True,
    )
    assert sym_repeat == "++"

    # 7. Accuracy & Game Rating calibration matches Chess.com (70.7% -> 700, 71.4% -> 750)
    assert ACC.rating_from_accuracy(70.4) == 700
    assert ACC.rating_from_accuracy(70.7) == 700
    assert ACC.rating_from_accuracy(71.4) == 750
    assert ACC.rating_from_accuracy(71.6) == 750

    # 8. Hikaru Brilliant (36... Qh7!!) leaving g5-knight en prise -> '!!' ('knight' sacrifice)
    b_qh7 = chess.Board("5k2/p5q1/8/Pp1p1Pn1/2pP2NQ/8/2r1r2P/3R2RK b - - 2 36")
    mv_qh7 = chess.Move.from_uci("g7h7")
    assert C.is_sacrifice(b_qh7, mv_qh7, 2) is True
    assert C.brilliant_category(b_qh7, mv_qh7) == "knight"
    sym_qh7 = C.classify(
        0.0, True, 50.0, 50.0, 50.0, True, 50.0,
        system="modern",
    )
    assert sym_qh7 == "!!"

    # 9. Hikaru Great moves & non-Great exclusions (26... h5!, 35. Nxf6+!, 37. Qg3!, 37... Qe7!, 56. Nxh8, 67... Qxb7#)
    # 26... h5! (pawn kicks knight defender after opponent blunder)
    assert C.classify(
        0.0, True, 59.1, 59.1, 59.1, False, 50.9,
        system="modern", attacks_piece=True,
    ) == "!"
    # 35. Nxf6+! (discovered attack saving a lost position from -3.20 to 0.00)
    assert C.classify(
        0.0, True, 50.0, 50.0, 50.0, False, 24.6,
        system="modern", is_capture=True, gives_check=True,
    ) == "!"
    # 37... Qe7! (critical non-capture defense immediately after a Brilliant/Great move)
    assert C.classify(
        0.0, True, 50.0, 50.0, 46.6, False, 50.0,
        system="modern", best_cp=0, prev_critical=True,
    ) == "!"
    # 56. Nxh8 (capturing an already-attacked undefended piece is Best +++, not Great !)
    assert C.classify(
        0.0, True, 55.8, 55.8, 19.0, False, 55.8,
        system="modern", is_capture=True, pre_attacked_free_piece=True,
    ) == "+++"
    # 67... Qxb7# (mate in 1 is Best +++, not Great !)
    assert C.classify(
        0.0, True, 100.0, 100.0, 5.0, False, 10.0,
        system="modern", best_cp=10000,
    ) == "+++"


def test_brilliant_system_core_and_context_conditions():
    import chess
    import classify as C

    # 1. Tactical Knight underpromotion (c8=N+ royal fork) vs decorative Rook underpromotion (c8=R+)
    b_fork = chess.Board("4k3/2P2q2/8/8/8/8/8/4K3 w - - 0 1")
    mv_knight_fork = chess.Move.from_uci("c7c8n")
    assert C.is_brilliant_underpromotion(b_fork, mv_knight_fork, is_best=True, loss=0.0) is True

    # Open board where c8=Q+ and c8=R+ both give check and neither stalemates:
    # decorative c8=R+ (not engine best or tied with Queen) is NOT a tactical underpromotion
    b_open = chess.Board("2k5/2P5/8/8/8/8/8/4K3 w - - 0 1")
    mv_decor_rook = chess.Move.from_uci("c7c8r")
    assert C.is_brilliant_underpromotion(
        b_open, mv_decor_rook, is_best=False, loss=0.5, second_wp=95.0, best_wp=95.5
    ) is False

    # 2. Context Condition: Must not be worse after the move
    # Unsound/speculative sacrifice leaving mover at 36% (-150 cp) is NOT Brilliant
    assert C.classify(
        1.5, True, 36.0, 37.5, 30.0, True, 38.0,
        system="modern", cp_before=-130, cp_after=-150, best_cp=-130,
    ) != "!!"

    # 3. Context Condition: Cannot already be overwhelmingly winning (+10.00 or Queen up with trivial wins)
    assert C.classify(
        0.0, True, 97.0, 97.0, 94.0, True, 96.0,
        system="modern", cp_before=1000, cp_after=1000, best_cp=1000,
    ) == "+++"
    assert C.classify(
        0.0, True, 92.0, 92.0, 88.0, True, 85.0,
        system="modern", cp_before=500, cp_after=500, best_cp=500, already_overwhelming=True,
    ) == "+++"

    # 4. Context Condition: Must be critical
    # Non-critical sacrifice when already comfortably winning (wp_before=82%, cp_before=350)
    # and 2nd-best move also wins easily (second_wp=85%, best_wp=86%) -> Best (+++), not Brilliant (!!)
    assert C.classify(
        0.0, True, 86.0, 86.0, 85.0, True, 82.0,
        system="modern", cp_before=350, cp_after=380, best_cp=380,
    ) == "+++"
    # Critical sacrifice where any other move forfeits the win (best_wp=88%, second_wp=50%) -> Brilliant (!!)
    assert C.classify(
        0.0, True, 88.0, 88.0, 50.0, True, 82.0,
        system="modern", cp_before=350, cp_after=400, best_cp=400,
    ) == "!!"





def test_clock_and_move_time_parsing():
    pgn = ('[White "a"]\n[Black "b"]\n[TimeControl "180+2"]\n\n'
           '1. e4 {[%clk 0:03:00]} e5 {[%clk 0:03:00]} 2. Nf3 {[%clk 0:02:55.5]} Nc6 {[%clk 0:02:58]} *\n')
    g = chess.pgn.read_game(io.StringIO(pgn))
    d = A.extract_game_clocks(g)
    assert d["has_clocks"]
    assert d["initial_white"] == "3:00"
    assert len(d["plies"]) == 4 and len(d["positions"]) == 5
    assert d["plies"][2]["move_time_text"] == "6.5s"
    assert d["positions"][3][0] == "2:56" or d["positions"][3][0].startswith("2:5")
    none = A.extract_game_clocks(chess.pgn.read_game(io.StringIO("1. e4 e5 *")))
    assert not none["has_clocks"] and none["initial_white"] == "--:--"


def test_favorites_and_brilliant_sorting(tmp_path):
    lib = LIB.GameLibrary(str(tmp_path / "f.db"))
    g, res = _sample_game_and_results()
    gid = lib.save(g, res, user_color="white")
    pgn2 = '[White "X"]\n[Black "Y"]\n[Result "*"]\n\n1. d4 d5 *\n'
    g2 = chess.pgn.read_game(io.StringIO(pgn2))
    gid2 = lib.save(g2, [], user_color="white")
    assert lib.toggle_favorite(gid2) is True
    assert [r["id"] for r in lib.list(favorites_only=True)] == [gid2]
    assert lib.list(sort_by="most_brilliant")[0]["id"] == gid
    assert lib.list(sort_by="least_brilliant")[0]["id"] == gid2
    assert lib.list(sort_by="opponent_brilliant")[0]["id"] == gid
    assert lib.toggle_favorite(gid2) is False


def test_profile_rules_and_updater():
    import updater
    assert updater.is_newer_version("v1.10.0", "v1.9.0")
    assert updater.is_newer_version("v1.10.0-beta.2", "v1.10.0-beta.1")
    assert updater.is_newer_version("v1.10.0-beta.10", "v1.10.0-beta.7")
    assert updater.is_newer_version("v1.10.0", "v1.10.0-beta.2")
    assert not updater.is_newer_version("v1.9.0", "v1.9.0")
    assert updater.is_prerelease_version("v1.10.0-beta.1")
    assert not updater.is_prerelease_version("v1.9.1")
    rels = [{"tag_name": "v2.0.0-beta.1", "prerelease": True}, {"tag_name": "v1.9.5", "prerelease": False}]
    assert updater.select_latest_stable_release(rels)["tag_name"] == "v1.9.5"
    assert updater.select_latest_prerelease(rels)["tag_name"] == "v2.0.0-beta.1"
    import main as M
    assert M.elide_profile_name("A" * 40).endswith("...")
    assert M.elide_profile_name("Holly") == "Holly"
    h = {"White": "Holly", "Black": "Bob"}
    assert not M.should_show_board_avatar("", chess.WHITE, h)
    assert M.should_show_board_avatar("Holly", chess.WHITE, h)
    assert not M.should_show_board_avatar("Holly", chess.BLACK, h)


def test_windows_updater_validation_and_cleanup(tmp_path):
    import updater
    import winutil

    target = tmp_path / "Holly's Chess Analyzer.exe"
    target.write_bytes(b"MZold")

    # Reject invalid / non-MZ downloaded payload
    bad_src = tmp_path / "bad.exe"
    bad_src.write_bytes(b"<html>not an exe</html>")
    assert updater.apply_windows_exe_update(str(bad_src), str(target)) is False

    # Cleanup removes leftover .old / .old.<pid> / .new.<pid> / .hca_old_* files
    leftovers = [
        tmp_path / "Holly's Chess Analyzer.exe.old",
        tmp_path / "Holly's Chess Analyzer.exe.old.1234",
        tmp_path / "Holly's Chess Analyzer.exe.new.1234",
        tmp_path / ".hca_old_1234.exe",
    ]
    for p in leftovers:
        p.write_bytes(b"junk")
    winutil.cleanup_old_exe_files(str(target))
    for p in leftovers:
        assert not p.exists()
    assert target.exists()


def test_holiday_events_and_app_icons(tmp_path, monkeypatch):
    from datetime import datetime
    import themes
    monkeypatch.setattr(themes, "data_root", lambda: str(tmp_path))

    assert themes.active_holiday_event(datetime(2026, 10, 15)) == "halloween"
    assert themes.active_holiday_event(datetime(2026, 12, 1)) == "christmas"
    assert themes.active_holiday_event(datetime(2026, 12, 30)) == "christmas"
    assert themes.active_holiday_event(datetime(2026, 12, 31)) == "new_year"
    assert themes.active_holiday_event(datetime(2027, 1, 1)) == "new_year"
    assert themes.active_holiday_event(datetime(2026, 11, 12)) is None
    assert themes.active_holiday_event(datetime(2026, 10, 15), disabled=True) is None

    selectable_ids = [i["id"] for i in themes.list_selectable_app_icons(now=datetime(2026, 11, 12))]
    for expected_icon in ("fluent", "aero", "flatdesign", "liquidglass", "metro", "skueomorphism"):
        assert expected_icon in selectable_ids
    for removed_icon in ("classic", "midnight", "gold"):
        assert removed_icon not in selectable_ids
    for hol in themes.HOLIDAY_IDS:
        assert hol not in selectable_ids

    # During October, Halloween is added to the library, without forcing Fluent users onto it
    oct_ids = [i["id"] for i in themes.list_selectable_app_icons(now=datetime(2026, 10, 20))]
    assert "halloween" in oct_ids
    assert themes.resolve_active_app_icon("fluent", False, datetime(2026, 10, 20))["id"] == "fluent"
    assert themes.resolve_active_app_icon("halloween", False, datetime(2026, 10, 20))["id"] == "halloween"
    # Once October ends (or events are disabled), Halloween reverts to Fluent
    assert themes.resolve_active_app_icon("halloween", False, datetime(2026, 11, 1))["id"] == "fluent"
    assert themes.resolve_active_app_icon("halloween", True, datetime(2026, 10, 20))["id"] == "fluent"
    assert not themes.delete_custom_app_icon("fluent")


def test_sound_board_background_and_piece_templates(tmp_path, monkeypatch):
    from datetime import datetime
    from PySide6.QtGui import QImage, QColor
    import themes
    monkeypatch.setattr(themes, "data_root", lambda: str(tmp_path))

    # Sounds: Original and Legacy are locked
    stpls = themes.list_sound_templates()
    assert [t["id"] for t in stpls[:2]] == ["original", "legacy"]
    assert stpls[0]["locked"] and stpls[1]["locked"]
    assert not themes.set_sound_slot("original", "events", "Move", __file__)
    assert not themes.delete_sound_template("legacy")

    custom_snd = themes.create_sound_template("Test Pack", copy_from_id="original")
    assert not custom_snd["locked"]
    dummy_wav = tmp_path / "ding.wav"
    dummy_wav.write_bytes(b"RIFF0000WAVEfmt ")
    assert themes.set_sound_slot(custom_snd["id"], "annotations", "!!", str(dummy_wav))
    loaded_snd = themes.get_sound_template(custom_snd["id"])
    assert "!!" in loaded_snd["annotations"]
    assert themes.clear_sound_slot(custom_snd["id"], "annotations", "!!")
    assert "!!" not in themes.get_sound_template(custom_snd["id"])["annotations"]
    assert themes.delete_sound_template(custom_snd["id"])

    # Boards: exact names & holiday rules & saved game New Years colors persistence
    b_names = [b["name"] for b in themes.list_selectable_board_templates(now=datetime(2026, 11, 12))]
    for expected in ("Brown & Tan", "Black & White", "Red & White", "Blue & White"):
        assert expected in b_names
    ny_ids = [b["id"] for b in themes.list_selectable_board_templates(now=datetime(2026, 12, 31))]
    assert "new_year" in ny_ids
    assert themes.resolve_active_board_template("brown_tan", False, datetime(2026, 12, 31))["id"] == "brown_tan"
    ny_board = themes.resolve_active_board_template("new_year", False, datetime(2026, 12, 31))
    assert ny_board["id"] == "new_year" and ny_board.get("random_light")
    assert themes.resolve_active_board_template("new_year", False, datetime(2026, 11, 12))["id"] == "brown_tan"

    # Event auto-select on start & auto-restore on end
    import analysis as A
    s = A.Settings(app_icon="aero", board_template="blue_white")
    assert themes.sync_holiday_event_state(s, now=datetime(2026, 10, 15)) is True
    assert s.app_icon == "halloween" and s.board_template == "halloween"
    assert s.pre_event_app_icon == "aero" and s.pre_event_board_template == "blue_white"
    # Second call during same event doesn't overwrite user changes
    s.app_icon = "metro"
    assert themes.sync_holiday_event_state(s, now=datetime(2026, 10, 20)) is False
    assert s.app_icon == "metro"
    # When event ends, automatically goes back to previously selected templates
    assert themes.sync_holiday_event_state(s, now=datetime(2026, 11, 1)) is True
    assert s.app_icon == "aero" and s.board_template == "blue_white"

    # Christmas board is Green & Snow White (#ffffff)
    xmas = themes.HOLIDAY_BOARDS["christmas"]
    assert xmas["light_hex"].lower() == "#ffffff"
    assert xmas["dark_hex"].lower() == "#1b7a3d"

    # ICO generation from PNG
    ico_bytes = themes.image_to_ico_bytes(themes.resolve_active_app_icon("fluent")["path"])
    assert len(ico_bytes) > 100 and ico_bytes[:4] == b"\x00\x00\x01\x00"
    light_bg = themes.get_background_template("light")
    hc_bg = themes.get_background_template("high_contrast")
    assert themes.get_theme_palette(light_bg)["bar_bg"] == "#e5e7eb"
    assert themes.get_theme_palette(light_bg)["graph_bg"] == "#e5e7eb"
    hc_qss = themes.build_app_stylesheet(hc_bg)
    assert "QDialog" in hc_qss and "#000000" in hc_qss and "#ffff00" in hc_qss

    lib = LIB.GameLibrary(str(tmp_path / "ny.db"))
    g, res = _sample_game_and_results()
    pal = themes.generate_new_years_palette(seed=42)
    gid = lib.save(g, res, new_years_colors=pal)
    assert lib.get_new_years_colors(gid) == pal

    # Backgrounds & Pieces
    bg_names = [b["name"] for b in themes.list_background_templates()]
    for expected in ("Dark", "Light", "High Contrast", "Aqua Blue"):
        assert expected in bg_names
    assert themes.list_piece_templates()[0]["name"] == "Default"
    assert themes.list_piece_templates()[0]["locked"]
    pt = themes.create_piece_template("Custom Set")
    png = tmp_path / "wk.png"
    img = QImage(32, 32, QImage.Format_RGBA8888)
    img.fill(QColor("#ffffff"))
    img.save(str(png), "PNG")
    assert themes.set_piece_slot(pt["id"], "wK", str(png))
    assert "wK" in themes.get_piece_template(pt["id"])["pieces"]
    assert themes.delete_piece_template(pt["id"])
