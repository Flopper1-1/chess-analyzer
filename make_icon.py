"""Generate icon.ico (PNG-embedded, multi-size) using Qt."""
import struct
import sys
from PySide6.QtCore import Qt, QRectF, QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QGuiApplication, QImage, QPainter, QColor, QFont, QLinearGradient, QBrush

app = QGuiApplication(sys.argv)
SIZES = [16, 24, 32, 48, 64, 128, 256]


def render(sz):
    img = QImage(sz, sz, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    g = QLinearGradient(0, 0, sz, sz)
    g.setColorAt(0, QColor("#3b6b3a"))
    g.setColorAt(1, QColor("#1f3d1f"))
    p.setBrush(QBrush(g))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(0, 0, sz, sz), sz * 0.2, sz * 0.2)
    # checker strip
    c = sz / 8
    p.setBrush(QColor(255, 255, 255, 40))
    for i in range(8):
        if i % 2 == 0:
            p.drawRect(QRectF(i * c, sz - c, c, c))
    p.setPen(QColor("#ffffff"))
    p.setFont(QFont("Segoe UI Symbol", int(sz * 0.62)))
    p.drawText(QRectF(0, -sz * 0.04, sz, sz * 0.95), Qt.AlignCenter, "♞")
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
    out += struct.pack("<BBBBHHII", 0 if s >= 256 else s, 0 if s >= 256 else s, 0, 0, 1, 32, len(d), offset + len(body))
    body += d
open("icon.ico", "wb").write(out + body)
print("icon written", len(out + body))

