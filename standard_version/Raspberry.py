#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -*- encoding:UTF-8 -*-
# coding=utf-8
# coding:utf-8

import os
import math
import plistlib
import subprocess
import json
import time
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QGridLayout, QPushButton, QLineEdit, QMenu, QLabel, QHBoxLayout, QSizePolicy, QMenuBar, QMessageBox, QFileDialog, QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QDialog, QTextEdit, QToolButton
)
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QFont, QPalette, QColor, QGuiApplication, QPainterPath, QRegion, QMouseEvent, QTextOption, QFontMetrics, QLinearGradient, QPen, QBrush, QAction, QSurfaceFormat, QCursor
from PyQt6.QtCore import Qt, QPropertyAnimation, QRect, pyqtSignal, QSize, QPoint, QRectF, QTimer, QThread, QEasingCurve, QParallelAnimationGroup, QAbstractAnimation, QEvent, QPointF, QCoreApplication, QElapsedTimer, QEventLoop
from qframelesswindow import AcrylicWindow, FramelessWindow, TitleBar, StandardTitleBar
import hashlib
import sys
from PIL import Image, ImageFilter, ImageQt
from pathlib import Path
import shutil
import webbrowser
import urllib3
import logging
import requests
import re
from bs4 import BeautifulSoup
import html2text
if sys.platform == "darwin":
    import objc
    from Foundation import NSObject, NSNotificationCenter, NSSelectorFromString, NSDistributedNotificationCenter, NSUserDefaults
    from AppKit import NSWorkspace, NSImage, NSApp
    from PyQt6.QtGui import QImage


GROUPS_FILE = os.path.expanduser("~/.launchpad_groups.json")
ICON_CACHE_DIR = os.path.expanduser("~/.launchpad_icon_cache")
os.makedirs(ICON_CACHE_DIR, exist_ok=True)
APP_PATHS_FILE = os.path.expanduser("~/.launchpad_app_paths.json")
APP_ORDER_FILE = os.path.expanduser("~/.launchpad_app_order.json")
MAIN_ORDER_FILE = os.path.expanduser("~/.launchpad_main_order.json")
VERSION = "0.0.6"
NAME = 'Raspberry'

os.environ["QT_QUICK_BACKEND"] = "metal"

fmt = QSurfaceFormat()
fmt.setSamples(8)  # 打开 MSAA 多重采样抗锯齿
QSurfaceFormat.setDefaultFormat(fmt)

def is_dark_theme(app):
    defaults = NSUserDefaults.standardUserDefaults()
    style = defaults.stringForKey_("AppleInterfaceStyle")
    return style == "Dark"

def set_light_palette(app):
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
    app.setPalette(palette)
    light_sheet = '''
    QTextEdit{
        border: 1px grey;  
        border-radius:4px;
        padding: 1px 5px 1px 3px; 
        background-clip: border;
        background-color: #F3F2EE;
        color: #000000;
        font: 14pt;
    }
    QListWidget{
        border: 1px grey;  
        border-radius:4px;
        padding: 1px 5px 1px 3px; 
        background-clip: border;
        background-color: #F3F2EE;
        color: #000000;
        font: 14pt;
    }
    QLabel{
        color: #000000;
    }
    '''
    app.setStyleSheet(light_sheet)

def set_dark_palette(app):
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
    palette.setColor(QPalette.ColorRole.Base, QColor(40, 40, 40))
    palette.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
    palette.setColor(QPalette.ColorRole.Button, QColor(50, 50, 50))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 220))
    app.setPalette(palette)
    dark_sheet = '''
    QTextEdit{
        border: 1px grey;  
        border-radius:4px;
        padding: 1px 5px 1px 3px; 
        background-clip: border;
        background-color: #2D2D2D;
        color: #FFFFFF;
        font: 14pt;
    }
    QListWidget{
        border: 1px grey;  
        border-radius:4px;
        padding: 1px 5px 1px 3px; 
        background-clip: border;
        background-color: #2D2D2D;
        color: #FFFFFF;
        font: 14pt;
    }
    QLabel{
        color: #FFFFFF;
    }
        '''
    app.setStyleSheet(dark_sheet)


class ThemeObserver(NSObject):
    def initWithApp_(self, app):
        self = objc.super(ThemeObserver, self).init()
        self.app = app
        return self

    def themeChanged_(self, notification):
        # 主题变更时自动切换 palette
        if is_dark_theme(self.app):
            set_dark_palette(self.app)
            #print("Dark theme changed")
        else:
            set_light_palette(self.app)
            #print("Light theme changed")


def install_theme_observer(app):
    observer = ThemeObserver.alloc().initWithApp_(app)
    center = NSDistributedNotificationCenter.defaultCenter()
    center.addObserver_selector_name_object_(
        observer,
        NSSelectorFromString("themeChanged:"),
        "AppleInterfaceThemeChangedNotification",
        None
    )
    return observer

app = QApplication(sys.argv)

if is_dark_theme(app):
    set_dark_palette(app)
else:
    set_light_palette(app)

theme_observer = install_theme_observer(app)

# 获取沙盒 Application Support 路径
base_dir = Path.home() / "Library/Application Support" / 'com.ryanthehito.raspberry'
base_dir.mkdir(parents=True, exist_ok=True)
resource_tarname = "Resources/"
#resource_tarname = '/Applications/Hazelnut.app/Contents/Resources/'  # test
BasePath = str(os.path.join(base_dir, resource_tarname))
#BasePath = ''  # test
#base_dir = ''  # test

# copy items from app to basepath
old_base_path = Path('/Applications/Raspberry.app/Contents/Resources/')
if getattr(sys, 'frozen', False):  # 判断是否是打包后的应用
    old_base_path = Path(sys.executable).parent.parent / "Resources"
else:
    # 开发环境路径（可以自定义）
    old_base_path = Path(__file__).parent / "Resources"
    #old_base_path = Path('/Applications/Raspberry.app/Contents/Resources')  # test
source_dir = old_base_path
target_dir = os.path.join(base_dir, resource_tarname)
# 只在目标目录不存在文件时才复制
for item in source_dir.iterdir():
    target_item = os.path.join(target_dir, item.name)
    if os.path.exists(target_item):
        continue  # 已存在就跳过
    if item.is_dir():
        shutil.copytree(item, target_item)
    else:
        os.makedirs(os.path.dirname(target_item), exist_ok=True)  # 确保父目录存在
        shutil.copy2(item, target_item)


def save_main_order(order):
    with open(MAIN_ORDER_FILE, 'w') as f:
        json.dump(order, f)


def load_main_order():
    if not os.path.exists(MAIN_ORDER_FILE):
        return []
    with open(MAIN_ORDER_FILE, 'r') as f:
        return json.load(f)


def save_app_order(app_paths):
    with open(APP_ORDER_FILE, 'w') as f:
        json.dump(app_paths, f)


def load_app_order():
    if not os.path.exists(APP_ORDER_FILE):
        return []
    with open(APP_ORDER_FILE, 'r') as f:
        return json.load(f)

def save_app_paths(app_paths):
    with open(APP_PATHS_FILE, 'w') as f:
        json.dump(app_paths, f)


def load_app_paths():
    if not os.path.exists(APP_PATHS_FILE):
        return []
    with open(APP_PATHS_FILE, 'r') as f:
        return json.load(f)


def sync_app_paths():
    app_paths = load_app_paths()
    valid_paths = [p for p in app_paths if os.path.exists(p)]
    if len(valid_paths) != len(app_paths):
        save_app_paths(valid_paths)
    return valid_paths


def app_icon_cache_path(app_path, app_name):
    # 用 app 名字命名，防止重名可加下划线和 hash
    safe_name = app_name.replace('/', '_').replace(' ', '_')
    h = hashlib.md5(app_path.encode('utf-8')).hexdigest()[:6]
    return os.path.join(ICON_CACHE_DIR, f"{safe_name}_{h}.png")


def save_icon_to_cache(icon, app_path, app_name):
    cache_path = app_icon_cache_path(app_path, app_name)
    pix = icon.pixmap(100, 100)
    pix.save(cache_path, "PNG")


def load_icon_from_cache(app_path, app_name):
    cache_path = app_icon_cache_path(app_path, app_name)
    if os.path.exists(cache_path):
        return QIcon(cache_path)
    return None


def get_finder_icon(app_path):
    if sys.platform != "darwin":
        return QIcon()
    nsimage = NSWorkspace.sharedWorkspace().iconForFile_(app_path)
    if nsimage is None:
        return QIcon()
    image_data = nsimage.TIFFRepresentation()
    if image_data is None:
        return QIcon()
    qimage = QImage.fromData(bytes(image_data))
    pil_img = ImageQt.fromqimage(qimage).convert("RGBA")
    # 修复 premultiplied alpha
    r, g, b, a = pil_img.split()
    pil_img = Image.merge("RGBA", (r, g, b, a))
    qimage2 = ImageQt.toqimage(pil_img)
    return QIcon(QPixmap.fromImage(qimage2))


# def get_applications():  # 这个是 get 到路径下所有所有.app文件的写法
#     # 1. 如果本地有 app 路径列表，直接用
#     sync_app_paths()
#     app_paths = load_app_paths()
#     if not app_paths:
#         # 首次扫描
#         app_dirs = ["/Applications", "/System/Applications"]
#         app_paths = []
#         for app_dir in app_dirs:
#             for root, dirs, files in os.walk(app_dir):
#                 for item in dirs:
#                     if item.endswith('.app'):
#                         app_path = os.path.join(root, item)
#                         app_paths.append(app_path)
#         save_app_paths(app_paths)
#     apps = []
#     for app_path in app_paths:
#         info_plist = os.path.join(app_path, 'Contents', 'Info.plist')
#         if os.path.exists(info_plist):
#             try:
#                 with open(info_plist, 'rb') as f:
#                     plist = plistlib.load(f)
#             except Exception:
#                 continue
#             name = plist.get('CFBundleDisplayName') or plist.get('CFBundleName') or os.path.basename(app_path)[:-4]
#             icon = load_icon_from_cache(app_path, name)
#             if not icon:
#                 icon = get_finder_icon(app_path)
#                 if icon.isNull():
#                     icon_file = plist.get('CFBundleIconFile')
#                     if icon_file:
#                         if not icon_file.endswith('.icns'):
#                             icon_file += '.icns'
#                         icon_path = os.path.join(app_path, 'Contents', 'Resources', icon_file)
#                         if os.path.exists(icon_path):
#                             icon = QIcon(icon_path)
#                         else:
#                             icon = QIcon()
#                     else:
#                         icon = QIcon()
#                 if not icon.isNull():
#                     save_icon_to_cache(icon, app_path, name)
#             apps.append({'name': name, 'icon': icon, 'path': app_path})
#     return apps


def is_nested_in_app(path, app_dirs):  # 这个是只 get 到浅层文件夹的.app的写法
    # 检查 path 是否嵌套在其他 .app 之下
    parent = os.path.dirname(path)
    while parent and not any(parent == d for d in app_dirs):
        if parent.endswith('.app'):
            return True
        parent = os.path.dirname(parent)
    return False


def find_top_level_apps(app_dirs):  # 这个是只 get 到浅层文件夹的.app的写法
    app_paths = []
    for app_dir in app_dirs:
        for root, dirs, files in os.walk(app_dir, topdown=True):
            if root.endswith('.app'):
                if not is_nested_in_app(root, app_dirs):
                    app_paths.append(root)
                dirs[:] = []  # 阻止递归
    return app_paths


# def get_applications():  # 这个是只 get 到浅层文件夹的.app的写法，但是无法加载iOS软件
#     sync_app_paths()
#     app_paths = load_app_paths()
#     if not app_paths:
#         app_dirs = ["/Applications", "/System/Applications"]
#         app_paths = find_top_level_apps(app_dirs)
#         save_app_paths(app_paths)
#     apps = []
#     for app_path in app_paths:
#         info_plist = os.path.join(app_path, 'Contents', 'Info.plist')
#         if os.path.exists(info_plist):
#             try:
#                 with open(info_plist, 'rb') as f:
#                     plist = plistlib.load(f)
#             except Exception:
#                 continue
#             name = plist.get('CFBundleDisplayName') or plist.get('CFBundleName') or os.path.basename(app_path)[:-4]
#             icon = load_icon_from_cache(app_path, name)
#             if not icon:
#                 icon = get_finder_icon(app_path)
#                 if icon.isNull():
#                     icon_file = plist.get('CFBundleIconFile')
#                     if icon_file:
#                         if not icon_file.endswith('.icns'):
#                             icon_file += '.icns'
#                         icon_path = os.path.join(app_path, 'Contents', 'Resources', icon_file)
#                         if os.path.exists(icon_path):
#                             icon = QIcon(icon_path)
#                         else:
#                             icon = QIcon()
#                     else:
#                         icon = QIcon()
#                 if not icon.isNull():
#                     save_icon_to_cache(icon, app_path, name)
#             apps.append({'name': name, 'icon': icon, 'path': app_path})
#     return apps


def get_applications():  # 兼容加载检查iOS软件
    sync_app_paths()
    app_paths = load_app_paths()
    if not app_paths:
        app_dirs = ["/Applications", "/System/Applications", "/System/Volumes/Preboot/Cryptexes/App/System/Applications"]
        app_paths = find_top_level_apps(app_dirs)
        save_app_paths(app_paths)
    apps = []
    for app_path in app_paths:
        info_plist = os.path.join(app_path, 'Contents', 'Info.plist')
        itunes_plist = os.path.join(app_path, 'Wrapper', 'iTunesMetadata.plist')
        name = None
        plist = None
        # 1. 优先 Info.plist
        if os.path.exists(info_plist):
            try:
                with open(info_plist, 'rb') as f:
                    plist = plistlib.load(f)
                name = plist.get('CFBundleDisplayName') or plist.get('CFBundleName') or os.path.basename(app_path)[:-4]
            except Exception as e:
                print(f"Failed to parse Info.plist for {app_path}: {e}")
        # 2. iOS 应用的 iTunesMetadata.plist
        elif os.path.exists(itunes_plist):
            try:
                with open(itunes_plist, 'rb') as f:
                    plist = plistlib.load(f)
                name = plist.get('title') or plist.get('itemName') or os.path.basename(app_path)[:-4]
            except Exception as e:
                print(f"Failed to parse iTunesMetadata.plist for {app_path}: {e}")
        # 3. 都没有就用文件夹名
        if not name:
            name = os.path.basename(app_path)[:-4]
        icon = load_icon_from_cache(app_path, name)
        if not icon:
            try:
                icon = get_finder_icon(app_path)
                if not icon.isNull():
                    save_icon_to_cache(icon, app_path, name)
            except Exception as e:
                print(f"Failed to load icon for {app_path}: {e}")
                icon = QIcon()
        apps.append({'name': name, 'icon': icon, 'path': app_path})
    return apps


def save_groups(groups):
    data = []
    for group in groups:
        data.append({
            'name': group['name'],
            'apps': [app['path'] for app in group['apps']]
        })
    with open(GROUPS_FILE, 'w') as f:
        json.dump(data, f)

def load_groups(apps):
    if not os.path.exists(GROUPS_FILE):
        return []
    with open(GROUPS_FILE, 'r') as f:
        data = json.load(f)
    app_dict = {app['path']: app for app in apps}
    groups = []
    for group in data:
        group_apps = [app_dict[path] for path in group['apps'] if path in app_dict]
        if group_apps:
            groups.append({
                'name': group['name'],
                'apps': group_apps,
                'icon': create_group_icon(group_apps)
            })
    return groups


# def get_display_text(name, font, max_width):
#     metrics = QFontMetrics(font)
#     # 检查首个“单词”或“连续字符”是否超宽
#     # 对中日文等无空格的，直接用整个字符串
#     if ' ' in name:
#         first_word = name.split(' ')[0]
#     else:
#         first_word = name
#     if metrics.horizontalAdvance(first_word) > max_width:
#         # 首行超宽，单行省略号
#         return metrics.elidedText(name, Qt.TextElideMode.ElideRight, max_width), False
#     else:
#         # 否则用多行HTML
#         html = (
#             f'<div style="'
#             'display:-webkit-box;'
#             '-webkit-line-clamp:2;'
#             '-webkit-box-orient:vertical;'
#             'overflow:hidden;'
#             'text-overflow:ellipsis;'
#             'word-break:break-all;'
#             f'max-width:{max_width}px;">{name}</div>'
#         )
#         return html, True
#
#
# def multiline_elide_strict(text, font, max_width, max_lines=2):
#     metrics = QFontMetrics(font)
#     lines = []
#     idx = 0
#     while idx < len(text) and len(lines) < max_lines:
#         # 尝试找到本行能容纳的最大子串
#         for end in range(len(text), idx, -1):
#             substr = text[idx:end]
#             if metrics.horizontalAdvance(substr) <= max_width:
#                 break
#         else:
#             # 一个字符都放不下，强制一个字符
#             end = idx + 1
#             substr = text[idx:end]
#         if len(lines) == max_lines - 1 and end < len(text):
#             # 最后一行且还有剩余，elide
#             substr = metrics.elidedText(text[idx:], Qt.TextElideMode.ElideRight, max_width)
#             lines.append(substr)
#             break
#         lines.append(substr)
#         idx = end
#     return '\n'.join(lines)
#
#
# def multiline_elide_smart(text, font, max_width, max_lines=2):
#     metrics = QFontMetrics(font)
#     lines = []
#     idx = 0
#     length = len(text)
#     while idx < length and len(lines) < max_lines:
#         # 先尝试整行能放下多少
#         end = idx
#         last_space = -1
#         while end < length:
#             substr = text[idx:end+1]
#             if metrics.horizontalAdvance(substr) > max_width:
#                 break
#             if text[end] == ' ':
#                 last_space = end
#             end += 1
#         if end == idx:
#             # 一个字符都放不下，强制一个字符
#             end = idx + 1
#         elif last_space >= idx:
#             # 优先在空格处断行
#             end = last_space + 1
#         # 判断是否是最后一行且还有剩余
#         if len(lines) == max_lines - 1 and end < length:
#             substr = metrics.elidedText(text[idx:], Qt.TextElideMode.ElideRight, max_width)
#             lines.append(substr)
#             break
#         lines.append(text[idx:end].rstrip())
#         idx = end
#     return '\n'.join(lines)


def multiline_elide_with_firstline(text, font, max_width, max_lines=2):
    metrics = QFontMetrics(font)
    # 检查首行是否能放下整个字符串
    if metrics.horizontalAdvance(text) <= max_width:
        return text
    # 检查首个“单词”或“连续字符”是否超宽
    if ' ' in text:
        first_word = text.split(' ')[0]
    else:
        first_word = text
    if metrics.horizontalAdvance(first_word) > max_width:
        # 首行第一个单词就超宽，直接单行省略号
        return metrics.elidedText(text, Qt.TextElideMode.ElideRight, max_width)
    # 否则允许多行
    lines = []
    idx = 0
    length = len(text)
    while idx < length and len(lines) < max_lines:
        end = idx
        last_space = -1
        while end < length:
            substr = text[idx:end+1]
            if metrics.horizontalAdvance(substr) > max_width:
                break
            if text[end] == ' ':
                last_space = end
            end += 1
        if end == idx:
            end = idx + 1
        elif last_space >= idx:
            end = last_space + 1
        if len(lines) == max_lines - 1 and end < length:
            substr = metrics.elidedText(text[idx:], Qt.TextElideMode.ElideRight, max_width)
            lines.append(substr)
            break
        lines.append(text[idx:end].rstrip())
        idx = end
    return '\n'.join(lines)


class EmptyButton(QPushButton):
    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.main_window = main_window          # 保存主窗引用
        self.setFixedSize(135, 128)
        self.setFlat(True)
        self.setEnabled(True)                  # 必须能接收事件
        # 和背景一致：完全透明
        self.setStyleSheet("background: transparent; border: none;")

    def mouseDoubleClickEvent(self, event):
        # 双击占位按钮 → 关闭主界面
        if event.button() == Qt.MouseButton.LeftButton and self.main_window:
            self.main_window.close_main_window()
        # 不再向父级传播，直接吞掉即可


class SearchLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._base_width = 500
        self._expanded_width = int(self._base_width * 1.5)
        self.setFixedWidth(self._base_width)
        self._anim = QPropertyAnimation(self, b"minimumWidth")
        self._anim.setDuration(250)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setStyleSheet("""
            QLineEdit {
                border-radius: 18px;
                padding-left: 20px;
                font-size: 16px;
                background: rgba(255,255,255,0.35);
                height: 36px;
            }
            QLineEdit:focus {
                border: 1.5px solid #0085FF;
                background: rgba(255,255,255,0.35);
            }
        """)

        # “X”按钮
        self.clear_btn = QToolButton(self)
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setStyleSheet("""
                    QToolButton {
                        border: none;
                        background: transparent;
                    }
                """)
        self.clear_btn.setIcon(self._make_x_icon())
        self.clear_btn.setFixedSize(24, 24)
        self.clear_btn.hide()
        self.clear_btn.clicked.connect(self.clear)
        self.textChanged.connect(self._update_clear_btn)

    def _make_x_icon(self):
        # 画一个圆形背景+“X”
        pix = QPixmap(24, 24)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # 圆形底
        painter.setBrush(QColor(220, 220, 220, 180))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 24, 24)
        # “X”
        pen = QPen(QColor(80, 80, 80), 2)
        painter.setPen(pen)
        painter.drawLine(7, 7, 17, 17)
        painter.drawLine(17, 7, 7, 17)
        painter.end()
        return QIcon(pix)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_clear_btn_pos()

    def _update_clear_btn_pos(self):
        # 右侧内边距
        margin = 8
        x = self.width() - self.clear_btn.width() - margin
        y = (self.height() - self.clear_btn.height()) // 2
        self.clear_btn.move(x, y)

    def _update_clear_btn(self):
        # 只有聚焦且有内容时显示
        if self.hasFocus() and self.text():
            self.clear_btn.show()
        else:
            self.clear_btn.hide()

    def focusInEvent(self, event):
        self._anim.stop()
        self._anim.setStartValue(self.width())
        self._anim.setEndValue(self._expanded_width)
        self._anim.start()
        super().focusInEvent(event)
        self._update_clear_btn()
        self.update()

    def focusOutEvent(self, event):
        self._anim.stop()
        self._anim.setStartValue(self.width())
        self._anim.setEndValue(self._base_width)
        self._anim.start()
        super().focusOutEvent(event)
        self._update_clear_btn()
        self.update()

    def setMinimumWidth(self, w):
        self.setFixedWidth(w)
        self._update_clear_btn()
        self.update()

    def minimumWidth(self):
        return self.width()

    def paintEvent(self, event):
        super().paintEvent(event)
        # 高光特效
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = self.rect().adjusted(1, 1, 0, 0)
        radius = rect.height() // 2

        # 生成圆角矩形路径上的点
        points = self.rounded_rect_points(rect, radius, num_points=240)
        total = len(points)
        # 左上高光
        self.draw_highlight_with_fade(painter, points, int(0.02*total), int(0.22*total), fade_len=15, base_width=1, reverse=False)
        # 右下高光
        self.draw_highlight_with_fade(painter, points, int(0.55*total), int(0.87*total), fade_len=15, base_width=1, reverse=True)

    @staticmethod
    def rounded_rect_points(rect, radius, num_points=100):
        points = []
        for i in range(num_points//4):
            angle = 180 + 90 * (i / (num_points//4))
            x = rect.left() + radius + radius * math.cos(math.radians(angle))
            y = rect.top() + radius + radius * math.sin(math.radians(angle))
            points.append(QPointF(x, y))
        for i in range(num_points//4):
            angle = 270 + 90 * (i / (num_points//4))
            x = rect.right() - radius + radius * math.cos(math.radians(angle))
            y = rect.top() + radius + radius * math.sin(math.radians(angle))
            points.append(QPointF(x, y))
        for i in range(num_points//4):
            angle = 0 + 90 * (i / (num_points//4))
            x = rect.right() - radius + radius * math.cos(math.radians(angle))
            y = rect.bottom() - radius + radius * math.sin(math.radians(angle))
            points.append(QPointF(x, y))
        for i in range(num_points//4):
            angle = 90 + 90 * (i / (num_points//4))
            x = rect.left() + radius + radius * math.cos(math.radians(angle))
            y = rect.bottom() - radius + radius * math.sin(math.radians(angle))
            points.append(QPointF(x, y))
        return points

    @staticmethod
    def draw_highlight_with_fade(painter, points, start_idx, end_idx, fade_len=10, base_width=3, reverse=False):
        if not reverse:
            grad_main = QLinearGradient(points[start_idx], points[end_idx])
            grad_main.setColorAt(0, QColor(255,255,255,0))
            grad_main.setColorAt(1, QColor(255,255,255,255))
            pen_main = QPen(QBrush(grad_main), base_width, cap=Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_main)
            path_main = QPainterPath()
            path_main.moveTo(points[start_idx])
            for pt in points[start_idx+1:end_idx]:
                path_main.lineTo(pt)
            painter.drawPath(path_main)

            fade_start = end_idx
            fade_end = min(end_idx + fade_len, len(points)-1)
            grad_fade = QLinearGradient(points[fade_start], points[fade_end])
            grad_fade.setColorAt(0, QColor(255,255,255,255))
            grad_fade.setColorAt(1, QColor(255,255,255,0))
            pen_fade = QPen(QBrush(grad_fade), base_width, cap=Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_fade)
            path_fade = QPainterPath()
            path_fade.moveTo(points[fade_start])
            for pt in points[fade_start+1:fade_end]:
                path_fade.lineTo(pt)
            painter.drawPath(path_fade)
        else:
            grad_main = QLinearGradient(points[end_idx], points[start_idx])
            grad_main.setColorAt(0, QColor(255,255,255,0))
            grad_main.setColorAt(1, QColor(255,255,255,255))
            pen_main = QPen(QBrush(grad_main), base_width, cap=Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_main)
            path_main = QPainterPath()
            path_main.moveTo(points[end_idx])
            for pt in reversed(points[start_idx+1:end_idx+1]):
                path_main.lineTo(pt)
            painter.drawPath(path_main)

            fade_start = start_idx
            fade_end = max(start_idx - fade_len, 0)
            grad_fade = QLinearGradient(points[fade_start], points[fade_end])
            grad_fade.setColorAt(0, QColor(255,255,255,255))
            grad_fade.setColorAt(1, QColor(255,255,255,0))
            pen_fade = QPen(QBrush(grad_fade), base_width, cap=Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_fade)
            path_fade = QPainterPath()
            path_fade.moveTo(points[fade_start])
            for pt in reversed(points[fade_end:fade_start]):
                path_fade.lineTo(pt)
            painter.drawPath(path_fade)


class WhiteButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setFixedHeight(30)
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
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 40))  # 半透明黑色阴影
        self.setGraphicsEffect(shadow)


class MacWindowButton(QPushButton):
    def __init__(self, color, symbol, parent=None):
        super().__init__(parent)
        self.setFixedSize(16,16)
        self.base_color = QColor(color)
        self.symbol = symbol  # "x", "-", "+"
        self.hovered = False
        self.setStyleSheet("border: none; background: transparent;")

    def enterEvent(self, event):
        self.hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        # # 1. 选择底色
        # if self.hovered:
        #     # hover 时用更深的颜色
        #     if self.symbol == "x":
        #         color = QColor("#BF4943")
        #     elif self.symbol == "-":
        #         color = QColor("#B29B32")
        #     elif self.symbol == "+":
        #         color = QColor("#24912D")
        #     else:
        #         color = self.base_color
        # else:
        #     color = self.base_color
        # Draw circle
        painter.setBrush(self.base_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, self.width(), self.height())
        # Draw symbol if hovered
        if self.hovered:
            pen = QPen(QColor("black"))
            pen.setWidth(2)
            painter.setPen(pen)
            margin = 5  # 增大 margin，叉号更小
            if self.symbol == "x":
                painter.drawLine(margin, margin, self.width()-margin, self.height()-margin)
                painter.drawLine(self.width()-margin, margin, margin, self.height()-margin)
            elif self.symbol == "-":
                painter.drawLine(margin, self.height()//2, self.width()-margin, self.height()//2)
            elif self.symbol == "+":
                painter.drawLine(self.width()//2, margin, self.width()//2, self.height()-margin)
                painter.drawLine(margin, self.height()//2, self.width()-margin, self.height()//2)


class CustomMessageBox(QWidget):
    def __init__(self, text, parent=None, icon=None, buttons=("OK",), default=0):
        super().__init__(parent)
        self.radius = 16
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFixedSize(400, 200)
        self.result = None

        # 拖动支持
        self.drag_pos = None

        # 关闭按钮
        self.close_button = MacWindowButton("#FF605C", "x", self)
        self.close_button.move(10, 10)
        self.close_button.clicked.connect(self.close)

        # 主内容
        layout = QVBoxLayout()
        layout.setContentsMargins(32, 40, 32, 32)
        layout.setSpacing(16)

        # 图标
        if icon:
            icon_label = QLabel()
            icon_label.setPixmap(icon.pixmap(48, 48))
            icon_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            layout.addWidget(icon_label)

        # 文本
        label = QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        #label.setStyleSheet("font-size: 16px;")
        label.setStyleSheet("""
                    font-size: 16px;
                    background-color: rgba(255,255,255,0);
                    border-radius: 8px;
                    padding: 8px;
                """)
        layout.addWidget(label, stretch=1)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btns = []
        for i, btn_text in enumerate(buttons):
            btn = WhiteButton(btn_text)
            btn.setFixedWidth(150)
            # btn.setFixedHeight(32)
            # btn.setStyleSheet("""
            #     QPushButton {
            #         background: #F2F2F2;
            #         border-radius: 8px;
            #         border: 1px solid #E0E0E0;
            #         min-width: 80px;
            #         font-size: 15px;
            #     }
            #     QPushButton:hover {
            #         background: #E0E0E0;
            #     }
            # """)
            btn.clicked.connect(lambda checked, idx=i: self._on_btn(idx))
            btn_layout.addWidget(btn)
            self.btns.append(btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.btns[default].setFocus()

    def _on_btn(self, idx):
        self.result = idx
        self.accept()

    def accept(self):
        self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, self.radius, self.radius)
        painter.setClipPath(path)
        if is_dark_theme(self):
            painter.fillPath(path, QColor(30, 30, 30, 245))
        else:
            painter.fillPath(path, QColor(255, 255, 255, 245))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def exec(self):
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.show()
        loop = QEventLoop()
        self.destroyed.connect(loop.quit)
        loop.exec()
        return self.result


class RestartMessageBox(QWidget):
    def __init__(self, text, parent=None, icon=None, buttons=("OK",), default=0):
        super().__init__(parent)
        self.radius = 16
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFixedSize(400, 200)
        self.result = None

        # 拖动支持
        self.drag_pos = None

        # 关闭按钮
        self.close_button = MacWindowButton("#FF605C", "x", self)
        self.close_button.move(10, 10)
        self.close_button.clicked.connect(self.close)

        # 主内容
        layout = QVBoxLayout()
        layout.setContentsMargins(32, 40, 32, 32)
        layout.setSpacing(16)

        # 图标
        if icon:
            icon_label = QLabel()
            icon_label.setPixmap(icon.pixmap(48, 48))
            icon_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            layout.addWidget(icon_label)

        # 文本
        label = QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        # label.setStyleSheet("font-size: 16px;")
        label.setStyleSheet("""
            font-size: 16px;
            background-color: rgba(255,255,255,0);
            border-radius: 8px;
            padding: 8px;
        """)
        layout.addWidget(label, stretch=1)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btns = []
        for i, btn_text in enumerate(buttons):
            btn = WhiteButton(btn_text)
            btn.setFixedWidth(150)
            # btn.setFixedHeight(32)
            # btn.setStyleSheet("""
            #     QPushButton {
            #         background: #F2F2F2;
            #         border-radius: 8px;
            #         border: 1px solid #E0E0E0;
            #         min-width: 80px;
            #         font-size: 15px;
            #     }
            #     QPushButton:hover {
            #         background: #E0E0E0;
            #     }
            # """)
            btn.clicked.connect(lambda checked, idx=i: self._on_btn(idx))
            btn_layout.addWidget(btn)
            self.btns.append(btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.btns[default].setFocus()

    def _on_btn(self, idx):
        if idx == 0:
            time.sleep(3)
            applescript = '''
                if application "Raspberry" is running then
                    try
                        tell application "Raspberry"
                            quit
                            delay 1
                            activate
                        end tell
                    on error number -128
                        quit application "Raspberry"
                        delay 1
                        activate application "Raspberry"
                    end try
                end if
                '''
            subprocess.Popen(['osascript', '-e', applescript])
        self.result = idx
        self.accept()

    def accept(self):
        self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, self.radius, self.radius)
        painter.setClipPath(path)
        if is_dark_theme(self):
            painter.fillPath(path, QColor(30, 30, 30, 245))
        else:
            painter.fillPath(path, QColor(255, 255, 255, 245))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def exec(self):
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.show()
        loop = QEventLoop()
        self.destroyed.connect(loop.quit)
        loop.exec()
        return self.result


class GlassEffectWidget(QWidget):
    def __init__(self, radius=36, bg_color=(255,255,255,20), highlight_color=(255,255,255,80), parent=None):
        super().__init__(parent)
        self.radius = radius
        self.bg_color = QColor(*bg_color)
        self.highlight_color = QColor(*highlight_color)
        self.blur_bg = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.width(), self.height()).adjusted(2, 2, -2, -2)
        path = QPainterPath()
        path.addRoundedRect(rect, self.radius, self.radius)
        center_y = rect.center().y()

        painter.setBrush(QBrush(self.bg_color))
        painter.setPen(QPen(QColor(255, 255, 255, 50), 1))
        painter.drawPath(path)

        if self.blur_bg is None or self.blur_bg.size() != self.size():
            tmp_img = QImage(self.size(), QImage.Format.Format_ARGB32)
            tmp_img.fill(Qt.GlobalColor.transparent)
            tmp_painter = QPainter(tmp_img)
            tmp_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            tmp_painter.setBrush(QBrush(QColor(255, 255, 255, 20)))
            tmp_painter.setPen(QPen(QColor(255, 255, 255, 50), 1))
            tmp_painter.drawPath(path)
            tmp_painter.end()
            pil_img = Image.fromqimage(tmp_img)
            pil_img = pil_img.filter(ImageFilter.GaussianBlur(radius=2))
            self.blur_bg = QImage(
                pil_img.tobytes("raw", "RGBA"),
                pil_img.width,
                pil_img.height,
                QImage.Format.Format_ARGB32
            )
        painter.drawImage(0, 0, self.blur_bg)

        path = QPainterPath()
        path.moveTo(rect.left()+self.radius, rect.bottom())
        path.lineTo(rect.right()-self.radius, rect.bottom())
        path.arcTo(rect.right() - 2 * self.radius, rect.bottom() - 2 * self.radius,
                   2 * self.radius, 2 * self.radius, 270, 90)
        path.lineTo(rect.right(), center_y)
        path.lineTo(rect.left(), center_y)
        path.arcTo(rect.left(), rect.bottom() - 2 * self.radius,
                   2 * self.radius, 2 * self.radius, 180, 90)
        path.closeSubpath()
        gradient = QLinearGradient(rect.left(), rect.bottom(), rect.left(), center_y)
        gradient.setColorAt(0, self.highlight_color)
        gradient.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setPen(QPen(QBrush(gradient), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

class GlassButton(QPushButton):
    def __init__(self, text="Glass Button", parent=None, on_double_click=None):
        super().__init__(text, parent)
        self.on_double_click = on_double_click

        self.setStyleSheet("""
            background-color: transparent;
            border: none;
            color: white;
            font-size: 16px;
            padding: 8px 24px;
        """)

    def mouseDoubleClickEvent(self, event):
        if self.on_double_click:
            self.on_double_click()
        else:
            print("GlassButton was double-clicked!")
        super().mouseDoubleClickEvent(event)

class GlassButtonWidget(QWidget):
    def __init__(self, text, radius=36, bg_color=(255,255,255,20), highlight_color=(255,255,255,80), on_double_click=None):
        super().__init__()
        self.effect = GlassEffectWidget(radius, bg_color, highlight_color)
        self.button = GlassButton(text, on_double_click=on_double_click)
        self.button.setParent(self)
        self.effect.setParent(self)
        self.effect.lower()
        self.button.raise_()
        #self.button.setEnabled(False)
        self.resize(200, 48)

    def resizeEvent(self, event):
        self.effect.resize(self.size())
        self.button.resize(self.size())


class ClearCacheWorker(QThread):
    finished = pyqtSignal(object, object, object, str)  # apps, groups, filtered_apps, error_msg

    def run(self):
        import shutil
        error_msg = ""
        try:
            shutil.rmtree(ICON_CACHE_DIR)
            os.makedirs(ICON_CACHE_DIR, exist_ok=True)
        except Exception as e:
            error_msg = f"Clear cache failed: {e}"
            self.finished.emit(None, None, None, error_msg)
            return
        try:
            apps = get_applications()
            groups = load_groups(apps)
            filtered_apps = [a for a in apps if not any(a in g['apps'] for g in groups)]
            self.finished.emit(apps, groups, filtered_apps, "")
        except Exception as e:
            error_msg = f"Failed to refresh the application: {e}"
            self.finished.emit(None, None, None, error_msg)


class AppScanWorker(QThread):
    apps_found = pyqtSignal(object)  # 新 app 列表

    def __init__(self):
        super().__init__()
        self._running = True

    # def run(self):  # 这个是只 get 到浅层文件夹的.app的写法，非兼容版本
    #     sync_app_paths()
    #     known_paths = set(load_app_paths())
    #     app_dirs = ["/Applications", "/System/Applications"]
    #     found_paths = set()
    #     new_apps = []
    #     all_app_paths = find_top_level_apps(app_dirs)
    #     for app_path in all_app_paths:
    #         if not self._running:
    #             return
    #         found_paths.add(app_path)
    #         if app_path not in known_paths:
    #             info_plist = os.path.join(app_path, 'Contents', 'Info.plist')
    #             if os.path.exists(info_plist):
    #                 try:
    #                     with open(info_plist, 'rb') as f:
    #                         plist = plistlib.load(f)
    #                 except Exception:
    #                     continue
    #                 name = plist.get('CFBundleDisplayName') or plist.get('CFBundleName') or os.path.basename(app_path)[
    #                                                                                         :-4]
    #                 icon = load_icon_from_cache(app_path, name)
    #                 if not icon:
    #                     icon = get_finder_icon(app_path)
    #                     if icon.isNull():
    #                         icon_file = plist.get('CFBundleIconFile')
    #                         if icon_file:
    #                             if not icon_file.endswith('.icns'):
    #                                 icon_file += '.icns'
    #                             icon_path = os.path.join(app_path, 'Contents', 'Resources', icon_file)
    #                             if os.path.exists(icon_path):
    #                                 icon = QIcon(icon_path)
    #                             else:
    #                                 icon = QIcon()
    #                         else:
    #                             icon = QIcon()
    #                     if not icon.isNull():
    #                         save_icon_to_cache(icon, app_path, name)
    #                 new_apps.append({'name': name, 'icon': icon, 'path': app_path})
    #     if new_apps:
    #         all_paths = list(known_paths | found_paths)
    #         save_app_paths(all_paths)
    #     self.apps_found.emit({'new_apps': new_apps, 'all_paths': list(found_paths)})

    def run(self):  # 兼容版本
        sync_app_paths()
        known_paths = set(load_app_paths())
        app_dirs = ["/Applications", "/System/Applications",
                    "/System/Volumes/Preboot/Cryptexes/App/System/Applications"]
        found_paths = set()
        new_apps = []
        all_app_paths = find_top_level_apps(app_dirs)
        for app_path in all_app_paths:
            if not self._running:
                return
            found_paths.add(app_path)
            if app_path not in known_paths:
                info_plist = os.path.join(app_path, 'Contents', 'Info.plist')
                itunes_plist = os.path.join(app_path, 'Wrapper', 'iTunesMetadata.plist')
                name = None
                plist = None
                # 1. 优先 Info.plist
                if os.path.exists(info_plist):
                    try:
                        with open(info_plist, 'rb') as f:
                            plist = plistlib.load(f)
                        name = plist.get('CFBundleDisplayName') or plist.get('CFBundleName') or os.path.basename(
                            app_path)[:-4]
                    except Exception as e:
                        print(f"Failed to parse Info.plist for {app_path}: {e}")
                # 2. iOS 应用的 iTunesMetadata.plist
                elif os.path.exists(itunes_plist):
                    try:
                        with open(itunes_plist, 'rb') as f:
                            plist = plistlib.load(f)
                        name = plist.get('title') or plist.get('itemName') or os.path.basename(app_path)[:-4]
                    except Exception as e:
                        print(f"Failed to parse iTunesMetadata.plist for {app_path}: {e}")
                # 3. 都没有就用文件夹名
                if not name:
                    name = os.path.basename(app_path)[:-4]
                icon = load_icon_from_cache(app_path, name)
                if not icon:
                    try:
                        icon = get_finder_icon(app_path)
                        if not icon.isNull():
                            save_icon_to_cache(icon, app_path, name)
                    except Exception as e:
                        print(f"Failed to load icon for {app_path}: {e}")
                        icon = QIcon()
                new_apps.append({'name': name, 'icon': icon, 'path': app_path})
        if new_apps:
            all_paths = list(known_paths | found_paths)
            save_app_paths(all_paths)
        self.apps_found.emit({'new_apps': new_apps, 'all_paths': list(found_paths)})

    # def run(self):  # 这个是获取所有 .app 的写法
    #     sync_app_paths()
    #     # 1. 加载本地 app 路径列表
    #     known_paths = set(load_app_paths())
    #     # 2. 实际扫描
    #     app_dirs = ["/Applications", "/System/Applications"]
    #     found_paths = set()
    #     new_apps = []
    #     for app_dir in app_dirs:
    #         for root, dirs, files in os.walk(app_dir):
    #             for item in dirs:
    #                 if not self._running:
    #                     return
    #                 if item.endswith('.app'):
    #                     app_path = os.path.join(root, item)
    #                     found_paths.add(app_path)
    #                     if app_path not in known_paths:
    #                         info_plist = os.path.join(app_path, 'Contents', 'Info.plist')
    #                         if os.path.exists(info_plist):
    #                             try:
    #                                 with open(info_plist, 'rb') as f:
    #                                     plist = plistlib.load(f)
    #                             except Exception:
    #                                 continue
    #                             name = plist.get('CFBundleDisplayName') or plist.get('CFBundleName') or item[:-4]
    #                             icon = load_icon_from_cache(app_path, name)
    #                             if not icon:
    #                                 icon = get_finder_icon(app_path)
    #                                 if icon.isNull():
    #                                     icon_file = plist.get('CFBundleIconFile')
    #                                     if icon_file:
    #                                         if not icon_file.endswith('.icns'):
    #                                             icon_file += '.icns'
    #                                         icon_path = os.path.join(app_path, 'Contents', 'Resources', icon_file)
    #                                         if os.path.exists(icon_path):
    #                                             icon = QIcon(icon_path)
    #                                         else:
    #                                             icon = QIcon()
    #                                     else:
    #                                         icon = QIcon()
    #                                 if not icon.isNull():
    #                                     save_icon_to_cache(icon, app_path, name)
    #                             new_apps.append({'name': name, 'icon': icon, 'path': app_path})
    #     # 3. 如果有新 app，更新本地 app 路径列表
    #     if new_apps:
    #         all_paths = list(known_paths | found_paths)
    #         save_app_paths(all_paths)
    #     self.apps_found.emit({'new_apps': new_apps, 'all_paths': list(found_paths)})

    def stop(self):
        self._running = False

class AppButton(QPushButton):
    def __init__(self, app_info, parent=None, parent_group=None, main_window=None):
        super().__init__(parent)
        self.app_info = app_info
        self.parent_group = parent_group
        self.main_window = main_window
        self.setStyleSheet("background: transparent; border: none;")
        self.setFixedSize(140, 140)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.icon_label.setFixedSize(100, 100)
        pix = app_info['icon'].pixmap(100, 100)
        self.icon_label.setPixmap(pix)
        layout.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.text_label = QLabel()

        # name = app_info['name']
        # font = self.text_label.font()
        # max_width = 200
        #
        # display_text, is_html = get_display_text(name, font, max_width)
        # if is_html:
        #     self.text_label.setTextFormat(Qt.TextFormat.RichText)
        # else:
        #     self.text_label.setTextFormat(Qt.TextFormat.PlainText)
        # self.text_label.setText(display_text)
        # self.text_label.setWordWrap(True)
        # self.text_label.setMaximumWidth(max_width)

        name = app_info['name']
        font = self.text_label.font()
        max_width = 130
        max_lines = 2

        display_text = multiline_elide_with_firstline(name, font, max_width, max_lines)
        self.text_label.setTextFormat(Qt.TextFormat.PlainText)
        self.text_label.setText(display_text)
        self.text_label.setWordWrap(False)  # 关键！不用 Qt 的自动换行
        self.text_label.setMaximumWidth(max_width)

        self.text_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.text_label.setStyleSheet("font-size: 13px;")
        # self.text_label.setWordWrap(True)
        # self.text_label.setMaximumWidth(160)
        # self.text_label.setProperty("wrapMode", QTextOption.WrapMode.WrapAnywhere)  # 关键！

        # metrics = self.text_label.fontMetrics()
        # max_width = 120
        # elided = metrics.elidedText(app_info['name'], Qt.TextElideMode.ElideRight, max_width)
        # self.text_label.setText(elided)
        # self.text_label.setMaximumWidth(max_width)
        # self.text_label.setWordWrap(False)
        # if elided != app_info['name']:
        #     self.text_label.setToolTip(app_info['name'])

        layout.addWidget(self.text_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        # layout.setStretch(0, 3)
        # layout.setStretch(1, 1)
        self.setLayout(layout)
        # 右键菜单设置
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            subprocess.Popen(['open', self.app_info['path']])
            if self.main_window:
                self.main_window.close_main_window()  # 保证恢复 Dock
        else:
            super().mousePressEvent(event)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        light_menu_style = '''
        QMenu {
            background-color: #FFFFFF;
            color: #222222;
            border: 1px solid #CCCCCC;
            border-radius: 12px;
            padding: 4px;
        }
        QMenu::item {
            padding: 8px 32px 8px 24px;
            min-height: 15px;
            border-radius: 6px;
        }
        QMenu::item:selected {
            background-color: #0085FF;
            color: #FFFFFF;
        }
        '''

        dark_menu_style = '''
        QMenu {
            background-color: #232323;
            color: #EEEEEE;
            border: 1px solid #444444;
            border-radius: 12px;
            padding: 4px;
        }
        QMenu::item {
            padding: 8px 32px 8px 24px;
            min-height: 15px;
            border-radius: 6px;
        }
        QMenu::item:selected {
            background-color: #0085FF;
            color: #FFFFFF;
        }
        '''
        if is_dark_theme(self):
            menu.setStyleSheet(dark_menu_style)
        else:
            menu.setStyleSheet(light_menu_style)
    #     menu.setStyleSheet('''
    #     QMenu {
    #     background-color: #FFFFFF;
    #     border: 1px solid #CCCCCC;
    #     border-radius: 12px;
    #     padding: 4px;
    # }
    # QMenu::item {
    #     padding: 8px 32px 8px 24px;
    #     min-height: 15px;
    #     border-radius: 6px;
    # }
    # QMenu::item:selected {
    #     background-color: #0085FF;
    #     color: #FFFFFF;
    # }
    # ''')
        if self.parent_group:
            move_menu = QMenu("Move to another group", self)
            if is_dark_theme(self):
                move_menu.setStyleSheet(dark_menu_style)
            else:
                move_menu.setStyleSheet(light_menu_style)
            # move_menu.setStyleSheet('''
            #     QMenu {
            #     background-color: #FFFFFF;
            #     border: 1px solid #CCCCCC;
            #     border-radius: 12px;
            #     padding: 4px;
            # }
            # QMenu::item {
            #     padding: 8px 32px 8px 24px;
            #     min-height: 15px;
            #     border-radius: 6px;
            # }
            # QMenu::item:selected {
            #     background-color: #0085FF;
            #     color: #FFFFFF;
            # }
            # ''')
            for group in self.main_window.groups:
                if self.parent_group and group is self.parent_group:
                    continue
                move_menu.addAction(group['name'], lambda g=group: self.main_window.move_app_to_group(self, g))
            menu.addMenu(move_menu)
            menu.addAction("Put it back to the main interface", self.move_out_of_group)
        if not self.parent_group:
            group_menu = QMenu("Combine into a group", self)
            for group in self.main_window.groups:
                group_menu.addAction(group['name'], lambda g=group: self.main_window.combine_app_to_group(self, g))
            group_menu.addAction("🆕 New group", lambda: self.main_window.combine_app_to_group(self, None))
            if is_dark_theme(self):
                group_menu.setStyleSheet(dark_menu_style)
            else:
                group_menu.setStyleSheet(light_menu_style)
            # group_menu.setStyleSheet('''
            #         QMenu {
            #         background-color: #FFFFFF;
            #         border: 1px solid #CCCCCC;
            #         border-radius: 12px;
            #         padding: 4px;
            #     }
            #     QMenu::item {
            #         padding: 8px 32px 8px 24px;
            #         min-height: 15px;
            #         border-radius: 6px;
            #     }
            #     QMenu::item:selected {
            #         background-color: #0085FF;
            #         color: #FFFFFF;
            #     }
            #     ''')
            menu.addMenu(group_menu)
        menu.addAction("Move to the trash can", self.move_to_trash)
        menu.exec(self.mapToGlobal(pos))

    def move_out_of_group(self):
        if self.main_window and self.parent_group:
            self.main_window.move_app_out_of_group(self.app_info, self.parent_group)

    def move_to_trash(self):
        subprocess.Popen(['osascript', '-e', f'tell app "Finder" to move POSIX file "{self.app_info["path"]}" to trash'])
        if self.main_window:
            self.main_window.remove_app(self.app_info)

class GroupButton(QPushButton):
    def __init__(self, group, parent=None, main_window=None):
        super().__init__(parent)
        self.group = group
        self.main_window = main_window
        self.setFixedSize(140, 140)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.icon_label.setFixedSize(100, 100)
        pix = group['icon'].pixmap(80, 80)
        self.icon_label.setPixmap(pix)
        layout.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.text_label = QLabel()

        name = group['name']
        font = self.text_label.font()
        max_width = 130
        max_lines = 2

        display_text = multiline_elide_with_firstline(name, font, max_width, max_lines)
        self.text_label.setTextFormat(Qt.TextFormat.PlainText)
        self.text_label.setText(display_text)
        self.text_label.setWordWrap(False)  # 关键！不用 Qt 的自动换行
        self.text_label.setMaximumWidth(max_width)

        self.text_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.text_label.setStyleSheet("font-size: 13px;")
        # self.text_label.setWordWrap(True)
        layout.addWidget(self.text_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        # layout.setStretch(0, 3)
        # layout.setStretch(1, 1)
        self.setLayout(layout)
        # 右键菜单设置
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.main_window.show_group_widget(self.group, group_btn=self)
        else:
            super().mousePressEvent(event)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        light_menu_style = '''
        QMenu {
            background-color: #FFFFFF;
            color: #222222;
            border: 1px solid #CCCCCC;
            border-radius: 12px;
            padding: 4px;
        }
        QMenu::item {
            padding: 8px 32px 8px 24px;
            min-height: 15px;
            border-radius: 6px;
        }
        QMenu::item:selected {
            background-color: #0085FF;
            color: #FFFFFF;
        }
        '''

        dark_menu_style = '''
        QMenu {
            background-color: #232323;
            color: #EEEEEE;
            border: 1px solid #444444;
            border-radius: 12px;
            padding: 4px;
        }
        QMenu::item {
            padding: 8px 32px 8px 24px;
            min-height: 15px;
            border-radius: 6px;
        }
        QMenu::item:selected {
            background-color: #0085FF;
            color: #FFFFFF;
        }
        '''
        if is_dark_theme(self):
            menu.setStyleSheet(dark_menu_style)
        else:
            menu.setStyleSheet(light_menu_style)
    #     menu.setStyleSheet('''
    #     QMenu {
    #     background-color: #FFFFFF;
    #     border: 1px solid #CCCCCC;
    #     border-radius: 16px;
    #     padding: 4px;
    # }
    # QMenu::item {
    #     padding: 8px 32px 8px 24px;
    #     min-height: 15px;
    #     border-radius: 6px;
    # }
    # QMenu::item:selected {
    #     background-color: #0085FF;
    #     color: #FFFFFF;
    # }
    # ''')
        menu.addAction("Rename", self.rename_group)
        menu.addAction("Dissolve this group", self.disband_group)
        menu.exec(self.mapToGlobal(pos))

    def rename_group(self):
        self.main_window.rename_group(self.group)

    def disband_group(self):
        if self.main_window:
            self.main_window.disband_group(self.group)

def rounded_rect_points(rect, radius, num_points=100):
    """返回圆角矩形边框上的点列表，顺时针"""
    points = []
    # 四个角的圆弧，每个弧各占 num_points//4
    for i in range(num_points//4):
        # 左上
        angle = 180 + 90 * (i / (num_points//4))
        x = rect.left() + radius + radius * math.cos(math.radians(angle))
        y = rect.top() + radius + radius * math.sin(math.radians(angle))
        points.append(QPointF(x, y))
    for i in range(num_points//4):
        # 右上
        angle = 270 + 90 * (i / (num_points//4))
        x = rect.right() - radius + radius * math.cos(math.radians(angle))
        y = rect.top() + radius + radius * math.sin(math.radians(angle))
        points.append(QPointF(x, y))
    for i in range(num_points//4):
        # 右下
        angle = 0 + 90 * (i / (num_points//4))
        x = rect.right() - radius + radius * math.cos(math.radians(angle))
        y = rect.bottom() - radius + radius * math.sin(math.radians(angle))
        points.append(QPointF(x, y))
    for i in range(num_points//4):
        # 左下
        angle = 90 + 90 * (i / (num_points//4))
        x = rect.left() + radius + radius * math.cos(math.radians(angle))
        y = rect.bottom() - radius + radius * math.sin(math.radians(angle))
        points.append(QPointF(x, y))
    return points

# def draw_highlight_with_fade(painter, points, start_idx, end_idx, fade_len=10, base_width=4):
#     # 主高光段
#     grad_main = QLinearGradient(points[start_idx], points[end_idx])
#     grad_main.setColorAt(0, QColor(255,255,255,0))  # 半透明白
#     grad_main.setColorAt(1, QColor(255,255,255,255))  # 全白
#     pen_main = QPen(QBrush(grad_main), base_width, cap=Qt.PenCapStyle.RoundCap)
#     painter.setPen(pen_main)
#     path_main = QPainterPath()
#     path_main.moveTo(points[start_idx])
#     for pt in points[start_idx+1:end_idx]:
#         path_main.lineTo(pt)
#     painter.drawPath(path_main)
#
#     # 收尾段
#     fade_start = end_idx
#     fade_end = min(end_idx + fade_len, len(points)-1)
#     grad_fade = QLinearGradient(points[fade_start], points[fade_end])
#     grad_fade.setColorAt(0, QColor(255,255,255,255))  # 全白
#     grad_fade.setColorAt(1, QColor(255,255,255,0))    # 全透明
#     pen_fade = QPen(QBrush(grad_fade), base_width, cap=Qt.PenCapStyle.RoundCap)
#     painter.setPen(pen_fade)
#     path_fade = QPainterPath()
#     path_fade.moveTo(points[fade_start])
#     for pt in points[fade_start+1:fade_end]:
#         path_fade.lineTo(pt)
#     painter.drawPath(path_fade)

def draw_highlight_with_fade(painter, points, start_idx, end_idx, fade_len=10, base_width=4, reverse=False):
    """
    reverse: False=主段从start到end，fade在end后面
             True=主段从end到start，fade在start前面
    """
    if not reverse:
        # 主高光段：从半透明白到全白
        grad_main = QLinearGradient(points[start_idx], points[end_idx])
        grad_main.setColorAt(0, QColor(255,255,255,0))  # 半透明白
        grad_main.setColorAt(1, QColor(255,255,255,255))  # 全白
        pen_main = QPen(QBrush(grad_main), base_width, cap=Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_main)
        path_main = QPainterPath()
        path_main.moveTo(points[start_idx])
        for pt in points[start_idx+1:end_idx]:
            path_main.lineTo(pt)
        painter.drawPath(path_main)

        # 收尾段：从全白到全透明
        fade_start = end_idx
        fade_end = min(end_idx + fade_len, len(points)-1)
        grad_fade = QLinearGradient(points[fade_start], points[fade_end])
        grad_fade.setColorAt(0, QColor(255,255,255,255))  # 全白
        grad_fade.setColorAt(1, QColor(255,255,255,0))    # 全透明
        pen_fade = QPen(QBrush(grad_fade), base_width, cap=Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_fade)
        path_fade = QPainterPath()
        path_fade.moveTo(points[fade_start])
        for pt in points[fade_start+1:fade_end]:
            path_fade.lineTo(pt)
        painter.drawPath(path_fade)
    else:
        # 主高光段：从半透明白到全白（反向）
        grad_main = QLinearGradient(points[end_idx], points[start_idx])
        grad_main.setColorAt(0, QColor(255,255,255,0))  # 半透明白
        grad_main.setColorAt(1, QColor(255,255,255,255))  # 全白
        pen_main = QPen(QBrush(grad_main), base_width, cap=Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_main)
        path_main = QPainterPath()
        path_main.moveTo(points[end_idx])
        for pt in reversed(points[start_idx+1:end_idx+1]):
            path_main.lineTo(pt)
        painter.drawPath(path_main)

        # 收尾段：从全白到全透明（反向）
        fade_start = start_idx
        fade_end = max(start_idx - fade_len, 0)
        grad_fade = QLinearGradient(points[fade_start], points[fade_end])
        grad_fade.setColorAt(0, QColor(255,255,255,255))  # 全白
        grad_fade.setColorAt(1, QColor(255,255,255,0))    # 全透明
        pen_fade = QPen(QBrush(grad_fade), base_width, cap=Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_fade)
        path_fade = QPainterPath()
        path_fade.moveTo(points[fade_start])
        for pt in reversed(points[fade_end:fade_start]):
            path_fade.lineTo(pt)
        painter.drawPath(path_fade)

def create_group_icon(apps,
                     highlight1_start=0.02, highlight1_len=0.22,
                     highlight2_start=0.55, highlight2_len=0.22):
    size = 240
    radius = 56
    icon_size = 56
    spacing = 8
    grid = 3

    # 1. 玻璃背景
    bg_img = QImage(size, size, QImage.Format.Format_ARGB32)
    bg_img.fill(Qt.GlobalColor.transparent)
    painter = QPainter(bg_img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    rect = QRectF(0, 0, size, size)
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    painter.setClipPath(path)
    painter.fillPath(path, QColor(255, 255, 255, 40))
    painter.end()
    from PIL import Image, ImageFilter
    pil_img = Image.fromqimage(bg_img)
    pil_img = pil_img.filter(ImageFilter.GaussianBlur(radius=2))
    bg_img_blur = QImage(pil_img.tobytes("raw", "RGBA"), pil_img.width, pil_img.height, QImage.Format.Format_ARGB32)

    # 2. 画到 QPixmap
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.drawImage(0, 0, bg_img_blur)

    # 3. 画圆角边框
    # border_pen = QPen(QColor(200, 200, 200, 220), 3)
    # painter.setPen(border_pen)
    # painter.drawRoundedRect(rect.adjusted(1.5, 1.5, -1.5, -1.5), radius, radius)

    # 4. 画高光（可自定义长度和位置）
    points = rounded_rect_points(rect.adjusted(3, 3, -3, -3), radius-2, num_points=240)
    total = len(points)

    # 左上高光
    draw_highlight_with_fade(painter, points, start_idx=2, end_idx=int(0.22 * total), fade_len=10, base_width=4,
                             reverse=False)
    # draw_highlight_with_fade(painter, points, start_idx, end_idx, fade_len=10, base_width=4, reverse=False)
    # original:
    # start_idx = int(highlight1_start * total)
    # end_idx = int((highlight1_start + highlight1_len) * total)
    # painter.save()
    # grad = QLinearGradient(points[start_idx], points[end_idx])
    # grad.setColorAt(0, QColor(255,255,255,160))
    # grad.setColorAt(1, QColor(255,255,255,0))
    # pen = QPen(QBrush(grad), 4, cap=Qt.PenCapStyle.RoundCap)
    # painter.setPen(pen)
    # highlight_path = QPainterPath()
    # highlight_path.moveTo(points[start_idx])
    # for pt in points[start_idx+1:end_idx]:
    #     highlight_path.lineTo(pt)
    # painter.drawPath(highlight_path)
    # painter.restore()

    # 右下高光

    draw_highlight_with_fade(painter, points, start_idx=int(0.55 * total), end_idx=int(0.87 * total), fade_len=13,
                             base_width=4, reverse=True)
    # draw_highlight_with_fade(painter, points, start_idx2, end_idx2, fade_len=10, base_width=4, reverse=True)
    # original:
    # start_idx2 = int(highlight2_start * total)
    # end_idx2 = int((highlight2_start + highlight2_len) * total)
    # painter.save()
    # grad2 = QLinearGradient(points[start_idx2], points[end_idx2])
    # grad2.setColorAt(0, QColor(255,255,255,120))
    # grad2.setColorAt(1, QColor(255,255,255,0))
    # pen2 = QPen(QBrush(grad2), 4, cap=Qt.PenCapStyle.RoundCap)
    # painter.setPen(pen2)
    # highlight_path2 = QPainterPath()
    # highlight_path2.moveTo(points[start_idx2])
    # for pt in points[start_idx2+1:end_idx2]:
    #     highlight_path2.lineTo(pt)
    # painter.drawPath(highlight_path2)
    # painter.restore()

    # 5. 画3*3小icon（缩小并居中）
    n = min(9, len(apps))
    total_icons = min(n, 9)
    start_x = (size - (icon_size * grid + spacing * (grid - 1))) // 2
    start_y = (size - (icon_size * grid + spacing * (grid - 1))) // 2
    for i in range(total_icons):
        row, col = divmod(i, 3)
        icon = apps[i]['icon']
        icon_pix = icon.pixmap(icon_size, icon_size)
        x = start_x + col * (icon_size + spacing)
        y = start_y + row * (icon_size + spacing)
        painter.drawPixmap(x, y, icon_pix)

    painter.end()
    return QIcon(pixmap)

class GroupWidget(QWidget):
    closed = pyqtSignal()
    def __init__(self, group, parent=None, main_window=None, close_group_widget=None):
        super().__init__(parent)
        self.group = group
        self.main_window = main_window
        self.close_group_widget = close_group_widget
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        screen = QGuiApplication.primaryScreen().geometry()
        padding_lr = 60
        apps_per_row = 7
        btn_size = 120
        spacing = 32
        content_width = apps_per_row * btn_size + (apps_per_row - 1) * spacing
        group_width = content_width + 2 * padding_lr
        group_width = min(group_width, int(screen.width() * 0.95))
        apps_count = len(group['apps'])
        max_rows = 5
        row_height = 150
        rows = min((apps_count + apps_per_row - 1) // apps_per_row, max_rows)
        extra = 20  # 想再往下 20 像素
        group_height = 100 + rows * row_height + 60 + 60 + extra
        self.setFixedSize(group_width, group_height)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(padding_lr-8, 40, padding_lr-8, 60)
        self.name_label = QLabel(group['name'])
        self.name_label.setFont(QFont("Arial", 20))
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setFixedHeight(100)
        self.name_label.setStyleSheet('''
            background-color: transparent;
            border: 0px;
        ''')
        self.layout.addWidget(self.name_label)
        self.name_label.mouseDoubleClickEvent = self.edit_name
        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet('''
            background-color: transparent;
            border: 0px;
        ''')
        self.grid_widget.setMinimumHeight(5 * 150)
        self.grid_widget.setMinimumWidth(content_width)
        self.layout.addWidget(self.grid_widget)

        self.page_indicator = QHBoxLayout()
        self.page_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_indicator.setSpacing(24)

        self.page_indicator_widget = QWidget()
        self.page_indicator_widget.setStyleSheet('''
            background-color: transparent;
            border: 0px;
        ''')
        self.page_indicator_widget.setLayout(self.page_indicator)
        self.page_indicator_widget.setMaximumWidth(content_width)
        self.page_indicator_widget.setFixedHeight(40)
        self.page_indicator_widget.setMinimumWidth(60)
        self.layout.addWidget(self.page_indicator_widget, alignment=Qt.AlignmentFlag.AlignHCenter)

        w3 = GlassButtonWidget("", on_double_click=self.close_group_widget)
        w3.setLayout(self.layout)
        # w3.setStyleSheet('''
        #     background-color: #f0f0f0;
        #     color: #333333;
        #     border-radius: 36px;
        # ''')
        # w3.setStyleSheet('''
        #     background: qlineargradient(
        #         x1:0, y1:0, x2:0, y2:1,
        #         stop:0 rgba(255,255,255,0.80),
        #         stop:1 rgba(255,255,255,0.35)
        #     );
        #     border-radius: 36px;
        #     border: 1.5px solid rgba(255,255,255,0.5);
        #     box-shadow: 0 8px 32px 0 rgba(31,38,135,0.18);
        #     backdrop-filter: blur(16px);
        # ''')
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(w3)
        self.setLayout(layout)

        self.current_page = 0
        self.items_per_page = 35
        self._mouse_press_pos = None
        self._mouse_move_pos = None
        self.display_apps(self.group['apps'], self.current_page)

        self.focus_index = -1
        self.focused_btn = None

        self.installEventFilter(self)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._cooldown = False
        self._gesture_timer = QElapsedTimer()
        self._min_gesture_interval_ms = 300
        self._cooldown_duration_ms = 1000
        self._scroll_threshold = 20
        self._accumulated_scroll = 0
        self._reset_scroll_timer = QTimer()
        self._reset_scroll_timer.setSingleShot(True)
        self._reset_scroll_timer.timeout.connect(self._reset_scroll)

    def display_apps(self, apps, page=0):
        for w in self.grid_widget.findChildren(QWidget):
            w.setParent(None)
            w.deleteLater()
        apps_per_row = 7
        btn_size = 120
        row_height = 150
        margin_x = 0
        margin_y = 0
        spacing = 32
        start = page * self.items_per_page
        end = start + self.items_per_page
        page_items = apps[start:end]
        for idx, app in enumerate(page_items):
            row, col = divmod(idx, apps_per_row)
            row_count = min(apps_per_row, len(page_items) - row * apps_per_row)
            if row_count == apps_per_row:
                x0 = margin_x
            else:
                x0 = margin_x
            x = x0 + col * (btn_size + spacing)
            y = margin_y + row * row_height
            btn = AppButton(app, self, parent_group=self.group, main_window=self.main_window)
            btn.setParent(self.grid_widget)
            btn.move(x, y)
            btn.show()
        self.update_page_indicator(len(apps))

        self.focus_index = -1
        self.focused_btn = None

    def update_page_indicator(self, total_items):
        while self.page_indicator.count():
            item = self.page_indicator.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        total_pages = max(1, (total_items + self.items_per_page - 1) // self.items_per_page)
        dot_width = 40
        spacing = self.page_indicator.spacing()
        total_width = total_pages * dot_width + (total_pages - 1) * spacing
        self.page_indicator_widget.setFixedWidth(min(total_width, self.width() - 120))
        for i in range(total_pages):
            dot = QPushButton("●" if i == self.current_page else "○")
            dot.setFixedSize(dot_width, dot_width)
            if is_dark_theme(QApplication.instance()):
                dot_color = "#CCCCCC"
            else:
                dot_color = "#666666"
            dot.setStyleSheet(f"border:none; font-size:18px; color: {dot_color};")
            # dot.setStyleSheet("border:none; font-size:18px; color: #666;")
            dot.clicked.connect(lambda checked, idx=i: self.goto_page(idx))
            self.page_indicator.addWidget(dot)

    # def goto_page(self, page):
    #     self.current_page = page
    #     self.display_apps(self.group['apps'], self.current_page)
    # gotoanimation
    def goto_page(self, page):
        total_pages = max(1, (len(self.group['apps']) + self.items_per_page - 1) // self.items_per_page)
        if page < 0 or page >= total_pages or page == self.current_page:
            return
        direction = "left" if page > self.current_page else "right"
        self.animate_page_transition(page, direction)
        self.current_page = page

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._mouse_press_pos = event.position()
            self._mouse_move_pos = event.position()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._mouse_press_pos is not None:
            self._mouse_move_pos = event.position()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._mouse_press_pos is not None and self._mouse_move_pos is not None:
            dx = self._mouse_move_pos.x() - self._mouse_press_pos.x()
            if abs(dx) > 80:
                total_pages = max(1, (len(self.group['apps']) + self.items_per_page - 1) // self.items_per_page)
                if dx < 0:
                    self.goto_page(min(self.current_page + 1, total_pages - 1))
                else:
                    self.goto_page(max(self.current_page - 1, 0))
        self._mouse_press_pos = None
        self._mouse_move_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.close_group_widget:
            self.close_group_widget()

    def edit_name(self, event):
        parent = self.name_label.parentWidget()
        geo = self.name_label.geometry()
        self.name_edit = QLineEdit(self.group['name'], parent)
        self.name_edit.setFont(self.name_label.font())
        self.name_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_edit.setGeometry(geo)
        self.name_edit.setFixedHeight(self.name_label.height())
        self.name_edit.setStyleSheet("background: transparent; border: none;")
        self.name_edit.show()
        self.name_label.hide()
        self.grid_widget.hide()  # 新增：重命名时隐藏 grid_widget
        self.page_indicator_widget.hide()
        self.name_edit.returnPressed.connect(self.save_name)
        self.name_edit.setFocus()

    def save_name(self):
        new_name = self.name_edit.text()
        self.group['name'] = new_name
        self.name_label.setText(new_name)
        self.name_label.show()
        self.name_edit.deleteLater()
        self.grid_widget.show()  # 新增：重命名后恢复 grid_widget
        self.page_indicator_widget.show()
        if self.main_window:
            self.main_window.refresh_groups()
        save_groups(self.main_window.groups)

    # def keyPressEvent(self, event):
    #     if event.key() == Qt.Key.Key_Left:
    #         self.goto_page(max(self.current_page - 1, 0))
    #         return
    #     elif event.key() == Qt.Key.Key_Right:
    #         total_pages = max(1, (len(self.group['apps']) + self.items_per_page - 1) // self.items_per_page)
    #         self.goto_page(min(self.current_page + 1, total_pages - 1))
    #         return
    #     elif event.key() == Qt.Key.Key_Space:
    #         self.focus_next_btn()
    #         return
    #     elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
    #         if self.focused_btn:
    #             if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
    #                 pos = self.focused_btn.rect().center()
    #                 self.focused_btn.show_context_menu(pos)
    #             else:
    #                 self.focused_btn.click()
    #         return
    #     else:
    #         super().keyPressEvent(event)

    def focus_next_btn(self):
        btns = [w for w in self.grid_widget.findChildren(AppButton)]
        if not btns:
            return
        if self.focused_btn not in btns:
            self.focus_index = -1
            self.focused_btn = None
        if self.focused_btn:
            self.focused_btn.icon_label.setStyleSheet("")
        self.focus_index = (self.focus_index + 1) % len(btns)
        self.focused_btn = btns[self.focus_index]
        #self.focused_btn.setStyleSheet(self.focused_btn.styleSheet() + "border: 2px solid #0085FF;")
        # 只给icon_label加边框
        self.focused_btn.icon_label.setStyleSheet(
            "border: 1.5px solid #0085FF; border-radius: 24px; padding: 0px;"
        )
        self.setFocus()

    def focus_prev_btn(self):
        btns = [w for w in self.grid_widget.findChildren(AppButton)]
        if not btns:
            return
        if self.focused_btn not in btns:
            self.focus_index = -1
            self.focused_btn = None
        if self.focused_btn:
            self.focused_btn.icon_label.setStyleSheet("")
        self.focus_index = (self.focus_index - 1 + len(btns)) % len(btns)
        self.focused_btn = btns[self.focus_index]
        # self.focused_btn.setStyleSheet(self.focused_btn.styleSheet() + "border: 2px solid #0085FF;")
        # 只给icon_label加边框
        self.focused_btn.icon_label.setStyleSheet(
            "border: 1.5px solid #0085FF; border-radius: 24px; padding: 0px;"
        )
        self.setFocus()

    def focus_up_btn(self):
        btns = [w for w in self.grid_widget.findChildren(AppButton)]
        if not btns:
            return
        for btn in btns:
            btn.icon_label.setStyleSheet("")
        apps_per_row = 7
        if self.focus_index == -1:
            self.focus_index = 0
        else:
            self.focus_index = (self.focus_index - apps_per_row) % len(btns)
        self.focused_btn = btns[self.focus_index]
        self.focused_btn.icon_label.setStyleSheet(
            "border: 1.5px solid #0085FF; border-radius: 24px; padding: 0px;"
        )
        self.setFocus()

    def focus_down_btn(self):
        btns = [w for w in self.grid_widget.findChildren(AppButton)]
        if not btns:
            return
        for btn in btns:
            btn.icon_label.setStyleSheet("")
        apps_per_row = 7
        if self.focus_index == -1:
            self.focus_index = 0
        else:
            self.focus_index = (self.focus_index + apps_per_row) % len(btns)
        self.focused_btn = btns[self.focus_index]
        self.focused_btn.icon_label.setStyleSheet(
            "border: 1.5px solid #0085FF; border-radius: 24px; padding: 0px;"
        )
        self.setFocus()

    def eventFilter(self, obj, event):
        if event.type() == event.Type.KeyPress:
            return self.handle_key_event(event)
        return super().eventFilter(obj, event)

    def handle_key_event(self, event):
        if event.key() == Qt.Key.Key_Left:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.move_focused_btn_left()
                return True
            self.goto_page(max(self.current_page - 1, 0))
            return True
        elif event.key() == Qt.Key.Key_Right:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.move_focused_btn_right()
                return True
            total_pages = max(1, (len(self.group['apps']) + self.items_per_page - 1) // self.items_per_page)
            self.goto_page(min(self.current_page + 1, total_pages - 1))
            return True
        elif event.key() == Qt.Key.Key_Space:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.focus_prev_btn()
            else:
                self.focus_next_btn()
            return True
        elif event.key() == Qt.Key.Key_Tab:
            if self.close_group_widget:
                self.close_group_widget()
            return True
        elif event.key() == Qt.Key.Key_Up:
            self.focus_up_btn()
            return True
        elif event.key() == Qt.Key.Key_Down:
            self.focus_down_btn()
            return True
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.focused_btn is None:
                return False  # 新增：没有选中的按钮时直接返回，避免报错
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                pos = self.focused_btn.rect().center()
                self.focused_btn.show_context_menu(pos)
            else:
                # 计算本地和全局坐标
                local_pos = QPointF(self.focused_btn.rect().center())
                global_pos = QPointF(self.focused_btn.mapToGlobal(self.focused_btn.rect().center()))
                mouse_event = QMouseEvent(
                    QEvent.Type.MouseButtonPress,
                    local_pos,
                    global_pos,
                    Qt.MouseButton.LeftButton,
                    Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier
                )
                QApplication.sendEvent(self.focused_btn, mouse_event)
                mouse_event_release = QMouseEvent(
                    QEvent.Type.MouseButtonRelease,
                    local_pos,
                    global_pos,
                    Qt.MouseButton.LeftButton,
                    Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier
                )
                QApplication.sendEvent(self.focused_btn, mouse_event_release)
            return True
        return False

    def wheelEvent(self, event):
        delta_x = event.angleDelta().x()
        if delta_x == 0:
            return

        if self._cooldown:
            return

        if self._gesture_timer.isValid() and self._gesture_timer.elapsed() < self._min_gesture_interval_ms:
            return

        self._gesture_timer.start()
        self._accumulated_scroll += delta_x
        self._reset_scroll_timer.start(2000)

        if self._accumulated_scroll >= self._scroll_threshold:
            self._start_cooldown()
            self._reset_scroll()
            self.goto_page(max(self.current_page - 1, 0))
        elif self._accumulated_scroll <= -self._scroll_threshold:
            self._start_cooldown()
            self._reset_scroll()
            total_pages = max(1, (len(self.group['apps']) + self.items_per_page - 1) // self.items_per_page)
            self.goto_page(min(self.current_page + 1, total_pages - 1))

    def _start_cooldown(self):
        self._cooldown = True
        QTimer.singleShot(self._cooldown_duration_ms, self._end_cooldown)

    def _end_cooldown(self):
        self._cooldown = False

    def _reset_scroll(self):
        self._accumulated_scroll = 0

    def move_focused_btn_left(self):
        if not self.focused_btn:
            return
        for idx, app in enumerate(self.group['apps']):
            if self.focused_btn.app_info == app:
                break
        else:
            return
        if idx == 0:
            return
        self.group['apps'][idx], self.group['apps'][idx - 1] = self.group['apps'][idx - 1], self.group['apps'][idx]
        self.group['icon'] = create_group_icon(self.group['apps'])  # 立即刷新缩略图
        save_groups(self.main_window.groups)
        new_page = (idx - 1) // self.items_per_page
        self.current_page = new_page
        self.display_apps(self.group['apps'], self.current_page)
        self.focus_index = (idx - 1) % self.items_per_page
        self.set_focus_by_global_index(idx - 1)

    def move_focused_btn_right(self):
        if not self.focused_btn:
            return
        for idx, app in enumerate(self.group['apps']):
            if self.focused_btn.app_info == app:
                break
        else:
            return
        if idx == len(self.group['apps']) - 1:
            return
        self.group['apps'][idx], self.group['apps'][idx + 1] = self.group['apps'][idx + 1], self.group['apps'][idx]
        self.group['icon'] = create_group_icon(self.group['apps'])  # 立即刷新缩略图
        save_groups(self.main_window.groups)
        new_page = (idx + 1) // self.items_per_page
        self.current_page = new_page
        self.display_apps(self.group['apps'], self.current_page)
        self.focus_index = (idx + 1) % self.items_per_page
        self.set_focus_by_global_index(idx + 1)

    def set_focus_by_global_index(self, global_idx):
        grid = self.grid_widget
        page_start = self.current_page * self.items_per_page
        rel_idx = global_idx - page_start
        btns = [w for w in grid.findChildren(AppButton)]
        if 0 <= rel_idx < len(btns):
            self.focused_btn = btns[rel_idx]
            self.focused_btn.icon_label.setStyleSheet(
                "border: 1.5px solid #0085FF; border-radius: 24px; padding: 0px;"
            )
            self.focus_index = rel_idx
            self.setFocus()

    def animate_page_transition(self, new_page, direction="left"):
        grid = self.grid_widget
        old_btns = [w for w in grid.findChildren(AppButton)]
        if not old_btns:
            self.display_apps(self.group['apps'], new_page)
            return

        screen_width = self.width()
        speed = 6000
        anim_group_out = QParallelAnimationGroup(self)
        for btn in old_btns:
            start_pos = btn.pos()
            if direction == "left":
                end_pos = QPoint(-btn.width(), start_pos.y())
                distance = start_pos.x() + btn.width()
            else:  # direction == "right"
                end_pos = QPoint(screen_width + btn.width(), start_pos.y())
                distance = screen_width - start_pos.x() + btn.width()
            duration = int(distance / speed * 1000)
            anim = QPropertyAnimation(btn, b"pos", self)
            anim.setDuration(duration)
            anim.setStartValue(start_pos)
            anim.setEndValue(end_pos)
            anim.setEasingCurve(QEasingCurve.Type.OutCurve)
            anim_group_out.addAnimation(anim)

        def cleanup_old_btns():
            for btn in old_btns:
                btn.hide()
                btn.setParent(None)
                btn.deleteLater()
            self.display_apps(self.group['apps'], new_page)

        anim_group_out.finished.connect(cleanup_old_btns)
        anim_group_out.start()
        self.anim = anim_group_out


class Window(AcrylicWindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("Acrylic Window")
        self.titleBar.raise_()

        # customize acrylic effect
        self.windowEffect.setAcrylicEffect(self.winId(), "F2F2F299")

        # you can also enable mica effect on Win11
        # self.windowEffect.setMicaEffect(self.winId(), isDarkMode=False, isAlt=False)

        # 移除默认的右上角按钮
        self.titleBar.minBtn.hide()
        self.titleBar.maxBtn.hide()
        self.titleBar.closeBtn.hide()

        self.setSystemTitleBarButtonVisible(True)

        # 设置圆角半径为20
        self.set_rounded_corners(0)

    def set_rounded_corners(self, radius):
        """设置窗口圆角蒙版"""
        path = QPainterPath()
        rect = QRectF(0, 0, self.width(), self.height())
        path.addRoundedRect(rect, radius, radius)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)

    def resizeEvent(self, event):
        """窗口大小变化时，自动更新圆角蒙版"""
        self.set_rounded_corners(0)
        super().resizeEvent(event)


class MainContentWidget(QWidget):
    def __init__(self, parent, apps, groups, main_window):
        super().__init__(parent)
        self.setGeometry(parent.geometry())
        self.setAutoFillBackground(True)
        self.search_bar = SearchLineEdit()
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.setFixedWidth(500)
        # self.search_bar.setStyleSheet("""
        #     QLineEdit {
        #         border-radius: 18px;
        #         border: 1px solid rgba(204, 204, 204, 0.5);  /* 你的主色调，未聚焦时 */
        #         padding-left: 20px;          /* 给左侧icon留空间 */
        #         font-size: 16px;
        #         background: rgba(255,255,255,0.35);
        #         height: 36px;
        #     }
        #     QLineEdit:focus {
        #         border: 1.5px solid #0085FF; /* 聚焦时高亮色，可自定义 */
        #         background: rgba(255,255,255,0.35);
        #     }
        # """)

        # 搜索icon
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(0)
        search_layout.addStretch()
        search_layout.addWidget(self.search_bar)
        search_layout.addStretch()
        self.search_widget = QWidget()
        self.search_widget.setStyleSheet('''background-color: transparent;''')
        self.search_widget.setLayout(search_layout)
        self.search_widget.setFixedHeight(40)

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)

        self.page_indicator = QHBoxLayout()
        self.page_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.page_indicator_widget = QWidget()
        self.page_indicator_widget.setLayout(self.page_indicator)
        self.page_indicator_widget.setMaximumWidth(800)
        self.page_indicator_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        w3 = Window()
        blay3 = QVBoxLayout()
        blay3.setContentsMargins(80, 60, 80, 60)
        blay3.addWidget(self.search_widget)
        blay3.addWidget(self.grid_widget)
        blay3.addWidget(self.page_indicator_widget, alignment=Qt.AlignmentFlag.AlignHCenter)
        w3.setLayout(blay3)
        #w3.setObjectName("Main")

        blayend = QHBoxLayout()
        blayend.setContentsMargins(0, 0, 0, 0)
        blayend.addWidget(w3)
        self.setLayout(blayend)

        self.apps = apps
        self.groups = groups
        self.main_window = main_window
        self.search_bar.textChanged.connect(self.main_window.filter_apps)


class LaunchpadWindow(QWidget):
    def __init__(self, apps):
        super().__init__()
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: rgba(255,255,255,1); border-radius: 0px;")
        self.setWindowOpacity(1)
        self._mouse_press_pos = None
        self._mouse_move_pos = None

        self.apps = apps
        self.groups = load_groups(self.apps)
        self.current_page = 0
        self.items_per_page = 35
        #self.filtered_apps = [a for a in self.apps if not any(a in g['apps'] for g in self.groups)]

        # main_order
        self.app_dict = {a['path']: a for a in self.apps}
        self.group_dict = {g['name']: g for g in self.groups}

        main_order = load_main_order()
        self.main_order = []
        for oid in main_order:
            if oid in self.group_dict:
                self.main_order.append(('group', self.group_dict[oid]))
            elif oid in self.app_dict:
                self.main_order.append(('app', self.app_dict[oid]))
        # 加入未在 main_order 的 group/app
        for g in self.groups:
            if ('group', g) not in self.main_order:
                self.main_order.append(('group', g))
        for a in self.apps:
            if ('app', a) not in self.main_order and not any(a in g['apps'] for g in self.groups):
                self.main_order.append(('app', a))

        order = load_app_order()
        app_dict = {a['path']: a for a in self.apps if not any(a in g['apps'] for g in self.groups)}
        ordered_apps = [app_dict[p] for p in order if p in app_dict]
        unordered_apps = [a for p, a in app_dict.items() if p not in order]
        self.filtered_apps = ordered_apps + unordered_apps

        self.group_widget = None

        self.main_content = MainContentWidget(self, self.apps, self.groups, self)
        self.main_content.setGeometry(self.geometry())
        self.display_apps(self.filtered_apps, self.current_page)

        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self.start_background_scan)
        self.scan_timer.start(20000)  # 20秒
        self.scan_worker = None

        self.focus_index = -1
        self.focused_btn = None

        self.installEventFilter(self)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # 添加菜单栏
        self.menu_bar = QMenuBar(self)
        self.menu_bar.setGeometry(0, 0, 300, 24)  # 你可以根据需要调整宽度
        self.menu = self.menu_bar.addMenu("Actions")
        # 新增菜单项：显示主界面
        self.show_main_action = QAction("⭕️ Display the main interface", self)
        self.menu.addAction(self.show_main_action)
        self.show_main_action.triggered.connect(self.show_main_window)
        # 新增菜单项：关闭主界面
        self.close_main_action = QAction("❌ Close the main interface", self)
        self.menu.addAction(self.close_main_action)
        self.close_main_action.triggered.connect(self.close_main_window)

        self.menu.addSeparator()

        # 新增菜单项：更新指定App图标缓存
        self.update_single_app_icon_action = QAction("❇️ Update the specified app icon cache", self)
        self.menu.addAction(self.update_single_app_icon_action)
        self.update_single_app_icon_action.triggered.connect(self.update_single_app_icon)
        # 新增菜单项：清除所有图标缓存
        self.clear_cache_action = QAction("🧹 Clear icon cache and refresh all apps", self)
        self.menu.addAction(self.clear_cache_action)
        self.clear_cache_action.triggered.connect(self.clear_icon_cache_and_refresh)

        self.menu.addSeparator()

        # 新增菜单项：始终隐藏dock
        self.always_hide_dock_action = QAction("🌀 Always hide Dock", self)
        self.menu.addAction(self.always_hide_dock_action)
        self.always_hide_dock_action.setCheckable(True)
        self.always_hide_dock_action.triggered.connect(self.always_hide_dock)
        # login
        self.action10 = QAction("🛠️ Start on login")
        self.action10.setCheckable(True)
        self.menu.addAction(self.action10)
        plist_filename = 'com.ryanthehito.raspberry.plist'
        launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
        launch_agents_dir.mkdir(parents=True, exist_ok=True)
        destination = launch_agents_dir / plist_filename
        if os.path.exists(destination):
            self.action10.setChecked(True)
        else:
            self.action10.setChecked(False)
        self.action10.triggered.connect(self.login_start)
        # restart
        self.action8 = QAction("🔁 Click to restart")
        self.menu.addAction(self.action8)
        self.action8.triggered.connect(self.restart_app)

        self.menu.addSeparator()

        # 新增菜单项：运行 lporg
        self.run_lporg_action = QAction("▶️ Back up Launchpad groups to Raspberry (Paid feature)", self)
        self.menu.addAction(self.run_lporg_action)
        self.run_lporg_action.triggered.connect(self.run_lporg)
        # 新增菜单项：备份 group
        self.backup_groups_action = QAction("🗂️ Backup current groups (Paid feature)", self)
        self.menu.addAction(self.backup_groups_action)
        self.backup_groups_action.triggered.connect(self.backup_groups)
        # 新增菜单项：恢复备份
        self.restore_backup_action = QAction("🔄 Restore backups (Paid feature)", self)
        self.menu.addAction(self.restore_backup_action)
        self.restore_backup_action.triggered.connect(self.restore_backup)

        # 新增 About 菜单
        self.about_menu = self.menu_bar.addMenu("Info")
        # 示例：添加 About 菜单项
        self.about_action = QAction("🆕 Check for Updates", self)
        self.win_update = WindowUpdate()
        self.about_action.triggered.connect(self.win_update.activate)
        self.about_menu.addAction(self.about_action)

        self.help_action = QAction("ℹ️ About this app", self)
        self.win_about = WindowAbout()
        self.help_action.triggered.connect(self.win_about.activate)
        self.about_menu.addAction(self.help_action)

        self.website_action = QAction("🔤 Guide and Support", self)
        self.win_permission = PermissionInfoWidget()
        self.website_action.triggered.connect(self.win_permission.show_window)
        self.about_menu.addAction(self.website_action)

        self.clear_cache_worker = None

        self._always_hide_dock = False

        # 滑动翻页
        self._cooldown = False
        self._gesture_timer = QElapsedTimer()
        self._min_gesture_interval_ms = 300
        self._cooldown_duration_ms = 1000
        self._scroll_threshold = 20
        self._accumulated_scroll = 0
        self._reset_scroll_timer = QTimer()
        self._reset_scroll_timer.setSingleShot(True)
        self._reset_scroll_timer.timeout.connect(self._reset_scroll)

        self.setFocus()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._mouse_press_pos = event.position()
            self._mouse_move_pos = event.position()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._mouse_press_pos is not None:
            self._mouse_move_pos = event.position()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.group_widget and self.group_widget.isVisible():
            self._mouse_press_pos = None
            self._mouse_move_pos = None
            super().mouseReleaseEvent(event)
            return

        if self._mouse_press_pos is not None and self._mouse_move_pos is not None:
            dx = self._mouse_move_pos.x() - self._mouse_press_pos.x()
            if abs(dx) > 80:
                if dx < 0:
                    self.goto_page(min(self.current_page + 1, self.total_pages() - 1))
                else:
                    self.goto_page(max(self.current_page - 1, 0))
        self._mouse_press_pos = None
        self._mouse_move_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.close_main_window()

    def total_pages(self):
        return max(1, (len(self.groups) + len(self.filtered_apps) + self.items_per_page - 1) // self.items_per_page)

    def display_apps(self, apps, page=0):
        grid_layout = self.main_content.grid_layout
        for i in reversed(range(grid_layout.count())):
            grid_layout.itemAt(i).widget().setParent(None)
        start = page * self.items_per_page
        end = start + self.items_per_page

        # 判断是否在搜索
        is_searching = bool(self.main_content.search_bar.text().strip())
        if is_searching:
            # 只显示搜索到的app
            page_items = [('app', app) for app in apps[start:end]]
        else:
            # 正常显示 group + app
            page_items = self.main_order[start:end]

        for idx, (typ, obj) in enumerate(page_items):
            row, col = divmod(idx, 7)
            if row >= 5:
                break
            if typ == 'group':
                btn = GroupButton(obj, self.main_content.grid_widget, main_window=self)
            else:
                btn = AppButton(obj, self.main_content.grid_widget, main_window=self)
            grid_layout.addWidget(btn, row, col)

        # 补齐空白按钮
        total = len(page_items)
        for idx in range(total, 35):
            row, col = divmod(idx, 7)
            if row >= 5:
                break
            btn = EmptyButton(main_window=self, parent=self.main_content.grid_widget)
            grid_layout.addWidget(btn, row, col)

        # 指示器数量也要区分
        if is_searching:
            self.update_page_indicator(len(apps))
        else:
            self.update_page_indicator(len(self.main_order))
        self.focus_index = -1
        self.focused_btn = None

    def update_page_indicator(self, total_items):
        page_indicator = self.main_content.page_indicator
        while page_indicator.count():
            item = page_indicator.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        total_pages = self.total_pages()
        for i in range(total_pages):
            dot = QPushButton("●" if i == self.current_page else "○")
            dot.setFixedSize(24, 24)
            if is_dark_theme(QApplication.instance()):
                dot_color = "#CCCCCC"
            else:
                dot_color = "#666666"
            dot.setStyleSheet(f"border:none; font-size:18px; color: {dot_color};")
            # dot.setStyleSheet("border:none; font-size:18px; color: #666;")
            dot.clicked.connect(lambda checked, idx=i: self.goto_page(idx))
            page_indicator.addWidget(dot)

    # def goto_page(self, page):
    #     self.current_page = page
    #     self.display_apps(self.filtered_apps, self.current_page)
    # goto animation
    def goto_page(self, page):
        total_pages = self.total_pages()
        if page < 0 or page >= total_pages or page == self.current_page:
            return
        direction = "left" if page > self.current_page else "right"
        self.current_page = page
        self.update_page_indicator(
            len(self.main_order) if not self.main_content.search_bar.text().strip() else len(self.filtered_apps))
        is_searching = bool(self.main_content.search_bar.text().strip())
        if is_searching:  # remove animation when searching
            # page_items = [('app', app) for app in
            #               self.filtered_apps[page * self.items_per_page:(page + 1) * self.items_per_page]]
            self.current_page = page
            self.display_apps(self.filtered_apps, self.current_page)
        else:
            page_items = self.main_order[page * self.items_per_page:(page + 1) * self.items_per_page]
            self.animate_page_transition(page_items, direction)

    def filter_apps(self, text):
        if not text.strip():
            self.reset_layout()  # 恢复初始界面
            return
        self.filtered_apps = [a for a in self.apps if text.lower() in a['name'].lower()]
        self.current_page = 0
        self.display_apps(self.filtered_apps, self.current_page)

    def reset_layout(self):
        # 恢复到最初的界面，比如只显示未分组 app
        order = load_app_order()
        app_dict = {a['path']: a for a in self.apps if not any(a in g['apps'] for g in self.groups)}
        ordered_apps = [app_dict[p] for p in order if p in app_dict]
        unordered_apps = [a for p, a in app_dict.items() if p not in order]
        self.filtered_apps = ordered_apps + unordered_apps
        self.current_page = 0
        self.display_apps(self.filtered_apps, self.current_page)

    def combine_app_to_group(self, app_btn, group):
        if group is None:
            group = {'name': 'New Group', 'apps': [app_btn.app_info], 'icon': create_group_icon([app_btn.app_info])}
            self.groups.append(group)
            # 新增：将新 group 加在所有 group 类型的末尾
            last_group_idx = -1
            for idx, (typ, obj) in enumerate(self.main_order):
                if typ == 'group':
                    last_group_idx = idx
            insert_idx = last_group_idx + 1
            self.main_order.insert(insert_idx, ('group', group))
        else:
            if app_btn.app_info not in group['apps']:
                group['apps'].append(app_btn.app_info)
                group['icon'] = create_group_icon(group['apps'])
        # 从 filtered_apps 移除
        if app_btn.app_info in self.filtered_apps:
            self.filtered_apps.remove(app_btn.app_info)
        # 从 main_order 移除
        for idx, (typ, obj) in enumerate(self.main_order):
            if typ == 'app' and obj == app_btn.app_info:
                del self.main_order[idx]
                break
        save_groups(self.groups)
        self.filtered_apps = [a for a in self.apps if not any(a in g['apps'] for g in self.groups)]
        self.display_apps(self.filtered_apps, self.current_page)
        self.save_current_order()

    def move_app_to_group(self, app_btn, target_group):
        # 只允许从组内移动到其他组
        from_group = None
        for group in self.groups:
            if app_btn.app_info in group['apps']:
                group['apps'].remove(app_btn.app_info)
                group['icon'] = create_group_icon(group['apps'])
                from_group = group
        if app_btn.app_info not in target_group['apps']:
            target_group['apps'].append(app_btn.app_info)
            target_group['icon'] = create_group_icon(target_group['apps'])
        save_groups(self.groups)
        self.filtered_apps = [a for a in self.apps if not any(a in g['apps'] for g in self.groups)]
        self.display_apps(self.filtered_apps, self.current_page)
        # 刷新当前组视图（如果有打开的组窗口且是from_group）
        if self.group_widget and from_group and self.group_widget.group is from_group:
            self.group_widget.display_apps(from_group['apps'], self.group_widget.current_page)

    def show_group_widget(self, group, group_btn=None):
        if self.group_widget:
            self.group_widget.hide()
        self.main_content.search_widget.hide()
        self.main_content.grid_widget.hide()
        self.main_content.page_indicator_widget.hide()
        for i in range(self.main_content.page_indicator.count()):
            item = self.main_content.page_indicator.itemAt(i)
            widget = item.widget()
            if widget:
                widget.hide()
        self.group_widget = GroupWidget(group, self, main_window=self, close_group_widget=self.close_group_widget)
        self.group_widget.setParent(self)
        group_width = self.group_widget.width()
        group_height = self.group_widget.height()
        if group_btn is not None:
            btn_rect = group_btn.geometry()
            start_pos = btn_rect.topLeft()
            start_size = btn_rect.size()
            self._last_group_btn_rect = btn_rect
        else:
            start_pos = QPoint(self.width() // 2, self.height() // 2)
            start_size = QSize(10, 10)
            self._last_group_btn_rect = QRect(start_pos, start_size)
        end_pos = QPoint((self.width() - group_width) // 2, (self.height() - group_height) // 2)
        end_size = QSize(group_width, group_height)

        self.group_widget.setGeometry(QRect(start_pos, start_size))
        self.group_widget.setFixedSize(start_size)
        self.group_widget.hide()
        self.group_widget.repaint()

        # 分别动画
        pos_anim = QPropertyAnimation(self.group_widget, b"pos")
        pos_anim.setDuration(200)
        pos_anim.setStartValue(start_pos)
        pos_anim.setEndValue(end_pos)
        pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        size_anim = QPropertyAnimation(self.group_widget, b"dummy")  # dummy属性
        size_anim.setDuration(250)  # 缩放慢一点
        size_anim.setStartValue(start_size)
        size_anim.setEndValue(end_size)
        size_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        size_anim.valueChanged.connect(lambda value: self.group_widget.setFixedSize(value))

        group = QParallelAnimationGroup()
        group.addAnimation(pos_anim)
        group.addAnimation(size_anim)

        # 动画开始时再 show
        def on_anim_start():
            self.group_widget.show()

        group.stateChanged.connect(
            lambda new, old: on_anim_start() if new == QAbstractAnimation.State.Running else None)

        group.start()
        self.anim = group  # 防止被垃圾回收

    def close_group_widget(self):
        if self.group_widget:
            # 目标位置和大小
            btn_rect = self._last_group_btn_rect
            end_pos = btn_rect.topLeft()
            end_size = QSize(0, 0)

            # 当前的位置和大小
            start_pos = self.group_widget.pos()
            start_size = self.group_widget.size()

            # 位移动画
            pos_anim = QPropertyAnimation(self.group_widget, b"pos")
            pos_anim.setDuration(150)
            pos_anim.setStartValue(start_pos)
            pos_anim.setEndValue(end_pos)
            pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

            # 缩放动画（用 valueChanged 手动 setFixedSize）
            size_anim = QPropertyAnimation(self.group_widget, b"dummy")
            size_anim.setDuration(150)
            size_anim.setStartValue(start_size)
            size_anim.setEndValue(end_size)
            size_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            size_anim.valueChanged.connect(lambda value: self.group_widget.setFixedSize(value))

            group = QParallelAnimationGroup()
            group.addAnimation(pos_anim)
            group.addAnimation(size_anim)
            group.finished.connect(self._close_group_widget)
            group.start()
            self.anim = group  # 防止被垃圾回收

    def _close_group_widget(self):
        self.group_widget.hide()
        self.group_widget = None
        self.main_content.search_widget.show()
        self.main_content.grid_widget.show()
        self.main_content.page_indicator_widget.show()
        for i in range(self.main_content.page_indicator.count()):
            item = self.main_content.page_indicator.itemAt(i)
            widget = item.widget()
            if widget:
                widget.show()

    def rename_group(self, group):
        self.show_group_widget(group)
        self.anim.finished.connect(lambda: self.group_widget.edit_name(None))

    def refresh_groups(self):
        for group in self.groups:
            group['icon'] = create_group_icon(group['apps'])
        self.display_apps(self.filtered_apps, self.current_page)
        save_groups(self.groups)
        self.main_content.search_widget.hide()
        self.main_content.grid_widget.hide()
        for i in range(self.main_content.page_indicator.count()):
            item = self.main_content.page_indicator.itemAt(i)
            widget = item.widget()
            if widget:
                widget.hide()

    def remove_app(self, app_info):
        # 从所有数据结构中移除
        if app_info in self.apps:
            self.apps.remove(app_info)
        if app_info in self.filtered_apps:
            self.filtered_apps.remove(app_info)
        for group in self.groups:
            if app_info in group['apps']:
                group['apps'].remove(app_info)
                group['icon'] = create_group_icon(group['apps'])
        # 从 main_order 里移除
        self.main_order = [
            (typ, obj) for (typ, obj) in self.main_order
            if not (typ == 'app' and obj == app_info)
        ]
        # 移除后刷新
        save_groups(self.groups)
        self.save_current_order()
        self.display_apps(self.filtered_apps, self.current_page)

    # def disband_group(self, group):
    #     # 1. 找到 group 在 main_order 的索引
    #     group_idx = None
    #     for idx, (typ, obj) in enumerate(self.main_order):
    #         if typ == 'group' and obj == group:
    #             group_idx = idx
    #             break
    #
    #     # 2. 将组内所有 app 放回主界面（如果不在其它组），并插入 main_order
    #     insert_idx = group_idx if group_idx is not None else len(self.main_order)
    #     apps_to_add = []
    #     for app in group['apps']:
    #         in_other_group = any(app in g['apps'] for g in self.groups if g is not group)
    #         if not in_other_group:
    #             if app not in self.filtered_apps:
    #                 self.filtered_apps.append(app)
    #             apps_to_add.append(app)
    #
    #     # 3. 从 groups 移除
    #     if group in self.groups:
    #         self.groups.remove(group)
    #     save_groups(self.groups)
    #
    #     # 4. 从 main_order 移除该 group
    #     self.main_order = [(typ, obj) for (typ, obj) in self.main_order if not (typ == 'group' and obj == group)]
    #
    #     # 5. 把 apps_to_add 插入 main_order（原 group 位置后面）
    #     for offset, app in enumerate(apps_to_add):
    #         self.main_order.insert(insert_idx + offset, ('app', app))
    #
    #     # 6. 重新构建 group_dict
    #     self.group_dict = {g['name']: g for g in self.groups}
    #
    #     # 7. 刷新界面
    #     self.display_apps(self.filtered_apps, self.current_page)
    #     self.save_current_order()

    def disband_group(self, group):
        # 将组内所有 app 放回主界面（如果不在其它组），并准备插入 main_order
        apps_to_add = []
        for app in group['apps']:
            in_other_group = any(app in g['apps'] for g in self.groups if g is not group)
            if not in_other_group:
                if app not in self.filtered_apps:
                    self.filtered_apps.append(app)
                apps_to_add.append(app)

        # 从 groups 移除
        if group in self.groups:
            self.groups.remove(group)
        save_groups(self.groups)

        # 从 main_order 移除该 group
        self.main_order = [(typ, obj) for (typ, obj) in self.main_order if not (typ == 'group' and obj == group)]

        # 把 apps_to_add 插入 main_order 的末尾
        for app in apps_to_add:
            self.main_order.append(('app', app))

        # 重新构建 group_dict
        self.group_dict = {g['name']: g for g in self.groups}

        # 刷新界面
        self.filtered_apps = [a for a in self.apps if not any(a in g['apps'] for g in self.groups)]
        self.display_apps(self.filtered_apps, self.current_page)
        self.save_current_order()

    def start_background_scan(self):
        if self.scan_worker and self.scan_worker.isRunning():
            return  # 上一次还没结束
        self.scan_worker = AppScanWorker()
        self.scan_worker.apps_found.connect(self.on_new_apps_found)
        self.scan_worker.start()

    def dedup_apps(self, apps):
        seen = set()
        result = []
        for a in apps:
            if a['path'] not in seen:
                seen.add(a['path'])
                result.append(a)
        return result

    def on_new_apps_found(self, result):
        new_apps = result.get('new_apps', [])
        all_paths = set(result.get('all_paths', []))
        if new_apps:
            self.apps.extend(new_apps)
            self.apps = self.dedup_apps(self.apps)
            # 新增：自动加到 main_order 顺序末尾
            for a in new_apps:
                # 只加未分组的 app
                if not any(a in g['apps'] for g in self.groups):
                    already_in = any((typ == 'app' and obj['path'] == a['path']) for typ, obj in self.main_order)
                    if not already_in:
                        self.main_order.append(('app', a))
            self.save_current_order()
        # 检查已删除的 app
        current_paths = set(a['path'] for a in self.apps)
        removed_paths = current_paths - all_paths
        if removed_paths:
            self.apps = [a for a in self.apps if a['path'] not in removed_paths]
            self.filtered_apps = [a for a in self.filtered_apps if a['path'] not in removed_paths]
            # 同步 groups
            for group in self.groups:
                group['apps'] = [a for a in group['apps'] if a['path'] not in removed_paths]
                group['icon'] = create_group_icon(group['apps'])
            save_groups(self.groups)
            # 清理无用 icon 缓存
            for path in removed_paths:
                app_name = None
                for a in new_apps:
                    if a['path'] == path:
                        app_name = a['name']
                        break
                if not app_name:
                    for a in self.apps:
                        if a['path'] == path:
                            app_name = a['name']
                            break
                if app_name:
                    cache_path = app_icon_cache_path(path, app_name)
                    if os.path.exists(cache_path):
                        os.remove(cache_path)
            # 同步 main_order
            self.main_order = [
                (typ, obj) for (typ, obj) in self.main_order
                if not (typ == 'app' and obj['path'] in removed_paths)
            ]
            self.save_current_order()
        save_app_order([a['path'] for a in self.filtered_apps])  # save again
        self.display_apps(self.filtered_apps, self.current_page)

    # def keyPressEvent(self, event):
    #     if self.group_widget and self.group_widget.isVisible():
    #         self.group_widget.keyPressEvent(event)
    #         return
    #
    #     if event.key() == Qt.Key.Key_Left:
    #         self.goto_page(max(self.current_page - 1, 0))
    #         return
    #     elif event.key() == Qt.Key.Key_Right:
    #         self.goto_page(min(self.current_page + 1, self.total_pages() - 1))
    #         return
    #     elif event.key() == Qt.Key.Key_Space:
    #         self.focus_next_btn()
    #         return
    #     elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
    #         if self.focused_btn:
    #             if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
    #                 pos = self.focused_btn.rect().center()
    #                 self.focused_btn.show_context_menu(pos)
    #             else:
    #                 self.focused_btn.click()
    #         return
    #     else:
    #         super().keyPressEvent(event)

    def focus_next_btn(self):
        grid_layout = self.main_content.grid_layout
        btns = []
        for i in range(grid_layout.count()):
            w = grid_layout.itemAt(i).widget()
            if isinstance(w, (AppButton, GroupButton)):
                btns.append(w)
        if not btns:
            return
        # 检查self.focused_btn是否还有效
        if self.focused_btn not in btns:
            self.focus_index = -1
            self.focused_btn = None
        if self.focused_btn:
            self.focused_btn.icon_label.setStyleSheet("")
        self.focus_index = (self.focus_index + 1) % len(btns)
        self.focused_btn = btns[self.focus_index]
        #self.focused_btn.setStyleSheet(self.focused_btn.styleSheet() + "border: 2px solid #0085FF;")
        # 只给icon_label加边框
        self.focused_btn.icon_label.setStyleSheet(
            "border: 1.5px solid #0085FF; border-radius: 24px; padding: 0px;"
        )
        # 让主窗口重新获得焦点，保证事件过滤器继续生效
        self.setFocus()

    def focus_prev_btn(self):
        grid_layout = self.main_content.grid_layout
        btns = []
        for i in range(grid_layout.count()):
            w = grid_layout.itemAt(i).widget()
            if isinstance(w, (AppButton, GroupButton)):
                btns.append(w)
        if not btns:
            return
        # 检查self.focused_btn是否还有效
        if self.focused_btn not in btns:
            self.focus_index = -1
            self.focused_btn = None
        if self.focused_btn:
            self.focused_btn.icon_label.setStyleSheet("")
        self.focus_index = (self.focus_index - 1 + len(btns)) % len(btns)
        self.focused_btn = btns[self.focus_index]
        #self.focused_btn.setStyleSheet(self.focused_btn.styleSheet() + "border: 2px solid #0085FF;")
        # 只给icon_label加边框
        self.focused_btn.icon_label.setStyleSheet(
            "border: 1.5px solid #0085FF; border-radius: 24px; padding: 0px;"
        )
        self.setFocus()

    def focus_up_btn(self):
        grid_layout = self.main_content.grid_layout
        btns = []
        for i in range(grid_layout.count()):
            w = grid_layout.itemAt(i).widget()
            if isinstance(w, (AppButton, GroupButton)):
                btns.append(w)
        if not btns:
            return
        for btn in btns:
            btn.icon_label.setStyleSheet("")
        apps_per_row = 7
        if self.focus_index == -1:
            self.focus_index = 0
        else:
            self.focus_index = (self.focus_index - apps_per_row) % len(btns)
        self.focused_btn = btns[self.focus_index]
        self.focused_btn.icon_label.setStyleSheet(
            "border: 1.5px solid #0085FF; border-radius: 24px; padding: 0px;"
        )
        self.setFocus()

    def focus_down_btn(self):
        grid_layout = self.main_content.grid_layout
        btns = []
        for i in range(grid_layout.count()):
            w = grid_layout.itemAt(i).widget()
            if isinstance(w, (AppButton, GroupButton)):
                btns.append(w)
        if not btns:
            return
        for btn in btns:
            btn.icon_label.setStyleSheet("")
        apps_per_row = 7
        if self.focus_index == -1:
            self.focus_index = 0
        else:
            self.focus_index = (self.focus_index + apps_per_row) % len(btns)
        self.focused_btn = btns[self.focus_index]
        self.focused_btn.icon_label.setStyleSheet(
            "border: 1.5px solid #0085FF; border-radius: 24px; padding: 0px;"
        )
        self.setFocus()

    def eventFilter(self, obj, event):
        if event.type() == event.Type.KeyPress:
            # 如果group_widget可见，交给group_widget处理
            if self.group_widget and self.group_widget.isVisible():
                return self.group_widget.eventFilter(self.group_widget, event)
            # 只在主界面时处理
            return self.handle_key_event(event)
        return super().eventFilter(obj, event)

    def handle_key_event(self, event):
        if event.key() == Qt.Key.Key_Left:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.move_focused_btn_left()
                return True
            self.goto_page(max(self.current_page - 1, 0))
            return True
        elif event.key() == Qt.Key.Key_Right:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.move_focused_btn_right()
                return True
            self.goto_page(min(self.current_page + 1, self.total_pages() - 1))
            return True
        elif event.key() == Qt.Key.Key_Space:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.focus_prev_btn()
            else:
                self.focus_next_btn()
            return True
        elif event.key() == Qt.Key.Key_Up:
            self.focus_up_btn()
            return True
        elif event.key() == Qt.Key.Key_Down:
            self.focus_down_btn()
            return True
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.focused_btn is None:
                return False  # 新增：没有选中的按钮时直接返回，避免报错
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                pos = self.focused_btn.rect().center()
                self.focused_btn.show_context_menu(pos)
            else:
                # 计算本地和全局坐标
                local_pos = QPointF(self.focused_btn.rect().center())
                global_pos = QPointF(self.focused_btn.mapToGlobal(self.focused_btn.rect().center()))
                mouse_event = QMouseEvent(
                    QEvent.Type.MouseButtonPress,
                    local_pos,
                    global_pos,
                    Qt.MouseButton.LeftButton,
                    Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier
                )
                QApplication.sendEvent(self.focused_btn, mouse_event)
                mouse_event_release = QMouseEvent(
                    QEvent.Type.MouseButtonRelease,
                    local_pos,
                    global_pos,
                    Qt.MouseButton.LeftButton,
                    Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier
                )
                QApplication.sendEvent(self.focused_btn, mouse_event_release)
            return True
        return False

    def move_app_out_of_group(self, app_info, group):
        # 从 group 里移除
        if app_info in group['apps']:
            group['apps'].remove(app_info)
            group['icon'] = create_group_icon(group['apps'])
            save_groups(self.groups)
        # 检查是否还属于其他组
        in_other_group = any(
            app_info in g['apps'] for g in self.groups if g is not group
        )
        # 只有不属于其他组才放回主界面
        if not in_other_group and app_info not in self.filtered_apps:
            self.filtered_apps.append(app_info)
            # 先从 main_order 移除所有该 app
            self.main_order = [(typ, obj) for (typ, obj) in self.main_order if not (typ == 'app' and obj == app_info)]
            # 插入到所有 app 类型的末尾
            last_app_idx = -1
            for idx, (typ, obj) in enumerate(self.main_order):
                if typ == 'app':
                    last_app_idx = idx
            insert_idx = last_app_idx + 1
            self.main_order.insert(insert_idx, ('app', app_info))
            self.save_current_order()
        self.display_apps(self.filtered_apps, self.current_page)
        # 如果组窗口还开着，刷新组窗口
        if self.group_widget and self.group_widget.group is group:
            self.group_widget.display_apps(group['apps'], self.group_widget.current_page)

    def clear_icon_cache_and_refresh(self):
        if self.clear_cache_worker and self.clear_cache_worker.isRunning():
            #QMessageBox.information(self, "请稍候", "正在清除缓存和刷新应用，请勿重复操作。")
            msg = CustomMessageBox("Clearing cache and refreshing the app, please do not repeat the operation.", parent=self, buttons=("OK",))
            msg.exec()
            return
        self.clear_cache_action.setEnabled(False)
        self.clear_cache_worker = ClearCacheWorker()
        self.clear_cache_worker.finished.connect(self.on_clear_cache_finished)
        self.clear_cache_worker.start()

    def on_clear_cache_finished(self, apps, groups, filtered_apps, error_msg):
        self.clear_cache_action.setEnabled(True)
        if error_msg:
            #QMessageBox.warning(self, "错误", error_msg)
            msg = CustomMessageBox(error_msg, parent=self, buttons=("OK",))
            msg.exec()
            return
        self.apps = apps
        self.groups = groups
        self.filtered_apps = filtered_apps
        self.current_page = 0
        self.display_apps(self.filtered_apps, self.current_page)
        #QMessageBox.information(self, "完成", "图标缓存已清除，应用已刷新。")
        msg = RestartMessageBox("Icon cache cleared, app refreshed.\nRaspberry will restart.", parent=self,
                               buttons=("OK", "Later"))
        msg.exec()
        # if msg.exec() == 0:
        #     QTimer.singleShot(0, self.restart_app)

    def show_main_window(self):
        if not self.isVisible():
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def showEvent(self, event):
        super().showEvent(event)
        self.adapt_to_screen()  # 每次 show 都刷新几何
        self.prepare_icons_for_animation()
        self.hide_dock()
        QTimer.singleShot(10, self.animate_icons_in)  # 动画延迟触发

    def close_main_window(self):
        if self.isVisible():
            self.hide()

    # def closeEvent(self, event):
    #     #print('event')
    #     self.initial_release = False
    #     if self._dock_was_hidden_by_me:
    #         self.show_dock()
    #         self._dock_was_hidden_by_me = False
    #     super().closeEvent(event)

    def hideEvent(self, event):
        if self._always_hide_dock == False:
            self.show_dock()
        super().hideEvent(event)

    def update_single_app_icon(self):
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("App Files (*.app)")
        file_dialog.setViewMode(QFileDialog.ViewMode.Detail)
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                app_path = selected_files[0]
                info_plist = os.path.join(app_path, 'Contents', 'Info.plist')
                itunes_plist = os.path.join(app_path, 'Wrapper', 'iTunesMetadata.plist')
                name = None
                plist = None
                # 1. 优先 Info.plist
                if os.path.exists(info_plist):
                    try:
                        with open(info_plist, 'rb') as f:
                            plist = plistlib.load(f)
                        name = plist.get('CFBundleDisplayName') or plist.get('CFBundleName') or os.path.basename(app_path)[:-4]
                    except Exception as e:
                        #QMessageBox.warning(self, "错误", f"解析 Info.plist 失败: {e}")
                        msg = CustomMessageBox(f"Failed to parse Info.plist: {e}", parent=self, buttons=("OK",))
                        msg.exec()
                        return
                # 2. iOS 应用的 iTunesMetadata.plist
                elif os.path.exists(itunes_plist):
                    try:
                        with open(itunes_plist, 'rb') as f:
                            plist = plistlib.load(f)
                        name = plist.get('title') or plist.get('itemName') or os.path.basename(app_path)[:-4]
                    except Exception as e:
                        #QMessageBox.warning(self, "错误", f"解析 iTunesMetadata.plist 失败: {e}")
                        msg = CustomMessageBox(f"Failed to parse iTunesMetadata.plist: {e}", parent=self, buttons=("OK",))
                        msg.exec()
                        return
                # 3. 都没有就用文件夹名
                if not name:
                    name = os.path.basename(app_path)[:-4]
                # 删除该 app 的缓存图标文件
                cache_path = app_icon_cache_path(app_path, name)
                if os.path.exists(cache_path):
                    os.remove(cache_path)
                # 重新获取图标并缓存
                icon = get_finder_icon(app_path)
                if not icon.isNull():
                    save_icon_to_cache(icon, app_path, name)
                else:
                    #QMessageBox.warning(self, "错误", "无法获取该App的图标。")
                    msg = CustomMessageBox("Unable to retrieve the icon for this app.", parent=self, buttons=("OK",))
                    msg.exec()
                    return
                # 更新内存中的app信息
                updated = False
                for app in self.apps:
                    if app['path'] == app_path:
                        app['icon'] = icon
                        app['name'] = name
                        updated = True
                for group in self.groups:
                    for idx, app in enumerate(group['apps']):
                        if app['path'] == app_path:
                            group['apps'][idx]['icon'] = icon
                            group['apps'][idx]['name'] = name
                            group['icon'] = create_group_icon(group['apps'])
                if updated:
                    self.display_apps(self.filtered_apps, self.current_page)
                    msg = CustomMessageBox(f"The icon cache for {name} has been updated.", parent=self, buttons=("OK",))
                    msg.exec()
                    #QMessageBox.information(self, "完成", f"{name} 的图标缓存已更新。")
                else:
                    msg = CustomMessageBox(f"The icon of {name} has been cached, but the app is not in the main interface list.", parent=self, buttons=("OK",))
                    msg.exec()
                    #QMessageBox.information(self, "提示", f"已缓存 {name} 的图标，但该App不在主界面列表中。")

    def always_hide_dock(self):
        if self.always_hide_dock_action.isChecked():
            self._always_hide_dock = True
        if not self.always_hide_dock_action.isChecked():
            self._always_hide_dock = False

    # def is_dock_hidden(self):
    #     try:
    #         result = subprocess.run(
    #             ["defaults", "read", "com.apple.dock", "autohide"],
    #             capture_output=True, text=True, check=True
    #         )
    #         # check_dock_hide_script = '''
    #         #     tell application "System Events"
    #         #         get the autohide of dock preferences
    #         #     end tell
    #         #     '''
    #         # # 运行AppleScript
    #         # result = subprocess.run(["osascript", "-e", check_dock_hide_script], capture_output=True, text=True)
    #         # 解析输出结果
    #         if result.stdout.strip() == "1":
    #             return True
    #         else:
    #             return False
    #     except Exception:
    #         return False

    def hide_dock(self):
        try:
            # AppleScript命令
            toggle_dock_script = '''
                tell application "System Events" to set the autohide of dock preferences to true
                '''
            # 运行AppleScript
            subprocess.run(["osascript", "-e", toggle_dock_script])
            # subprocess.run(
            #     ["defaults", "write", "com.apple.dock", "autohide", "-bool", "true"], check=True
            # )
            # subprocess.run(["killall", "Dock"], check=True)
        except Exception as e:
            pass
            # print(f"隐藏 Dock 失败: {e}")

    def show_dock(self):
        try:
            # AppleScript命令
            toggle_dock_script = '''
                tell application "System Events" to set the autohide of dock preferences to false
                '''
            # 运行AppleScript
            subprocess.run(["osascript", "-e", toggle_dock_script])
            # subprocess.run(
            #     ["defaults", "write", "com.apple.dock", "autohide", "-bool", "false"], check=True
            # )
            # subprocess.run(["killall", "Dock"], check=True)
        except Exception as e:
            pass
            # print(f"显示 Dock 失败: {e}")

    def wheelEvent(self, event):
        delta_x = event.angleDelta().x()
        if delta_x == 0:
            return

        if self._cooldown:
            return

        if self._gesture_timer.isValid() and self._gesture_timer.elapsed() < self._min_gesture_interval_ms:
            return

        self._gesture_timer.start()
        self._accumulated_scroll += delta_x
        self._reset_scroll_timer.start(2000)

        if self._accumulated_scroll >= self._scroll_threshold:
            self._start_cooldown()
            self._reset_scroll()
            self.goto_page(max(self.current_page - 1, 0))
        elif self._accumulated_scroll <= -self._scroll_threshold:
            self._start_cooldown()
            self._reset_scroll()
            self.goto_page(min(self.current_page + 1, self.total_pages() - 1))

    def _start_cooldown(self):
        self._cooldown = True
        QTimer.singleShot(self._cooldown_duration_ms, self._end_cooldown)

    def _end_cooldown(self):
        self._cooldown = False

    def _reset_scroll(self):
        self._accumulated_scroll = 0

    # def get_surrounding_position(self, index, total, btn_size, width, height):
    #     # 四边均匀分布
    #     per_side = max(1, total // 4)
    #     if index < per_side:
    #         # 顶部
    #         x = int((width - btn_size) * index / max(1, per_side - 1))
    #         y = 0
    #     elif index < 2 * per_side:
    #         # 右侧
    #         x = width - btn_size
    #         y = int((height - btn_size) * (index - per_side) / max(1, per_side - 1))
    #     elif index < 3 * per_side:
    #         # 底部
    #         x = int((width - btn_size) * (index - 2 * per_side) / max(1, per_side - 1))
    #         y = height - btn_size
    #     else:
    #         # 左侧
    #         x = 0
    #         y = int((height - btn_size) * (index - 3 * per_side) / max(1, per_side - 1))
    #     return QPoint(x, y)

    def prepare_icons_for_animation(self):
        grid_layout = self.main_content.grid_layout
        total = grid_layout.count()
        for i in range(total):
            btn = grid_layout.itemAt(i).widget()
            if not isinstance(btn, (AppButton, GroupButton)):
                continue
            effect = QGraphicsOpacityEffect(btn)
            btn.setGraphicsEffect(effect)
            effect.setOpacity(0.0)

    # def animate_icons_in(self):  # 是移动+渐变动画
    #     grid_layout = self.main_content.grid_layout
    #     center = QPoint(self.width() // 2, self.height() // 2)
    #     anim_group = QParallelAnimationGroup(self)
    #     duration = 400
    #
    #     for i in range(grid_layout.count()):
    #         btn = grid_layout.itemAt(i).widget()
    #         if not isinstance(btn, (AppButton, GroupButton)):
    #             continue
    #
    #         # 记录最终位置
    #         final_pos = btn.pos()
    #         # 计算初始位置（四周，按象限分布）
    #         if i % 4 == 0:
    #             start_pos = QPoint(0, 0)  # 左上
    #         elif i % 4 == 1:
    #             start_pos = QPoint(self.width() - btn.width(), 0)  # 右上
    #         elif i % 4 == 2:
    #             start_pos = QPoint(0, self.height() - btn.height())  # 左下
    #         else:
    #             start_pos = QPoint(self.width() - btn.width(), self.height() - btn.height())  # 右下
    #
    #         btn.move(start_pos)
    #
    #         # total = grid_layout.count()
    #         # width = self.width()
    #         # height = self.height()
    #         # start_pos = self.get_surrounding_position(i, total, 140, width, height)
    #         # btn.move(start_pos)
    #
    #         # 透明度动画
    #         effect = QGraphicsOpacityEffect(btn)
    #         btn.setGraphicsEffect(effect)
    #         effect.setOpacity(0.0)
    #
    #         opacity_anim = QPropertyAnimation(effect, b"opacity", self)
    #         opacity_anim.setDuration(duration)
    #         opacity_anim.setStartValue(0.0)
    #         opacity_anim.setEndValue(1.0)
    #
    #         # 位置动画
    #         pos_anim = QPropertyAnimation(btn, b"pos", self)
    #         pos_anim.setDuration(duration)
    #         pos_anim.setStartValue(start_pos)
    #         pos_anim.setEndValue(final_pos)
    #
    #         anim_group.addAnimation(pos_anim)
    #         anim_group.addAnimation(opacity_anim)
    #
    #     anim_group.start()

    def animate_icons_in(self):  # 缩放+渐变动画
        grid_layout = self.main_content.grid_layout
        duration = 400
        anim_group = QParallelAnimationGroup(self)

        for i in range(grid_layout.count()):
            btn = grid_layout.itemAt(i).widget()
            if not isinstance(btn, (AppButton, GroupButton)):
                continue

            # 记录最终位置和大小
            final_pos = btn.pos()
            final_size = btn.size()
            scale_factor = 1.25

            # 初始缩放
            scaled_width = int(final_size.width() * scale_factor)
            scaled_height = int(final_size.height() * scale_factor)
            start_pos = final_pos - QPoint((scaled_width - final_size.width()) // 2,
                                           (scaled_height - final_size.height()) // 2)

            btn.setGeometry(QRect(start_pos, QSize(scaled_width, scaled_height)))

            # 透明度动画
            effect = QGraphicsOpacityEffect(btn)
            btn.setGraphicsEffect(effect)
            effect.setOpacity(0.0)

            opacity_anim = QPropertyAnimation(effect, b"opacity", self)
            opacity_anim.setDuration(duration*2)
            opacity_anim.setStartValue(0.0)
            opacity_anim.setEndValue(1.0)
            opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

            # 缩放动画（通过 setGeometry）
            size_anim = QPropertyAnimation(btn, b"geometry", self)
            size_anim.setDuration(duration)
            size_anim.setStartValue(QRect(start_pos, QSize(scaled_width, scaled_height)))
            size_anim.setEndValue(QRect(final_pos, final_size))
            size_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

            anim_group.addAnimation(opacity_anim)
            anim_group.addAnimation(size_anim)

        anim_group.start()
        self.anim = anim_group  # 防止被垃圾回收

    def move_focused_btn_left(self):
        # 全局 main_order 移动，支持跨页
        if not self.focused_btn:
            return
        # 找到 main_order 里的全局 idx
        for idx, (typ, obj) in enumerate(self.main_order):
            if (isinstance(self.focused_btn, AppButton) and typ == 'app' and obj == self.focused_btn.app_info) or \
                    (isinstance(self.focused_btn, GroupButton) and typ == 'group' and obj == self.focused_btn.group):
                break
        else:
            return
        if idx == 0:
            return
        # 交换
        self.main_order[idx], self.main_order[idx - 1] = self.main_order[idx - 1], self.main_order[idx]
        self.save_current_order()
        # 计算新页码
        new_page = (idx - 1) // self.items_per_page
        self.current_page = new_page
        self.display_apps(self.filtered_apps, self.current_page)
        # 聚焦到新位置
        self.focus_index = (idx - 1) % self.items_per_page
        self.set_focus_by_global_index(idx - 1)

    def move_focused_btn_right(self):
        if not self.focused_btn:
            return
        for idx, (typ, obj) in enumerate(self.main_order):
            if (isinstance(self.focused_btn, AppButton) and typ == 'app' and obj == self.focused_btn.app_info) or \
                    (isinstance(self.focused_btn, GroupButton) and typ == 'group' and obj == self.focused_btn.group):
                break
        else:
            return
        if idx == len(self.main_order) - 1:
            return
        self.main_order[idx], self.main_order[idx + 1] = self.main_order[idx + 1], self.main_order[idx]
        self.save_current_order()
        new_page = (idx + 1) // self.items_per_page
        self.current_page = new_page
        self.display_apps(self.filtered_apps, self.current_page)
        self.focus_index = (idx + 1) % self.items_per_page
        self.set_focus_by_global_index(idx + 1)

    def set_focus_by_global_index(self, global_idx):
        # 在当前页找到对应按钮并聚焦
        grid_layout = self.main_content.grid_layout
        page_start = self.current_page * self.items_per_page
        page_end = page_start + self.items_per_page
        rel_idx = global_idx - page_start
        btns = []
        for i in range(grid_layout.count()):
            w = grid_layout.itemAt(i).widget()
            if isinstance(w, (AppButton, GroupButton)):
                btns.append(w)
        if 0 <= rel_idx < len(btns):
            self.focused_btn = btns[rel_idx]
            self.focused_btn.icon_label.setStyleSheet(
                "border: 1.5px solid #0085FF; border-radius: 24px; padding: 0px;"
            )
            self.focus_index = rel_idx
            self.setFocus()

    def save_current_order(self):
        # 保存 main_order 到本地
        order_ids = []
        for typ, obj in self.main_order:
            if typ == 'group':
                order_ids.append(obj['name'])
            else:
                order_ids.append(obj['path'])
        save_main_order(order_ids)

    def login_start(self):
        plist_filename = 'com.ryanthehito.raspberry.plist'
        if self.action10.isChecked():
            try:
                launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
                launch_agents_dir.mkdir(parents=True, exist_ok=True)
                plist_source_path = BasePath + plist_filename
                destination = launch_agents_dir / plist_filename
                shutil.copy2(plist_source_path, destination)
                # 设置权限确保 macOS 能读
                os.chmod(destination, 0o644)
            except Exception as e:
                # 发生异常时打印错误信息
                p = "程序发生异常: Autostart failed: " + str(e)
                with open(BasePath + "Error.txt", 'a', encoding='utf-8') as f0:
                    f0.write(p)
        if not self.action10.isChecked():
            try:
                plist_path = Path.home() / "Library" / "LaunchAgents" / plist_filename
                if plist_path.exists():
                    # 删除文件
                    os.remove(plist_path)
            except Exception as e:
                # 发生异常时打印错误信息
                p = "程序发生异常: Removing autostart failed: " + str(e)
                with open(BasePath + "Error.txt", 'a', encoding='utf-8') as f0:
                    f0.write(p)

    def restart_app(self):
        time.sleep(3)
        applescript = '''
    	if application "Raspberry" is running then
    		try
    			tell application "Raspberry"
    				quit
    				delay 1
    				activate
    			end tell
    		on error number -128
    			quit application "Raspberry"
    			delay 1
    			activate application "Raspberry"
    		end try
    	end if
    	'''
        subprocess.Popen(['osascript', '-e', applescript])

    def run_lporg(self):
        webbrowser.open('https://buymeacoffee.com/ryanthehito/extras')

    def animate_page_transition(self, next_page_items, direction="left"):
        grid_layout = self.main_content.grid_layout
        old_btns = []
        for i in range(grid_layout.count()):
            btn = grid_layout.itemAt(i).widget()
            if isinstance(btn, (AppButton, GroupButton)):
                old_btns.append(btn)

        if not next_page_items:
            for btn in old_btns:
                btn.hide()
                btn.setParent(None)
                btn.deleteLater()
            return

        # 动画：旧按钮平移消失，方向可选
        screen_width = self.width()
        speed = 6000
        anim_group_out = QParallelAnimationGroup(self)
        for btn in old_btns:
            start_pos = btn.pos()
            if direction == "left":
                end_pos = QPoint(-btn.width(), start_pos.y())
                distance = start_pos.x() + btn.width()
            else:  # direction == "right"
                end_pos = QPoint(screen_width + btn.width(), start_pos.y())
                distance = screen_width - start_pos.x() + btn.width()
            duration = int(distance / speed * 1000)
            anim = QPropertyAnimation(btn, b"pos", self)
            anim.setDuration(duration)
            anim.setStartValue(start_pos)
            anim.setEndValue(end_pos)
            anim.setEasingCurve(QEasingCurve.Type.OutCurve)
            anim_group_out.addAnimation(anim)

        def cleanup_old_btns():
            for btn in old_btns:
                btn.hide()
                btn.setParent(None)
                btn.deleteLater()
            # 动画结束后，直接显示新一页内容
            self.display_apps(
                [obj for typ, obj in next_page_items if typ == 'app'],
                self.current_page
            )

        anim_group_out.finished.connect(cleanup_old_btns)
        anim_group_out.start()
        self.anim = anim_group_out

    def backup_groups(self):
        webbrowser.open('https://buymeacoffee.com/ryanthehito/extras')

    def restore_backup(self):
        webbrowser.open('https://buymeacoffee.com/ryanthehito/extras')

    def adapt_to_screen(self):
        """每次显示或分辨率变化时调用，让窗口和所有子布局都重算尺寸"""
        # 1️⃣ 选定目标屏幕
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        geo: QRect = screen.geometry()

        # 2️⃣ 如果尺寸真的变了才更新
        if geo != self.geometry():
            self.setGeometry(geo)

            # 让主内容覆盖整个窗口
            self.main_content.setGeometry(self.rect())

            # 如果正在显示 group_widget，也需要重新居中
            if self.group_widget and self.group_widget.isVisible():
                gw = self.group_widget
                gw.move((self.width() - gw.width()) // 2,
                        (self.height() - gw.height()) // 2)

            # 3️⃣ 重新排布图标（依赖 self.width()/height() 的那些计算）
            self.display_apps(self.filtered_apps, self.current_page)


class WindowAbout(QWidget):  # 增加说明页面(About)
    def __init__(self):
        super().__init__()
        self.radius = 16  # 圆角半径，可按 macOS 15 或 26 设置为 16~26

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        self.init_ui()

    def init_ui(self):
        self.setUpMainWindow()
        self.setFixedSize(400, 600)
        self.center()
        self.setFocus()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, self.radius, self.radius)

        painter.setClipPath(path)
        bg_color = self.palette().color(QPalette.ColorRole.Window)
        painter.fillPath(path, bg_color)

    # 让无边框窗口可拖动
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def setUpMainWindow(self):
        # 添加关闭按钮（仿 macOS 左上角红色圆点）
        # self.close_button = QPushButton(self)
        # self.close_button.setFixedSize(12, 12)
        # self.close_button.move(10, 10)
        # self.close_button.setStyleSheet("""
        #     QPushButton {
        #         background-color: #FF5F57;
        #         border-radius: 6px;
        #         border: none;
        #     }
        #     QPushButton:hover {
        #         background-color: #BF4943;
        #     }
        # """)
        # self.close_button.clicked.connect(self.close)
        # 三个按钮
        ##FF5F57
        self.close_button = MacWindowButton("#FF605C", "x", self)
        self.close_button.move(10, 10)
        self.close_button.clicked.connect(self.close)
        ##FFBD2E
        # self.min_button = MacWindowButton("#FFBD44", "-", self)
        # self.min_button.move(30, 10)
        # self.min_button.clicked.connect(self.showMinimized)
        ##28C940
        # self.max_button = MacWindowButton("#00CA4E", "+", self)
        # self.max_button.move(50, 10)
        # self.max_button.clicked.connect(self.showMaximized)

        widg1 = QWidget()
        l1 = QLabel(self)
        png = QPixmap(BasePath + 'Raspberry_menu.png')  # 调用QtGui.QPixmap方法，打开一个图片，存放在变量png中
        l1.setPixmap(png)  # 在l1里面，调用setPixmap命令，建立一个图像存放框，并将之前的图像png存放在这个框框里。
        l1.setMaximumWidth(100)
        l1.setMaximumHeight(100)
        l1.setScaledContents(True)
        blay1 = QHBoxLayout()
        blay1.setContentsMargins(0, 0, 0, 0)
        blay1.addStretch()
        blay1.addWidget(l1)
        blay1.addStretch()
        widg1.setLayout(blay1)

        widg2 = QWidget()
        lbl0 = QLabel(NAME, self)
        font = QFont()
        font.setFamily("Arial")
        font.setBold(True)
        font.setPointSize(20)
        lbl0.setFont(font)
        blay2 = QHBoxLayout()
        blay2.setContentsMargins(0, 0, 0, 0)
        blay2.addStretch()
        blay2.addWidget(lbl0)
        blay2.addStretch()
        widg2.setLayout(blay2)

        widg3 = QWidget()
        lbl1 = QLabel(f'Version {VERSION}', self)
        blay3 = QHBoxLayout()
        blay3.setContentsMargins(0, 0, 0, 0)
        blay3.addStretch()
        blay3.addWidget(lbl1)
        blay3.addStretch()
        widg3.setLayout(blay3)

        widg4 = QWidget()
        lbl2 = QLabel('Thanks for your love🤟.', self)
        blay4 = QHBoxLayout()
        blay4.setContentsMargins(0, 0, 0, 0)
        blay4.addStretch()
        blay4.addWidget(lbl2)
        blay4.addStretch()
        widg4.setLayout(blay4)

        widg5 = QWidget()
        lbl3 = QLabel('For more of my works, please visit the homepage🥰.', self)
        blay5 = QHBoxLayout()
        blay5.setContentsMargins(0, 0, 0, 0)
        blay5.addStretch()
        blay5.addWidget(lbl3)
        blay5.addStretch()
        widg5.setLayout(blay5)

        widg6 = QWidget()
        lbl4 = QLabel('Special thanks to ut.code(); of the University of Tokyo❤️.', self)
        blay6 = QHBoxLayout()
        blay6.setContentsMargins(0, 0, 0, 0)
        blay6.addStretch()
        blay6.addWidget(lbl4)
        blay6.addStretch()
        widg6.setLayout(blay6)

        widg7 = QWidget()
        lbl5 = QLabel('This app is under the protection of  GPL-3.0 license.', self)
        blay7 = QHBoxLayout()
        blay7.setContentsMargins(0, 0, 0, 0)
        blay7.addStretch()
        blay7.addWidget(lbl5)
        blay7.addStretch()
        widg7.setLayout(blay7)

        widg8 = QWidget()
        widg8.setFixedHeight(50)
        bt1 = WhiteButton('The Author')
        bt1.setMinimumWidth(100)
        bt1.clicked.connect(self.intro)
        bt2 = WhiteButton('Github Page')
        bt2.setMinimumWidth(100)
        bt2.clicked.connect(self.homepage)
        blay8 = QHBoxLayout()
        blay8.setContentsMargins(0, 0, 0, 0)
        blay8.addStretch()
        blay8.addWidget(bt1)
        blay8.addWidget(bt2)
        blay8.addStretch()
        widg8.setLayout(blay8)

        bt7 = WhiteButton('Buy me a cup of coffee☕')
        bt7.setMinimumWidth(215)
        bt7.clicked.connect(self.coffee)
        widg8_5 = QWidget()
        widg8_5.setFixedHeight(50)
        blay8_5 = QHBoxLayout()
        blay8_5.setContentsMargins(0, 0, 0, 0)
        blay8_5.addStretch()
        blay8_5.addWidget(bt7)
        blay8_5.addStretch()
        widg8_5.setLayout(blay8_5)

        widg9 = QWidget()
        widg9.setFixedHeight(70)
        bt3 = WhiteButton('🍪\n¥5')
        bt3.setMaximumHeight(50)
        bt3.setMinimumHeight(50)
        bt3.setMinimumWidth(50)
        bt3.clicked.connect(self.donate)
        bt4 = WhiteButton('🥪\n¥10')
        bt4.setMaximumHeight(50)
        bt4.setMinimumHeight(50)
        bt4.setMinimumWidth(50)
        bt4.clicked.connect(self.donate2)
        bt5 = WhiteButton('🍜\n¥20')
        bt5.setMaximumHeight(50)
        bt5.setMinimumHeight(50)
        bt5.setMinimumWidth(50)
        bt5.clicked.connect(self.donate3)
        bt6 = WhiteButton('🍕\n¥50')
        bt6.setMaximumHeight(50)
        bt6.setMinimumHeight(50)
        bt6.setMinimumWidth(50)
        bt6.clicked.connect(self.donate4)
        blay9 = QHBoxLayout()
        blay9.setContentsMargins(0, 0, 0, 0)
        blay9.addStretch()
        blay9.addWidget(bt3)
        blay9.addWidget(bt4)
        blay9.addWidget(bt5)
        blay9.addWidget(bt6)
        blay9.addStretch()
        widg9.setLayout(blay9)

        widg10 = QWidget()
        lbl6 = QLabel('© 2025 Yixiang SHEN. All rights reserved.', self)
        blay10 = QHBoxLayout()
        blay10.setContentsMargins(0, 0, 0, 0)
        blay10.addStretch()
        blay10.addWidget(lbl6)
        blay10.addStretch()
        widg10.setLayout(blay10)

        main_h_box = QVBoxLayout()
        main_h_box.setContentsMargins(20, 40, 20, 20)  # 重要，用来保证关闭按钮的位置。
        main_h_box.addSpacing(10)
        main_h_box.addWidget(widg1)
        main_h_box.addWidget(widg2)
        main_h_box.addSpacing(5)
        main_h_box.addWidget(widg3)
        main_h_box.addSpacing(5)
        main_h_box.addWidget(widg4)
        main_h_box.addSpacing(5)
        main_h_box.addWidget(widg5)
        main_h_box.addSpacing(5)
        main_h_box.addWidget(widg6)
        main_h_box.addSpacing(5)
        main_h_box.addWidget(widg7)
        main_h_box.addStretch()
        main_h_box.addWidget(widg8)
        main_h_box.addWidget(widg8_5)
        main_h_box.addWidget(widg9)
        main_h_box.addWidget(widg10)
        main_h_box.addStretch()
        main_h_box.addSpacing(10)
        self.setLayout(main_h_box)

    def intro(self):
        webbrowser.open('https://github.com/Ryan-the-hito/Ryan-the-hito')

    def homepage(self):
        webbrowser.open('https://github.com/Ryan-the-hito/Raspberry')

    def coffee(self):
        webbrowser.open('https://www.buymeacoffee.com/ryanthehito')

    def donate(self):
        dlg = CustomDialog()
        dlg.exec()

    def donate2(self):
        dlg = CustomDialog2()
        dlg.exec()

    def donate3(self):
        dlg = CustomDialog3()
        dlg.exec()

    def donate4(self):
        dlg = CustomDialog4()
        dlg.exec()

    def center(self):  # 设置窗口居中
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def activate(self):  # 设置窗口显示
        self.show()


class CustomDialog(QDialog):  # (About1)
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setUpMainWindow()
        self.setWindowTitle("Thank you for your support!")
        self.center()
        self.resize(440, 390)
        self.setFocus()
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

    def setUpMainWindow(self):
        widge_all = QWidget()
        l1 = QLabel(self)
        png = QPixmap(BasePath + 'wechat5.png')  # 调用QtGui.QPixmap方法，打开一个图片，存放在变量png中
        l1.setPixmap(png)  # 在l1里面，调用setPixmap命令，建立一个图像存放框，并将之前的图像png存放在这个框框里。
        l1.setMaximumSize(160, 240)
        l1.setScaledContents(True)
        l2 = QLabel(self)
        png = QPixmap(BasePath + 'alipay5.png')  # 调用QtGui.QPixmap方法，打开一个图片，存放在变量png中
        l2.setPixmap(png)  # 在l2里面，调用setPixmap命令，建立一个图像存放框，并将之前的图像png存放在这个框框里。
        l2.setMaximumSize(160, 240)
        l2.setScaledContents(True)
        bk = QHBoxLayout()
        bk.setContentsMargins(0, 0, 0, 0)
        bk.addWidget(l1)
        bk.addWidget(l2)
        widge_all.setLayout(bk)

        m1 = QLabel('Thank you for your kind support! 😊', self)
        m2 = QLabel('I will write more interesting apps! 🥳', self)

        widg_c = QWidget()
        widg_c.setFixedHeight(50)
        bt1 = WhiteButton('Thank you!')
        #bt1.setMaximumHeight(20)
        bt1.setMinimumWidth(100)
        bt1.clicked.connect(self.cancel)
        bt2 = WhiteButton('Neither one above? Buy me a coffee~')
        #bt2.setMaximumHeight(20)
        bt2.setMinimumWidth(260)
        bt2.clicked.connect(self.coffee)
        blay8 = QHBoxLayout()
        blay8.setContentsMargins(0, 0, 0, 0)
        blay8.addStretch()
        blay8.addWidget(bt1)
        blay8.addWidget(bt2)
        blay8.addStretch()
        widg_c.setLayout(blay8)

        self.layout = QVBoxLayout()
        self.layout.addWidget(widge_all)
        self.layout.addWidget(m1)
        self.layout.addWidget(m2)
        self.layout.addStretch()
        self.layout.addWidget(widg_c)
        self.layout.addStretch()
        self.setLayout(self.layout)

    def center(self):  # 设置窗口居中
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def coffee(self):
        webbrowser.open('https://www.buymeacoffee.com/ryanthehito')

    def cancel(self):  # 设置取消键的功能
        self.close()


class CustomDialog2(QDialog):  # (About2)
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setUpMainWindow()
        self.setWindowTitle("Thank you for your support!")
        self.center()
        self.resize(440, 390)
        self.setFocus()
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

    def setUpMainWindow(self):
        widge_all = QWidget()
        l1 = QLabel(self)
        png = QPixmap(BasePath + 'wechat10.png')  # 调用QtGui.QPixmap方法，打开一个图片，存放在变量png中
        l1.setPixmap(png)  # 在l1里面，调用setPixmap命令，建立一个图像存放框，并将之前的图像png存放在这个框框里。
        l1.setMaximumSize(160, 240)
        l1.setScaledContents(True)
        l2 = QLabel(self)
        png = QPixmap(BasePath + 'alipay10.png')  # 调用QtGui.QPixmap方法，打开一个图片，存放在变量png中
        l2.setPixmap(png)  # 在l2里面，调用setPixmap命令，建立一个图像存放框，并将之前的图像png存放在这个框框里。
        l2.setMaximumSize(160, 240)
        l2.setScaledContents(True)
        bk = QHBoxLayout()
        bk.setContentsMargins(0, 0, 0, 0)
        bk.addWidget(l1)
        bk.addWidget(l2)
        widge_all.setLayout(bk)

        m1 = QLabel('Thank you for your kind support! 😊', self)
        m2 = QLabel('I will write more interesting apps! 🥳', self)

        widg_c = QWidget()
        widg_c.setFixedHeight(50)
        bt1 = WhiteButton('Thank you!')
        #bt1.setMaximumHeight(20)
        bt1.setMinimumWidth(100)
        bt1.clicked.connect(self.cancel)
        bt2 = WhiteButton('Neither one above? Buy me a coffee~')
        #bt2.setMaximumHeight(20)
        bt2.setMinimumWidth(260)
        bt2.clicked.connect(self.coffee)
        blay8 = QHBoxLayout()
        blay8.setContentsMargins(0, 0, 0, 0)
        blay8.addStretch()
        blay8.addWidget(bt1)
        blay8.addWidget(bt2)
        blay8.addStretch()
        widg_c.setLayout(blay8)

        self.layout = QVBoxLayout()
        self.layout.addWidget(widge_all)
        self.layout.addWidget(m1)
        self.layout.addWidget(m2)
        self.layout.addStretch()
        self.layout.addWidget(widg_c)
        self.layout.addStretch()
        self.setLayout(self.layout)

    def center(self):  # 设置窗口居中
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def coffee(self):
        webbrowser.open('https://www.buymeacoffee.com/ryanthehito')

    def cancel(self):  # 设置取消键的功能
        self.close()


class CustomDialog3(QDialog):  # (About3)
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setUpMainWindow()
        self.setWindowTitle("Thank you for your support!")
        self.center()
        self.resize(440, 390)
        self.setFocus()
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

    def setUpMainWindow(self):
        widge_all = QWidget()
        l1 = QLabel(self)
        png = QPixmap(BasePath + 'wechat20.png')  # 调用QtGui.QPixmap方法，打开一个图片，存放在变量png中
        l1.setPixmap(png)  # 在l1里面，调用setPixmap命令，建立一个图像存放框，并将之前的图像png存放在这个框框里。
        l1.setMaximumSize(160, 240)
        l1.setScaledContents(True)
        l2 = QLabel(self)
        png = QPixmap(BasePath + 'alipay20.png')  # 调用QtGui.QPixmap方法，打开一个图片，存放在变量png中
        l2.setPixmap(png)  # 在l2里面，调用setPixmap命令，建立一个图像存放框，并将之前的图像png存放在这个框框里。
        l2.setMaximumSize(160, 240)
        l2.setScaledContents(True)
        bk = QHBoxLayout()
        bk.setContentsMargins(0, 0, 0, 0)
        bk.addWidget(l1)
        bk.addWidget(l2)
        widge_all.setLayout(bk)

        m1 = QLabel('Thank you for your kind support! 😊', self)
        m2 = QLabel('I will write more interesting apps! 🥳', self)

        widg_c = QWidget()
        widg_c.setFixedHeight(50)
        bt1 = WhiteButton('Thank you!')
        #bt1.setMaximumHeight(20)
        bt1.setMinimumWidth(100)
        bt1.clicked.connect(self.cancel)
        bt2 = WhiteButton('Neither one above? Buy me a coffee~')
        #bt2.setMaximumHeight(20)
        bt2.setMinimumWidth(260)
        bt2.clicked.connect(self.coffee)
        blay8 = QHBoxLayout()
        blay8.setContentsMargins(0, 0, 0, 0)
        blay8.addStretch()
        blay8.addWidget(bt1)
        blay8.addWidget(bt2)
        blay8.addStretch()
        widg_c.setLayout(blay8)

        self.layout = QVBoxLayout()
        self.layout.addWidget(widge_all)
        self.layout.addWidget(m1)
        self.layout.addWidget(m2)
        self.layout.addStretch()
        self.layout.addWidget(widg_c)
        self.layout.addStretch()
        self.setLayout(self.layout)

    def center(self):  # 设置窗口居中
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def coffee(self):
        webbrowser.open('https://www.buymeacoffee.com/ryanthehito')

    def cancel(self):  # 设置取消键的功能
        self.close()


class CustomDialog4(QDialog):  # (About4)
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setUpMainWindow()
        self.setWindowTitle("Thank you for your support!")
        self.center()
        self.resize(440, 390)
        self.setFocus()
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

    def setUpMainWindow(self):
        widge_all = QWidget()
        l1 = QLabel(self)
        png = QPixmap(BasePath + 'wechat50.png')  # 调用QtGui.QPixmap方法，打开一个图片，存放在变量png中
        l1.setPixmap(png)  # 在l1里面，调用setPixmap命令，建立一个图像存放框，并将之前的图像png存放在这个框框里。
        l1.setMaximumSize(160, 240)
        l1.setScaledContents(True)
        l2 = QLabel(self)
        png = QPixmap(BasePath + 'alipay50.png')  # 调用QtGui.QPixmap方法，打开一个图片，存放在变量png中
        l2.setPixmap(png)  # 在l2里面，调用setPixmap命令，建立一个图像存放框，并将之前的图像png存放在这个框框里。
        l2.setMaximumSize(160, 240)
        l2.setScaledContents(True)
        bk = QHBoxLayout()
        bk.setContentsMargins(0, 0, 0, 0)
        bk.addWidget(l1)
        bk.addWidget(l2)
        widge_all.setLayout(bk)

        m1 = QLabel('Thank you for your kind support! 😊', self)
        m2 = QLabel('I will write more interesting apps! 🥳', self)

        widg_c = QWidget()
        widg_c.setFixedHeight(50)
        bt1 = WhiteButton('Thank you!')
        #bt1.setMaximumHeight(20)
        bt1.setMinimumWidth(100)
        bt1.clicked.connect(self.cancel)
        bt2 = WhiteButton('Neither one above? Buy me a coffee~')
        #bt2.setMaximumHeight(20)
        bt2.setMinimumWidth(260)
        bt2.clicked.connect(self.coffee)
        blay8 = QHBoxLayout()
        blay8.setContentsMargins(0, 0, 0, 0)
        blay8.addStretch()
        blay8.addWidget(bt1)
        blay8.addWidget(bt2)
        blay8.addStretch()
        widg_c.setLayout(blay8)

        self.layout = QVBoxLayout()
        self.layout.addWidget(widge_all)
        self.layout.addWidget(m1)
        self.layout.addWidget(m2)
        self.layout.addStretch()
        self.layout.addWidget(widg_c)
        self.layout.addStretch()
        self.setLayout(self.layout)

    def center(self):  # 设置窗口居中
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def coffee(self):
        webbrowser.open('https://www.buymeacoffee.com/ryanthehito')

    def cancel(self):  # 设置取消键的功能
        self.close()


class WindowUpdate(QWidget):  # 增加更新页面（Check for Updates）
    def __init__(self):
        super().__init__()
        self.radius = 16  # 圆角半径，可按 macOS 15 或 26 设置为 16~26

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        self.init_ui()

    def init_ui(self):
        self.setUpMainWindow()
        self.setFixedSize(280, 170)
        self.center()
        self.setFocus()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, self.radius, self.radius)

        painter.setClipPath(path)
        bg_color = self.palette().color(QPalette.ColorRole.Window)
        painter.fillPath(path, bg_color)

    # 让无边框窗口可拖动
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def setUpMainWindow(self):
        # 添加关闭按钮（仿 macOS 左上角红色圆点）
        # self.close_button = QPushButton(self)
        # self.close_button.setFixedSize(12, 12)
        # self.close_button.move(10, 10)
        # self.close_button.setStyleSheet("""
        #     QPushButton {
        #         background-color: #FF5F57;
        #         border-radius: 6px;
        #         border: none;
        #     }
        #     QPushButton:hover {
        #         background-color: #BF4943;
        #     }
        # """)
        # self.close_button.clicked.connect(self.close)
        self.close_button = MacWindowButton("#FF605C", "x", self)
        self.close_button.move(10, 10)
        self.close_button.clicked.connect(self.close)

        widg5 = QWidget()
        lbl1 = QLabel('Latest version:', self)
        self.lbl2 = QLabel('', self)
        blay5 = QHBoxLayout()
        blay5.setContentsMargins(0, 0, 0, 0)
        # blay5.addStretch()
        blay5.addWidget(lbl1)
        blay5.addWidget(self.lbl2)
        blay5.addStretch()
        widg5.setLayout(blay5)

        widg3 = QWidget()
        self.lbl = QLabel(f'Current version: v{VERSION}', self)
        blay3 = QHBoxLayout()
        blay3.setContentsMargins(0, 0, 0, 0)
        # blay3.addStretch()
        blay3.addWidget(self.lbl)
        blay3.addStretch()
        widg3.setLayout(blay3)

        widg4 = QWidget()
        widg4.setFixedHeight(50)
        lbl0 = QLabel('Check release:', self)
        bt1 = WhiteButton('Github')
        bt1.clicked.connect(self.upd)
        blay4 = QHBoxLayout()
        blay4.setContentsMargins(0, 0, 0, 0)
        # blay4.addStretch()
        blay4.addWidget(lbl0)
        blay4.addWidget(bt1)
        blay4.addStretch()
        widg4.setLayout(blay4)

        main_h_box = QVBoxLayout()
        main_h_box.setContentsMargins(20, 40, 20, 20)  # 重要，用来保证关闭按钮的位置。
        main_h_box.addWidget(widg5)
        main_h_box.addSpacing(10)
        main_h_box.addWidget(widg3)
        main_h_box.addWidget(widg4)
        self.setLayout(main_h_box)

    def upd(self):
        webbrowser.open('https://github.com/Ryan-the-hito/Raspberry/releases')

    def center(self):  # 设置窗口居中
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def activate(self):  # 设置窗口显示
        self.show()
        self.checkupdate()

    def checkupdate(self):
        targetURL = 'https://github.com/Ryan-the-hito/Raspberry/releases'
        try:
            # Fetch the HTML content from the URL
            urllib3.disable_warnings()
            logging.captureWarnings(True)
            s = requests.session()
            s.keep_alive = False  # 关闭多余连接
            response = s.get(targetURL, verify=False)
            response.encoding = 'utf-8'
            html_content = response.text
            # Parse the HTML using BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")
            # Remove all images from the parsed HTML
            for img in soup.find_all("img"):
                img.decompose()
            # Convert the parsed HTML to plain text using html2text
            text_maker = html2text.HTML2Text()
            text_maker.ignore_links = True
            text_maker.ignore_images = True
            plain_text = text_maker.handle(str(soup))
            # Convert the plain text to UTF-8
            plain_text_utf8 = plain_text.encode(response.encoding).decode("utf-8")

            for i in range(10):
                plain_text_utf8 = plain_text_utf8.replace('\n\n\n\n', '\n\n')
                plain_text_utf8 = plain_text_utf8.replace('\n\n\n', '\n\n')
                plain_text_utf8 = plain_text_utf8.replace('   ', ' ')
                plain_text_utf8 = plain_text_utf8.replace('  ', ' ')

            pattern2 = re.compile(r'(v\d+\.\d+\.\d+)\sLatest')
            result = pattern2.findall(plain_text_utf8)
            result = ''.join(result)
            nowversion = self.lbl.text().replace('Current Version: ', '').replace('Current version: ', '')
            if result == nowversion:
                alertupdate = result + ' (up-to-date)'
                self.lbl2.setText(alertupdate)
                self.lbl2.adjustSize()
            else:
                alertupdate = result + ' is ready!'
                self.lbl2.setText(alertupdate)
                self.lbl2.adjustSize()
        except:
            alertupdate = 'No Intrenet'
            self.lbl2.setText(alertupdate)
            self.lbl2.adjustSize()


class PermissionInfoWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.radius = 16  # 圆角半径，可按 macOS 15 或 26 设置为 16~26

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        self.init_ui()

    def init_ui(self):
        self.setUpMainWindow()
        self.setFixedSize(400, 600)
        self.center()
        self.setFocus()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, self.radius, self.radius)

        painter.setClipPath(path)
        bg_color = self.palette().color(QPalette.ColorRole.Window)
        painter.fillPath(path, bg_color)

    # 让无边框窗口可拖动
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def setUpMainWindow(self):
        # 添加关闭按钮（仿 macOS 左上角红色圆点）
        # self.close_button = QPushButton(self)
        # self.close_button.setFixedSize(12, 12)
        # self.close_button.move(10, 10)
        # self.close_button.setStyleSheet("""
        #             QPushButton {
        #                 background-color: #FF5F57;
        #                 border-radius: 6px;
        #                 border: none;
        #             }
        #             QPushButton:hover {
        #                 background-color: #BF4943;
        #             }
        #         """)
        # self.close_button.clicked.connect(self.close)
        self.close_button = MacWindowButton("#FF605C", "x", self)
        self.close_button.move(10, 10)
        self.close_button.clicked.connect(self.close)

        layout = QVBoxLayout()

        title = QLabel("<h2>Permissions Required</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        info_text = (
            "<b>This application requires the following macOS permissions:</b><br><br>"
            "<b>Accessibility</b> and <b>Automation / AppleEvents:</b><br>"
            "Used to<br>"
            "• communicate with <i>Finder</i> when sending apps to the Trash;<br>"
            "• toggle Dock auto-hide via <i>System Events</i>.<br>"
            "macOS will display a system dialog the first time these actions are triggered.  "
            "Please click “OK” to allow the app to control Finder and System Events.<br><br>"
            "This is necessary for the app to work as intended.<br><br>"
            "<hr>"
            "<b>How to grant Accessibility and Input Monitoring permissions:</b><br>"
            "1. Open <b>System Settings</b> (or <b>System Preferences</b> on older macOS).<br>"
            "2. Go to <b>Privacy & Security</b>.<br>"
            "3. Select <b>Accessibility</b> from the sidebar.<br>"
            "4. Click the <b>+</b> button and add this application.<br>"
            "5. Repeat for <b>Terminal</b> if necessary.<br>"
            "6. Restart the app if necessary.<br><br>"
            "For AppleEvents, macOS will prompt you automatically when needed.<br><br>"
            "<hr>"
            "<b>How to use this application:</b><br>"
"1. On first launch, the app will request permission to control Finder and System Events. Please grant permission and restart the application.<br>"
"2. When the app runs for the first time, it will index all available applications on your Mac. This process may take some time if you have many apps installed.<br>"
"3. After indexing, if you notice that some app icons are not displayed correctly, please restart the app once more. Icons will then appear as expected.<br><br>"
"From then on, Raspberry works similarly to Launchpad, with some improvements:<br>"
"• Click any app icon to launch that application instantly.<br>"
"• Right-click an app icon to create a group. You can enter a group by clicking its icon, and exit by double-clicking the blank area below the group. Likewise, double-clicking any blank space in the main interface will close it.<br>"
"• To add more apps to a group, simply right-click other app icons in the main interface and select the desired group—no need to drag and drop repeatedly.<br>"
"• Within a group, right-click an app to remove it or move it to another group.<br>"
"• To rename a group, open it and double-click the group name at the top.<br>"
"• To uninstall an app, right-click its icon and choose to move it to the Trash. For best results, use this feature together with dedicated uninstaller apps.<br>"
"• When you install new apps, Raspberry will automatically index them and display them at the end of the main interface within about 30 seconds.<br>"
"• To customize the order of apps and groups, use keyboard shortcuts: Press the spacebar to focus the first app or group (when not searching), spacebar to move focus right, Shift+space to move left, up/down arrows to move focus vertically.<br>"
"• Press Return to open the focused app or group. In a group, press Tab to exit to the main interface.<br>"
"• If you have multiple pages, use the left and right arrow keys to turn pages.<br>"
"• To adjust the order of the focused app or group, use Shift+left/right arrow keys. Changes are saved automatically.<br>"
"• If you previously had many Launchpad groups and want to transfer them efficiently, Raspberry offers a paid feature to back up and import your group information before upgrading to macOS 26. About 80–90% of apps can be grouped with a click. If you have many apps, this feature can save you significant time!<br><br>"
"<b>Enjoy using Raspberry! 😊🎉</b>"
        )

        info_label = QTextEdit()
        info_label.setReadOnly(True)
        info_label.setHtml(info_text)
        info_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(info_label)

        self.setLayout(layout)

    def first_show_window(self):
        home_dir = base_dir
        tarname1 = "RaspberryAppPath"
        fulldir1 = os.path.join(home_dir, tarname1)
        if not os.path.exists(fulldir1):
            os.mkdir(fulldir1)
        tarname2 = "Permission.txt"
        self.fulldir4 = os.path.join(fulldir1, tarname2)
        if not os.path.exists(self.fulldir4):
            self.show()
            self.raise_()
            with open(self.fulldir4, 'a', encoding='utf-8') as f0:
                f0.write('shown')

    def show_window(self):
        self.show()
        self.raise_()

    def center(self):  # 设置窗口居中
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


style_sheet_ori = '''
	QTabWidget::pane {
		border: 1px solid #ECECEC;
		background: #ECECEC;
		border-radius: 9px;
}
	QTableWidget{
		border: 1px solid grey;  
		border-radius:4px;
		background-clip: border;
		background-color: #FFFFFF;
		color: #000000;
		font: 14pt Helvetica;
}
	QWidget#Main {
		border: 1px solid #ECECEC;
		background: #ECECEC;
		border-radius: 9px;
}
	QPushButton{
		border: 1px outset grey;
		background-color: #FFFFFF;
		border-radius: 4px;
		padding: 1px;
		color: #000000
}
	QPushButton:pressed{
		border: 1px outset grey;
		background-color: #0085FF;
		border-radius: 4px;
		padding: 1px;
		color: #FFFFFF
}
	QPlainTextEdit{
		border: 1px solid grey;  
		border-radius:4px;
		padding: 1px 5px 1px 3px; 
		background-clip: border;
		background-color: #F3F2EE;
		color: #000000;
		font: 14pt Times New Roman;
}
	QPlainTextEdit#edit{
		border: 1px solid grey;  
		border-radius:4px;
		padding: 1px 5px 1px 3px; 
		background-clip: border;
		background-color: #FFFFFF;
		color: rgb(113, 113, 113);
		font: 14pt Helvetica;
}
	QTableWidget#small{
		border: 1px solid grey;  
		border-radius:4px;
		background-clip: border;
		background-color: #F3F2EE;
		color: #000000;
		font: 14pt Times New Roman;
}
	QLineEdit{
		border-radius:4px;
		border: 1px solid gray;
		background-color: #FFFFFF;
}
	QTextEdit{
		border: 1px grey;  
		border-radius:4px;
		padding: 1px 5px 1px 3px; 
		background-clip: border;
		background-color: #F3F2EE;
		color: #000000;
		font: 14pt;
}
	QListWidget{
		border: 1px grey;  
		border-radius:4px;
		padding: 1px 5px 1px 3px; 
		background-clip: border;
		background-color: #F3F2EE;
		color: #000000;
		font: 14pt;
}
'''

if __name__ == "__main__":
    SINGLETON = "com.ryanthehito.raspberry.singleton"

    def other_instance_running():
        s = QLocalSocket()
        s.connectToServer(SINGLETON)
        ok = s.waitForConnected(100)
        s.close()
        return ok

    if other_instance_running():
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    apps = get_applications()
    permission = PermissionInfoWidget()
    permission.first_show_window()
    win = LaunchpadWindow(apps)
    win.setAutoFillBackground(True)
    p = win.palette()
    p.setColor(win.backgroundRole(), QColor('#ECECEC'))
    win.setPalette(p)
    win.hide()
    app.setStyleSheet(style_sheet_ori)

    def bring_main_window_to_front():
        win.showNormal()  # 如果窗口被最小化
        win.raise_()  # 提到最前
        win.activateWindow()  # 获取焦点

    _server = QLocalServer()
    QLocalServer.removeServer(SINGLETON)
    _server.listen(SINGLETON)
    _server.newConnection.connect(lambda: bring_main_window_to_front())

    # if sys.platform == "darwin":
    #     listener = AppEventListener.alloc().initWithMainWindow_(win)
    # def on_app_activated(state):
    #     if state == Qt.ApplicationState.ApplicationActive:
    #         # 这里调用你的主界面显示方法
    #         win.show_main_window()
    # app.applicationStateChanged.connect(on_app_activated)
    class _DockClickDelegate(NSObject):
        # selector: applicationShouldHandleReopen:hasVisibleWindows:
        def applicationShouldHandleReopen_hasVisibleWindows_(self, app, flag):
            # 仅当 Dock 图标被点（或 Finder 再次双击图标）时会进来
            QTimer.singleShot(0, win.show_main_window)
            # 返回 False 让 Qt 自己决定是否把其他窗口带到前台
            return False
    dock_delegate = _DockClickDelegate.alloc().init()
    NSApp.setDelegate_(dock_delegate)

    sys.exit(app.exec())
