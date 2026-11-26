# -*- coding: utf-8 -*-
"""Liquid Glass kit for Raspberry — Tomato's glass_kit.py as of 2026-11-16 (= Broccoli snapshot 418),
copied unchanged except the translation context below ("Raspberry:").

UI STYLE BOOK: /Users/ryanshen/Documents/A-workingfilewithp3.11/UI_STYLEBOOK_macOS27.md
The style book (section 8) says new apps copy Broccoli's functions instead of rewriting them,
so the blocks below are Broccoli's own code, verbatim except where marked "Strawberry:".
Import this module AFTER the QApplication exists (and after the new-design declaration).
"""
import sys
import os
import re
import math
import time
import json
import logging
import weakref
import threading
import functools
import atexit
from ctypes import c_void_p
from PyQt6.QtWidgets import (QApplication, QDialog, QGraphicsDropShadowEffect, QGraphicsScene, QHBoxLayout, QLabel, QLineEdit, QMenu, QPlainTextEdit, QProxyStyle, QPushButton, QSizePolicy, QStyle, QTextEdit, QVBoxLayout, QWidget, QWidgetAction)
from PyQt6.QtCore import (QCoreApplication, QEvent, QObject, QPoint, QPointF, QRect, QRectF, QSize, QTimer, Qt, pyqtSignal)
from PyQt6.QtGui import (QAction, QBrush, QColor, QCursor, QFont, QGuiApplication, QIcon, QImage, QKeySequence, QLinearGradient, QPainter, QPainterPath, QPalette, QPen, QPixmap, QRegion)
import PyQt6.QtGui
import PyQt6.QtWidgets
import PyQt6.QtCore

app = QApplication.instance()
if app is None:
    raise RuntimeError('glass_kit: create the QApplication before importing this module')

from smooth_widgets import smooth_round_rect_path

try:
    import AppKit
    from AppKit import NSApp, NSColor
except ImportError:
    AppKit = None
    NSApp = None
    NSColor = None
try:
    from Foundation import NSUserDefaults, NSSelectorFromString, NSDistributedNotificationCenter, NSObject
    import objc
except Exception:
    NSUserDefaults = None
    NSSelectorFromString = None
    NSDistributedNotificationCenter = None
    NSObject = None
    objc = None

MAIN_WINDOW_SMOOTH_RADIUS = 36
NOTICE_SMOOTH_RADIUS = 59
FLOATING_PANEL_SMOOTH_RADIUS = MAIN_WINDOW_SMOOTH_RADIUS
FLOATING_PANEL_GLASS_RADIUS = 16
APPROVAL_DIALOG_SMOOTH_RADIUS = 36
BAR_ACCESSORY_SMOOTH_RADIUS = 36
EDITOR_CARD_SMOOTH_RADIUS = 36


def _tr(text: str) -> str:
    """Raspberry: translate a UI string via the installed Qt translator (context 'Raspberry')."""
    return QCoreApplication.translate('Raspberry', text)

# ---- Broccoli 418 lines 620-831 ----

class SmoothPanelWidget(QWidget):
    """Root panel background drawn with continuous-curvature corners."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._smooth_panel_bg = QColor('#FFFFFF')
        self._smooth_panel_border = QColor('#ECECEC')
        self._smooth_panel_radius = float(FLOATING_PANEL_SMOOTH_RADIUS)
        self._smooth_panel_border_width = 1.0

    def set_smooth_panel_background(self, bg_color, border_color, radius=FLOATING_PANEL_SMOOTH_RADIUS, border_width=1.0):
        bg = QColor(bg_color)
        border = QColor(border_color)
        next_bg = bg if bg.isValid() else self._smooth_panel_bg
        next_border = border if border.isValid() else self._smooth_panel_border
        next_radius = float(radius)
        next_border_width = float(border_width)
        if (
            next_bg == self._smooth_panel_bg
            and next_border == self._smooth_panel_border
            and next_radius == self._smooth_panel_radius
            and next_border_width == self._smooth_panel_border_width
        ):
            return
        if bg.isValid():
            self._smooth_panel_bg = bg
        if border.isValid():
            self._smooth_panel_border = border
        self._smooth_panel_radius = float(radius)
        self._smooth_panel_border_width = float(border_width)
        self.update()

    def paintEvent(self, event):
        if getattr(self, '_liquid_glass_active', False):
            return   # 液态玻璃时只剩内容，底色和边框由系统玻璃提供
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            bw = max(0.0, float(getattr(self, '_smooth_panel_border_width', 1.0)))
            inset = bw / 2.0
            rect = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)
            path = smooth_round_rect_path(rect, getattr(self, '_smooth_panel_radius', float(FLOATING_PANEL_SMOOTH_RADIUS)))
            source = getattr(self, '_frosted_backdrop_source', None)
            backdrop = source() if callable(source) else None
            if backdrop is not None:
                self._paint_frosted_glass(painter, path, *backdrop)
                return
            painter.fillPath(path, getattr(self, '_smooth_panel_bg', QColor('#FFFFFF')))
            if bw > 0:
                pen = QPen(getattr(self, '_smooth_panel_border', QColor('#ECECEC')), bw)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                painter.strokePath(path, pen)
        finally:
            painter.end()

    def _paint_frosted_glass(self, painter, path, pixmap, target):
        """Frosted glass for a panel sliding over the main panel: the blurred snapshot of
        what lies under it (taken by its scrim), a translucent tint of the panel colour
        and a light rim — system glass cannot sit under ordinary widgets inside the
        main window, so this is drawn by Qt."""
        dark = self._smooth_panel_bg.lightness() < 128
        painter.save()
        painter.setClipPath(path)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawPixmap(target, pixmap, QRectF(pixmap.rect()))
        painter.restore()
        tint = QColor(self._smooth_panel_bg)
        tint.setAlpha(198 if dark else 182)
        painter.fillPath(path, tint)
        rim = QLinearGradient(0, 0, 0, max(1, self.height()))
        rim.setColorAt(0.0, QColor(255, 255, 255, 70 if dark else 235))
        rim.setColorAt(0.45, QColor(255, 255, 255, 22 if dark else 110))
        rim.setColorAt(1.0, QColor(255, 255, 255, 40 if dark else 170))
        pen = QPen(QBrush(rim), 1.3)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.strokePath(path, pen)
        outline = QColor(0, 0, 0, 60 if dark else 22)
        painter.strokePath(path, QPen(outline, 0.6))


class PanelCachedShadow(QWidget):
    """A sliding panel's soft drop shadow laid under it as a sibling, drawn once into a picture per
    size (with Qt's own drop-shadow blur, so it looks the same). A QGraphicsDropShadowEffect on the
    panel looks the same but renders and blurs the WHOLE panel again on every change inside it: one
    scroll step in the question branches list cost ~14 ms, with this ~1 ms (2026-11-08)."""

    def __init__(self, panel, blur: float = 34.0, dy: float = 10.0, color=None):
        super().__init__(panel.parentWidget())
        self._panel = panel
        self._blur = float(blur)
        self._dy = float(dy)
        self._color = QColor(color) if color is not None else QColor(0, 0, 0, 45)
        self._margin = int(math.ceil(self._blur)) + int(math.ceil(abs(self._dy)))
        self._image = None
        self._image_key = None
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.hide()
        panel.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self._panel:
            kind = event.type()
            if kind in (QEvent.Type.Move, QEvent.Type.Resize):
                self._follow()
            elif kind == QEvent.Type.Show:
                self._follow()
                self.show()
                self.stackUnder(self._panel)
            elif kind == QEvent.Type.Hide:
                self.hide()
            elif kind == QEvent.Type.ZOrderChange:
                self.stackUnder(self._panel)
        return False

    def _follow(self):
        m = self._margin
        self.setGeometry(self._panel.geometry().adjusted(-m, -m, m, m))

    def _shadow_image(self) -> QImage:
        panel = self._panel
        ratio = max(1.0, float(self.devicePixelRatioF()))
        radius = float(getattr(panel, '_smooth_panel_radius', FLOATING_PANEL_SMOOTH_RADIUS))
        key = (panel.width(), panel.height(), radius, ratio, self._color.rgba())
        if self._image is not None and self._image_key == key:
            return self._image
        m = self._margin
        w, h = float(panel.width()), float(panel.height())
        shape = smooth_round_rect_path(QRectF(0, 0, w, h), radius)
        scene = QGraphicsScene()
        item = PyQt6.QtWidgets.QGraphicsPathItem(shape)
        item.setBrush(QColor(0, 0, 0))
        item.setPen(QPen(Qt.PenStyle.NoPen))
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(self._blur)
        effect.setOffset(0, self._dy)
        effect.setColor(self._color)
        item.setGraphicsEffect(effect)
        scene.addItem(item)
        image = QImage(int(math.ceil((w + 2 * m) * ratio)), int(math.ceil((h + 2 * m) * ratio)),
                       QImage.Format.Format_ARGB32_Premultiplied)
        image.setDevicePixelRatio(ratio)
        image.fill(0)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        scene.render(painter, QRectF(0, 0, w + 2 * m, h + 2 * m), QRectF(-m, -m, w + 2 * m, h + 2 * m))
        # the shape itself goes: only the shadow around it stays (the panel covers that area)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.translate(m, m)
        painter.fillPath(shape, QColor(0, 0, 0))
        painter.end()
        self._image, self._image_key = image, key
        return image

    def paintEvent(self, event):
        if self._panel.width() <= 0 or self._panel.height() <= 0:
            return
        painter = QPainter(self)
        painter.drawImage(QPointF(0, 0), self._shadow_image())
        painter.end()


def broccoli_blurred_backdrop(pixmap):
    """A cheap, edge-safe blur of a snapshot: shrink a lot, grow back a little (bilinear);
    drawn stretched to the full size it reads as a soft frosted backdrop."""
    if pixmap is None or pixmap.isNull():
        return None
    image = pixmap.toImage()
    width, height = max(1, image.width()), max(1, image.height())
    tiny = image.scaled(max(2, width // 14), max(2, height // 14), Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation)
    soft = tiny.scaled(max(2, width // 4), max(2, height // 4), Qt.AspectRatioMode.IgnoreAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
    return QPixmap.fromImage(soft)


def enable_frosted_panel(panel, scrim):
    """Panel draws as frosted glass over the blurred snapshot its scrim took."""
    if not FROSTED_PANELS_ENABLED:
        return

    def source(panel=panel, scrim=scrim):
        try:
            if not scrim.isVisible():
                return None
            backdrop = getattr(scrim, '_backdrop', None)
            if backdrop is None or backdrop.isNull():
                return None
            offset = scrim.pos() - panel.pos()
            return backdrop, QRectF(QRect(offset, scrim.size()))
        except RuntimeError:
            return None
    panel._frosted_backdrop_source = source


FROSTED_PANELS_ENABLED = os.environ.get('BROCCOLI_FROSTED_PANELS', '1') != '0'


def _strip_menu_icons(menu) -> None:
    # Remove the leading icon from every item (recursively into submenus) so our styled
    # menu is text-only. Standard menus (Cut/Copy/Paste...) ship icons; this drops them.
    try:
        for action in menu.actions():
            if not action.icon().isNull():
                action.setIcon(QIcon())
            sub = action.menu()
            if sub is not None:
                _strip_menu_icons(sub)
    except Exception:
        pass


# ---- Broccoli 418 lines 833-879 ----

def style_broccoli_context_menu(menu: QMenu) -> QMenu:
    dark = is_dark_theme(app)
    bg = '#2D2D2D' if dark else '#FFFFFF'
    border = '#3A3A3A' if dark else '#E5E5EA'
    text = '#F2F2F7' if dark else '#20242B'
    hover = '#3A3A3A' if dark else '#F2F2F7'
    separator = '#3A3A3A' if dark else '#E5E5EA'
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    menu.setStyleSheet(f"""
        QMenu {{
            background-color: {bg};
            color: {text};
            border: 1px solid {border};
            border-radius: 12px;
            padding: 6px;
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 13px;
        }}
        QMenu::item {{
            background: transparent;
            border-radius: 8px;
            padding: 7px 28px 7px 12px;
            min-width: 120px;
        }}
        QMenu::item:selected {{
            background: {hover};
        }}
        QMenu::item:disabled {{
            color: {'#8E8E93' if dark else '#A0A0A6'};
        }}
        QMenu::separator {{
            height: 1px;
            background: {separator};
            margin: 5px 8px;
        }}
        QMenu::right-arrow {{
            width: 8px;
            height: 8px;
            padding-right: 8px;
        }}
    """)
    _strip_menu_icons(menu)                                       # icons present now
    menu.aboutToShow.connect(lambda: _strip_menu_icons(menu))     # and any added later
    # On macOS this menu is shown as a native NSMenu (see exec_native_qmenu); the stylesheet
    # above is what the Qt fallback looks like.
    menu.setProperty('broccoliNativeMenu', True)
    return menu

# ---- Broccoli 418 lines 966-3502 ----

# 菜单内容照旧用 QMenu 定义（style_broccoli_context_menu 给菜单打上 broccoliNativeMenu
# 标记）；在 macOS 上 menu.exec() 时逐项翻成系统 NSMenu 弹出：液态玻璃外观、macOS 27
# 自动加的 "Ask Siri" 一栏、"自动填充 / 服务"，以及可编辑文字框里的写作工具，都由系统
# 提供。选中项照旧触发对应 QAction 并作为 exec() 的返回值，调用处一行不用改。
# 退回 Qt 自绘菜单：非 cocoa 平台（离屏测试）、菜单里有没说明原生样子的 QWidgetAction、
# 出错、或环境变量 BROCCOLI_NATIVE_MENUS=0。
NATIVE_CONTEXT_MENUS_ENABLED = os.environ.get('BROCCOLI_NATIVE_MENUS', '1') != '0'
# Single-choice drop-downs (DropdownButton) use the system pop-up menu too.
NATIVE_DROPDOWNS_ENABLED = os.environ.get('BROCCOLI_NATIVE_DROPDOWNS', '1') != '0'
NATIVE_MENU_CONTEXT_WINDOW_SECONDS = 2.0   # 右键后多久内弹出的菜单算右键菜单（对话区菜单是异步弹出的）
_QMENU_EXEC_QT = QMenu.exec
_NATIVE_MENU_RIGHT_CLICK = {'t': -1e9}
_NATIVE_MENU_MONITOR = []
_ACTIVE_NATIVE_MENU = {}   # 测试用：当前打开的 NSMenu
_NATIVE_MENU_LAST_INFO = {}   # 测试用：最近一次原生菜单的呈现方式

if NSObject is not None and objc is not None:
    class BroccoliNativeMenuTarget(NSObject):
        """NSMenuItem 的 action 目标：只记下选了第几项，菜单关掉后再执行。"""

        def init(self):
            self = objc.super(BroccoliNativeMenuTarget, self).init()
            if self is None:
                return None
            self.chosen_tag = -1
            return self

        def menuItemChosen_(self, sender):
            self.chosen_tag = int(sender.tag())

        # While a modal dialog is open (Qt runs it as an NSModalSession), AppKit only sends a
        # menu item's action to a target that says it works when modal — without this every
        # choice in a drop-down inside a modal dialog was silently dropped (the group colour,
        # the MCP transport…: they always stayed on the first item). 2026-10-27
        @objc.typedSelector(b'Z@:')
        def worksWhenModal(self):
            return True

    class BroccoliRunLoopCallback(NSObject):
        """NSTimer 目标：在 AppKit 的模态循环里（如 NSAlert.runModal）执行一段 Python。"""

        def initWithCallback_(self, callback):
            self = objc.super(BroccoliRunLoopCallback, self).init()
            if self is None:
                return None
            self.callback = callback
            return self

        def fire_(self, timer):
            try:
                self.callback()
            except Exception:
                logging.exception('Run-loop callback failed.')
else:
    BroccoliNativeMenuTarget = None
    BroccoliRunLoopCallback = None


def _ensure_native_menu_right_click_monitor():
    """记下最近一次右键（或 Control+左键）的时间：只监听这几种事件，开销可以忽略。
    对话区的菜单要先异步查询选区才弹出，那时“当前事件”早已不是右键了。"""
    if _NATIVE_MENU_MONITOR or AppKit is None or sys.platform != 'darwin':
        return
    try:
        if QGuiApplication.platformName() != 'cocoa':
            return
        right_down = int(getattr(AppKit, 'NSEventTypeRightMouseDown', 3))
        right_up = int(getattr(AppKit, 'NSEventTypeRightMouseUp', 4))
        left_down = int(getattr(AppKit, 'NSEventTypeLeftMouseDown', 1))
        control = int(getattr(AppKit, 'NSEventModifierFlagControl', 1 << 18))
        mask = (int(getattr(AppKit, 'NSEventMaskRightMouseDown', 1 << 3))
                | int(getattr(AppKit, 'NSEventMaskRightMouseUp', 1 << 4))
                | int(getattr(AppKit, 'NSEventMaskLeftMouseDown', 1 << 1)))

        def handler(event):
            try:
                kind = int(event.type())
                if kind in (right_down, right_up) or (kind == left_down and int(event.modifierFlags()) & control):
                    _NATIVE_MENU_RIGHT_CLICK['t'] = time.monotonic()
            except Exception:
                pass
            return event

        monitor = AppKit.NSEvent.addLocalMonitorForEventsMatchingMask_handler_(mask, handler)
        _NATIVE_MENU_MONITOR.append((monitor, handler))
    except Exception:
        logging.exception('Installing the right-click monitor for native menus failed.')


def set_native_menu_items(action, items: list) -> None:
    """For a QWidgetAction: what its embedded widget is in a native menu. Each item is
    {'title', 'callback', 'icon' (QIcon), 'tooltip', 'enabled', 'children'}; without this a
    menu containing the widget action falls back to the Qt-drawn menu."""
    action.setProperty('broccoliNativeItems', list(items or []))


def _native_menu_title(text: str) -> str:
    # Qt mnemonics: '&&' is a literal '&', a single '&' marks the shortcut letter.
    return str(text or '').replace('&&', '\0').replace('&', '').replace('\0', '&')


def _qmenu_can_go_native(menu) -> bool:
    for action in menu.actions():
        if isinstance(action, QWidgetAction) and action.isVisible() and action.property('broccoliNativeItems') is None:
            return False
        if action.menu() is not None and not _qmenu_can_go_native(action.menu()):
            return False
    return True


def _native_menu_image(icon) -> object:
    if icon is None or icon.isNull():
        return None
    from PyQt6.QtCore import QBuffer, QIODevice
    pixmap = icon.pixmap(QSize(28, 28))   # @2x for a 14 pt image
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(buffer, 'PNG')
    data = bytes(buffer.data())
    image = AppKit.NSImage.alloc().initWithData_(AppKit.NSData.dataWithBytes_length_(data, len(data)))
    if image is not None:
        import Foundation
        image.setSize_(Foundation.NSMakeSize(14, 14))
    return image


def _native_key_equivalent(action):
    """Shortcut text on the right (⌘C …) for simple shortcuts such as Qt's standard text menu."""
    try:
        sequence = action.shortcut()
        if sequence.isEmpty():
            return '', 0
        parts = sequence.toString(QKeySequence.SequenceFormat.PortableText).split(',')[0].split('+')
    except Exception:
        return '', 0
    key = parts[-1] if parts else ''
    if len(key) != 1:
        return '', 0
    masks = {
        'Ctrl': int(getattr(AppKit, 'NSEventModifierFlagCommand', 1 << 20)),   # Qt Ctrl = ⌘ on macOS
        'Shift': int(getattr(AppKit, 'NSEventModifierFlagShift', 1 << 17)),
        'Alt': int(getattr(AppKit, 'NSEventModifierFlagOption', 1 << 19)),
        'Meta': int(getattr(AppKit, 'NSEventModifierFlagControl', 1 << 18)),
    }
    mask = 0
    for part in parts[:-1]:
        mask |= masks.get(part, 0)
    return key.lower(), mask


def _mirror_native_items(native, items, target, flat):
    for spec in items or []:
        if not isinstance(spec, dict):
            continue
        if spec.get('separator'):
            native.addItem_(AppKit.NSMenuItem.separatorItem())
            continue
        item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            _native_menu_title(spec.get('title', '')), None, '')
        item.setEnabled_(bool(spec.get('enabled', True)))
        if spec.get('tooltip'):
            item.setToolTip_(str(spec['tooltip']))
        image = _native_menu_image(spec.get('icon'))
        if image is not None:
            item.setImage_(image)
        children = spec.get('children')
        if children:
            submenu = AppKit.NSMenu.alloc().initWithTitle_(_native_menu_title(spec.get('title', '')))
            submenu.setAutoenablesItems_(False)
            _mirror_native_items(submenu, children, target, flat)
            item.setSubmenu_(submenu)
        elif callable(spec.get('callback')):
            item.setTarget_(target)
            item.setAction_('menuItemChosen:')
            item.setTag_(len(flat))
            flat.append(spec['callback'])
        native.addItem_(item)


def _mirror_qmenu_to_nsmenu(menu, target, flat, shown_menus):
    menu.aboutToShow.emit()          # dynamic menus fill / adjust themselves here, as with exec()
    shown_menus.append(menu)
    native = AppKit.NSMenu.alloc().initWithTitle_(_native_menu_title(menu.title()))
    native.setAutoenablesItems_(False)   # enabled state comes from the QAction
    for action in menu.actions():
        if not action.isVisible():
            continue
        if action.isSeparator():
            native.addItem_(AppKit.NSMenuItem.separatorItem())
            continue
        if isinstance(action, QWidgetAction):
            _mirror_native_items(native, action.property('broccoliNativeItems'), target, flat)
            continue
        key, modifiers = _native_key_equivalent(action)
        item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(_native_menu_title(action.text()), None, key)
        if key:
            item.setKeyEquivalentModifierMask_(modifiers)
        item.setEnabled_(action.isEnabled())
        if action.toolTip() and action.toolTip() != action.text().replace('&', ''):
            item.setToolTip_(action.toolTip())
        submenu = action.menu()
        if submenu is not None:
            item.setSubmenu_(_mirror_qmenu_to_nsmenu(submenu, target, flat, shown_menus))
        else:
            item.setTarget_(target)
            item.setAction_('menuItemChosen:')
            item.setTag_(len(flat))
            flat.append(action)
            if action.isCheckable():
                item.setState_(int(getattr(AppKit, 'NSControlStateValueOn', 1)) if action.isChecked()
                               else int(getattr(AppKit, 'NSControlStateValueOff', 0)))
        native.addItem_(item)
    return native


def _native_menu_host_widget(menu, global_pos):
    host = QApplication.widgetAt(global_pos)
    if host is None or isinstance(host, QMenu):
        host = menu.parentWidget()
    return host or QApplication.activeWindow()


def _native_menu_is_editable_text(host) -> bool:
    widget = host
    for _depth in range(4):              # a QTextEdit's viewport is the widget under the pointer
        if widget is None:
            return False
        if isinstance(widget, (QLineEdit, QTextEdit, QPlainTextEdit)):
            return not widget.isReadOnly()
        widget = widget.parentWidget()
    return False


def _qt_object_gone(obj) -> bool:
    try:
        from PyQt6 import sip
        return sip.isdeleted(obj)
    except Exception:
        return False


def _menus_about_to_hide(shown_menus):
    """Tell the mirrored Qt menus that they closed. While the system menu was open the app kept
    running: a menu whose owner was rebuilt in the meantime (Raspberry: the icon grid) is gone."""
    for shown in shown_menus:
        if _qt_object_gone(shown):
            continue
        try:
            shown.aboutToHide.emit()
        except RuntimeError:
            pass


def _finish_native_menu(flat, chosen_tag):
    """Run what was chosen once the menu has closed; return the QAction like QMenu.exec."""
    if not 0 <= int(chosen_tag) < len(flat):
        return None
    chosen = flat[int(chosen_tag)]
    if isinstance(chosen, QAction):
        if _qt_object_gone(chosen):
            return None    # its menu was deleted while the system menu was open
        chosen.trigger()   # emits triggered (and toggles checkable actions), as QMenu.exec does
        return chosen
    try:
        chosen()           # a widget action's button (e.g. a quick-annotation row)
    except Exception:
        logging.exception('A native menu item callback failed.')
    return None


def exec_native_qmenu(menu, global_pos, presentation=None, positioning_action=None, min_width=None, dark=None):
    """(handled, chosen QAction or None). handled=False means: show the Qt menu instead.
    presentation='dropdown' always shows a plain pop-up (never the context-menu extras);
    positioning_action is put at global_pos (like a pop-up button: the current choice sits
    on the button); min_width in points; dark=True forces a dark menu."""
    if not (NATIVE_CONTEXT_MENUS_ENABLED and AppKit is not None and objc is not None
            and BroccoliNativeMenuTarget is not None and sys.platform == 'darwin'):
        return False, None
    if QGuiApplication.platformName() != 'cocoa' or not _qmenu_can_go_native(menu):
        return False, None
    _ensure_native_menu_right_click_monitor()
    shown_menus = []
    try:
        host = _native_menu_host_widget(menu, global_pos)
        if host is None:
            return False, None
        view = objc.objc_object(c_void_p=int(host.window().winId()))
        ns_window = view.window()
        if ns_window is None:
            return False, None
        target = BroccoliNativeMenuTarget.alloc().init()
        flat = []
        native = _mirror_qmenu_to_nsmenu(menu, target, flat, shown_menus)
        context = (time.monotonic() - _NATIVE_MENU_RIGHT_CLICK['t']) < NATIVE_MENU_CONTEXT_WINDOW_SECONDS
        editable = _native_menu_is_editable_text(host)
        if context and editable:
            # AppKit does not insert Writing Tools into this menu by itself, but the standard
            # item works: Qt's QNSView serves the selection and takes the result back.
            tools = list(AppKit.NSMenuItem.writingToolsItems() or [])
            if tools:
                native.insertItem_atIndex_(AppKit.NSMenuItem.separatorItem(), 0)
                for item in reversed(tools):
                    native.insertItem_atIndex_(item, 0)
        if presentation == 'dropdown':
            context = False
        if min_width:
            native.setMinimumWidth_(float(min_width))
        if dark:
            native.setAppearance_(_ns_appearance(True))
        positioning_item = None
        if positioning_action is not None and positioning_action in flat:
            positioning_item = native.itemWithTag_(flat.index(positioning_action))
        primary_height = AppKit.NSScreen.screens()[0].frame().size.height
        import Foundation
        window_point = ns_window.convertPointFromScreen_(
            Foundation.NSMakePoint(global_pos.x(), primary_height - global_pos.y()))
        current = AppKit.NSApp.currentEvent()
    except Exception:
        logging.exception('Building the native menu failed; showing the Qt menu.')
        _menus_about_to_hide(shown_menus)
        return False, None
    _ACTIVE_NATIVE_MENU['menu'] = native
    _NATIVE_MENU_LAST_INFO.clear()
    _NATIVE_MENU_LAST_INFO.update({'context': bool(context), 'editable': bool(editable),
                                   'items': int(native.numberOfItems()), 'host': type(host).__name__})
    try:
        if context:
            right_kinds = (int(getattr(AppKit, 'NSEventTypeRightMouseDown', 3)), int(getattr(AppKit, 'NSEventTypeRightMouseUp', 4)))
            if current is not None and int(current.type()) in right_kinds and current.window() is ns_window:
                event = current
            else:
                event = AppKit.NSEvent.mouseEventWithType_location_modifierFlags_timestamp_windowNumber_context_eventNumber_clickCount_pressure_(
                    right_kinds[0], window_point, 0, Foundation.NSProcessInfo.processInfo().systemUptime(),
                    ns_window.windowNumber(), None, 0, 1, 1.0)
            # Context menu: macOS adds Ask Siri / AutoFill / Services by itself.
            AppKit.NSMenu.popUpContextMenu_withEvent_forView_(native, event, view)
        else:
            # Button drop-downs: a plain pop-up, without the context-menu extras.
            native.popUpMenuPositioningItem_atLocation_inView_(positioning_item, view.convertPoint_fromView_(window_point, None), view)
    finally:
        _ACTIVE_NATIVE_MENU.pop('menu', None)
        _reset_qt_mouse_buttons(view, host if context else None)
        _menus_about_to_hide(shown_menus)
    return True, _finish_native_menu(flat, target.chosen_tag)


def _reset_qt_mouse_buttons(view, context_host=None):
    """The system menu swallows the mouse-up of the click that opened it, so Qt still believed
    that button held: every later click then counted as part of that old press — it went to
    the widget that had been right-clicked, and buttons (tabs, trigger bands) did nothing.
    Qt's own native menus clear the state the same way once they close (QCocoaMenu).

    `context_host` (a widget of the window a right-click menu was shown in): Qt's widgets keep their
    own note of "the widget the button went down on", which the view's reset does not clear — the next
    right-click, wherever it was, then asked that first widget for its menu again (Raspberry
    2026-11-16: an app showed the group's menu). Hand Qt the mouse-up it never got."""
    try:
        if view is not None and view.respondsToSelector_('resetMouseButtons'):
            view.resetMouseButtons()
    except Exception:
        pass
    try:
        top = context_host.window() if context_host is not None else None
        handle = top.windowHandle() if top is not None else None
        if handle is not None:
            # through Qt's own event entry (what the system's mouse-up would have taken), so that
            # every layer — the application's pressed buttons and the widgets' note — is cleared
            from PyQt6.QtTest import QTest
            QTest.mouseRelease(handle, Qt.MouseButton.RightButton, Qt.KeyboardModifier.NoModifier,
                               top.mapFromGlobal(QCursor.pos()))
    except Exception:
        pass


def _qmenu_exec_dispatch(self, *args, **kwargs):
    if (isinstance(self, QMenu) and not kwargs and len(args) <= 2
            and (not args or isinstance(args[0], (QPoint, QPointF)))
            and self.property('broccoliNativeMenu')):
        pos = args[0].toPoint() if args and isinstance(args[0], QPointF) else (args[0] if args else QCursor.pos())
        handled, chosen = exec_native_qmenu(self, pos)
        if handled:
            return chosen
    return _QMENU_EXEC_QT(self, *args, **kwargs)


QMenu.exec = _qmenu_exec_dispatch
_ensure_native_menu_right_click_monitor()


_QDIALOG_EXEC_QT = QDialog.exec


def _qdialog_exec_return_focus(self, *args, **kwargs):
    """A modal dialog hands the window and the keyboard focus back when it closes. Without
    this the window it was opened over stayed inactive (Qt had no active window at all):
    the conversation page drew its selection grey instead of blue and the first click only
    woke the window up — after adding a comment the tab bar seemed not to respond."""
    owner = QApplication.activeWindow()
    focus = QApplication.focusWidget()
    try:
        return _QDIALOG_EXEC_QT(self, *args, **kwargs)
    finally:
        def give_back(owner=owner, focus=focus, dialog=self):
            try:
                if owner is None or owner is dialog or not owner.isVisible():
                    return
                if QApplication.activeWindow() not in (None, dialog):
                    return   # another window took over meanwhile: leave it alone
                owner.activateWindow()
                if focus is not None and focus.isVisible() and focus.window() is owner:
                    focus.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
            except RuntimeError:
                pass
        QTimer.singleShot(0, give_back)


QDialog.exec = _qdialog_exec_return_focus


_CONTEXT_MENU_EVENT = QEvent.Type.ContextMenu


def default_text_menu_owner(obj):
    """The text box whose right-click would show Qt's own built-in menu, or None. Qt builds
    that menu and pops it up inside C++, past menu.exec(), so it never became native. Text
    boxes with a menu of their own are left alone: a changed menu policy, or a class that
    handles contextMenuEvent itself."""
    if not isinstance(obj, QWidget):
        return None
    owner = obj
    if not isinstance(obj, (QLineEdit, QTextEdit, QPlainTextEdit)):
        # A multi-line box gets the event on its inner viewport.
        parent = obj.parentWidget()
        if not (isinstance(parent, (QTextEdit, QPlainTextEdit)) and parent.viewport() is obj):
            return None
        owner = parent
        if obj.contextMenuPolicy() != Qt.ContextMenuPolicy.DefaultContextMenu:
            return None
    if owner.contextMenuPolicy() != Qt.ContextMenuPolicy.DefaultContextMenu:
        return None
    for cls in type(owner).__mro__:
        if cls.__module__.startswith('PyQt6'):
            break
        if 'contextMenuEvent' in cls.__dict__:
            return None
    return owner


class NativeTextContextMenus(QObject):
    """右键任何没有自己菜单的文字框（设置页填写框、各处搜索框、弹窗里的输入框……）：
    在应用层拦下右键，拿 Qt 同一份标准菜单（撤销 … 全选）打上标记再 exec()，macOS 上就是
    系统菜单，写作工具、自动填充、服务、问 Siri 都由系统加。离屏或关掉原生菜单时是
    Broccoli 自己的样式菜单。"""

    def eventFilter(self, obj, event):
        if event.type() != _CONTEXT_MENU_EVENT:
            return False
        try:
            owner = default_text_menu_owner(obj)
            if owner is None:
                return False
            if isinstance(owner, QTextEdit):
                # 文档坐标（链接上右键时多出“复制链接地址”）= 显示区坐标 + 滚动距离。
                viewport_pos = event.pos() if obj is not owner else owner.viewport().mapFrom(owner, event.pos())
                menu = owner.createStandardContextMenu(viewport_pos + QPoint(
                    owner.horizontalScrollBar().value(), owner.verticalScrollBar().value()))
            else:
                menu = owner.createStandardContextMenu()
        except RuntimeError:
            return False
        if menu is None:
            return False
        style_broccoli_context_menu(menu)
        try:
            menu.exec(event.globalPos())
        finally:
            menu.deleteLater()
        event.accept()
        return True


_NATIVE_TEXT_CONTEXT_MENUS = NativeTextContextMenus(app)
app.installEventFilter(_NATIVE_TEXT_CONTEXT_MENUS)


def _remove_native_text_context_menus():
    # Before the interpreter tears down: Qt must not call into this Python filter while
    # the app object and the module globals are being destroyed.
    try:
        app.removeEventFilter(_NATIVE_TEXT_CONTEXT_MENUS)
    except Exception:
        pass


atexit.register(_remove_native_text_context_menus)


def use_native_web_context_menu(view):
    """A web view's own right-click menu (Back, Forward, Reload, Copy …) as a system menu.
    QtWebEngine builds that menu and pops it up itself, past menu.exec(); through the custom
    menu signal the same standard menu is exec()'d instead."""
    def show(pos, v=view):
        try:
            menu = v.createStandardContextMenu()
        except RuntimeError:
            return
        if menu is None:
            return
        style_broccoli_context_menu(menu)
        try:
            menu.exec(v.mapToGlobal(pos))
        finally:
            menu.deleteLater()

    view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    view.customContextMenuRequested.connect(show)


# ── 液态玻璃（macOS 26+ NSGlassEffectView，2026-10-19）────────────────────────
# 第一档：独立的小窗口（对话框、弹出列表、划词菜单、编辑权限面板）整窗垫玻璃；
# 对话标签、提示卡片、翻译按钮这些窗口里的小块用“子控件玻璃”。Qt 那边对应的
# paintEvent 看到 _liquid_glass_active 就不再画实心底色，由系统玻璃当底。
# 阴影：系统窗口阴影按窗口透明度算，玻璃只有边缘不透明，算出来是一道生硬的偏移
# 弧线；所以带玻璃的窗口关掉窗口阴影，在玻璃下面垫一层柔和阴影（中间挖空，
# 不压暗玻璃）。不可用（非 cocoa / 旧系统 / BROCCOLI_LIQUID_GLASS=0）时一切照旧。
LIQUID_GLASS_ENABLED = os.environ.get('BROCCOLI_LIQUID_GLASS', '1') != '0'


def liquid_glass_available() -> bool:
    if not (LIQUID_GLASS_ENABLED and sys.platform == 'darwin' and AppKit is not None and objc is not None):
        return False
    try:
        if QGuiApplication.platformName() != 'cocoa':
            return False
        return objc.lookUpClass('NSGlassEffectView') is not None
    except Exception:
        return False


def _ns_color(color):
    qcolor = QColor(color)
    return AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(
        qcolor.redF(), qcolor.greenF(), qcolor.blueF(), qcolor.alphaF())


def _ns_appearance(dark):
    if dark is None:
        return None
    name = getattr(AppKit, 'NSAppearanceNameDarkAqua' if dark else 'NSAppearanceNameAqua')
    return AppKit.NSAppearance.appearanceNamed_(name)


def _broccoli_own_ns_window(widget):
    """This top-level widget's OWN NSWindow, or None when its native view resolves to a
    window another Broccoli top-level also uses (the winId poison: a widget parented to
    the main window can report the MAIN NSWindow; changing that one kills the main
    window's clicks and draws black corners). Never touch a window we are unsure of."""
    try:
        if widget is None or not widget.isWindow():
            return None
        window = objc.objc_object(c_void_p=int(widget.winId())).window()
        if window is None:
            return None
        for other in QApplication.topLevelWidgets():
            if other is widget or not other.testAttribute(Qt.WidgetAttribute.WA_WState_Created):
                continue
            try:
                if objc.objc_object(c_void_p=int(other.winId())).window() is window:
                    return None
            except Exception:
                continue
        return window
    except Exception:
        return None


def _set_glass_tint(glass, tint):
    """Tint a glass view. Tinted glass uses the "clear" style: the regular style drops
    its tint (turns grey) whenever its window is not the active one — and the shelf and
    toast windows never are."""
    glass.setTintColor_(_ns_color(tint) if tint is not None else None)
    if glass.respondsToSelector_('setStyle:'):
        glass.setStyle_(1 if tint is not None else 0)


# System glass looks beyond the public regular / clear styles (2026-10-28). The glass view
# numbers them in the order of the system's own list (regular, identity, clear, dock,
# appIcons, widgets, text, avplayer, facetime, controlCenter, …); the public clear style
# reads back as 2, which is how we check that numbering before trusting one. setStyle_
# resets the look, so a glass with a look only ever changes its tint afterwards.
GLASS_LOOK_CONTROL_CENTER = 'control_center'
_GLASS_LOOK_NUMBERS = {GLASS_LOOK_CONTROL_CENTER: 9}
_GLASS_LOOK_NUMBERING = []   # [bool] once checked


def _glass_look_numbering_ok() -> bool:
    if not _GLASS_LOOK_NUMBERING:
        ok = False
        try:
            probe = objc.lookUpClass('NSGlassEffectView').alloc().initWithFrame_(AppKit.NSMakeRect(0, 0, 1, 1))
            if probe.respondsToSelector_('set_variant:') and probe.respondsToSelector_('_variant'):
                probe.setStyle_(1)
                ok = int(probe._variant()) == 2
        except Exception:
            ok = False
        _GLASS_LOOK_NUMBERING.append(ok)
    return _GLASS_LOOK_NUMBERING[0]


def _set_glass_look(glass, look):
    """Give a glass view a system look by name; where this macOS numbers its looks
    differently (or has none), the public clear style, untinted, stands in."""
    if look in _GLASS_LOOK_NUMBERS and _glass_look_numbering_ok():
        glass.set_variant_(_GLASS_LOOK_NUMBERS[look])
    elif glass.respondsToSelector_('setStyle:'):
        glass.setStyle_(1)


# System glass draws ordinary (continuous) corners, while Broccoli's own panels use the
# smooth superellipse path whose control radius is ~2.27x larger for the same look (see
# "Smooth corner radius tiers" near smooth_round_rect_path). Pass the glass the
# mechanical radius of the surface's tier — and second/third-level surfaces one tier
# lower, as their glass versions read larger than the painted ones.
GLASS_CORNER_TIERS = ((59, 26), (45, 20), (36, 16), (20, 9), (18, 8), (14, 6), (9, 4))   # (smooth, mechanical)


def glass_corner_radius(radius, smooth=True, lower=0) -> float:
    column = 0 if smooth else 1
    index = min(range(len(GLASS_CORNER_TIERS)), key=lambda i: abs(GLASS_CORNER_TIERS[i][column] - float(radius)))
    return float(GLASS_CORNER_TIERS[min(len(GLASS_CORNER_TIERS) - 1, index + max(0, int(lower)))][1])


def _new_glass_view(frame, radius, tint=None, dark=None):
    glass = objc.lookUpClass('NSGlassEffectView').alloc().initWithFrame_(frame)
    glass.setCornerRadius_(float(radius))
    if tint is not None:
        _set_glass_tint(glass, tint)
    appearance = _ns_appearance(dark)
    if appearance is not None:
        glass.setAppearance_(appearance)
    return glass


_FITTED_SHADOW_CACHE = {}


def _fitted_shadow_image(radius: float, pad: float, color: QColor, blur: float, dy: float, scale: float = 2.0):
    """A 9-slice picture of a soft shadow around a rounded card that fades to exactly nothing at the
    edge of its space (2026-11-07, Ryan: "特别不自然的切线"). A layer shadow is a Gaussian whose tail
    reaches past any margin, so the margin's edge cut it off in a straight line around every glass
    card and dialog. Here: the blurred card (Gaussian edge, blur ≈ the old shadow radius, moved down
    by dy) times a window that falls smoothly to 0 at `pad` from the card; nothing under the card
    itself (the glass is see-through). Returns (CGImage, size in points) or (None, 0)."""
    radius, pad, blur, dy = (round(float(radius), 1), round(float(pad), 1), max(0.5, float(blur)), float(dy))
    key = (radius, pad, QColor(color).rgba(), round(blur, 1), round(dy, 1), scale)
    cached = _FITTED_SHADOW_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        import math
        from PyQt6.QtCore import QBuffer, QIODevice
        size = 2.0 * pad + 2.0 * radius + 2.0
        pixels = max(1, int(round(size * scale)))
        sigma = max(0.5, blur * 0.5)
        color = QColor(color)
        base_alpha = color.alphaF()
        reach = max(1.0, pad - abs(dy))
        half = size / 2.0 - pad                       # the card's half size (a square: 9-slice)
        r = max(0.0, min(radius, half))
        data = bytearray(pixels * pixels * 4)

        def rounded_distance(x, y, cy):
            qx = abs(x - size / 2.0) - (half - r)
            qy = abs(y - cy) - (half - r)
            outside = math.hypot(max(qx, 0.0), max(qy, 0.0))
            return outside + min(max(qx, qy), 0.0) - r

        for py in range(pixels):
            y = (py + 0.5) / scale
            for px in range(pixels):
                x = (px + 0.5) / scale
                card = rounded_distance(x, y, size / 2.0)
                if card <= 0.0 or card >= reach:
                    continue
                source = rounded_distance(x, y, size / 2.0 + dy)
                coverage = 0.5 * math.erfc(source / (sigma * math.sqrt(2.0)))
                window = (1.0 - (card / reach) ** 2) ** 2
                alpha = base_alpha * coverage * window
                if alpha <= 0.0:
                    continue
                a = min(255, int(round(alpha * 255)))
                index = (py * pixels + px) * 4
                data[index] = int(color.blue() * a / 255)
                data[index + 1] = int(color.green() * a / 255)
                data[index + 2] = int(color.red() * a / 255)
                data[index + 3] = a
        image = QImage(bytes(data), pixels, pixels, pixels * 4, QImage.Format.Format_ARGB32_Premultiplied)
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, 'PNG')
        payload = bytes(buffer.data())
        ns_data = AppKit.NSData.dataWithBytes_length_(payload, len(payload))
        rep_ = AppKit.NSBitmapImageRep.imageRepWithData_(ns_data)
        result = (rep_.CGImage(), size) if rep_ is not None else (None, 0)
    except Exception:
        logging.exception('Drawing a fitted soft shadow failed.')
        result = (None, 0)
    _FITTED_SHADOW_CACHE[key] = result
    return result


class _GlassSoftShadow:
    """A soft drop shadow drawn by a plain layer-backed NSView placed just below a glass
    view: shadowPath = the glass's rounded shape, and a mask that cuts that shape out so
    the shadow never darkens the glass itself. `blur` is the CALayer shadow radius,
    `dy` > 0 moves the shadow down. Raises when QuartzCore is not available."""

    def __init__(self, superview, below, color=QColor(0, 0, 0, 52), blur=12.0, dy=4.0, pad=None, fit=True):
        import Quartz
        self._quartz = Quartz
        self._pad = float(pad if pad is not None else blur * 2.0 + abs(dy) + 4.0)
        self._color = QColor(color)
        self._blur = float(blur)
        self._dy = float(dy)
        self._key = None
        # fit: a picture that fades to nothing at the edge of its space (no cut line); otherwise a
        # layer shadow (kept for the collapsed button's body, whose shadow changes every frame)
        self._fit = bool(fit)
        self._frame = None
        self._radius = 0.0
        self.view = AppKit.NSView.alloc().initWithFrame_(AppKit.NSMakeRect(0, 0, 1, 1))
        self.view.setWantsLayer_(True)
        self._mask = None
        if not self._fit:
            self._mask = Quartz.CAShapeLayer.layer()
            self._mask.setFillRule_(Quartz.kCAFillRuleEvenOdd)
            self.view.layer().setMask_(self._mask)
        superview.addSubview_positioned_relativeTo_(self.view, int(getattr(AppKit, 'NSWindowBelow', -1)), below)
        self._apply_style()

    def _apply_fitted_contents(self):
        if self._frame is None:
            return
        Quartz = self._quartz
        layer = self.view.layer()
        # the picture's "down" is the view's down: flip dy when the layer draws upside down
        flipped = bool(layer.contentsAreFlipped()) if hasattr(layer, 'contentsAreFlipped') else False
        image, size = _fitted_shadow_image(self._radius, self._pad, self._color, self._blur,
                                           -self._dy if flipped else self._dy)
        if image is None or not size:
            layer.setContents_(None)
            return
        edge = (self._pad + self._radius) / size
        layer.setContents_(image)
        layer.setContentsScale_(2.0)
        layer.setContentsCenter_(Quartz.CGRectMake(edge, edge, 2.0 / size, 2.0 / size))

    def _apply_style(self):
        layer = self.view.layer()
        if self._fit:
            layer.setShadowOpacity_(0.0)
            self._apply_fitted_contents()
            return
        opaque = QColor(self._color)
        opaque.setAlpha(255)
        layer.setShadowColor_(_ns_color(opaque).CGColor())
        layer.setShadowOpacity_(float(self._color.alphaF()))
        layer.setShadowRadius_(self._blur)
        # Layer y points up unless the layer is flipped (it follows its superview).
        down = self._dy if layer.isGeometryFlipped() or (self.view.superview() is not None
                                                         and self.view.superview().isFlipped()) else -self._dy
        layer.setShadowOffset_((0.0, down))

    def set_style(self, color=None, blur=None, dy=None):
        key = (QColor(color).rgba() if color is not None else None, blur, dy)
        if key == self._key:
            return
        self._key = key
        if color is not None:
            self._color = QColor(color)
        if blur is not None:
            self._blur = float(blur)
        if dy is not None:
            self._dy = float(dy)
        self._apply_style()

    def update(self, glass_frame, radius):
        Quartz = self._quartz
        pad = self._pad
        frame = AppKit.NSInsetRect(glass_frame, -pad, -pad)
        self.view.setFrame_(frame)
        width, height = float(glass_frame.size.width), float(glass_frame.size.height)
        r = max(0.0, min(float(radius), width / 2.0, height / 2.0))
        if self._fit:
            key = (round(r, 1), round(width, 1), round(height, 1))
            if key != self._frame:
                self._frame, self._radius = key, r
                self._apply_fitted_contents()
            return
        shape = Quartz.CGPathCreateWithRoundedRect(Quartz.CGRectMake(pad, pad, width, height), r, r, None)
        layer = self.view.layer()
        layer.setShadowPath_(shape)
        cutout = Quartz.CGPathCreateMutable()
        Quartz.CGPathAddRect(cutout, None, Quartz.CGRectMake(0, 0, frame.size.width, frame.size.height))
        Quartz.CGPathAddPath(cutout, None, shape)
        self._mask.setFrame_(Quartz.CGRectMake(0, 0, frame.size.width, frame.size.height))
        self._mask.setPath_(cutout)

    def set_hidden(self, hidden):
        self.view.setHidden_(bool(hidden))

    def set_opacity(self, value):
        self.view.setAlphaValue_(max(0.0, min(1.0, float(value))))

    def restack(self, below):
        superview = below.superview()
        if superview is not None:
            superview.addSubview_positioned_relativeTo_(self.view, int(getattr(AppKit, 'NSWindowBelow', -1)), below)

    def remove(self):
        self.view.removeFromSuperview()


def _soft_shadow_or_none(superview, below, **kwargs):
    try:
        return _GlassSoftShadow(superview, below, **kwargs)
    except Exception:
        logging.exception('Soft shadow under Liquid Glass failed; continuing without it.')
        return None


class _WindowGlassFollower(QObject):
    """Keeps a window-level glass's soft shadow matching the glass after resizes."""

    def __init__(self, widget, glass, shadow, radius):
        super().__init__(widget)
        self._glass, self._shadow, self._radius = glass, shadow, float(radius)
        widget.installEventFilter(self)
        widget.destroyed.connect(lambda *_args, s=shadow: s.remove())

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            try:
                self._shadow.update(self._glass.frame(), self._radius)
            except Exception:
                pass
        return False


# ── Glass that keeps the active look ────────────────────────────────────────────────
# AppKit draws glass dimmer and greyer in a window it treats as inactive: a pop-up list
# (never key) always, the main window whenever another app is in front. The system menu
# window answers the private _hasActiveAppearanceIgnoringKeyFocus with YES and keeps its
# bright glass. Broccoli adds that method ONCE to Qt's window classes (QNSWindow,
# QNSPanel): YES for the windows registered here (the main window with its glass controls,
# the pop-up lists), AppKit's own answer for every other window. Window objects are never
# changed (switching one window's class breaks the system's key-value observation of a
# window that is already observed — the main window is from the start). Undocumented
# hook: if a future macOS drops it, these windows get the ordinary glass again.
_ACTIVE_GLASS_WINDOWS = set()   # NSWindow pointers
_ACTIVE_GLASS_HOOK = {}


def _install_active_glass_hook() -> bool:
    if _ACTIVE_GLASS_HOOK:
        return bool(_ACTIVE_GLASS_HOOK.get('ok'))
    _ACTIVE_GLASS_HOOK['ok'] = False
    try:
        import ctypes
        import ctypes.util
        lib = ctypes.CDLL(ctypes.util.find_library('objc') or '/usr/lib/libobjc.dylib')
        for name, restype, argtypes in (
                ('objc_getClass', ctypes.c_void_p, [ctypes.c_char_p]),
                ('class_getSuperclass', ctypes.c_void_p, [ctypes.c_void_p]),
                ('sel_registerName', ctypes.c_void_p, [ctypes.c_char_p]),
                ('class_getInstanceMethod', ctypes.c_void_p, [ctypes.c_void_p, ctypes.c_void_p]),
                ('method_getImplementation', ctypes.c_void_p, [ctypes.c_void_p]),
                ('class_addMethod', ctypes.c_bool, [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p])):
            getattr(lib, name).restype = restype
            getattr(lib, name).argtypes = argtypes
        answer_t = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)   # BOOL (id, SEL)
        selector = lib.sel_registerName(b'_hasActiveAppearanceIgnoringKeyFocus')
        callbacks = []
        for class_name in (b'QNSWindow', b'QNSPanel'):
            cls = lib.objc_getClass(class_name)
            inherited = lib.class_getInstanceMethod(lib.class_getSuperclass(cls), selector) if cls else None
            if not inherited:
                continue   # no such Qt class, or AppKit no longer has the hook
            original = answer_t(lib.method_getImplementation(inherited))

            def answer(window, sel, _original=original):
                return True if window in _ACTIVE_GLASS_WINDOWS else bool(_original(window, sel))
            callback = answer_t(answer)
            if lib.class_addMethod(cls, selector, ctypes.cast(callback, ctypes.c_void_p), b'B@:'):
                callbacks.append((callback, original))   # kept alive for the process lifetime
        _ACTIVE_GLASS_HOOK.update(ok=bool(callbacks), callbacks=callbacks)
    except Exception:
        logging.exception('Installing the active-glass hook failed.')
    return bool(_ACTIVE_GLASS_HOOK.get('ok'))


def _want_active_glass(window, owner=None) -> bool:
    """`window` (an NSWindow) draws its glass with the active look from now on; register it
    before its glass views are created. `owner` (a QWidget): forget the window with it."""
    if window is None or not _install_active_glass_hook():
        return False
    try:
        pointer = int(objc.pyobjc_id(window))
    except Exception:
        return False
    if pointer not in _ACTIVE_GLASS_WINDOWS:
        _ACTIVE_GLASS_WINDOWS.add(pointer)
        if owner is not None:
            owner.destroyed.connect(lambda *_args, p=pointer: _ACTIVE_GLASS_WINDOWS.discard(p))
    return True


def apply_window_liquid_glass(widget, radius, inset=0.0, dark=None, tint=None, keep_shadow=False, menu_look=False) -> bool:
    """Put system Liquid Glass under the whole content of a frameless top-level window.
    `inset` = the transparent margin around the painted card; `radius` its corner. The
    window's own shadow is switched off; with a margin of 6+ points a soft shadow is
    drawn in it instead."""
    if not liquid_glass_available():
        return False
    glass = getattr(widget, '_broccoli_window_glass', None)
    if glass is not None and glass.superview() is not None:
        appearance = _ns_appearance(dark)
        if appearance is not None:
            glass.setAppearance_(appearance)
        return True
    window = _broccoli_own_ns_window(widget)
    if window is None:
        return False
    try:
        root = objc.objc_object(c_void_p=int(widget.winId()))
        container = root.superview()
        if container is None:
            return False
        if menu_look:   # before the glass exists, so it starts out with the active look
            _want_active_glass(window, widget)
            if window.respondsToSelector_('_setCornerRadius:'):
                # The window's own corner radius, like the menu window's (12): the system
                # shadow then follows the rounded card instead of the square window frame
                # (which showed as a thin square outline at the corners).
                window._setCornerRadius_(float(radius))
        glass = _new_glass_view(AppKit.NSInsetRect(root.frame(), float(inset), float(inset)), radius, tint=tint, dark=dark)
        glass.setAutoresizingMask_(int(getattr(AppKit, 'NSViewWidthSizable', 2)) | int(getattr(AppKit, 'NSViewHeightSizable', 16)))
        window.setOpaque_(False)
        window.setBackgroundColor_(AppKit.NSColor.clearColor())
        container.addSubview_positioned_relativeTo_(glass, int(getattr(AppKit, 'NSWindowBelow', -1)), root)
        # A tinted glass card filling the window gives the system shadow a solid shape to
        # follow (lists): keep it. Clear glass would turn it into a hard offset line.
        window.setHasShadow_(bool(keep_shadow))
        if keep_shadow:
            QTimer.singleShot(80, lambda w=window: w.invalidateShadow())
        if float(inset) >= 6.0:
            # The shadow must have faded out before the window edge (inset points away),
            # or it ends in a hard straight line there.
            dy = min(2.5, float(inset) * 0.15)
            blur = max(2.0, (float(inset) - dy - 1.0) / 2.0)
            shadow = _soft_shadow_or_none(container, glass, color=QColor(0, 0, 0, 62), blur=blur,
                                          dy=dy, pad=float(inset))
            if shadow is not None:
                shadow.update(glass.frame(), radius)
                widget._broccoli_window_glass_shadow = shadow
                _WindowGlassFollower(widget, glass, shadow, radius)
    except Exception:
        logging.exception('Applying Liquid Glass to %s failed.', type(widget).__name__)
        return False
    widget._broccoli_window_glass = glass
    widget._liquid_glass_active = True
    widget.update()
    return True


if AppKit is not None and objc is not None:
    class BroccoliGlassContainerView(AppKit.NSView):
        """Holds a window's child glass: top-left origin like Qt, never takes the mouse."""

        def isFlipped(self):
            return True

        def hitTest_(self, point):
            return None
else:
    BroccoliGlassContainerView = None


class _WindowGlassLayer:
    """One per window: a container view placed just BELOW the window's Qt content view.
    Child glass and soft shadows live in it, at their widget's rectangle. The widgets
    themselves stay ordinary (non-native) Qt widgets: focus, mouse routing, hover and Qt
    graphics effects behave exactly as without glass. (Turning them into native child
    views — the first attempt — moved Qt's focus window onto the shelf for good after a
    tag click, and hover pop-ups in the main window stopped appearing.)
    `clip` mirrors the window's Qt mask (the glass sits outside the masked content view);
    `fade` = (top, bottom) points over which the glass fades out at the window edges."""

    def __init__(self, top):
        self.top = top
        self.view = None
        self._win_id = None
        current_mask = top.mask()
        self._clip = QRegion(current_mask) if not current_mask.isEmpty() else None
        edge_fade = getattr(top, '_edge_fade', None)   # a window that fades its content (the shelf)
        self._fade = (float(edge_fade[0]), float(edge_fade[1])) if isinstance(edge_fade, tuple) and len(edge_fade) >= 2 else (0.0, 0.0)

    def ensure(self) -> bool:
        try:
            win_id = int(self.top.winId())
        except RuntimeError:
            return False
        if self.view is not None and win_id == self._win_id and self.view.superview() is not None:
            return True
        if BroccoliGlassContainerView is None or _broccoli_own_ns_window(self.top) is None:
            return False
        root = objc.objc_object(c_void_p=win_id)
        frame_view = root.superview()
        if frame_view is None:
            return False
        old = self.view
        view = BroccoliGlassContainerView.alloc().initWithFrame_(root.frame())
        view.setWantsLayer_(True)
        view.setAutoresizingMask_(int(getattr(AppKit, 'NSViewWidthSizable', 2)) | int(getattr(AppKit, 'NSViewHeightSizable', 16)))
        frame_view.addSubview_positioned_relativeTo_(view, int(getattr(AppKit, 'NSWindowBelow', -1)), root)
        if old is not None:   # the window was recreated: carry the glass views over
            for sub in list(old.subviews() or []):
                view.addSubview_(sub)
            old.removeFromSuperview()
        self.view = view
        self._win_id = win_id
        self._apply_mask()
        return True

    def set_clip(self, region):
        self._clip = QRegion(region) if region is not None and not region.isEmpty() else None
        self._apply_mask()

    def set_fade(self, top_px=0.0, bottom_px=0.0):
        fade = (max(0.0, float(top_px)), max(0.0, float(bottom_px)))
        if fade != self._fade:
            self._fade = fade
            self._apply_mask()

    def _apply_mask(self):
        if self.view is None:
            return
        try:
            import Quartz
            layer = self.view.layer()
            top_fade, bottom_fade = self._fade
            if self._clip is None and not top_fade and not bottom_fade:
                layer.setMask_(None)
                return
            bounds = layer.bounds()
            height = max(1.0, float(bounds.size.height))
            flipped = bool(layer.isGeometryFlipped())

            shape = None
            if self._clip is not None:
                region_path = QPainterPath()   # (QRegion's rectangles are not iterable from PyQt6)
                region_path.addRegion(self._clip)
                path = Quartz.CGPathCreateMutable()
                for index in range(region_path.elementCount()):
                    element = region_path.elementAt(index)
                    x = float(element.x)
                    y = float(element.y) if flipped else height - float(element.y)
                    if element.isMoveTo():
                        if index:
                            Quartz.CGPathCloseSubpath(path)
                        Quartz.CGPathMoveToPoint(path, None, x, y)
                    else:
                        Quartz.CGPathAddLineToPoint(path, None, x, y)
                if region_path.elementCount():
                    Quartz.CGPathCloseSubpath(path)
                shape = Quartz.CAShapeLayer.layer()
                shape.setFrame_(bounds)
                shape.setPath_(path)
            if top_fade or bottom_fade:
                gradient = Quartz.CAGradientLayer.layer()
                gradient.setFrame_(bounds)
                solid = AppKit.NSColor.blackColor().CGColor()
                clear = AppKit.NSColor.clearColor().CGColor()
                gradient.setColors_([clear if top_fade else solid, solid, solid, clear if bottom_fade else solid])
                gradient.setLocations_([0.0, min(0.5, top_fade / height), max(0.5, 1.0 - bottom_fade / height), 1.0])
                gradient.setStartPoint_((0.5, 0.0 if flipped else 1.0))
                gradient.setEndPoint_((0.5, 1.0 if flipped else 0.0))
                if shape is not None:
                    gradient.setMask_(shape)
                layer.setMask_(gradient)
            else:
                layer.setMask_(shape)
        except Exception:
            logging.exception('Updating the glass clip failed.')


_WINDOW_GLASS_LAYERS = {}


def _window_glass_layer(top, create=True):
    if top is None:
        return None
    key = id(top)
    layer = _WINDOW_GLASS_LAYERS.get(key)
    if layer is not None and layer.top is not top:
        layer = None
    if layer is None:
        if not create:
            return None
        layer = _WindowGlassLayer(top)
        _WINDOW_GLASS_LAYERS[key] = layer
        top.destroyed.connect(lambda *_args, k=key: _WINDOW_GLASS_LAYERS.pop(k, None))
    return layer if layer.ensure() else None


def set_window_glass_clip(top, region):
    """Keep a window's child glass inside its Qt mask (call right after setMask/clearMask)."""
    layer = _window_glass_layer(top, create=False) if liquid_glass_available() else None
    if layer is not None:
        layer.set_clip(region)


def set_window_glass_fade(top, top_px=0.0, bottom_px=0.0):
    layer = _window_glass_layer(top, create=False) if liquid_glass_available() else None
    if layer is not None:
        layer.set_fade(top_px, bottom_px)


class ChildLiquidGlass(QObject):
    """An NSGlassEffectView (and/or a soft shadow) under a child widget, in its window's
    _WindowGlassLayer: same rectangle (minus `inset`), same visibility, following moves /
    resizes / animations of the widget and its parents, stacked like the widgets (a
    raised widget brings its glass up); removed together with the widget. The widget is
    NOT made native. `shadow` = dict(color=, blur=, dy=, pad=); `glass=False` keeps only
    the shadow (for a plain painted panel next to glass widgets)."""

    def __init__(self, widget, radius, inset=0.0, tint=None, dark=None, radius_for=None, shadow=None, glass=True):
        super().__init__(widget)
        self._widget = widget
        self._top = widget.window()
        self._layer = _window_glass_layer(self._top)
        if self._layer is None or self._top is widget:
            raise RuntimeError('no glass layer for this window')
        self._inset = float(inset)
        self._radius = float(radius)
        self._radius_for = radius_for
        self._opacity = 1.0
        self.glass = None
        self.shadow = None
        container = self._layer.view
        if glass:
            self.glass = _new_glass_view(AppKit.NSMakeRect(0, 0, 1, 1), self._current_radius(), tint, dark)
            container.addSubview_(self.glass)
        if shadow is not None:
            self.shadow = _soft_shadow_or_none(container, self.glass, **shadow)
        glass_view, shadow_helper = self.glass, self.shadow
        widget.destroyed.connect(lambda *_args, g=glass_view, s=shadow_helper: (
            g.removeFromSuperview() if g is not None else None, s.remove() if s is not None else None))
        # The widget's rectangle in the window changes when it or any parent moves.
        self._watched = [widget]
        parent = widget.parentWidget()
        while parent is not None and parent is not self._top:
            self._watched.append(parent)
            parent = parent.parentWidget()
        self._watched.append(self._top)
        for watched in self._watched:
            watched.installEventFilter(self)
        self.sync()

    def _current_radius(self):
        return float(self._radius_for()) if self._radius_for is not None else self._radius

    def _frame(self):
        widget = self._widget
        origin = widget.mapTo(self._top, QPoint(0, 0))
        width, height = float(widget.width()), float(widget.height())
        inset = max(0.0, min(self._inset, width / 2.0, height / 2.0))   # buttons animate down to 2×2
        return AppKit.NSMakeRect(origin.x() + inset, origin.y() + inset, width - 2 * inset, height - 2 * inset)

    def eventFilter(self, obj, event):
        kind = event.type()
        if kind in (QEvent.Type.Move, QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.Hide):
            self.sync()
        elif kind == QEvent.Type.ZOrderChange and obj is self._widget:
            self.sync(reorder=True)
        return False

    def _views(self):
        return [view for view in (self.shadow.view if self.shadow is not None else None, self.glass) if view is not None]

    def sync(self, reorder=False):
        try:
            if not self._layer.ensure():
                return
            container = self._layer.view
            views = self._views()
            for view in views:
                if view.superview() is not container:
                    container.addSubview_(view)
                    reorder = True
            visible = self._widget.isVisible()
            for view in views:
                view.setHidden_(not visible)
            if not visible:
                return
            frame = self._frame()
            radius = self._current_radius()
            if self.glass is not None:
                self.glass.setFrame_(frame)
                self.glass.setCornerRadius_(radius)
            if self.shadow is not None:
                self.shadow.update(frame, radius)
            if reorder:   # shadow then glass on top of the other widgets' glass
                for view in views:
                    container.addSubview_positioned_relativeTo_(view, int(getattr(AppKit, 'NSWindowAbove', 1)), None)
        except Exception:
            pass

    def set_tint(self, color):
        if self.glass is not None:
            _set_glass_tint(self.glass, color)

    def set_shadow_style(self, color=None, blur=None, dy=None):
        if self.shadow is not None:
            self.shadow.set_style(color, blur, dy)

    def set_opacity(self, value):
        value = max(0.0, min(1.0, float(value)))
        if value == self._opacity:
            return
        self._opacity = value
        for view in self._views():
            view.setAlphaValue_(value)


def attach_child_liquid_glass(widget, radius, inset=0.0, tint=None, dark=None, radius_for=None, shadow=None, glass=True,
                              keep_window_shadow=False):
    """ChildLiquidGlass for `widget`, or None when glass is unavailable / failed (the
    widget then keeps painting its own background). The host window's own shadow is
    switched off (around nearly clear glass it outlines the edge as a hard offset line)
    unless `keep_window_shadow` (a widget filling its window, with a solid tint)."""
    if not liquid_glass_available():
        return None
    existing = getattr(widget, '_broccoli_child_glass', None)
    if existing is not None:
        return existing
    try:
        helper = ChildLiquidGlass(widget, radius, inset=inset, tint=tint, dark=dark, radius_for=radius_for,
                                  shadow=shadow, glass=glass)
    except Exception:
        logging.exception('Child Liquid Glass for %s failed.', type(widget).__name__)
        return None
    widget._broccoli_child_glass = helper
    if glass:
        widget._liquid_glass_active = True
    host = None if keep_window_shadow else _broccoli_own_ns_window(widget.window())
    if host is not None:
        host.setHasShadow_(False)
    widget.update()
    return helper


# ── 主窗口里的液态玻璃控件（胶囊按钮、顶部胶囊导航栏）────────────────────────────
# 主窗口的面板是 Qt 画的不透明底色，系统玻璃垫不到控件下面。做法：玻璃盖在 Qt 内容
# 上面（窗口内容视图的子视图，所以折射的是它下面的界面），控件自己的文字/图标由 Qt
# 画成图片放进玻璃里；玻璃不接收鼠标（hitTest 返回 nil），点击照常落到下面的普通
# Qt 控件，没有任何原生子控件（不会再出“焦点卡住”的问题）。控件被侧滑面板 / 遮罩 /
# 弹出块盖住时临时退回 Qt 自己画、玻璃隐藏，层级始终正确。
# BROCCOLI_INWINDOW_GLASS=0 关闭。
INWINDOW_GLASS_ENABLED = os.environ.get('BROCCOLI_INWINDOW_GLASS', '1') != '0'
try:
    if AppKit is not None and objc is not None and objc.lookUpClass('NSGlassEffectView') is not None:
        class BroccoliPassThroughGlassView(objc.lookUpClass('NSGlassEffectView')):
            """Glass that lets every mouse event through to the Qt view underneath."""

            def hitTest_(self, point):
                return None
    else:
        BroccoliPassThroughGlassView = None
except Exception:
    BroccoliPassThroughGlassView = None

_INWINDOW_GLASS_BY_WINDOW = {}
_GLASS_OCCLUDERS = weakref.WeakSet()
_GLASS_RENDER_STACK = []   # widgets whose glass image is being rendered right now


def inwindow_glass_available() -> bool:
    return bool(INWINDOW_GLASS_ENABLED and BroccoliPassThroughGlassView is not None and liquid_glass_available())


class _GlassOccluderWatch(QObject):
    """On an overlay (scrim, pop-up): re-check the in-window glass of its window when it
    appears / disappears / moves / is raised or lowered."""

    def eventFilter(self, obj, event):
        kind = event.type()
        if kind in (QEvent.Type.Show, QEvent.Type.Hide, QEvent.Type.ZOrderChange):
            resync_inwindow_glass(obj.window())          # now: no frame with glass over it
        elif kind in (QEvent.Type.Move, QEvent.Type.Resize):
            QTimer.singleShot(0, lambda w=obj: resync_inwindow_glass(w.window()))
        return False


_GLASS_OCCLUDER_WATCH = None


def register_glass_occluder(widget):
    """Overlays that can cover in-window glass controls (scrims, pop-ups, sliding panels).
    An overlay whose frame is partly transparent can say what it really covers with
    `_glass_occluding_rect()` (a QRect in its window's coordinates)."""
    global _GLASS_OCCLUDER_WATCH
    if widget is None:
        return
    _GLASS_OCCLUDERS.add(widget)
    if _GLASS_OCCLUDER_WATCH is None:
        _GLASS_OCCLUDER_WATCH = _GlassOccluderWatch()
    widget.installEventFilter(_GLASS_OCCLUDER_WATCH)


def _glass_stacked_above(upper, lower) -> bool:
    """Whether `upper` is painted over `lower` (same window). Compares the two branches
    under their closest common ancestor: a later child is stacked higher (raise_() moves a
    widget to the end of its parent's children). Unknown → True (treat it as covering)."""
    lower_chain = []
    node = lower
    while node is not None:
        lower_chain.append(node)
        node = node.parentWidget()
    upper_branch, node = upper, upper.parentWidget()
    while node is not None and not any(node is item for item in lower_chain):
        upper_branch, node = node, node.parentWidget()
    if node is None:
        return True
    depth = next(i for i, item in enumerate(lower_chain) if item is node)
    if depth == 0:
        return True
    lower_branch = lower_chain[depth - 1]
    siblings = [child for child in node.children() if isinstance(child, QWidget)]
    try:
        return siblings.index(upper_branch) > siblings.index(lower_branch)
    except ValueError:
        return True


def _inwindow_glass_occluded(widget, top) -> bool:
    """An overlay over the control: Qt cannot paint over system glass, so the control falls
    back to Qt paint. Only an overlay stacked ABOVE it counts: the Settings scrim lies under
    the Settings panel, whose tab bar keeps its glass (it used to count, by rectangle alone)."""
    try:
        rect = QRect(widget.mapTo(top, QPoint(0, 0)), widget.size())
        for occluder in list(_GLASS_OCCLUDERS):
            try:
                if occluder.window() is not top or not occluder.isVisible():
                    continue
                if occluder is widget or occluder.isAncestorOf(widget) or widget.isAncestorOf(occluder):
                    continue
                area = getattr(occluder, '_glass_occluding_rect', None)
                covered = area() if callable(area) else QRect(occluder.mapTo(top, QPoint(0, 0)), occluder.size())
                if covered.intersects(rect) and _glass_stacked_above(occluder, widget):
                    return True
            except RuntimeError:
                continue
    except RuntimeError:
        return True
    return False


def glass_visible_part(widget) -> QRect:
    """The part of a clipped widget (a tray in its wrapper, a card sliding in its dock) that
    its ancestors let show, in widget coordinates. Qt's visible region also counts a drop
    shadow's margin around it; that margin is not the widget."""
    return widget.visibleRegion().boundingRect().intersected(widget.rect())


def resync_inwindow_glass(top):
    for helper in list(_INWINDOW_GLASS_BY_WINDOW.get(id(top), [])):
        helper.sync()


def restack_window_glass(top):
    """The glass views of one window back in Qt's paint order: a parent's glass under its
    children's, a later sibling's over an earlier one's (children() is the stacking order).
    When Qt rebuilds a window's native view (the first web view in it does that — the
    editor's diagram renderer), every glass moves over on its own and lands on top in
    whatever order it happens to move: the file bar's glass then covered its "+" disc,
    which stayed washed out for good."""
    helpers = {id(helper._widget): helper for helper in list(_INWINDOW_GLASS_BY_WINDOW.get(id(top), []))}
    if not helpers:
        return
    order = []

    def walk(widget):
        helper = helpers.get(id(widget))
        if helper is not None:
            order.append(helper)
        for child in widget.children():
            if isinstance(child, QWidget) and not child.isWindow():
                walk(child)

    try:
        walk(top)
    except RuntimeError:
        return
    above = int(getattr(AppKit, 'NSWindowAbove', 1)) if AppKit is not None else 1
    for helper in order:
        try:
            view = helper.glass.superview()
            if view is not None:
                view.addSubview_positioned_relativeTo_(helper.glass, above, None)
        except Exception:
            continue


def _schedule_restack_window_glass(top):
    """Once per batch: all of a rebuilt window's glass has moved over by then."""
    if getattr(top, '_broccoli_glass_restack_pending', False):
        return
    top._broccoli_glass_restack_pending = True

    def run(t=top):
        try:
            t._broccoli_glass_restack_pending = False
            restack_window_glass(t)
        except RuntimeError:
            pass
    QTimer.singleShot(0, run)


_GLASS_IMAGE_DIRECT = {'on': True}


def _qimage_to_layer_contents(image, ratio):
    """A Qt image as layer contents without a PNG round trip: its pixels as a CGImage. Encoding a
    card-sized image as PNG took ~33 ms — every glass refresh paid it (2026-10-26). None when
    Quartz is not there (the caller then uses the PNG way)."""
    if not _GLASS_IMAGE_DIRECT['on'] or AppKit is None:
        return None
    try:
        import Quartz
        if image.format() != QImage.Format.Format_ARGB32_Premultiplied:
            image = image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        bits = image.constBits()
        bits.setsize(image.sizeInBytes())
        data = AppKit.NSData.dataWithBytes_length_(bytes(bits), image.sizeInBytes())
        provider = Quartz.CGDataProviderCreateWithCFData(data)
        space = Quartz.CGColorSpaceCreateWithName(Quartz.kCGColorSpaceSRGB)
        info = Quartz.kCGImageAlphaPremultipliedFirst | Quartz.kCGBitmapByteOrder32Little   # Qt's BGRA in memory
        return Quartz.CGImageCreate(image.width(), image.height(), 8, 32, image.bytesPerLine(), space, info,
                                    provider, None, False, Quartz.kCGRenderingIntentDefault)
    except Exception:
        logging.exception('Direct glass image failed; using PNG.')
        _GLASS_IMAGE_DIRECT['on'] = False
        return None


def _qimage_to_nsimage(image, size_points):
    from PyQt6.QtCore import QBuffer, QIODevice
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, 'PNG')
    raw = bytes(buffer.data())
    data = AppKit.NSData.dataWithBytes_length_(raw, len(raw))
    ns_image = AppKit.NSImage.alloc().initWithData_(data)
    if ns_image is not None:
        ns_image.setSize_(AppKit.NSMakeSize(float(size_points.width()), float(size_points.height())))
    return ns_image


class _GlassPaintGate(QObject):
    """While in-window glass is up, the widget and its children must not paint into the
    window (they would show through the glass, blurred): their paint events are dropped
    and turned into a refresh of the glass image — which renders them with the gate open."""

    def __init__(self, helper):
        super().__init__(helper)
        self._helper = helper

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.ChildAdded and isinstance(event.child(), QWidget):
            # A child added later (a rebuilt list row, a new hint label) must not paint into the
            # window under the glass before the next refresh: gate it (and its own children)
            # once it is set up, and redraw the glass image.
            self._helper.schedule_gate_new_children()
            return False
        if event.type() == QEvent.Type.Paint:
            helper = self._helper
            if not helper.active:
                return False
            own = helper._widget
            top = getattr(helper, '_top', None)
            if top is not None and obj is not own and isinstance(obj, QWidget) and obj.window() is not top:
                return False   # in a window of its own (a hover text shown for the bar): paints normally
            if not _GLASS_RENDER_STACK:
                inner = getattr(obj, '_broccoli_inwindow_glass', None)
                if inner is None or inner is helper or not inner.active:
                    helper.schedule_refresh()   # (a control with its own glass refreshes that one)
                return True
            rendering = _GLASS_RENDER_STACK[-1]
            if rendering is own or own.isAncestorOf(rendering):
                return False   # this glass, or one inside it, is being rendered: paint
            if rendering.isAncestorOf(own):
                return True    # a surrounding bar renders: this control lives in its own glass
        return False


_GLASS_WATCH_KINDS = frozenset((QEvent.Type.Move, QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.Hide,
                                 QEvent.Type.ZOrderChange))


class _InWindowGlassWatch(QObject):
    """One event filter per watched widget (a glass control and its ancestors), shared by every
    in-window glass under it: an ordinary event costs one quick type check, not one call per
    glass control (the Settings panel alone holds dozens of glass buttons)."""

    def __init__(self, watched):
        super().__init__(watched)
        self._helpers = []
        watched.installEventFilter(self)

    def add(self, helper):
        if helper not in self._helpers:
            self._helpers.append(helper)

    def discard(self, helper):
        try:
            self._helpers.remove(helper)
        except ValueError:
            pass

    def eventFilter(self, obj, event):
        if event.type() in _GLASS_WATCH_KINDS:
            for helper in list(self._helpers):
                helper.on_watched_event(obj, event)
        return False


def _inwindow_glass_watch(widget):
    watch = getattr(widget, '_broccoli_glass_watch', None)
    if watch is None:
        watch = _InWindowGlassWatch(widget)
        widget._broccoli_glass_watch = watch
    return watch


def _innermost_active_glass(widget):
    """The nearest ancestor (or the widget itself) whose in-window glass is up, or None."""
    node = widget
    while node is not None:
        helper = getattr(node, '_broccoli_inwindow_glass', None)
        if helper is not None and helper.active:
            return helper
        if node.isWindow():
            return None
        node = node.parentWidget()
    return None


_GLASS_CARET = {'on': True, 'timer': None}


def _glass_caret_tick():
    _GLASS_CARET['on'] = not _GLASS_CARET['on']
    focus = QApplication.focusWidget()
    if isinstance(focus, (QPlainTextEdit, QTextEdit, QLineEdit)) and getattr(focus, '_broccoli_glass_caret_width', None) is not None:
        helper = _innermost_active_glass(focus)
        if helper is not None:
            helper.schedule_refresh()


def _glass_caret_restart(*_args):
    """Typing / moving the cursor shows the caret at once (like Qt's own blink)."""
    _GLASS_CARET['on'] = True
    timer = _GLASS_CARET.get('timer')
    if timer is not None:
        timer.start()


_NO_QT_CARET_STYLE = []


def _no_qt_caret_style():
    """A one-line field has no caret-width setting: this style gives Qt's caret width 0 (its
    stylesheet still applies on top). Based on the application style, which it does not own."""
    if not _NO_QT_CARET_STYLE:
        class _NoQtCaretStyle(QProxyStyle):
            def pixelMetric(self, metric, option=None, widget=None):
                if metric == QStyle.PixelMetric.PM_TextCursorWidth:
                    return 0
                return super().pixelMetric(metric, option, widget)
        _NO_QT_CARET_STYLE.append(_NoQtCaretStyle())
    return _NO_QT_CARET_STYLE[0]


_GLASS_CARET_IME_ANSWER = []


def _glass_caret_ime_answer():
    """Where the input method's candidate window goes (2026-11-01): a text box with Qt's caret
    width 0 answers "where is the caret?" with a 0-wide box, and Qt takes a 0-wide box as no
    answer — it is passed on untranslated, in the box's own coordinates, so macOS put the
    candidate window near the top-left corner of the window instead of at the caret. This
    filter lets the box answer as usual, then gives the caret boxes the width the glass draws."""
    if not _GLASS_CARET_IME_ANSWER:
        class _GlassCaretImeAnswer(QObject):
            def eventFilter(self, obj, event):
                if event.type() != QEvent.Type.InputMethodQuery:
                    return False
                try:
                    if obj.cursorWidth() > 0:
                        return False   # Qt's own caret (no glass): its answer is right
                    obj.event(event)
                    width = max(1, int(getattr(obj, '_broccoli_glass_caret_width', None) or 1))
                    for query in (Qt.InputMethodQuery.ImCursorRectangle, Qt.InputMethodQuery.ImAnchorRectangle):
                        if not (event.queries() & query):
                            continue
                        box = event.value(query)
                        if isinstance(box, (QRect, QRectF)) and box.width() <= 0 and box.height() > 0:
                            event.setValue(query, QRectF(box.x(), box.y(), width, box.height()))
                    return True
                except RuntimeError:
                    return False
        _GLASS_CARET_IME_ANSWER.append(_GlassCaretImeAnswer())
    return _GLASS_CARET_IME_ANSWER[0]


def _sync_glass_carets(root):
    """Text boxes under live in-window glass draw no caret of their own (the glass draws it,
    see InWindowLiquidGlass._draw_own_caret); without glass Qt's caret comes back."""
    try:
        edits = [root] if isinstance(root, (QPlainTextEdit, QTextEdit, QLineEdit)) else []
        edits += root.findChildren(QPlainTextEdit) + root.findChildren(QTextEdit) + root.findChildren(QLineEdit)
    except RuntimeError:
        return
    for edit in edits:
        try:
            under_glass = _innermost_active_glass(edit) is not None
            stored = getattr(edit, '_broccoli_glass_caret_width', None)
            if under_glass and stored is None and isinstance(edit, QLineEdit):
                edit._broccoli_glass_caret_width = 1
                edit.setStyle(_no_qt_caret_style())
                if not getattr(edit, '_broccoli_glass_caret_wired', False):
                    edit._broccoli_glass_caret_wired = True
                    edit.cursorPositionChanged.connect(_glass_caret_restart)
                    edit.textEdited.connect(_glass_caret_restart)
                if _GLASS_CARET.get('timer') is None:
                    timer = QTimer()
                    timer.setInterval(max(250, int(QGuiApplication.styleHints().cursorFlashTime() / 2) or 500))
                    timer.timeout.connect(_glass_caret_tick)
                    _GLASS_CARET['timer'] = timer
                    timer.start()
            elif not under_glass and stored is not None and isinstance(edit, QLineEdit):
                edit.setStyle(None)   # back to the application style: Qt's caret again
                edit._broccoli_glass_caret_width = None
            elif under_glass and stored is None:
                edit._broccoli_glass_caret_width = max(1, edit.cursorWidth())
                edit.setCursorWidth(0)
                if not getattr(edit, '_broccoli_glass_caret_wired', False):
                    edit._broccoli_glass_caret_wired = True
                    edit.cursorPositionChanged.connect(_glass_caret_restart)
                    edit.installEventFilter(_glass_caret_ime_answer())   # candidate window at the caret
                if _GLASS_CARET.get('timer') is None:
                    timer = QTimer()
                    timer.setInterval(max(250, int(QGuiApplication.styleHints().cursorFlashTime() / 2) or 500))
                    timer.timeout.connect(_glass_caret_tick)
                    _GLASS_CARET['timer'] = timer
                    timer.start()
            elif not under_glass and stored is not None:
                edit.setCursorWidth(int(stored))
                edit._broccoli_glass_caret_width = None
        except RuntimeError:
            continue


# CALayer.contentsRect of the glass's content view: is its y measured from the top? (The content
# view is an ordinary unflipped NSView: from the bottom.) Checked on screen 2026-10-26.
_GLASS_CONTENTS_RECT_TOP_DOWN = False


class InWindowLiquidGlass(QObject):
    """System glass on top of a widget in an opaque-painted window (see the block comment).
    The widget cooperates: while `_liquid_glass_active` it paints nothing, and when
    `_glass_foreground_pass` is set it paints only its foreground (that image goes into
    the glass). `radius_for()` gives the corner radius, `dark_for()` dark appearance.
    hover_tint: its tints are hover / press feedback — they keep the frosted (regular)
    glass instead of switching it to the clear kind, so hovering only darkens it a little.
    look: a system glass look by name (_set_glass_look) instead of the frosted one; its
    tints then only tint, like hover_tint (a style switch would drop the look)."""

    def __init__(self, widget, radius_for, dark_for=None, rect_for=None, wanted_for=None, tint_for=None,
                 hover_tint=False, look=None):
        super().__init__(widget)
        self._widget = widget
        self._top = widget.window()
        own_window = _broccoli_own_ns_window(self._top)
        if self._top is widget or own_window is None:
            raise RuntimeError('no own window for in-window glass')
        # Its glass keeps the active look while another app is in front (registered before
        # any glass view of this window exists, so they all start out that way).
        _want_active_glass(own_window, self._top)
        self._hover_tint = bool(hover_tint)
        self._look = look
        self._radius_for = radius_for
        self._dark_for = dark_for
        self._rect_for = rect_for       # the part of the widget that is glass (default: all of it)
        self._wanted_for = wanted_for   # False → the widget paints itself (e.g. an expanded pill)
        self._tint_for = tint_for
        self._active = False
        self._dirty = True
        self._refresh_pending = False
        self._image_size = None    # the widget size the glass image was rendered at (all of it)
        self._sliding = False      # its visible part is moving (a card sliding in its dock)
        self._settle_timer = None
        self._tint_key = 'unset'
        self._win_id = int(self._top.winId())
        self._gate = _GlassPaintGate(self)
        self._gated = set()
        self.glass = BroccoliPassThroughGlassView.alloc().initWithFrame_(AppKit.NSMakeRect(0, 0, 1, 1))
        if look is not None:
            _set_glass_look(self.glass, look)   # before it is first shown: no frosted flash
        self.content = AppKit.NSView.alloc().initWithFrame_(AppKit.NSMakeRect(0, 0, 1, 1))
        self.content.setWantsLayer_(True)
        self.content.layer().setContentsGravity_('resize')
        self.glass.setContentView_(self.content)
        self.glass.setHidden_(True)
        objc.objc_object(c_void_p=self._win_id).addSubview_(self.glass)
        _INWINDOW_GLASS_BY_WINDOW.setdefault(id(self._top), []).append(self)
        self._restack_descendants()
        top_key, glass_view = id(self._top), self.glass
        widget.destroyed.connect(lambda *_args, k=top_key, g=glass_view, me=self: (
            g.removeFromSuperview(),
            _INWINDOW_GLASS_BY_WINDOW.get(k, []).remove(me) if me in _INWINDOW_GLASS_BY_WINDOW.get(k, []) else None))
        self._watched = [widget]
        parent = widget.parentWidget()
        while parent is not None and parent is not self._top:
            self._watched.append(parent)
            parent = parent.parentWidget()
        self._watched.append(self._top)
        self._watches = [_inwindow_glass_watch(watched) for watched in self._watched]
        for watch in self._watches:
            watch.add(self)
        widget.destroyed.connect(lambda *_args, me=self: me._forget_watches())
        self._install_gate()
        self.sync()

    def _forget_watches(self):
        for watch in getattr(self, '_watches', []):
            try:
                watch.discard(self)
            except RuntimeError:
                pass
        self._watches = []

    @property
    def active(self) -> bool:
        return self._active

    def schedule_gate_new_children(self):
        if not getattr(self, '_gate_pending', False):   # one pass per batch (a list rebuild adds many)
            self._gate_pending = True
            QTimer.singleShot(0, self.gate_new_children)

    def gate_new_children(self):
        self._gate_pending = False
        try:
            self._install_gate()
            _sync_glass_carets(self._widget)
            if self._active:
                self._widget.update()   # a repaint wipes anything it drew under the glass meanwhile
                self.schedule_refresh()
        except RuntimeError:
            pass

    def _draw_own_caret(self, image):
        """The caret of a focused text box inside this glass, drawn in its text colour. Qt's
        own caret is switched off under glass (_sync_glass_carets): Qt inverts the pixels
        under the caret but keeps their alpha, and on the glass image (transparent, or the
        faint grey veil of the bar's text field) that gave a bright white line in every theme."""
        focus = QApplication.focusWidget()
        widget = self._widget
        if not isinstance(focus, (QPlainTextEdit, QTextEdit, QLineEdit)) or not (focus is widget or widget.isAncestorOf(focus)):
            return
        if getattr(focus, '_broccoli_glass_caret_width', None) is None or not _GLASS_CARET['on']:
            return
        if _innermost_active_glass(focus) is not self or not focus.hasFocus():
            return
        if isinstance(focus, QLineEdit):
            if focus.isReadOnly() or focus.hasSelectedText():
                return
            try:   # a line edit reports a 10 pt box centred on its caret
                box = focus.inputMethodQuery(Qt.InputMethodQuery.ImCursorRectangle)
                box = box.toRect() if isinstance(box, QRectF) else QRect(box)
                origin = focus.mapTo(widget, QPoint(box.x() + box.width() // 2, box.y()))
                painter = QPainter(image)
                painter.fillRect(QRect(origin, QSize(1, box.height())), focus.palette().color(QPalette.ColorRole.Text))
                painter.end()
            except Exception:
                pass
            return
        caret_flags = Qt.TextInteractionFlag.TextEditable | Qt.TextInteractionFlag.TextSelectableByKeyboard
        if not (focus.textInteractionFlags() & caret_flags):
            return   # read-only text (an explanation card, a log): Qt shows no caret there either
        try:
            caret = focus.cursorRect()
            origin = focus.viewport().mapTo(widget, caret.topLeft())
            width = max(1, int(focus._broccoli_glass_caret_width or 1))
            painter = QPainter(image)
            painter.fillRect(QRect(origin, QSize(width, caret.height())), focus.palette().color(QPalette.ColorRole.Text))
            painter.end()
        except Exception:
            pass

    def _install_gate(self):
        for target in [self._widget] + self._widget.findChildren(QWidget):
            top = getattr(self, '_top', None)
            if top is not None and target is not self._widget and target.window() is not top:
                continue   # its own window (a hover text, a pop-up): it never paints under this glass
            key = id(target)
            if key not in self._gated:
                self._gated.add(key)
                target.installEventFilter(self._gate)
                target.destroyed.connect(lambda *_args, k=key: self._gated.discard(k))

    def on_watched_event(self, obj, event):
        kind = event.type()
        if kind in (QEvent.Type.Move, QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.Hide):
            self.sync()
        elif kind == QEvent.Type.ZOrderChange and obj is self._widget and self.glass.superview() is not None:
            self.glass.superview().addSubview_positioned_relativeTo_(self.glass, int(getattr(AppKit, 'NSWindowAbove', 1)), None)
            self._restack_descendants()
        elif kind == QEvent.Type.ZOrderChange:
            self.sync()   # an ancestor was raised / lowered: an overlay may now be under it, or over it
        return False

    def _restack_descendants(self):
        """Glass of controls inside this widget (a bar's buttons) stays above this glass."""
        for other in list(_INWINDOW_GLASS_BY_WINDOW.get(id(self._top), [])):
            try:
                if other is not self and self._widget.isAncestorOf(other._widget) and other.glass.superview() is not None:
                    other.glass.superview().addSubview_positioned_relativeTo_(
                        other.glass, int(getattr(AppKit, 'NSWindowAbove', 1)), None)
            except RuntimeError:
                continue

    def sync(self):
        try:
            widget, top = self._widget, self._top
            win_id = int(top.winId())
            if win_id != self._win_id or self.glass.superview() is None:   # window recreated
                self._win_id = win_id
                _want_active_glass(_broccoli_own_ns_window(top), top)
                objc.objc_object(c_void_p=win_id).addSubview_(self.glass)
                _schedule_restack_window_glass(top)   # it lands on top: back into Qt's order
            want = bool(widget.isVisible() and top.isVisible() and not _inwindow_glass_occluded(widget, top)
                        and (self._wanted_for is None or self._wanted_for()))
            if want != self._active:
                self._active = want
                widget._liquid_glass_active = want
                hook = getattr(widget, '_on_inwindow_glass_changed', None)
                if callable(hook):
                    hook(want)
                _sync_glass_carets(widget)
                self._dirty = True
                widget.update()
            self.glass.setHidden_(not want)
            if not want:
                return
            part = self._glass_rect()
            part_changed = part != getattr(self, '_shown_part', None)
            if part_changed:
                self._shown_part = QRect(part)
                if self._image_size is not None and self._image_size == widget.size():
                    # a clipped widget slid further in / out: show another part of the image it
                    # already has — re-rendering it every frame (and encoding it) left the
                    # editor cards' slide at ~25 fps with 50 ms hitches
                    self._show_image_part(part)
                    self._begin_sliding()
                else:
                    self._dirty = True
            origin = widget.mapTo(top, part.topLeft())
            frame = AppKit.NSMakeRect(origin.x(), origin.y(), part.width(), part.height())
            self.glass.setFrame_(frame)
            self.glass.setCornerRadius_(float(self._radius_for()))
            self.content.setFrame_(AppKit.NSMakeRect(0, 0, part.width(), part.height()))
            if self._tint_for is not None:
                self.set_tint(self._tint_for())
            dark = bool(self._dark_for()) if callable(self._dark_for) else None
            appearance = _ns_appearance(True if dark else None)
            self.glass.setAppearance_(appearance)
            if self._dirty and part_changed and not self._sliding:
                # in the same pass as the new frame: a later refresh let every animation step
                # show the old image stretched into the new frame (squeezed / widened text)
                self.refresh_content()
            elif self._dirty:
                self.schedule_refresh()   # while sliding: once it has settled
        except RuntimeError:
            pass
        except Exception:
            logging.exception('In-window glass sync failed.')

    def _glass_rect(self):
        rect = self._rect_for() if callable(self._rect_for) else None
        return QRect(rect) if rect is not None and not rect.isEmpty() else QRect(QPoint(0, 0), self._widget.size())

    def set_tint(self, color):
        key = QColor(color).rgba() if color is not None else None
        if key != self._tint_key:
            self._tint_key = key
            if self._hover_tint or self._look is not None:   # keep the glass kind: only the veil comes and goes
                self.glass.setTintColor_(_ns_color(color) if color is not None else None)
            else:
                _set_glass_tint(self.glass, color)

    def schedule_refresh(self):
        self._dirty = True
        if self._sliding:
            return   # repaints of what the slide uncovers: one refresh once it has settled
        if not self._refresh_pending:
            self._refresh_pending = True
            QTimer.singleShot(0, self.refresh_content)

    def _begin_sliding(self):
        self._sliding = True
        if self._settle_timer is None:
            self._settle_timer = QTimer(self)
            self._settle_timer.setSingleShot(True)
            self._settle_timer.setInterval(90)   # still for this long: the slide is over
            self._settle_timer.timeout.connect(self._end_sliding)
        self._settle_timer.start()

    def _end_sliding(self):
        self._sliding = False
        if self._dirty:
            self.refresh_content()

    def _show_image_part(self, part):
        """The glass shows `part` of its full image (widget coordinates)."""
        size = self._image_size
        if size is None:
            return
        w, h = float(max(1, size.width())), float(max(1, size.height()))
        y = part.y() / h if _GLASS_CONTENTS_RECT_TOP_DOWN else (h - part.y() - part.height()) / h
        self.content.layer().setContentsRect_(AppKit.NSMakeRect(part.x() / w, y, part.width() / w, part.height() / h))

    def refresh_content(self):
        self._refresh_pending = False
        widget = self._widget
        try:
            if not self._active or widget.width() <= 0 or widget.height() <= 0:
                return
            ratio = max(1.0, float(widget.devicePixelRatioF()))
            self._install_gate()   # children added since (new tabs, an inline editor…)
            image = render_glass_foreground(widget)
            self._draw_own_caret(image)
            # the whole widget's image; the glass shows the part that is glass (a clipped widget
            # sliding just shows another part of it, without rendering again)
            layer = self.content.layer()
            direct = _qimage_to_layer_contents(image, ratio)
            if direct is not None:
                layer.setContents_(direct)
                layer.setContentsScale_(ratio)
            else:
                layer.setContents_(_qimage_to_nsimage(image, widget.size()))
            self._image_size = QSize(widget.size())
            self._show_image_part(self._glass_rect())
            self._dirty = False
        except RuntimeError:
            pass
        except Exception:
            logging.exception('In-window glass content refresh failed.')


def install_inwindow_bar_glass(cls, dark_for):
    """A capsule bar becomes a glass capsule: its children (text box, buttons, tabs) are
    rendered into the glass; its own capsule background and drop shadow give way."""
    original_show = cls.showEvent

    def showEvent(self, event, _original=original_show):
        _original(self, event)
        if getattr(self, '_broccoli_inwindow_glass', None) is None and inwindow_glass_available():
            QTimer.singleShot(120, lambda w=self: attach_inwindow_liquid_glass(
                w, lambda w=w: w.height() / 2.0, lambda w=w: dark_for(w)) if w.isVisible() else None)

    def _on_inwindow_glass_changed(self, active):
        effect = self.graphicsEffect()
        if effect is not None:
            effect.setEnabled(not active)   # the glass brings its own shadow
    cls.showEvent = showEvent
    cls._on_inwindow_glass_changed = _on_inwindow_glass_changed


def install_inwindow_panel_glass(cls, dark_for, radius_for=None, rect_for=None, wanted_for=None):
    """A floating card inside the main window (the / list's kind: Agent plan, queue) is
    frosted system glass: its own solid card and drop shadow give way, and its contents are
    rendered into the glass. It floats over other glass controls, so it covers them."""
    original_init, original_show, original_paint = cls.__init__, cls.showEvent, cls.paintEvent

    def __init__(self, *args, _original=original_init, **kwargs):
        _original(self, *args, **kwargs)
        register_glass_occluder(self)

    def showEvent(self, event, _original=original_show):
        _original(self, event)
        if getattr(self, '_broccoli_inwindow_glass', None) is None and inwindow_glass_available():
            QTimer.singleShot(0, lambda w=self: attach_inwindow_liquid_glass(
                w, (lambda w=w: float(radius_for(w))) if radius_for is not None
                else (lambda w=w: glass_corner_radius(getattr(w, '_panel_radius', 34), smooth=True)),
                lambda w=w: dark_for(w),
                rect_for=(lambda w=w: rect_for(w)) if rect_for is not None else None,
                wanted_for=(lambda w=w: bool(wanted_for(w))) if wanted_for is not None else None) if w.isVisible() else None)

    def paintEvent(self, event, _original=original_paint):
        if getattr(self, '_liquid_glass_active', False):
            return   # the glass is the card
        _original(self, event)

    def _on_inwindow_glass_changed(self, active):
        effect = self.graphicsEffect()
        if effect is not None:
            effect.setEnabled(not active)   # the glass brings its own shadow
        restyle = getattr(self, '_apply_theme', None)
        if callable(restyle):
            restyle()   # inner backgrounds that must turn see-through under the glass
    cls.__init__ = __init__
    cls.showEvent = showEvent
    cls.paintEvent = paintEvent
    cls._on_inwindow_glass_changed = _on_inwindow_glass_changed


def install_inwindow_circle_glass(widget, rect_for, wanted_for=None, tint_for=None, dark_for=None, hover_tint=False):
    """A round button inside a (glass) bar becomes its own glass disc, above the bar's
    glass; its icon / glyph is drawn into it. Attached when first shown. hover_tint: the
    tint is hover / press feedback (see InWindowLiquidGlass)."""
    def attach(w=widget):
        try:
            if getattr(w, '_broccoli_inwindow_glass', None) is None and w.isVisible():
                attach_inwindow_liquid_glass(
                    w, lambda w=w: rect_for(w).height() / 2.0, dark_for=(lambda w=w: dark_for(w)) if dark_for else None,
                    rect_for=lambda w=w: rect_for(w), wanted_for=(lambda w=w: wanted_for(w)) if wanted_for else None,
                    tint_for=(lambda w=w: tint_for(w)) if tint_for else None, hover_tint=hover_tint)
        except RuntimeError:
            pass
    if inwindow_glass_available():
        QTimer.singleShot(0, attach)


def render_glass_foreground(widget) -> QImage:
    """What a glass widget puts into its glass (its text / icon; fills and borders give way to the
    glass), as an image at the screen's pixel ratio."""
    ratio = max(1.0, float(widget.devicePixelRatioF()))
    image = QImage(int(widget.width() * ratio), int(widget.height() * ratio), QImage.Format.Format_ARGB32_Premultiplied)
    image.setDevicePixelRatio(ratio)
    image.fill(0)
    effect = widget.graphicsEffect()
    effect_was_enabled = effect.isEnabled() if effect is not None else False
    if effect is not None and effect_was_enabled:
        effect.setEnabled(False)   # render() skips a widget with an active effect
    widget._glass_foreground_pass = True
    _GLASS_RENDER_STACK.append(widget)
    try:
        widget.render(image, QPoint(), QRegion(), QWidget.RenderFlag.DrawChildren)
    finally:
        _GLASS_RENDER_STACK.pop()
        widget._glass_foreground_pass = False
        if effect is not None and effect_was_enabled:
            effect.setEnabled(True)
    return image


def glass_hover_tint(widget, pressed: bool, hovered: bool, dark: bool):
    """Hover / press feedback on a glass button: a light veil on the (still frosted) glass."""
    if pressed:
        return QColor(255, 255, 255, 34) if dark else QColor(0, 0, 0, 22)
    if hovered:
        return QColor(255, 255, 255, 16) if dark else QColor(0, 0, 0, 9)
    return None


def attach_inwindow_liquid_glass(widget, radius_for, dark_for=None, rect_for=None, wanted_for=None, tint_for=None,
                                 hover_tint=False, look=None):
    if not inwindow_glass_available():
        return None
    existing = getattr(widget, '_broccoli_inwindow_glass', None)
    if existing is not None:
        return existing
    try:
        helper = InWindowLiquidGlass(widget, radius_for, dark_for, rect_for=rect_for, wanted_for=wanted_for, tint_for=tint_for,
                                     hover_tint=hover_tint, look=look)
    except Exception:
        logging.exception('In-window glass for %s failed.', type(widget).__name__)
        return None
    widget._broccoli_inwindow_glass = helper
    if helper.active:
        # it turned on inside its constructor, before the widget held it: the caret switch
        # then found no glass (a glass search field kept Qt's white caret)
        _sync_glass_carets(widget)
    return helper


# ── 玻璃按钮（2026-10-25）：所有按钮统一成主窗口底栏那种玻璃胶囊 ─────────────────────
# 以前只有底栏的胶囊按钮是玻璃；对话框、设置、About、编辑器、各面板里的按钮还是旧的
# 自画底色（两套：22 高 6 圆角的灰底，和 30 高全圆角的白底）。现在一律：按钮的样式表
# 只留文字（颜色、字体、边距、对齐），底色和边框交给系统玻璃；原来有颜色的底（蓝色
# 主按钮、红色警示按钮）变成玻璃的着色；悬停 / 按下是一层浅浅的薄纱。没有玻璃时
# （离屏、关掉玻璃、被遮罩盖住时）照旧画原来的样子。
_GLASS_BUTTON_FILL_RE = re.compile(r'(?<![\w-])(background(?:-color)?)\s*:\s*[^;}]+')
_GLASS_BUTTON_BORDER_RE = re.compile(r'(?<![\w-])border\s*:\s*[^;}]+')
_GLASS_BUTTON_BORDER_COLOR_RE = re.compile(r'(?<![\w-])border-color\s*:\s*[^;}]+')
_QSS_RGBA_RE = re.compile(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)(%?)\s*)?\)')


def glassify_button_qss(qss: str) -> str:
    """The button's stylesheet with every fill and border taken out (text stays)."""
    qss = _GLASS_BUTTON_FILL_RE.sub(lambda m: m.group(1) + ': transparent', str(qss or ''))
    qss = _GLASS_BUTTON_BORDER_RE.sub('border: none', qss)
    return _GLASS_BUTTON_BORDER_COLOR_RE.sub('border-color: transparent', qss)


def _qss_colour(value):
    value = str(value or '').strip()
    match = _QSS_RGBA_RE.match(value)
    if match:
        r, g, b = (int(match.group(i)) for i in (1, 2, 3))
        alpha = 255
        if match.group(4) is not None:
            a = float(match.group(4))
            alpha = int(round(a * 2.55)) if match.group(5) else (int(round(a * 255)) if a <= 1.0 and '.' in match.group(4) else int(a))
        return QColor(r, g, b, max(0, min(255, alpha)))
    colour = QColor(value)
    return colour if colour.isValid() else None


def _button_qss_state_value(qss: str, prop: str):
    """`prop` in the button's normal state: the first rule without a pseudo-state or a
    property selector (a stylesheet without any selector counts as that rule)."""
    qss = str(qss or '')
    pattern = re.compile(r'(?<![\w-])' + re.escape(prop) + r'\s*:\s*([^;}]+)')
    if '{' not in qss:
        found = pattern.search(qss)
        return found.group(1).strip() if found else None
    for match in re.finditer(r'([^{}]*)\{([^{}]*)\}', qss):
        selector = match.group(1).strip()
        if ':' in selector or '[' in selector:
            continue
        found = pattern.search(match.group(2))
        if found:
            return found.group(1).strip()
    return None


def glass_button_role_tint(qss: str):
    """A coloured fill (accent blue, alert red …) becomes the glass tint; greys and white
    stay plain glass."""
    for prop in ('background-color', 'background'):
        colour = _qss_colour(_button_qss_state_value(qss, prop))
        if colour is not None:
            if colour.alpha() >= 120 and colour.hsvSaturationF() >= 0.35 and colour.valueF() >= 0.3:
                tinted = QColor(colour)
                tinted.setAlpha(215)
                return tinted
            return None
    return None


def _glass_button_text_is_light(qss: str) -> bool:
    colour = _qss_colour(_button_qss_state_value(qss, 'color'))
    return bool(colour is not None and colour.lightnessF() > 0.6)


class GlassButtonSkin(QObject):
    """One push button as a glass capsule (InWindowLiquidGlass, hover_tint), attached the
    first time it is shown. While the glass is up the button's stylesheet is kept with its
    fills and borders taken out, also when its owner restyles it later (setStyleSheet is
    routed through here), so Qt draws only the text into the glass. tint_for(button):
    an explicit role tint (e.g. a pinned toggle); otherwise a coloured fill is the tint.
    look: a system glass look by name (e.g. GLASS_LOOK_CONTROL_CENTER) instead of the
    frosted one; hover / press lay the same light veil on it."""

    def __init__(self, button, tint_for=None, dark_for=None, radius_for=None, hover=True, on_change=None,
                 wanted_for=None, rect_for=None, look=None):
        super().__init__(button)
        self._button = button
        self._look = look
        self._wanted_for = wanted_for
        self._rect_for = rect_for   # rect_for(button): the part that is glass (a clipped button: what shows)
        self._tint_for = tint_for
        self._dark_for = dark_for
        self._radius_for = radius_for
        self._hover = bool(hover)
        self._on_change = on_change
        self._source_qss = button.styleSheet()
        self._active = False
        self._effect_was_enabled = None
        button._broccoli_glass_skin = self
        button._on_inwindow_glass_changed = self._glass_changed
        button.setStyleSheet = self._set_stylesheet      # the owner's restyles pass through here
        button.installEventFilter(self)
        if button.isVisible():
            QTimer.singleShot(0, self._attach)

    @property
    def active(self) -> bool:
        return self._active

    def source_stylesheet(self) -> str:
        return self._source_qss

    def _set_stylesheet(self, qss):
        self._source_qss = str(qss or '')
        QWidget.setStyleSheet(self._button, glassify_button_qss(self._source_qss) if self._active else self._source_qss)
        self._update_tint()

    def _attach(self):
        button = self._button
        try:
            if getattr(button, '_broccoli_inwindow_glass', None) is not None or not button.isVisible():
                return
            if _broccoli_own_ns_window(button.window()) is None:
                return   # no window of its own (e.g. hosted in a shared window): keep the Qt look
            attach_inwindow_liquid_glass(button, self._radius, self._dark, hover_tint=True, look=self._look,
                                         wanted_for=(lambda: bool(self._wanted_for(self._button)))
                                         if self._wanted_for is not None else None,
                                         rect_for=(lambda: self._rect_for(self._button))
                                         if self._rect_for is not None else None)
            # The glass turns on inside its constructor, before the button knows its helper,
            # so that first tint update found none: a blue Done came up untinted (white on white).
            self._update_tint()
        except RuntimeError:
            pass

    def _radius(self) -> float:
        if self._radius_for is not None:
            return float(self._radius_for(self._button))
        height = self._button.height()
        return height / 2.0 if height <= 40 else 16.0   # capsule; a tall tile keeps soft corners

    def _role_tint(self):
        button = self._button
        if not button.isEnabled():
            return None
        if self._tint_for is not None:
            return self._tint_for(button)
        return glass_button_role_tint(self._source_qss)

    def _dark(self) -> bool:
        if self._dark_for is not None:
            return bool(self._dark_for(self._button))
        if self._role_tint() is not None:
            return is_dark_theme(app)
        return _glass_button_text_is_light(self._source_qss)

    def _update_tint(self):
        helper = getattr(self._button, '_broccoli_inwindow_glass', None)
        if helper is None:
            return
        button = self._button
        pressed = bool(getattr(button, 'isDown', lambda: False)()) and self._hover
        hovered = button.underMouse() and button.isEnabled() and self._hover
        role = self._role_tint()
        if role is not None:
            tint = QColor(role).darker(116 if pressed else (108 if hovered else 100))
            tint.setAlpha(role.alpha())
        else:
            tint = glass_hover_tint(button, pressed, hovered, self._dark())
        helper.set_tint(tint)

    def _glass_changed(self, active: bool):
        button = self._button
        self._active = bool(active)
        QWidget.setStyleSheet(button, glassify_button_qss(self._source_qss) if self._active else self._source_qss)
        effect = button.graphicsEffect()
        if effect is not None:
            if self._active:
                self._effect_was_enabled = effect.isEnabled()
                effect.setEnabled(False)   # the glass brings its own shadow
            elif self._effect_was_enabled is not None:
                effect.setEnabled(self._effect_was_enabled)
        self._update_tint()
        if callable(self._on_change):
            self._on_change(self._active)

    def eventFilter(self, obj, event):
        kind = event.type()
        if kind == QEvent.Type.Show:
            if getattr(obj, '_broccoli_inwindow_glass', None) is None and inwindow_glass_available():
                QTimer.singleShot(0, self._attach)
        elif kind in (QEvent.Type.Enter, QEvent.Type.Leave, QEvent.Type.MouseButtonPress,
                      QEvent.Type.MouseButtonRelease, QEvent.Type.EnabledChange, QEvent.Type.DynamicPropertyChange):
            QTimer.singleShot(0, self._update_tint)
        return False


_SEARCH_GLYPH_ICON = []


def _search_glyph_icon() -> QIcon:
    """The system search field's magnifier, drawn (no image file): a mid grey that reads on
    light and dark glass alike."""
    if not _SEARCH_GLYPH_ICON:
        pixmap = QPixmap(32, 32)
        pixmap.setDevicePixelRatio(2.0)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor('#8E8E93'), 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawEllipse(QRectF(2.2, 2.2, 9.6, 9.6))
        painter.drawLine(QPointF(10.6, 10.6), QPointF(14.0, 14.0))
        painter.end()
        _SEARCH_GLYPH_ICON.append(QIcon(pixmap))
    return _SEARCH_GLYPH_ICON[0]


def add_search_glyph(edit):
    """The magnifier in front of a search field's text (the same drawn glyph everywhere, so the
    text does not start flush at the edge). Once per field. Returns the field."""
    if edit is not None and not getattr(edit, '_broccoli_search_glyph', False):
        edit._broccoli_search_glyph = True
        edit.addAction(_search_glyph_icon(), QLineEdit.ActionPosition.LeadingPosition)
    return edit


GLASS_SEARCH_HEIGHT = 36   # = the top tab bar (PillNavBar); a search is never taller (style book 5.5)


def glass_search_field(edit):
    """A global search field (one that searches a whole panel or page: the floating panels, the
    settings search, the editor's File and Logic Map pages) drawn like macOS 27's own (the system
    search field): a frosted glass capsule with a magnifier in front, as tall as the top tab bar.
    The skin takes its fill away under the glass; text, placeholder and caret are drawn into the
    glass. Returns the field."""
    if edit is None or getattr(edit, '_broccoli_glass_skin', None) is not None:
        return edit
    add_search_glyph(edit)
    edit.setFixedHeight(GLASS_SEARCH_HEIGHT)
    return glass_button(edit, hover=False)


def glass_button(button, tint_for=None, dark_for=None, radius_for=None, hover=True, on_change=None, wanted_for=None,
                 rect_for=None, look=None):
    """Make one QPushButton (or a stylesheet-painted QWidget) system glass (see GlassButtonSkin).
    Returns the widget."""
    if button is not None and getattr(button, '_broccoli_glass_skin', None) is None:
        GlassButtonSkin(button, tint_for=tint_for, dark_for=dark_for, radius_for=radius_for, hover=hover,
                        on_change=on_change, wanted_for=wanted_for, rect_for=rect_for, look=look)
    return button


def glass_disc_in_clip(button, alive_for=None):
    """A small round button inside something that slides in a clipping parent (an editor card,
    the card pager): a glass disc only where it shows — glass is not clipped by Qt, so it would
    float outside the card mid-slide — and only while alive_for(button) holds (a closing card
    fades in its Qt look)."""
    def owner_dark(b):
        # the owner's theme (the card / dock keep `_dark`): guessed from the text colour, the
        # card's light-grey ✕ read as dark mode and its disc came up grey
        widget = b
        while widget is not None:
            value = getattr(widget, '_dark', None)
            if isinstance(value, bool):
                return value
            widget = widget.parentWidget()
        return is_dark_theme(app)

    return glass_button(
        button, radius_for=lambda b: b.height() / 2.0, rect_for=glass_visible_part, dark_for=owner_dark,
        wanted_for=lambda b: not glass_visible_part(b).isEmpty() and (alive_for is None or bool(alive_for(b))))


def install_glass_button_class(cls, tint_for=None, dark_for=None, when=None):
    """Every button of `cls` (and its subclasses) for which when(button) holds is a glass capsule."""
    original_init = cls.__init__

    def __init__(self, *args, _original=original_init, **kwargs):
        _original(self, *args, **kwargs)
        if when is None or when(self):
            glass_button(self, tint_for=tint_for, dark_for=dark_for)
    cls.__init__ = __init__


# ── 统一的列表样式（必须保持打开的列表：多选、边打字边筛选）─────────────────────────
# 单选下拉已经是系统菜单；其余列表照系统菜单量出来的尺寸画（macOS 26/27 的 NSMenu：
# 底板 = 普通款液态玻璃、不着色、圆角 12、系统窗口阴影；行高 24、上下留 5；高亮 =
# 左右各缩进 5、圆角 7 的蓝底白字；勾号在 12、文字在 28（没有勾号列时 14）；分隔线
# 行高 11、半点细线）。没有玻璃时画同样尺寸的实心底板。
GLASS_LIST_ROW_H = 24
GLASS_LIST_PAD = 5             # card top / bottom, and the highlight's left / right inset
GLASS_LIST_RADIUS = 12
GLASS_LIST_ROW_RADIUS = 7
GLASS_LIST_FONT_PX = 13
GLASS_LIST_CHECK_X = 12        # check mark column (13 x 11)
GLASS_LIST_TEXT_X = 28         # text start when the list has a check column
GLASS_LIST_TEXT_X_PLAIN = 14   # text start without one
GLASS_LIST_TEXT_RIGHT = 12     # free space after the text
GLASS_LIST_SEPARATOR_H = 11
# The system highlight on the default blue accent, as it shows over the menu glass.
_GLASS_LIST_DEFAULT_ACCENT = (10, 130, 255)
_GLASS_LIST_HIGHLIGHT = {False: (100, 155, 248), True: (100, 150, 228)}


def _glass_list_highlight(dark: bool) -> QColor:
    """The menu highlight for the user's accent colour: the default blue gives exactly the
    measured system colour; another accent is shifted by the same amount."""
    base = _GLASS_LIST_HIGHLIGHT[bool(dark)]
    accent = _GLASS_LIST_DEFAULT_ACCENT
    try:
        if AppKit is not None and sys.platform == 'darwin':
            color = AppKit.NSColor.controlAccentColor().colorUsingColorSpace_(AppKit.NSColorSpace.sRGBColorSpace())
            if color is not None:
                accent = tuple(int(round(color.componentAtIndex_(i) * 255)) for i in range(3))
    except Exception:
        pass
    return QColor(*[max(0, min(255, a + (b - d))) for a, b, d in zip(accent, base, _GLASS_LIST_DEFAULT_ACCENT)])


def glass_list_palette(dark: bool) -> dict:
    return {
        'text': QColor(255, 255, 255, 217) if dark else QColor(0, 0, 0, 217),
        'muted': QColor(255, 255, 255, 140) if dark else QColor(0, 0, 0, 128),
        'accent': _glass_list_highlight(dark),
        'on_accent': QColor('#FFFFFF'),
        'separator': QColor(255, 255, 255, 36) if dark else QColor(0, 0, 0, 26),
        'bg': QColor(44, 44, 46, 246) if dark else QColor(246, 246, 246, 248),
        'border': QColor(255, 255, 255, 30) if dark else QColor(0, 0, 0, 22),
    }


def paint_glass_list_background(painter, widget, dark: bool):
    """The list's own card when there is no glass under it."""
    palette = glass_list_palette(dark)
    path = QPainterPath()
    path.addRoundedRect(QRectF(widget.rect()).adjusted(0.5, 0.5, -0.5, -0.5), GLASS_LIST_RADIUS, GLASS_LIST_RADIUS)
    painter.fillPath(path, palette['bg'])
    painter.strokePath(path, QPen(palette['border'], 1))


def glass_list_highlight_rect(widget_width, top) -> QRectF:
    """A row's highlight: full row height, inset like the system menu."""
    return QRectF(GLASS_LIST_PAD, top, widget_width - 2 * GLASS_LIST_PAD, GLASS_LIST_ROW_H)


def paint_glass_list_highlight(painter, rect, dark: bool):
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(glass_list_palette(dark)['accent']))
    painter.drawRoundedRect(QRectF(rect), GLASS_LIST_ROW_RADIUS, GLASS_LIST_ROW_RADIUS)
    painter.restore()


def paint_glass_list_check(painter, row_top, color):
    """The system menu's check mark: a 9.5 x 9 glyph centred in the 13 x 11 slot at x 12."""
    box = QRectF(GLASS_LIST_CHECK_X + 1.75, row_top + (GLASS_LIST_ROW_H - 9) / 2.0, 9.5, 9.0)
    path = QPainterPath()
    path.moveTo(box.left() + 0.7, box.top() + 4.9)
    path.lineTo(box.left() + 3.5, box.bottom() - 0.8)
    path.lineTo(box.right() - 0.6, box.top() + 0.8)
    painter.save()
    pen = QPen(QColor(color), 1.55)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)
    painter.restore()


def paint_glass_list_separator(painter, row_top, widget_width, dark: bool, text_x=GLASS_LIST_TEXT_X):
    """A half-point line in the middle of an 11 pt separator row, from the text column on."""
    y = row_top + GLASS_LIST_SEPARATOR_H / 2.0
    painter.save()
    painter.setPen(QPen(glass_list_palette(dark)['separator'], 0.5))
    painter.drawLine(QPointF(text_x, y), QPointF(widget_width - GLASS_LIST_TEXT_X_PLAIN, y))
    painter.restore()


def glass_list_font(base_font):
    font = QFont(base_font)
    font.setPixelSize(GLASS_LIST_FONT_PX)
    return font


def glass_list_view_qss(dark: bool, glass: bool, selector: str = 'QListWidget', outer_pad: bool = False) -> str:
    """Rows of a list view like the system menu (no check column). The view must sit
    GLASS_LIST_PAD inside the card (a container's margins), or pass outer_pad when the view
    itself is the card (a completer pop-up): then it keeps that space as its own padding."""
    palette = glass_list_palette(dark)
    text = 'rgba(%d,%d,%d,%d)' % palette['text'].getRgb()
    accent = palette['accent'].name()
    # Over glass the view is see-through (its caller keeps the scroll bar's knob right with
    # keep_scroll_bar_knob(), style book 5.9); without glass it paints the card colour, opaque — Qt
    # counts a half see-through list background as black for the knob.
    background = ('background: transparent; ' if glass
                  else 'background: rgb(%d,%d,%d); ' % palette['bg'].getRgb()[:3])
    pad = f'{GLASS_LIST_PAD}px' if outer_pad else '0px'
    return f"""
        {selector} {{ border: none; {background}color: {text}; font-size: {GLASS_LIST_FONT_PX}px;
                      outline: none; padding: {pad}; }}
        {selector}::item {{ min-height: {GLASS_LIST_ROW_H}px; max-height: {GLASS_LIST_ROW_H}px; margin: 0px;
                            padding: 0px {GLASS_LIST_TEXT_RIGHT - GLASS_LIST_PAD}px 0px {GLASS_LIST_TEXT_X_PLAIN - GLASS_LIST_PAD}px;
                            border: none; border-radius: {GLASS_LIST_ROW_RADIUS}px; }}
        {selector}::item:selected, {selector}::item:hover {{ background: {accent}; color: #FFFFFF; }}
        {selector}::item:disabled {{ color: rgba({palette['muted'].red()},{palette['muted'].green()},{palette['muted'].blue()},{palette['muted'].alpha()}); }}
    """   # no scroll bar rules: the system's overlay scroll bar shows only while scrolling


def fit_dialog_window_to_card(widget) -> bool:
    """Drop a dialog's see-through margin (its _panel_margin, 16): the window shrinks to the card
    it painted inside that margin and moves by the margin, so the card keeps its size and place;
    the layout's margins shrink by the same amount, so nothing inside moves. Once per dialog,
    before it is first drawn, and only with Liquid Glass (without it the card paints itself)."""
    if getattr(widget, '_window_fits_card', False) or not liquid_glass_available():
        return False
    margin = int(round(float(getattr(widget, '_panel_margin', 0) or 0)))
    widget._window_fits_card = True
    if margin <= 0:
        return False
    layout = widget.layout()
    if layout is not None:
        left, top, right, bottom = layout.getContentsMargins()
        layout.setContentsMargins(max(0, left - margin), max(0, top - margin),
                                  max(0, right - margin), max(0, bottom - margin))
    geometry = widget.geometry()
    width, height = max(1, geometry.width() - 2 * margin), max(1, geometry.height() - 2 * margin)
    if widget.minimumSize() == widget.maximumSize():
        widget.setFixedSize(width, height)
    else:
        widget.setMinimumSize(max(0, widget.minimumWidth() - 2 * margin), max(0, widget.minimumHeight() - 2 * margin))
        if widget.maximumWidth() < 16777215:
            widget.setMaximumWidth(max(1, widget.maximumWidth() - 2 * margin))
        if widget.maximumHeight() < 16777215:
            widget.setMaximumHeight(max(1, widget.maximumHeight() - 2 * margin))
        widget.resize(width, height)
    widget.move(geometry.x() + margin, geometry.y() + margin)
    widget._panel_margin = 0
    widget.update()
    return True


def install_dialog_fit_to_card(cls):
    """Run fit_dialog_window_to_card just before a dialog of `cls` is first shown."""
    original = cls.showEvent

    def showEvent(self, event, _original=original):
        fit_dialog_window_to_card(self)
        _original(self, event)

    cls.showEvent = showEvent


def install_window_liquid_glass(cls, radius, inset=0.0, dark_attrs=('_force_dark', '_always_dark', '_dark'), dark_for=None,
                                keep_shadow=False, menu_look=False):
    """Give every window of `cls` Liquid Glass the first time it is shown (wraps showEvent).
    radius / inset: numbers, or callables taking the widget. A truthy force-dark attribute
    makes the glass dark like the dialog's own palette. menu_look: a pop-up list (see
    _want_active_glass and the corner radius in apply_window_liquid_glass)."""
    original = cls.showEvent

    def showEvent(self, event, _original=original):
        _original(self, event)
        if not liquid_glass_available():
            return
        forced = dark_for(self) if dark_for is not None else any(bool(getattr(self, attr, False)) for attr in dark_attrs)
        dark = True if forced else None
        r = radius(self) if callable(radius) else radius
        i = inset(self) if callable(inset) else inset
        if not apply_window_liquid_glass(self, r, i, dark=dark, keep_shadow=keep_shadow, menu_look=menu_look):
            QTimer.singleShot(0, lambda w=self, r=r, i=i, d=dark: apply_window_liquid_glass(
                w, r, i, dark=d, keep_shadow=keep_shadow, menu_look=menu_look))

    cls.showEvent = showEvent



# ---- Broccoli 418 lines 15194-15202 ----

def is_dark_theme(app_obj) -> bool:
    try:
        if NSUserDefaults is not None:
            defaults = NSUserDefaults.standardUserDefaults()
            style = defaults.stringForKey_("AppleInterfaceStyle")
            return style == "Dark"
        return app_obj.palette().window().color().lightness() < 128
    except Exception:
        return False

# ---- Broccoli 418 lines 15251-15296 ----

def _input_card_stylesheet(dark: bool) -> str:
    if dark:
        return '''
            QListWidget {
                border: 1px solid #3A3A3A;
                border-radius: 14px;
                background: #2D2D2D;
                outline: none;
                padding: 6px;
                font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
                font-size: 13px;
                color: #F2F2F7;
            }
            QListWidget::item {
                border-radius: 10px;
                padding: 10px 12px;
                margin: 0 0 6px 0;
                background: #3A3A3A;
            }
            QListWidget::item:selected {
                background: #2E5C91;
                color: #FFFFFF;
            }
        '''
    return '''
        QListWidget {
            border: 1px solid #ECECEC;
            border-radius: 14px;
            background: #FFFFFF;
            outline: none;
            padding: 6px;
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 13px;
            color: #20242B;
        }
        QListWidget::item {
            border-radius: 10px;
            padding: 10px 12px;
            margin: 0 0 6px 0;
            background: #F7F7F8;
        }
        QListWidget::item:selected {
            background: #E8EEF8;
            color: #1A4B7A;
        }
    '''

# ---- Broccoli 418 lines 15299-15419 ----

def _settings_table_stylesheet(dark: bool) -> str:
    """URL 历史管理表（General 第 9 页）的主题样式，视觉语言与
    _input_card_stylesheet 的卡片一致；含表头、选中态和单元格编辑框。

    圆角策略（不用 mask——mask 只裁形状、裁出的边缘没有描边，四角
    永远缺边框弧线）：QSS 自己的圆角背景+边框负责四角；表头两个上角
    由 section:first/:last 的圆角背景匹配（半径小 1px 贴在边框内侧）；
    底部 12px padding 让行区退出弧角区域，弧角处显示的是 QSS 圆角背景。"""
    if dark:
        return '''
            QTableWidget {
                border: 1px solid #3A3A3A;
                border-radius: 14px;
                background: #2D2D2D;
                padding-bottom: 12px;
                gridline-color: #3A3A3A;
                outline: none;
                font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
                font-size: 13px;
                color: #F2F2F7;
                selection-background-color: #2E5C91;
                selection-color: #FFFFFF;
            }
            QTableWidget::item {
                padding: 6px 10px;
                border-bottom: 1px solid #3A3A3A;
            }
            QTableWidget::item:selected {
                background: #2E5C91;
                color: #FFFFFF;
            }
            QHeaderView {
                background: transparent;
                border: none;
            }
            QHeaderView::section {
                background: #3A3A3A;
                color: #A7AEB8;
                border: none;
                border-bottom: 1px solid #2D2D2D;
                padding: 6px 10px;
                font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
                font-size: 12px;
            }
            QHeaderView::section:first {
                border-top-left-radius: 13px;
                border-right: 1px solid #2D2D2D;
            }
            QHeaderView::section:last {
                border-top-right-radius: 13px;
            }
            QTableCornerButton::section {
                background: transparent;
                border: none;
            }
            QTableWidget QLineEdit {
                background: #1C1C1E;
                color: #F2F2F7;
                border: 1px solid #2E5C91;
                border-radius: 6px;
                padding: 2px 6px;
                font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
                font-size: 13px;
            }
        '''
    return '''
        QTableWidget {
            border: 1px solid #ECECEC;
            border-radius: 14px;
            background: #FFFFFF;
            padding-bottom: 12px;
            gridline-color: #ECECEC;
            outline: none;
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 13px;
            color: #20242B;
            selection-background-color: #E8EEF8;
            selection-color: #1A4B7A;
        }
        QTableWidget::item {
            padding: 6px 10px;
            border-bottom: 1px solid #ECECEC;
        }
        QTableWidget::item:selected {
            background: #E8EEF8;
            color: #1A4B7A;
        }
        QHeaderView {
            background: transparent;
            border: none;
        }
        QHeaderView::section {
            background: #F7F7F8;
            color: #7A8391;
            border: none;
            border-bottom: 1px solid #ECECEC;
            padding: 6px 10px;
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 12px;
        }
        QHeaderView::section:first {
            border-top-left-radius: 13px;
            border-right: 1px solid #ECECEC;
        }
        QHeaderView::section:last {
            border-top-right-radius: 13px;
        }
        QTableCornerButton::section {
            background: transparent;
            border: none;
        }
        QTableWidget QLineEdit {
            background: #FFFFFF;
            color: #20242B;
            border: 1px solid #2E5C91;
            border-radius: 6px;
            padding: 2px 6px;
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 13px;
        }
    '''

# ---- Broccoli 418 lines 15434-15457 ----

def _search_input_stylesheet(dark: bool) -> str:
    if dark:
        return '''
            QLineEdit {
                border: none;
                border-radius: 18px;
                padding: 0px 16px 0px 4px;   /* the magnifier sits in front; the height is fixed (36) */
                background: #3A3A3A;
                color: #F2F2F7;
                font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
                font-size: 15px;
            }
        '''
    return '''
        QLineEdit {
            border: none;
            border-radius: 18px;
            padding: 0px 16px 0px 4px;   /* the magnifier sits in front; the height is fixed (36) */
            background: #F5F6F8;
            color: #20242B;
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 15px;
        }
    '''

# ---- Broccoli 418 lines 15470-15497 ----

class _ScrollBarKnobBackdrop(QObject):
    """Keeps a see-through scroll area's Base colour white or black (style book 5.9). Qt's style sheets set
    it again — to black — whenever they re-style the area (its own or an ancestor's style sheet, the
    system appearance), so it is put back on every palette / style change."""
    _GROUPS = (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled)

    def __init__(self, area):
        super().__init__(area)
        self.area = area
        self.dark = False
        area.installEventFilter(self)

    def apply(self):
        try:
            want = QColor(0, 0, 0) if self.dark else QColor(255, 255, 255)
            palette = self.area.palette()
            if all(palette.color(group, QPalette.ColorRole.Base) == want for group in self._GROUPS):
                return
            for group in self._GROUPS:
                palette.setColor(group, QPalette.ColorRole.Base, want)
            self.area.setPalette(palette)
        except RuntimeError:   # the area is being destroyed
            pass

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.StyleChange, QEvent.Type.Polish):
            self.apply()
        return False

# ---- Broccoli 418 lines 15500-15515 ----

def keep_scroll_bar_knob(area, dark: bool) -> None:
    """Style book 5.9: a see-through scroll area (a list, a text box, a QScrollArea with 'background:
    transparent') tells the system scroll bar what it sits on. The scroll bar picks its knob from the
    area's Base colour — a dark knob on a light colour, a light knob on a dark one, transparency not
    looked at — and Qt makes a see-through area's Base black (lists and text boxes even for a half
    see-through background), so light panels got the white knob meant for dark backgrounds. This keeps
    Base white (dark=False) or black (dark=True), also through later re-styling; the area still paints
    nothing (its view keeps its own see-through colours). Call it where the area's colours are set,
    with what it sits on: the panel's appearance, or the one look of a surface that keeps it (the
    terminal and its panels: dark; the background-vision card, the translation's light glass: light)."""
    keeper = getattr(area, '_broccoli_scroll_knob', None)
    if keeper is None:
        keeper = _ScrollBarKnobBackdrop(area)
        area._broccoli_scroll_knob = keeper
    keeper.dark = bool(dark)
    keeper.apply()

# ---- Broccoli 418 lines 15518-15525 ----

def settings_scroll_area_style() -> str:
    """A settings page's scroller (pages scroll instead of being squashed; the panel is 500 x 760).
    System scroll bars (style book 5.9): no scroll bar rules; the scroll area and the page inside are
    see-through (the panel's appearance goes to the scroll bar through keep_scroll_bar_knob()); the
    page's rule names only the content, since "QScrollArea > QWidget > QWidget" picks the scroll bar
    too and turns it into the old arrow-button kind."""
    return ('QScrollArea { border: none; background: transparent; } '
            'QScrollArea > QWidget#qt_scrollarea_viewport > QWidget { background: transparent; }')

# ---- Broccoli 418 lines 15725-15760 ----

def _settings_lineedit_stylesheet(dark: bool) -> str:
    if dark:
        return '''
            QLineEdit {
                border: 1px solid #4A4B4F;
                border-radius: 6px;
                background: #3A3A3A;
                color: #F2F2F7;
                font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
                font-size: 13px;
                selection-background-color: #2E5C91;
                selection-color: #FFFFFF;
            }
            QLineEdit:disabled {
                background: #313133;
                color: #8E8E93;
                border: 1px solid #3E3E42;
            }
        '''
    return '''
        QLineEdit {
            border: 1px solid #D9D9DE;
            border-radius: 6px;
            background: #FFFFFF;
            color: #20242B;
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 13px;
            selection-background-color: #DCEAFB;
            selection-color: #20242B;
        }
        QLineEdit:disabled {
            background: #F7F7F8;
            color: #A0A3AA;
            border: 1px solid #E6E6EA;
        }
    '''

# ---- Broccoli 418 lines 15763-15800 ----

def _settings_textedit_stylesheet(dark: bool) -> str:
    if dark:
        return '''
            QTextEdit, QPlainTextEdit {
                border: 1px solid #4A4B4F;
                border-radius: 14px;
                background: #3A3A3A;
                padding: 10px 12px;
                color: #F2F2F7;
                font-size: 13px;
                font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
                selection-background-color: #2E5C91;
                selection-color: #FFFFFF;
            }
            QTextEdit:disabled, QPlainTextEdit:disabled {
                background: #313133;
                color: #8E8E93;
                border: 1px solid #3E3E42;
            }
        '''
    return '''
        QTextEdit, QPlainTextEdit {
            border: 1px solid #ECECEC;
            border-radius: 14px;
            background: #FFFFFF;
            padding: 10px 12px;
            color: #20242B;
            font-size: 13px;
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            selection-background-color: #DCEAFB;
            selection-color: #20242B;
        }
        QTextEdit:disabled, QPlainTextEdit:disabled {
            background: #F7F7F8;
            color: #A0A3AA;
            border: 1px solid #E6E6EA;
        }
    '''

# ---- Broccoli 418 lines 15961-16036 ----

class MacNormalButton(QPushButton):
    def __init__(self, text, parent=None, always_dark=False):
        super().__init__(text, parent)
        self.setAutoDefault(False)
        self.setFixedHeight(22)
        self._always_dark = bool(always_dark)
        self._alert = False
        self._updating_style = False
        self.update_theme()

    def update_theme(self):
        if self._updating_style:
            return
        self._updating_style = True
        try:
            if self._alert:
                bg = "#FF4D4D"
                bg_hover = "#FF6666"
                bg_pressed = "#CC3D3D"
                bg_disabled = "#E6E6E6"
                text = "#FFFFFF"
                text_disabled = "#777777"
            else:
                dark = self._always_dark or bool(getattr(self, '_force_dark', False)) or is_dark_theme(app)
                if dark:
                    bg = "#404145"
                    bg_hover = "#4A4B4F"
                    bg_pressed = "#343538"
                    bg_disabled = "#2F3033"
                    text = "#FFFFFF"
                    text_disabled = "#777777"
                else:
                    bg = "#E7E7E7"
                    bg_hover = "#EEEEEE"
                    bg_pressed = "#DCDCDC"
                    bg_disabled = "#E1E1E1"
                    text = "#111111"
                    text_disabled = "#777777"
            self.setStyleSheet(f"""
                QPushButton {{
                    border: 1px solid transparent;
                    background-color: {bg};
                    border-radius: 6px;
                    padding: 1px 8px;
                    color: {text};
                }}
                QPushButton:hover {{
                    background-color: {bg_hover};
                }}
                QPushButton:pressed {{
                    background-color: {bg_pressed};
                }}
                QPushButton:disabled {{
                    background-color: {bg_disabled};
                    color: {text_disabled};
                }}
            """)
        finally:
            self._updating_style = False

    def changeEvent(self, event):
        super().changeEvent(event)
        if self._updating_style:
            return
        if event.type() in (
            QEvent.Type.PaletteChange,
            QEvent.Type.ApplicationPaletteChange,
        ):
            self.update_theme()

    def set_alert(self, enabled):
        enabled = bool(enabled)
        if self._alert == enabled:
            return
        self._alert = enabled
        self.update_theme()

# ---- Broccoli 418 lines 16039-16120 ----

class WhiteButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._theme_updating = False
        self.setAutoDefault(False)
        self.setFixedHeight(30)
        self.apply_default_style()
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)

    def apply_default_style(self):
        if self._theme_updating:
            return
        self._theme_updating = True
        try:
            dark = bool(getattr(self, '_force_dark', False)) or is_dark_theme(app)
            if dark:
                self.setStyleSheet("""
                    QPushButton {
                        background-color: #3A3A3A;
                        color: #F2F2F7;
                        border: 1px solid #4A4B4F;
                        border-radius: 15px;
                        font-size: 13px;
                        padding: 5px 20px;
                    }
                    QPushButton:hover {
                        background-color: #454547;
                    }
                    QPushButton:pressed {
                        background-color: #323234;
                    }
                    QPushButton:disabled {
                        background-color: #2E2E30;
                        color: #8E8E93;
                        border: 1px solid #3A3A3D;
                    }
                """)
            else:
                self.setStyleSheet("""
                    QPushButton {
                        background-color: white;
                        color: #444;
                        border: none;
                        border-radius: 15px;
                        font-size: 13px;
                        padding: 5px 20px;
                    }
                    QPushButton:hover {
                        background-color: #f5f5f5;
                    }
                    QPushButton:pressed {
                        background-color: #ececec;
                    }
                    QPushButton:disabled {
                        background-color: #f2f2f2;
                        color: #9a9a9a;
                    }
                """)
        finally:
            self._theme_updating = False

    def changeEvent(self, event):
        super().changeEvent(event)
        if self._theme_updating:
            return
        # An owner that painted a custom state onto this button (e.g. the Settings
        # save button's dirty-red) sets _pinned_stylesheet. Without this guard the
        # palette-change this stylesheet swap ITSELF triggers would immediately
        # revert the button to the default look — the red survived only one event
        # loop cycle, so the dirty highlight was never visible.
        if getattr(self, '_pinned_stylesheet', False):
            return
        if event.type() in (
            QEvent.Type.PaletteChange,
            QEvent.Type.ApplicationPaletteChange,
        ):
            self.apply_default_style()

# ---- Broccoli 418 lines 16123-16230 ----

class BroccoliMessageDialog(QDialog):
    def __init__(self,
                 title: str,
                 message: str,
                 button_text: str = 'OK',
                 parent=None,
                 buttons: list[str] | None = None,
                 default_button_text: str | None = None,
                 size: QSize | None = None,
                 force_dark: bool = False,
                 approval: bool = False):
        super().__init__(parent)
        self._theme_updating = False
        self._force_dark = bool(force_dark)
        self._panel_margin = 16
        # a notice stands in for the system alert; an approval / a prompt is a dialog
        self._panel_radius = APPROVAL_DIALOG_SMOOTH_RADIUS if approval else NOTICE_SMOOTH_RADIUS
        self.selected_button = ''
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        dialog_size = size if isinstance(size, QSize) else QSize(420, 178)
        self.setFixedSize(dialog_size)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(34, 30, 34, 30)
        root_layout.setSpacing(10)

        self.title_lbl = QLabel(str(title or ''), self)
        self.message_lbl = QLabel(str(message or ''), self)
        self.message_lbl.setWordWrap(True)
        self.message_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        root_layout.addWidget(self.title_lbl)
        root_layout.addWidget(self.message_lbl, 1)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 8, 0, 0)
        button_row.setSpacing(6)
        button_row.addStretch()
        if button_text == 'OK':
            # translate only the built-in default; explicit labels pass through
            button_text = _tr('OK')
        labels = [str(item) for item in (buttons or [button_text]) if str(item).strip()]
        if not labels:
            labels = [_tr('OK')]
        self._dialog_buttons = []
        default_label = str(default_button_text or labels[0])
        for label in labels:
            button = MacNormalButton(label, self, always_dark=self._force_dark)
            button.setFixedWidth(max(84, button.sizeHint().width()))
            button.clicked.connect(lambda _checked=False, chosen=label: self._choose_button(chosen))
            if label == default_label:
                self.setFocusProxy(button)
                button.setFocus()
            self._dialog_buttons.append(button)
            button_row.addWidget(button)
        root_layout.addLayout(button_row)

        self._apply_theme()

    def _choose_button(self, label: str):
        self.selected_button = str(label or '')
        self.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        dark = self._force_dark or is_dark_theme(app)
        panel_rect = QRectF(
            self._panel_margin,
            self._panel_margin,
            self.width() - self._panel_margin * 2,
            self.height() - self._panel_margin * 2,
        )
        bg_path = smooth_round_rect_path(panel_rect, self._panel_radius)
        if not getattr(self, '_liquid_glass_active', False):   # 液态玻璃时由系统玻璃当底
            painter.fillPath(bg_path, QColor('#2D2D2D' if dark else '#FFFFFF'))
            painter.setPen(QPen(QColor('#3A3A3A' if dark else '#ECECEC'), 1))
            painter.drawPath(bg_path)
        painter.end()

    def _apply_theme(self):
        if self._theme_updating:
            return
        self._theme_updating = True
        dark = self._force_dark or is_dark_theme(app)
        try:
            self.title_lbl.setStyleSheet(
                f'font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; '
                f'font-size: 14px; font-weight: 600; color: {"#F2F2F7" if dark else "#20242B"};'
            )
            self.message_lbl.setStyleSheet(
                f'font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; '
                f'font-size: 13px; color: {"#C6CBD4" if dark else "#4A4F58"};'
            )
            for button in getattr(self, '_dialog_buttons', []):
                button.update_theme()
            self.update()
        finally:
            self._theme_updating = False

    def changeEvent(self, event):
        super().changeEvent(event)
        if self._theme_updating:
            return
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.ApplicationPaletteChange):
            self._apply_theme()

# ---- Broccoli 418 lines 16270-16295 ----

def _center_broccoli_dialog(dialog: QDialog, parent=None):
    dialog.adjustSize()
    parent_widget = parent if isinstance(parent, QWidget) else QApplication.activeWindow()
    if parent_widget is None:
        parent_geometry = QApplication.primaryScreen().availableGeometry()
    elif parent_widget.isWindow():
        parent_geometry = parent_widget.frameGeometry()
    else:
        # A panel inside the main window (e.g. History → Rename…): its frameGeometry() is in
        # its parent's coordinates, so the dialog used to open near the screen's top-left.
        parent_geometry = QRect(parent_widget.mapToGlobal(QPoint(0, 0)), parent_widget.size())
    dialog_geometry = dialog.frameGeometry()
    dialog_geometry.moveCenter(parent_geometry.center())
    # Keep the whole dialog on a screen. The parent can be partly or fully off-screen (the
    # main window tucked against a screen edge leaves only a 2 pt sliver), and a dialog
    # centred on it would then open where nobody can see it.
    screen = QGuiApplication.screenAt(parent_geometry.center())
    if screen is None and parent_widget is not None:
        screen = parent_widget.screen()
    screen = screen or QGuiApplication.primaryScreen()
    if screen is not None:
        bounds = screen.availableGeometry()
        left = max(bounds.left(), min(dialog_geometry.left(), bounds.right() - dialog_geometry.width() + 1))
        top = max(bounds.top(), min(dialog_geometry.top(), bounds.bottom() - dialog_geometry.height() + 1))
        dialog_geometry.moveTo(left, top)
    dialog.move(dialog_geometry.topLeft())

# ---- Broccoli 418 lines 16342-16342 ----

NATIVE_ALERTS_ENABLED = os.environ.get('BROCCOLI_NATIVE_ALERTS', '1') != '0'

# ---- Broccoli 418 lines 16345-16346 ----

def native_alerts_available() -> bool:
    return bool(NATIVE_ALERTS_ENABLED and liquid_glass_available())

# ---- Broccoli 418 lines 16349-16357 ----

def native_alert_plan(labels, default_label=None):
    """(button order for NSAlert — default first, so Return picks it —, the Esc button or None)."""
    labels = [str(label) for label in (labels or []) if str(label).strip()]
    if not labels:
        labels = [_tr('OK')]
    default = default_label if default_label in labels else labels[0]
    order = [default] + [label for label in labels if label != default]
    escape = next((label for label in order[1:] if label in native_alert_cancel_labels()), None)
    return order, escape

# ---- Broccoli 418 lines 16360-16361 ----

def native_alert_cancel_labels() -> set:
    return {_tr('Cancel'), _tr('Deny'), _tr('No'), 'Cancel', 'Deny', 'No'}

# ---- Broccoli 418 lines 16364-16393 ----

def _native_alert_origin(window, parent):
    """Where an alert goes: centred over the window it was asked from and inside it (runModal
    puts it in the middle of the screen, often far from Broccoli). None — leave it there —
    when that window is hidden or tucked against a screen edge."""
    top = parent.window() if isinstance(parent, QWidget) else None
    if top is None or not top.isVisible() or not top.testAttribute(Qt.WidgetAttribute.WA_WState_Created):
        return None
    owner = objc.objc_object(c_void_p=int(top.winId())).window()   # read only
    if owner is None:
        return None
    frame = owner.frame()
    screen = owner.screen() or AppKit.NSScreen.mainScreen()
    visible = screen.visibleFrame() if screen is not None else frame
    # the part of the window that is on the screen
    left = max(frame.origin.x, visible.origin.x)
    bottom = max(frame.origin.y, visible.origin.y)
    right = min(frame.origin.x + frame.size.width, visible.origin.x + visible.size.width)
    top_y = min(frame.origin.y + frame.size.height, visible.origin.y + visible.size.height)
    if right - left < 120 or top_y - bottom < 120:
        return None
    size = window.frame().size
    x = (left + right - size.width) / 2.0
    y = (bottom + top_y - size.height) / 2.0
    if size.width <= right - left:
        x = min(max(x, left), right - size.width)
    if size.height <= top_y - bottom:
        y = min(max(y, bottom), top_y - size.height)
    x = min(max(x, visible.origin.x), visible.origin.x + visible.size.width - size.width)
    y = min(max(y, visible.origin.y), visible.origin.y + visible.size.height - size.height)
    return x, y

# ---- Broccoli 418 lines 16396-16469 ----

def run_native_alert(parent, title: str, message: str, labels, default_label=None, force_dark: bool = False):
    """Show an app-modal NSAlert; return the clicked label (None if it closed otherwise)."""
    order, escape = native_alert_plan(labels, default_label)
    alert = AppKit.NSAlert.alloc().init()
    alert.setMessageText_(str(title or ''))
    alert.setInformativeText_(str(message or ''))
    for label in order:
        alert.addButtonWithTitle_(label)
    buttons = list(alert.buttons())
    if escape is not None:
        buttons[order.index(escape)].setKeyEquivalent_('\x1b')
    window = alert.window()
    if force_dark:
        window.setAppearance_(_ns_appearance(True))
    alert.layout()
    # Stay above Broccoli's always-on-top windows: Qt puts those at the modal-panel level
    # (8) too, and the main window raises itself now and then. runModal resets the
    # alert's level when it starts, so the level is raised from inside the modal loop.
    level = int(getattr(AppKit, 'NSModalPanelWindowLevel', 8))
    for top in [parent.window() if isinstance(parent, QWidget) else None, *QApplication.topLevelWidgets()]:
        try:
            if top is not None and top.isVisible() and top.testAttribute(Qt.WidgetAttribute.WA_WState_Created):
                parent_window = objc.objc_object(c_void_p=int(top.winId())).window()
                if parent_window is not None:
                    level = max(level, int(parent_window.level()))
        except Exception:
            continue
    window.setLevel_(level + 1)
    # Raspberry (2026-11-19, "Show on all Spaces"): an alert asked from a window that is on every Space
    # / over a full-screen app opens there too — these marks are per window, not inherited
    try:
        top = parent.window() if isinstance(parent, QWidget) else None
        if top is not None and top.isVisible() and top.testAttribute(Qt.WidgetAttribute.WA_WState_Created):
            owner_window = objc.objc_object(c_void_p=int(top.winId())).window()
            space_bits = (int(getattr(AppKit, 'NSWindowCollectionBehaviorCanJoinAllSpaces', 1 << 0))
                          | int(getattr(AppKit, 'NSWindowCollectionBehaviorFullScreenAuxiliary', 1 << 8)))
            if owner_window is not None:
                behavior = int(window.collectionBehavior())
                wanted = (behavior & ~space_bits) | (int(owner_window.collectionBehavior()) & space_bits)
                if wanted != behavior:
                    window.setCollectionBehavior_(wanted)
    except Exception:
        pass
    keep = []
    if BroccoliRunLoopCallback is not None:
        # runModal also centres the alert on the screen when it starts; it is moved over the
        # window it was asked from in the same first pass, hidden until it is there.
        window.setAlphaValue_(0.0)

        def first_pass():
            try:
                window.setLevel_(level + 1)
                origin = _native_alert_origin(window, parent)
                if origin is not None:
                    window.setFrameOrigin_(origin)
            except Exception:
                logging.exception('Placing the alert over its window failed.')
            finally:
                window.setAlphaValue_(1.0)

        target = BroccoliRunLoopCallback.alloc().initWithCallback_(first_pass)
        timer = AppKit.NSTimer.timerWithTimeInterval_target_selector_userInfo_repeats_(0.0, target, 'fire:', None, False)
        AppKit.NSRunLoop.currentRunLoop().addTimer_forMode_(timer, AppKit.NSModalPanelRunLoopMode)
        keep.append((target, timer))
    monitor = None
    if escape is None and order[0] in native_alert_cancel_labels():
        # Cancel is the default (Return) button, and a button holds one key only: Esc picks it too
        # (a destructive question — Settings › delete history — must never go on with Esc).
        def escape_to_default(event):
            try:
                if int(event.keyCode()) == 53 and event.window() == window:
                    buttons[0].performClick_(None)
                    return None
            except Exception:
                pass
            return event
        try:
            monitor = AppKit.NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
                int(getattr(AppKit, 'NSEventMaskKeyDown', 1 << 10)), escape_to_default)
        except Exception:
            monitor = None
    try:
        index = int(alert.runModal()) - int(getattr(AppKit, 'NSAlertFirstButtonReturn', 1000))
    finally:
        if monitor is not None:
            AppKit.NSEvent.removeMonitor_(monitor)
    for _target, timer in keep:
        timer.invalidate()
    return order[index] if 0 <= index < len(order) else None

# ---- Broccoli 418 lines 16472-16482 ----

def show_broccoli_message(parent, title: str, message: str, button_text: str = 'OK', force_dark: bool = False):
    if native_alerts_available():
        label = _tr('OK') if button_text == 'OK' else button_text
        try:
            return run_native_alert(parent, title, message, [label], label, force_dark) or button_text
        except Exception:
            logging.exception('Native alert failed; using the Broccoli dialog.')
    dialog = BroccoliMessageDialog(title, message, button_text, parent, force_dark=force_dark)
    _center_broccoli_dialog(dialog, parent)
    dialog.exec()
    return dialog.selected_button or button_text

# ---- Broccoli 418 lines 16485-16494 ----

def approval_window_width(parent, preferred: int = 640, minimum: int = 420) -> int:
    """An approval window (its 16 px shadow margin included) a little narrower than the main
    window it is asked over — the terminal approval's rule, shared by the others."""
    try:
        top = parent.window() if isinstance(parent, QWidget) else None
        host = getattr(top, 'qw3', None) or top
        width = int(host.width()) if host is not None else 0
    except Exception:
        width = 0
    return max(minimum, min(int(preferred), width - 32)) if width > 0 else int(preferred)

# ---- Broccoli 418 lines 16497-16532 ----

def ask_broccoli_message(parent,
                         title: str,
                         message: str,
                         buttons: list[str],
                         default_button_text: str | None = None,
                         size: QSize | None = None,
                         force_dark: bool = False,
                         approval: bool = False,
                         escape_button_text: str | None = None) -> str:
    """approval=True: an approval with details (the MCP tool request) — shown as a Broccoli
    approval dialog like the terminal / computer-use ones, not as the system alert (that is
    for notices and quick questions). escape_button_text: what Esc / closing the dialog means
    (for an approval its "Deny"; without it the default button was returned)."""
    if native_alerts_available() and not approval:
        try:
            chosen = run_native_alert(parent, title, message, buttons, default_button_text, force_dark)
            return chosen or (default_button_text or (buttons[0] if buttons else ''))
        except Exception:
            logging.exception('Native alert failed; using the Broccoli dialog.')
    if approval and isinstance(size, QSize):
        size = QSize(approval_window_width(parent, size.width()), size.height())
    dialog = BroccoliMessageDialog(
        title,
        message,
        parent=parent,
        buttons=buttons,
        default_button_text=default_button_text,
        size=size,
        force_dark=force_dark,
        approval=approval,
    )
    _center_broccoli_dialog(dialog, parent)
    dialog.exec()
    if not dialog.selected_button and escape_button_text:
        return escape_button_text
    return dialog.selected_button or (default_button_text or (buttons[0] if buttons else ''))

# ---- Broccoli 418 lines 17016-17017 ----

NATIVE_TITLEBAR_HEIGHT = 40           # the compact title bar; window content starts below it
NATIVE_TITLEBAR_TOOLBAR_ID = 'BroccoliNativeTitlebar'

# ---- Broccoli 418 lines 17022-17038 ----

def native_titlebar_window_flags(kind=Qt.WindowType.Window, *, zoom=False, stays_on_top=False):
    """Qt window flags for a window with the system's traffic lights (use with apply_native_titlebar).
    Only macOS gives a transparent title bar the content reaches under; on any other platform —
    including the offscreen one the tests run on, which would add a 2-pt fake frame — the window
    stays frameless, as these windows were before."""
    on_mac = QGuiApplication.platformName() == 'cocoa'
    if on_mac:
        flags = (kind | Qt.WindowType.ExpandedClientAreaHint | Qt.WindowType.NoTitleBarBackgroundHint
                 | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint
                 | Qt.WindowType.WindowCloseButtonHint)
        if zoom:
            flags |= Qt.WindowType.WindowMaximizeButtonHint
    else:
        flags = kind | Qt.WindowType.FramelessWindowHint
    if stays_on_top:
        flags |= Qt.WindowType.WindowStaysOnTopHint
    return flags

# ---- Broccoli 418 lines 17041-17079 ----

def apply_native_titlebar(widget, normal_size_buttons=False, fixed_buttons=False) -> bool:
    """Give `widget`'s own NSWindow the compact transparent title bar. Idempotent: run it before every
    show, so a native window Qt rebuilt (the always-on-top switch) gets it again.
    normal_size_buttons: a Qt.Tool window is a utility panel, whose system buttons are the small 10-pt
    kind — take that style off so they are the regular 14. fixed_buttons: also take 'miniaturizable'
    and 'resizable' off, so the system itself shows yellow and green greyed (changing the style drops
    the greying Qt applied)."""
    if sys.platform != 'darwin' or AppKit is None or objc is None:
        return False
    window = _broccoli_own_ns_window(widget)
    if window is None:
        return False
    try:
        if normal_size_buttons or fixed_buttons:
            mask = int(window.styleMask())
            wanted = mask
            if normal_size_buttons:
                wanted &= ~int(getattr(AppKit, 'NSWindowStyleMaskUtilityWindow', 1 << 4))
            if fixed_buttons:
                wanted &= ~(int(getattr(AppKit, 'NSWindowStyleMaskMiniaturizable', 1 << 2))
                            | int(getattr(AppKit, 'NSWindowStyleMaskResizable', 1 << 3)))
            if wanted != mask:
                window.setStyleMask_(wanted)
        toolbar = window.toolbar()
        if toolbar is None or str(toolbar.identifier()) != NATIVE_TITLEBAR_TOOLBAR_ID:
            window.setToolbar_(AppKit.NSToolbar.alloc().initWithIdentifier_(NATIVE_TITLEBAR_TOOLBAR_ID))
        window.setToolbarStyle_(int(getattr(AppKit, 'NSWindowToolbarStyleUnifiedCompact', 4)))
        window.setTitleVisibility_(int(getattr(AppKit, 'NSWindowTitleHidden', 1)))
        window.setTitlebarAppearsTransparent_(True)
        if window.respondsToSelector_('setTitlebarSeparatorStyle:'):
            window.setTitlebarSeparatorStyle_(int(getattr(AppKit, 'NSTitlebarSeparatorStyleNone', 1)))
        if widget.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground):
            # a titled window paints its own background behind the content unless told not to
            window.setOpaque_(False)
            window.setBackgroundColor_(AppKit.NSColor.clearColor())
        return True
    except Exception:
        logging.exception('Native title bar for %s failed.', type(widget).__name__)
        return False

# ---- Broccoli 418 lines 17082-17091 ----

def install_native_traffic_lights(cls, **options):
    """apply_native_titlebar for every window of `cls`, run just before each show (the native window
    exists, but is not on screen yet)."""
    original = cls.showEvent

    def showEvent(self, event, _original=original):
        apply_native_titlebar(self, **options)
        _original(self, event)

    cls.showEvent = showEvent

# ---- Broccoli 418 lines 17835-18046 ----

class DropdownPopup(QWidget):
    item_selected = pyqtSignal(int)

    def __init__(self, parent_button):
        super().__init__(None)
        self.parent_button = parent_button
        self.items = []
        self.current_index = -1
        self.hovered_index = -1
        self.item_height = GLASS_LIST_ROW_H
        self.padding = GLASS_LIST_PAD
        self.scroll_offset = 0
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

    def set_items(self, items):
        self.items = list(items)
        self.scroll_offset = 0
        self.hovered_index = -1
        self._update_size()

    def set_current_index(self, index):
        if 0 <= index < len(self.items):
            self.current_index = index
            self._ensure_index_visible(index)
        else:
            self.current_index = -1
        self.update()

    def _visible_item_capacity(self) -> int:
        return max(1, (self.height() - self.padding * 2) // self.item_height)

    def _max_scroll_offset(self) -> int:
        return max(0, len(self.items) - self._visible_item_capacity())

    def _clamp_scroll_offset(self):
        self.scroll_offset = max(0, min(self.scroll_offset, self._max_scroll_offset()))

    def _ensure_index_visible(self, index: int):
        if not (0 <= index < len(self.items)):
            return
        visible_count = self._visible_item_capacity()
        if index < self.scroll_offset:
            self.scroll_offset = index
        elif index >= self.scroll_offset + visible_count:
            self.scroll_offset = index - visible_count + 1
        self._clamp_scroll_offset()

    def _index_at_y(self, y_pos: float) -> int:
        local_y = y_pos - self.padding
        if local_y < 0:
            return -1
        row = int(local_y // self.item_height)
        index = self.scroll_offset + row
        visible_limit = min(len(self.items), self.scroll_offset + self._visible_item_capacity())
        if index >= visible_limit:
            return -1
        return index

    def _scroll_by(self, steps: int) -> bool:
        if not self.items or steps == 0:
            return False
        previous = self.scroll_offset
        self.scroll_offset = max(0, min(self.scroll_offset + steps, self._max_scroll_offset()))
        return self.scroll_offset != previous

    def _update_size(self):
        if not self.items:
            return
        fm = PyQt6.QtGui.QFontMetrics(glass_list_font(self.font()))
        max_width = self.parent_button.width() if getattr(self.parent_button, '_popup_min_width_to_button', True) else 0
        for item in self.items:
            text_width = fm.horizontalAdvance(str(item)) + GLASS_LIST_TEXT_X + GLASS_LIST_TEXT_RIGHT
            max_width = max(max_width, text_width)
        popup_max_width = getattr(self.parent_button, '_popup_max_width', None)
        try:
            popup_max_width = int(popup_max_width) if popup_max_width is not None else None
        except (TypeError, ValueError):
            popup_max_width = None
        if popup_max_width and popup_max_width > 0:
            min_width = self.parent_button.width() if getattr(self.parent_button, '_popup_min_width_to_button', True) else 96
            max_width = min(max_width, max(min_width, popup_max_width))
        height = len(self.items) * self.item_height + self.padding * 2
        max_height = 320
        if height > max_height:
            height = max_height
        self.setFixedSize(max_width, height)
        self._clamp_scroll_offset()

    def show_above_button(self):
        if not self.items:
            return
        self._update_size()
        no_focus = bool(getattr(self.parent_button, '_popup_no_focus', False))
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, no_focus)
        self.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, no_focus)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus if no_focus else Qt.FocusPolicy.StrongFocus)
        btn_pos = self.parent_button.mapToGlobal(self.parent_button.rect().topLeft())
        # Screen-aware placement (same rule as RankedSelectPopup): pop above the
        # button, but flip below when popping above would overflow the screen top,
        # and clamp x/y into the available screen so a tall list near the top edge
        # never runs off-screen upward.
        screen = QGuiApplication.screenAt(btn_pos) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry() if screen is not None else QRect(0, 0, 1440, 900)
        x = min(max(geo.left() + 4, btn_pos.x()), geo.right() - self.width() - 4)
        y = btn_pos.y() - self.height() - 2
        if y < geo.top() + 4:
            y = btn_pos.y() + self.parent_button.height() + 2
        self.move(int(x), int(max(geo.top() + 4, y)))
        self.show()
        if not no_focus:
            self.activateWindow()
            self.setFocus(Qt.FocusReason.PopupFocusReason)
        app.installEventFilter(self)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        dark = (
            bool(getattr(self.parent_button, '_always_dark', False))
            or bool(getattr(self.parent_button, '_force_dark', False))
            or is_dark_theme(app)
        )
        palette = glass_list_palette(dark)
        if not getattr(self, '_liquid_glass_active', False):   # 液态玻璃时由系统玻璃当底
            paint_glass_list_background(painter, self, dark)
        painter.setFont(glass_list_font(self.font()))
        fm = painter.fontMetrics()

        y = self.padding
        visible_count = self._visible_item_capacity()
        start_index = self.scroll_offset
        end_index = min(len(self.items), start_index + visible_count)
        for i in range(start_index, end_index):
            item = self.items[i]
            hovered = i == self.hovered_index
            if hovered:   # like a system menu: blue row, white text, ✓ on the current choice
                paint_glass_list_highlight(painter, glass_list_highlight_rect(self.width(), y), dark)
            color = palette['on_accent'] if hovered else palette['text']
            if i == self.current_index:
                paint_glass_list_check(painter, y, color)
            painter.setPen(color)
            text_rect = QRectF(GLASS_LIST_TEXT_X, y, self.width() - GLASS_LIST_TEXT_X - GLASS_LIST_TEXT_RIGHT, self.item_height)
            visible_text = fm.elidedText(str(item), Qt.TextElideMode.ElideRight, max(24, int(text_rect.width())))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, visible_text)
            y += self.item_height
            if y > self.height() - self.padding:
                break

    def mouseMoveEvent(self, event):
        index = self._index_at_y(event.position().y())
        if 0 <= index < len(self.items):
            if self.hovered_index != index:
                self.hovered_index = index
                self.update()
        elif self.hovered_index != -1:
            self.hovered_index = -1
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            index = self._index_at_y(event.position().y())
            if 0 <= index < len(self.items):
                self.current_index = index
                self.item_selected.emit(index)
                self.hide()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta == 0:
            event.ignore()
            return
        steps = max(1, abs(delta) // 120)
        direction = -steps if delta > 0 else steps
        if self._scroll_by(direction):
            self.update()
            event.accept()
            return
        event.ignore()

    def leaveEvent(self, event):
        self.hovered_index = -1
        self.update()

    def focusOutEvent(self, event):
        if not bool(getattr(self.parent_button, '_popup_no_focus', False)):
            self.hide()

    def hideEvent(self, event):
        try:
            app.removeEventFilter(self)
        except Exception:
            pass
        super().hideEvent(event)

    def eventFilter(self, obj, event):
        if self.isVisible() and event.type() == QEvent.Type.MouseButtonPress:
            try:
                global_pos = event.globalPosition().toPoint()
            except Exception:
                try:
                    global_pos = event.globalPos()
                except Exception:
                    global_pos = None
            if global_pos is not None:
                popup_rect = QRect(self.mapToGlobal(QPoint(0, 0)), self.size())
                button_rect = QRect(self.parent_button.mapToGlobal(QPoint(0, 0)), self.parent_button.size())
                if not popup_rect.contains(global_pos) and not button_rect.contains(global_pos):
                    self.hide()
        return super().eventFilter(obj, event)

# ---- Broccoli 418 lines 18049-18347 ----

class DropdownButton(QPushButton):
    currentIndexChanged = pyqtSignal(int)

    def __init__(self, parent=None, always_dark=False, compact_light=False, height=None):
        super().__init__(parent)
        self.setAutoDefault(False)
        # The white glass capsule is 30 high; one in the row of a glass search takes the
        # search's height (GLASS_SEARCH_HEIGHT), never the other way round (style book 5.2).
        self._capsule_height = int(height or 30)
        self._items = []
        self._item_data = []
        self._current_index = -1
        self._always_dark = bool(always_dark)
        self._compact_light = bool(compact_light)
        self._enabled = True
        self._signals_blocked = False
        self._updating_style = False
        self._placeholder = ''
        self._popup_min_width_to_button = True
        self._popup_max_width = None
        self._popup = DropdownPopup(self)
        self._popup.item_selected.connect(self._on_item_selected)
        self.clicked.connect(self._show_popup)
        self.setFixedHeight(22 if (always_dark or compact_light) else self._capsule_height)
        self._update_style()

    def _update_style(self):
        if self._updating_style:
            return
        self._updating_style = True
        dark = self._always_dark or bool(getattr(self, '_force_dark', False)) or is_dark_theme(app)
        try:
            if self._enabled:
                if dark:
                    bg = "#404145"
                    bg_hover = "#4A4B4F"
                    bg_pressed = "#343538"
                    text = "#FFFFFF"
                    if self._compact_light:
                        radius = 6
                        padding = "1px 8px"
                    else:
                        radius = self._capsule_height // 2
                        padding = "5px 20px"
                else:
                    if self._compact_light:
                        bg = "#E7E7E7"
                        bg_hover = "#EEEEEE"
                        bg_pressed = "#DCDCDC"
                        text = "#111111"
                        radius = 6
                        padding = "1px 8px"
                    else:
                        bg = "#FFFFFF"
                        bg_hover = "#F5F5F5"
                        bg_pressed = "#ECECEC"
                        text = "#444444"
                        radius = self._capsule_height // 2
                        padding = "5px 20px"
            else:
                if dark:
                    bg = "#2F3033"
                    bg_hover = "#2F3033"
                    bg_pressed = "#2F3033"
                    text = "#777777"
                    if self._compact_light:
                        radius = 6
                        padding = "1px 8px"
                    else:
                        radius = self._capsule_height // 2
                        padding = "5px 20px"
                else:
                    if self._compact_light:
                        bg = "#E1E1E1"
                        bg_hover = "#E1E1E1"
                        bg_pressed = "#E1E1E1"
                        text = "#777777"
                        radius = 6
                        padding = "1px 8px"
                    else:
                        bg = "#F2F2F2"
                        bg_hover = "#F2F2F2"
                        bg_pressed = "#F2F2F2"
                        text = "#9A9A9A"
                        radius = self._capsule_height // 2
                        padding = "5px 20px"

            self.setStyleSheet(f"""
                QPushButton {{
                    border: 1px solid transparent;
                    background-color: {bg};
                    border-radius: {radius}px;
                    padding: {padding};
                    color: {text};
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: {bg_hover};
                }}
                QPushButton:pressed {{
                    background-color: {bg_pressed};
                }}
                QPushButton::menu-indicator {{
                    width: 0px;
                }}
            """)
        finally:
            self._updating_style = False

    def changeEvent(self, event):
        super().changeEvent(event)
        if self._updating_style:
            return
        if event.type() in (
            QEvent.Type.PaletteChange,
            QEvent.Type.ApplicationPaletteChange,
        ):
            self._update_style()
            if self._popup.isVisible():
                self._popup.update()

    def _show_popup(self):
        if not self._enabled or not self._items:
            return
        if self._popup.isVisible():
            self._popup.hide()
            return
        if self._show_native_menu():
            return
        self._popup.set_items(self._items)
        self._popup.set_current_index(self._current_index)
        self._popup.show_above_button()

    def _show_native_menu(self) -> bool:
        """The system pop-up menu (Liquid Glass, native rows and shadow, ✓ on the current
        choice, which sits on the button like a pop-up button's). False → the Qt list."""
        if not NATIVE_DROPDOWNS_ENABLED:
            return False
        menu = QMenu(self)
        actions = []
        for index, text in enumerate(self._items):
            action = menu.addAction(str(text).replace('&', '&&'))
            action.setCheckable(True)
            action.setChecked(index == self._current_index)
            actions.append(action)
        current = actions[self._current_index] if 0 <= self._current_index < len(actions) else None
        anchor = self.mapToGlobal(QPoint(0, 0)) if current is not None else self.mapToGlobal(QPoint(0, self.height() + 4))
        dark = bool(getattr(self, '_always_dark', False) or getattr(self, '_force_dark', False))
        try:
            handled, chosen = exec_native_qmenu(menu, anchor, presentation='dropdown', positioning_action=current,
                                                min_width=self.width(), dark=dark or None)
        finally:
            menu.deleteLater()
        if not handled:
            return False
        if chosen is not None and chosen in actions:
            self._on_item_selected(actions.index(chosen))
        return True

    def _on_item_selected(self, index):
        if index != self._current_index:
            self._current_index = index
            self._update_text()
            if not self._signals_blocked:
                self.currentIndexChanged.emit(index)

    def _update_text(self):
        if 0 <= self._current_index < len(self._items):
            full_text = str(self._items[self._current_index])
            fm = self.fontMetrics()
            available_width = max(24, self.width() - (20 if self._compact_light else 44))
            self.setText(fm.elidedText(full_text, Qt.TextElideMode.ElideRight, available_width))
        else:
            self.setText(self._placeholder)
        if getattr(self, '_fit_current_text', False) and self.currentText() != getattr(self, '_fit_hint_text', None):
            self._fit_hint_text = self.currentText()
            self.updateGeometry()   # another choice: ask the row for its width

    def setFitToCurrentText(self, enabled: bool):
        """Ask for the width of the whole current choice and give way (eliding) only when the
        row is short of room. Without it the width came from the already elided text, so a
        button that started narrow stayed narrow (the reader's languages showed "C…" → "E…")."""
        self._fit_current_text = bool(enabled)
        self.setSizePolicy(QSizePolicy.Policy.Preferred if enabled else QSizePolicy.Policy.Minimum,
                           self.sizePolicy().verticalPolicy())
        self._fit_hint_text = None
        self._update_text()

    def sizeHint(self):
        hint = super().sizeHint()
        if getattr(self, '_fit_current_text', False):
            full = self.currentText() or self._placeholder
            hint.setWidth(max(hint.width(), self.fontMetrics().horizontalAdvance(full) + 24))   # _update_text keeps 20 spare
        return hint

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        if getattr(self, '_fit_current_text', False):
            hint.setWidth(min(hint.width(), 48))   # may give way down to a couple of letters + "…"
        return hint

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_text()

    def showEvent(self, event):
        super().showEvent(event)
        self._update_text()

    def addItem(self, text, data=None):
        self._items.append(text)
        self._item_data.append(data)
        if self._current_index == -1:
            self.setCurrentIndex(0)

    def addItems(self, texts):
        for text in texts:
            self._items.append(text)
            self._item_data.append(None)
        if self._current_index == -1 and self._items:
            self.setCurrentIndex(0)

    def clear(self):
        self._items = []
        self._item_data = []
        self._current_index = -1
        self._update_text()

    def count(self):
        return len(self._items)

    def currentIndex(self):
        return self._current_index

    def setCurrentIndex(self, index):
        if 0 <= index < len(self._items):
            old_index = self._current_index
            self._current_index = index
            self._update_text()
            if old_index != index and not self._signals_blocked:
                self.currentIndexChanged.emit(index)
        elif index == -1 or not self._items:
            self._current_index = -1
            self._update_text()

    def currentText(self):
        if 0 <= self._current_index < len(self._items):
            return str(self._items[self._current_index])
        return ''

    def itemText(self, index):
        if 0 <= index < len(self._items):
            return str(self._items[index])
        return ''

    def itemData(self, index):
        if 0 <= index < len(self._item_data):
            return self._item_data[index]
        return None

    def setItemData(self, index, data):
        if 0 <= index < len(self._item_data):
            self._item_data[index] = data

    def currentData(self):
        return self.itemData(self._current_index)

    def findData(self, data):
        for index, item_data in enumerate(self._item_data):
            if item_data == data:
                return index
        return -1

    def setEnabled(self, enabled):
        self._enabled = enabled
        super().setEnabled(enabled)
        self._update_style()

    def blockSignals(self, block):
        self._signals_blocked = block
        return super().blockSignals(block)

    def setPlaceholderText(self, text):
        self._placeholder = str(text or '')
        if self._current_index == -1:
            self._update_text()

    def setPopupMinWidthToButton(self, enabled: bool):
        self._popup_min_width_to_button = bool(enabled)

    def setPopupMaxWidth(self, width):
        try:
            width = int(width)
        except (TypeError, ValueError):
            width = None
        self._popup_max_width = width if width and width > 0 else None
        if self._popup.isVisible():
            self._popup._update_size()
            self._popup.update()

# ---- Broccoli 418 lines 48143-48373 ----

class PillNavBar(QWidget):
    """
    药丸形状导航栏：
    - Bar 本体：白色/浅色背景，带底部 drop shadow
    - Tab 之间竖线分隔符
    - 选中 pill：深灰色，覆盖两侧分隔符，平滑滑动动画
    - 无选中 pill 的阴影；pill 直接在 paintEvent 绘制，透明按钮露出 pill
    """
    tab_changed = pyqtSignal(int)

    def __init__(self, tabs, initial_index=0, parent=None):
        super().__init__(parent)
        self._tabs = tabs
        self._current = initial_index
        self._buttons = []
        self._theme = 'light'
        self._pill_rect = QRect()
        self._anim_start = QRect()
        self._anim_end = QRect()
        self._anim_progress = 1.0
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(14)  # ≈ 70fps
        self._anim_timer.timeout.connect(self._anim_tick)
        self._setup()

    # ── 动画 ──────────────────────────────────────────────
    def _ease_out_cubic(self, t):
        return 1.0 - (1.0 - t) ** 3

    def _lerp_rect(self, r1, r2, t):
        def li(a, b): return int(round(a + (b - a) * t))
        return QRect(li(r1.x(), r2.x()), li(r1.y(), r2.y()),
                     li(r1.width(), r2.width()), li(r1.height(), r2.height()))

    def _anim_tick(self):
        self._anim_progress = min(1.0, self._anim_progress + 0.065)
        t = self._ease_out_cubic(self._anim_progress)
        self._pill_rect = self._lerp_rect(self._anim_start, self._anim_end, t)
        self.update()
        if self._anim_progress >= 1.0:
            self._anim_timer.stop()

    # ── 初始化 ──────────────────────────────────────────
    def _setup(self):
        # 高度 46px：外框 + 足够的 pill 高度
        self.setFixedHeight(36)

        # Bar 本身的底部 drop shadow（通过 QGraphicsDropShadowEffect）
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)
        for i, label in enumerate(self._tabs):
            btn = QPushButton(label, self)
            btn.setFlat(True)
            btn.setFixedHeight(32)  # fill bar height (36 - top_margin 2 - bottom_margin 2)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, idx=i: self.select(idx))
            layout.addWidget(btn)
            self._buttons.append(btn)
        self._apply_button_styles()

    def _theme_palette(self):
        if self._theme == 'dark':
            return {
                'bar_bg': '#2D2D2D',
                'pill_bg': '#3A3A3A',
                'active_text': '#FFFFFF',
                'inactive_text': '#B8B8B8',
                'separator': QColor(255, 255, 255, 36),
            }
        return {
            'bar_bg': '#FFFFFF',
            'pill_bg': '#CBCBCB',
            'active_text': '#111111',
            'inactive_text': '#777777',
            'separator': QColor(0, 0, 0, 35),
        }

    def set_theme(self, theme):
        theme = 'dark' if theme == 'dark' else 'light'
        if self._theme == theme:
            return
        self._theme = theme
        self._apply_button_styles()
        self.update()
        helper = getattr(self, '_broccoli_inwindow_glass', None)
        if helper is not None:
            helper.sync()

    def _apply_button_styles(self):
        palette = self._theme_palette()
        if getattr(self, '_liquid_glass_active', False):
            # The labels are drawn into the glass by the bar itself (see paintEvent).
            for btn in self._buttons:
                btn.setStyleSheet("QPushButton { background: transparent; border: none; color: transparent; padding: 0; }")
            return
        for i, btn in enumerate(self._buttons):
            if i == self._current:
                btn.setStyleSheet(
                    "QPushButton { background: transparent; border: none; "
                    f"color: {palette['active_text']}; font-size: 13px; font-weight: 600; padding: 0; }} "
                    "QPushButton:pressed { background: transparent; border: none; }"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { background: transparent; border: none; "
                    f"color: {palette['inactive_text']}; font-size: 13px; font-weight: normal; padding: 0; }} "
                    "QPushButton:pressed { background: transparent; border: none; }"
                )

    def _pill_rect_for(self, idx):
        """
        pill 宽度覆盖整个按钮（0 横向 inset），确保覆盖两侧竖线分隔符。
        纵向 inset = 2px，生成饱满的药丸形状。
        """
        if 0 <= idx < len(self._buttons):
            btn = self._buttons[idx]
            # x: 与按钮左边对齐（覆盖左侧分隔符）
            # width: 按钮宽 +1（确保覆盖右侧分隔符）
            return QRect(btn.x() + 1, btn.y() + 1, btn.width() - 2, btn.height() - 2)
        return QRect()

    # ── 首次显示定位 ──────────────────────────────────────
    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._init_pill)
        if getattr(self, '_broccoli_inwindow_glass', None) is None and inwindow_glass_available():
            QTimer.singleShot(0, self._attach_liquid_glass)

    # ── liquid glass (InWindowLiquidGlass): glass bar; the pill + labels are drawn into it ──
    def _attach_liquid_glass(self):
        if getattr(self, '_broccoli_inwindow_glass', None) is None and self.isVisible():
            attach_inwindow_liquid_glass(self, lambda w=self: w.height() / 2.0, lambda w=self: w._theme == 'dark')

    def _on_inwindow_glass_changed(self, active: bool):
        effect = self.graphicsEffect()
        if effect is not None:
            effect.setEnabled(not active)   # the glass brings its own shadow
        self._apply_button_styles()

    def _init_pill(self):
        r = self._pill_rect_for(self._current)
        if r.isValid():
            self._pill_rect = r
            self.update()

    # ── 切换 Tab ──────────────────────────────────────────
    def select(self, index):
        if index == self._current:
            return
        self._current = index
        self._apply_button_styles()
        target = self._pill_rect_for(index)
        if target.isValid():
            self._anim_start = QRect(self._pill_rect) if self._pill_rect.isValid() else target
            self._anim_end = target
            self._anim_progress = 0.0
            self._anim_timer.start()
        self.tab_changed.emit(index)

    # ── 绘制 ─────────────────────────────────────────────
    def _paint_glass_foreground(self, painter, palette):
        dark = self._theme == 'dark'
        if self._buttons:
            painter.setPen(QPen(palette['separator'], 1))
            for i in range(1, len(self._buttons)):
                if i == self._current or i == self._current + 1:
                    continue
                x = self._buttons[i].x()
                painter.drawLine(x, 9, x, self.height() - 9)
        if self._pill_rect.isValid():
            pill_rr = self._pill_rect.height() / 2.0
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 46) if dark else QColor(0, 0, 0, 30)))
            painter.drawRoundedRect(self._pill_rect, pill_rr, pill_rr)
        for i, btn in enumerate(self._buttons):
            font = QFont(btn.font())
            font.setPixelSize(13)
            font.setWeight(QFont.Weight.DemiBold if i == self._current else QFont.Weight.Normal)
            painter.setFont(font)
            painter.setPen(QColor(palette['active_text'] if i == self._current else palette['inactive_text']))
            painter.drawText(btn.geometry(), Qt.AlignmentFlag.AlignCenter, btn.text())

    def paintEvent(self, event):
        if getattr(self, '_liquid_glass_active', False):
            if not getattr(self, '_glass_foreground_pass', False):
                return   # pill + labels live in the glass
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            self._paint_glass_foreground(painter, self._theme_palette())
            painter.end()
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        palette = self._theme_palette()

        outer_r = self.height() / 2.0

        # 1. Bar 本体
        painter.setBrush(QBrush(QColor(palette['bar_bg'])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRect(0, 0, self.width(), self.height()), outer_r, outer_r)

        # 2. 竖线分隔符（先于 pill 绘制，pill 会覆盖相邻分隔符）
        if self._buttons:
            sep_pen = QPen(palette['separator'])
            sep_pen.setWidth(1)
            painter.setPen(sep_pen)
            for i in range(1, len(self._buttons)):
                # suppress separators on both sides of the selected pill
                if i == self._current or i == self._current + 1:
                    continue
                x = self._buttons[i].x()
                painter.drawLine(x, 9, x, self.height() - 9)

        # 3. 选中的深灰药丸（后于分隔符绘制 → 覆盖紧邻的竖线）
        if self._pill_rect.isValid():
            pill_rr = self._pill_rect.height() / 2.0
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(palette['pill_bg'])))
            painter.drawRoundedRect(self._pill_rect, pill_rr, pill_rr)

        painter.end()

# ---- Broccoli 418 lines 70925-70925 ----

_EDGE_HINT_SYMBOLS = {}

# ---- Broccoli 418 lines 70928-70972 ----

def edge_hint_symbol_pixmap(name: str, color, size: int = 14, dpr: float = 2.0):
    """A system line icon (SF Symbol) in one colour, fitted into size × size points, or None (no AppKit,
    an unknown name). Drawn once per name / colour."""
    key = (str(name or ''), QColor(color).rgba(), int(size), float(dpr))
    if key in _EDGE_HINT_SYMBOLS:
        return _EDGE_HINT_SYMBOLS[key]
    pixmap = None
    if AppKit is not None and name:
        try:
            image = AppKit.NSImage.imageWithSystemSymbolName_accessibilityDescription_(str(name), None)
            if image is not None:
                config = AppKit.NSImageSymbolConfiguration.configurationWithPointSize_weight_(
                    float(size), float(getattr(AppKit, 'NSFontWeightRegular', 0.0)))
                image = image.imageWithSymbolConfiguration_(config) or image
                width, height = float(image.size().width), float(image.size().height)
                scale = min(size / max(1.0, width), size / max(1.0, height))
                drawn_w, drawn_h = width * scale, height * scale
                pixels = int(round(size * dpr))
                rep = AppKit.NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
                    None, pixels, pixels, 8, 4, True, False, AppKit.NSDeviceRGBColorSpace, 0, 0)
                rep.setSize_(AppKit.NSMakeSize(size, size))
                AppKit.NSGraphicsContext.saveGraphicsState()
                try:
                    AppKit.NSGraphicsContext.setCurrentContext_(
                        AppKit.NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep))
                    image.drawInRect_(AppKit.NSMakeRect((size - drawn_w) / 2.0, (size - drawn_h) / 2.0, drawn_w, drawn_h))
                finally:
                    AppKit.NSGraphicsContext.restoreGraphicsState()
                png = rep.representationUsingType_properties_(AppKit.NSBitmapImageFileTypePNG, {})
                glyph = QImage.fromData(bytes(png))
                if not glyph.isNull():
                    pixmap = QPixmap(pixels, pixels)
                    pixmap.setDevicePixelRatio(dpr)
                    pixmap.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(pixmap)
                    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                    painter.drawImage(QRectF(0, 0, size, size), glyph)
                    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                    painter.fillRect(QRectF(0, 0, size, size), QColor(color))
                    painter.end()
        except Exception:
            logging.exception('Drawing the system icon %s failed.', name)
            pixmap = None
    _EDGE_HINT_SYMBOLS[key] = pixmap
    return pixmap


# ==== Strawberry: additions (not in Broccoli) ===================================================

_THEME_CALLBACKS = []


def on_theme_changed(callback):
    """Strawberry: run callback(dark: bool) whenever macOS switches light / dark (style book 5.8:
    both sets, following the system live). Broccoli calls its global apply_theme() instead."""
    _THEME_CALLBACKS.append(callback)
    return callback


def _run_theme_callbacks():
    dark = is_dark_theme(app)
    for callback in list(_THEME_CALLBACKS):
        try:
            callback(dark)
        except Exception:
            logging.exception('theme callback failed')


if NSObject is not None and objc is not None:
    class StrawberryThemeObserver(NSObject):
        def themeChanged_(self, notification):
            # the notification arrives before the system palette settles: run on the next turn
            QTimer.singleShot(0, _run_theme_callbacks)
else:
    StrawberryThemeObserver = None


_THEME_OBSERVER = []


def install_theme_observer():
    if StrawberryThemeObserver is None or NSDistributedNotificationCenter is None or _THEME_OBSERVER:
        return None
    try:
        observer = StrawberryThemeObserver.alloc().init()
        NSDistributedNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            observer, NSSelectorFromString("themeChanged:"), "AppleInterfaceThemeChangedNotification", None)
        _THEME_OBSERVER.append(observer)
        return observer
    except Exception:
        return None


class StrawberryDropdown(DropdownButton):
    """Strawberry: DropdownButton with the few QComboBox calls Strawberry's code makes that the
    Broccoli button does not have (findText, showPopup, setEditable / setMaxVisibleItems no-ops)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # a click opens the list through showPopup(), so an owner's own showPopup (one that refreshes
        # the items first, like QComboBox subclasses do) still runs
        self.clicked.disconnect(self._show_popup)
        self.clicked.connect(lambda _checked=False: self.showPopup())

    def findText(self, text, flags=None):
        for index, item in enumerate(self._items):
            if str(item) == str(text):
                return index
        return -1

    def showPopup(self):
        self._show_popup()

    def setEditable(self, editable):
        pass

    def setMaxVisibleItems(self, count):
        pass
