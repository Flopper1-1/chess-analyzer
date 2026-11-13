import ctypes
import io
import math
import os
import sys
import threading
import time
try:
    import winsound
except ImportError:
    winsound = None

import chess
import chess.pgn
from PySide6.QtCore import Qt, QThread, Signal, QSettings, QRectF, QPointF, QSize, QEvent, QTimer, QUrl
from PySide6.QtGui import (
    QPainter, QColor, QFont, QFontMetrics, QPen, QBrush, QShortcut, QKeySequence, QIcon, QPixmap,
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QFileDialog, QDialog, QPlainTextEdit, QDialogButtonBox, QFormLayout,
    QComboBox, QLineEdit, QSpinBox, QProgressBar, QListWidget, QListWidgetItem, QHeaderView, QMessageBox,
    QAbstractItemView, QSizePolicy, QToolBar, QToolTip, QColorDialog, QTabWidget, QGridLayout,
    QSlider, QStackedWidget, QScrollArea, QCheckBox, QFrame, QSystemTrayIcon, QInputDialog,
)

import analysis as A
import classify as C
from openings import OpeningBook, resource_path
import styles
import icons
import winutil
import accuracy as ACC
import library as LIB
import themes
import updater

APP_TITLE = "Holly's Chess Analyzer"
APP_VERSION = updater.APP_VERSION


def elide_profile_name(name: str, max_chars: int = 16, font_metrics=None, max_px: int = 125) -> str:
    """Truncate a profile name so it ends in '...' if it gets too large and can't fit."""
    clean = (name or "").strip()
    if not clean:
        return ""
    if font_metrics is not None:
        try:
            if font_metrics.horizontalAdvance(clean) > max_px:
                elided = font_metrics.elidedText(clean, Qt.ElideRight, max_px)
                elided = elided.replace("\u2026", "...")
                if not elided.endswith("..."):
                    elided = elided.rstrip(".") + "..."
                return elided
        except Exception:
            pass
    if len(clean) > max_chars:
        cut = max(1, max_chars - 3)
        return clean[:cut].rstrip() + "..."
    return clean


def should_show_board_avatar(
    player_name: str,
    side_color: bool,
    headers: dict = None,
    fallback_color: str = "white",
) -> bool:
    """Return True if the user's square profile picture should appear next to this side on the board.

    If the user has NOT set their player name, their profile picture never appears on the board.
    """
    clean_name = (player_name or "").strip()
    if not clean_name:
        return False
    if headers:
        resolved_uc, _matched = LIB.resolve_user_color(
            headers.get("White", ""),
            headers.get("Black", ""),
            clean_name,
            fallback_color,
        )
        target = chess.BLACK if resolved_uc == "black" else chess.WHITE
        return bool(side_color == target)
    target = chess.BLACK if (fallback_color or "").strip().lower() == "black" else chess.WHITE
    return bool(side_color == target)

PIECES = {"K": "♔", "Q": "♕", "R": "♖", "B": "♗", "N": "♘", "P": "♙",
          "k": "♚", "q": "♛", "r": "♜", "b": "♝", "n": "♞", "p": "♟"}


class SoundPlayer:
    """Zero-latency sound effect player supporting templates, .wav, .mp3, and per-annotation sounds."""

    def __init__(self):
        self.enabled = True
        self.template_id = "original"
        self._events = {}
        self._annotations = {}
        self._mci_seq = 0
        self.set_template("original")

    def set_template(self, template_id: str) -> None:
        self.template_id = template_id or "original"
        tpl = themes.get_sound_template(self.template_id)
        self._events = dict(tpl.get("events") or {})
        self._annotations = dict(tpl.get("annotations") or {})

    def _play_file(self, path: str) -> None:
        if not path or not os.path.exists(path):
            return
        low = path.lower()
        if low.endswith(".wav") and winsound is not None:
            try:
                winsound.PlaySound(
                    path,
                    winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
                )
                return
            except Exception:
                pass
        if sys.platform == "win32":
            try:
                winmm = ctypes.windll.winmm
                self._mci_seq = (self._mci_seq + 1) % 64
                alias = f"hca_snd_{self._mci_seq}"
                winmm.mciSendStringW(f"close {alias}", None, 0, None)
                winmm.mciSendStringW(f'open "{path}" alias {alias}', None, 0, None)
                winmm.mciSendStringW(f"play {alias}", None, 0, None)
            except Exception:
                pass

    def play(self, name: str) -> None:
        if not self.enabled:
            return
        self._play_file(self._events.get(name, ""))

    def play_for_move(self, event_name: str, symbol: str = "") -> None:
        if not self.enabled:
            return
        if symbol and symbol in self._annotations:
            path = self._annotations.get(symbol, "")
            if path:
                self._play_file(path)
                return
        self._play_file(self._events.get(event_name, ""))


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
        self.board_template = dict(themes.BUILTIN_BOARDS[0])
        self.new_years_colors = []
        self.piece_template = {"id": "default", "name": "Default", "locked": True, "pieces": {}}
        self._tile_cache = {}
        self._piece_cache = {}
        # Piece slide & flashy Brilliant (!!) animation state
        self.anim_move = None
        self.anim_piece = None
        self.anim_progress = 1.0
        self.anim_is_brilliant = False
        self.anim_start_time = 0.0
        self.anim_duration = 0.56
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(16)
        self.anim_timer.timeout.connect(self._tick_anim)
        self.setMinimumSize(380, 380)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_position(self, board, last_move=None, badge="", alt_move=None, end_badges=None, animate=True):
        self.board, self.last_move, self.badge = board, last_move, badge
        self.alt_move, self.end_badges = alt_move, end_badges or []
        if animate and last_move is not None and board is not None:
            pc = board.piece_at(last_move.to_square)
            if pc is not None:
                self.anim_move = last_move
                self.anim_piece = pc
                self.anim_is_brilliant = (badge == "!!")
                self.anim_progress = 0.0
                self.anim_start_time = time.perf_counter()
                self.anim_duration = 0.56 if self.anim_is_brilliant else 0.16
                if not self.anim_timer.isActive():
                    self.anim_timer.start()
            else:
                self._stop_anim()
        else:
            self._stop_anim()
        self.update()

    def _stop_anim(self):
        if self.anim_timer.isActive():
            self.anim_timer.stop()
        self.anim_move = None
        self.anim_piece = None
        self.anim_progress = 1.0
        self.anim_is_brilliant = False

    def _tick_anim(self):
        elapsed = time.perf_counter() - self.anim_start_time
        if elapsed >= self.anim_duration:
            self._stop_anim()
        else:
            self.anim_progress = max(0.0, min(1.0, elapsed / max(0.001, self.anim_duration)))
        self.update()

    def draw_badge(self, p, r, key, corner="tr", slide_t=1.0):
        d = r.width() * 0.42
        scale = 1.0
        offset_x = 0.0
        offset_y = 0.0
        opacity = 1.0
        if slide_t < 1.0:
            # Elastic pop-in after piece impact (t = 0.30..1.0)
            bt = max(0.0, min(1.0, (slide_t - 0.30) / 0.70))
            if bt <= 0.0:
                return
            opacity = min(1.0, bt * 2.2)
            # Elastic overshoot: rises to ~1.34x then settles at 1.0x
            overshoot = math.sin(bt * math.pi) * 0.34 * (1.0 - bt * 0.4)
            ease = 1.0 - (1.0 - bt) ** 3
            scale = 0.35 + 0.65 * ease + overshoot
            offset_x = (1.0 - ease) * (-d * 0.55)
            offset_y = (1.0 - ease) * (d * 0.45)
        w = d * scale
        x = (r.right() - d * 0.9 if corner == "tr" else r.left() - d * 0.1) + (d - w) * 0.5 + offset_x
        y = (r.top() - d * 0.1) + (d - w) * 0.5 + offset_y
        c = QRectF(x, y, w, w)
        if key == "!!" and slide_t < 1.0:
            # Expanding cyan halo behind the Brilliant badge
            bt = max(0.0, min(1.0, (slide_t - 0.30) / 0.70))
            halo_r = d * (0.55 + 0.65 * bt)
            halo_alpha = int(200 * (1.0 - bt) ** 1.4)
            if halo_alpha > 0:
                p.save()
                p.setPen(QPen(QColor(38, 198, 218, halo_alpha), max(1.5, d * 0.10)))
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(c.center(), halo_r, halo_r)
                p.restore()
        if styles.mode == "icons":
            pm = icons.pixmap_for_key(key, max(8, int(d * 2)))
            if pm is not None:
                p.save()
                if opacity < 1.0:
                    p.setOpacity(opacity)
                p.drawPixmap(c.toRect(), pm)
                p.restore()
                return
        if key in LEGACY_END:
            sym, bg, fg = LEGACY_END[key]
        else:
            sym, bg, fg = styles.symbol(key), styles.color(key), "#ffffff"
        p.save()
        if opacity < 1.0:
            p.setOpacity(opacity)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(bg))
        p.drawEllipse(c)
        p.setPen(QColor(fg))
        f = QFont("Segoe UI", max(6, int(w * 0.38)), QFont.Bold)
        f.setFamilies(["Segoe UI", "Segoe UI Emoji", "Segoe UI Symbol"])
        p.setFont(f)
        p.drawText(c, Qt.AlignCenter, sym)
        p.restore()

    def set_board_theme(self, board_tpl: dict, new_years_colors: list = None):
        self.board_template = dict(board_tpl or themes.BUILTIN_BOARDS[0])
        self.new_years_colors = list(new_years_colors or [])
        self._tile_cache.clear()
        self.update()

    def set_piece_theme(self, piece_tpl: dict):
        self.piece_template = dict(piece_tpl or {"id": "default", "name": "Default", "locked": True, "pieces": {}})
        self._piece_cache.clear()
        self.update()

    def _tile_pixmap(self, path: str, size: int):
        if not path or not os.path.exists(path):
            return None
        key = (path, size)
        pm = self._tile_cache.get(key)
        if pm is None:
            src = QPixmap(path)
            if src.isNull():
                return None
            pm = src.scaled(size, size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            self._tile_cache[key] = pm
        return pm

    def _piece_pixmap(self, pc: chess.Piece, size: int):
        pieces = self.piece_template.get("pieces") or {}
        if not pieces:
            return None
        pkey = ("w" if pc.color else "b") + pc.symbol().upper()
        path = pieces.get(pkey, "")
        if not path or not os.path.exists(path):
            return None
        key = (path, size)
        pm = self._piece_cache.get(key)
        if pm is None:
            src = QPixmap(path)
            if src.isNull():
                return None
            pm = src.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._piece_cache[key] = pm
        return pm

    def _draw_piece(self, p, r, pc, scale=1.0):
        sq_size = max(8, int(round(r.width() * scale)))
        pm = self._piece_pixmap(pc, sq_size)
        if pm is not None:
            if abs(scale - 1.0) > 0.005:
                dw = r.width() * (scale - 1.0) * 0.5
                dh = r.height() * (scale - 1.0) * 0.5
                target = r.adjusted(-dw, -dh, dw, dh)
            else:
                target = r
            p.drawPixmap(target.toRect(), pm)
            return
        self._draw_piece_glyph(p, r, pc, scale=scale)

    @staticmethod
    def _draw_piece_glyph(p, r, pc, scale=1.0):
        sym = pc.symbol()
        glyph = PIECES[sym.lower()]
        p.save()
        if abs(scale - 1.0) > 0.005:
            f = QFont(p.font())
            f.setPointSizeF(max(8.0, f.pointSizeF() * scale))
            p.setFont(f)
        outline = QColor("#000") if pc.color else QColor("#fff")
        p.setPen(outline)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            p.drawText(r.translated(dx, dy), Qt.AlignCenter, glyph)
        p.setPen(QColor("#ffffff") if pc.color else QColor("#000000"))
        p.drawText(r, Qt.AlignCenter, glyph)
        p.restore()

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

        animating = self.anim_move is not None and self.anim_progress < 1.0
        if animating and self.anim_is_brilliant:
            # Flight completes in first 45% of duration; impact shockwaves & sparkles run 38%..100%
            flight_raw = min(1.0, self.anim_progress / 0.45)
            flight_ease = 1.0 - (1.0 - flight_raw) ** 3
        elif animating:
            flight_raw = self.anim_progress
            flight_ease = 1.0 - (1.0 - self.anim_progress) ** 3
        else:
            flight_raw = 1.0
            flight_ease = 1.0

        is_ny = bool(self.board_template.get("random_light"))
        light_hex = self.board_template.get("light_hex") or "#f0d9b5"
        dark_hex = self.board_template.get("dark_hex") or "#b58863"
        light_img_path = self.board_template.get("light_img") or ""
        dark_img_path = self.board_template.get("dark_img") or ""
        light_pm = self._tile_pixmap(light_img_path, max(8, s)) if not is_ny else None
        dark_pm = self._tile_pixmap(dark_img_path, max(8, s))
        ny_idx = 0

        for sq in chess.SQUARES:
            light = (chess.square_file(sq) + chess.square_rank(sq)) % 2 == 1
            sq_rect = rect(sq)
            if light and is_ny:
                c_hex = self.new_years_colors[ny_idx % len(self.new_years_colors)] if self.new_years_colors else "#ffd54f"
                ny_idx += 1
                p.fillRect(sq_rect, QColor(c_hex))
            elif light and light_pm is not None:
                p.drawPixmap(sq_rect.toRect(), light_pm)
            elif (not light) and dark_pm is not None:
                p.drawPixmap(sq_rect.toRect(), dark_pm)
            else:
                col = QColor(light_hex) if light else QColor(dark_hex)
                p.fillRect(sq_rect, col)

            if self.last_move and sq in (self.last_move.from_square, self.last_move.to_square):
                if self.badge == "!!":
                    hl = QColor(92, 214, 229, 155) if light else QColor(38, 166, 184, 155)
                else:
                    hl = QColor(205, 210, 106, 145) if light else QColor(170, 162, 58, 145)
                p.fillRect(sq_rect, hl)

        # Flashy Brilliant (!!) trail, impact flash, dual shockwave rings & starburst sparks
        if self.badge == "!!" and self.last_move:
            r_from = rect(self.last_move.from_square)
            r_to = rect(self.last_move.to_square)
            if animating and self.anim_is_brilliant:
                cur_center = QPointF(
                    r_from.center().x() + (r_to.center().x() - r_from.center().x()) * flight_ease,
                    r_from.center().y() + (r_to.center().y() - r_from.center().y()) * flight_ease,
                )
                fade = max(0.0, 1.0 - max(0.0, (self.anim_progress - 0.35) / 0.65))
                if fade > 0.0:
                    # Outer cyan comet glow
                    outer_pen = QPen(QColor(38, 198, 218, int(185 * fade)), s * 0.28, Qt.SolidLine, Qt.RoundCap)
                    p.setPen(outer_pen)
                    p.drawLine(r_from.center(), cur_center)
                    # Inner bright cyan-white core
                    core_pen = QPen(QColor(224, 247, 250, int(235 * fade)), s * 0.11, Qt.SolidLine, Qt.RoundCap)
                    p.setPen(core_pen)
                    p.drawLine(r_from.center(), cur_center)

                # Impact effects once the piece reaches the destination square
                if self.anim_progress >= 0.36:
                    imp_t = min(1.0, (self.anim_progress - 0.36) / 0.64)
                    # 1. Square white-cyan impact flash
                    flash_alpha = int(195 * (1.0 - imp_t) ** 2.2)
                    if flash_alpha > 0:
                        p.fillRect(r_to, QColor(224, 247, 250, flash_alpha))
                    # 2. Primary expanding cyan shockwave ring
                    ring1_r = s * (0.38 + 1.05 * (1.0 - (1.0 - imp_t) ** 2))
                    ring1_alpha = int(240 * (1.0 - imp_t) ** 1.5)
                    if ring1_alpha > 0:
                        p.setPen(QPen(QColor(38, 198, 218, ring1_alpha), max(2.0, s * 0.09 * (1.0 - imp_t * 0.6))))
                        p.setBrush(Qt.NoBrush)
                        p.drawEllipse(r_to.center(), ring1_r, ring1_r)
                    # 3. Secondary bright shockwave ring
                    if imp_t > 0.12:
                        imp2_t = min(1.0, (imp_t - 0.12) / 0.88)
                        ring2_r = s * (0.30 + 0.85 * imp2_t)
                        ring2_alpha = int(210 * (1.0 - imp2_t) ** 1.6)
                        if ring2_alpha > 0:
                            p.setPen(QPen(QColor(178, 235, 242, ring2_alpha), max(1.5, s * 0.05 * (1.0 - imp2_t * 0.5))))
                            p.drawEllipse(r_to.center(), ring2_r, ring2_r)
                    # 4. 8-ray starburst sparks radiating from destination square
                    spark_alpha = int(245 * (1.0 - imp_t) ** 1.4)
                    if spark_alpha > 0:
                        p.setPen(QPen(QColor(224, 247, 250, spark_alpha), max(2.0, s * 0.055), Qt.SolidLine, Qt.RoundCap))
                        cx, cy = r_to.center().x(), r_to.center().y()
                        r_in = s * (0.34 + 0.58 * imp_t)
                        r_out = s * (0.52 + 0.84 * imp_t)
                        for k in range(8):
                            ang = k * (math.pi / 4.0)
                            p1 = QPointF(cx + math.cos(ang) * r_in, cy + math.sin(ang) * r_in)
                            p2 = QPointF(cx + math.cos(ang) * r_out, cy + math.sin(ang) * r_out)
                            p.drawLine(p1, p2)

            glow_pen = QPen(QColor(38, 198, 218, 230), max(2.5, s * 0.065))
            p.setPen(glow_pen)
            p.setBrush(Qt.NoBrush)
            p.drawRect(r_to.adjusted(1.5, 1.5, -1.5, -1.5))

        font = QFont("Segoe UI Symbol", int(s * 0.62))
        p.setFont(font)
        for sq, pc in self.board.piece_map().items():
            if animating and self.anim_move and sq == self.anim_move.to_square:
                continue
            self._draw_piece(p, rect(sq), pc)

        if animating and self.anim_move and self.anim_piece is not None:
            r_from = rect(self.anim_move.from_square)
            r_to = rect(self.anim_move.to_square)
            ix = r_from.x() + (r_to.x() - r_from.x()) * flight_ease
            iy = r_from.y() + (r_to.y() - r_from.y()) * flight_ease
            anim_rect = QRectF(ix, iy, s, s)
            p_scale = 1.0
            if self.anim_is_brilliant and flight_raw < 1.0:
                p_scale = 1.0 + 0.30 * math.sin(flight_raw * math.pi)
            self._draw_piece(p, anim_rect, self.anim_piece, scale=p_scale)

        # best alternative: arrow + icon on the destination square
        if self.alt_move:
            a, b = rect(self.alt_move.from_square).center(), rect(self.alt_move.to_square).center()
            pen = QPen(QColor(107, 163, 107, 190), s * 0.14, Qt.SolidLine, Qt.RoundCap)
            p.setPen(pen)
            p.drawLine(a, b)
            ang = math.atan2(b.y() - a.y(), b.x() - a.x())
            for da in (2.6, -2.6):
                p.drawLine(b, QPointF(b.x() + math.cos(ang + da) * s * 0.3, b.y() + math.sin(ang + da) * s * 0.3))
            self.draw_badge(p, rect(self.alt_move.to_square), "alt", "tl")
        if self.badge and self.last_move:
            slide_t = self.anim_progress if (animating and self.anim_is_brilliant) else 1.0
            self.draw_badge(p, rect(self.last_move.to_square), self.badge, "tr", slide_t=slide_t)
        for sq, key in self.end_badges:
            self.draw_badge(p, rect(sq), key, "tr")


class EvalBar(QWidget):
    def __init__(self):
        super().__init__()
        self.cp = 0
        self.text = "0.0"
        self.formula = "improved"
        self.is_start = True
        self.setFixedWidth(44)

    def set_eval(self, cp, text="", is_start=False):
        self.is_start = bool(is_start)
        if self.is_start:
            self.cp = 0
            self.text = "0.0"
            self.update()
            return
        self.cp = 0 if cp is None else cp
        if text in ("+0.00", "-0.00", "0.00", "+0.0", "-0.0", "0.0"):
            self.cp = 0
            text = "0.0"
        elif not text:
            if cp is None or cp == 0:
                text = "0.0"
            else:
                text = ("%+.1f" % (cp / 100.0)) if abs(cp) < 9000 else ("M" if cp > 0 else "-M")
        self.text = text or "0.0"
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        h, w = self.height(), self.width()
        pct = C.eval_bar_pct(self.cp, mode=self.formula, is_start=self.is_start)
        white_h = h * pct / 100.0
        p.fillRect(0, 0, w, h, QColor("#333"))
        p.fillRect(0, int(round(h - white_h)), w, int(round(white_h)) + 1, QColor("#eee"))
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
        self.formula = "improved"
        self.hover = -1
        self.bg_color = "#262626"
        self.white_fill = "#d9d9d9"
        self.mid_color = "#777777"
        self.border_color = "#3f3f46"
        self.setMouseTracking(True)
        self.setMinimumHeight(70)
        self.setMaximumHeight(90)

    def set_theme(self, bg_hex: str, fill_hex: str, mid_hex: str, border_hex: str = "#3f3f46") -> None:
        self.bg_color = bg_hex
        self.white_fill = fill_hex
        self.mid_color = mid_hex
        self.border_color = border_hex
        self.update()

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
        p.fillRect(self.rect(), QColor(self.bg_color))
        if len(self.values) >= 2:
            w, h = self.width(), self.height()
            pts = [
                QPointF(
                    i * w / (len(self.values) - 1),
                    h - h * C.eval_bar_pct(v, mode=self.formula, is_start=(i == 0 and v == 0)) / 100.0,
                )
                for i, v in enumerate(self.values)
            ]
            poly = [QPointF(0, h)] + pts + [QPointF(w, h)]
            from PySide6.QtGui import QPolygonF
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(self.white_fill))
            p.drawPolygon(QPolygonF(poly))
            p.setPen(QPen(QColor(self.mid_color), 1))
            p.drawLine(0, h // 2, w, h // 2)
            if self.hover >= 0:
                x = int(pts[self.hover].x())
                p.setPen(QPen(QColor("#e8b923"), 1))
                p.drawLine(x, 0, x, h)
                p.setBrush(QColor("#e8b923"))
                p.drawEllipse(pts[self.hover], 3, 3)
        p.setPen(QPen(QColor(self.border_color), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))


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
        self.title = ""
        self.lib_id = None
        self.new_years_colors = themes.generate_new_years_palette()


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


class UpdateCheckWorker(QThread):
    finished_check = Signal(dict)
    failed = Signal(str)

    def __init__(self, current_version: str = APP_VERSION):
        super().__init__()
        self.current_version = current_version

    def run(self):
        try:
            info = updater.check_for_updates(self.current_version)
            self.finished_check.emit(info)
        except Exception as e:
            self.failed.emit(str(e))


class UpdateDownloadWorker(QThread):
    progress = Signal(int, int)
    finished_download = Signal(str)
    failed = Signal(str)

    def __init__(self, download_url: str, dest_path: str):
        super().__init__()
        self.download_url = download_url
        self.dest_path = dest_path

    def run(self):
        try:
            out = updater.download_update(
                self.download_url,
                self.dest_path,
                progress_cb=lambda done, tot: self.progress.emit(done, tot),
            )
            self.finished_download.emit(out)
        except Exception as e:
            self.failed.emit(str(e))


class ChannelCheckWorker(QThread):
    finished_channels = Signal(dict)
    failed = Signal(str)

    def __init__(self, current_version: str = APP_VERSION):
        super().__init__()
        self.current_version = current_version

    def run(self):
        try:
            info = updater.check_release_channels(self.current_version)
            self.finished_channels.emit(info)
        except Exception as e:
            self.failed.emit(str(e))


class PlayerBarWidget(QFrame):
    """Player bar displayed on a player's side of the board (top or bottom).

    Shows:
      - Side piece-color square badge
      - Player name (and rating if available)
      - Square profile picture immediately to the right of the player's name (only when
        the user has set their name and this side matches the user)
      - Colored timer badge next to their name (White timer = white bg / black text;
        Black timer = black bg / white text)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PlayerBar")
        self.setStyleSheet(
            "QFrame#PlayerBar { background:#232323; border:1px solid #3a3a3a; border-radius:4px; }"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(8)

        self.color_chip = QLabel()
        self.color_chip.setFixedSize(12, 12)
        lay.addWidget(self.color_chip)

        self.name_label = QLabel("White")
        self.name_label.setTextFormat(Qt.RichText)
        self.name_label.setStyleSheet("font-size:13px; color:#e6e6e6; border:none; background:transparent;")
        lay.addWidget(self.name_label)

        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(24, 24)
        self.avatar_label.setStyleSheet("border:1px solid #555; background:#1f1f1f;")
        self.avatar_label.setVisible(False)
        lay.addWidget(self.avatar_label)

        self.clock_label = QLabel("--:--")
        self.clock_label.setAlignment(Qt.AlignCenter)
        self.clock_label.setMinimumWidth(62)
        lay.addWidget(self.clock_label)

        lay.addStretch(1)
        self.side_color = chess.WHITE
        self.set_player(chess.WHITE, "White", "", "--:--", show_avatar=False)

    def set_player(
        self,
        side_color: bool,
        name: str,
        rating: str = "",
        clock_text: str = "--:--",
        show_avatar: bool = False,
    ) -> None:
        self.side_color = bool(side_color)
        if self.side_color == chess.WHITE:
            self.color_chip.setStyleSheet(
                "background:#f0f0f0; border:1px solid #888; border-radius:2px;"
            )
            self.clock_label.setStyleSheet(
                "background:#f0f0f0; color:#141414; border:1px solid #bbbbbb; "
                "border-radius:3px; padding:2px 8px; font-family:'Consolas','Segoe UI',monospace; "
                "font-size:13px; font-weight:bold;"
            )
        else:
            self.color_chip.setStyleSheet(
                "background:#141414; border:1px solid #666; border-radius:2px;"
            )
            self.clock_label.setStyleSheet(
                "background:#141414; color:#f0f0f0; border:1px solid #555555; "
                "border-radius:3px; padding:2px 8px; font-family:'Consolas','Segoe UI',monospace; "
                "font-size:13px; font-weight:bold;"
            )
        disp_name = (name or ("White" if self.side_color else "Black")).strip()
        rat_html = f" <span style='color:#9e9e9e;font-weight:normal;'>({rating})</span>" if rating else ""
        self.name_label.setText(f"<b>{disp_name}</b>{rat_html}")
        self.clock_label.setText(clock_text if clock_text else "--:--")
        if show_avatar:
            pm = icons.profile_pixmap(24)
            if pm is not None and not pm.isNull():
                self.avatar_label.setPixmap(pm)
            self.avatar_label.setVisible(True)
        else:
            self.avatar_label.setVisible(False)

    def set_clock(self, clock_text: str) -> None:
        self.clock_label.setText(clock_text if clock_text else "--:--")

    def set_theme(self, panel_bg: str, text_fg: str, border_fg: str) -> None:
        self.setStyleSheet(
            f"QFrame#PlayerBar {{ background:{panel_bg}; border:1px solid {border_fg}; border-radius:4px; }}"
        )
        self.name_label.setStyleSheet(
            f"font-size:13px; color:{text_fg}; border:none; background:transparent;"
        )


class ProfileButtonWidget(QFrame):
    """Top-right profile widget displaying the user's elided name and square profile picture."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ProfileButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Click to edit your profile picture and player name")
        self.setStyleSheet(
            "QFrame#ProfileButton { background:#232323; border:1px solid #444; border-radius:4px; padding:2px 6px; }"
            "QFrame#ProfileButton:hover { background:#303030; border:1px solid #26c6da; }"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 2, 6, 2)
        lay.setSpacing(6)

        self.name_label = QLabel("Profile")
        self.name_label.setStyleSheet("font-size:12px; font-weight:bold; color:#ddd; border:none; background:transparent;")
        self.name_label.setMaximumWidth(135)
        lay.addWidget(self.name_label)

        self._text_fg = "#e6e6e6"
        self._muted_fg = "#aaaaaa"
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(26, 26)
        self.avatar_label.setStyleSheet("border:1px solid #555; background:#1f1f1f;")
        lay.addWidget(self.avatar_label)
        self.refresh("")

    def set_theme(self, panel_bg: str, text_fg: str, border_fg: str, muted_fg: str = "#aaaaaa", hover_bg: str = "#303030") -> None:
        self._text_fg = text_fg
        self._muted_fg = muted_fg
        self.setStyleSheet(
            f"QFrame#ProfileButton {{ background:{panel_bg}; border:1px solid {border_fg}; border-radius:4px; padding:2px 6px; }}"
            f"QFrame#ProfileButton:hover {{ background:{hover_bg}; border:1px solid #26c6da; }}"
        )
        cur = self.name_label.text()
        if cur and cur != "Profile":
            self.name_label.setStyleSheet(f"font-size:12px; font-weight:bold; color:{self._text_fg}; border:none; background:transparent;")
        else:
            self.name_label.setStyleSheet(f"font-size:12px; color:{self._muted_fg}; border:none; background:transparent;")

    def refresh(self, player_name: str) -> None:
        clean = (player_name or "").strip()
        if clean:
            fm = QFontMetrics(self.name_label.font())
            elided = elide_profile_name(clean, max_chars=16, font_metrics=fm, max_px=120)
            self.name_label.setText(elided)
            self.name_label.setStyleSheet(f"font-size:12px; font-weight:bold; color:{self._text_fg}; border:none; background:transparent;")
        else:
            self.name_label.setText("Profile")
            self.name_label.setStyleSheet(f"font-size:12px; color:{self._muted_fg}; border:none; background:transparent;")
        pm = icons.profile_pixmap(26)
        if pm is not None and not pm.isNull():
            self.avatar_label.setPixmap(pm)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()
            e.accept()
            return
        super().mousePressEvent(e)


def _board_swatch_icon(b: dict, size: int = 36) -> QIcon:
    """Create a 2x2 mini-board swatch icon for the board template library."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    half = size // 2
    light_c = QColor(b.get("light_hex", "#f0d9b5"))
    dark_c = QColor(b.get("dark_hex", "#b58863"))
    if b.get("id") == "new_year":
        light_c = QColor("#ffd54f")
        dark_c = QColor("#181818")
    p.fillRect(0, 0, half, half, light_c)
    p.fillRect(half, 0, half, half, dark_c)
    p.fillRect(0, half, half, half, dark_c)
    p.fillRect(half, half, half, half, light_c)
    p.setPen(QColor("#666666"))
    p.drawRect(0, 0, size - 1, size - 1)
    p.end()
    return QIcon(pm)


def _bg_swatch_icon(bg: dict, size: int = 36) -> QIcon:
    """Create a swatch icon for a background template or custom image."""
    img_path = bg.get("image_path") or ""
    if img_path and os.path.exists(img_path):
        pm = QPixmap(img_path)
        if not pm.isNull():
            return QIcon(icons.crop_to_square_pixmap(pm, size))
    pm = QPixmap(size, size)
    pm.fill(QColor(bg.get("window_bg", "#1e1e1e")))
    p = QPainter(pm)
    p.setPen(QColor(bg.get("text_fg", "#e6e6e6")))
    p.drawRect(0, 0, size - 1, size - 1)
    p.fillRect(4, size - 10, size - 8, 6, QColor(bg.get("panel_bg", "#252526")))
    p.end()
    return QIcon(pm)


class ProfileDialog(QDialog):
    """Tabbed Profile & Customization dialog: Profile, App Icon, Sounds, Board, Background, Pieces, Annotations."""

    def __init__(self, settings: A.Settings, parent=None):
        super().__init__(parent)
        self.main_win = parent
        self.settings = settings
        self.setWindowTitle("Profile & Customizations")
        self.resize(680, 560)
        self._pending_image_path = None
        self._reset_requested = False

        self._sel_app_icon = getattr(settings, "app_icon", "fluent")
        self._sel_sound = getattr(settings, "sound_template", "original")
        self._sel_board = getattr(settings, "board_template", "brown_tan")
        self._sel_bg = getattr(settings, "background_template", "dark")
        self._sel_pieces = getattr(settings, "piece_template", "default")
        self._disable_holidays = bool(getattr(settings, "disable_holiday_events", False))

        lay = QVBoxLayout(self)
        self.tabs = QTabWidget()
        lay.addWidget(self.tabs, 1)

        self._build_profile_tab()
        self._build_icon_tab()
        self._build_sound_tab()
        self._build_board_tab()
        self._build_bg_tab()
        self._build_pieces_tab()
        self._build_annotations_tab()

        bb = QDialogButtonBox()
        self.btn_ok = bb.addButton(QDialogButtonBox.Ok)
        self.btn_close = bb.addButton(QDialogButtonBox.Close)
        self.btn_ok.setToolTip("Apply changes without closing this menu")
        self.btn_ok.clicked.connect(self._on_apply)
        self.btn_close.clicked.connect(self.accept)
        lay.addWidget(bb)

    # ---- Tab 1: Profile
    def _build_profile_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(10)
        self.tabs.addTab(page, "Profile")

        pic_row = QHBoxLayout()
        self.preview = QLabel()
        self.preview.setFixedSize(88, 88)
        self.preview.setStyleSheet("border:1px solid #555; background:#1f1f1f;")
        pic_row.addWidget(self.preview)

        btn_col = QVBoxLayout()
        self.btn_choose = QPushButton("Choose Square Picture…")
        self.btn_reset = QPushButton("Reset Picture to Default")
        self.btn_choose.clicked.connect(self._choose_picture)
        self.btn_reset.clicked.connect(self._reset_picture)
        btn_col.addWidget(self.btn_choose)
        btn_col.addWidget(self.btn_reset)
        pic_hint = QLabel("Images are automatically cropped to a 1:1 square.")
        pic_hint.setStyleSheet("font-size:11px;")
        pic_hint.setWordWrap(True)
        btn_col.addWidget(pic_hint)
        btn_col.addStretch(1)
        pic_row.addLayout(btn_col, 1)
        lay.addLayout(pic_row)

        form = QFormLayout()
        self.name_edit = QLineEdit(self.settings.player_name or "")
        self.name_edit.setPlaceholderText("Enter your chess username (e.g. TheHollyCow)…")
        form.addRow("My player name:", self.name_edit)
        lay.addLayout(form)

        info = QLabel(
            "Your profile picture appears to the right of your name on the board and in the top-right bar. "
            "If you leave your player name blank, your profile picture will only appear on the top-right bar."
        )
        info.setWordWrap(True)
        info.setStyleSheet("font-size:11px;")
        lay.addWidget(info)
        lay.addStretch(1)
        self._refresh_preview()

    # ---- Tab 2: App Icon (Library)
    def _build_icon_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        self.tabs.addTab(page, "App Icon")

        holiday = themes.active_holiday_event(disabled=self._disable_holidays)
        if holiday:
            hl = QLabel(
                f"Limited-time event available in library: <b>{themes.capitalize_asset_name(holiday)}</b> "
                "(select it if you want to use it during the event)."
            )
            hl.setWordWrap(True)
            hl.setStyleSheet("color:#26c6da; font-size:12px;")
            lay.addWidget(hl)

        btn_row = QHBoxLayout()
        self.btn_add_icon = QPushButton("Add Custom Icon…")
        self.btn_del_icon = QPushButton("Delete Custom")
        self.btn_add_icon.clicked.connect(self._add_custom_icon)
        self.btn_del_icon.clicked.connect(self._delete_custom_icon)
        btn_row.addWidget(QLabel("<b>App Icon Library</b>"))
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_add_icon)
        btn_row.addWidget(self.btn_del_icon)
        lay.addLayout(btn_row)

        self.icon_list = QListWidget()
        self.icon_list.setIconSize(QSize(40, 40))
        self.icon_list.setSpacing(2)
        self.icon_list.currentItemChanged.connect(self._on_icon_changed)
        lay.addWidget(self.icon_list, 1)

        prev_row = QHBoxLayout()
        self.app_icon_preview = QLabel()
        self.app_icon_preview.setFixedSize(72, 72)
        self.app_icon_preview.setStyleSheet("border:1px solid #555;")
        self.app_icon_info = QLabel("")
        self.app_icon_info.setWordWrap(True)
        prev_row.addWidget(self.app_icon_preview)
        prev_row.addWidget(self.app_icon_info, 1)
        lay.addLayout(prev_row)
        self._reload_icon_list()

    def _reload_icon_list(self):
        self.icon_list.blockSignals(True)
        self.icon_list.clear()
        sel_row = 0
        items = themes.list_selectable_app_icons(disable_holidays=self._disable_holidays)
        for i, item in enumerate(items):
            tag = " [Event]" if item.get("holiday") else (" [Built-in]" if item["locked"] else " [Custom]")
            li = QListWidgetItem(item["name"] + tag)
            pm = themes.cropped_icon_pixmap(item["path"], 48)
            if not pm.isNull():
                li.setIcon(QIcon(pm))
            li.setData(Qt.UserRole, item)
            self.icon_list.addItem(li)
            if item["id"] == self._sel_app_icon:
                sel_row = i
        if self.icon_list.count() > 0:
            self.icon_list.setCurrentRow(sel_row)
        self.icon_list.blockSignals(False)
        self._on_icon_changed()

    def _on_icon_changed(self):
        li = self.icon_list.currentItem()
        item = li.data(Qt.UserRole) if li else None
        if not item:
            return
        self._sel_app_icon = item["id"]
        self.btn_del_icon.setEnabled(not item["locked"])
        pm = themes.cropped_icon_pixmap(item["path"], 72)
        if not pm.isNull():
            self.app_icon_preview.setPixmap(pm)
        desc = "Built-in icon (cannot be edited or deleted)."
        if item.get("holiday"):
            desc = "Limited-time event icon (available during event dates)."
        elif not item["locked"]:
            desc = "Custom user icon saved on your computer."
        self.app_icon_info.setText(f"<b>{item['name']}</b><br>{desc}")

    def _add_custom_icon(self):
        p, _ = QFileDialog.getOpenFileName(
            self, "Select Custom App Icon", "", "Images (*.png *.jpg *.jpeg *.ico *.bmp *.webp)"
        )
        if not p:
            return
        default_nm = themes.capitalize_asset_name(p)
        nm, ok = QInputDialog.getText(self, "Custom Icon Name", "Icon name:", QLineEdit.Normal, default_nm)
        if not ok:
            return
        added = themes.add_custom_app_icon(p, nm)
        if not added:
            QMessageBox.warning(self, "Invalid Image", "Could not load the selected icon file.")
            return
        self._sel_app_icon = added["id"]
        self._reload_icon_list()

    def _delete_custom_icon(self):
        li = self.icon_list.currentItem()
        item = li.data(Qt.UserRole) if li else None
        if not item or item["locked"]:
            return
        if themes.delete_custom_app_icon(item["id"]):
            self._sel_app_icon = "fluent"
            self._reload_icon_list()

    # ---- Tab 3: Sounds (Library)
    def _build_sound_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        self.tabs.addTab(page, "Sounds")

        top = QHBoxLayout()
        top.addWidget(QLabel("<b>Sound Template Library</b>"))
        top.addStretch(1)
        self.btn_new_sound = QPushButton("New Template…")
        self.btn_del_sound = QPushButton("Delete")
        self.btn_new_sound.clicked.connect(self._create_sound_tpl)
        self.btn_del_sound.clicked.connect(self._delete_sound_tpl)
        top.addWidget(self.btn_new_sound)
        top.addWidget(self.btn_del_sound)
        lay.addLayout(top)

        self.sound_list = QListWidget()
        self.sound_list.setMaximumHeight(115)
        self.sound_list.currentItemChanged.connect(self._on_sound_tpl_changed)
        lay.addWidget(self.sound_list)

        self.sound_lock_lbl = QLabel("")
        self.sound_lock_lbl.setStyleSheet("font-size:11px;")
        lay.addWidget(self.sound_lock_lbl)

        sc = QScrollArea()
        sc.setWidgetResizable(True)
        inner = QWidget()
        self.sound_grid = QGridLayout(inner)
        self.sound_slot_widgets = []
        row_idx = 0
        self.sound_grid.addWidget(QLabel("<b>Move & Game Events</b>"), row_idx, 0, 1, 4)
        row_idx += 1
        for key, label in themes.SOUND_EVENT_SLOTS:
            self._add_sound_slot_row(row_idx, "events", key, label)
            row_idx += 1
        self.sound_grid.addWidget(QLabel("<b>Per-Annotation Sounds</b>"), row_idx, 0, 1, 4)
        row_idx += 1
        for key, label in themes.ANNOTATION_SLOTS:
            self._add_sound_slot_row(row_idx, "annotations", key, label)
            row_idx += 1
        sc.setWidget(inner)
        lay.addWidget(sc, 1)
        self._reload_sound_list()

    def _add_sound_slot_row(self, row_idx: int, category: str, key: str, label: str):
        lbl = QLabel(label)
        st = QLabel("None")
        btn_set = QPushButton("Replace…")
        btn_clr = QPushButton("Remove")
        btn_set.clicked.connect(lambda _=False, c=category, k=key: self._replace_sound_slot(c, k))
        btn_clr.clicked.connect(lambda _=False, c=category, k=key: self._clear_sound_slot(c, k))
        self.sound_grid.addWidget(lbl, row_idx, 0)
        self.sound_grid.addWidget(st, row_idx, 1)
        self.sound_grid.addWidget(btn_set, row_idx, 2)
        self.sound_grid.addWidget(btn_clr, row_idx, 3)
        self.sound_slot_widgets.append((category, key, st, btn_set, btn_clr))

    def _reload_sound_list(self):
        self.sound_list.blockSignals(True)
        self.sound_list.clear()
        sel_row = 0
        for i, tpl in enumerate(themes.list_sound_templates()):
            tag = " [Built-in]" if tpl["locked"] else " [Custom]"
            li = QListWidgetItem(tpl["name"] + tag)
            li.setData(Qt.UserRole, tpl)
            self.sound_list.addItem(li)
            if tpl["id"] == self._sel_sound:
                sel_row = i
        if self.sound_list.count() > 0:
            self.sound_list.setCurrentRow(sel_row)
        self.sound_list.blockSignals(False)
        self._on_sound_tpl_changed()

    def _on_sound_tpl_changed(self):
        li = self.sound_list.currentItem()
        tpl = li.data(Qt.UserRole) if li else None
        if not tpl:
            return
        self._sel_sound = tpl["id"]
        locked = bool(tpl.get("locked"))
        self.btn_del_sound.setEnabled(not locked)
        self.sound_lock_lbl.setText(
            "Built-in template (read-only). Create a new template to customize or add annotation sounds."
            if locked else "Custom template: replace or remove event sounds and per-annotation sounds."
        )
        for category, key, st, btn_set, btn_clr in self.sound_slot_widgets:
            path = (tpl.get(category) or {}).get(key, "")
            st.setText(os.path.basename(path) if path and os.path.exists(path) else "None")
            btn_set.setEnabled(not locked)
            btn_clr.setEnabled((not locked) and bool(path))

    def _create_sound_tpl(self):
        nm, ok = QInputDialog.getText(self, "New Sound Template", "Template name:", QLineEdit.Normal, "My Sounds")
        if not ok or not nm.strip():
            return
        base_id = self._sel_sound if self._sel_sound in ("original", "legacy") else "original"
        created = themes.create_sound_template(nm.strip(), copy_from_id=base_id)
        self._sel_sound = created["id"]
        self._reload_sound_list()

    def _delete_sound_tpl(self):
        if themes.delete_sound_template(self._sel_sound):
            self._sel_sound = "original"
            self._reload_sound_list()

    def _replace_sound_slot(self, category: str, key: str):
        p, _ = QFileDialog.getOpenFileName(
            self, "Select Sound File", "", "Audio Files (*.wav *.mp3 *.ogg);;All files (*)"
        )
        if p and themes.set_sound_slot(self._sel_sound, category, key, p):
            self._reload_sound_list()

    def _clear_sound_slot(self, category: str, key: str):
        if themes.clear_sound_slot(self._sel_sound, category, key):
            self._reload_sound_list()

    # ---- Tab 4: Board (Library)
    def _build_board_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        self.tabs.addTab(page, "Board")

        holiday = themes.active_holiday_event(disabled=self._disable_holidays)
        if holiday:
            hb = themes.HOLIDAY_BOARDS[holiday]
            hl = QLabel(
                f"Limited-time event available in library: <b>{hb['name']}</b> "
                "(select it if you want to use it during the event)."
            )
            hl.setWordWrap(True)
            hl.setStyleSheet("color:#26c6da; font-size:12px;")
            lay.addWidget(hl)

        top = QHBoxLayout()
        top.addWidget(QLabel("<b>Board Template Library</b>"))
        top.addStretch(1)
        self.btn_new_board = QPushButton("New Custom Board…")
        self.btn_del_board = QPushButton("Delete")
        self.btn_new_board.clicked.connect(self._create_board_tpl)
        self.btn_del_board.clicked.connect(self._delete_board_tpl)
        top.addWidget(self.btn_new_board)
        top.addWidget(self.btn_del_board)
        lay.addLayout(top)

        self.board_list = QListWidget()
        self.board_list.setIconSize(QSize(36, 36))
        self.board_list.setSpacing(2)
        self.board_list.currentItemChanged.connect(self._on_board_changed)
        lay.addWidget(self.board_list, 1)

        form = QFormLayout()
        self.board_light_hex = QLineEdit("#f0d9b5")
        self.btn_pick_light = QPushButton("Pick…")
        self.btn_pick_light.clicked.connect(lambda: self._pick_board_color(True))
        self.btn_png_light = QPushButton("White Tile PNG…")
        self.btn_png_light.clicked.connect(lambda: self._pick_board_png(True))
        self.lbl_png_light = QLabel("Hex color")
        r1 = QHBoxLayout()
        r1.addWidget(self.board_light_hex)
        r1.addWidget(self.btn_pick_light)
        r1.addWidget(self.btn_png_light)
        r1.addWidget(self.lbl_png_light, 1)
        form.addRow("White Tiles:", r1)

        self.board_dark_hex = QLineEdit("#b58863")
        self.btn_pick_dark = QPushButton("Pick…")
        self.btn_pick_dark.clicked.connect(lambda: self._pick_board_color(False))
        self.btn_png_dark = QPushButton("Black Tile PNG…")
        self.btn_png_dark.clicked.connect(lambda: self._pick_board_png(False))
        self.lbl_png_dark = QLabel("Hex color")
        r2 = QHBoxLayout()
        r2.addWidget(self.board_dark_hex)
        r2.addWidget(self.btn_pick_dark)
        r2.addWidget(self.btn_png_dark)
        r2.addWidget(self.lbl_png_dark, 1)
        form.addRow("Black Tiles:", r2)

        self.btn_save_board = QPushButton("Save Custom Board Changes")
        self.btn_save_board.clicked.connect(self._save_board_edits)
        form.addRow("", self.btn_save_board)
        lay.addLayout(form)
        self._reload_board_list()

    def _reload_board_list(self):
        self.board_list.blockSignals(True)
        self.board_list.clear()
        sel_row = 0
        boards = themes.list_selectable_board_templates(disable_holidays=self._disable_holidays)
        for i, b in enumerate(boards):
            tag = " [Event]" if b.get("holiday") else (" [Built-in]" if b["locked"] else " [Custom]")
            li = QListWidgetItem(_board_swatch_icon(b), b["name"] + tag)
            li.setData(Qt.UserRole, b)
            self.board_list.addItem(li)
            if b["id"] == self._sel_board:
                sel_row = i
        if self.board_list.count() > 0:
            self.board_list.setCurrentRow(sel_row)
        self.board_list.blockSignals(False)
        self._on_board_changed()

    def _on_board_changed(self):
        li = self.board_list.currentItem()
        b = li.data(Qt.UserRole) if li else None
        if not b:
            return
        self._sel_board = b["id"]
        locked = bool(b.get("locked"))
        self.board_light_hex.setText(b.get("light_hex", "#f0d9b5"))
        self.board_dark_hex.setText(b.get("dark_hex", "#b58863"))
        self.lbl_png_light.setText(os.path.basename(b["light_img"]) if b.get("light_img") else "Hex color")
        self.lbl_png_dark.setText(os.path.basename(b["dark_img"]) if b.get("dark_img") else "Hex color")
        for w in (self.board_light_hex, self.board_dark_hex, self.btn_pick_light, self.btn_pick_dark,
                  self.btn_png_light, self.btn_png_dark, self.btn_save_board, self.btn_del_board):
            w.setEnabled(not locked)

    def _create_board_tpl(self):
        nm, ok = QInputDialog.getText(self, "New Board Template", "Board template name:", QLineEdit.Normal, "My Board")
        if not ok or not nm.strip():
            return
        created = themes.save_custom_board_template(nm.strip())
        self._sel_board = created["id"]
        self._reload_board_list()

    def _delete_board_tpl(self):
        if themes.delete_custom_board_template(self._sel_board):
            self._sel_board = "brown_tan"
            self._reload_board_list()

    def _pick_board_color(self, is_light: bool):
        ed = self.board_light_hex if is_light else self.board_dark_hex
        c = QColorDialog.getColor(
            QColor(ed.text()),
            self,
            "Select Tile Color",
            options=QColorDialog.DontUseNativeDialog,
        )
        if c.isValid():
            ed.setText(c.name())

    def _pick_board_png(self, is_light: bool):
        li = self.board_list.currentItem()
        b = li.data(Qt.UserRole) if li else None
        if not b or b.get("locked"):
            return
        p, _ = QFileDialog.getOpenFileName(self, "Select Tile PNG", "", "PNG Images (*.png);;All files (*)")
        if not p:
            return
        l_png = p if is_light else b.get("light_img", "")
        d_png = b.get("dark_img", "") if is_light else p
        themes.save_custom_board_template(
            b["name"],
            self.board_light_hex.text(),
            self.board_dark_hex.text(),
            light_png=l_png,
            dark_png=d_png,
            template_id=b["id"],
        )
        self._reload_board_list()

    def _save_board_edits(self):
        li = self.board_list.currentItem()
        b = li.data(Qt.UserRole) if li else None
        if not b or b.get("locked"):
            return
        themes.save_custom_board_template(
            b["name"],
            self.board_light_hex.text(),
            self.board_dark_hex.text(),
            light_png=b.get("light_img", ""),
            dark_png=b.get("dark_img", ""),
            template_id=b["id"],
        )
        self._reload_board_list()

    # ---- Tab 5: Background (Library)
    def _build_bg_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        self.tabs.addTab(page, "Background")

        row = QHBoxLayout()
        row.addWidget(QLabel("<b>Background Library</b>"))
        row.addStretch(1)
        self.btn_add_bg = QPushButton("Add Image Background…")
        self.btn_del_bg = QPushButton("Delete")
        self.btn_add_bg.clicked.connect(self._add_custom_bg)
        self.btn_del_bg.clicked.connect(self._delete_custom_bg)
        row.addWidget(self.btn_add_bg)
        row.addWidget(self.btn_del_bg)
        lay.addLayout(row)

        self.bg_list = QListWidget()
        self.bg_list.setIconSize(QSize(36, 36))
        self.bg_list.setSpacing(2)
        self.bg_list.currentItemChanged.connect(self._on_bg_changed)
        lay.addWidget(self.bg_list, 1)

        self.bg_info = QLabel("")
        self.bg_info.setWordWrap(True)
        lay.addWidget(self.bg_info)
        self._reload_bg_list()

    def _reload_bg_list(self):
        self.bg_list.blockSignals(True)
        self.bg_list.clear()
        sel_row = 0
        for i, bg in enumerate(themes.list_background_templates()):
            tag = " [Built-in]" if bg["locked"] else " [Custom Image]"
            li = QListWidgetItem(_bg_swatch_icon(bg), bg["name"] + tag)
            li.setData(Qt.UserRole, bg)
            self.bg_list.addItem(li)
            if bg["id"] == self._sel_bg:
                sel_row = i
        if self.bg_list.count() > 0:
            self.bg_list.setCurrentRow(sel_row)
        self.bg_list.blockSignals(False)
        self._on_bg_changed()

    def _on_bg_changed(self):
        li = self.bg_list.currentItem()
        bg = li.data(Qt.UserRole) if li else None
        if not bg:
            return
        self._sel_bg = bg["id"]
        self.btn_del_bg.setEnabled(not bg.get("locked"))
        self.bg_info.setText(
            f"<b>{bg['name']}</b><br>"
            + ("Built-in theme template (cannot be edited)." if bg.get("locked") else f"Custom image: {bg.get('image_path', '')}")
        )

    def _add_custom_bg(self):
        p, _ = QFileDialog.getOpenFileName(
            self, "Select Background Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not p:
            return
        nm, ok = QInputDialog.getText(
            self, "Background Name", "Background template name:", QLineEdit.Normal, themes.capitalize_asset_name(p)
        )
        if not ok or not nm.strip():
            return
        created = themes.create_custom_background(nm.strip(), p)
        if created:
            self._sel_bg = created["id"]
            self._reload_bg_list()

    def _delete_custom_bg(self):
        if themes.delete_custom_background(self._sel_bg):
            self._sel_bg = "dark"
            self._reload_bg_list()

    # ---- Tab 6: Pieces (Library)
    def _build_pieces_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        self.tabs.addTab(page, "Pieces")

        top = QHBoxLayout()
        top.addWidget(QLabel("<b>Piece Template Library</b>"))
        top.addStretch(1)
        self.btn_new_pieces = QPushButton("New Piece Template…")
        self.btn_del_pieces = QPushButton("Delete")
        self.btn_new_pieces.clicked.connect(self._create_pieces_tpl)
        self.btn_del_pieces.clicked.connect(self._delete_pieces_tpl)
        top.addWidget(self.btn_new_pieces)
        top.addWidget(self.btn_del_pieces)
        lay.addLayout(top)

        self.pieces_list = QListWidget()
        self.pieces_list.setMaximumHeight(110)
        self.pieces_list.currentItemChanged.connect(self._on_pieces_changed)
        lay.addWidget(self.pieces_list)

        self.pieces_lock_lbl = QLabel("")
        self.pieces_lock_lbl.setStyleSheet("font-size:11px;")
        lay.addWidget(self.pieces_lock_lbl)

        sc = QScrollArea()
        sc.setWidgetResizable(True)
        inner = QWidget()
        grid = QGridLayout(inner)
        self.piece_slot_widgets = []
        for idx, (pkey, label) in enumerate(themes.PIECE_SLOTS):
            lbl = QLabel(label)
            st = QLabel("Default glyph")
            btn_set = QPushButton("Set PNG…")
            btn_clr = QPushButton("Clear")
            btn_set.clicked.connect(lambda _=False, k=pkey: self._set_piece_slot(k))
            btn_clr.clicked.connect(lambda _=False, k=pkey: self._clear_piece_slot(k))
            grid.addWidget(lbl, idx, 0)
            grid.addWidget(st, idx, 1)
            grid.addWidget(btn_set, idx, 2)
            grid.addWidget(btn_clr, idx, 3)
            self.piece_slot_widgets.append((pkey, st, btn_set, btn_clr))
        sc.setWidget(inner)
        lay.addWidget(sc, 1)
        self._reload_pieces_list()

    def _reload_pieces_list(self):
        self.pieces_list.blockSignals(True)
        self.pieces_list.clear()
        sel_row = 0
        for i, tpl in enumerate(themes.list_piece_templates()):
            tag = " [Built-in]" if tpl["locked"] else " [Custom]"
            li = QListWidgetItem(tpl["name"] + tag)
            li.setData(Qt.UserRole, tpl)
            self.pieces_list.addItem(li)
            if tpl["id"] == self._sel_pieces:
                sel_row = i
        if self.pieces_list.count() > 0:
            self.pieces_list.setCurrentRow(sel_row)
        self.pieces_list.blockSignals(False)
        self._on_pieces_changed()

    def _on_pieces_changed(self):
        li = self.pieces_list.currentItem()
        tpl = li.data(Qt.UserRole) if li else None
        if not tpl:
            return
        self._sel_pieces = tpl["id"]
        locked = bool(tpl.get("locked"))
        self.btn_del_pieces.setEnabled(not locked)
        self.pieces_lock_lbl.setText(
            "Default piece template (read-only). Create a new template to upload custom piece PNGs."
            if locked else "Custom piece template: upload a PNG for each piece (blank slots fall back to Default)."
        )
        pieces = tpl.get("pieces") or {}
        for pkey, st, btn_set, btn_clr in self.piece_slot_widgets:
            path = pieces.get(pkey, "")
            st.setText(os.path.basename(path) if path and os.path.exists(path) else "Default glyph")
            btn_set.setEnabled(not locked)
            btn_clr.setEnabled((not locked) and bool(path))

    def _create_pieces_tpl(self):
        nm, ok = QInputDialog.getText(self, "New Piece Template", "Piece template name:", QLineEdit.Normal, "My Pieces")
        if not ok or not nm.strip():
            return
        created = themes.create_piece_template(nm.strip())
        self._sel_pieces = created["id"]
        self._reload_pieces_list()

    def _delete_pieces_tpl(self):
        if themes.delete_piece_template(self._sel_pieces):
            self._sel_pieces = "default"
            self._reload_pieces_list()

    def _set_piece_slot(self, pkey: str):
        p, _ = QFileDialog.getOpenFileName(self, "Select Piece PNG", "", "Images (*.png *.webp *.jpg);;All files (*)")
        if p and themes.set_piece_slot(self._sel_pieces, pkey, p):
            self._reload_pieces_list()

    def _clear_piece_slot(self, pkey: str):
        if themes.clear_piece_slot(self._sel_pieces, pkey):
            self._reload_pieces_list()

    # ---- Tab 7: Annotations (moved from Settings)
    def _build_annotations_tab(self):
        page = QWidget()
        l2 = QVBoxLayout(page)
        self.tabs.addTab(page, "Annotations")

        self.mode = QComboBox()
        self.mode.addItem("Icons (new)", "icons")
        self.mode.addItem("Legacy (symbols and colours)", "legacy")
        self.mode.setCurrentIndex(max(0, self.mode.findData(styles.mode)))
        mrow = QHBoxLayout()
        mrow.addWidget(QLabel("Annotation style:"))
        mrow.addWidget(self.mode, 1)
        l2.addLayout(mrow)

        self.stack = QStackedWidget()
        l2.addWidget(self.stack, 1)

        ip = QWidget()
        il = QVBoxLayout(ip)
        il.addWidget(QLabel("Edit an icon in Microsoft Paint, save it, then come back here (the preview updates)."))
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        inner = QWidget()
        grid = QGridLayout(inner)
        self.icon_rows = {}
        for row, (stem, label) in enumerate(icons.ICON_LIST):
            pv = QLabel()
            pv.setFixedSize(34, 34)
            tag = QLabel()
            tag.setStyleSheet("color:#e8b923;")
            eb = QPushButton("Edit in Paint")
            rb = QPushButton("Reset")
            eb.clicked.connect(lambda _=False, st=stem: self.edit_icon(st))
            rb.clicked.connect(lambda _=False, st=stem: self.reset_icon(st))
            grid.addWidget(pv, row, 0)
            grid.addWidget(QLabel(label), row, 1)
            grid.addWidget(tag, row, 2)
            grid.addWidget(eb, row, 3)
            grid.addWidget(rb, row, 4)
            self.icon_rows[stem] = (pv, tag)
        sc.setWidget(inner)
        il.addWidget(sc, 1)
        ra = QPushButton("Reset ALL icons to default")
        ra.clicked.connect(self.reset_all_icons)
        il.addWidget(ra)
        self.stack.addWidget(ip)

        lp = QWidget()
        ll = QVBoxLayout(lp)
        ll.addWidget(QLabel("Pick the symbol (text or emoji) and colour for each annotation."))
        self.style_rows = {}
        g2 = QGridLayout()
        for row, (key, (name, _s, _c)) in enumerate(styles.DEFAULTS.items()):
            sym, col = styles.get_all()[key]
            ed = QLineEdit(sym)
            ed.setMaxLength(4)
            ed.setFixedWidth(70)
            btn = QPushButton()
            btn.setFixedWidth(70)
            self._paint_btn(btn, col)
            btn.clicked.connect(lambda _=False, k=key: self.pick_color(k))
            g2.addWidget(QLabel(name), row, 0)
            g2.addWidget(ed, row, 1)
            g2.addWidget(btn, row, 2)
            self.style_rows[key] = [ed, btn, col]
        ll.addLayout(g2)
        rb2 = QPushButton("Reset legacy annotations to defaults")
        rb2.clicked.connect(self.reset_styles)
        ll.addWidget(rb2)
        ll.addStretch(1)
        self.stack.addWidget(lp)
        self.mode.currentIndexChanged.connect(lambda: self.stack.setCurrentIndex(self.mode.currentIndex()))
        self.stack.setCurrentIndex(self.mode.currentIndex())
        self.refresh_icons()

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

    @staticmethod
    def _paint_btn(btn, col):
        btn.setStyleSheet("background:%s;border:1px solid #888;" % col)

    def pick_color(self, key):
        row = self.style_rows[key]
        c = QColorDialog.getColor(
            QColor(row[2]),
            self,
            "Colour",
            options=QColorDialog.DontUseNativeDialog,
        )
        if c.isValid():
            row[2] = c.name()
            self._paint_btn(row[1], row[2])

    def reset_styles(self):
        for key, (name, sym, col) in styles.DEFAULTS.items():
            row = self.style_rows[key]
            row[0].setText(sym)
            row[2] = col
            self._paint_btn(row[1], col)

    def result_styles(self):
        return {k: (r[0].text() or styles.DEFAULTS[k][1], r[2]) for k, r in self.style_rows.items()}

    # ---- Profile Picture handlers
    def _refresh_preview(self):
        if self._pending_image_path:
            src = QPixmap(self._pending_image_path)
            pm = icons.crop_to_square_pixmap(src, 88)
        elif self._reset_requested:
            pm = icons._default_profile_pixmap(88)
        else:
            pm = icons.profile_pixmap(88)
        if pm is not None and not pm.isNull():
            self.preview.setPixmap(pm)

    def _choose_picture(self):
        p, _ = QFileDialog.getOpenFileName(
            self,
            "Select Profile Picture",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp);;All files (*)",
        )
        if p:
            src = QPixmap(p)
            if src.isNull():
                QMessageBox.warning(self, "Invalid Image", "Could not load the selected image file.")
                return
            self._pending_image_path = p
            self._reset_requested = False
            self._refresh_preview()

    def _reset_picture(self):
        self._pending_image_path = None
        self._reset_requested = True
        self._refresh_preview()

    def _on_apply(self):
        if self._reset_requested:
            icons.reset_profile_avatar()
            self._reset_requested = False
        elif self._pending_image_path:
            icons.save_profile_avatar(self._pending_image_path)
            self._pending_image_path = None
        if self.main_win and hasattr(self.main_win, "apply_profile_dialog"):
            self.main_win.apply_profile_dialog(self)

    def result_name(self) -> str:
        return self.name_edit.text().strip()

    def result_customizations(self) -> dict:
        return {
            "app_icon": self._sel_app_icon,
            "sound_template": self._sel_sound,
            "board_template": self._sel_board,
            "background_template": self._sel_bg,
            "piece_template": self._sel_pieces,
        }


# ---------------------------------------------------------------- dialogs
class SettingsDialog(QDialog):
    PRESETS = [("Custom", "custom"), ("Low (fast)", "low"), ("Medium", "medium"), ("High (accurate)", "high")]

    def __init__(self, s, parent=None):
        super().__init__(parent)
        self.main_win = parent
        self._player_name = s.player_name
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
        self.eval_formula = QComboBox()
        self.eval_formula.addItem("Improved Eval Determination (Default)", "improved")
        self.eval_formula.addItem("Win Probability (Legacy)", "win_prob")
        self.eval_formula.setCurrentIndex(max(0, self.eval_formula.findData(getattr(s, "eval_formula", "improved"))))
        self.annotation_system = QComboBox()
        self.annotation_system.addItem("Modern Expected-Points System (Default)", "modern")
        self.annotation_system.addItem("Legacy Annotation System", "legacy")
        self.annotation_system.setCurrentIndex(
            max(0, self.annotation_system.findData(getattr(s, "annotation_system", "modern")))
        )
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
        f.addRow("Eval bar formula", self.eval_formula)
        f.addRow("Annotation system", self.annotation_system)
        f.addRow("", self.lenient)
        f.addRow("Preset", self.preset)
        f.addRow("Depth (slider)", srow)
        f.addRow("Threads", self.threads)
        f.addRow("Hash (MB)", self.hash)
        f.addRow("Engine path", self.path)
        hint = QLabel("Moving the depth slider switches to Custom and sets threads and hash automatically.")
        hint.setWordWrap(True)
        f.addRow(hint)

        # ---- events tab
        page_ev = QWidget(); lev = QVBoxLayout(page_ev)
        tabs.addTab(page_ev, "Events")
        self.disable_holidays = QCheckBox("Disable limited-time holiday events (Halloween, Christmas, New Year)")
        self.disable_holidays.setChecked(bool(getattr(s, "disable_holiday_events", False)))
        lev.addWidget(self.disable_holidays)
        ev_note = QLabel(
            "Holiday event icons and board templates appear in your Profile customization libraries only "
            "during their local OS clock timeframes (you can choose whether to equip them):\n"
            "• Halloween: October 1 – October 31\n"
            "• Christmas: December 1 – December 30\n"
            "• New Year: December 31 – January 1\n\n"
            "When an event ends (or if events are disabled), any equipped event theme automatically reverts to default."
        )
        ev_note.setWordWrap(True)
        ev_note.setStyleSheet("font-size:11px;")
        lev.addWidget(ev_note)
        lev.addStretch(1)

        # ---- updates tab
        page3 = QWidget(); l3 = QVBoxLayout(page3)
        tabs.addTab(page3, "Updates")
        ver_lbl = QLabel(f"<b>Current version:</b> {APP_VERSION}")
        ver_lbl.setStyleSheet("font-size:13px;")
        l3.addWidget(ver_lbl)
        self.auto_update = QCheckBox("Automatically check for updates on startup (newest stable releases only)")
        self.auto_update.setChecked(bool(getattr(s, "auto_update", True)))
        l3.addWidget(self.auto_update)
        self._is_prerelease = updater.is_prerelease_version(APP_VERSION)
        self.auto_install_prereleases = QCheckBox("Automatically install any new pre-releases on startup")
        self.auto_install_prereleases.setChecked(bool(getattr(s, "auto_install_prereleases", True)))
        self.auto_install_prereleases.setVisible(self._is_prerelease)
        l3.addWidget(self.auto_install_prereleases)
        upd_note = QLabel(
            "When enabled, Holly's Chess Analyzer checks GitHub for the newest stable release "
            "(pre-releases and drafts are ignored) and offers a one-click update."
        )
        upd_note.setWordWrap(True)
        upd_note.setStyleSheet("font-size:11px;")
        l3.addWidget(upd_note)
        chk_row = QHBoxLayout()
        self.btn_check_updates = QPushButton("Check for Updates Now")
        self.btn_check_updates.clicked.connect(self._check_updates_now)
        chk_row.addWidget(self.btn_check_updates)

        self._channel_target = None
        btn_txt = (
            "Go Back to Latest Stable Version"
            if self._is_prerelease else "Switch to Latest Pre-release"
        )
        self.btn_switch_channel = QPushButton(btn_txt)
        self.btn_switch_channel.setEnabled(False)
        self.btn_switch_channel.clicked.connect(self._switch_channel)
        chk_row.addWidget(self.btn_switch_channel)
        chk_row.addStretch(1)
        l3.addLayout(chk_row)
        self.update_status_lbl = QLabel("Checking available release channels…")
        self.update_status_lbl.setWordWrap(True)
        self.update_status_lbl.setStyleSheet("font-size:12px;")
        l3.addWidget(self.update_status_lbl)
        l3.addStretch(1)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        lay.addWidget(bb)

        if self.main_win and hasattr(self.main_win, "check_channels") and "--selftest" not in sys.argv:
            self.main_win.check_channels(self._on_channels_loaded)

    def _on_channels_loaded(self, data: dict, err: str = ""):
        if err:
            self.update_status_lbl.setText("Could not fetch release channels: " + err)
            return
        if self._is_prerelease:
            target = data.get("stable")
            if target and target.get("latest_version"):
                self._channel_target = target
                self.btn_switch_channel.setText(f"Go Back to Latest Stable ({target['latest_version']})")
                self.btn_switch_channel.setEnabled(True)
                self.update_status_lbl.setText(f"Latest stable release: {target['latest_version']}")
            else:
                self.btn_switch_channel.setEnabled(False)
                self.update_status_lbl.setText("No stable release found on GitHub.")
        else:
            target = data.get("prerelease")
            if target and target.get("latest_version"):
                self._channel_target = target
                self.btn_switch_channel.setText(f"Switch to Latest Pre-release ({target['latest_version']})")
                self.btn_switch_channel.setEnabled(True)
                self.update_status_lbl.setText(f"Latest pre-release available: {target['latest_version']}")
            else:
                self.btn_switch_channel.setEnabled(False)
                self.update_status_lbl.setText("No pre-release currently available on GitHub.")

    def _switch_channel(self):
        if self._channel_target and self.main_win and hasattr(self.main_win, "install_release"):
            self.main_win.install_release(self._channel_target, confirm=True)

    def _check_updates_now(self):
        if self.main_win and hasattr(self.main_win, "check_updates"):
            self.update_status_lbl.setText("Checking GitHub for the newest stable release…")
            self.btn_check_updates.setEnabled(False)
            self.main_win.check_updates(silent=False, status_callback=self._on_update_check_done)

    def _on_update_check_done(self, msg: str):
        self.btn_check_updates.setEnabled(True)
        self.update_status_lbl.setText(msg)

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

    def result_settings(self):
        cur_s = self.main_win.settings if (self.main_win and getattr(self.main_win, "settings", None)) else None
        cur_name = cur_s.player_name if cur_s is not None else self._player_name
        return A.Settings(
            self.scope.currentData(),
            self.side.currentData(),
            cur_name,
            self.slider.value(),
            self.threads.value(),
            self.hash.value(),
            self.path.text(),
            self.preset.currentData(),
            self.lenient.isChecked(),
            eval_formula=self.eval_formula.currentData(),
            annotation_system=self.annotation_system.currentData(),
            auto_update=self.auto_update.isChecked(),
            auto_install_prereleases=self.auto_install_prereleases.isChecked(),
            app_icon=getattr(cur_s, "app_icon", "fluent"),
            sound_template=getattr(cur_s, "sound_template", "original"),
            board_template=getattr(cur_s, "board_template", "brown_tan"),
            background_template=getattr(cur_s, "background_template", "dark"),
            piece_template=getattr(cur_s, "piece_template", "default"),
            disable_holiday_events=self.disable_holidays.isChecked(),
            last_holiday_event=getattr(cur_s, "last_holiday_event", ""),
            pre_event_app_icon=getattr(cur_s, "pre_event_app_icon", "fluent"),
            pre_event_board_template=getattr(cur_s, "pre_event_board_template", "brown_tan"),
        )


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


class LibraryDialog(QDialog):
    COLS = [
        "★", "Game Name", "Saved", "White", "Black", "Result",
        "Brilliant (!!)", "Your !!", "Opp !!", "Opening",
        "White Acc", "Black Acc", "Est. Rating", "Moves",
    ]
    BRIL_COLOR = "#26c6da"
    BRIL_SPECS = [
        ("queen", "♛ Queen Sacrifices"),
        ("rook", "♜ Rook Sacrifices"),
        ("bishop", "♝ Bishop Sacrifices"),
        ("knight", "♞ Knight Sacrifices"),
        ("underpromotion", "⇧ Underpromotions"),
    ]

    def __init__(self, lib: LIB.GameLibrary, parent=None):
        super().__init__(parent)
        self.lib = lib
        self.main_win = parent
        self.selected_id = None
        self.setWindowTitle(f"{APP_TITLE} — Saved Games Library")
        self.resize(1160, 640)
        lay = QVBoxLayout(self)

        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search by game name, player, opening, ECO, or event…")
        self.search.textChanged.connect(self.refresh)
        top.addWidget(QLabel("Search:"))
        top.addWidget(self.search, 2)
        top.addSpacing(10)

        top.addWidget(QLabel("Favorites:"))
        self.fav_filter = QComboBox()
        self.fav_filter.addItem("All Games", False)
        self.fav_filter.addItem("★ Favorites Only", True)
        self.fav_filter.currentIndexChanged.connect(self.refresh)
        top.addWidget(self.fav_filter)
        top.addSpacing(10)

        top.addWidget(QLabel("Brilliants:"))
        self.bril_sort = QComboBox()
        self.bril_sort.addItem("Default (Newest)", "recent")
        self.bril_sort.addItem("Most Brilliants", "most_brilliant")
        self.bril_sort.addItem("Least Brilliants", "least_brilliant")
        self.bril_sort.addItem("Opponent Brilliants", "opponent_brilliant")
        self.bril_sort.currentIndexChanged.connect(self.refresh)
        top.addWidget(self.bril_sort)
        lay.addLayout(top)

        # ---- Brilliant Moves Breakdown Section ----
        self.bril_panel = QFrame()
        self.bril_panel.setStyleSheet(
            "QFrame#BrilPanel { background:#1f1f1f; border:1px solid #444; border-radius:4px; padding:6px; }"
        )
        self.bril_panel.setObjectName("BrilPanel")
        bp_lay = QVBoxLayout(self.bril_panel)
        bp_lay.setContentsMargins(10, 8, 10, 8)
        bp_lay.setSpacing(6)

        banner = QHBoxLayout()
        self.bril_icon = QLabel()
        pm = icons.pixmap_for_key("!!", 24)
        if pm is not None:
            self.bril_icon.setPixmap(pm)
        self.summary_label = QLabel()
        self.summary_label.setTextFormat(Qt.RichText)
        self.summary_label.setStyleSheet(f"font-size:13px; color:{self.BRIL_COLOR};")
        banner.addWidget(self.bril_icon)
        banner.addWidget(self.summary_label, 1)
        bp_lay.addLayout(banner)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(8)
        self.cat_labels = {}
        for key, title in self.BRIL_SPECS:
            card = QFrame()
            card.setStyleSheet(
                f"QFrame {{ background:#262626; border:1px solid #444; border-left:3px solid {self.BRIL_COLOR}; border-radius:4px; padding:4px 8px; }}"
            )
            cl = QVBoxLayout(card)
            cl.setContentsMargins(6, 4, 6, 4)
            cl.setSpacing(2)
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("font-size:11px; color:#ccc; border:none;")
            v_lbl = QLabel("0")
            v_lbl.setStyleSheet(f"font-size:15px; font-weight:bold; color:{self.BRIL_COLOR}; border:none;")
            cl.addWidget(t_lbl)
            cl.addWidget(v_lbl)
            cards_row.addWidget(card, 1)
            self.cat_labels[key] = v_lbl
        bp_lay.addLayout(cards_row)
        lay.addWidget(self.bril_panel)

        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.setIconSize(QSize(18, 18))
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(9, QHeaderView.Stretch)
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.cellDoubleClicked.connect(lambda _r, c: c != 0 and self.open_selected())
        lay.addWidget(self.table, 1)

        btns = QHBoxLayout()
        self.btn_open = QPushButton("Open")
        self.btn_fav = QPushButton("★ Favorite")
        self.btn_rename = QPushButton("Rename…")
        self.btn_side = QPushButton("Switch My Side (W/B)")
        self.btn_del = QPushButton("Delete")
        self.btn_exp = QPushButton("Export PGN…")
        self.btn_imp = QPushButton("Import PGN…")
        self.btn_close = QPushButton("Close")
        self.btn_open.clicked.connect(self.open_selected)
        self.btn_fav.clicked.connect(self.toggle_favorite_selected)
        self.btn_rename.clicked.connect(self.rename_selected)
        self.btn_side.clicked.connect(self.toggle_side_selected)
        self.btn_del.clicked.connect(self.delete_selected)
        self.btn_exp.clicked.connect(self.export_selected)
        self.btn_imp.clicked.connect(self.import_pgn)
        self.btn_close.clicked.connect(self.reject)
        for b in (self.btn_open, self.btn_fav, self.btn_rename, self.btn_side, self.btn_del, self.btn_exp, self.btn_imp):
            btns.addWidget(b)
        btns.addStretch(1)
        btns.addWidget(self.btn_close)
        lay.addLayout(btns)
        QShortcut(QKeySequence(Qt.Key_F2), self, activated=self.rename_selected)
        self.refresh()

    def _current_username(self) -> str:
        if self.main_win and getattr(self.main_win, "settings", None):
            return (self.main_win.settings.player_name or "").strip()
        return ""

    def refresh(self):
        uname = self._current_username()
        fav_only = bool(self.fav_filter.currentData()) if hasattr(self, "fav_filter") else False
        sort_mode = self.bril_sort.currentData() if hasattr(self, "bril_sort") else "recent"
        self.rows = self.lib.list(
            self.search.text(),
            player_name=uname,
            favorites_only=fav_only,
            sort_by=sort_mode,
        )
        self.table.setRowCount(len(self.rows))
        fmt_acc = lambda v: "–" if v is None else f"{v:.1f}%"
        bril_pm = icons.pixmap_for_key("!!", 18)
        total_bril_all = sum(r.get("brilliant_total", 0) for r in self.rows)
        yours_bril_all = sum(r.get("brilliant_yours", 0) for r in self.rows)
        opp_bril_all = sum(r.get("brilliant_opponent", 0) for r in self.rows)
        cat_yours = {cat: 0 for cat in C.BRILLIANT_CATEGORIES}
        cat_total = {cat: 0 for cat in C.BRILLIANT_CATEGORIES}
        for r in self.rows:
            by = r.get("brilliant_breakdown_yours") or {}
            bt = r.get("brilliant_breakdown_total") or {}
            for cat in C.BRILLIANT_CATEGORIES:
                cat_yours[cat] += int(by.get(cat, 0))
                cat_total[cat] += int(bt.get(cat, 0))

        user_tag = f"for <b>{uname}</b> (White &amp; Black)" if uname else "(set your name in Profile on top-right to auto-match)"
        self.summary_label.setText(
            f"<b>Your Brilliant Moves (!!): {yours_bril_all}</b> {user_tag} "
            f"&nbsp;•&nbsp; <b>Opponent:</b> {opp_bril_all} "
            f"&nbsp;•&nbsp; <b>All Players:</b> {total_bril_all} across {len(self.rows)} game(s)"
        )
        for key, _title in self.BRIL_SPECS:
            mine_n = cat_yours.get(key, 0)
            all_n = cat_total.get(key, 0)
            lbl = self.cat_labels.get(key)
            if lbl is not None:
                lbl.setText(f"{mine_n}" if mine_n == all_n else f"{mine_n}  (all: {all_n})")

        for r_idx, row in enumerate(self.rows):
            is_fav = bool(row.get("favorite"))
            fav_str = "★" if is_fav else "☆"
            opening = f"{row['eco']} {row['opening']}".strip() or "–"
            w_r = row["white_rating"]
            b_r = row["black_rating"]
            rat = f"{w_r or '–'} / {b_r or '–'}"
            bw = int(row.get("brilliant_white") or 0)
            bb = int(row.get("brilliant_black") or 0)
            btot = int(row.get("brilliant_total") or 0)
            byours = int(row.get("brilliant_yours") or 0)
            bopp = int(row.get("brilliant_opponent") or 0)
            uc = (row.get("user_color") or "white").title()
            matched_by_name = bool(row.get("matched_by_name"))
            bril_str = f"{btot} ({bw}W / {bb}B)" if btot > 0 else "0"
            yours_str = f"{byours} ({uc})"
            opp_str = str(bopp)
            vals = [
                fav_str,
                row.get("title") or f"{row['white']} vs {row['black']}",
                row["saved_at"] or "",
                row["white"] or "?",
                row["black"] or "?",
                row["result"] or "*",
                bril_str,
                yours_str,
                opp_str,
                opening,
                fmt_acc(row["white_acc"]),
                fmt_acc(row["black_acc"]),
                rat,
                str(row["moves"] or 0),
            ]
            bd_yours = row.get("brilliant_breakdown_yours") or {}
            bd_parts = [
                f"{bd_yours.get(k, 0)} {k.title()}"
                for k in C.BRILLIANT_CATEGORIES
                if bd_yours.get(k, 0) > 0
            ]
            bd_desc = (", ".join(bd_parts)) if bd_parts else "No brilliant moves"
            match_note = f"matched username '{uname}'" if matched_by_name else "click 'Switch My Side (W/B)' or set your name in Profile"
            for c_idx, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if c_idx in (0, 2, 5, 6, 7, 8, 10, 11, 12, 13):
                    it.setTextAlignment(Qt.AlignCenter)
                if c_idx == 0:
                    it.setToolTip("Click to toggle Favorite")
                    it.setForeground(QColor("#26c6da") if is_fav else QColor("#777777"))
                    f = it.font(); f.setPointSize(12); it.setFont(f)
                if c_idx == 6 and btot > 0 and bril_pm is not None:
                    it.setIcon(QIcon(bril_pm))
                if c_idx == 7:
                    it.setToolTip(f"Tracking {uc} ({match_note}).\nBreakdown: {bd_desc}")
                    if byours > 0:
                        it.setForeground(QColor("#26c6da"))
                        f = it.font(); f.setBold(True); it.setFont(f)
                if c_idx == 8 and bopp > 0:
                    it.setForeground(QColor("#26c6da"))
                self.table.setItem(r_idx, c_idx, it)
        if self.rows:
            self.table.selectRow(0)

    def _on_cell_clicked(self, row_idx: int, col_idx: int):
        if col_idx == 0 and 0 <= row_idx < len(self.rows):
            gid = self.rows[row_idx]["id"]
            self.lib.toggle_favorite(gid)
            self.refresh()
            for idx, r in enumerate(self.rows):
                if r["id"] == gid:
                    self.table.selectRow(idx)
                    break

    def toggle_favorite_selected(self):
        row = self._cur_row()
        if not row:
            return
        gid = row["id"]
        self.lib.toggle_favorite(gid)
        self.refresh()
        for idx, r in enumerate(self.rows):
            if r["id"] == gid:
                self.table.selectRow(idx)
                break

    def _cur_row(self):
        r = self.table.currentRow()
        if 0 <= r < len(self.rows):
            return self.rows[r]
        return None

    def open_selected(self):
        row = self._cur_row()
        if not row:
            return
        self.selected_id = row["id"]
        self.accept()

    def rename_selected(self):
        row = self._cur_row()
        if not row:
            return
        cur_title = row.get("title") or f"{row['white']} vs {row['black']}"
        new_title, ok = QInputDialog.getText(self, "Rename Game", "Enter new name for this game:", QLineEdit.Normal, cur_title)
        if ok and new_title.strip():
            self.lib.rename(row["id"], new_title.strip())
            if self.main_win and getattr(self.main_win, "job", None) and self.main_win.job.lib_id == row["id"]:
                self.main_win.job.title = new_title.strip()
                self.main_win.update_players_header()
                self.main_win.refresh_combo(self.main_win.job)
            self.refresh()

    def toggle_side_selected(self):
        row = self._cur_row()
        if not row:
            return
        cur = (row.get("user_color") or "white").lower()
        new_side = "black" if cur == "white" else "white"
        self.lib.set_user_color(row["id"], new_side)
        self.refresh()

    def delete_selected(self):
        row = self._cur_row()
        if not row:
            return
        self.lib.delete(row["id"])
        self.refresh()

    def export_selected(self):
        row = self._cur_row()
        if not row or not self.main_win:
            return
        game, results = self.lib.load(row["id"])
        default = f"{row['white']}-vs-{row['black']}.pgn"
        default = "".join(c if c.isalnum() or c in "-_. " else "_" for c in default)
        path, _ = QFileDialog.getSaveFileName(self, "Export annotated PGN", default, "PGN files (*.pgn)")
        if path:
            text = self.main_win.format_annotated_pgn(game, results)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text + "\n")

    def import_pgn(self):
        if not self.main_win:
            return
        p, _ = QFileDialog.getOpenFileName(self, "Import PGN to analyse", "", "PGN files (*.pgn);;All files (*)")
        if p:
            self.reject()
            self.main_win.load_path(p)


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
    COLS = ["#", "Move", "", "Eval", "Time", "Opening", ""]

    def __init__(self):
        super().__init__()
        winutil.cleanup_old_exe_files()
        self.setWindowTitle(APP_TITLE)
        self.resize(1180, 760)
        self.setAcceptDrops(True)
        qs = QSettings("ChessAnalyzer", "ChessAnalyzer")
        self.qs = qs
        self.settings = A.Settings(
            qs.value("scope", "all"),
            qs.value("side", "both"),
            qs.value("name", ""),
            int(qs.value("depth", 16)),
            int(qs.value("threads", 1)),
            int(qs.value("hash", 128)),
            qs.value("engine", ""),
            qs.value("preset", "custom"),
            qs.value("lenient", False, type=bool),
            eval_formula=qs.value("eval_formula", "improved"),
            annotation_system=qs.value("annotation_system", "modern"),
            auto_update=qs.value("auto_update", True, type=bool),
            auto_install_prereleases=qs.value("auto_install_prereleases", True, type=bool),
            app_icon=qs.value("app_icon", "fluent"),
            sound_template=qs.value("sound_template", "original"),
            board_template=qs.value("board_template", "brown_tan"),
            background_template=qs.value("background_template", "dark"),
            piece_template=qs.value("piece_template", "default"),
            disable_holiday_events=qs.value("disable_holiday_events", False, type=bool),
            last_holiday_event=qs.value("last_holiday_event", ""),
            pre_event_app_icon=qs.value("pre_event_app_icon", "fluent"),
            pre_event_board_template=qs.value("pre_event_board_template", "brown_tan"),
        )
        self._last_exe_icon_id = None
        self.channel_worker = None
        self._bg_pixmap = None
        styles.load(qs)
        self.sound = SoundPlayer()
        self.holder = EngineHolder()
        self.library = LIB.GameLibrary()
        self.book = None
        self.games, self.game, self.results = [], None, []
        self.jobs, self.job = [], None
        self.basic = []
        self.clock_data = A.extract_game_clocks(None)
        self.worker = None
        self.line_workers = []
        self.update_worker = None
        self.download_worker = None
        self.cur = 0
        self.pv_boards = None

        c = QWidget(); self.setCentralWidget(c)
        root = QHBoxLayout(c)
        left = QVBoxLayout()
        left.setSpacing(5)
        self.opening_label = QLabel("Opening: –")
        self.opening_label.setStyleSheet("font-size:15px;font-weight:bold;")
        self.players = QLabel("")
        left.addWidget(self.players)

        self.top_player_bar = PlayerBarWidget()
        left.addWidget(self.top_player_bar)

        bh = QHBoxLayout()
        self.evalbar = EvalBar()
        self.evalbar.formula = self.settings.eval_formula
        self.board = BoardWidget()
        bh.addWidget(self.evalbar); bh.addWidget(self.board, 1)
        left.addLayout(bh, 1)

        self.bottom_player_bar = PlayerBarWidget()
        left.addWidget(self.bottom_player_bar)

        left.addWidget(self.opening_label)
        nav = QHBoxLayout()
        for t, fn in (("|◂", lambda: self.goto(0)), ("◂", lambda: self.goto(self.cur - 1)),
                      ("▸", lambda: self.goto(self.cur + 1)), ("▸|", lambda: self.goto(len(self.results))),
                      ("Flip", self.flip)):
            b = QPushButton(t); b.clicked.connect(fn); nav.addWidget(b)
        left.addLayout(nav)
        self.graph = GraphWidget()
        self.graph.formula = self.settings.eval_formula
        self.graph.clicked.connect(self.goto)
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
        for i, w in ((0, 36), (2, 40), (3, 56), (4, 54), (6, 54)):
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

        tb = QToolBar()
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.setContextMenuPolicy(Qt.PreventContextMenu)
        self.addToolBar(tb)
        self.tb = tb
        self.save_act = None
        for t, fn in (("Open PGN…", self.open_file), ("Paste PGN/FEN…", self.paste),
                      ("Re-analyze", self.restart_all), ("Stop", self.stop),
                      ("Save Game", self.save_to_library), ("Rename Game…", self.rename_current_game),
                      ("Library…", self.open_library), ("Settings…", self.open_settings)):
            act = tb.addAction(t, fn)
            if t == "Save Game":
                self.save_act = act
        self.game_combo = QComboBox(); self.game_combo.setVisible(False)
        self.game_combo.currentIndexChanged.connect(self.pick_game)
        tb.addWidget(self.game_combo)
        tb.addAction("Win% Guide", self.show_win_guide)
        tb.addAction("Keys", self.show_keys)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        spacer.setStyleSheet("background:transparent;")
        tb.addWidget(spacer)

        self.profile_btn = ProfileButtonWidget(self)
        self.profile_btn.clicked.connect(self.open_profile)
        tb.addWidget(self.profile_btn)

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
            (Qt.Key_F2, "Rename current game", self.rename_current_game),
            (QKeySequence("Ctrl+O"), "Open PGN", self.open_file),
            (QKeySequence("Ctrl+S"), "Save to library", self.save_to_library),
            (QKeySequence("Ctrl+L"), "Open library", self.open_library),
        ]
        for key, _d, fn in self.keymap:
            QShortcut(QKeySequence(key), self, activated=fn)
        self.setStyleSheet("QMainWindow,QWidget{background:#2b2b2b;color:#ddd;} QTableWidget{background:#1f1f1f;gridline-color:#333;}"
                           "QPushButton{background:#444;border:1px solid #555;padding:3px 8px;} QHeaderView::section{background:#333;color:#ddd;}"
                           "QListWidget,QPlainTextEdit,QLineEdit,QSpinBox,QComboBox{background:#1f1f1f;}")
        self.apply_customizations()
        self.refresh_profile_ui()
        if "--selftest" not in sys.argv:
            if updater.is_prerelease_version(APP_VERSION) and getattr(self.settings, "auto_install_prereleases", True):
                QTimer.singleShot(1400, self.check_prerelease_auto_update)
            elif self.settings.auto_update:
                QTimer.singleShot(1400, lambda: self.check_updates(silent=True))

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
            QMessageBox.warning(self, APP_TITLE, "No valid PGN or FEN found."); return
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
        if hasattr(self, "sound"):
            self.sound.play("Game_load")
        self.start_queue()

    def combo_text(self, i):
        h = self.games[i].headers
        j = self.jobs[i]
        if j.done:
            st = "saved" if j.lib_id else "done"
        elif j.running:
            a, b = j.progress
            st = "… %d%%" % (100 * a // max(1, b))
        else:
            st = "queued"
        label = j.title or ("%s – %s" % (h.get("White", "?"), h.get("Black", "?")))
        return "%d. %s   [%s]" % (i + 1, label, st)

    def refresh_combo(self, job=None):
        for i, j in enumerate(self.jobs):
            if job is None or j is job:
                self.game_combo.setItemText(i, self.combo_text(i))

    def update_players_header(self):
        if not self.game or not self.job:
            self.players.setText("")
            self.update_save_button(False)
            return
        h = self.game.headers
        base = "%s  vs  %s   %s" % (h.get("White", "?"), h.get("Black", "?"), h.get("Result", ""))
        if self.job.title and self.job.title != f"{h.get('White', '?')} vs {h.get('Black', '?')}":
            text = f"<b>{self.job.title}</b> &nbsp; <span style='color:#aaa;'>({base})</span>"
        else:
            text = f"<b>{base}</b>"
        if self.job.lib_id is not None:
            text += " &nbsp; <span style='color:#aaa;font-size:12px;'>(Saved)</span>"
        self.players.setTextFormat(Qt.RichText)
        self.players.setText(text)

    def update_save_button(self, flash: bool = False):
        if not self.save_act:
            return
        w = self.tb.widgetForAction(self.save_act)
        if w:
            w.setStyleSheet("")
        self.save_act.setText("Saved" if flash else "Save Game")

    def pick_game(self, i):
        if i < 0 or i >= len(self.games):
            return
        self.job = self.jobs[i]
        self.game = self.games[i]
        self.results = self.job.results
        self.update_players_header()
        self.populate_basic()
        self.orient()
        self.apply_customizations()
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
        self.update_player_bars()

    def populate_basic(self):
        b = self.game.board()
        self.start_board = b.copy()
        self.clock_data = A.extract_game_clocks(self.game)
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
        self.setWindowTitle(APP_TITLE)
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
        self.setWindowTitle("%s – analysing %d/%d (%d%%)" % (
            APP_TITLE, min(done + 1, len(self.jobs)), len(self.jobs), 100 * a // max(1, b)))
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
                self.goto(self.cur, animate=False, play_sound=False)
            self.update_status()
        if not any(not j.done for j in self.jobs):
            self.progress.setVisible(False)
            winutil.keep_awake(False)
            self.setWindowTitle(APP_TITLE)
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
            self.tray.showMessage(APP_TITLE, "Analysis finished for %d game(s)." % len(self.jobs),
                                  QSystemTrayIcon.Information, 6000)

    def refresh_graph(self):
        results = self.results
        if not results:
            self.graph.set_values([]); return
        is_std = C.is_standard_start(getattr(self, "start_board", None))
        start_val = 0 if is_std else (results[0].eval_before if results[0].eval_before is not None else 0)
        vals = [start_val]
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
        for c in (0, 2, 3, 4, 5):
            self.table.setItem(0, c, QTableWidgetItem(""))
        self.table.setCellWidget(0, 6, self.best_button(0))
        for k in range(len(rows)):
            self.set_row(k)
            self.table.setCellWidget(k + 1, 6, self.best_button(k + 1))

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
            if sym == "!!" and getattr(r, "brilliant_type", ""):
                bt = r.brilliant_type
                bt_label = "Underpromotion" if bt == "underpromotion" else f"{bt.title()} Sacrifice"
                tip += f" ({bt_label})"
            if r.best_san and self.alt_for(r):
                tip += " – best was " + r.best_san
            it.setToolTip(tip)
        self.table.setItem(row, 2, it)
        self.table.setItem(row, 3, QTableWidgetItem(r.eval_after_text if r else ""))
        plies = self.clock_data.get("plies", [])
        mt = (r.move_time_text if r and r.move_time_text else "") or (
            plies[k]["move_time_text"] if k < len(plies) else "")
        tit = QTableWidgetItem(mt)
        tit.setTextAlignment(Qt.AlignCenter)
        tit.setForeground(QColor("#aaaaaa"))
        self.table.setItem(row, 4, tit)
        self.table.setItem(row, 5, QTableWidgetItem((r.opening if r and r.book else "")))

    # ------------------------------------------------------------ saving
    NAGS = {"!!": chess.pgn.NAG_BRILLIANT_MOVE, "!": chess.pgn.NAG_GOOD_MOVE, "?!": chess.pgn.NAG_DUBIOUS_MOVE,
            "?": chess.pgn.NAG_MISTAKE, "??": chess.pgn.NAG_BLUNDER}

    def annotated_pgn(self, idx):
        """PGN text of game idx with NAGs, [%eval] and a short comment per analysed move."""
        return self.format_annotated_pgn(self.games[idx], self.jobs[idx].results)

    def format_annotated_pgn(self, game, results):
        copy = chess.pgn.read_game(io.StringIO(str(game)))     # never mutate the loaded game
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
        copy.headers["Annotator"] = "%s (Stockfish, depth %d)" % (APP_TITLE, self.settings.depth)
        exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=True)
        return copy.accept(exporter)

    def save_game(self):
        if not self.games:
            QMessageBox.information(self, APP_TITLE, "Open a game first."); return
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
            QMessageBox.information(self, APP_TITLE, "Open a game first."); return
        path, _ = QFileDialog.getSaveFileName(self, "Save all analysed games", "analysed-games.pgn", "PGN files (*.pgn)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(self.annotated_pgn(i) for i in range(len(self.games))) + "\n")
            self.status.setText("Saved %d game(s) to %s" % (len(self.games), path))

    def _current_user_color(self):
        if self.game:
            mc = self.settings.matched_color(self.game.headers)
            if mc == chess.WHITE:
                return "white"
            if mc == chess.BLACK:
                return "black"
        if self.settings.side in ("white", "black"):
            return self.settings.side
        return "black" if self.board.flipped else "white"

    def rename_current_game(self):
        if not self.game or not self.job:
            QMessageBox.information(self, APP_TITLE, "Open a game first."); return
        h = self.game.headers
        cur = self.job.title or f"{h.get('White', '?')} vs {h.get('Black', '?')}"
        new_title, ok = QInputDialog.getText(self, "Rename Game", "Enter name for this game:", QLineEdit.Normal, cur)
        if ok and new_title.strip():
            self.job.title = new_title.strip()
            if self.job.lib_id is not None:
                self.library.rename(self.job.lib_id, self.job.title)
            self.update_players_header()
            self.refresh_combo(self.job)
            self.status.setText(f"Renamed game to '{self.job.title}'.")

    def save_to_library(self):
        if not self.game or not self.job:
            QMessageBox.information(self, APP_TITLE, "Open and analyse a game first."); return
        if not self.job.done:
            QMessageBox.information(self, APP_TITLE, "Wait for analysis to finish before saving to the library."); return
        h = self.game.headers
        mc = self.settings.matched_color(h)
        if mc == chess.WHITE:
            uc = "white"
        elif mc == chess.BLACK:
            uc = "black"
        elif self.settings.side in ("white", "black"):
            uc = self.settings.side
        else:
            uc = "black" if self.board.flipped else "white"
        ny_colors = getattr(self.job, "new_years_colors", None) or themes.generate_new_years_palette()
        self.job.new_years_colors = ny_colors
        gid = self.library.save(
            self.game, self.job.results, self.settings,
            title=self.job.title or None, user_color=uc, new_years_colors=ny_colors,
        )
        self.job.lib_id = gid
        if not self.job.title:
            for row in self.library.list():
                if row["id"] == gid:
                    self.job.title = row["title"]
                    break
        self.update_players_header()
        self.update_save_button(flash=True)
        QTimer.singleShot(1800, lambda: self.update_save_button(flash=False))
        self.refresh_combo(self.job)
        name = self.job.title or f"{h.get('White', '?')} vs {h.get('Black', '?')}"
        self.status.setText(f"Saved '{name}' to library (#{gid}).")

    def open_library(self):
        d = LibraryDialog(self.library, self)
        if d.exec() and d.selected_id is not None:
            self.load_from_library(d.selected_id)

    def load_from_library(self, game_id: int):
        self.stop()
        game, results = self.library.load(game_id)
        job = Job(game)
        job.results = list(results)
        job.done = True
        job.running = False
        job.progress = (len(results), max(1, len(results)))
        job.lib_id = game_id
        saved_ny = self.library.get_new_years_colors(game_id)
        if saved_ny:
            job.new_years_colors = saved_ny
        else:
            self.library.set_new_years_colors(game_id, job.new_years_colors)
        for row in self.library.list():
            if row["id"] == game_id:
                job.title = row.get("title") or ""
                break
        self.games = [game]
        self.jobs = [job]
        self.ensure_book()
        self.game_combo.blockSignals(True)
        self.game_combo.clear()
        self.game_combo.addItem(self.combo_text(0))
        self.game_combo.setVisible(False)
        self.game_combo.blockSignals(False)
        self.pick_game(0)
        if hasattr(self, "sound"):
            self.sound.play("Game_load")
        self.status.setText("Loaded saved game from library (%d moves, instant)." % len(results))

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

    def goto(self, idx, animate=True, play_sound=True):
        if not self.game:
            return
        idx = max(0, min(idx, len(self.basic)))
        prev_idx = self.cur
        self.cur = idx
        b = self.board_at(idx)
        mv = self.basic[idx - 1][3] if idx else None
        r = self.results[idx - 1] if idx and idx - 1 < len(self.results) else None
        sym = r.symbol if r else ""
        do_anim = bool(animate and mv is not None and (sym == "!!" or idx != prev_idx))
        self.board.set_position(b, mv, sym, self.alt_for(r), self.end_badges(b, idx), animate=do_anim)
        if play_sound and idx > 0 and mv is not None and idx != prev_idx and hasattr(self, "sound"):
            b_before = self.board_at(idx - 1)
            is_draw_end = (
                b.is_stalemate()
                or b.is_insufficient_material()
                or b.is_fifty_moves()
                or b.is_repetition(3)
                or (idx == len(self.basic) and self.game and self.game.headers.get("Result") == "1/2-1/2")
            )
            if sym == "!!":
                self.sound.play_for_move("brilliant", sym)
            elif b.is_checkmate():
                self.sound.play_for_move("Checkmate", sym)
            elif is_draw_end:
                self.sound.play_for_move("draw", sym)
            elif b.is_check():
                self.sound.play_for_move("Check", sym)
            elif b_before.is_castling(mv):
                self.sound.play_for_move("Castle", sym)
            elif b_before.is_capture(mv):
                self.sound.play_for_move("Capture", sym)
            else:
                self.sound.play_for_move("Move", sym)
        self.table.blockSignals(True)
        self.table.selectRow(idx)
        self.table.blockSignals(False)
        cp, txt, is_start = None, "", False
        if idx == 0:
            if C.is_standard_start(b):
                cp, txt, is_start = 0, "0.0", True
            elif self.results and self.results[0].eval_before is not None:
                cp = self.results[0].eval_before
            else:
                cp, txt, is_start = 0, "0.0", True
        elif r and r.eval_after is not None:
            cp, txt = r.eval_after, r.eval_after_text
        if C.is_deadlocked_position(b, r.pv_uci if (r and r.pv_uci) else None):
            cp, txt = 0, "0.0"
        self.evalbar.set_eval(cp, txt, is_start=is_start)
        name = "–"
        for k in range(idx, 0, -1):
            if k - 1 < len(self.results) and self.results[k - 1].opening:
                name = "%s  %s" % (self.results[k - 1].eco, self.results[k - 1].opening); break
        self.opening_label.setText("Opening: " + name)
        self.update_player_bars()

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
        self.update_player_bars()

    def update_player_bars(self):
        """Fill top/bottom player bars (names, clocks, conditional profile picture)."""
        h = self.game.headers if self.game else {}
        positions = self.clock_data.get("positions") or [("--:--", "--:--")]
        idx = max(0, min(self.cur, len(positions) - 1))
        w_clk, b_clk = positions[idx]
        top_color = chess.WHITE if self.board.flipped else chess.BLACK
        fallback = "black" if self.board.flipped else "white"
        for bar, color in ((self.top_player_bar, top_color), (self.bottom_player_bar, not top_color)):
            nm = h.get("White" if color else "Black", "White" if color else "Black")
            rt = h.get("WhiteElo" if color else "BlackElo", "")
            rt = "" if rt in ("?", "") else rt
            show = bool(self.game) and should_show_board_avatar(
                self.settings.player_name, color, h, fallback)
            bar.set_player(color, nm, rt, w_clk if color else b_clk, show_avatar=show)

    def refresh_profile_ui(self):
        self.profile_btn.refresh(self.settings.player_name)
        self.update_player_bars()

    def paintEvent(self, e):
        if self._bg_pixmap is not None and not self._bg_pixmap.isNull():
            p = QPainter(self)
            scaled = self._bg_pixmap.scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            x = (scaled.width() - self.width()) // 2
            y = (scaled.height() - self.height()) // 2
            p.drawPixmap(0, 0, scaled, x, y, self.width(), self.height())
            p.fillRect(self.rect(), QColor(0, 0, 0, 85))
            return
        super().paintEvent(e)

    def apply_customizations(self):
        """Apply App Icon, Sound Template, Board Template, Background, and Piece Template."""
        if themes.sync_holiday_event_state(self.settings):
            for k in (
                "app_icon", "board_template", "last_holiday_event",
                "pre_event_app_icon", "pre_event_board_template",
            ):
                self.qs.setValue(k, getattr(self.settings, k))
        dis_hol = bool(getattr(self.settings, "disable_holiday_events", False))
        # 1. App Icon
        icon_info = themes.resolve_active_app_icon(
            getattr(self.settings, "app_icon", "fluent"),
            disable_holidays=dis_hol,
        )
        pm_icon = themes.cropped_icon_pixmap(icon_info.get("path", ""), 256)
        if not pm_icon.isNull():
            app_ic = QIcon(pm_icon)
            self.setWindowIcon(app_ic)
            app_inst = QApplication.instance()
            if app_inst is not None:
                app_inst.setWindowIcon(app_ic)
        if getattr(sys, "frozen", False) and icon_info.get("id") != self._last_exe_icon_id:
            self._last_exe_icon_id = icon_info.get("id")
            ico_bytes = themes.image_to_ico_bytes(icon_info.get("path", ""))
            if ico_bytes:
                winutil.apply_icon_to_running_exe(ico_bytes)

        # 2. Sound Template
        self.sound.set_template(getattr(self.settings, "sound_template", "original"))

        # 3. Board Template
        board_tpl = themes.resolve_active_board_template(
            getattr(self.settings, "board_template", "brown_tan"),
            disable_holidays=dis_hol,
        )
        ny_colors = getattr(self.job, "new_years_colors", None) if self.job else themes.generate_new_years_palette()
        self.board.set_board_theme(board_tpl, ny_colors)

        # 4. Piece Template
        piece_tpl = themes.get_piece_template(getattr(self.settings, "piece_template", "default"))
        self.board.set_piece_theme(piece_tpl)

        # 5. Background Template & Global UI Theme
        bg = themes.get_background_template(getattr(self.settings, "background_template", "dark"))
        img_path = bg.get("image_path") or ""
        has_img = bool(img_path and os.path.exists(img_path))
        self._bg_pixmap = QPixmap(img_path) if has_img else None

        qss = themes.build_app_stylesheet(bg, is_custom_image=has_img)
        app_inst = QApplication.instance()
        if app_inst is not None:
            app_inst.setStyleSheet(qss)
            self.setStyleSheet("")
        else:
            self.setStyleSheet(qss)

        pal = themes.get_theme_palette(bg)
        self.top_player_bar.set_theme(pal["bar_bg"], pal["bar_fg"], pal["bar_border"])
        self.bottom_player_bar.set_theme(pal["bar_bg"], pal["bar_fg"], pal["bar_border"])
        self.profile_btn.set_theme(pal["bar_bg"], pal["bar_fg"], pal["bar_border"], pal["muted"], pal["btn_hover"])
        self.graph.set_theme(pal["graph_bg"], pal["graph_fill"], pal["graph_mid"], pal["border"])
        self.update()

    def apply_profile_dialog(self, d: ProfileDialog):
        old_name = self.settings.player_name
        self.settings.player_name = d.result_name()
        cust = d.result_customizations()
        for k, v in cust.items():
            setattr(self.settings, k, v)
            self.qs.setValue(k, v)
        self.qs.setValue("name", self.settings.player_name)

        styles.set_all(d.result_styles())
        styles.mode = d.mode.currentData()
        styles.save(self.qs)
        icons._cache.clear()

        if (old_name or "").strip().lower() != self.settings.player_name.lower() and self.game:
            self.orient()
            if self.settings.scope != "all":
                self.restart_all()
        if self.game:
            for k in range(len(self.basic)):
                self.render_row(k)
            self.update_stats()
            self.go(self.cur)

        self.apply_customizations()
        self.refresh_profile_ui()

    def open_profile(self):
        d = ProfileDialog(self.settings, self)
        d.exec()

    # ------------------------------------------------------------ auto-update
    def check_updates(self, silent=True, status_callback=None):
        if self.update_worker and self.update_worker.isRunning():
            return
        w = UpdateCheckWorker(APP_VERSION)
        self.update_worker = w

        def done(info):
            if info.get("update_available"):
                msg = "Update available: %s (current %s)." % (info["latest_version"], APP_VERSION)
                if status_callback:
                    status_callback(msg)
                self.prompt_update(info)
            else:
                msg = "You are up to date (%s)." % APP_VERSION
                if status_callback:
                    status_callback(msg)

        def failed(m):
            if status_callback:
                status_callback("Update check failed: " + m)

        w.finished_check.connect(done)
        w.failed.connect(failed)
        w.start()

    def check_channels(self, callback):
        if self.channel_worker and self.channel_worker.isRunning():
            return
        w = ChannelCheckWorker(APP_VERSION)
        self.channel_worker = w
        w.finished_channels.connect(lambda data: callback(data, ""))
        w.failed.connect(lambda err: callback({}, err))
        w.start()

    def check_prerelease_auto_update(self):
        """When running a pre-release build, automatically install any newer pre-release."""
        def _on_channels(data, err):
            if err or not data:
                return
            pre = data.get("prerelease")
            if pre and pre.get("update_available") and pre.get("download_url"):
                self.install_release(pre, confirm=False)
        self.check_channels(_on_channels)

    def prompt_update(self, info):
        self.install_release(info, confirm=True)

    def install_release(self, info, confirm: bool = True):
        frozen = getattr(sys, "frozen", False)
        text = "Version %s is available (you have %s)." % (info["latest_version"], APP_VERSION)
        if not (frozen and info.get("download_url") and sys.platform == "win32"):
            QMessageBox.information(self, APP_TITLE, text + "\n\n" + info.get("html_url", ""))
            return
        if confirm and QMessageBox.question(self, APP_TITLE, text + "\n\nDownload and install now?") != QMessageBox.Yes:
            return
        import tempfile
        dest = os.path.join(tempfile.gettempdir(), "hca_update_%s.exe" % info["latest_version"].lstrip("v"))
        self.status.setText("Downloading update…")
        self.progress.setVisible(True)
        w = UpdateDownloadWorker(info["download_url"], dest)
        self.download_worker = w
        w.progress.connect(lambda a, b: (self.progress.setMaximum(max(1, b)), self.progress.setValue(a)))

        def ok(path):
            self.progress.setVisible(False)
            if updater.apply_windows_exe_update(path):
                self.close()
                QApplication.quit()
            else:
                self.status.setText("Update downloaded but could not be applied: " + path)

        def bad(m):
            self.progress.setVisible(False)
            self.status.setText("Update download failed: " + m)

        w.finished_download.connect(ok)
        w.failed.connect(bad)
        w.start()

    def show_win_guide(self):
        msg = (
            "<h3>Evaluation Bar &amp; Move Annotations Guide</h3>"
            "<p><b>Evaluation Bar Formulas (selectable in Settings):</b></p>"
            "<ul>"
            "<li><b>Improved Eval Determination (Default):</b> Starts strictly at <code>0.0</code> (50%/50%) before any moves are played, "
            "dampens tiny engine tempo noise near <code>0.00</code>, uses a WDL-calibrated smooth curve, and clamps non-mate advantages "
            "to <code>[2.5%, 97.5%]</code> so <code>100%</code> is reserved exclusively for forced checkmate.</li>"
            "<li><b>Win Probability (Legacy):</b> Uses the Lichess logistic formula "
            "<code>win% = 50 + 50 · (2 / (1 + e^(-0.00368208 · cp)) - 1)</code>.</li>"
            "</ul>"
            "<p><b>Annotation Systems (selectable in Settings):</b></p>"
            "<ul>"
            "<li><b>Modern Expected-Points System (Default):</b> Context-aware classification using Expected Points loss (ΔEP), "
            "true pre-move position evaluation, MultiPV uniqueness for <b>Great (!)</b> and <b>Miss</b>, winning-position protection, "
            "and sound sacrifice / underpromotion verification for <b>Brilliant (!!)</b>.</li>"
            "<li><b>Legacy Annotation System:</b> Classic fixed win-percentage drop thresholds "
            "(<b>Inaccuracy (?!)</b> 5–10%, <b>Mistake (?)</b> 10–20%, <b>Blunder (??)</b> &gt;20%).</li>"
            "</ul>"
        )
        QMessageBox.information(self, "Evaluation & Annotations Guide", msg)

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
            old = self.settings
            s = d.result_settings()
            self.settings = s
            for k, v in (("scope", s.scope), ("side", s.side), ("name", s.player_name), ("depth", s.depth),
                         ("threads", s.threads), ("hash", s.hash_mb), ("engine", s.engine_path),
                         ("preset", s.preset), ("eval_formula", s.eval_formula),
                         ("annotation_system", s.annotation_system), ("auto_update", s.auto_update),
                         ("auto_install_prereleases", s.auto_install_prereleases),
                         ("disable_holiday_events", s.disable_holiday_events)):
                self.qs.setValue(k, v)
            self.apply_customizations()
            self.qs.setValue("lenient", s.lenient_brilliant)
            self.evalbar.formula = s.eval_formula
            self.graph.formula = s.eval_formula

            # Only re-analyze with Stockfish if engine or search-depth/scope parameters changed.
            engine_changed = (
                old.threads != s.threads
                or old.hash_mb != s.hash_mb
                or old.engine_path != s.engine_path
            )
            analysis_changed = (
                engine_changed
                or old.scope != s.scope
                or old.depth != s.depth
                or (s.scope == "mine_brilliant" and old.lenient_brilliant != s.lenient_brilliant)
                or (
                    s.scope != "all"
                    and (
                        old.side != s.side
                        or (old.player_name or "").strip().lower() != (s.player_name or "").strip().lower()
                    )
                )
            )
            reclassify_needed = (
                old.annotation_system != s.annotation_system
                or old.lenient_brilliant != s.lenient_brilliant
            )
            if analysis_changed:
                self.stop()
                if engine_changed:
                    self.holder.close()
                if self.game:
                    self.orient()
                    self.restart_all()
            else:
                if reclassify_needed:
                    for j in self.jobs:
                        if j.results:
                            A.reclassify_results(j.game, j.results, s)
                if self.game:
                    self.orient()
                    for k in range(len(self.basic)):
                        self.set_row(k)
                    self.refresh_graph()
                    self.update_accuracy(final=bool(self.job and self.job.done))
                    self.goto(self.cur, animate=False, play_sound=False)
                else:
                    self.evalbar.update()
                    self.graph.update()

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
