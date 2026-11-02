"""One-off: build assets/icons from C:\\Users\\pierr\\Downloads\\Assets (+ a generated 'excellent' icon)."""
import os
import sys
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (QGuiApplication, QImage, QPainter, QColor, QFont, QPainterPath, QBrush)

app = QGuiApplication(sys.argv)
SRC = r"C:\Users\pierr\Downloads\Assets"
DST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons")
os.makedirs(DST, exist_ok=True)
W = 256

for fn in os.listdir(SRC):
    if not fn.endswith("_1024x.png"):
        continue
    stem = fn[: -len("_1024x.png")]
    img = QImage(os.path.join(SRC, fn))
    img = img.scaledToWidth(W, Qt.SmoothTransformation)
    img.save(os.path.join(DST, stem + ".png"))
    print(stem, img.width(), img.height())

# generated "excellent" icon (no source asset): green circle + white thumbs-up, same style as best/good
ref = QImage(os.path.join(DST, "best.png"))
h = ref.height()
img = QImage(W, h, QImage.Format_ARGB32)
img.fill(Qt.transparent)
p = QPainter(img)
p.setRenderHint(QPainter.Antialiasing)
p.setPen(Qt.NoPen)
p.setBrush(QColor("#b2b2b2"))
p.drawEllipse(QRectF(0, 6, W, h - 6))
p.setBrush(QColor("#7fb04f"))
p.drawEllipse(QRectF(0, 0, W, W - 6))
path = QPainterPath()
f = QFont("Segoe UI Symbol", 100)
path.addText(0, 0, f, "\U0001F44D")
br = path.boundingRect()
scale = (W * 0.5) / max(br.width(), br.height())
cx, cy = W / 2, (W - 6) / 2
p.translate(cx - br.center().x() * scale, cy - br.center().y() * scale + 3)
p.scale(scale, scale)
p.setBrush(QColor("#5f8a37"))
p.drawPath(path.translated(0, 6))      # soft shadow
p.setBrush(QColor("white"))
p.drawPath(path)
p.end()
img.save(os.path.join(DST, "excellent.png"))
print("excellent done", br)


# generated "miss" icon: salmon circle with an outlined white X (same style as the other icons)
from PySide6.QtGui import QPen
ref = QImage(os.path.join(DST, "incorrect.png"))
img = QImage(W, ref.height(), QImage.Format_ARGB32)
img.fill(Qt.transparent)
p = QPainter(img)
p.setRenderHint(QPainter.Antialiasing)
p.setPen(Qt.NoPen)
p.setBrush(QColor("#b2b2b2"))
p.drawEllipse(QRectF(0, 6, W, img.height() - 6))
p.setBrush(QColor("#ee6b6e"))
p.drawEllipse(QRectF(0, 0, W, W - 6))
a, b = W * 0.30, W * 0.70
for color, width in (("white", 44), ("#ee6b6e", 24)):
    p.setPen(QPen(QColor(color), width, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(a, a - 3), QPointF(b, b - 3))
    p.drawLine(QPointF(b, a - 3), QPointF(a, b - 3))
p.end()
img.save(os.path.join(DST, "miss.png"))
print("miss done")
