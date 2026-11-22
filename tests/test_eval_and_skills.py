import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import chess
import chess.pgn

import accuracy as ACC
import analysis as A
import classify as C
import skills as SK
from openings import OpeningBook

ROOT = os.path.join(os.path.dirname(__file__), "..")


def test_expected_points_and_wdl_curve():
    # Exact center and mate extremes
    assert abs(C.expected_points(0, 2000) - 0.5) < 1e-6
    assert C.expected_points(10000, 2000) == 1.0
    assert C.expected_points(-10000, 2000) == 0.0
    assert C.expected_points(None, 2000) == 0.5

    # Calibrated points at Elo 2000
    assert abs(C.expected_points(100, 2000) - 0.64680) < 5e-4
    assert abs(C.expected_points(200, 2000) - 0.81077) < 5e-4
    assert abs(C.expected_points(300, 2000) - 0.88544) < 5e-4
    assert abs(C.expected_points(500, 2000) - 0.96213) < 5e-4
    assert abs(C.expected_points(1000, 2000) - 0.99972) < 5e-4

    # Antisymmetry ep(cp) + ep(-cp) == 1.0 and monotonicity across Elo
    for cp in (50, 150, 400):
        assert abs(C.expected_points(cp, 1800) + C.expected_points(-cp, 1800) - 1.0) < 1e-9
    assert C.expected_points(150, 2500) > C.expected_points(150, 2000) > C.expected_points(150, 1000)

    # WDL consistency: W + D + L == 1.0 and W + 0.5*D == expected_points
    for cp in (0, 120, -250, 600, 10000, -10000):
        for elo in (1200, 2000, 2800):
            w, d, l = C.wdl_probabilities(cp, elo)
            assert abs((w + d + l) - 1.0) < 1e-9
            assert abs((w + 0.5 * d) - C.expected_points(cp, elo)) < 1e-9
            assert 0.0 <= w <= 1.0 and 0.0 <= d <= 1.0 and 0.0 <= l <= 1.0


def test_linear_eval_bar_and_raw_accuracy():
    b_mid = chess.Board("rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2")
    assert C.eval_bar_pct(0, mode="improved", board=b_mid) == 50.0
    assert C.eval_bar_pct(15, mode="improved", board=b_mid) == 50.0
    assert abs(C.eval_bar_pct(200, mode="improved", board=b_mid) - 72.5) < 1e-6
    assert abs(C.eval_bar_pct(-200, mode="improved", board=b_mid) - 27.5) < 1e-6
    assert C.eval_bar_pct(400, mode="improved", board=b_mid) == 95.0
    assert C.eval_bar_pct(1200, mode="improved", board=b_mid) == 95.0
    assert C.eval_bar_pct(-1200, mode="improved", board=b_mid) == 5.0
    assert C.eval_bar_pct(10000, mode="improved", board=b_mid) == 100.0
    assert C.eval_bar_pct(-10000, mode="improved", board=b_mid) == 0.0

    # Raw accuracy: Book=100, already-decided floor=80, severe blunder negative averaged cleanly
    assert ACC.raw_move_accuracy(5.0, is_book=True) == 100.0
    assert abs(ACC.raw_move_accuracy(2.0) - 94.3) < 1e-6
    assert abs(ACC.raw_move_accuracy(10.0) - 63.0) < 1e-6
    assert ACC.raw_move_accuracy(8.0, ep_before=98.0, ep_after=95.5) == 80.0
    assert ACC.raw_move_accuracy(30.0) < 0.0

    # Summarize computes overall, phase, and P/N/B/R/Q/K piece accuracy
    res = [
        A.MoveResult(ply=1, color=True, san="e4", uci="e2e4", fen_before=chess.Board().fen(), fen_after="", symbol="/", analysed=True, book=True, loss=0.0, eval_before=0, eval_after=15, phase="opening"),
        A.MoveResult(ply=2, color=False, san="e5", uci="e7e5", fen_before=b_mid.fen(), fen_after="", symbol="/", analysed=True, book=True, loss=0.0, eval_before=15, eval_after=15, phase="opening"),
        A.MoveResult(ply=3, color=True, san="Nf3", uci="g1f3", fen_before="rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2", fen_after="", symbol="+++", analysed=True, loss=0.0, eval_before=15, eval_after=25, phase="opening"),
        A.MoveResult(ply=4, color=False, san="Nc6", uci="b8c6", fen_before="rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2", fen_after="", symbol="?!", analysed=True, loss=8.0, eval_before=25, eval_after=85, phase="middlegame"),
    ]
    summ = ACC.summarize(res, elo=2000)
    assert summ[chess.WHITE]["overall"] == 100.0
    assert summ[chess.WHITE]["by_piece"]["P"] == 100.0
    assert summ[chess.WHITE]["by_piece"]["N"] == 100.0
    assert summ[chess.WHITE]["by_piece"]["Q"] is None
    assert 80.0 < summ[chess.BLACK]["overall"] < 90.0
    assert summ[chess.BLACK]["by_piece"]["N"] < 80.0

    # Game ELO extraction
    g = chess.pgn.read_game(io.StringIO('[WhiteElo "1400"]\n[BlackElo "1600"]\n\n1. e4 e5 *\n'))
    assert A.extract_average_elo(g.headers) == 1500
    assert A.extract_average_elo({}) == 2000


def test_skills_catalog_integrity_and_acyclic():
    assert SK.SKILL_CATEGORIES == ("Fundamentals", "Openings", "Tactics", "Strategy", "Endgames")
    assert len(SK.SKILLS) == 72
    assert len(SK.SKILL_BY_ID) == 72
    counts = {cat: len(SK.SKILLS_BY_CATEGORY[cat]) for cat in SK.SKILL_CATEGORIES}
    assert counts == {
        "Fundamentals": 7,
        "Openings": 10,
        "Tactics": 21,
        "Strategy": 16,
        "Endgames": 18,
    }
    for sd in SK.SKILLS:
        assert 3 <= sd.points_to_master <= 5
        for pid in sd.unlocked_by:
            assert pid in SK.SKILL_BY_ID
            assert pid != sd.id

    # Verify DAG has no cycles via topological visit
    state = {}
    def visit(sid):
        if state.get(sid) == 1:
            raise AssertionError(f"Cycle detected involving {sid}")
        if state.get(sid) == 2:
            return
        state[sid] = 1
        for pid in SK.SKILL_BY_ID[sid].unlocked_by:
            visit(pid)
        state[sid] = 2

    for sd in SK.SKILLS:
        visit(sd.id)


def test_skill_detectors_all_categories():
    # Unsound moves never earn skills
    b_start = chess.Board()
    assert SK.detect_move_skills(b_start, chess.Move.from_uci("e2e4"), symbol="??") == []
    assert SK.detect_move_skills(b_start, chess.Move.from_uci("e2e4"), symbol="miss") == []

    # Openings & Fundamentals: Pawns in center, Book streak, Develop, Fianchetto, Castling, Connect Rooks
    s_center = SK.detect_move_skills(b_start, chess.Move.from_uci("e2e4"), symbol="/", phase="opening", is_book=True, book_count_for_side=3)
    assert {"one_book_move", "two_book_moves", "three_book_moves", "pawns_in_center"}.issubset(s_center)

    b_dev = chess.Board("rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2")
    assert "develops_piece" in SK.detect_move_skills(b_dev, chess.Move.from_uci("g1f3"), symbol="+++", phase="opening")

    b_fian = chess.Board("rnbqkbnr/pppppppp/8/8/8/6P1/PPPPPP1P/RNBQKBNR w KQkq - 0 2")
    assert "fianchetto" in SK.detect_move_skills(b_fian, chess.Move.from_uci("f1g2"), symbol="+++", phase="opening")

    b_castle = chess.Board("r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4")
    assert "castle" in SK.detect_move_skills(b_castle, chess.Move.from_uci("e1g1"), symbol="+++", phase="opening")

    b_conn = chess.Board("4k3/8/8/8/8/3PP3/PPP2PPP/R2Q1RK1 w - - 0 12")
    assert "connect_rooks" in SK.detect_move_skills(b_conn, chess.Move.from_uci("d1e2"), symbol="+++", phase="middlegame")

    # Tactics: Free Piece, Recapture, Royal/Knight Fork, Pin, Absolute Pin, Skewer, Discovered/Double Check, Brilliant Queen Sacrifice
    b_free = chess.Board("4k3/8/8/3n4/8/8/8/3QK3 w - - 0 1")
    assert {"capture", "free_piece"}.issubset(SK.detect_move_skills(b_free, chess.Move.from_uci("d1d5"), symbol="+++"))

    b_recap = chess.Board("4k3/8/8/3q4/4N3/8/8/3QK3 w - - 0 10")
    s_recap = SK.detect_move_skills(
        b_recap, chess.Move.from_uci("d1d5"), symbol="+++",
        prev_move=chess.Move.from_uci("d8d5"), prev_was_capture=True,
    )
    assert {"recapture", "winning_capture"}.issubset(s_recap)

    b_rfork = chess.Board("4k3/8/4q3/3N4/8/8/8/6K1 w - - 0 15")
    s_rfork = SK.detect_move_skills(b_rfork, chess.Move.from_uci("d5c7"), symbol="!")
    assert {"fork", "knight_fork", "royal_fork", "check"}.issubset(s_rfork)

    b_pin = chess.Board("4k3/3n4/8/8/8/8/8/R3KB2 w - - 0 15")
    s_pin = SK.detect_move_skills(b_pin, chess.Move.from_uci("f1b5"), symbol="+++")
    assert {"pin", "absolute_pin"}.issubset(s_pin)

    b_skew = chess.Board("4q3/8/4k3/8/8/8/8/3R2K1 w - - 0 25")
    assert "skewer" in SK.detect_move_skills(b_skew, chess.Move.from_uci("d1e1"), symbol="!")

    b_dcheck = chess.Board("4k3/8/8/4N3/8/8/8/4R1K1 w - - 0 20")
    s_dc = SK.detect_move_skills(b_dcheck, chess.Move.from_uci("e5c6"), symbol="!")
    assert {"discovered_check", "discovered_attack"}.issubset(s_dc)

    b_dbl = chess.Board("3k4/8/8/8/3N4/8/8/3R2K1 w - - 0 20")
    s_dbl = SK.detect_move_skills(b_dbl, chess.Move.from_uci("d4e6"), symbol="!")
    assert {"double_check", "discovered_check"}.issubset(s_dbl)

    b_qsac = chess.Board("r5k1/5ppp/8/8/8/8/5PPP/3QK3 w - - 0 25")
    s_qsac = SK.detect_move_skills(b_qsac, chess.Move.from_uci("d1d8"), symbol="!!", brilliant_type="queen")
    assert {"brilliant_sacrifice", "queen_sacrifice"}.issubset(s_qsac)

    # Strategy: Open File, Double Rooks, Battery, Outpost, Kick, En Passant
    b_open = chess.Board("4k3/p1pp1ppp/8/8/8/8/P1PP1PPP/3R2K1 w - - 0 18")
    assert "rook_to_open_file" in SK.detect_move_skills(b_open, chess.Move.from_uci("d1e1"), symbol="+++")

    b_dblr = chess.Board("4k3/8/8/8/8/8/4R3/3R2K1 w - - 0 20")
    assert "double_rooks" in SK.detect_move_skills(b_dblr, chess.Move.from_uci("d1e1"), symbol="+++")

    b_batt = chess.Board("4k3/8/8/8/8/8/2B1Q3/4K3 w - - 0 16")
    assert "creates_battery" in SK.detect_move_skills(b_batt, chess.Move.from_uci("e2d3"), symbol="+++")

    b_outpost = chess.Board("4k3/p6p/8/8/2P5/4N3/8/4K3 w - - 0 18")
    assert "outpost" in SK.detect_move_skills(b_outpost, chess.Move.from_uci("e3d5"), symbol="+++")

    b_kick = chess.Board("4k3/8/8/4n3/8/8/3P4/4K3 w - - 0 12")
    assert "kick" in SK.detect_move_skills(b_kick, chess.Move.from_uci("d2d4"), symbol="+++")

    b_ep = chess.Board("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 25")
    assert "en_passant" in SK.detect_move_skills(b_ep, chess.Move.from_uci("e5d6"), symbol="+++", phase="endgame")

    # Endgames: Backrank Mate, Ladder Mate, Promotion, Passed Pawn, Rook to 7th, Opposition, KP Endgame
    b_br = chess.Board("6k1/5ppp/8/8/8/8/8/3R2K1 w - - 0 30")
    assert {"checkmate", "backrank_mate"}.issubset(SK.detect_move_skills(b_br, chess.Move.from_uci("d1d8"), symbol="+++", phase="endgame"))

    b_lad = chess.Board("3k4/R7/8/8/8/8/1R6/4K3 w - - 0 40")
    assert {"checkmate", "ladder_mate"}.issubset(SK.detect_move_skills(b_lad, chess.Move.from_uci("b2b8"), symbol="+++", phase="endgame"))

    b_pp = chess.Board("6k1/8/4P3/8/8/8/8/4K3 w - - 0 35")
    assert {"pushes_passed_pawn", "king_and_pawn_endgames"}.issubset(
        SK.detect_move_skills(b_pp, chess.Move.from_uci("e6e7"), symbol="+++", phase="endgame")
    )

    b_prom = chess.Board("6k1/4P3/8/8/8/8/8/4K3 w - - 0 36")
    assert "promotion" in SK.detect_move_skills(b_prom, chess.Move.from_uci("e7e8q"), symbol="+++", phase="endgame")

    b_r7 = chess.Board("6k1/8/8/8/8/8/8/3R2K1 w - - 0 30")
    assert {"rook_to_seventh", "rook_endgames"}.issubset(
        SK.detect_move_skills(b_r7, chess.Move.from_uci("d1d7"), symbol="+++", phase="endgame")
    )

    b_actk = chess.Board("4k3/8/8/8/8/8/8/4K3 w - - 0 40")
    assert "activate_king" in SK.detect_move_skills(b_actk, chess.Move.from_uci("e1e2"), symbol="+++", phase="endgame")

    b_opp = chess.Board("3k4/8/8/3K4/8/8/8/8 w - - 0 45")
    assert {"opposition", "king_and_pawn_endgames"}.issubset(
        SK.detect_move_skills(b_opp, chess.Move.from_uci("d5d6"), symbol="+++", phase="endgame")
    )


def test_skills_store_progression_dedup_and_reset(tmp_path):
    store_path = str(tmp_path / "skills_progress.json")
    store = SK.SkillsStore(store_path)

    summ0 = store.summary()
    assert summ0["total"] == 72
    assert summ0["mastered"] == 0
    assert summ0["unlocked"] > 0 and summ0["locked"] > 0

    # Verify ordering: Unlocked first, Mastered second, Locked last
    listed = store.list_skills()
    ranks = [{"unlocked": 0, "mastered": 1, "locked": 2}[d["state"]] for d in listed]
    assert ranks == sorted(ranks)

    # Child skill 'free_piece' starts locked (requires 'capture' x 3)
    assert store.get_skill_state("capture")["state"] == "unlocked"
    assert store.get_skill_state("free_piece")["state"] == "locked"

    # Re-claiming the exact same game + ply does not double-count
    r1 = store.claim_move_skills("gameA", 3, ["capture", "free_piece"])
    assert r1["awarded"] == ["capture"]
    assert store.get_skill_state("capture")["points"] == 1
    assert store.get_skill_state("free_piece")["points"] == 0  # locked stays 0
    r_dup = store.claim_move_skills("gameA", 3, ["capture", "free_piece"])
    assert r_dup["awarded"] == []
    assert store.get_skill_state("capture")["points"] == 1

    # Master 'capture' across 2 more unique moves -> automatically unlocks 'free_piece' and 'defend_piece'
    store.claim_move_skills("gameA", 5, ["capture"])
    r3 = store.claim_move_skills("gameA", 7, ["capture"])
    assert "capture" in r3["newly_mastered"]
    assert "free_piece" in r3["newly_unlocked"]
    assert "defend_piece" in r3["newly_unlocked"]
    assert store.get_skill_state("capture")["state"] == "mastered"
    assert store.get_skill_state("free_piece")["state"] == "unlocked"

    # Reload from disk persists state accurately
    store2 = SK.SkillsStore(store_path)
    assert store2.get_skill_state("capture")["state"] == "mastered"
    assert store2.get_skill_state("free_piece")["state"] == "unlocked"
    assert "mastered" in [d["state"] for d in store2.list_skills("Fundamentals")]

    # Reset clears everything cleanly
    store2.reset()
    assert store2.get_skill_state("capture")["points"] == 0
    assert store2.get_skill_state("free_piece")["state"] == "locked"
