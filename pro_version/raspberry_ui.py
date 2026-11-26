# -*- coding: utf-8 -*-
"""Raspberry's Liquid Glass UI (2026-11-16) — the parts built on glass_kit.py.

UI STYLE BOOK: /Users/ryanshen/Documents/A-workingfilewithp3.11/UI_STYLEBOOK_macOS27.md (section 5.13)
Ryan 2026-11-16: "raspberry 也需要像其他的软件一样换上彻底的液态玻璃的主题". He chose:
 - the full-screen backdrop stays a blurred wallpaper, but the CLEAN wallpaper (not whatever windows
   happen to be on the screen);
 - a group in the grid = a real glass tile; the open group = a glass panel floating ON the icons (they
   stay, dimmed); the page dots sit in a glass capsule.

The launcher window is transparent, so all its glass lies in the layer UNDER the Qt content (the kit's
child glass), with the blurred wallpaper at the very bottom of that layer; texts and icons are ordinary
Qt widgets drawn above the glass.
Import this module AFTER the QApplication exists.
"""
import os
import sys
import time
import logging
import weakref
import threading
from ctypes import c_void_p
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QHBoxLayout, QVBoxLayout, QDialog, QLineEdit
from PyQt6.QtCore import (Qt, QRect, QRectF, QPoint, QPointF, QSize, QTimer, QEvent, QObject, pyqtSignal,
                          QVariantAnimation, QEasingCurve, QCoreApplication)
from PyQt6.QtGui import (QColor, QPainter, QPainterPath, QPen, QFont, QImage, QPixmap, QPalette)

app = QApplication.instance()
if app is None:
    raise RuntimeError('raspberry_ui: create the QApplication before importing this module')

import glass_kit
from glass_kit import (is_dark_theme, MacNormalButton, WhiteButton, glass_corner_radius,
                       install_window_liquid_glass, install_native_traffic_lights, show_broccoli_message,
                       ask_broccoli_message, liquid_glass_available, smooth_round_rect_path,
                       broccoli_blurred_backdrop, MAIN_WINDOW_SMOOTH_RADIUS, NATIVE_TITLEBAR_HEIGHT)

AppKit = glass_kit.AppKit
objc = glass_kit.objc


def _tr(text: str) -> str:
    return QCoreApplication.translate('Raspberry', text)


# ── numbers (style book 5.13) ──────────────────────────────────────────────────────────────────────────
BACKDROP_WASH = 0.45            # the veil over the blurred wallpaper: white (light) / black (dark)
BACKDROP_WORK_WIDTH = 480       # the wallpaper is blurred at this width, then stretched over the screen
BACKDROP_BLUR = 0.016           # blur sigma as a share of the picture's width (≈ 40 pt on a 2560 screen)
SEARCH_HEIGHT = glass_kit.GLASS_SEARCH_HEIGHT   # 36 (5.5 A)
TILE_SIZE = 80                  # a group in the grid: a glass tile of this size …
TILE_RADIUS = 18                # … with an app icon's corner
PANEL_GLASS_RADIUS = 26         # the open group: the largest tier (Ryan 2026-11-16: "这个分组的圆角不够"; was 16)
GROUP_OPEN_MS = 340             # the group grows out of its tile …
GROUP_CLOSE_MS = 260            # … and shrinks back into it
PANEL_SHADOW_BLUR = 34.0        # Broccoli's floating panel shadow
PANEL_SHADOW_DY = 10.0
PANEL_SHADOW_PAD = 60.0
SCRIM_ALPHA_LIGHT = 72          # the icons behind an open group: black 28 % …
SCRIM_ALPHA_DARK = 140          # … / 55 %  (Ryan 2026-11-16: heavier; in dark the panel did not stand out)
# … while what lies right under the panel's own glass is NOT darkened like that: the panel is a lighter
# slab on the darker field (light: a touch of white; dark: only a little black) — light or dark
PANEL_UNDER_LIGHT = (255, 255, 255, 26)
PANEL_UNDER_DARK = (0, 0, 0, 50)
SCRIM_FADE_MS = 200
SCRIM_BLUR = 22.0               # what is behind an open group is blurred this much (pt) — Ryan 2026-11-16
SCRIM_PICTURE_WIDTH = 1024      # … on a picture this wide, stretched over the window
SCRIM_PLATE_LIGHT = 70          # a group's glass tile in that picture: white at this alpha …
SCRIM_PLATE_DARK = 34           # … (dark)
DOCK_GAP = 20                   # the page dots stay this far above a Dock that is showing
CONTENT_MARGIN_SIDE = 80        # the launcher's content: left / right …
CONTENT_MARGIN_TOP = 60
CONTENT_MARGIN_BOTTOM = 60      # … and bottom (no Dock in the way)
DOTS_HEIGHT = 30
DOTS_DOT = 8
DOTS_STEP = 20
DOTS_PAD = 14
FOCUS_RING_RADIUS = 24

_THEME_HOOKS = []                 # callback(dark) after the application stylesheet changed
_UNDER_GLASS = weakref.WeakSet()  # every child glass of the launcher (told light / dark explicitly)


def ui_palette(dark=None) -> dict:
    if dark is None:
        dark = is_dark_theme(app)
    if dark:
        return {'dark': True, 'body': QColor('#2D2D2D'), 'panel': QColor('#2D2D2D'), 'text': '#F2F2F7',
                'secondary': '#8E8E93', 'border': QColor('#4A4B4F'), 'capsule': QColor(58, 58, 58, 178)}
    return {'dark': False, 'body': QColor('#FFFFFF'), 'panel': QColor('#FFFFFF'), 'text': '#20242B',
            'secondary': '#8E8E93', 'border': QColor('#ECECEC'), 'capsule': QColor(255, 255, 255, 178)}


def accent_color() -> QColor:
    """The system accent colour (style book 5.8: never a fixed blue)."""
    return QColor(app.palette().color(QPalette.ColorRole.Accent))


def focus_ring_qss() -> str:
    """The ring around the icon chosen with the keyboard."""
    return 'border: 1.5px solid %s; border-radius: %dpx; padding: 0px;' % (accent_color().name(), FOCUS_RING_RADIUS)


def native_layer_available() -> bool:
    try:
        return bool(sys.platform == 'darwin' and AppKit is not None and objc is not None
                    and QApplication.platformName() == 'cocoa' and glass_kit.BroccoliGlassContainerView is not None)
    except Exception:
        return False


def _layer_container(top):
    """The view under a window's Qt content where its glass and pictures live (the kit's), or None."""
    if not native_layer_available():
        return None
    try:
        layer = glass_kit._window_glass_layer(top)
        return layer.view if layer is not None else None
    except Exception:
        return None


def _picture_view():
    """A plain layer-backed view that shows one picture stretched over itself; never takes the mouse
    (it lies under the Qt content anyway)."""
    view = AppKit.NSView.alloc().initWithFrame_(AppKit.NSMakeRect(0, 0, 1, 1))
    view.setWantsLayer_(True)
    view.layer().setContentsGravity_('resize')
    return view


def _set_picture(view, image: QImage, keep):
    """Show `image` in a picture view. `keep` (a list) holds what the layer needs alive."""
    contents = glass_kit._qimage_to_layer_contents(image, 1.0)
    if contents is None:
        ns_image = glass_kit._qimage_to_nsimage(image, QSize(image.width(), image.height()))
        contents = ns_image
    keep[:] = [contents]
    view.layer().setContents_(contents)


# ── the clean desktop wallpaper ────────────────────────────────────────────────────────────────────────
# Ryan 2026-11-16: "理论上最好是可以拿到一个干净的桌面壁纸然后保持全屏模糊壁纸，现在是直接在任何地方盖上去".
# Two ways to get it, neither ever asks for a permission:
#  1. with Screen Recording access already granted: a picture of the system's wallpaper layer alone
#     (every kind of wallpaper, exactly as it is on the screen);
#  2. otherwise the wallpaper's file, laid out the way the system does (fill / fit / stretch / centre).
# Neither works → the old look: the system blurs whatever is behind the window.
_WALLPAPER_OWNERS = ('Dock', 'WindowManager', 'Wallpaper', 'Window Server', 'loginwindow')


# PyObjC looks a function up the first time it is used, and that first look-up is not safe from two
# threads at once (seen 2026-11-22: KeyError 'CGImageGetWidth', and a crash, when the wallpaper thread
# and the main thread met there). So every name the wallpaper thread uses is looked up once, here, on
# the main thread (the first call is screen_capture_allowed, before any wallpaper thread starts).
_QUARTZ_NAMES = (
    'CGBitmapContextCreate', 'CGBitmapContextCreateImage', 'CGColorSpaceCreateWithName', 'CGContextDrawImage',
    'CGContextSetInterpolationQuality', 'CGDataProviderCopyData', 'CGImageGetBytesPerRow',
    'CGImageGetDataProvider', 'CGImageGetHeight', 'CGImageGetWidth', 'CGImageSourceCopyPropertiesAtIndex',
    'CGImageSourceCreateThumbnailAtIndex', 'CGImageSourceCreateWithURL', 'CGPreflightScreenCaptureAccess',
    'CGRectMake', 'CGWindowLevelForKey', 'CGWindowListCopyWindowInfo', 'CGWindowListCreateImageFromArray',
    'kCGBitmapByteOrder32Little', 'kCGColorSpaceSRGB', 'kCGDesktopWindowLevelKey', 'kCGImageAlphaNoneSkipFirst',
    'kCGImageSourceCreateThumbnailFromImageAlways', 'kCGImageSourceCreateThumbnailWithTransform',
    'kCGImageSourceThumbnailMaxPixelSize', 'kCGInterpolationHigh', 'kCGNullWindowID',
    'kCGWindowImageNominalResolution', 'kCGWindowListOptionOnScreenOnly')
_QUARTZ_LOCK = threading.Lock()
_QUARTZ_READY = []


def _quartz():
    try:
        import Quartz
    except Exception:
        return None
    if not _QUARTZ_READY:
        with _QUARTZ_LOCK:
            if not _QUARTZ_READY:
                for name in _QUARTZ_NAMES:
                    try:
                        getattr(Quartz, name)
                    except Exception:
                        pass
                try:
                    if AppKit is not None:
                        AppKit.NSURL     # used by the wallpaper thread too
                except Exception:
                    pass
                _QUARTZ_READY.append(True)
    return Quartz


def screen_capture_allowed() -> bool:
    """True only when this app may already record the screen. Asking is never done here."""
    quartz = _quartz()
    try:
        return bool(quartz is not None and quartz.CGPreflightScreenCaptureAccess())
    except Exception:
        return False


def _cgimage_to_qimage(cgimage, width: int, height: int):
    """A CGImage drawn into a width × height QImage (RGB32)."""
    quartz = _quartz()
    space = quartz.CGColorSpaceCreateWithName(quartz.kCGColorSpaceSRGB)
    context = quartz.CGBitmapContextCreate(None, width, height, 8, width * 4, space,
                                           quartz.kCGImageAlphaNoneSkipFirst | quartz.kCGBitmapByteOrder32Little)
    if context is None:
        return None
    quartz.CGContextSetInterpolationQuality(context, quartz.kCGInterpolationHigh)
    quartz.CGContextDrawImage(context, quartz.CGRectMake(0, 0, width, height), cgimage)
    small = quartz.CGBitmapContextCreateImage(context)
    data = quartz.CGDataProviderCopyData(quartz.CGImageGetDataProvider(small))
    raw = bytes(data)
    stride = int(quartz.CGImageGetBytesPerRow(small))
    return QImage(raw, width, height, stride, QImage.Format.Format_RGB32).copy()


def _nearly_black(image: QImage) -> bool:
    probe = image.scaled(8, 8, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    for y in range(probe.height()):
        for x in range(probe.width()):
            colour = QColor(probe.pixel(x, y))
            if max(colour.red(), colour.green(), colour.blue()) > 6:
                return False
    return True


def capture_wallpaper(geometry: QRect, width: int = BACKDROP_WORK_WIDTH):
    """The system's wallpaper layer of the screen at `geometry` (global points), without any window,
    desktop icon or desktop widget: → QImage (width wide) or None. Only called with access granted."""
    quartz = _quartz()
    if quartz is None:
        return None
    try:
        infos = quartz.CGWindowListCopyWindowInfo(quartz.kCGWindowListOptionOnScreenOnly, quartz.kCGNullWindowID)
        desk = quartz.CGWindowLevelForKey(quartz.kCGDesktopWindowLevelKey)
        ids = []
        for info in infos or []:
            if int(info.get('kCGWindowLayer', 0)) > desk or info.get('kCGWindowOwnerName') not in _WALLPAPER_OWNERS:
                continue
            bounds = info.get('kCGWindowBounds') or {}
            rect = QRect(int(bounds.get('X', 0)), int(bounds.get('Y', 0)),
                         int(bounds.get('Width', 0)), int(bounds.get('Height', 0)))
            if rect.intersects(geometry):
                ids.append(int(info.get('kCGWindowNumber')))
        if not ids:
            return None
        cgimage = quartz.CGWindowListCreateImageFromArray(
            quartz.CGRectMake(geometry.x(), geometry.y(), geometry.width(), geometry.height()), ids,
            quartz.kCGWindowImageNominalResolution)
        if cgimage is None or not quartz.CGImageGetWidth(cgimage):
            return None
        height = max(1, round(width * geometry.height() / max(1, geometry.width())))
        image = _cgimage_to_qimage(cgimage, width, height)
        if image is None or _nearly_black(image):
            return None
        return image
    except Exception:
        logging.exception('Taking the picture of the wallpaper failed.')
        return None


def wallpaper_file_info(geometry: QRect):
    """(path, mtime, scaling, clipping, fill colour as (r, g, b)) of the wallpaper of the screen at
    `geometry`, or None. Main thread (asks the workspace)."""
    if AppKit is None:
        return None
    try:
        target = None
        for screen in AppKit.NSScreen.screens():
            frame = screen.frame()
            if (int(frame.size.width) == geometry.width() and int(frame.size.height) == geometry.height()
                    and int(frame.origin.x) == geometry.x()):
                target = screen
                break
        if target is None:
            target = AppKit.NSScreen.mainScreen()
        workspace = AppKit.NSWorkspace.sharedWorkspace()
        url = workspace.desktopImageURLForScreen_(target)
        if url is None or not url.isFileURL():
            return None
        path = str(url.path())
        if not os.path.isfile(path):
            return None
        options = workspace.desktopImageOptionsForScreen_(target) or {}
        scaling = options.get('NSWorkspaceDesktopImageScalingKey')
        clipping = options.get('NSWorkspaceDesktopImageAllowClippingKey')
        fill = options.get('NSWorkspaceDesktopImageFillColorKey')
        rgb = (0, 0, 0)
        if fill is not None:
            try:
                converted = fill.colorUsingColorSpace_(AppKit.NSColorSpace.sRGBColorSpace())
                rgb = (int(converted.redComponent() * 255), int(converted.greenComponent() * 255),
                       int(converted.blueComponent() * 255))
            except Exception:
                rgb = (0, 0, 0)
        return (path, os.path.getmtime(path), 3 if scaling is None else int(scaling),
                True if clipping is None else bool(clipping), rgb)
    except Exception:
        logging.exception('Reading the wallpaper setting failed.')
        return None


def wallpaper_from_file(info, geometry: QRect, width: int = BACKDROP_WORK_WIDTH):
    """The wallpaper's file laid out like the system does: → QImage (width wide) or None."""
    quartz = _quartz()
    if quartz is None or info is None:
        return None
    try:
        path, _mtime, scaling, clipping, rgb = info
        url = AppKit.NSURL.fileURLWithPath_(path)
        source = quartz.CGImageSourceCreateWithURL(url, None)
        if source is None:
            return None
        properties = quartz.CGImageSourceCopyPropertiesAtIndex(source, 0, None) or {}
        full_width = float(properties.get('PixelWidth', 0) or 0)
        thumb = quartz.CGImageSourceCreateThumbnailAtIndex(source, 0, {
            quartz.kCGImageSourceCreateThumbnailFromImageAlways: True,
            quartz.kCGImageSourceCreateThumbnailWithTransform: True,
            quartz.kCGImageSourceThumbnailMaxPixelSize: width * 2})
        if thumb is None:
            return None
        picture_w, picture_h = int(quartz.CGImageGetWidth(thumb)), int(quartz.CGImageGetHeight(thumb))
        if not picture_w or not picture_h:
            return None
        picture = _cgimage_to_qimage(thumb, picture_w, picture_h)
        if picture is None:
            return None
        height = max(1, round(width * geometry.height() / max(1, geometry.width())))
        canvas = QImage(width, height, QImage.Format.Format_RGB32)
        canvas.fill(QColor(*rgb))
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if scaling == 1:                                   # stretch
            target = QRectF(0, 0, width, height)
        elif scaling == 2:                                 # centre at its own size
            scale = (width / max(1.0, float(geometry.width()))) * ((full_width or picture_w) / picture_w)
            draw_w, draw_h = picture_w * scale / 2.0, picture_h * scale / 2.0   # file pixels ≈ 2 per point
            target = QRectF((width - draw_w) / 2.0, (height - draw_h) / 2.0, draw_w, draw_h)
        else:                                              # proportional: fill (clipping) or fit
            ratio = (max if clipping else min)(width / picture_w, height / picture_h)
            draw_w, draw_h = picture_w * ratio, picture_h * ratio
            target = QRectF((width - draw_w) / 2.0, (height - draw_h) / 2.0, draw_w, draw_h)
        painter.drawImage(target, picture)
        painter.end()
        return canvas
    except Exception:
        logging.exception('Reading the wallpaper file failed.')
        return None


def blur_wallpaper(image: QImage):
    """The wallpaper blurred (and a little more vivid, as the system's own materials are)."""
    try:
        from PIL import Image, ImageFilter, ImageEnhance
        image = image.convertToFormat(QImage.Format.Format_RGB32)
        bits = image.constBits()
        bits.setsize(image.sizeInBytes())
        picture = Image.frombuffer('RGBA', (image.width(), image.height()), bytes(bits), 'raw', 'BGRA',
                                   image.bytesPerLine(), 1).convert('RGB')
        picture = picture.filter(ImageFilter.GaussianBlur(max(2.0, image.width() * BACKDROP_BLUR)))
        picture = ImageEnhance.Color(picture).enhance(1.2)
        raw = picture.tobytes('raw', 'RGB')
        return QImage(raw, picture.width, picture.height, picture.width * 3, QImage.Format.Format_RGB888).copy()
    except Exception:
        logging.exception('Blurring the wallpaper failed.')
        return None


def wash_backdrop(blurred: QImage, dark: bool) -> QImage:
    """The veil that keeps the names under the icons readable: white (light) / black (dark)."""
    image = blurred.convertToFormat(QImage.Format.Format_RGB32)
    painter = QPainter(image)
    veil = QColor(0, 0, 0) if dark else QColor(255, 255, 255)
    veil.setAlphaF(BACKDROP_WASH)
    painter.fillRect(image.rect(), veil)
    painter.end()
    return image


class LauncherBackdrop(QObject):
    """What fills the launcher's window behind everything: the blurred clean wallpaper of the screen
    it is on (a picture at the bottom of the window's glass layer; without that layer the window paints
    the same picture itself), or — wallpaper not to be had / switched off — the system's blur of
    whatever is behind the window. A screen's picture is kept; every show uses the kept one at once and
    fetches a fresh one in the background."""

    changed = pyqtSignal()
    _fetched = pyqtSignal(object, object, object)   # screen key, source key, blurred QImage or None

    def __init__(self, window):
        super().__init__(window)
        self._window = window
        self.clean = True
        self._kept = {}          # screen key → (source key, blurred QImage)
        self._screen_key = None
        self._geometry = None
        self._washed = None      # the picture shown now (blurred + veil), or None
        self._picture = None
        self._picture_keep = []
        self._effect = None
        self._busy = set()
        self._fetched.connect(self._on_fetched)

    # ── what to show ──
    @staticmethod
    def _key_of(geometry: QRect) -> tuple:
        return (geometry.x(), geometry.y(), geometry.width(), geometry.height())

    def set_clean(self, on: bool):
        self.clean = bool(on)
        self._compose()

    def image(self):
        """The picture to paint when there is no native layer (None = paint the plain body colour)."""
        return self._washed

    def shows_wallpaper(self) -> bool:
        return self._washed is not None

    def prepare(self, geometry: QRect):
        """Call when the window is about to show on the screen at `geometry`: the kept picture of that
        screen is used at once and a fresh one is fetched in the background; only a screen never seen
        before is fetched here and now."""
        self._geometry = QRect(geometry)
        self._screen_key = self._key_of(geometry)
        if self.clean and self._screen_key not in self._kept:
            source_key, blurred = self._fetch(QRect(geometry), self._source_plan(geometry))
            if blurred is not None:
                self._kept[self._screen_key] = (source_key, blurred)
        elif self.clean:
            self.refresh_async(geometry)
        self._compose()

    def warm(self, geometry: QRect):
        """Fetch a screen's wallpaper in the background before the window is ever shown there."""
        if self.clean and self._key_of(geometry) not in self._kept:
            self.refresh_async(geometry)

    def _source_plan(self, geometry: QRect):
        """('capture', None) with Screen Recording access (the file is only looked up should the picture
        fail), else ('file', info) or ('none', None)."""
        if screen_capture_allowed():
            return ('capture', None)
        info = wallpaper_file_info(geometry)
        return ('file', info) if info is not None else ('none', None)

    @staticmethod
    def _fetch(geometry: QRect, plan):
        kind, info = plan
        image = None
        if kind == 'capture':
            image = capture_wallpaper(geometry)
            if image is None:
                info = wallpaper_file_info(geometry)
                if info is not None:
                    image = wallpaper_from_file(info, geometry)
        elif kind == 'file':
            image = wallpaper_from_file(info, geometry)
        if image is None:
            return plan, None
        return plan, blur_wallpaper(image)

    def refresh_async(self, geometry=None):
        """Fetch a screen's wallpaper again off the main thread; the picture changes when it differs."""
        geometry = QRect(geometry) if geometry is not None else (QRect(self._geometry) if self._geometry else None)
        if geometry is None:
            return
        key = self._key_of(geometry)
        if key in self._busy:
            return
        plan = self._source_plan(geometry)
        kept = self._kept.get(key)
        if plan[0] == 'file' and kept is not None and kept[0] == plan:
            return   # the same file, unchanged
        if plan[0] == 'none':
            return
        self._busy.add(key)

        def work():
            try:
                source_key, blurred = self._fetch(geometry, plan)
            except Exception:
                source_key, blurred = plan, None
            try:
                self._fetched.emit(key, source_key, blurred)
            except RuntimeError:
                pass

        threading.Thread(target=work, name='raspberry-wallpaper', daemon=True).start()

    def _on_fetched(self, key, source_key, blurred):
        self._busy.discard(key)
        if blurred is None:
            return
        old = self._kept.get(key)
        self._kept[key] = (source_key, blurred)
        if key == self._screen_key and (old is None or old[1] != blurred):
            self._compose()

    def retheme(self):
        self._compose()

    # ── showing it ──
    def _compose(self):
        kept = self._kept.get(self._screen_key) if self.clean else None
        self._washed = wash_backdrop(kept[1], is_dark_theme(app)) if kept is not None else None
        self._apply_native()
        self.changed.emit()

    def native(self) -> bool:
        return self._picture is not None or self._effect is not None

    def _apply_native(self):
        container = _layer_container(self._window)
        if container is None:
            return
        try:
            below = int(getattr(AppKit, 'NSWindowBelow', -1))
            sizable = int(getattr(AppKit, 'NSViewWidthSizable', 2)) | int(getattr(AppKit, 'NSViewHeightSizable', 16))
            if self._effect is None:
                effect = AppKit.NSVisualEffectView.alloc().initWithFrame_(container.bounds())
                effect.setMaterial_(int(getattr(AppKit, 'NSVisualEffectMaterialPopover', 6)))
                effect.setBlendingMode_(int(getattr(AppKit, 'NSVisualEffectBlendingModeBehindWindow', 0)))
                effect.setState_(int(getattr(AppKit, 'NSVisualEffectStateActive', 1)))
                effect.setAutoresizingMask_(sizable)
                self._effect = effect
            if self._picture is None:
                picture = _picture_view()
                picture.setAutoresizingMask_(sizable)
                self._picture = picture
            for view in (self._picture, self._effect):   # the effect ends up lowest
                if view.superview() is not container:
                    if view.superview() is not None:
                        view.removeFromSuperview()
                    view.setFrame_(container.bounds())
                    container.addSubview_positioned_relativeTo_(view, below, None)
            if self._washed is not None:
                _set_picture(self._picture, self._washed, self._picture_keep)
                self._picture.setHidden_(False)
                self._effect.setHidden_(True)
            else:
                self._picture.setHidden_(True)
                self._effect.setHidden_(False)
        except Exception:
            logging.exception('Showing the launcher backdrop failed.')

    def paint_fallback(self, painter: QPainter, rect: QRect):
        """Without the native layer: the same picture, or the plain body colour."""
        if self.native():
            return
        if self._washed is not None:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawImage(QRectF(rect), self._washed)
        else:
            painter.fillRect(rect, ui_palette()['body'])


# ── the system menu bar, covered while the launcher is up ───────────────────────────────────────────────
# Ryan 2026-11-21: 「主界面把菜单栏整条盖住，像系统自带的启动台那样，打开时完全看不到菜单栏」 — and not by
# making the menu bar slide away. The launcher itself must stay under the Dock (which he keeps), and the
# menu bar is above the Dock, so the launcher cannot simply be lifted: a second, strip-high window with
# the same backdrop lies over the menu bar instead, for as long as the launcher is showing.
class MenuBarCover(QWidget):
    """A strip as high as the menu bar, above it, showing the top of the launcher's backdrop. Follows
    the launcher: its screen, its opacity (the fades), its being shown at all. Never takes the keyboard.
    The mouse on it → it fades away and lets clicks through, so the menu bar (Raspberry's menus, the
    system's icons) is there to use; it comes back a moment after the mouse has left and no menu is
    open (Ryan 2026-11-21: 「鼠标 hover 上去的时候盖住的东西消失」). While it covers, a click on it is
    swallowed (the menu bar under it must not open unseen)."""

    LEVEL = 26          # the menu bar's window is at 24, the Dock at 20
    FOLLOW_MS = 16
    REVEAL_MS = 120     # the fade away / back
    RETURN_MS = 350     # how long after the mouse has left the menu bar it is covered again
    # the menu bar throws a soft shadow on what lies under it (seen 2026-11-21 as a dark line right
    # below the cover, fading out over about 6 points): the cover reaches that much further down
    SHADOW_ROOM = 10

    def __init__(self, launcher, backdrop):
        super().__init__(None)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                            | Qt.WindowType.WindowDoesNotAcceptFocus | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._launcher = launcher
        self._backdrop = backdrop
        self._full = QSize()        # the screen's size: the backdrop is stretched over that, not over the strip
        self._picture = None
        self._effect = None
        self._picture_keep = []
        self._dim_view = None
        self._dim = QColor(0, 0, 0, 0)   # what an open group lays over the launcher (the scrim's colour)
        self._reveal = 0.0          # 0 = covering … 1 = gone (the menu bar shows)
        self._away_since = None     # when the mouse left the revealed menu bar
        self._lets_clicks_through = False
        self._timer = QTimer(self)
        self._timer.setInterval(self.FOLLOW_MS)
        self._timer.timeout.connect(self.follow)
        backdrop.changed.connect(self.refresh)

    @staticmethod
    def strip_of(screen) -> QRect:
        """The menu bar's room on `screen` (empty when the screen shows none)."""
        if screen is None:
            return QRect()
        whole, free = screen.geometry(), screen.availableGeometry()
        return QRect(whole.x(), whole.y(), whole.width(), max(0, free.top() - whole.top()))

    def start(self):
        """The launcher is being shown."""
        self._reveal, self._away_since = 0.0, None
        self.follow()
        self._timer.start()

    def follow(self):
        launcher = self._launcher
        if launcher is None or not launcher.isVisible():
            self._timer.stop()
            if self.isVisible():
                self.hide()
            return
        screen = launcher.screen()
        strip = self.strip_of(screen)
        if strip.height() <= 0:
            if self.isVisible():
                self.hide()
            return
        full = screen.geometry().size()
        area = strip.adjusted(0, 0, 0, self.SHADOW_ROOM)      # the menu bar and its shadow
        moved = self.geometry() != area or full != self._full
        if moved:
            self._full = full
            self.setGeometry(area)
        wanted = self._menu_bar_wanted(strip)
        step = self.FOLLOW_MS / float(self.REVEAL_MS)
        self._reveal = min(1.0, self._reveal + step) if wanted else max(0.0, self._reveal - step)
        self._let_clicks_through(wanted or self._reveal > 0.0)
        opacity = launcher.windowOpacity() * (1.0 - self._reveal)
        if abs(self.windowOpacity() - opacity) > 0.003:
            self.setWindowOpacity(opacity)
        if not self.isVisible():
            self.show()
            self._lift()
            self.refresh()
        elif moved:
            self._pin()
            self.refresh()

    # ── the mouse on the menu bar ──
    def _mouse_pos(self) -> QPoint:
        from PyQt6.QtGui import QCursor
        return QCursor.pos()

    def _buttons_down(self) -> bool:
        return QApplication.mouseButtons() != Qt.MouseButton.NoButton

    def _menu_open(self) -> bool:
        """One of Raspberry's menus in the menu bar is open."""
        try:
            if AppKit is None or QApplication.platformName() != 'cocoa':
                return False
            menu = AppKit.NSApp.mainMenu()
            return menu is not None and menu.highlightedItem() is not None
        except Exception:
            return False

    def _menu_bar_wanted(self, strip: QRect) -> bool:
        """The menu bar is to show: the mouse is on it (not while something is being dragged there),
        or a menu is open, or the mouse has only just left."""
        showing = self._reveal > 0.0
        inside = strip.contains(self._mouse_pos())
        if (inside and (showing or not self._buttons_down())) or (showing and (self._menu_open() or self._buttons_down())):
            self._away_since = None
            return True
        if not showing:
            return False
        now = time.monotonic()
        if self._away_since is None:
            self._away_since = now
        return (now - self._away_since) * 1000.0 < self.RETURN_MS

    def _let_clicks_through(self, through: bool):
        if through == self._lets_clicks_through:
            return
        self._lets_clicks_through = bool(through)
        window = widget_ns_window(self)
        if window is not None:
            try:
                window.setIgnoresMouseEvents_(bool(through))
            except Exception:
                pass

    def lets_clicks_through(self) -> bool:
        return self._lets_clicks_through

    def _lift(self):
        window = widget_ns_window(self)
        if window is None:
            return
        try:
            window.setLevel_(self.LEVEL)
            window.setHidesOnDeactivate_(False)
            window.setHasShadow_(False)
            window.invalidateShadow()
            window.setIgnoresMouseEvents_(bool(self._lets_clicks_through))
            apply_space_behavior(window, all_spaces_enabled())
            self._pin(window)
        except Exception:
            logging.exception('Lifting the menu bar cover failed.')

    def _pin(self, window=None) -> bool:
        """The system puts a window that is shown in the menu bar's room right below the menu bar
        (measured 2026-11-21: the strip came out 39 lower). Its frame is therefore set again by hand,
        in the screen's own coordinates, once it is at its level."""
        window = window if window is not None else widget_ns_window(self)
        screen = window.screen() if window is not None else None
        if window is None or screen is None or self.height() <= 0:
            return False
        try:
            whole = screen.frame()
            want = AppKit.NSMakeRect(whole.origin.x, whole.origin.y + whole.size.height - self.height(),
                                     whole.size.width, self.height())
            now = window.frame()
            if (abs(now.origin.y - want.origin.y) > 0.5 or abs(now.origin.x - want.origin.x) > 0.5
                    or abs(now.size.width - want.size.width) > 0.5 or abs(now.size.height - want.size.height) > 0.5):
                window.setFrame_display_(want, True)
            return True
        except Exception:
            logging.exception('Placing the menu bar cover failed.')
            return False

    def _host_view(self):
        if AppKit is None or objc is None or QApplication.platformName() != 'cocoa':
            return None
        try:
            return objc.objc_object(c_void_p=int(self.winId()))
        except Exception:
            return None

    def picture_frame(self, flipped: bool):
        """Where the full-screen picture sits in the strip so that its top edge is the strip's."""
        height = self._full.height()
        return (0, 0 if flipped else self.height() - height, self._full.width(), height)

    def refresh(self):
        """The same picture as the launcher's (or, without a wallpaper, the system's blur)."""
        self.update()
        host = self._host_view()
        if host is None or not self.isVisible() or self._full.isEmpty():
            return
        try:
            image = self._backdrop.image()
            if self._picture is None:
                self._picture = _picture_view()
                host.addSubview_(self._picture)
            if self._effect is None:
                effect = AppKit.NSVisualEffectView.alloc().initWithFrame_(host.bounds())
                effect.setMaterial_(int(getattr(AppKit, 'NSVisualEffectMaterialPopover', 6)))
                effect.setBlendingMode_(int(getattr(AppKit, 'NSVisualEffectBlendingModeBehindWindow', 0)))
                effect.setState_(int(getattr(AppKit, 'NSVisualEffectStateActive', 1)))
                self._effect = effect
                host.addSubview_(effect)
            if self._dim_view is None:              # added last: above the picture and the blur
                dim = AppKit.NSView.alloc().initWithFrame_(host.bounds())
                dim.setWantsLayer_(True)
                self._dim_view = dim
                host.addSubview_(dim)
            x, y, width, height = self.picture_frame(bool(host.isFlipped()))
            self._picture.setFrame_(AppKit.NSMakeRect(x, y, width, height))
            self._effect.setFrame_(host.bounds())
            self._dim_view.setFrame_(host.bounds())
            self._apply_dim()
            if image is not None:
                _set_picture(self._picture, image, self._picture_keep)
            self._picture.setHidden_(image is None)
            self._effect.setHidden_(image is not None)
        except Exception:
            logging.exception('Showing the menu bar cover failed.')

    def native(self) -> bool:
        return self._picture is not None

    def set_dim(self, colour: QColor):
        """An open group darkens the launcher behind it; the cover gets exactly the same veil (Ryan
        2026-11-21: with a group open the strip stood out bright above the dimmed launcher)."""
        colour = QColor(colour) if colour is not None else QColor(0, 0, 0, 0)
        if colour == self._dim:
            return
        self._dim = colour
        self._apply_dim()
        self.update()

    def dim(self) -> QColor:
        return QColor(self._dim)

    def _apply_dim(self):
        view = self._dim_view
        if view is None:
            return
        try:
            c = self._dim
            view.layer().setBackgroundColor_(
                AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(c.redF(), c.greenF(), c.blueF(), c.alphaF()).CGColor())
            view.setHidden_(c.alpha() == 0)
        except Exception:
            logging.exception('Dimming the menu bar cover failed.')

    def paintEvent(self, event):
        if self.native():
            return
        painter = QPainter(self)
        image = self._backdrop.image()
        if image is not None and not self._full.isEmpty():
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawImage(QRectF(0, 0, self._full.width(), self._full.height()), image)
        else:
            painter.fillRect(self.rect(), ui_palette()['body'])
        if self._dim.alpha() > 0:
            painter.fillRect(self.rect(), self._dim)
        painter.end()

    def mousePressEvent(self, event):
        event.accept()

    def mouseReleaseEvent(self, event):
        event.accept()


# ── glass under a widget of the launcher ───────────────────────────────────────────────────────────────
class UnderGlass(glass_kit.ChildLiquidGlass):
    """System Liquid Glass under a child widget (the kit's child glass: in the window's glass layer,
    under the Qt content), optionally kept inside another widget's rectangle (`clip`: a tile sliding
    out of the grid shows no glass beyond it), told light / dark explicitly."""

    def __init__(self, widget, radius, inset=0.0, clip=None, shadow=None, dark=None):
        self._clip = clip
        self._extra_views = []
        super().__init__(widget, radius, inset=inset, dark=is_dark_theme(app) if dark is None else dark,
                         shadow=shadow)
        _UNDER_GLASS.add(self)

    def _frame(self):
        frame = super()._frame()
        clip = self._clip
        if clip is None:
            return frame
        try:
            origin = clip.mapTo(self._top, QPoint(0, 0))
            rect = QRectF(frame.origin.x, frame.origin.y, frame.size.width, frame.size.height).intersected(
                QRectF(origin.x(), origin.y(), clip.width(), clip.height()))
        except RuntimeError:
            return frame
        if rect.isEmpty():
            return AppKit.NSMakeRect(frame.origin.x, frame.origin.y, 0, 0)
        return AppKit.NSMakeRect(rect.x(), rect.y(), rect.width(), rect.height())

    def set_dark(self, dark: bool):
        try:
            if self.glass is not None:
                self.glass.setAppearance_(glass_kit._ns_appearance(bool(dark)))
        except Exception:
            pass

    def raise_views(self):
        """Bring this glass (and its shadow) above every other glass of the window."""
        self.sync(reorder=True)


def under_glass(widget, radius, inset=0.0, clip=None, shadow=None):
    """UnderGlass for `widget`, or None when glass is not available / failed (the widget then paints
    its own background — style book 1.5: the same shape without glass)."""
    if not liquid_glass_available():
        return None
    existing = getattr(widget, '_broccoli_child_glass', None)
    if existing is not None:
        return existing
    try:
        helper = UnderGlass(widget, radius, inset=inset, clip=clip, shadow=shadow)
    except Exception:
        logging.exception('Glass under %s failed.', type(widget).__name__)
        return None
    widget._broccoli_child_glass = helper
    widget._liquid_glass_active = True
    try:
        host = glass_kit._broccoli_own_ns_window(widget.window())
        if host is not None:
            host.setHasShadow_(False)
    except Exception:
        pass
    widget.update()
    return helper


def glass_active(widget) -> bool:
    return bool(getattr(widget, '_liquid_glass_active', False))


# ── the page dots: one glass capsule ───────────────────────────────────────────────────────────────────
class PageDots(QWidget):
    """The page dots in one glass capsule (style book 5.13): height 30, a dot of 8 per page, 20 apart,
    the current page's dot solid, the others at 30 %. Clicking a dot goes to its page."""

    pageClicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._total = 1
        self._current = 0
        self._step = DOTS_STEP
        self._max_width = 800
        self.setFixedSize(self._width_for(1), DOTS_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _width_for(self, total: int) -> int:
        return DOTS_PAD * 2 + DOTS_DOT + max(0, total - 1) * self._step

    def set_max_width(self, width: int):
        self._max_width = max(DOTS_PAD * 2 + DOTS_DOT, int(width))
        self.set_pages(self._total, self._current)

    def set_pages(self, total: int, current: int):
        total = max(1, int(total))
        self._step = DOTS_STEP
        if self._width_for(total) > self._max_width and total > 1:
            self._step = max(DOTS_DOT + 2, (self._max_width - DOTS_PAD * 2 - DOTS_DOT) // (total - 1))
        self._total, self._current = total, max(0, min(int(current), total - 1))
        self.setFixedSize(self._width_for(total), DOTS_HEIGHT)
        self.update()

    def pages(self):
        return self._total, self._current

    def dot_center(self, index: int) -> QPointF:
        return QPointF(DOTS_PAD + DOTS_DOT / 2.0 + index * self._step, self.height() / 2.0)

    def dot_at(self, x: float) -> int:
        index = round((x - DOTS_PAD - DOTS_DOT / 2.0) / float(self._step))
        return max(0, min(self._total - 1, int(index)))

    def showEvent(self, event):
        super().showEvent(event)
        under_glass(self, DOTS_HEIGHT / 2.0)

    def mousePressEvent(self, event):
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.pageClicked.emit(self.dot_at(event.position().x()))
        event.accept()

    def mouseDoubleClickEvent(self, event):
        event.accept()   # a quick second click on a dot must not close the launcher

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        palette = ui_palette()
        if not glass_active(self):
            painter.setPen(QPen(palette['border'], 1.0))
            painter.setBrush(palette['capsule'])
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), self.height() / 2.0,
                                    self.height() / 2.0)
        painter.setPen(Qt.PenStyle.NoPen)
        for index in range(self._total):
            colour = QColor(palette['text'])
            if index != self._current:
                colour.setAlphaF(0.30)
            painter.setBrush(colour)
            painter.drawEllipse(self.dot_center(index), DOTS_DOT / 2.0, DOTS_DOT / 2.0)
        painter.end()


# ── the Dock ───────────────────────────────────────────────────────────────────────────────────────────
def dock_insets(geometry: QRect) -> tuple:
    """(left, bottom, right): how much of the screen at `geometry` a Dock that is showing takes, in
    points; all 0 when the Dock hides itself. Read from the system at this moment (the screen's visible
    frame), Qt's own copy only as the fallback."""
    try:
        screens = list(AppKit.NSScreen.screens())
        if screens:
            primary_height = float(screens[0].frame().size.height)
            for screen in screens:
                frame = screen.frame()
                top = primary_height - (frame.origin.y + frame.size.height)
                if (abs(frame.origin.x - geometry.x()) > 1 or abs(top - geometry.y()) > 1
                        or abs(frame.size.width - geometry.width()) > 1
                        or abs(frame.size.height - geometry.height()) > 1):
                    continue
                visible = screen.visibleFrame()
                left = visible.origin.x - frame.origin.x
                bottom = visible.origin.y - frame.origin.y
                right = (frame.origin.x + frame.size.width) - (visible.origin.x + visible.size.width)
                return tuple(max(0, int(round(value))) for value in (left, bottom, right))
    except Exception:
        pass
    try:
        for screen in QApplication.screens():
            if screen.geometry() == geometry:
                free = screen.availableGeometry()
                return (max(0, free.left() - geometry.left()), max(0, geometry.bottom() - free.bottom()),
                        max(0, geometry.right() - free.right()))
    except Exception:
        pass
    return (0, 0, 0)


def content_margins(insets) -> tuple:
    """The launcher's content margins (left, top, right, bottom) for these Dock insets: the usual ones,
    or DOCK_GAP beyond the Dock where that is more."""
    left, bottom, right = (max(0, int(value)) for value in insets)
    return (max(CONTENT_MARGIN_SIDE, left + DOCK_GAP if left else 0), CONTENT_MARGIN_TOP,
            max(CONTENT_MARGIN_SIDE, right + DOCK_GAP if right else 0),
            max(CONTENT_MARGIN_BOTTOM, bottom + DOCK_GAP if bottom else 0))


# ── the open group: a glass panel floating on the icons ────────────────────────────────────────────────
def blurred_content(launcher, sources, plates=()):
    """A blurred picture of the launcher's own content (`sources`: the search, the icons, the dots) with a
    clear background — the wallpaper under it is blurred already. `plates`: the glass behind the group — the
    search capsule, the groups' tiles, the dots — as (QRectF in the launcher, corner), drawn as soft white shapes since system glass is not in a widget's
    picture. A small QImage (premultiplied) to stretch over the launcher, or None."""
    size = launcher.size()
    if size.isEmpty():
        return None
    try:
        from PIL import Image, ImageFilter
        image = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        plate = QColor(255, 255, 255, SCRIM_PLATE_DARK if is_dark_theme(app) else SCRIM_PLATE_LIGHT)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(plate)
        for rect, radius in plates:
            radius = min(float(radius), rect.width() / 2.0, rect.height() / 2.0)
            painter.drawRoundedRect(QRectF(rect), radius, radius)
        for widget in sources:
            try:
                if widget.isVisible():
                    widget.render(painter, widget.mapTo(launcher, QPoint(0, 0)),
                                  flags=QWidget.RenderFlag.DrawChildren)
            except RuntimeError:
                continue
        painter.end()
        scale = min(1.0, SCRIM_PICTURE_WIDTH / float(size.width()))
        if scale < 1.0:
            image = image.scaled(max(2, round(size.width() * scale)), max(2, round(size.height() * scale)),
                                 Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        image = image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        bits = image.constBits()
        bits.setsize(image.sizeInBytes())
        # premultiplied colours blur correctly channel by channel
        picture = Image.frombuffer('RGBA', (image.width(), image.height()), bytes(bits), 'raw', 'BGRA',
                                   image.bytesPerLine(), 1)
        picture = picture.filter(ImageFilter.GaussianBlur(max(1.0, SCRIM_BLUR * scale)))
        raw = picture.tobytes('raw', 'BGRA')
        return QImage(raw, picture.width, picture.height, picture.width * 4,
                      QImage.Format.Format_ARGB32_Premultiplied).copy()
    except Exception:
        logging.exception('Blurring what is behind the group failed.')
        return None


class FolderScrim(QWidget):
    """What an open group does to everything behind it (style book 5.13): the icons, the search and the
    dots turn into their blurred picture and get a little darker. This widget lies over them: as it fades
    in it takes their sharp pixels away and puts the blurred ones in their place (the wallpaper under the
    window is untouched). Takes no mouse press of its own (they reach the launcher window, which closes
    the group / the launcher as before) but keeps them from the icons."""

    levelChanged = pyqtSignal(float)

    def __init__(self, parent):
        super().__init__(parent)
        self._level = 0.0
        self._picture = None
        self._fade = QVariantAnimation(self)
        self._fade.setDuration(SCRIM_FADE_MS)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade.valueChanged.connect(self._set_level)
        self._fade.finished.connect(self._on_fade_finished)
        self.hide()

    def colour(self, level=None) -> QColor:
        alpha = SCRIM_ALPHA_DARK if is_dark_theme(app) else SCRIM_ALPHA_LIGHT
        return QColor(0, 0, 0, round(alpha * (self._level if level is None else level)))

    def level(self) -> float:
        return self._level

    def picture(self):
        return self._picture

    def set_picture(self, image):
        """The blurred picture of what is behind (blurred_content), or None: only the dimming."""
        self._picture = image if image is not None and not image.isNull() else None
        self.update()

    def _set_level(self, value):
        self._level = float(value)
        self.update()
        self.levelChanged.emit(self._level)

    def _on_fade_finished(self):
        if self._level <= 0.001:
            self.hide()
            self._picture = None

    def fade_in(self):
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self._fade.stop()
        self._fade.setStartValue(self._level)
        self._fade.setEndValue(1.0)
        self._fade.start()

    def fade_out(self):
        self._fade.stop()
        self._fade.setStartValue(self._level)
        self._fade.setEndValue(0.0)
        self._fade.start()

    def mousePressEvent(self, event):
        event.ignore()

    def mouseReleaseEvent(self, event):
        event.ignore()

    def mouseDoubleClickEvent(self, event):
        event.ignore()

    def paintEvent(self, event):
        if self._level <= 0.0:
            return
        painter = QPainter(self)
        if self._picture is not None:
            level = max(0.0, min(1.0, self._level))
            # sharp × (1 − level) + blurred × level, on what the widgets below have just painted
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
            painter.fillRect(self.rect(), QColor(0, 0, 0, round(255 * (1.0 - level))))
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
            painter.setOpacity(level)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawImage(self.rect(), self._picture)
            painter.setOpacity(1.0)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.fillRect(self.rect(), self.colour())
        painter.end()


class FolderPanelGlass(QObject):
    """The open group's glass (style book 5.13): system glass under the panel, and right under the
    glass a picture of what the launcher shows at the panel's place — the dimmed icons — so the glass
    softens those, while the panel itself cuts its part out of the Qt content. The picture is taken
    once per change of the grid; while the panel grows or shrinks only the part shown changes.
    `picture`: the blurred picture the scrim shows (the glass then lies on exactly what is around it)."""

    def __init__(self, panel, launcher, source_widgets, picture=None):
        super().__init__(panel)
        self._panel = panel
        self._launcher = launcher
        self._sources = list(source_widgets)
        self._clip_view = None
        self._picture = None
        self._picture_keep = []
        self._picture_size = None
        dark = is_dark_theme(app)
        shadow = dict(color=QColor(0, 0, 0, 120 if dark else 45), blur=PANEL_SHADOW_BLUR, dy=PANEL_SHADOW_DY,
                      pad=PANEL_SHADOW_PAD)
        self.glass = under_glass(panel, PANEL_GLASS_RADIUS, shadow=shadow)
        if self.glass is not None:
            # while the panel grows out of / shrinks into its tile the corner goes along (panel_radius)
            self.glass._radius_for = lambda panel=panel: panel_radius(panel)
            # the shadow's picture is drawn point by point for each corner size (≈ 0.14 s): while the
            # panel grows its corner changes every frame → the shadow keeps the open panel's corner
            # (one picture, stretched), and comes in with the panel (set_progress)
            shadow_helper = self.glass.shadow
            if shadow_helper is not None:
                original_update = shadow_helper.update
                shadow_helper.update = lambda frame, _radius, _update=original_update: _update(
                    frame, float(PANEL_GLASS_RADIUS))
                self.glass.sync()
        if self.glass is not None:
            panel.installEventFilter(self)
            self.retake(picture=picture)

    def active(self) -> bool:
        return self.glass is not None

    def set_progress(self, progress):
        """How open the panel is (0 = still the tile): its shadow comes and goes with it."""
        try:
            if self.glass is not None and self.glass.shadow is not None:
                self.glass.shadow.set_opacity(max(0.0, min(1.0, float(progress) * 1.4)))
        except Exception:
            pass

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Type.Move, QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.Hide):
            self._place()
        return False

    def retake(self, scrim_colour=None, picture=None):
        """Take the picture of the launcher's content again (the grid changed). With `picture` (the
        scrim's blurred one) that is what lies under the glass."""
        if self.glass is None:
            return
        launcher = self._launcher
        size = launcher.size()
        if size.isEmpty():
            return
        if scrim_colour is None:
            scrim_colour = QColor(*(PANEL_UNDER_DARK if is_dark_theme(app) else PANEL_UNDER_LIGHT))
        if picture is not None and not picture.isNull():
            image = picture.copy()
            painter = QPainter(image)
            painter.fillRect(image.rect(), scrim_colour)
            painter.end()
        else:
            ratio = max(1.0, float(launcher.devicePixelRatioF()))
            image = QImage(int(size.width() * ratio), int(size.height() * ratio),
                           QImage.Format.Format_ARGB32_Premultiplied)
            image.setDevicePixelRatio(ratio)
            image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(image)
            for widget in self._sources:
                try:
                    if widget.isVisible():
                        widget.render(painter, widget.mapTo(launcher, QPoint(0, 0)),
                                      flags=QWidget.RenderFlag.DrawChildren)
                except RuntimeError:
                    continue
            painter.fillRect(QRect(QPoint(0, 0), size), scrim_colour)
            painter.end()
        self._ensure_views()
        if self._picture is None:
            return
        image.setDevicePixelRatio(1.0)
        _set_picture(self._picture, image, self._picture_keep)
        self._picture_size = QSize(size)
        self._place()

    def _ensure_views(self):
        if self._clip_view is not None:
            return
        container = _layer_container(self._launcher)
        if container is None or self.glass is None or self.glass.glass is None:
            return
        try:
            clip = AppKit.NSView.alloc().initWithFrame_(AppKit.NSMakeRect(0, 0, 1, 1))
            clip.setWantsLayer_(True)
            clip.layer().setMasksToBounds_(True)
            clip.layer().setCornerRadius_(float(PANEL_GLASS_RADIUS))
            try:
                clip.layer().setCornerCurve_('continuous')
            except Exception:
                pass
            picture = _picture_view()
            clip.addSubview_(picture)
            container.addSubview_positioned_relativeTo_(clip, int(getattr(AppKit, 'NSWindowBelow', -1)), self.glass.glass)
            self._clip_view, self._picture = clip, picture
            panel = self._panel
            panel.destroyed.connect(lambda *_args, view=clip: view.removeFromSuperview())
        except Exception:
            logging.exception('The picture under the group panel failed.')

    def _place(self):
        clip, picture = self._clip_view, self._picture
        if clip is None or self._picture_size is None:
            return
        try:
            panel = self._panel
            visible = panel.isVisible()
            clip.setHidden_(not visible)
            if not visible:
                return
            origin = panel.mapTo(self._launcher, QPoint(0, 0))
            width, height = float(panel.width()), float(panel.height())
            clip.setFrame_(AppKit.NSMakeRect(origin.x(), origin.y(), width, height))
            clip.layer().setCornerRadius_(panel_radius(panel))
            total = self._picture_size
            # the clip view is not flipped: its origin is its bottom-left corner
            picture.setFrame_(AppKit.NSMakeRect(-origin.x(), origin.y() + height - total.height(),
                                                total.width(), total.height()))
        except Exception:
            pass

    def raise_views(self):
        """After new glass appeared in the window (the grid was rebuilt): the panel's stays on top."""
        if self.glass is None:
            return
        try:
            self.glass.raise_views()
            container = _layer_container(self._launcher)
            if container is not None and self._clip_view is not None and self.glass.glass is not None:
                container.addSubview_positioned_relativeTo_(
                    self._clip_view, int(getattr(AppKit, 'NSWindowBelow', -1)), self.glass.glass)
        except Exception:
            pass


def warm_panel_shadow():
    """Draw the open group's shadow picture ahead of time (it is kept): the first opening of a group
    does not wait for it."""
    try:
        dark = is_dark_theme(app)
        colour = QColor(0, 0, 0, 120 if dark else 45)
        pad = PANEL_SHADOW_PAD
        for dy in (PANEL_SHADOW_DY, -PANEL_SHADOW_DY):
            glass_kit._fitted_shadow_image(float(PANEL_GLASS_RADIUS), pad, colour, PANEL_SHADOW_BLUR, dy)
    except Exception:
        pass


def panel_radius(panel) -> float:
    """The open group's corner at this moment: the panel says it while it is growing / shrinking
    (`morph_radius`), else the panel's own; never more than half of its size."""
    radius = float(PANEL_GLASS_RADIUS)
    try:
        own = getattr(panel, 'morph_radius', None)
        if own is not None:
            radius = float(own())
        return max(0.0, min(radius, panel.width() / 2.0, panel.height() / 2.0))
    except RuntimeError:
        return radius


def paint_folder_panel(panel, painter: QPainter, frost=None):
    """The open group's own paint. With glass: cut this part out of the Qt content (the glass under it
    shows). Without: the blurred picture of what is under it + the panel colour + a hairline (= Broccoli's
    sliding panel)."""
    rect = QRectF(panel.rect())
    radius = panel_radius(panel)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    if glass_active(panel):
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillPath(path, Qt.GlobalColor.black)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        return
    dark = is_dark_theme(app)
    painter.save()
    painter.setClipPath(path)
    if frost is not None and not frost.isNull():
        painter.drawPixmap(panel.rect(), frost)
    colour = QColor(ui_palette(dark)['panel'])
    colour.setAlpha(198 if dark else 182)
    painter.fillPath(path, colour)
    painter.restore()
    painter.setPen(QPen(QColor(255, 255, 255, 40 if dark else 150), 1.0))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)


def frosted_under(launcher, sources, rect: QRect):
    """Without glass: the blurred picture of the launcher's content at `rect` (for paint_folder_panel)."""
    if rect.isEmpty():
        return None
    pixmap = QPixmap(rect.size())
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        launcher.paint_backdrop(painter, QRect(-rect.x(), -rect.y(), launcher.width(), launcher.height()))
    except Exception:
        pass
    for widget in sources:
        try:
            if widget.isVisible():
                widget.render(painter, widget.mapTo(launcher, QPoint(0, 0)) - rect.topLeft(),
                              flags=QWidget.RenderFlag.DrawChildren)
        except RuntimeError:
            continue
    painter.end()
    return broccoli_blurred_backdrop(pixmap)


# ── theme ──────────────────────────────────────────────────────────────────────────────────────────────
def raspberry_stylesheet(dark: bool) -> str:
    """The application-wide look (style book 5.4 / 5.8). No rule here may select a QScrollBar or set a
    background on QWidget (5.9: that turns the system scroll bars into the old style)."""
    if dark:
        text, border_in, bg_in, sel, sel_text = '#F2F2F7', '#4A4B4F', '#3A3A3A', '#2E5C91', '#FFFFFF'
    else:
        text, border_in, bg_in, sel, sel_text = '#20242B', '#D9D9DE', '#FFFFFF', '#DCEAFB', '#20242B'
    return '''
    QLabel { color: %(text)s; }
    QLineEdit {
        border: 1px solid %(border_in)s;
        border-radius: 6px;
        background: %(bg_in)s;
        color: %(text)s;
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
        font-size: 13px;
        padding: 0px 4px;
        selection-background-color: %(sel)s;
        selection-color: %(sel_text)s;
    }
    QTextEdit {
        border: none;
        background: transparent;
        color: %(text)s;
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
        font-size: 13px;
        selection-background-color: %(sel)s;
        selection-color: %(sel_text)s;
    }
    ''' % locals()


def search_field_stylesheet(dark: bool, glass: bool) -> str:
    """The launcher's search (5.5 A). Over glass the field has no fill of its own."""
    text = '#F2F2F7' if dark else '#20242B'
    fill = 'transparent' if glass else ('rgba(58,58,58,178)' if dark else 'rgba(255,255,255,178)')
    return '''
        QLineEdit {
            border: none;
            border-radius: 18px;
            padding: 0px 12px 0px 6px;
            background: %s;
            color: %s;
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 15px;
        }
    ''' % (fill, text)


def on_theme(callback):
    _THEME_HOOKS.append(callback)
    return callback


def apply_raspberry_theme(dark=None):
    """Light / dark, live (style book 5.8)."""
    if dark is None:
        dark = is_dark_theme(app)
    palette = QPalette(app.palette())
    palette.setColor(QPalette.ColorRole.WindowText, QColor(ui_palette(dark)['text']))
    palette.setColor(QPalette.ColorRole.Text, QColor(ui_palette(dark)['text']))
    app.setPalette(palette)
    app.setStyleSheet(raspberry_stylesheet(dark))
    for helper in list(_UNDER_GLASS):
        try:
            helper.set_dark(dark)
        except RuntimeError:
            pass
    for widget in app.allWidgets():
        try:
            if isinstance(widget, MacNormalButton):
                widget.update_theme()
            elif isinstance(widget, WhiteButton):
                widget.apply_default_style()
        except RuntimeError:
            pass
    for callback in list(_THEME_HOOKS):
        try:
            callback(dark)
        except Exception:
            logging.exception('theme hook failed')
    for top in app.topLevelWidgets():
        try:
            glass_kit.resync_inwindow_glass(top)
            top.update()
        except Exception:
            pass


# ── standalone windows and dialogs (as Tomato's / Strawberry's) ────────────────────────────────────────
def make_native_glass_window(widget, kind=Qt.WindowType.Window, resizable=False, stays_on_top=True):
    """A standalone window per the style book: the system's own traffic lights (new design, 5.7.2) in the
    compact transparent title bar (content starts 40 down), and the window's Liquid Glass behind
    everything (4.1 ①: frosted, untinted, corner 16, system shadow). Without glass the window paints the
    same rounded card itself (see glass_window_paint)."""
    widget.setWindowFlags(glass_kit.native_titlebar_window_flags(kind, zoom=resizable, stays_on_top=stays_on_top))
    widget.setAttribute(Qt.WidgetAttribute.WA_ContentsMarginsRespectsSafeArea, False)
    widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    widget.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
    widget.radius = MAIN_WINDOW_SMOOTH_RADIUS
    layout = QWidget.layout(widget)   # some windows keep a `layout` attribute that hides the method
    if layout is not None:
        left, top, right, bottom = layout.getContentsMargins()
        layout.setContentsMargins(max(left, 20), NATIVE_TITLEBAR_HEIGHT, max(right, 20), max(bottom, 16))


def glass_window_paint(widget, event):
    """Paint for a glass window: nothing while its glass is up, the rounded body colour (light / dark)
    when there is no glass."""
    if getattr(widget, '_liquid_glass_active', False):
        return
    painter = QPainter(widget)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = smooth_round_rect_path(QRectF(widget.rect()), getattr(widget, 'radius', MAIN_WINDOW_SMOOTH_RADIUS))
    painter.fillPath(path, ui_palette()['body'])
    painter.end()


def place_glass_dialog(dialog):
    """An edit dialog / the indexing card opens in the middle of the screen the mouse is on (the
    launcher fills that screen)."""
    from PyQt6.QtGui import QCursor, QGuiApplication
    screen = QGuiApplication.screenAt(QCursor.pos()) or dialog.screen()
    area = screen.availableGeometry()
    frame = dialog.frameGeometry()
    frame.moveCenter(area.center())
    dialog.move(frame.topLeft())


# ── "Show on all Spaces" (as Broccoli's main window; Ryan 2026-11-19) ─────────────────────────────────
# The launcher's NSWindow joins every Space and may sit over another app's full-screen Space. That is
# per NSWindow and not inherited, so each window opened beside the launcher (About, the update window,
# the edit dialogs, the system alerts) is given the same marks as it shows — otherwise it would open
# on the Space it was created on, out of sight.
_ALL_SPACES = {'on': False}


def all_spaces_enabled() -> bool:
    return bool(_ALL_SPACES['on'])


def _space_bits() -> int:
    return (int(getattr(AppKit, 'NSWindowCollectionBehaviorCanJoinAllSpaces', 1 << 0))
            | int(getattr(AppKit, 'NSWindowCollectionBehaviorFullScreenAuxiliary', 1 << 8)))


def apply_space_behavior(ns_window, enabled: bool) -> bool:
    """Broccoli's rule: on = join all Spaces + allowed beside a full-screen app; off = neither; the
    "move to the active Space" mark never (it cannot be combined with the first)."""
    if ns_window is None or AppKit is None:
        return False
    try:
        behavior = int(ns_window.collectionBehavior())
        wanted = behavior & ~int(getattr(AppKit, 'NSWindowCollectionBehaviorMoveToActiveSpace', 1 << 1))
        wanted = (wanted | _space_bits()) if enabled else (wanted & ~_space_bits())
        if wanted != behavior:
            ns_window.setCollectionBehavior_(wanted)
        return True
    except Exception:
        return False


def widget_ns_window(widget):
    """A top-level widget's own NSWindow (None off the Mac screen, or when unsure whose window it is)."""
    from PyQt6.QtGui import QGuiApplication
    if AppKit is None or objc is None or widget is None or QGuiApplication.platformName() != 'cocoa':
        return None
    return glass_kit._broccoli_own_ns_window(widget)


def keep_out_of_stage_manager(widget) -> bool:
    """Stage Manager (2026-11-25, Ryan: "把修改同样给 strawberry 和 raspberry"; in the sister app the system fitted
    the main window into the room beside its strip). The launcher covers the whole screen and is no document
    window: marked as belonging to no stage and showing with every app's (auxiliary + can join all
    applications, never primary), so the system has no stage to fit it into."""
    window = widget_ns_window(widget)
    if window is None:
        return False
    try:
        behavior = int(window.collectionBehavior())
        wanted = (behavior & ~(1 << 16)) | (1 << 17) | (1 << 18)
        if wanted != behavior:
            window.setCollectionBehavior_(wanted)
            logging.info('Main window marked as outside Stage Manager: behaviour %#x -> %#x', behavior, int(window.collectionBehavior()))
        return True
    except Exception:
        logging.exception('Main window: the Stage Manager mark could not be set')
        return False


def follow_all_spaces(widget) -> bool:
    """`widget` (a window of ours that is being shown) goes where the launcher goes. A dialog (a panel
    for the system) is also made "non-activating" while the switch is on: measured 2026-11-19, such a
    panel is let onto other apps' full-screen Spaces although Raspberry has a Dock icon, and it still
    takes the keyboard — so nothing has to be done to the Dock icon for the dialogs made later."""
    window = widget_ns_window(widget)
    if window is None:
        return False
    try:
        if all_spaces_enabled() and window.isKindOfClass_(AppKit.NSPanel):
            mask = int(window.styleMask())
            non_activating = int(getattr(AppKit, 'NSWindowStyleMaskNonactivatingPanel', 1 << 7))
            if not mask & non_activating:
                window.setStyleMask_(mask | non_activating)
    except Exception:
        pass
    return apply_space_behavior(window, all_spaces_enabled())


def set_all_spaces(enabled: bool):
    """The switch changed: every window of ours that exists follows at once."""
    _ALL_SPACES['on'] = bool(enabled)
    for top in QApplication.topLevelWidgets():
        try:
            if top.testAttribute(Qt.WidgetAttribute.WA_WState_Created):
                follow_all_spaces(top)
        except Exception:
            continue


def _install_follow_all_spaces(cls):
    original = cls.showEvent

    def showEvent(self, event, _original=original):
        _original(self, event)
        follow_all_spaces(self)

    cls.showEvent = showEvent


def install_glass_dialog_class(cls, radius=None):
    """A frameless dialog whose whole window is the card: window glass at corner 16 with the system shadow
    (4.1 ①, 2.3), the fallback paint, placed on first show."""
    cls.paintEvent = lambda self, event: glass_window_paint(self, event)
    install_window_liquid_glass(
        cls, (lambda w: glass_corner_radius(MAIN_WINDOW_SMOOTH_RADIUS, smooth=True)) if radius is None else radius, 0,
        keep_shadow=True, menu_look=True)
    original = cls.showEvent

    def showEvent(self, event, _original=original):
        if not getattr(self, '_glass_dialog_placed', False) and not getattr(self, '_no_auto_place', False):
            self._glass_dialog_placed = True
            place_glass_dialog(self)
        _original(self, event)

    cls.showEvent = showEvent
    _install_follow_all_spaces(cls)


def install_native_glass_window_class(cls, fixed=True):
    """Every window of `cls`: traffic lights set just before each show, window glass on first show
    (radius = glass 16), the fallback paint."""
    cls.paintEvent = lambda self, event: glass_window_paint(self, event)
    install_native_traffic_lights(cls, fixed_buttons=fixed)
    install_window_liquid_glass(cls, lambda w: glass_corner_radius(getattr(w, 'radius', MAIN_WINDOW_SMOOTH_RADIUS),
                                                                   smooth=True), 0,
                                keep_shadow=True, menu_look=True)
    _install_follow_all_spaces(cls)


def make_glass_dialog(dialog, stays_on_top=True):
    """Window flags / attributes of a frameless glass dialog (see install_glass_dialog_class)."""
    flags = Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
    if stays_on_top:
        flags |= Qt.WindowType.WindowStaysOnTopHint
    dialog.setWindowFlags(flags)
    dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    dialog.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
    dialog.radius = MAIN_WINDOW_SMOOTH_RADIUS


def raspberry_alert(parent, text: str, title: str = ''):
    """A notice / warning: the system alert (style book 5.7, 26 corners)."""
    show_broccoli_message(parent, title or 'Raspberry', text)


def raspberry_choice(parent, text: str, buttons, default=None, title: str = '') -> str:
    """A question with the given buttons as the system alert; returns the chosen label."""
    buttons = list(buttons)
    return ask_broccoli_message(parent, title or 'Raspberry', text, buttons, default or buttons[0])


class GlassFormDialog(QDialog):
    """An edit / confirm dialog (style book 5.7 approval frame): the window is the card — window glass,
    corner 16, system shadow; grey normal buttons (min 96 wide), Return = the default button, Esc = cancel.
    Put the content into `self.body` (a QVBoxLayout)."""

    def __init__(self, title, parent=None, ok_text=None, cancel_text=None):
        super().__init__(parent)
        make_glass_dialog(self)
        self.setWindowTitle(title)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 16)
        outer.setSpacing(12)
        heading = QLabel(title, self)
        font = QFont(heading.font())
        font.setPixelSize(15)
        font.setBold(True)
        heading.setFont(font)
        outer.addWidget(heading)
        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(8)
        outer.addLayout(self.body, 1)
        row = QHBoxLayout()
        row.setContentsMargins(0, 4, 0, 0)
        row.setSpacing(8)
        row.addStretch(1)
        self.cancel_button = MacNormalButton(cancel_text or _tr('Cancel'), self)
        self.cancel_button.setMinimumWidth(96)
        self.cancel_button.clicked.connect(self.reject)
        self.ok_button = MacNormalButton(ok_text or _tr('OK'), self)
        self.ok_button.setMinimumWidth(96)
        self.ok_button.setDefault(True)
        self.ok_button.clicked.connect(self.accept)
        row.addWidget(self.cancel_button)
        row.addWidget(self.ok_button)
        outer.addLayout(row)
        self.setMinimumWidth(420)   # the approval width's lower end (style book 3)
        self.resize(420, 10)


install_glass_dialog_class(GlassFormDialog)


def ask_text(parent, title: str, label: str, text: str = '', ok_text=None, cancel_text=None):
    """One line of text asked in a glass dialog: → (text, accepted)."""
    dialog = GlassFormDialog(title, parent, ok_text=ok_text, cancel_text=cancel_text)
    prompt = QLabel(label, dialog)
    prompt.setWordWrap(True)
    edit = QLineEdit(dialog)
    edit.setFixedHeight(22)
    edit.setText(text)
    edit.selectAll()
    edit.returnPressed.connect(dialog.accept)
    dialog.body.addWidget(prompt)
    dialog.body.addWidget(edit)
    dialog.adjustSize()
    edit.setFocus()
    accepted = dialog.exec() == QDialog.DialogCode.Accepted
    return edit.text(), accepted


class BusyBar(QWidget):
    """A bar that keeps moving while something of unknown length runs: a thin rounded track with a piece
    in the accent colour gliding to and fro. Drawn by the program — the system's own progress bar draws
    nothing under the new design (style book 5.7.2)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(6)
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._step)

    def _step(self):
        self._phase = (self._phase + 0.02) % 2.0
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        self._timer.start()

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def piece_rect(self) -> QRectF:
        width = float(self.width())
        piece = max(24.0, width * 0.3)
        travel = self._phase if self._phase <= 1.0 else 2.0 - self._phase      # 0 → 1 → 0
        eased = travel * travel * (3.0 - 2.0 * travel)
        return QRectF((width - piece) * eased, 0.0, piece, float(self.height()))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        track = QColor(ui_palette()['text'])
        track.setAlphaF(0.12)
        radius = self.height() / 2.0
        painter.setBrush(track)
        painter.drawRoundedRect(QRectF(self.rect()), radius, radius)
        painter.setBrush(accent_color())
        painter.drawRoundedRect(self.piece_rect(), radius, radius)
        painter.end()


class BusyCard(QDialog):
    """A small glass card in the middle of the screen with one sentence and a bar that keeps moving
    ("indexing…"): window glass, corner 16; never modal."""

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.radius = MAIN_WINDOW_SMOOTH_RADIUS
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(14)
        self.label = QLabel(text, self)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        self.progress = BusyBar(self)
        layout.addWidget(self.progress)
        self.setFixedWidth(360)
        self.adjustSize()


install_glass_dialog_class(BusyCard)
