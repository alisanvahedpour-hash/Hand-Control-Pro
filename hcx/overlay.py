"""ابزار ارائه روی کل صفحه (لیزر، نقاشی، نورافکن، زمان‌سنج) و کیبورد هوایی"""
import time

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QCursor, QGuiApplication, QPainter, QPen, QPainterPath
from PyQt6.QtWidgets import (QGridLayout, QHBoxLayout, QPushButton, QSizePolicy,
                             QVBoxLayout, QWidget)

# ------------------------------------------------------------------ حالت (منطق خالص)


class OverlayState:
    COLORS = ["#ff3b30", "#ffcc00", "#34c759", "#0a84ff", "#ffffff"]

    def __init__(self):
        self.laser = self.draw = self.spot = self.pen = False
        self.strokes, self.cur = [], None
        self.pos = (0, 0)
        self.timer_t0 = None
        self.color_i = 0

    @property
    def color(self):
        return self.COLORS[self.color_i % len(self.COLORS)]

    def command(self, name):
        """نام فرمان: laser / draw / spot / clear / timer / pen_down / pen_up / color"""
        if name == "laser":
            self.laser = not self.laser
        elif name == "draw":
            self.draw = not self.draw
            if not self.draw:
                self.pen, self.cur = False, None
        elif name == "spot":
            self.spot = not self.spot
        elif name == "clear":
            self.strokes, self.cur = [], None
        elif name == "timer":
            self.timer_t0 = None if self.timer_t0 else time.time()
        elif name == "color":
            self.color_i += 1
        elif name == "pen_down":
            self.pen = True
        elif name == "pen_up":
            self.pen, self.cur = False, None

    def feed(self, x, y):
        self.pos = (x, y)
        if self.pen and self.draw:
            if self.cur is None:
                self.cur = {"color": self.color, "pts": []}
                self.strokes.append(self.cur)
            self.cur["pts"].append((x, y))

    def active(self):
        return bool(self.laser or self.draw or self.spot or self.strokes
                    or self.timer_t0)

    def timer_text(self):
        if not self.timer_t0:
            return ""
        s = int(time.time() - self.timer_t0)
        return f"{s // 60:02d}:{s % 60:02d}"


# ------------------------------------------------------------------ پنجرهٔ روی صفحه


class OverlayWindow(QWidget):
    """پنجرهٔ شفاف، بدون کلیک‌خور، روی همهٔ مانیتورها"""

    def __init__(self):
        super().__init__(None, Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.Tool
                         | Qt.WindowType.WindowTransparentForInput)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.state = OverlayState()
        self.fit_to_screens()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)

    def fit_to_screens(self):
        rect = None
        for sc in QGuiApplication.screens():
            g = sc.geometry()
            rect = g if rect is None else rect.united(g)
        if rect is not None:
            self.setGeometry(rect)

    def command(self, name):
        self.state.command(name)
        if self.state.active():
            if not self.isVisible():
                self.fit_to_screens()
                self.show()
        else:
            self.hide()
        self.update()

    def tick(self):
        if not self.isVisible():
            return
        p = self.mapFromGlobal(QCursor.pos())
        self.state.feed(p.x(), p.y())
        self.update()

    def paintEvent(self, _e):
        st = self.state
        qp = QPainter(self)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)
        if st.spot:                       # نورافکن: همه‌جا تیره به‌جز دایره دور نشانگر
            path = QPainterPath()
            path.addRect(QRectF(self.rect()))
            hole = QPainterPath()
            hole.addEllipse(QPointF(*st.pos), 130, 130)
            qp.fillPath(path.subtracted(hole), QColor(0, 0, 0, 170))
        for s in st.strokes:              # نقاشی
            pts = s["pts"]
            qp.setPen(QPen(QColor(s["color"]), 5, Qt.PenStyle.SolidLine,
                           Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            for a, b in zip(pts, pts[1:]):
                qp.drawLine(QPointF(*a), QPointF(*b))
        if st.laser:                      # لیزر
            c = QPointF(*st.pos)
            qp.setPen(Qt.PenStyle.NoPen)
            qp.setBrush(QColor(255, 40, 40, 70))
            qp.drawEllipse(c, 22, 22)
            qp.setBrush(QColor(255, 30, 30, 230))
            qp.drawEllipse(c, 9, 9)
        text = st.timer_text()
        if text:                          # زمان‌سنج ارائه
            f = qp.font()
            f.setPointSize(22)
            f.setBold(True)
            qp.setFont(f)
            qp.setPen(QColor(255, 255, 255, 230))
            qp.fillRect(QRectF(self.width() - 150, 14, 136, 46), QColor(0, 0, 0, 150))
            qp.drawText(QRectF(self.width() - 150, 14, 136, 46),
                        Qt.AlignmentFlag.AlignCenter, text)


# ------------------------------------------------------------------ کیبورد هوایی

KB_EN = [list("1234567890"), list("qwertyuiop"), list("asdfghjkl"),
         ["Shift"] + list("zxcvbnm") + ["⌫"], ["🌐", "Space", ".", ",", "Enter"]]
KB_FA = [list("۱۲۳۴۵۶۷۸۹۰"), list("ضصثقفغعهخحجچ"), list("شسیبلاتنمکگ"),
         ["Shift"] + list("ظطزرذدپو") + ["⌫"], ["🌐", "Space", "،", ".", "Enter"]]
SPECIAL = {"Shift", "⌫", "🌐", "Space", "Enter"}


def key_output(label, shift=False):
    """('char', متن) یا ('special', نام) برای یک کلید"""
    if label in SPECIAL:
        return ("special", label)
    return ("char", label.upper() if shift and label.isalpha() else label)


class AirKeyboard(QWidget):
    """کیبورد روی صفحه برای استفاده با اشاره + کلیک با مکث؛ فوکوس را از برنامهٔ مقصد نمی‌گیرد"""

    def __init__(self, on_char, on_special, scale=1.0):
        super().__init__(None, Qt.WindowType.Tool
                         | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowTitle("کیبورد هوایی")
        self.on_char, self.on_special = on_char, on_special
        self.scale = scale
        self.lang, self.shift = "en", False
        self.root = QVBoxLayout(self)
        self.root.setSpacing(4)
        self.build()

    def build(self):
        while self.root.count():
            item = self.root.takeAt(0)
            lay = item.layout()
            if lay is not None:
                while lay.count():
                    w = lay.takeAt(0).widget()
                    if w is not None:
                        w.deleteLater()
        rows = KB_EN if self.lang == "en" else KB_FA
        size = int(52 * self.scale)
        for row in rows:
            h = QHBoxLayout()
            h.setSpacing(4)
            for label in row:
                shown = label.upper() if (self.shift and self.lang == "en"
                                          and label.isalpha()) else label
                b = QPushButton(shown)
                b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                b.setMinimumSize(int(size * (3.2 if label == "Space" else 1.3
                                              if label in SPECIAL else 1)), size)
                b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                b.clicked.connect(lambda _=False, lb=label: self.press(lb))
                h.addWidget(b)
            self.root.addLayout(h)

    def press(self, label):
        kind, val = key_output(label, self.shift)
        if kind == "char":
            self.on_char(val)
            if self.shift:
                self.shift = False
                self.build()
        elif val == "Shift":
            self.shift = not self.shift
            self.build()
        elif val == "🌐":
            self.lang = "fa" if self.lang == "en" else "en"
            self.shift = False
            self.build()
        else:
            self.on_special(val)
