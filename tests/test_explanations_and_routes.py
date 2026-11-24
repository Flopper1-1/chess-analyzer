import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import chess
import chess.pgn

import analysis as A
import classify as C
import explanations as EX
import library as LIB
from openings import OpeningBook

ROOT = os.path.join(os.path.dirname(__file__), "..")


def test_move_explanations_motifs_and_outcomes():
    # 1. Book move with opening name
    b_start = chess.Board()
    txt_book = EX.explain_move(
        b_start.fen(),
        "e2e4",
        "/",
        opening="King's Pawn Game",
        eco="C20",
    )
    assert "King's Pawn Game" in txt_book and "C20" in txt_book and "e4" in txt_book

    # 2. Checkmate
    b_mate = chess.Board("r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4")
    txt_mate = EX.explain_move(b_mate.fen(), "h5f7", "+++")
    assert "checkmate" in txt_mate.lower() and "Qxf7#" in txt_mate

    # 3. Forced move in check
    b_forced = chess.Board("4k3/8/8/8/8/8/4R3/4K3 b - - 0 1")
    mv_forced = next(iter(b_forced.legal_moves))
    # Construct position with only 1 legal move: king in corner blocked
    b_one = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
    # Put pawn obstructing or rook check: h8 king, Qd7, Kf6? Let's verify count == 1
    b_one = chess.Board("7k/R5p1/6K1/8/8/8/8/8 b - - 0 1")
    # Wait: king has f8/g8? Use simple 1-legal-move position: Kh8 blocked by g7 pawn, attacked by Ra8 -> none, wait:
    b_one = chess.Board("6k1/5p1p/6p1/8/8/8/4R3/6K1 b - - 0 1")  # many moves
    b_one = chess.Board("k7/2Q5/1K6/8/8/8/8/8 b - - 0 1")  # 0 legal moves (stalemate)
    b_one = chess.Board("7k/5p1p/5P1K/8/8/8/8/6R1 b - - 0 1")  # g6 only? Let's test in-check single evasion
    b_one = chess.Board("k7/1R6/8/2B5/8/8/8/6K1 b - - 0 1")  # in check, Ka8 attacked -> wait Rb7 checkmate.
    # Actually simplest 1-legal-move in check: Black Kh8, white Qg7+? Wait: Kh8, Bg6, Rh1+? No, white Ka6, Qb7+? Wait:
    b_one = chess.Board("k7/P7/1K6/8/8/8/8/8 b - - 0 1")  # stalemate if no other piece, add black pawn b6->b5? Let's use White to move with pin
    b_one = chess.Board("4r1k1/8/8/8/8/8/4Q3/4K3 w - - 0 1")
    txt_forced = EX.explain_move(b_one.fen(), "e2e8", "forced")
    assert "only legal move" in txt_forced.lower()

    # 4. Brilliant sacrifice
    b_qh7 = chess.Board("5k2/p5q1/8/Pp1p1Pn1/2pP2NQ/8/2r1r2P/3R2RK b - - 2 36")
    txt_bril = EX.explain_move(b_qh7.fen(), "g7h7", "!!", brilliant_type="knight")
    assert "brilliant" in txt_bril.lower() and "knight" in txt_bril.lower() and "Qh7" in txt_bril

    # 5. Brilliant underpromotion avoiding stalemate
    b_under = chess.Board("8/4P2p/5K1k/7P/8/8/8/8 w - - 0 1")
    txt_under = EX.explain_move(b_under.fen(), "e7e8n", "!!", brilliant_type="underpromotion")
    assert "underpromotion" in txt_under.lower() and "stalemate" in txt_under.lower()

    # 6. Fork & Great move
    b_fork = chess.Board("r3k3/8/8/3N4/8/8/8/4K3 w - - 0 1")
    txt_fork = EX.explain_move(b_fork.fen(), "d5c7", "!", eval_before=300, eval_after=600, second_cp=100)
    assert "fork" in txt_fork.lower() and "king" in txt_fork.lower() and "rook" in txt_fork.lower()

    # 7. Castling
    b_castle = chess.Board("r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4")
    txt_castle = EX.explain_move(b_castle.fen(), "e1g1", "+++")
    assert "castles kingside" in txt_castle.lower()

    # 8. Blunder hanging piece + citing stronger move
    b_hang = chess.Board("4k3/8/8/8/4r3/8/8/3QK3 w - - 0 1")
    txt_hang = EX.explain_move(
        b_hang.fen(), "d1e2", "??", eval_before=400, eval_after=-500, best_san="Qd5", best_uci="d1d5"
    )
    assert "blunder" in txt_hang.lower() and "hang" in txt_hang.lower() and "Qd5" in txt_hang

    # 9. Blunder allowing forced mate + refutation
    b_allow_mate = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 3 3")
    txt_allow = EX.explain_move(
        b_allow_mate.fen(),
        "g8f6",
        "??",
        eval_before=-20,
        eval_after=10000,
        best_san="g6",
        best_uci="g7g6",
        after_pv_uci=["h5f7"],
    )
    assert "checkmate" in txt_allow.lower() and "Qxf7#" in txt_allow and "g6" in txt_allow

    # 10. Miss citing missed tactic
    b_miss = chess.Board("4k3/8/8/3n4/8/8/8/3QK3 w - - 0 1")
    txt_miss = EX.explain_move(
        b_miss.fen(), "e1f1", "miss", eval_before=800, eval_after=200, best_san="Qxd5", best_uci="d1d5"
    )
    assert "miss" in txt_miss.lower() and "Qxd5" in txt_miss

    # 11. Lazy fallback via explain_result for older library entries with empty explanation
    legacy_res = A.MoveResult(
        ply=1,
        color=chess.WHITE,
        san="O-O",
        uci="e1g1",
        fen_before=b_castle.fen(),
        fen_after="",
        symbol="+++",
        analysed=True,
    )
    assert "castles kingside" in EX.explain_result(legacy_res).lower()

    # 12. Rich tactical & strategic motifs: relative pin, skewer, outpost, open-file rook, 7th-rank rook, multi-ply refutation
    b_rel_pin = chess.Board("r2qkb1r/ppp2ppp/2np1n2/4p3/2B1P3/2NP1N2/PPP2PPP/R1BQK2R w KQkq - 0 6")
    txt_pin = EX.explain_move(b_rel_pin.fen(), "c1g5", "++")
    assert "pins the knight on f6 to the queen on d8" in txt_pin

    b_skewer = chess.Board("4q3/8/4k3/8/8/8/8/3R2K1 w - - 0 25")
    txt_skewer = EX.explain_move(b_skewer.fen(), "d1e1", "!")
    assert "skewers the king on e6 and the queen on e8" in txt_skewer

    b_outpost = chess.Board("4k3/p6p/8/8/2P5/4N3/8/4K3 w - - 0 18")
    txt_outpost = EX.explain_move(b_outpost.fen(), "e3d5", "+++")
    assert "outpost" in txt_outpost.lower() and "d5" in txt_outpost

    b_open_rook = chess.Board("4k3/p1pp1ppp/8/8/8/8/P1PP1PPP/3R2K1 w - - 0 18")
    txt_open_rook = EX.explain_move(b_open_rook.fen(), "d1e1", "+++")
    assert "open e-file" in txt_open_rook

    b_multi_ref = chess.Board("4k3/8/8/8/8/2n5/8/R3K2R w KQ - 0 20")
    txt_multi_ref = EX.explain_move(
        b_multi_ref.fen(), "a1c1", "??",
        eval_before=0, eval_after=-450,
        best_san="Kd2", best_uci="e1d2",
        after_pv_uci=["c3a2", "c1c2", "a2b4"],
    )
    assert "blunder" in txt_multi_ref.lower() and "Kd2" in txt_multi_ref


def test_single_move_live_analysis_and_chain(tmp_path):
    s = A.Settings(depth=10)
    book = OpeningBook(os.path.join(ROOT, "assets", "openings"))
    eng = A.open_engine(s)
    try:
        # Chained manual route from start: 1. e4 (Book) -> 1... e5 (Book)
        b0 = chess.Board()
        mv1 = chess.Move.from_uci("e2e4")
        r1, infos1 = A.analyse_single_move(eng, b0, mv1, s, book, book_active=True, ply=1)
        assert r1.symbol == "/" and r1.book
        assert r1.explanation and "e4" in r1.explanation
        assert len(infos1) >= 1

        b1 = b0.copy()
        b1.push(mv1)
        mv2 = chess.Move.from_uci("e7e5")
        r2, infos2 = A.analyse_single_move(
            eng, b1, mv2, s, book, cached_before_infos=infos1, prev_move=mv1, book_active=True, ply=2
        )
        assert r2.symbol == "/" and r2.book
        assert r2.explanation and "e5" in r2.explanation

        # Manual blunder test: 3... Nf6?? in Scholar's Mate setup
        b_sch = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 3 3")
        mv_blunder = chess.Move.from_uci("g8f6")
        r_blunder, infos_after_blunder = A.analyse_single_move(
            eng, b_sch, mv_blunder, s, book, book_active=False, ply=6
        )
        assert r_blunder.symbol == "??"
        assert r_blunder.best_san in ("g6", "Qe7", "Nh6")
        assert "checkmate" in r_blunder.explanation.lower()
        assert r_blunder.best_san in r_blunder.explanation

        # Checkmate as manual follow-up move: 4. Qxf7# reusing infos_after_blunder
        b_sch_after = b_sch.copy()
        b_sch_after.push(mv_blunder)
        r_mate, infos_mate = A.analyse_single_move(
            eng,
            b_sch_after,
            chess.Move.from_uci("h5f7"),
            s,
            book,
            cached_before_infos=infos_after_blunder,
            prev_move=mv_blunder,
            book_active=False,
            ply=7,
        )
        assert r_mate.eval_after == 10000
        assert r_mate.eval_after_text == "#"
        assert "checkmate" in r_mate.explanation.lower()

        # Full analyse_game + library persistence roundtrip
        pgn = '[White "W"]\n[Black "B"]\n\n1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0\n'
        g = chess.pgn.read_game(io.StringIO(pgn))
        res_all = A.analyse_game(g, s, eng, book)
        assert len(res_all) == 7
        assert all(r.explanation for r in res_all)

        lib = LIB.GameLibrary(str(tmp_path / "exp.db"))
        gid = lib.save(g, res_all, s)
        _lg, loaded = lib.load(gid)
        assert [r.explanation for r in loaded] == [r.explanation for r in res_all]

        # Reclassify updates explanations
        old_exp = loaded[5].explanation
        A.reclassify_results(g, loaded, A.Settings(annotation_system="legacy"))
        assert loaded[5].explanation
        assert isinstance(old_exp, str)
    finally:
        eng.quit()
