"""
smooth_widgets.py — 曲率连续（超椭圆）圆角的 PyQt6 控件
- smooth_round_rect_path: 纯函数，生成超椭圆角路径
- SmoothRoundedWidget:    平滑圆角面板/卡片基类
- SmoothFramelessWindow:  无边框 + 半透明 + 阴影 + 可拖动 的圆角窗口
"""
import math
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen, QRegion
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGraphicsDropShadowEffect


def smooth_round_rect_path(rect: QRectF, radius: float, n: float = 5.0, seg: int | None = None) -> QPainterPath:
    """超椭圆角圆角矩形路径。n=2 等于普通圆角；n=4~6 接近 iOS squircle。"""
    x, y, w, h = rect.left(), rect.top(), rect.width(), rect.height()
    path = QPainterPath()
    if w <= 0 or h <= 0:
        return path
    r = max(0.0, min(float(radius), min(w, h) / 2.0))
    if r <= 0:
        path.addRect(rect)
        return path
    if seg is None:
        seg = max(12, int(r / 2))          # 半径越大采样越密
    else:
        seg = max(1, int(seg))
    e = 2.0 / max(0.001, float(n))
    pts = [(x + r, y), (x + w - r, y)]     # 上边
    corners = [                            # (圆心x, 圆心y, x符号, y符号, x是否用sin)
        (x + w - r, y + r,      1, -1, True),
        (x + w - r, y + h - r,  1,  1, False),
        (x + r,     y + h - r, -1,  1, True),
        (x + r,     y + r,     -1, -1, False),
    ]
    edge_end = [(x + w, y + h - r), (x + r, y + h), (x, y + r), None]
    for (cx, cy, sx, sy, x_is_sin), nxt in zip(corners, edge_end):
        for i in range(seg + 1):
            t = math.pi / 2 * i / seg
            a, b = (math.sin(t), math.cos(t)) if x_is_sin else (math.cos(t), math.sin(t))
            a = max(0.0, float(a))
            b = max(0.0, float(b))
            pts.append((cx + sx * r * a ** e, cy + sy * r * b ** e))
        if nxt:
            pts.append(nxt)
    path.moveTo(*pts[0])
    for p in pts[1:]:
        path.lineTo(*p)
    path.closeSubpath()
    return path


class SmoothRoundedWidget(QWidget):
    """平滑圆角面板。可直接用，也可继承后在 paintEvent 里 super() 之后叠加自定义绘制。"""

    def __init__(self, parent=None, *, radius=16.0, smoothness=5.0,
                 bg_color="#FFFFFF", border_color=None, border_width=0.0,
                 clip_children=False):
        super().__init__(parent)
        self._radius = float(radius)
        self._smoothness = float(smoothness)
        self._bg = QColor(bg_color) if bg_color else None
        self._border = QColor(border_color) if border_color else None
        self._border_w = float(border_width)
        self._clip = clip_children
        self._path = QPainterPath()

    # ---- 可运行时修改的属性 ----
    def setRadius(self, r):           self._radius = float(r);    self._rebuild(); self.update()
    def setSmoothness(self, n):       self._smoothness = float(n); self._rebuild(); self.update()
    def setBackgroundColor(self, c):  self._bg = QColor(c) if c else None; self.update()
    def setBorder(self, color, width=1.0):
        self._border = QColor(color) if color else None
        self._border_w = float(width); self._rebuild(); self.update()
    def shapePath(self) -> QPainterPath:  return QPainterPath(self._path)

    def _rebuild(self):
        bw = self._border_w
        inset = bw / 2.0  # 描边居中，向内缩半个线宽，避免描边被裁掉
        rect = QRectF(inset, inset, self.width() - bw, self.height() - bw)
        self._path = smooth_round_rect_path(rect, self._radius, self._smoothness)
        if self._clip:  # 注意：mask 是 1-bit，边缘有锯齿；仅在需要把子控件硬裁进圆角时用
            self.setMask(QRegion(self._path.toFillPolygon().toPolygon()))

    def resizeEvent(self, e):
        self._rebuild()
        super().resizeEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._bg:
            p.fillPath(self._path, self._bg)
        if self._border and self._border_w > 0:
            pen = QPen(self._border, self._border_w)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.strokePath(self._path, pen)
        # 继承后可在此之后画内容


class SmoothFramelessWindow(QWidget):
    """无边框 + 半透明 + 平滑圆角 + 阴影 + 可拖动。把内容加到 .contentLayout()。"""

    def __init__(self, *, radius=18.0, smoothness=5.0, bg_color="#FFFFFF",
                 border_color=None, border_width=0.0,
                 shadow_blur=36, shadow_color="#55000000", shadow_offset=(0, 8),
                 margin=48, draggable=True):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._draggable = draggable
        self._drag_pos = None

        self.card = SmoothRoundedWidget(
            self, radius=radius, smoothness=smoothness, bg_color=bg_color,
            border_color=border_color, border_width=border_width)
        eff = QGraphicsDropShadowEffect(self.card)
        eff.setBlurRadius(shadow_blur)
        eff.setColor(QColor(shadow_color))
        eff.setOffset(*shadow_offset)
        self.card.setGraphicsEffect(eff)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(margin, margin, margin, margin)  # 给阴影留空间
        outer.addWidget(self.card)
        self._content = QVBoxLayout(self.card)
        self._content.setContentsMargins(int(radius), int(radius), int(radius), int(radius))

    def contentLayout(self) -> QVBoxLayout:
        return self._content

    # ---- 拖动移动 ----
    def mousePressEvent(self, e):
        if self._draggable and e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)
    def mouseReleaseEvent(self, e):
        self._drag_pos = None
