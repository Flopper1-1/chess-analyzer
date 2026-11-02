import io
import sys
import threading

import chess
import chess.pgn
import os
import time
from PySide6.QtCore import Qt, QThread, Signal, QSettings, QRectF, QPointF, QSize, QEvent
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QShortcut, QKeySequence, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QFileDialog, QDialog, QPlainTextEdit, QDialogButtonBox, QFormLayout,
    QComboBox, QLineEdit, QSpinBox, QProgressBar, QListWidget, QHeaderView, QMessageBox,
    QAbstractItemView, QSizePolicy, QToolBar, QToolTip, QColorDialog, QTabWidget, QGridLayout,
    QSlider, QStackedWidget, QScrollArea, QCheckBox, QFrame, QSystemTrayIcon,
)

import analysis as A
import classify as C
from openings import OpeningBook, resource_path
import styles
import icons
import winutil
import accuracy as ACC

PIECES = {"K": "♔", "Q": "♕", "R": "♖", "B": "♗", "N": "♘", "P": "♙",
          "k": "♚", "q": "♛", "r": "♜", "b": "♝", "n": "♞", "p": "♟"}


# ---------------------------------------------------------------- widgets
LEGACY_END = {"checkmate_white": ("#", "#f2f2f2", "#111"), "checkmate_black": ("#", "#333", "#fff"),
              "draw_white": ("½", "#f2f2f2", "#111"), "draw_black": ("½", "#333", "#fff"),
              "resign_white": ("⚑", "#f2f2f2", "#111"), "resign_black": ("⚑", "#333", "#fff")}


class BoardWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.board = chess.Board()
        self.last_move = None
        self.badge = ""
        self.alt_move = None
        self.end_badges = []
        self.flipped = False
        self.setMinimumSize(380, 380)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_position(self, board, last_move=None, badge="", alt_move=None, end_badges=None):
        self.board, self.last_move, self.badge = board, last_move, badge
        self.alt_move, self.end_badges = alt_move, end_badges or []
        self.update()

    def draw_badge(self, p, r, key, corner="tr"):
        d = r.width() * 0.42
        x = r.right() - d * 0.9 if corner == "tr" else r.left() - d * 0.1
        c = QRectF(x, r.top() - d * 0.1, d, d)
        if styles.mode == "icons":
            pm = icons.pixmap_for_key(key, max(8, int(d * 2)))
            if pm is not None:
                p.drawPixmap(c.toRect(), pm)
                return
        if key in LEGACY_END:
            sym, bg, fg = LEGACY_END[key]
        else:
            sym, bg, fg = styles.symbol(key), styles.color(key), "#ffffff"
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(bg))
        p.drawEllipse(c)
        p.setPen(QColor(fg))
        f = QFont("Segoe UI", max(6, int(d * 0.38)), QFont.Bold)
        f.setFamilies(["Segoe UI", "Segoe UI Emoji", "Segoe UI Symbol"])
        p.setFont(f)
        p.drawText(c, Qt.AlignCenter, sym)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        s = min(self.width(), self.height()) // 8
        ox, oy = (self.width() - 8 * s) / 2, (self.height() - 8 * s) / 2

        def rect(sq):
            f, r = chess.square_file(sq), chess.square_rank(sq)
            if self.flipped:
                f, r = 7 - f, 7 - r
            return QRectF(ox + f * s, oy + (7 - r) * s, s, s)

        for sq in chess.SQUARES:
            light = (chess.square_file(sq) + chess.square_rank(sq)) % 2 == 1
            col = QColor("#f0d9b5") if light else QColor("#b58863")
            if self.last_move and sq in (self.last_move.from_square, self.last_move.to_square):
                col = QColor("#cdd26a") if light else QColor("#aaa23a")
            p.fillRect(rect(sq), col)
        font = QFont("Segoe UI Symbol", int(s * 0.62))
        p.setFont(font)
        for sq, pc in self.board.piece_map().items():
            sym = pc.symbol()
            glyph = PIECES[sym.lower()]
            r = rect(sq)
            outline = QColor("#000") if pc.color else QColor("#fff")
            p.setPen(outline)
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                p.drawText(r.translated(dx, dy), Qt.AlignCenter, glyph)
            p.setPen(QColor("#ffffff") if pc.color else QColor("#000000"))
            p.drawText(r, Qt.AlignCenter, glyph)
        # best alternative: arrow + icon on the destination square
        if self.alt_move:
            a, b = rect(self.alt_move.from_square).center(), rect(self.alt_move.to_square).center()
            pen = QPen(QColor(107, 163, 107, 190), s * 0.14, Qt.SolidLine, Qt.RoundCap)
            p.setPen(pen)
            p.drawLine(a, b)
            import math
            ang = math.atan2(b.y() - a.y(), b.x() - a.x())
            for da in (2.6, -2.6):
                p.drawLine(b, QPointF(b.x() + math.cos(ang + da) * s * 0.3, b.y() + math.sin(ang + da) * s * 0.3))
            self.draw_badge(p, rect(self.alt_move.to_square), "alt", "tl")
        if self.badge and self.last_move:
            self.draw_badge(p, rect(self.last_move.to_square), self.badge, "tr")
        for sq, key in self.end_badges:
            self.draw_badge(p, rect(sq), key, "tr")


class EvalBar(QWidget):
    def __init__(self):
        super().__init__()
        self.cp = 0
        self.text = "0.0"
        self.setFixedWidth(44)

    def set_eval(self, cp, text=""):
        self.cp = 0 if cp is None else cp
        if not text:
            text = "" if cp is None else ("%+.1f" % (cp / 100.0) if abs(cp) < 9000 else ("M" if cp > 0 else "-M"))
        self.text = text or "0.0"
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        h, w = self.height(), self.width()
        white_h = h * C.win_pct(self.cp) / 100.0
        p.fillRect(0, 0, w, h, QColor("#333"))
        p.fillRect(0, int(h - white_h), w, int(white_h) + 1, QColor("#eee"))
        p.setFont(QFont("Segoe UI", 9, QFont.Bold))
        white_ahead = self.cp >= 0
        # number sits on the side of whoever is ahead: bottom for white, top for black
        r = QRectF(0, h - 22, w, 20) if white_ahead else QRectF(0, 2, w, 20)
        p.setPen(QColor("#222") if white_ahead else QColor("#eee"))
        p.drawText(r, Qt.AlignCenter, self.text)


class GraphWidget(QWidget):
    clicked = Signal(int)

    def __init__(self):
        super().__init__()
        self.values = []
        self.labels = []
        self.hover = -1
        self.setMouseTracking(True)
        self.setMinimumHeight(70)
        self.setMaximumHeight(90)

    def set_values(self, v, labels=None):
        self.values = v
        self.labels = labels or [""] * len(v)
        self.update()

    def _index(self, x):
        return max(0, min(len(self.values) - 1, round(x / max(1, self.width()) * (len(self.values) - 1))))

    def mousePressEvent(self, e):
        if len(self.values) > 1:
            self.clicked.emit(self._index(e.position().x()))

    def mouseMoveEvent(self, e):
        if len(self.values) < 2:
            return
        i = self._index(e.position().x())
        self.hover = i
        cp = self.values[i]
        txt = ("%+.2f" % (cp / 100.0)) if abs(cp) < 9000 else ("Mate" if cp > 0 else "-Mate")
        lab = self.labels[i] if i < len(self.labels) else ""
        QToolTip.showText(e.globalPosition().toPoint(), "%s\nEval: %s" % (lab, txt), self)
        self.update()

    def leaveEvent(self, _):
        self.hover = -1
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#262626"))
        if len(self.values) < 2:
            return
        w, h = self.width(), self.height()
        pts = [QPointF(i * w / (len(self.values) - 1), h - h * C.win_pct(v) / 100) for i, v in enumerate(self.values)]
        poly = [QPointF(0, h)] + pts + [QPointF(w, h)]
        from PySide6.QtGui import QPolygonF
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#d9d9d9"))
        p.drawPolygon(QPolygonF(poly))
        p.setPen(QPen(QColor("#777"), 1))
        p.drawLine(0, h // 2, w, h // 2)
        if self.hover >= 0:
            x = int(pts[self.hover].x())
            p.setPen(QPen(QColor("#e8b923"), 1))
            p.drawLine(x, 0, x, h)
            p.setBrush(QColor("#e8b923"))
            p.drawEllipse(pts[self.hover], 3, 3)


# ---------------------------------------------------------------- workers
class EngineHolder:
    def __init__(self):
        self.engine = None
        self.waiting = 0
        self.lock = threading.Lock()

    def get(self, settings):
        if self.engine is None:
            self.engine = A.open_engine(settings)
            try:
                winutil.disable_throttle(self.engine.protocol.transport.get_pid())
            except Exception:
                pass
        return self.engine

    def close(self):
        if self.engine:
            try:
                self.engine.quit()
            except Exception:
                pass
            self.engine = None


class LockedEngine:
    """Engine proxy that takes the shared lock per call, so Best-line requests can interleave."""

    def __init__(self, holder, settings):
        self.holder, self.settings = holder, settings

    def analyse(self, *a, **k):
        while self.holder.waiting:
            time.sleep(0.01)
        with self.holder.lock:
            return self.holder.get(self.settings).analyse(*a, **k)


class Job:
    def __init__(self, game):
        self.game = game
        self.results = []
        self.done = False
        self.running = False
        self.progress = (0, 1)


class QueueWorker(QThread):
    """Analyses queued games one after another in the background."""
    move_ready = Signal(object, object)
    progress = Signal(object, int, int)
    job_done = Signal(object, bool)
    failed = Signal(str)

    def __init__(self, holder, jobs, settings, book):
        super().__init__()
        self.holder, self.settings, self.book = holder, settings, book
        self.pending = list(jobs)
        self.mutex = threading.Lock()
        self.cancel_flag = False

    def prioritize(self, job):
        with self.mutex:
            if job in self.pending:
                self.pending.remove(job)
                self.pending.insert(0, job)

    def run(self):
        eng = LockedEngine(self.holder, self.settings)
        while not self.cancel_flag:
            with self.mutex:
                if not self.pending:
                    break
                job = self.pending.pop(0)
            job.running = True
            try:
                A.analyse_game(job.game, self.settings, eng, self.book,
                               lambda a, b, j=job: self.progress.emit(j, a, b),
                               lambda: self.cancel_flag,
                               lambda r, j=job: self.move_ready.emit(j, r))
                job.running = False
                self.job_done.emit(job, not self.cancel_flag)
            except Exception as e:
                job.running = False
                self.failed.emit(str(e))
                self.job_done.emit(job, False)


class LineWorker(QThread):
    done = Signal(list, str)
    failed = Signal(str)

    def __init__(self, holder, fen, settings):
        super().__init__()
        self.holder, self.fen, self.settings = holder, fen, settings

    def run(self):
        self.holder.waiting += 1
        try:
            with self.holder.lock:
                self.holder.waiting -= 1
                eng = self.holder.get(self.settings)
                lines = A.best_line(eng, self.fen, self.settings.depth, 3)
            self.done.emit(lines, self.fen)
        except Exception as e:
            self.failed.emit(str(e))


# ---------------------------------------------------------------- dialogs
class SettingsDialog(QDialog):
    PRESETS = [("Custom", "custom"), ("Low (fast)", "low"), ("Medium", "medium"), ("High (accurate)", "high")]

    def __init__(self, s, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(520, 600)
        self._applying = False
        tabs = QTabWidget()
        lay = QVBoxLayout(self)
        lay.addWidget(tabs)
        page = QWidget(); f = QFormLayout(page)
        tabs.addTab(page, "Analysis")
        self.scope = QComboBox()
        self.scope.addItem("All moves (both sides)", "all")
        self.scope.addItem("My side only (faster)", "mine")
        self.scope.addItem("My side + brilliants (fast)", "mine_brilliant")
        self.scope.setCurrentIndex(max(0, self.scope.findData(s.scope)))
        self.side = QComboBox()
        for t, d in (("Both", "both"), ("White", "white"), ("Black", "black")):
            self.side.addItem(t, d)
        self.side.setCurrentIndex(max(0, self.side.findData(s.side)))
        self.name = QLineEdit(s.player_name)
        self.name.setPlaceholderText("optional: also flips the board to your side")
        self.lenient = QCheckBox("Lenient brilliants (smaller sacrifices and near-best moves count)")
        self.lenient.setChecked(s.lenient_brilliant)
        self.preset = QComboBox()
        for t, d in self.PRESETS:
            self.preset.addItem(t, d)
        self.preset.setCurrentIndex(max(0, self.preset.findData(s.preset)))
        self.slider = QSlider(Qt.Horizontal); self.slider.setRange(6, 30); self.slider.setValue(s.depth)
        self.depth_label = QLabel(str(s.depth)); self.depth_label.setFixedWidth(28)
        srow = QHBoxLayout(); srow.addWidget(self.slider, 1); srow.addWidget(self.depth_label)
        self.threads = QSpinBox(); self.threads.setRange(1, 64); self.threads.setValue(s.threads)
        self.hash = QSpinBox(); self.hash.setRange(16, 4096); self.hash.setValue(s.hash_mb)
        self.path = QLineEdit(s.engine_path)
        self.path.setPlaceholderText("blank = bundled Stockfish")
        self.preset.currentIndexChanged.connect(self.apply_preset)
        self.slider.valueChanged.connect(self.on_slider)
        for w in (self.threads, self.hash):
            w.valueChanged.connect(self.mark_custom)
        f.addRow("Analysis scope", self.scope)
        f.addRow("My side", self.side)
        f.addRow("My player name", self.name)
        f.addRow("", self.lenient)
        f.addRow("Preset", self.preset)
        f.addRow("Depth (slider)", srow)
        f.addRow("Threads", self.threads)
        f.addRow("Hash (MB)", self.hash)
        f.addRow("Engine path", self.path)
        hint = QLabel("Moving the depth slider switches to Custom and sets threads and hash automatically.")
        hint.setWordWrap(True)
        f.addRow(hint)

        # ---- annotations tab
        page2 = QWidget(); l2 = QVBoxLayout(page2)
        tabs.addTab(page2, "Annotations")
        self.mode = QComboBox()
        self.mode.addItem("Icons (new)", "icons")
        self.mode.addItem("Legacy (symbols and colours)", "legacy")
        self.mode.setCurrentIndex(max(0, self.mode.findData(styles.mode)))
        mrow = QHBoxLayout(); mrow.addWidget(QLabel("Annotation style:")); mrow.addWidget(self.mode, 1)
        l2.addLayout(mrow)
        self.stack = QStackedWidget(); l2.addWidget(self.stack, 1)

        # icons page
        ip = QWidget(); il = QVBoxLayout(ip)
        il.addWidget(QLabel("Edit an icon in Microsoft Paint, save it, then come back here (the preview updates)."))
        sc = QScrollArea(); sc.setWidgetResizable(True)
        inner = QWidget(); grid = QGridLayout(inner)
        self.icon_rows = {}
        for row, (stem, label) in enumerate(icons.ICON_LIST):
            pv = QLabel(); pv.setFixedSize(34, 34)
            tag = QLabel(); tag.setStyleSheet("color:#e8b923;")
            eb = QPushButton("Edit in Paint"); rb = QPushButton("Reset")
            eb.clicked.connect(lambda _=False, st=stem: self.edit_icon(st))
            rb.clicked.connect(lambda _=False, st=stem: self.reset_icon(st))
            grid.addWidget(pv, row, 0); grid.addWidget(QLabel(label), row, 1); grid.addWidget(tag, row, 2)
            grid.addWidget(eb, row, 3); grid.addWidget(rb, row, 4)
            self.icon_rows[stem] = (pv, tag)
        sc.setWidget(inner)
        il.addWidget(sc, 1)
        ra = QPushButton("Reset ALL icons to default"); ra.clicked.connect(self.reset_all_icons)
        il.addWidget(ra)
        self.stack.addWidget(ip)

        # legacy page
        lp = QWidget(); ll = QVBoxLayout(lp)
        ll.addWidget(QLabel("Pick the symbol (text or emoji) and colour for each annotation."))
        self.style_rows = {}
        g2 = QGridLayout()
        for row, (key, (name, _s, _c)) in enumerate(styles.DEFAULTS.items()):
            sym, col = styles.get_all()[key]
            ed = QLineEdit(sym); ed.setMaxLength(4); ed.setFixedWidth(70)
            btn = QPushButton(); btn.setFixedWidth(70)
            self._paint_btn(btn, col)
            btn.clicked.connect(lambda _=False, k=key: self.pick_color(k))
            g2.addWidget(QLabel(name), row, 0)
            g2.addWidget(ed, row, 1)
            g2.addWidget(btn, row, 2)
            self.style_rows[key] = [ed, btn, col]
        ll.addLayout(g2)
        rb2 = QPushButton("Reset legacy annotations to defaults"); rb2.clicked.connect(self.reset_styles)
        ll.addWidget(rb2)
        ll.addStretch(1)
        self.stack.addWidget(lp)
        self.mode.currentIndexChanged.connect(lambda: self.stack.setCurrentIndex(self.mode.currentIndex()))
        self.stack.setCurrentIndex(self.mode.currentIndex())
        self.refresh_icons()

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    # ---- icons
    def refresh_icons(self):
        for stem, (pv, tag) in self.icon_rows.items():
            pm = icons.pixmap(stem, 32)
            if pm is not None:
                pv.setPixmap(pm)
            tag.setText("custom" if icons.is_custom(stem) else "")

    def changeEvent(self, e):
        if e.type() == QEvent.ActivationChange and self.isActiveWindow() and hasattr(self, "icon_rows"):
            self.refresh_icons()
        super().changeEvent(e)

    def edit_icon(self, stem):
        icons.edit_in_paint(stem)
        self.refresh_icons()

    def reset_icon(self, stem):
        icons.reset(stem)
        self.refresh_icons()

    def reset_all_icons(self):
        icons.reset_all()
        self.refresh_icons()

    # ---- legacy
    @staticmethod
    def _paint_btn(btn, col):
        btn.setStyleSheet("background:%s;border:1px solid #888;" % col)

    def pick_color(self, key):
        row = self.style_rows[key]
        c = QColorDialog.getColor(QColor(row[2]), self, "Colour")
        if c.isValid():
            row[2] = c.name()
            self._paint_btn(row[1], row[2])

    def reset_styles(self):
        for key, (name, sym, col) in styles.DEFAULTS.items():
            row = self.style_rows[key]
            row[0].setText(sym); row[2] = col; self._paint_btn(row[1], col)

    # ---- presets / slider
    def apply_preset(self):
        vals = A.preset_values(self.preset.currentData())
        if vals:
            self._applying = True
            self.slider.setValue(vals[0]); self.threads.setValue(vals[1]); self.hash.setValue(vals[2])
            self.depth_label.setText(str(vals[0]))
            self._applying = False

    def on_slider(self, v):
        self.depth_label.setText(str(v))
        if self._applying:
            return
        self._applying = True
        self.preset.blockSignals(True)
        self.preset.setCurrentIndex(0)          # Custom
        self.preset.blockSignals(False)
        t, h = A.auto_resources(v)
        self.threads.setValue(t); self.hash.setValue(h)
        self._applying = False

    def mark_custom(self):
        if not self._applying and self.preset.currentData() != "custom":
            self.preset.blockSignals(True)
            self.preset.setCurrentIndex(0)
            self.preset.blockSignals(False)

    def result_styles(self):
        return {k: (r[0].text() or styles.DEFAULTS[k][1], r[2]) for k, r in self.style_rows.items()}

    def result_settings(self):
        return A.Settings(self.scope.currentData(), self.side.currentData(), self.name.text(),
                          self.slider.value(), self.threads.value(), self.hash.value(), self.path.text(),
                          self.preset.currentData(), self.lenient.isChecked())


class PasteDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Paste PGN or FEN")
        self.resize(520, 380)
        l = QVBoxLayout(self)
        self.text = QPlainTextEdit()
        l.addWidget(self.text)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        l.addWidget(bb)


def parse_input(text):
    """Return list of chess.pgn.Game from PGN text or a single FEN."""
    text = text.strip()
    if not text:
        return []
    first = text.splitlines()[0]
    if "[" not in text and "/" in first and len(first.split()) >= 2 and not any(c.isdigit() and "." in first for c in first[:3]):
        try:
            b = chess.Board(first.strip())
            g = chess.pgn.Game()
            g.setup(b)
            g.headers["Event"] = "FEN position"
            return [g]
        except ValueError:
            pass
    stream = io.StringIO(text)
    games = []
    while True:
        g = chess.pgn.read_game(stream)
        if g is None:
            break
        games.append(g)
    return games


# ---------------------------------------------------------------- main window
class MainWindow(QMainWindow):
    COLS = ["#", "Move", "", "Eval", "Opening", ""]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chess Analyzer")
        self.resize(1180, 760)
        self.setAcceptDrops(True)
        qs = QSettings("ChessAnalyzer", "ChessAnalyzer")
        self.qs = qs
        self.settings = A.Settings(qs.value("scope", "all"), qs.value("side", "both"), qs.value("name", ""),
                                   int(qs.value("depth", 16)), int(qs.value("threads", 2)),
                                   int(qs.value("hash", 128)), qs.value("engine", ""), qs.value("preset", "custom"), qs.value("lenient", False, type=bool))
        styles.load(qs)
        self.holder = EngineHolder()
        self.book = None
        self.games, self.game, self.results = [], None, []
        self.jobs, self.job = [], None
        self.worker = None
        self.line_workers = []

        c = QWidget(); self.setCentralWidget(c)
        root = QHBoxLayout(c)
        left = QVBoxLayout()
        self.opening_label = QLabel("Opening: –")
        self.opening_label.setStyleSheet("font-size:15px;font-weight:bold;")
        self.players = QLabel("")
        left.addWidget(self.players)
        bh = QHBoxLayout()
        self.evalbar = EvalBar()
        self.board = BoardWidget()
        bh.addWidget(self.evalbar); bh.addWidget(self.board, 1)
        left.addLayout(bh, 1)
        left.addWidget(self.opening_label)
        nav = QHBoxLayout()
        for t, fn in (("⏮", lambda: self.goto(0)), ("◀", lambda: self.goto(self.cur - 1)),
                      ("▶", lambda: self.goto(self.cur + 1)), ("⏭", lambda: self.goto(len(self.results))),
                      ("Flip", self.flip)):
            b = QPushButton(t); b.clicked.connect(fn); nav.addWidget(b)
        left.addLayout(nav)
        self.graph = GraphWidget(); self.graph.clicked.connect(self.goto)
        left.addWidget(self.graph)
        root.addLayout(left, 3)

        right = QVBoxLayout()
        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.setIconSize(QSize(22, 22))
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Stretch)
        for i, w in ((0, 36), (2, 44), (3, 60), (5, 56)):
            hh.setSectionResizeMode(i, QHeaderView.Fixed); self.table.setColumnWidth(i, w)
        self.table.cellClicked.connect(lambda r, _c: self.goto(r))
        right.addWidget(self.table, 3)
        self.line_title = QLabel("Best line: click “Best” on a move")
        right.addWidget(self.line_title)
        self.line_list = QListWidget()
        self.line_list.setMaximumHeight(130)
        self.line_list.itemClicked.connect(self.on_line_clicked)
        right.addWidget(self.line_list)
        self.acc_label = QLabel("")
        self.acc_label.setTextFormat(Qt.RichText)
        right.addWidget(self.acc_label)
        self.progress = QProgressBar(); self.progress.setVisible(False)
        right.addWidget(self.progress)
        self.status = QLabel("Open a PGN or paste a PGN/FEN to begin.")
        right.addWidget(self.status)
        root.addLayout(right, 2)

        tb = QToolBar(); self.addToolBar(tb)
        for t, fn in (("Open PGN…", self.open_file), ("Paste PGN/FEN…", self.paste),
                      ("Re-analyze", self.restart_all), ("Stop", self.stop), ("Save game…", self.save_game), ("Save all…", self.save_all), ("Settings…", self.open_settings)):
            tb.addAction(t, fn)
        self.game_combo = QComboBox(); self.game_combo.setVisible(False)
        self.game_combo.currentIndexChanged.connect(self.pick_game)
        tb.addWidget(self.game_combo)
        self.cur = 0
        self.pv_boards = None
        tb.addAction("Keys", self.show_keys)
        self.table.currentCellChanged.connect(lambda r, c, pr, pc: r >= 0 and r != self.cur and self.goto(r))
        self.keymap = [
            (Qt.Key_Left, "Previous move", lambda: self.goto(self.cur - 1)),
            (Qt.Key_Right, "Next move", lambda: self.goto(self.cur + 1)),
            (Qt.Key_Up, "Previous move", lambda: self.goto(self.cur - 1)),
            (Qt.Key_Down, "Next move", lambda: self.goto(self.cur + 1)),
            (Qt.Key_Home, "First position", lambda: self.goto(0)),
            (Qt.Key_End, "Last position", lambda: self.goto(len(self.basic))),
            (Qt.Key_PageUp, "Back 10 moves", lambda: self.goto(self.cur - 10)),
            (Qt.Key_PageDown, "Forward 10 moves", lambda: self.goto(self.cur + 10)),
            (Qt.Key_F, "Flip board", self.flip),
            (Qt.Key_B, "Show best line for current move", lambda: self.show_best(self.cur)),
            (QKeySequence("Ctrl+O"), "Open PGN", self.open_file),
            (QKeySequence("Ctrl+S"), "Save game", self.save_game),
        ]
        for key, _d, fn in self.keymap:
            QShortcut(QKeySequence(key), self, activated=fn)
        self.setStyleSheet("QMainWindow,QWidget{background:#2b2b2b;color:#ddd;} QTableWidget{background:#1f1f1f;gridline-color:#333;}"
                           "QPushButton{background:#444;border:1px solid #555;padding:3px 8px;} QHeaderView::section{background:#333;color:#ddd;}"
                           "QListWidget,QPlainTextEdit,QLineEdit,QSpinBox,QComboBox{background:#1f1f1f;}")

    # ------------------------------------------------------------ loading
    def ensure_book(self):
        if self.book is None:
            self.book = OpeningBook()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            self.load_path(u.toLocalFile()); break

    def open_file(self):
        p, _ = QFileDialog.getOpenFileName(self, "Open PGN", "", "PGN files (*.pgn);;All files (*)")
        if p:
            self.load_path(p)

    def load_path(self, p):
        with open(p, encoding="utf-8", errors="replace") as f:
            self.load_text(f.read())

    def paste(self):
        d = PasteDialog(self)
        if d.exec():
            self.load_text(d.text.toPlainText())

    def load_text(self, text):
        games = parse_input(text)
        if not games:
            QMessageBox.warning(self, "Chess Analyzer", "No valid PGN or FEN found."); return
        self.stop()
        self.games = games
        self.jobs = [Job(g) for g in games]
        self.ensure_book()
        self.game_combo.blockSignals(True)
        self.game_combo.clear()
        for i in range(len(games)):
            self.game_combo.addItem(self.combo_text(i))
        self.game_combo.setVisible(len(games) > 1)
        self.game_combo.blockSignals(False)
        self.game_combo.setCurrentIndex(0)
        self.pick_game(0)
        self.start_queue()

    def combo_text(self, i):
        h = self.games[i].headers
        j = self.jobs[i]
        if j.done:
            st = "✓"
        elif j.running:
            a, b = j.progress
            st = "… %d%%" % (100 * a // max(1, b))
        else:
            st = "queued"
        return "%d. %s – %s   [%s]" % (i + 1, h.get("White", "?"), h.get("Black", "?"), st)

    def refresh_combo(self, job=None):
        for i, j in enumerate(self.jobs):
            if job is None or j is job:
                self.game_combo.setItemText(i, self.combo_text(i))

    def pick_game(self, i):
        if i < 0 or i >= len(self.games):
            return
        self.job = self.jobs[i]
        self.game = self.games[i]
        self.results = self.job.results
        h = self.game.headers
        self.players.setText("%s  vs  %s   %s" % (h.get("White", "?"), h.get("Black", "?"), h.get("Result", "")))
        self.populate_basic()
        self.orient()
        for k in range(len(self.results)):
            self.set_row(k)
        self.refresh_graph()
        self.update_accuracy(final=self.job.done)
        self.goto(len(self.results) if self.job.running else 0)
        self.update_status()
        if not self.job.done and self.worker and self.worker.isRunning():
            self.worker.prioritize(self.job)       # analyse the game being viewed next
        elif not self.job.done and not self.job.running:
            self.start_queue()

    def orient(self):
        """Flip the board to the user's side when the player name (or a fixed side) is set."""
        color = self.settings.matched_color(self.game.headers)
        if color is None:
            color = {"white": chess.WHITE, "black": chess.BLACK}.get(self.settings.side)
        if color is not None:
            self.board.flipped = (color == chess.BLACK)
            self.board.update()

    def populate_basic(self):
        b = self.game.board()
        self.start_board = b.copy()
        rows = []
        for i, m in enumerate(self.game.mainline_moves()):
            rows.append((i + 1, b.turn, b.san(m), m, b.fen()))
            b.push(m)
        self.basic = rows
        self.fill_table()
        self.goto(0)

    # ------------------------------------------------------------ analysis (background queue)
    def start_queue(self):
        """Analyse every not-yet-done game in the background, the viewed game first."""
        if self.worker and self.worker.isRunning():
            return
        order = [self.job] + [j for j in self.jobs if j is not self.job] if self.job else list(self.jobs)
        pending = [j for j in order if not j.done]
        if not pending:
            return
        w = QueueWorker(self.holder, pending, self.settings, self.book)
        self.worker = w
        w.progress.connect(lambda j, a, b, w=w: self.worker is w and self.on_progress(j, a, b))
        w.move_ready.connect(lambda j, r, w=w: self.worker is w and self.on_move(j, r))
        w.job_done.connect(lambda j, ok, w=w: self.worker is w and self.on_job_done(j, ok))
        w.failed.connect(lambda m, w=w: self.worker is w and self.status.setText("Error: " + m))
        self.progress.setVisible(True)
        winutil.keep_awake(True)       # no sleep while analysing, even when tabbed out
        w.start()

    def restart_all(self):
        """Discard results and re-analyse everything (current game first)."""
        if not self.games:
            return
        self.stop()
        for j in self.jobs:
            j.results, j.done, j.running, j.progress = [], False, False, (0, 1)
        self.results = self.job.results
        self.fill_table()
        self.refresh_graph()
        self.update_accuracy(final=False)
        self.goto(0)
        self.refresh_combo()
        self.start_queue()

    def stop(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel_flag = True
            self.worker.wait(30000)
        winutil.keep_awake(False)
        self.setWindowTitle("Chess Analyzer")
        for j in self.jobs:
            j.running = False
        if self.games:
            self.refresh_combo()
            self.progress.setVisible(False)
            self.update_status()

    def update_status(self):
        j = self.job
        if j is None:
            return
        if j.done:
            self.status.setText("Analysis complete (%d moves)." % len(j.results))
        elif j.running:
            self.status.setText("Analyzing… results appear live. Other games continue in the background.")
        elif self.worker and self.worker.isRunning():
            self.status.setText("Queued – will be analysed next.")
        else:
            self.status.setText("Analysis stopped. Press Re-analyze to run it.")

    def on_progress(self, job, a, b):
        job.progress = (a, b)
        self.refresh_combo(job)
        done = sum(1 for j in self.jobs if j.done)
        self.setWindowTitle("Chess Analyzer – analysing %d/%d (%d%%)" % (
            min(done + 1, len(self.jobs)), len(self.jobs), 100 * a // max(1, b)))
        if job is self.job:
            self.progress.setVisible(True)
            self.progress.setMaximum(b); self.progress.setValue(a)
            self.update_status()

    def on_move(self, job, r):
        if r.ply == 1:
            job.results.clear()          # (re)starting this game's analysis
        prev = len(job.results)
        job.results.append(r)
        if job is not self.job:
            return
        frontier = self.cur >= prev       # the user is viewing the newest loaded position
        self.set_row(len(self.results) - 1)
        self.refresh_graph()
        self.update_accuracy(final=False)
        if frontier:
            self.goto(len(self.results))

    def on_job_done(self, job, ok):
        job.running = False
        job.done = ok
        self.refresh_combo(job)
        if job is self.job:
            self.progress.setVisible(any(j.running for j in self.jobs))
            if ok:
                for k in range(len(job.results)):
                    self.set_row(k)
                self.refresh_graph()
                self.update_accuracy(final=True)
                self.goto(self.cur)
            self.update_status()
        if not any(not j.done for j in self.jobs):
            self.progress.setVisible(False)
            winutil.keep_awake(False)
            self.setWindowTitle("Chess Analyzer")
            self.notify_done()

    def notify_done(self):
        """If the window is minimised / in the background, flash the taskbar and show a toast."""
        if self.isActiveWindow() and not self.isMinimized():
            return
        QApplication.alert(self, 0)
        if QSystemTrayIcon.isSystemTrayAvailable():
            if getattr(self, "tray", None) is None:
                self.tray = QSystemTrayIcon(self.windowIcon(), self)
            self.tray.show()
            self.tray.showMessage("Chess Analyzer", "Analysis finished for %d game(s)." % len(self.jobs),
                                  QSystemTrayIcon.Information, 6000)

    def refresh_graph(self):
        results = self.results
        if not results:
            self.graph.set_values([]); return
        vals = [results[0].eval_before if results[0].eval_before is not None else 0]
        labels = ["Start position"]
        for r in results:
            vals.append(r.eval_after if r.eval_after is not None else vals[-1])
            labels.append("%d%s %s" % ((r.ply + 1) // 2, "." if r.color else "…", r.san))
        self.graph.set_values(vals, labels)

    def update_accuracy(self, final):
        if not self.results:
            self.acc_label.setText(""); return
        summ = ACC.summarize(self.results)
        h = self.game.headers if self.game else {}
        fmt = lambda v: "–" if v is None else "%.1f%%" % v
        rows = ""
        for color, nm in ((chess.WHITE, h.get("White", "White")), (chess.BLACK, h.get("Black", "Black"))):
            d = summ[color]
            rating = "–" if d["rating"] is None else str(d["rating"])
            rows += ("<tr><td><b>%s</b></td><td>%s</td><td>%s</td><td>%s</td><td><b>%s</b></td><td><b>%s</b></td></tr>"
                     % (nm, fmt(d["opening"]), fmt(d["middlegame"]), fmt(d["endgame"]), fmt(d["overall"]), rating))
        title = "Final accuracy" if final else "Accuracy (live…)"
        self.acc_label.setText(
            "<b>%s</b><table cellspacing='6'><tr><th align='left'>Player</th><th>Opening</th><th>Middlegame</th>"
            "<th>Endgame</th><th>Overall</th><th>Est. rating</th></tr>%s</table>" % (title, rows))

    def fill_table(self):
        rows = self.basic
        self.table.setRowCount(len(rows) + 1)
        self.table.setItem(0, 1, QTableWidgetItem("Start position"))
        for c in (0, 2, 3, 4):
            self.table.setItem(0, c, QTableWidgetItem(""))
        self.table.setCellWidget(0, 5, self.best_button(0))
        for k in range(len(rows)):
            self.set_row(k)
            self.table.setCellWidget(k + 1, 5, self.best_button(k + 1))

    def alt_for(self, r):
        """Best alternative move (from the position before r) when r was an inaccuracy/mistake/blunder."""
        if r and r.symbol in ("?!", "?", "??", "miss") and r.pv_uci and r.pv_uci[0] != r.uci:
            return chess.Move.from_uci(r.pv_uci[0])
        return None

    def set_row(self, k):
        ply, color, san, mv, fen = self.basic[k]
        row = k + 1
        r = self.results[k] if k < len(self.results) else None
        num = "%d%s" % ((ply + 1) // 2, "." if color else "…")
        self.table.setItem(row, 0, QTableWidgetItem(num))
        self.table.setItem(row, 1, QTableWidgetItem(san))
        sym = r.symbol if r else ""
        it = QTableWidgetItem("")
        it.setTextAlignment(Qt.AlignCenter)
        if sym:
            pm = icons.pixmap_for_key(sym, 22) if styles.mode == "icons" else None
            if pm is not None:
                it.setIcon(QIcon(pm))
            else:
                it.setText(styles.symbol(sym))
                it.setForeground(QColor(styles.color(sym)))
                f = it.font(); f.setBold(True); it.setFont(f)
            tip = styles.name(sym)
            if r.best_san and self.alt_for(r):
                tip += " – best was " + r.best_san
            it.setToolTip(tip)
        self.table.setItem(row, 2, it)
        self.table.setItem(row, 3, QTableWidgetItem(r.eval_after_text if r else ""))
        self.table.setItem(row, 4, QTableWidgetItem((r.opening if r and r.book else "")))

    # ------------------------------------------------------------ saving
    NAGS = {"!!": chess.pgn.NAG_BRILLIANT_MOVE, "!": chess.pgn.NAG_GOOD_MOVE, "?!": chess.pgn.NAG_DUBIOUS_MOVE,
            "?": chess.pgn.NAG_MISTAKE, "??": chess.pgn.NAG_BLUNDER}

    def annotated_pgn(self, idx):
        """PGN text of game idx with NAGs, [%eval] and a short comment per analysed move."""
        game, job = self.games[idx], self.jobs[idx]
        copy = chess.pgn.read_game(io.StringIO(str(game)))     # never mutate the loaded game
        results = job.results
        node, k = copy, 0
        last_open = None
        while node.variations and k < len(results):
            node = node.variations[0]
            r = results[k]
            k += 1
            parts = []
            if r.symbol in self.NAGS:
                node.nags.add(self.NAGS[r.symbol])
            if r.symbol:
                parts.append(styles.name(r.symbol))
            if r.eval_after is not None:
                ev = r.eval_after_text or ("%+.2f" % (r.eval_after / 100.0))
                parts.append("[%%eval %s]" % (ev.lstrip("+") if not ev.startswith("#") and not ev.startswith("-#") else ev))
            if r.symbol in ("?!", "?", "??", "miss") and r.best_san and r.best_san != r.san:
                parts.append("best was " + r.best_san)
            if r.opening:
                last_open = (r.eco, r.opening)
            if parts:
                node.comment = " ".join(parts)
        if last_open:
            copy.headers["ECO"], copy.headers["Opening"] = last_open
        copy.headers["Annotator"] = "Chess Analyzer (Stockfish, depth %d)" % self.settings.depth
        exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=True)
        return copy.accept(exporter)

    def save_game(self):
        if not self.games:
            QMessageBox.information(self, "Chess Analyzer", "Open a game first."); return
        h = self.game.headers
        default = "%s-vs-%s.pgn" % (h.get("White", "White"), h.get("Black", "Black"))
        default = "".join(c if c.isalnum() or c in "-_. " else "_" for c in default)
        path, _ = QFileDialog.getSaveFileName(self, "Save analysed game", default, "PGN files (*.pgn)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.annotated_pgn(self.games.index(self.game)) + "\n")
            self.status.setText("Saved %s" % path)

    def save_all(self):
        if not self.games:
            QMessageBox.information(self, "Chess Analyzer", "Open a game first."); return
        path, _ = QFileDialog.getSaveFileName(self, "Save all analysed games", "analysed-games.pgn", "PGN files (*.pgn)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(self.annotated_pgn(i) for i in range(len(self.games))) + "\n")
            self.status.setText("Saved %d game(s) to %s" % (len(self.games), path))

    def best_button(self, row):
        b = QPushButton("Best")
        b.clicked.connect(lambda _=False, r=row: self.show_best(r))
        return b

    # ------------------------------------------------------------ navigation
    def board_at(self, idx):
        b = self.start_board.copy()
        for k in range(idx):
            b.push(self.basic[k][3])
        return b

    def goto(self, idx):
        if not self.game:
            return
        idx = max(0, min(idx, len(self.basic)))
        self.cur = idx
        b = self.board_at(idx)
        mv = self.basic[idx - 1][3] if idx else None
        r = self.results[idx - 1] if idx and idx - 1 < len(self.results) else None
        self.board.set_position(b, mv, r.symbol if r else "", self.alt_for(r), self.end_badges(b, idx))
        self.table.selectRow(idx)
        cp, txt = None, ""
        if r and r.eval_after is not None:
            cp, txt = r.eval_after, r.eval_after_text
        elif idx == 0 and self.results and self.results[0].eval_before is not None:
            cp = self.results[0].eval_before
        self.evalbar.set_eval(cp, txt)
        name = "–"
        for k in range(idx, 0, -1):
            if k - 1 < len(self.results) and self.results[k - 1].opening:
                name = "%s  %s" % (self.results[k - 1].eco, self.results[k - 1].opening); break
        self.opening_label.setText("Opening: " + name)

    def end_badges(self, b, idx):
        """Checkmate / draw / resignation markers on the kings of the final position."""
        if idx == 0 or idx != len(self.basic) or self.game is None:
            return []
        result = self.game.headers.get("Result", "*")
        term = self.game.headers.get("Termination", "").lower()
        wk, bk = b.king(chess.WHITE), b.king(chess.BLACK)
        if b.is_checkmate():
            return [(b.king(b.turn), "checkmate_white" if b.turn else "checkmate_black")]
        if b.is_game_over() or result == "1/2-1/2":
            return [(wk, "draw_white"), (bk, "draw_black")]
        if result in ("1-0", "0-1") and "time" not in term and "abandon" not in term:
            loser = chess.BLACK if result == "1-0" else chess.WHITE
            return [(b.king(loser), "resign_white" if loser else "resign_black")]
        return []

    def flip(self):
        self.board.flipped = not self.board.flipped
        self.board.update()

    def show_keys(self):
        lines = []
        for key, desc, _fn in self.keymap:
            lines.append("%s: %s" % (QKeySequence(key).toString(), desc))
        QMessageBox.information(self, "Keyboard shortcuts", "\n".join(lines))

    # ------------------------------------------------------------ best lines
    def show_best(self, row):
        self.goto(row)
        fen = self.board_at(row).fen()
        self.line_title.setText("Best line from this position (analyzing…)")
        self.line_list.clear()
        if 0 < row <= len(self.results) and self.results[row - 1].pv and self.results[row - 1].analysed:
            r = self.results[row - 1]
            self.fill_lines([(("%+.2f" % (r.eval_before / 100.0)) if r.eval_before is not None else "", r.pv, r.pv_uci)], fen)
        w = LineWorker(self.holder, fen, self.settings)
        w.done.connect(self.fill_lines)
        w.failed.connect(lambda m: self.line_title.setText("Error: " + m))
        self.line_workers.append(w)
        w.start()

    def fill_lines(self, lines, fen):
        if self.board_at(self.cur).fen() != fen:
            return
        self.line_title.setText("Best lines (click a move to preview it on the board)")
        self.line_list.clear()
        self.current_lines, self.current_fen = lines, fen
        from PySide6.QtWidgets import QListWidgetItem
        b = chess.Board(fen)
        for li, (ev, san, ucis) in enumerate(lines):
            bb = b.copy(); parts = []
            for s in san:
                num = ""
                if bb.turn:
                    num = "%d. " % bb.fullmove_number
                elif not parts:
                    num = "%d… " % bb.fullmove_number
                parts.append(num + s)
                bb.push_san(s)
            it = QListWidgetItem("[%s]  %s" % (ev, " ".join(parts)))
            it.setData(Qt.UserRole, li)
            self.line_list.addItem(it)

    def on_line_clicked(self, item):
        # preview: show position after full best line
        li = item.data(Qt.UserRole)
        ev, san, ucis = self.current_lines[li]
        b = chess.Board(self.current_fen)
        last = None
        for u in ucis:
            last = chess.Move.from_uci(u); b.push(last)
        self.board.set_position(b, last, "")

    def open_settings(self):
        d = SettingsDialog(self.settings, self)
        if d.exec():
            self.settings = d.result_settings()
            s = self.settings
            for k, v in (("scope", s.scope), ("side", s.side), ("name", s.player_name), ("depth", s.depth),
                         ("threads", s.threads), ("hash", s.hash_mb), ("engine", s.engine_path),
                         ("preset", s.preset)):
                self.qs.setValue(k, v)
            styles.set_all(d.result_styles())
            styles.save(self.qs)
            self.qs.setValue("lenient", s.lenient_brilliant)
            styles.mode = d.mode.currentData()
            styles.save(self.qs)
            self.stop()
            self.holder.close()
            if self.game:
                self.orient()
                self.restart_all()

    def closeEvent(self, e):
        try:
            self.stop()
        finally:
            self.holder.close()
        super().closeEvent(e)


def selftest():
    import chess.pgn as P
    g = P.read_game(io.StringIO("1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Qe7 *"))
    s = A.Settings(depth=8)
    eng = A.open_engine(s)
    try:
        res = A.analyse_game(g, s, eng, OpeningBook())
    finally:
        eng.quit()
    print([(r.san, r.symbol) for r in res])
    return 0 if len(res) == 10 and res[0].symbol == "/" else 1


def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    winutil.disable_throttle()          # stay at full speed when the window is in the background
    app = QApplication(sys.argv)
    icon = QIcon(resource_path("icon.ico"))
    app.setWindowIcon(icon)
    w = MainWindow()
    w.setWindowIcon(icon)
    w.show()
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        w.load_path(sys.argv[1])
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
