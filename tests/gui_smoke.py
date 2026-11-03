import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
import chess
import main as M
import icons, styles

HERE = os.path.dirname(os.path.abspath(__file__))
PGN = """[White "Alice"]
[Black "Bob"]
[Result "1-0"]

1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0

[White "Carl"]
[Black "Dana"]
[Result "0-1"]

1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Bg5 Be7 0-1
"""
app = QApplication(sys.argv)
w = M.MainWindow()
w.resize(1180, 760)
w.show()
w.settings.depth = 10
w.settings.player_name = "bob"
w.settings.lenient_brilliant = True
styles.mode = "icons"
w.load_text(PGN)
t = 0
while any(not j.done for j in w.jobs) and t < 900:
    QTest.qWait(100); t += 1
QTest.qWait(300)
print("jobs done:", [j.done for j in w.jobs], [len(j.results) for j in w.jobs])
print("combo:", [w.game_combo.itemText(i) for i in range(w.game_combo.count())])
print("symbols g1:", [r.symbol for r in w.jobs[0].results])
print("symbols g2:", [r.symbol for r in w.jobs[1].results])
print("flipped (bob is black):", w.board.flipped)
w.goto(6)
QTest.qWait(200)
w.grab().save(os.path.join(HERE, "shot_alt.png"))
w.goto(7)
QTest.qWait(200)
print("end badges:", w.board.end_badges)
w.grab().save(os.path.join(HERE, "shot_end.png"))
# switch to game 2 while done; then legacy mode shot
w.game_combo.setCurrentIndex(1)
QTest.qWait(300)
styles.mode = "legacy"
w.pick_game(0); w.goto(6)
QTest.qWait(200)
w.grab().save(os.path.join(HERE, "shot_legacy.png"))
styles.mode = "icons"
# settings dialog
d = M.SettingsDialog(w.settings, w)
d.show()
d.slider.setValue(24); print("slider 24 -> preset", d.preset.currentData(), d.threads.value(), d.hash.value())
d.slider.setValue(8); print("slider 8 ->", d.threads.value(), d.hash.value())
d.preset.setCurrentIndex(d.preset.findData("medium")); print("medium ->", d.slider.value(), d.threads.value(), d.hash.value())
d.stack.setCurrentIndex(0)
d.findChildren(M.QTabWidget)[0].setCurrentIndex(1)
QTest.qWait(200)
d.grab().save(os.path.join(HERE, "shot_settings.png"))

# Test in-app library save and instant reload without engine
import tempfile
import library as LIB
tmp_db = os.path.join(tempfile.gettempdir(), "smoke_lib.db")
if os.path.exists(tmp_db):
    os.remove(tmp_db)
w.library = LIB.GameLibrary(tmp_db)
w.pick_game(0)
orig_syms = [r.symbol for r in w.results]
w.save_to_library()
lib_rows = w.library.list()
assert len(lib_rows) == 1
w.holder.close()  # close engine first to prove reload does not start Stockfish
w.load_from_library(lib_rows[0]["id"])
assert [r.symbol for r in w.results] == orig_syms
assert w.holder.engine is None
os.remove(tmp_db)
print("library smoke ok!")

print('---PGN---'); print(w.annotated_pgn(0))
