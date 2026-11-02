"""Generate perfectly centered, balanced icon.ico and icon.png."""
import struct
import sys
from PySide6.QtCore import Qt, QRectF, QBuffer, QIODevice
from PySide6.QtGui import (
    QGuiApplication, QImage, QPainter, QColor, QFont, QLinearGradient, QBrush, QPainterPath
)

app = QGuiApplication(sys.argv)
SIZES = [16, 24, 32, 48, 64, 128, 256]


def render(sz):
    img = QImage(sz, sz, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)

    # 1. Background rounded rectangle (centered with balanced padding)
    pad = sz * 0.04
    r_rect = QRectF(pad, pad, sz - 2 * pad, sz - 2 * pad)
    radius = (sz - 2 * pad) * 0.22

    # Rich gradient
    g = QLinearGradient(0, 0, sz, sz)
    g.setColorAt(0.0, QColor("#387038"))
    g.setColorAt(0.5, QColor("#2a542a"))
    g.setColorAt(1.0, QColor("#183618"))

    p.setBrush(QBrush(g))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(r_rect, radius, radius)

    # Subtle inner border for polish
    p.setPen(QColor(255, 255, 255, 40))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(r_rect.adjusted(1, 1, -1, -1), radius * 0.95, radius * 0.95)

    # 2. Draw Knight Glyph with exact bounding box centering
    font_size = int(sz * 0.62)
    font = QFont("Segoe UI Symbol", font_size)
    path = QPainterPath()
    path.addText(0, 0, font, "♞")
    br = path.boundingRect()

    # Scale path to fit nicely within 66% of the squircle
    target_dim = (sz - 2 * pad) * 0.66
    scale = target_dim / max(br.width(), br.height())

    p.save()
    # Translate so the center of the bounding box is at the exact center of the image (sz/2, sz/2)
    cx, cy = sz / 2.0, sz / 2.0
    p.translate(cx - br.center().x() * scale, cy - br.center().y() * scale)
    p.scale(scale, scale)

    # Soft drop shadow for knight
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 70))
    p.drawPath(path.translated(0, 2))

    # Knight in crisp white
    p.setBrush(QColor("#ffffff"))
    p.drawPath(path)
    p.restore()

    p.end()

    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data()), img


pngs = []
for s in SIZES:
    data, img = render(s)
    pngs.append((s, data))
    if s == 256:
        img.save("icon.png")

out = struct.pack("<HHH", 0, 1, len(pngs))
offset = 6 + 16 * len(pngs)
body = b""
for s, d in pngs:
    out += struct.pack(
        "<BBBBHHII",
        0 if s >= 256 else s,
        0 if s >= 256 else s,
        0,
        0,
        1,
        32,
        len(d),
        offset + len(body),
    )
    body += d
open("icon.ico", "wb").write(out + body)
print("Centered icon generated successfully:", len(out + body), "bytes")
