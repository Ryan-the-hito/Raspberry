#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -*- encoding:UTF-8 -*-
# coding=utf-8
# coding:utf-8

import os
import math
import datetime
import plistlib
import subprocess
import yaml
import json
import time
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QGridLayout, QPushButton, QLineEdit, QMenu, QLabel, QHBoxLayout, QSizePolicy, QMenuBar, QMessageBox, QFileDialog, QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QDialog, QTextEdit, QToolButton, QProgressBar, QSlider, QWidgetAction, QInputDialog
)
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QFont, QPalette, QColor, QGuiApplication, QPainterPath, QRegion, QMouseEvent, QTextOption, QFontMetrics, QLinearGradient, QPen, QBrush, QAction, QSurfaceFormat, QCursor, QDrag
from PyQt6.QtCore import Qt, QPropertyAnimation, QRect, pyqtSignal, QSize, QPoint, QRectF, QTimer, QThread, QEasingCurve, QParallelAnimationGroup, QAbstractAnimation, QEvent, QPointF, QCoreApplication, QElapsedTimer, QEventLoop, QTranslator, QLocale, QLibraryInfo, pyqtSlot, QMargins, QMimeData
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
from PyQt6 import sip
from bs4 import BeautifulSoup
import html2text
if sys.platform == "darwin":
    import objc
    from Foundation import NSObject, NSNotificationCenter, NSSelectorFromString, NSDistributedNotificationCenter, NSUserDefaults, NSFileManager
    from AppKit import NSWorkspace, NSImage, NSApp
    from PyQt6.QtGui import QImage


GROUPS_FILE = os.path.expanduser("~/.launchpad_groups.json")
ICON_CACHE_DIR = os.path.expanduser("~/.launchpad_icon_cache")
os.makedirs(ICON_CACHE_DIR, exist_ok=True)
APP_PATHS_FILE = os.path.expanduser("~/.launchpad_app_paths.json")
APP_ORDER_FILE = os.path.expanduser("~/.launchpad_app_order.json")
MAIN_ORDER_FILE = os.path.expanduser("~/.launchpad_main_order.json")
DISPLAY_NAME_MAP_FILE = os.path.expanduser("~/.raspberry_display_names.json")
ALIAS_NAME_MAP_FILE = os.path.expanduser("~/.raspberry_alias_names.json")
DISPLAY_PROFILE_CACHE_FILE = os.path.expanduser("~/.raspberry_display_profiles.json")
VERSION = "0.0.16"
NAME = 'Raspberry Pro'

os.environ["QT_QUICK_BACKEND"] = "metal"

fmt = QSurfaceFormat()
fmt.setSamples(8)  # 打开 MSAA 多重采样抗锯齿
QSurfaceFormat.setDefaultFormat(fmt)

def load_display_name_map():
    try:
        if os.path.exists(DISPLAY_NAME_MAP_FILE):
            with open(DISPLAY_NAME_MAP_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_display_name_map(data: dict):
    try:
        with open(DISPLAY_NAME_MAP_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_alias_name_map():
    try:
        if os.path.exists(ALIAS_NAME_MAP_FILE):
            with open(ALIAS_NAME_MAP_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_alias_name_map(data: dict):
    try:
        with open(ALIAS_NAME_MAP_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_display_profile_cache():
    """
    Persisted auto-compact decisions keyed by screen name + resolution.
    """
    try:
        if os.path.exists(DISPLAY_PROFILE_CACHE_FILE):
            with open(DISPLAY_PROFILE_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {}


def save_display_profile_cache(data: dict):
    try:
        with open(DISPLAY_PROFILE_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _normalize_display_name(name: str) -> str:
    if not name:
        return ""
    if name.lower().endswith(".app"):
        return name[:-4]
    return name


def get_finder_display_name(path: str) -> str:
    """
    Return Finder-visible display name for a given path.
    """
    if sys.platform == "darwin":
        try:
            name = NSFileManager.defaultManager().displayNameAtPath_(path)
            if name:
                return _normalize_display_name(str(name))
        except Exception:
            pass
    return _normalize_display_name(os.path.basename(path))

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


def clean_env_for_child():
    """
    Remove Qt-related env vars so child apps don't inherit our packaged Qt paths.
    """
    env = os.environ.copy()
    for key in [
        "QT_PLUGIN_PATH",
        "QT_QPA_PLATFORM_PLUGIN_PATH",
        "QT_QUICK_BACKEND",
        "QT_WEBENGINE_DISABLE_SANDBOX",
        "QT_SCALE_FACTOR",
        "DYLD_LIBRARY_PATH",
        "DYLD_FRAMEWORK_PATH",
    ]:
        env.pop(key, None)
    return env

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
    # 特例：i18n 文件夹必须强制更新
    if item.is_dir() and item.name == "i18n":
        if os.path.exists(target_item):
            shutil.rmtree(target_item)  # 先删掉旧的
        shutil.copytree(item, target_item)
        continue
    if os.path.exists(target_item):
        continue  # 已存在就跳过
    if item.is_dir():
        shutil.copytree(item, target_item)
    else:
        os.makedirs(os.path.dirname(target_item), exist_ok=True)  # 确保父目录存在
        shutil.copy2(item, target_item)


def load_translation(app, lang: str = None):
    """
    lang: "system" -> 跟随系统；"en", "zh_CN", "ja_JP"…
    """
    if lang is None or lang == "system":
        lang = QLocale.system().name()           # 例如 "zh_CN"

    # 1) Qt 自带的翻译（对话框按钮等）
    qt_trans = QTranslator(app)
    qt_translations_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if qt_trans.load("qt_" + lang, qt_translations_path):
        app.installTranslator(qt_trans)

    # 2) 程序自己的翻译
    app_trans = QTranslator(app)
    search_paths = [
        Path(BasePath) / "translations",                       # 打包资源
        Path.home() / "Library/Application Support/com.ryanthehito.raspberry/Resources/i18n"
    ]
    for p in search_paths:
        qm_file = p / f"{lang}.qm"
        if qm_file.exists() and app_trans.load(str(qm_file)):
            app.installTranslator(app_trans)
            break


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


# def get_finder_icon(app_path):
#     """
#     获取 Finder 显示的 icon（支持自定义 icon）(在Tahoe上会造成透明像素黑色斑点)
#     """
#     if sys.platform != "darwin":
#         return QIcon()
#     nsimage = NSWorkspace.sharedWorkspace().iconForFile_(app_path)
#     if nsimage is None:
#         return QIcon()
#     image_data = nsimage.TIFFRepresentation()
#     if image_data is None:
#         return QIcon()
#     qimage = QImage.fromData(bytes(image_data))
#     return QIcon(QPixmap.fromImage(qimage))

# def get_finder_icon(app_path): # 似乎未解决问题
#     if sys.platform != "darwin":
#         return QIcon()
#     nsimage = NSWorkspace.sharedWorkspace().iconForFile_(app_path)
#     if nsimage is None:
#         return QIcon()
#     image_data = nsimage.TIFFRepresentation()
#     if image_data is None:
#         return QIcon()
#     qimage = QImage.fromData(bytes(image_data))
#     # 修复黑色斑点：将透明像素填充为白色
#     if qimage.hasAlphaChannel():
#         for y in range(qimage.height()):
#             for x in range(qimage.width()):
#                 color = qimage.pixelColor(x, y)
#                 if color.alpha() == 0:
#                     color.setRgb(255, 255, 255, 0)  # 透明像素填充为白色
#                     qimage.setPixelColor(x, y, color)
#     return QIcon(QPixmap.fromImage(qimage))

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
    display_name_map = load_display_name_map()
    alias_name_map = load_alias_name_map()
    display_dirty = False
    alias_dirty = False
    apps = []
    seen_paths = set()
    for app_path in app_paths:
        seen_paths.add(app_path)
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
        display_name = get_finder_display_name(app_path)
        if _normalize_display_name(display_name_map.get(app_path, "")) != display_name:
            display_dirty = True
            display_name_map[app_path] = display_name
        alias_val = alias_name_map.get(app_path)
        alias_val = _normalize_display_name(alias_val) if alias_val else None
        if alias_val and alias_val != alias_name_map.get(app_path):
            alias_name_map[app_path] = alias_val
            alias_dirty = True
        show_name = alias_val or display_name
        icon = load_icon_from_cache(app_path, name)
        if not icon:
            try:
                icon = get_finder_icon(app_path)
                if not icon.isNull():
                    save_icon_to_cache(icon, app_path, name)
            except Exception as e:
                print(f"Failed to load icon for {app_path}: {e}")
                icon = QIcon()
        apps.append({'name': show_name, 'display_name': display_name, 'icon': icon, 'path': app_path})
    # 清理不存在的路径
    for stale in list(display_name_map.keys()):
        if stale not in seen_paths:
            display_dirty = True
            display_name_map.pop(stale, None)
    for stale in list(alias_name_map.keys()):
        if stale not in seen_paths:
            alias_dirty = True
            alias_name_map.pop(stale, None)
    if display_dirty:
        save_display_name_map(display_name_map)
    if alias_dirty:
        save_alias_name_map(alias_name_map)
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


def is_newer_version(latest: str, current: str) -> bool:
    # 'v0.0.12' vs 'v0.0.11'
    def parse(v: str):
        return [int(x) for x in v.lstrip('vV').split('.')]
    try:
        return parse(latest) > parse(current)
    except Exception:
        return False


def safe_delete_widget(w):
    try:
        if w is not None and not sip.isdeleted(w):
            # 先断开父子关系，再让 Qt 异步回收
            w.setParent(None)
            w.deleteLater()
    except RuntimeError:
        pass


# 拖拽排序常量（与你现有布局一致）
GRID_COLS = 7
GRID_ROWS = 5
ICON_W = 140
ICON_H = 140
AUTO_PAGE_EDGE_PX = 40        # 靠左右边缘触发自动翻页的感应宽度
AUTO_PAGE_DELAY_MS = 500      # 悬停翻页延迟


class InsertCursorOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._visible = False
        self._line_x = None
        self._line_top = 0
        self._line_bottom = 0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setObjectName("insertOverlay")
        self.hide()

    def show_line(self, x: int, top: int, bottom: int):
        # 健壮：父已销毁/不可用时直接忽略
        p = self.parentWidget()
        if p is None:
            return
        try:
            self.setGeometry(p.rect())
        except RuntimeError:
            return

        self._visible = True
        self._line_x = x
        self._line_top = top
        self._line_bottom = bottom
        self.show()
        self.update()

    def hide_line(self):
        if not self._visible:
            return
        self._visible = False
        self._line_x = None
        try:
            self.hide()
        except RuntimeError:
            pass
        self.update()

    def paintEvent(self, event):
        if not self._visible or self._line_x is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(0, 120, 255), 3)
        painter.setPen(pen)
        painter.drawLine(self._line_x, self._line_top, self._line_x, self._line_bottom)



class AppGridWidget(QWidget):
    """
    作为主界面和组内网格容器的统一拖拽目标：
    - 计算插入槽位（row, col -> slot_index）
    - 绘制插入光标（通过 InsertCursorOverlay）
    - 自动翻页（左右边缘悬停）
    调用方需提供回调：
      - get_page_items(): 返回当前页的“可视条目”列表 [('group'|'app', obj), ...] 或 仅 apps
      - on_drop_app(app_path: str, slot_index_on_page: int): 执行排序后的数据更新
      - request_page_change(direction: int): -1 往左翻页，+1 往右翻页
      - accept_groups: bool  本网格是否包含 group（主界面 True，组内 False）
      - clamp_to_app_zone: bool 主界面 True（只允许 apps 段），组内 False
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.overlay = InsertCursorOverlay(self)
        self._get_page_items = None
        self._on_drop_app = None
        self._request_page_change = None
        self._accept_groups = True
        self._clamp_to_app_zone = False

        self._auto_page_timer = QTimer(self)
        self._auto_page_timer.setSingleShot(True)
        self._auto_page_timer.timeout.connect(self._do_auto_page)
        self._auto_page_dir = 0  # -1 左, +1 右

        self._enable_drag = True

        self._edge_hover_timer = QTimer(self)
        self._edge_hover_timer.setSingleShot(True)
        self._edge_hover_timer.timeout.connect(self._do_edge_auto_move)
        self._edge_hover_info = None  # (direction, app_path)

    def configure(self, get_page_items, on_drop_app, request_page_change,
                  accept_groups=True, clamp_to_app_zone=False, enable_drag=True):
        self._get_page_items = get_page_items
        self._on_drop_app = on_drop_app
        self._request_page_change = request_page_change
        self._accept_groups = accept_groups
        self._clamp_to_app_zone = clamp_to_app_zone
        self._enable_drag = enable_drag

    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            if hasattr(self, "overlay") and self.overlay is not None:
                self.overlay.resize(self.size())
        except RuntimeError:
            # overlay 已经被 Qt 删除，忽略
            pass

    # ---- 拖拽事件 ----
    def dragEnterEvent(self, event):
        if not self._enable_drag:
            event.ignore()
            return
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if not self._enable_drag:
            event.ignore()
            return

        self._ensure_overlay()
        slot_idx, line_x, line_top, line_bottom = self._calc_insert_visuals(event.position().toPoint())
        items = self._get_page_items() if self._get_page_items else []
        n = min(len(items), GRID_COLS * GRID_ROWS)

        # 判断是否在第一页第一个/最后一个插入位置
        is_first = (slot_idx == 0)
        is_last = (slot_idx == n)
        if is_first or is_last:
            # 启动2秒定时器
            if not self._edge_hover_timer.isActive():
                app_path = event.mimeData().text()
                direction = -1 if is_first else +1
                self._edge_hover_info = (direction, app_path)
                self._edge_hover_timer.start(2000)
        else:
            self._edge_hover_timer.stop()
            self._edge_hover_info = None

        if slot_idx is None:
            try:
                self.overlay.hide_line()
            except RuntimeError:
                pass
            event.ignore()
            return

        try:
            self.overlay.show_line(line_x, line_top, line_bottom)
        except RuntimeError:
            self._ensure_overlay()
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._auto_page_timer.stop()
        self._auto_page_dir = 0
        self._edge_hover_timer.stop()
        self._edge_hover_info = None
        try:
            self.overlay.hide_line()
        except RuntimeError:
            pass
        event.accept()

    def dropEvent(self, event):
        if not self._enable_drag:
            event.ignore()
            return
        self._auto_page_timer.stop()
        self._auto_page_dir = 0
        self._edge_hover_timer.stop()
        self._edge_hover_info = None
        pos = event.position().toPoint()
        slot_idx, *_ = self._calc_insert_visuals(pos)
        try:
            self.overlay.hide_line()
        except RuntimeError:
            pass
        if slot_idx is None or not self._on_drop_app:
            event.ignore()
            return
        app_path = event.mimeData().text()
        self._on_drop_app(app_path, slot_idx)
        event.acceptProposedAction()

    # ---

    def _do_edge_auto_move(self):
        # 2秒到时，翻页并移动app
        if not self._edge_hover_info:
            return
        direction, app_path = self._edge_hover_info
        self._edge_hover_info = None
        if self._request_page_change:
            self._request_page_change(direction)
        # 需要等翻页完成后再插入
        QTimer.singleShot(100, lambda: self._auto_move_app_after_page_change(app_path, direction))

    def _auto_move_app_after_page_change(self, app_path, direction):
        # direction: -1=上一页, +1=下一页
        # 插入到新页的第一个/最后一个位置
        items = self._get_page_items() if self._get_page_items else []
        n = min(len(items), GRID_COLS * GRID_ROWS)
        slot_idx = 0 if direction == +1 else n
        if self._on_drop_app:
            self._on_drop_app(app_path, slot_idx)

    # ---- 辅助：计算插入位置和光标 ----
    def _calc_insert_visuals(self, pos: QPoint):
        items = self._get_page_items() if self._get_page_items else []
        n = min(len(items), GRID_COLS * GRID_ROWS)
        if n == 0:
            cell = self._cell_rect(0, 0)
            line_x = cell.left()
            return 0, line_x, cell.top(), cell.bottom()

        best_idx = None
        best_dx = 10 ** 9
        target_cell = None
        for idx in range(GRID_COLS * GRID_ROWS):
            row = idx // GRID_COLS
            col = idx % GRID_COLS
            if row >= GRID_ROWS:
                break
            rect = self._cell_rect(row, col)
            x_left = rect.left()
            dx = abs(pos.x() - x_left)
            if rect.top() - ICON_H // 2 <= pos.y() <= rect.bottom() + ICON_H // 2:
                dx -= 50
            if dx < best_dx:
                best_dx = dx
                best_idx = idx
                target_cell = rect

        # 处理最后一个插入位置（右下角）
        if n > 0:
            last_row = (n - 1) // GRID_COLS
            last_col = (n - 1) % GRID_COLS
            last_rect = self._cell_rect(last_row, last_col)
            # 判断鼠标是否在最后一个格子的右侧一定范围内
            if (
                    last_rect.left() + last_rect.width() <= pos.x() <= last_rect.left() + last_rect.width() + ICON_W // 2 and
                    last_rect.top() - ICON_H // 2 <= pos.y() <= last_rect.bottom() + ICON_H // 2):
                # 插入到最后
                return n, last_rect.right(), last_rect.top(), last_rect.bottom()

        if best_idx is None:
            return None, None, None, None

        # 主界面apps区约束
        if self._clamp_to_app_zone and self._accept_groups:
            first_app_slot, last_app_slot = self._page_app_slot_range(items)
            if first_app_slot is None:
                return None, None, None, None
            best_idx = max(first_app_slot, min(best_idx, last_app_slot + 1))

        line_x = target_cell.left()
        return best_idx, line_x, target_cell.top(), target_cell.bottom()

    def _cell_rect(self, row: int, col: int) -> QRect:
        """
        使用网格内现有小部件的几何与布局间距推断单元格位置。
        为稳妥：以第一行已有的任意控件为基准推算格子宽高与间距。
        如该行为空，则使用默认 ICON_W/H 和布局 spacing。
        """
        layout = self.parent().layout() if self.parent() else None
        # 直接根据已有控件几何推算
        children = [w for w in self.findChildren(QWidget) if w is not self.overlay]
        sample = None
        for w in children:
            if isinstance(w, (AppButton, GroupButton, EmptyButton)):
                sample = w
                break
        if sample:
            cell_w = sample.width()
            cell_h = sample.height()
        else:
            cell_w, cell_h = ICON_W, ICON_H

        grid_layout = None
        if hasattr(self.parent(), "grid_layout"):
            grid_layout = getattr(self.parent(), "grid_layout")
        hgap = grid_layout.horizontalSpacing() if grid_layout and grid_layout.horizontalSpacing() >= 0 else 10
        vgap = grid_layout.verticalSpacing() if grid_layout and grid_layout.verticalSpacing() >= 0 else 10
        m = grid_layout.contentsMargins() if grid_layout else QMargins(0, 0, 0, 0)
        left = m.left() + col * (cell_w + hgap)
        top = m.top() + row * (cell_h + vgap)
        return QRect(left, top, cell_w, cell_h)

    def _page_app_slot_range(self, items):
        """
        对主界面页：返回当前页内 apps 段的 slot 范围（first, last）。
        items: 当前页 [('group'|'app', obj), ...]
        """
        first = None
        last = None
        for idx, (typ, _) in enumerate(items[:GRID_COLS * GRID_ROWS]):
            if typ == 'app':
                if first is None:
                    first = idx
                last = idx
        return first, last

    # ---- 自动翻页逻辑 ----
    def _maybe_start_auto_page(self, pos: QPoint) -> bool:
        w = self.width()
        if pos.x() <= AUTO_PAGE_EDGE_PX:
            self._auto_page_dir = -1
            if not self._auto_page_timer.isActive():
                self._auto_page_timer.start(AUTO_PAGE_DELAY_MS)
            return True
        elif pos.x() >= w - AUTO_PAGE_EDGE_PX:
            self._auto_page_dir = +1
            if not self._auto_page_timer.isActive():
                self._auto_page_timer.start(AUTO_PAGE_DELAY_MS)
            return True
        else:
            if self._auto_page_timer.isActive():
                self._auto_page_timer.stop()
            self._auto_page_dir = 0
            return False

    def _do_auto_page(self):
        if self._auto_page_dir != 0 and self._request_page_change:
            self._request_page_change(self._auto_page_dir)
        self._auto_page_dir = 0

    def _ensure_overlay(self):
        # overlay 失效或已被 Qt 删除时重建
        recreate = False
        if not hasattr(self, "overlay") or self.overlay is None:
            recreate = True
        else:
            try:
                _ = self.overlay.isVisible()
            except RuntimeError:
                recreate = True
        if recreate:
            self.overlay = InsertCursorOverlay(self)


class UpdateCheckWorker(QThread):
    update_available = pyqtSignal(str)  # latest version, e.g., 'v0.0.13'
    checked_ok = pyqtSignal(str)        # latest version (even if not newer),用于日志或状态
    checked_error = pyqtSignal(str)     # error message

    def __init__(self, current_version: str, interval_seconds: int = 86400, parent=None):
        super().__init__(parent)
        self._running = True
        self.current_version = current_version  # e.g., 'v0.0.12'
        self.interval_seconds = interval_seconds

    def stop(self):
        self._running = False

    def run(self):
        # 循环：只要应用在运行，就每隔 interval 检查一次
        while self._running:
            try:
                text = WindowUpdate.fetch_latest_version_text()
                latest = WindowUpdate.extract_latest_tag(text) if text else None
                if latest:
                    self.checked_ok.emit(latest)
                    if is_newer_version(latest, 'v' + VERSION):
                        # 通知主线程有新版本
                        self.update_available.emit(latest)
                else:
                    self.checked_error.emit("No version tag found")
            except Exception as e:
                self.checked_error.emit(str(e))

            # 可中断的“休眠”24小时
            for _ in range(self.interval_seconds):
                if not self._running:
                    return
                self.msleep(1000)



class AppIndexWorker(QThread):
    finished = pyqtSignal(object)  # apps

    def run(self):
        apps = get_applications()
        self.finished.emit(apps)


class IndexingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setModal(True)
        self.setFixedSize(340, 120)
        layout = QVBoxLayout()
        label = QLabel(self.tr("Raspberry is indexing applications, please wait and do not close this app. Raspberry will be ready after this window disappers."))
        label.setWordWrap(True)
        layout.addWidget(label)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # 无限进度条
        layout.addWidget(self.progress)
        self.setLayout(layout)


class EmptyButton(QPushButton):
    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.main_window = main_window          # 保存主窗引用
        self.setFixedSize(135, 128)
        self.setFlat(True)
        self.setEnabled(True)                  # 必须能接收事件
        # 和背景一致：完全透明
        self.setStyleSheet("background: transparent; border: none;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.main_window:
            # 只在传统模式下单击关闭
            if hasattr(self.main_window, "traditional_mode") and self.main_window.traditional_mode:
                self.main_window.close_main_window()
                return
        super().mousePressEvent(event)

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
            subprocess.Popen(['osascript', '-e', applescript], env=clean_env_for_child())
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


class CustomInputDialog(QDialog):
    """
    Frameless input dialog styled like CustomMessageBox.
    Result: exec() returns button index; text property stores input.
    """
    def __init__(self, title, message, default_text="", parent=None, buttons=("OK", "Cancel"), default=0):
        super().__init__(parent)
        self.radius = 16
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFixedSize(420, 240)
        self.result = None
        self.text = default_text
        self.drag_pos = None

        # 关闭按钮
        self.close_button = MacWindowButton("#FF605C", "x", self)
        self.close_button.move(10, 10)
        self.close_button.clicked.connect(self.reject)

        layout = QVBoxLayout()
        layout.setContentsMargins(32, 40, 32, 24)
        layout.setSpacing(12)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 600;")
        layout.addWidget(title_lbl)

        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("font-size: 14px;")
        layout.addWidget(msg_lbl)

        self.line_edit = QLineEdit(default_text)
        self.line_edit.setMinimumHeight(32)
        self.line_edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid #CCCCCC;
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1.5px solid #0085FF;
            }
        """)
        layout.addWidget(self.line_edit)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btns = []
        for i, btn_text in enumerate(buttons):
            btn = WhiteButton(btn_text)
            btn.setFixedWidth(150)
            btn.clicked.connect(lambda checked, idx=i: self._on_btn(idx))
            btn_layout.addWidget(btn)
            self.btns.append(btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.btns[default].setFocus()

    def _on_btn(self, idx):
        self.result = idx
        self.text = self.line_edit.text()
        self.done(idx)

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
            pass
            #print("GlassButton was double-clicked!")
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
            error_msg = self.tr(f"Clear cache failed: %n").replace('%n', str(e))
            self.finished.emit(None, None, None, error_msg)
            return
        try:
            apps = get_applications()
            groups = load_groups(apps)
            filtered_apps = [a for a in apps if not any(a in g['apps'] for g in groups)]
            self.finished.emit(apps, groups, filtered_apps, "")
        except Exception as e:
            error_msg = self.tr(f"Failed to refresh the application: %n").replace('%n', str(e))
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
        display_name_map = load_display_name_map()
        alias_name_map = load_alias_name_map()
        display_dirty = False
        alias_dirty = False
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
                display_name = get_finder_display_name(app_path)
                if _normalize_display_name(display_name_map.get(app_path, "")) != display_name:
                    display_dirty = True
                    display_name_map[app_path] = display_name
                alias_val = alias_name_map.get(app_path)
                alias_val = _normalize_display_name(alias_val) if alias_val else None
                if alias_val and alias_val != alias_name_map.get(app_path):
                    alias_name_map[app_path] = alias_val
                    alias_dirty = True
                show_name = alias_val or display_name
                new_apps.append({'name': show_name, 'display_name': display_name, 'icon': icon, 'path': app_path})
        if new_apps:
            all_paths = list(known_paths | found_paths)
            save_app_paths(all_paths)
        # 清理不存在的路径
        for stale in list(display_name_map.keys()):
            if stale not in found_paths and stale not in known_paths:
                display_dirty = True
                display_name_map.pop(stale, None)
        for stale in list(alias_name_map.keys()):
            if stale not in found_paths and stale not in known_paths:
                alias_dirty = True
                alias_name_map.pop(stale, None)
        if display_dirty:
            save_display_name_map(display_name_map)
        if alias_dirty:
            save_alias_name_map(alias_name_map)
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

        # 拖拽/点击判定状态
        self._press_pos = None
        self._dragging = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 只记录，不启动
            self._press_pos = event.position()
            self._dragging = False
            event.accept()
            return
        # 其它按键（右键等）维持原行为
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_pos is not None and not self._dragging:
            # 判断是否进入拖拽
            if (event.position() - self._press_pos).manhattanLength() > QApplication.startDragDistance():
                self._dragging = True
                self.startDrag()
                # 拖拽开始后，不交给父类处理，避免误触发点击等
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            try:
                # 如果按下过，且没有发生拖拽，且移动未超过阈值 → 视为点击，才启动
                if self._press_pos is not None and not self._dragging:
                    if (event.position() - self._press_pos).manhattanLength() <= QApplication.startDragDistance():
                        # 真正启动 app（与原先 mousePress 的逻辑相同）
                        subprocess.Popen(['open', self.app_info['path']], env=clean_env_for_child())
                        if self.main_window:
                            self.main_window.close_main_window()
                event.accept()
            finally:
                # 收尾复位
                self._press_pos = None
                self._dragging = False
            return
        super().mouseReleaseEvent(event)

    def startDrag(self):
        # 构造拖拽对象
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self.app_info['path'])  # 唯一标识
        drag.setMimeData(mime)
        # 拖拽显示的图标
        pm = self.app_info['icon'].pixmap(64, 64)
        drag.setPixmap(pm)
        # 触发拖拽（Move 意味着排序）
        drag.exec(Qt.DropAction.MoveAction)

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
            move_menu = QMenu(self.tr("Move to another group"), self)
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
            menu.addAction(self.tr("Put it back to the main interface"), self.move_out_of_group)
        if not self.parent_group:
            group_menu = QMenu(self.tr("Combine into a group"), self)
            for group in self.main_window.groups:
                group_menu.addAction(group['name'], lambda g=group: self.main_window.combine_app_to_group(self, g))
            group_menu.addAction(self.tr("🆕 New group"), lambda: self.main_window.combine_app_to_group(self, None))
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
        menu.addAction(self.tr("Move to the trash can"), self.move_to_trash)
        menu.exec(self.mapToGlobal(pos))

    def move_out_of_group(self):
        if self.main_window and self.parent_group:
            self.main_window.move_app_out_of_group(self.app_info, self.parent_group)

    def move_to_trash(self):
        subprocess.Popen(
            ['osascript', '-e', f'tell app "Finder" to move POSIX file "{self.app_info["path"]}" to trash'],
            env=clean_env_for_child()
        )
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
        menu.addAction(self.tr("Rename"), self.rename_group)
        menu.addAction(self.tr("Dissolve this group"), self.disband_group)
        menu.exec(self.mapToGlobal(pos))

    def rename_group(self):
        self.main_window.rename_group(self.group)

    def disband_group(self):
        if self.main_window:
            self.main_window.disband_group(self.group)

# def create_group_icon(apps):
#     size = 140
#     radius = 28
#     icon_size = 30
#     spacing = 6
#     grid = 3
#
#     # 1. 先画玻璃背景到 QImage
#     bg_img = QImage(size, size, QImage.Format.Format_ARGB32)
#     bg_img.fill(Qt.GlobalColor.transparent)
#     painter = QPainter(bg_img)
#     painter.setRenderHint(QPainter.RenderHint.Antialiasing)
#
#     rect = QRectF(0, 0, size, size)
#     path = QPainterPath()
#     path.addRoundedRect(rect, radius, radius)
#     painter.setClipPath(path)
#     # 半透明白色
#     painter.fillPath(path, QColor(255, 255, 255, 40))
#     painter.end()
#
#     # 2. PIL高斯模糊
#     from PIL import Image, ImageFilter
#     pil_img = Image.fromqimage(bg_img)
#     pil_img = pil_img.filter(ImageFilter.GaussianBlur(radius=2))
#     bg_img_blur = QImage(pil_img.tobytes("raw", "RGBA"), pil_img.width, pil_img.height, QImage.Format.Format_ARGB32)
#
#     # 3. 再画到 QPixmap
#     pixmap = QPixmap(size, size)
#     pixmap.fill(Qt.GlobalColor.transparent)
#     painter = QPainter(pixmap)
#     painter.setRenderHint(QPainter.RenderHint.Antialiasing)
#     painter.drawImage(0, 0, bg_img_blur)
#
#     # 4. 画高光（左上和右下）
#     # 左上高光
#     highlight_path = QPainterPath()
#     highlight_path.moveTo(rect.left() + radius, rect.top())
#     highlight_path.arcTo(rect.left(), rect.top(), 2*radius, 2*radius, 90, 90)
#     grad = QLinearGradient(rect.left(), rect.top(), rect.left() + radius*2, rect.top() + radius*2)
#     grad.setColorAt(0, QColor(255,255,255,120))
#     grad.setColorAt(1, QColor(255,255,255,0))
#     painter.setPen(QPen(QBrush(grad), 4))
#     painter.drawPath(highlight_path)
#
#     # 右下高光
#     highlight_path2 = QPainterPath()
#     highlight_path2.moveTo(rect.right() - radius, rect.bottom())
#     highlight_path2.arcTo(rect.right() - 2*radius, rect.bottom() - 2*radius, 2*radius, 2*radius, 270, 90)
#     grad2 = QLinearGradient(rect.right(), rect.bottom(), rect.right() - radius*2, rect.bottom() - radius*2)
#     grad2.setColorAt(0, QColor(255,255,255,100))
#     grad2.setColorAt(1, QColor(255,255,255,0))
#     painter.setPen(QPen(QBrush(grad2), 4))
#     painter.drawPath(highlight_path2)
#
#     # 5. 画圆角边框
#     # border_pen = QPen(QColor(200, 200, 200, 220), 3)
#     # painter.setPen(border_pen)
#     # painter.drawRoundedRect(rect.adjusted(1.5, 1.5, -1.5, -1.5), radius, radius)
#
#     # 6. 画3*3小icon（缩小并居中）
#     n = min(9, len(apps))
#     total_icons = min(n, 9)
#     start_x = (size - (icon_size * grid + spacing * (grid - 1))) // 2
#     start_y = (size - (icon_size * grid + spacing * (grid - 1))) // 2
#     for i in range(total_icons):
#         row, col = divmod(i, 3)
#         icon = apps[i]['icon']
#         icon_pix = icon.pixmap(icon_size, icon_size)
#         x = start_x + col * (icon_size + spacing)
#         y = start_y + row * (icon_size + spacing)
#         painter.drawPixmap(x, y, icon_pix)
#
#     painter.end()
#     return QIcon(pixmap)

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
        self.grid_widget = AppGridWidget()
        self.grid_widget.setStyleSheet('''
            background-color: transparent;
            border: 0px;
        ''')
        self.grid_widget.setMinimumHeight(5 * 150)
        self.grid_widget.setMinimumWidth(content_width)
        self.layout.addWidget(self.grid_widget)

        self.grid_layout = QGridLayout(self.grid_widget)

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

        # GroupWidget __init__ 新增
        self._touchpad_swipe_active = False
        self._touchpad_swipe_accum = 0
        self._touchpad_swipe_btns = []
        self._touchpad_swipe_anim = None
        self._touchpad_swipe_direction = None
        self._touchpad_swipe_timer = None

        def _get_page_items():
            start = self.current_page * self.items_per_page
            end = start + self.items_per_page
            return [('app', a) for a in self.group['apps'][start:end]]

        def _on_drop_app(app_path: str, slot_index_on_page: int):
            self.on_drop_reorder_in_group(app_path, slot_index_on_page)

        def _request_page_change(direction: int):
            total_pages = max(1, (len(self.group['apps']) + self.items_per_page - 1) // self.items_per_page)
            target = self.current_page + (1 if direction > 0 else -1)
            if 0 <= target < total_pages:
                self.goto_page(target)

        self.grid_widget.configure(
            get_page_items=_get_page_items,
            on_drop_app=_on_drop_app,
            request_page_change=_request_page_change,
            accept_groups=False,
            clamp_to_app_zone=False,
            enable_drag=True  # 组内允许拖拽
        )

    def display_apps(self, apps, page=0):
        # 安全清理布局和所有子控件，避免残留和重复删除
        grid_layout = self.grid_layout
        grid_widget = self.grid_widget

        # 先移除布局项
        for i in reversed(range(grid_layout.count())):
            w = grid_layout.itemAt(i).widget()
            try:
                if w is not None:
                    w.setParent(None)
                    w.deleteLater()
            except RuntimeError:
                pass

        # 再保险：删除 grid_widget 下残留子控件，但跳过 overlay
        for w in grid_widget.findChildren(QWidget):
            if w is grid_widget:
                continue
            # 跳过 InsertCursorOverlay
            if w.objectName() == "insertOverlay":
                continue
            # 某些情况下 isinstance 判断更直观：
            # if isinstance(w, InsertCursorOverlay): continue
            try:
                w.setParent(None)
                w.deleteLater()
            except RuntimeError:
                pass
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
        if self.main_window and getattr(self.main_window, "new_keyboard_mode", True):
            return self._handle_key_event_new_mode(event)
        if event.key() == Qt.Key.Key_Escape:
            self.close_group_widget()
            return True
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

    def _handle_key_event_new_mode(self, event):
        key = event.key()
        modifiers = event.modifiers()
        swap_mod = modifiers & (Qt.KeyboardModifier.ControlModifier |
                                Qt.KeyboardModifier.AltModifier |
                                Qt.KeyboardModifier.MetaModifier)
        shift_mod = modifiers & Qt.KeyboardModifier.ShiftModifier

        if key == Qt.Key.Key_Escape:
            self.close_group_widget()
            return True
        if swap_mod and key == Qt.Key.Key_Left:
            self.move_focused_btn_left()
            return True
        if swap_mod and key == Qt.Key.Key_Right:
            self.move_focused_btn_right()
            return True
        if shift_mod and key == Qt.Key.Key_Left:
            self.goto_page(max(self.current_page - 1, 0))
            return True
        if shift_mod and key == Qt.Key.Key_Right:
            total_pages = max(1, (len(self.group['apps']) + self.items_per_page - 1) // self.items_per_page)
            self.goto_page(min(self.current_page + 1, total_pages - 1))
            return True
        if key == Qt.Key.Key_Left:
            self.focus_prev_btn()
            return True
        if key == Qt.Key.Key_Right:
            self.focus_next_btn()
            return True
        if key == Qt.Key.Key_Up:
            self.focus_up_btn()
            return True
        if key == Qt.Key.Key_Down:
            self.focus_down_btn()
            return True
        if key == Qt.Key.Key_Space:
            if shift_mod:
                self.focus_prev_btn()
            else:
                self.focus_next_btn()
            return True
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.focused_btn is None:
                return False
            if shift_mod:
                pos = self.focused_btn.rect().center()
                self.focused_btn.show_context_menu(pos)
            else:
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
        # 动画期间禁翻，避免状态冲突
        if getattr(self, "_is_animating", False):
            event.accept()
            return

        pixel_delta = event.pixelDelta()
        angle_delta = event.angleDelta()
        dx = pixel_delta.x() if pixel_delta.x() != 0 else int(angle_delta.x() / 2)

        if dx != 0:
            # 初始化触控板滑动会话
            if not getattr(self, "_touchpad_swipe_active", False):
                self._touchpad_swipe_active = True
                self._touchpad_swipe_accum = 0
                self._touchpad_swipe_btns = []
                for w in self.grid_widget.findChildren(AppButton):
                    self._touchpad_swipe_btns.append(w)
                for btn in self._touchpad_swipe_btns:
                    if sip.isdeleted(btn):
                        continue
                    btn._orig_pos = btn.pos()

            # 累计位移
            self._touchpad_swipe_accum += dx

            page_w = self.grid_widget.width()
            threshold = page_w // 2

            # 实时越阈值：立刻触发（不等松手）
            if abs(self._touchpad_swipe_accum) >= threshold:
                direction = "left" if self._touchpad_swipe_accum < 0 else "right"
                is_first_page = (self.current_page == 0)
                total_pages = max(1, (len(self.group['apps']) + self.items_per_page - 1) // self.items_per_page)
                is_last_page = (self.current_page == total_pages - 1)

                # 首页右滑 / 末页左滑：四分之一页回弹
                if (direction == "right" and is_first_page) or (direction == "left" and is_last_page):
                    group = QParallelAnimationGroup(self)
                    for btn in self._touchpad_swipe_btns:
                        if sip.isdeleted(btn):
                            continue
                        orig = getattr(btn, "_orig_pos", btn.pos())
                        anim = QPropertyAnimation(btn, b"pos", self)
                        anim.setDuration(180)
                        anim.setStartValue(btn.pos())
                        anim.setEndValue(orig)
                        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                        group.addAnimation(anim)

                    def after_bounce():
                        self._touchpad_swipe_active = False
                        self._touchpad_swipe_accum = 0
                        self._touchpad_swipe_direction = None
                        self._touchpad_swipe_btns = []

                    if self._touchpad_swipe_timer and self._touchpad_swipe_timer.isActive():
                        self._touchpad_swipe_timer.stop()
                    group.finished.connect(after_bounce)
                    group.start()
                    self._touchpad_swipe_anim = group
                    event.accept()
                    return

                # 正常翻页（每次只翻一页）
                if direction == "left":
                    target_page = min(self.current_page + 1, total_pages - 1)
                    remaining = -page_w - self._touchpad_swipe_accum
                else:
                    target_page = max(self.current_page - 1, 0)
                    remaining = page_w - self._touchpad_swipe_accum

                self._is_animating = True
                group = QParallelAnimationGroup(self)
                for btn in self._touchpad_swipe_btns:
                    if sip.isdeleted(btn):
                        continue
                    anim = QPropertyAnimation(btn, b"pos", self)
                    duration = min(240, 160 + int(min(abs(remaining), page_w) * 0.25))
                    anim.setDuration(duration)
                    anim.setStartValue(btn.pos())
                    anim.setEndValue(btn.pos() + QPoint(remaining, 0))
                    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                    group.addAnimation(anim)

                def after_swipe_out():
                    self.goto_page_immediate(target_page)
                    self._is_animating = False
                    self._touchpad_swipe_active = False
                    self._touchpad_swipe_accum = 0
                    self._touchpad_swipe_direction = None
                    self._touchpad_swipe_btns = []

                if self._touchpad_swipe_timer and self._touchpad_swipe_timer.isActive():
                    self._touchpad_swipe_timer.stop()
                group.finished.connect(after_swipe_out)
                group.start()
                self._touchpad_swipe_anim = group
                event.accept()
                return

            # 未越阈值：跟手移动
            for btn in self._touchpad_swipe_btns:
                if sip.isdeleted(btn):
                    continue
                orig = getattr(btn, "_orig_pos", btn.pos())
                btn.move(orig + QPoint(self._touchpad_swipe_accum, 0))

            self._touchpad_swipe_direction = "left" if self._touchpad_swipe_accum < 0 else "right"

            # “松手回弹”的兜底计时器（若中断输入，仍能回弹）
            if self._touchpad_swipe_timer and self._touchpad_swipe_timer.isActive():
                self._touchpad_swipe_timer.stop()
            else:
                self._touchpad_swipe_timer = QTimer(self)
                self._touchpad_swipe_timer.setSingleShot(True)
                self._touchpad_swipe_timer.timeout.connect(self._on_touchpad_swipe_release)
            self._touchpad_swipe_timer.start(300)

            event.accept()
            return

        # 正在触控板滑动会话时，忽略垂直滚动，避免干扰
        if getattr(self, "_touchpad_swipe_active", False):
            event.accept()
            return

        # 传统滚轮垂直翻页保留
        dy = angle_delta.y()
        total_pages = max(1, (len(self.group['apps']) + self.items_per_page - 1) // self.items_per_page)
        if dy > 0:
            self.goto_page(max(self.current_page - 1, 0))
        elif dy < 0:
            self.goto_page(min(self.current_page + 1, total_pages - 1))
        event.accept()

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
        if getattr(self, "_is_animating", False):
            return
        self._is_animating = True

        grid = self.grid_widget
        old_btns = [w for w in grid.findChildren(AppButton)]

        if not old_btns:
            self.display_apps(self.group['apps'], new_page)
            self._is_animating = False
            return

        screen_width = self.width()
        speed = 6000
        anim_group_out = QParallelAnimationGroup(self)

        for btn in old_btns:
            if sip.isdeleted(btn):
                continue
            start_pos = btn.pos()
            if direction == "left":
                end_pos = QPoint(-btn.width(), start_pos.y())
                distance = start_pos.x() + btn.width()
            else:
                end_pos = QPoint(screen_width + btn.width(), start_pos.y())
                distance = screen_width - start_pos.x() + btn.width()
            duration = max(80, int(distance / speed * 1000))
            anim = QPropertyAnimation(btn, b"pos", self)
            anim.setDuration(duration)
            anim.setStartValue(start_pos)
            anim.setEndValue(end_pos)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim_group_out.addAnimation(anim)

        def cleanup_old_btns():
            for btn in old_btns:
                safe_delete_widget(btn)
            # 真正换页
            self.display_apps(self.group['apps'], new_page)
            self._is_animating = False

        anim_group_out.finished.connect(cleanup_old_btns)
        anim_group_out.start()
        self.anim = anim_group_out

    def on_drop_reorder_in_group(self, app_path: str, slot_index_on_page: int):
        # 找源 app
        src_idx = None
        for i, a in enumerate(self.group['apps']):
            if a['path'] == app_path:
                src_idx = i
                break
        if src_idx is None:
            return
        src_app = self.group['apps'][src_idx]

        # 计算目标全局插入位置
        page_start = self.current_page * self.items_per_page
        target = page_start + slot_index_on_page
        target = max(0, min(target, len(self.group['apps'])))

        # 移除原位置，插入新位置（注意：移除后索引偏移）
        del self.group['apps'][src_idx]
        if target > src_idx:
            target -= 1
        self.group['apps'].insert(target, src_app)

        # 组缩略图更新
        self.group['icon'] = create_group_icon(self.group['apps'])
        save_groups(self.main_window.groups)

        # 刷新本组页面
        self.display_apps(self.group['apps'], self.current_page)
        # 主界面也需要刷新（因为组缩略图变了）
        self.main_window.display_apps(self.main_window.filtered_apps, self.main_window.current_page)

    def _on_touchpad_swipe_release(self):
        page_w = self.grid_widget.width()
        threshold = page_w // 2
        accum = self._touchpad_swipe_accum
        direction = self._touchpad_swipe_direction
        btns = self._touchpad_swipe_btns
        total_pages = max(1, (len(self.group['apps']) + self.items_per_page - 1) // self.items_per_page)
        is_first_page = self.current_page == 0
        is_last_page = self.current_page == total_pages - 1

        # 首页右滑
        if is_first_page and accum > 0:
            max_accum = page_w // 4
            if accum > max_accum:
                accum = max_accum
            group = QParallelAnimationGroup(self)
            for btn in btns:
                if sip.isdeleted(btn):
                    continue
                orig = getattr(btn, "_orig_pos", btn.pos())
                anim = QPropertyAnimation(btn, b"pos", self)
                anim.setDuration(200)
                anim.setStartValue(btn.pos())
                anim.setEndValue(orig)
                anim.setEasingCurve(QEasingCurve.Type.InBounce)
                group.addAnimation(anim)
            group.start()
            self._touchpad_swipe_anim = group
            self._touchpad_swipe_active = False
            self._touchpad_swipe_accum = 0
            self._touchpad_swipe_direction = None
            self._touchpad_swipe_btns = []
            return

        # 末页左滑
        if is_last_page and accum < 0:
            min_accum = -page_w // 4
            if accum < min_accum:
                accum = min_accum
            group = QParallelAnimationGroup(self)
            for btn in btns:
                if sip.isdeleted(btn):
                    continue
                orig = getattr(btn, "_orig_pos", btn.pos())
                anim = QPropertyAnimation(btn, b"pos", self)
                anim.setDuration(200)
                anim.setStartValue(btn.pos())
                anim.setEndValue(orig)
                anim.setEasingCurve(QEasingCurve.Type.InBounce)
                group.addAnimation(anim)
            group.start()
            self._touchpad_swipe_anim = group
            self._touchpad_swipe_active = False
            self._touchpad_swipe_accum = 0
            self._touchpad_swipe_direction = None
            self._touchpad_swipe_btns = []
            return

        # 正常回弹或翻页
        if abs(accum) < threshold:
            group = QParallelAnimationGroup(self)
            for btn in btns:
                if sip.isdeleted(btn):
                    continue
                orig = getattr(btn, "_orig_pos", btn.pos())
                anim = QPropertyAnimation(btn, b"pos", self)
                anim.setDuration(200)
                anim.setStartValue(btn.pos())
                anim.setEndValue(orig)
                anim.setEasingCurve(QEasingCurve.Type.InBounce)
                group.addAnimation(anim)
            group.start()
            self._touchpad_swipe_anim = group
        else:
            if direction == "left":
                target_page = min(self.current_page + 1, total_pages - 1)
                remaining = -page_w - accum
            else:
                target_page = max(self.current_page - 1, 0)
                remaining = page_w - accum
            group = QParallelAnimationGroup(self)
            for btn in btns:
                if sip.isdeleted(btn):
                    continue
                anim = QPropertyAnimation(btn, b"pos", self)
                anim.setDuration(200)
                anim.setStartValue(btn.pos())
                anim.setEndValue(btn.pos() + QPoint(remaining, 0))
                anim.setEasingCurve(QEasingCurve.Type.InBounce)
                group.addAnimation(anim)

            def on_anim_start():
                self.goto_page_immediate(target_page)

            group.stateChanged.connect(
                lambda new, old: on_anim_start() if new == QAbstractAnimation.State.Running else None
            )
            group.start()
            self._touchpad_swipe_anim = group
        self._touchpad_swipe_active = False
        self._touchpad_swipe_accum = 0
        self._touchpad_swipe_direction = None
        self._touchpad_swipe_btns = []

    def goto_page_immediate(self, page: int):
        total_pages = max(1, (len(self.group['apps']) + self.items_per_page - 1) // self.items_per_page)
        if page < 0 or page >= total_pages:
            return
        self.current_page = page
        self.display_apps(self.group['apps'], self.current_page)


class Window(AcrylicWindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        #self.setWindowTitle("Acrylic Window")
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
        self.search_bar.setPlaceholderText(self.tr("Search..."))
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

        self.grid_widget = AppGridWidget()
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
        #blay3.addWidget(self.grid_widget, alignment=Qt.AlignmentFlag.AlignHCenter)
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

        # 配置拖拽回调（主界面：包含 groups，且 clamp 到 apps 区域）
        def _get_page_items():
            # 与 LaunchpadWindow.display_apps 相同的来源
            is_searching = bool(self.search_bar.text().strip())
            if is_searching:
                start = self.main_window.current_page * self.main_window.items_per_page
                end = start + self.main_window.items_per_page
                return [('app', a) for a in self.main_window.filtered_apps[start:end]]
            else:
                start = self.main_window.current_page * self.main_window.items_per_page
                end = start + self.main_window.items_per_page
                return self.main_window.main_order[start:end]

        def _on_drop_app(app_path: str, slot_index_on_page: int):
            self.main_window.on_drop_reorder_in_main(app_path, slot_index_on_page)

        def _request_page_change(direction: int):
            target = self.main_window.current_page + (1 if direction > 0 else -1)
            self.main_window.goto_page(target)

        self.grid_widget.configure(
            get_page_items=_get_page_items,
            on_drop_app=_on_drop_app,
            request_page_change=_request_page_change,
            accept_groups=True,
            clamp_to_app_zone=True,
            enable_drag=False  # 禁用主界面拖拽
        )


class LaunchpadWindow(QWidget):
    def __init__(self, apps):
        super().__init__()
        self.compact_mode = self.read_compact_mode_setting()  # or False

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: rgba(255,255,255,1); border-radius: 0px;")
        self.setWindowOpacity(1)
        self._mouse_press_pos = None
        self._mouse_move_pos = None

        self.apps = apps
        self.display_name_map = load_display_name_map()
        self.alias_name_map = load_alias_name_map()
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
        self.apply_display_aliases(refresh=False)

        self.group_widget = None

        self.main_content = MainContentWidget(self, self.apps, self.groups, self)
        self.main_content.setGeometry(self.geometry())
        #self.display_apps(self.filtered_apps, self.current_page)

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
        self.menu = self.menu_bar.addMenu(self.tr("Actions"))
        # 新增菜单项：显示主界面
        self.show_main_action = QAction(self.tr("⭕️ Display the main interface"), self)
        self.menu.addAction(self.show_main_action)
        self.show_main_action.triggered.connect(self.show_main_window)
        # 新增菜单项：关闭主界面
        self.close_main_action = QAction(self.tr("❌ Close the main interface"), self)
        self.close_main_action.setShortcut("Ctrl+W")  # 新增：设置 Command+W 快捷键
        self.menu.addAction(self.close_main_action)
        self.close_main_action.triggered.connect(self.close_main_window)

        self.menu.addSeparator()

        # 沙盒路径
        traditional_mode_dir = os.path.join(base_dir, "RaspberryAppPath")
        os.makedirs(traditional_mode_dir, exist_ok=True)
        self.TRADITIONAL_MODE_FILE = os.path.join(traditional_mode_dir, "TraditionalMode.txt")

        # 在菜单栏添加传统模式选项
        self.traditional_mode = self.read_traditional_mode()
        self.traditional_mode_action = QAction(self.tr("🕹 Traditional Mode (Click blank to close)"), self)
        self.traditional_mode_action.setCheckable(True)
        self.traditional_mode_action.setChecked(self.traditional_mode)
        self.traditional_mode_action.triggered.connect(self.toggle_traditional_mode)
        self.menu.addAction(self.traditional_mode_action)

        # 键盘映射模式（默认启用新的映射）
        self.new_keyboard_mode = self.read_keyboard_mode_setting()
        self.new_keyboard_mode_action = QAction(self.tr("⌨️ New keyboard navigation"), self)
        self.new_keyboard_mode_action.setCheckable(True)
        self.new_keyboard_mode_action.setChecked(self.new_keyboard_mode)
        self.new_keyboard_mode_action.triggered.connect(self.toggle_keyboard_mode)
        self.menu.addAction(self.new_keyboard_mode_action)

        # 关闭时自动清理搜索
        self.clear_search_on_close = self.read_clear_search_on_close_setting()
        self.clear_search_on_close_action = QAction(self.tr("🧽 Clear search when closing"), self)
        self.clear_search_on_close_action.setCheckable(True)
        self.clear_search_on_close_action.setChecked(self.clear_search_on_close)
        self.clear_search_on_close_action.triggered.connect(self.toggle_clear_search_on_close)
        self.menu.addAction(self.clear_search_on_close_action)

        self.menu.addSeparator()

        # 一键按字母排序未分组 App
        self.sort_alpha_action = QAction(self.tr("🔤 Sort ungrouped apps alphabetically"), self)
        self.sort_alpha_action.triggered.connect(self.sort_ungrouped_apps_alphabetically)
        self.menu.addAction(self.sort_alpha_action)

        # 自定义别名
        self.set_alias_action = QAction(self.tr("📝 Set custom alias (based on Finder name)"), self)
        self.set_alias_action.triggered.connect(self.prompt_set_alias)
        self.menu.addAction(self.set_alias_action)

        self.reset_alias_action = QAction(self.tr("♻️ Reset all aliases to Finder names"), self)
        self.reset_alias_action.triggered.connect(self.reset_aliases_to_finder)
        self.menu.addAction(self.reset_alias_action)

        self.menu.addSeparator()

        self.reset_all_action = QAction(self.tr("🗑 Reset All Data and Restart"), self)
        self.menu.addAction(self.reset_all_action)
        self.reset_all_action.triggered.connect(self.reset_all_data_and_restart)
        # 新增菜单项：更新指定App图标缓存
        self.update_single_app_icon_action = QAction(self.tr("❇️ Update the specified app icon cache"), self)
        self.menu.addAction(self.update_single_app_icon_action)
        self.update_single_app_icon_action.triggered.connect(self.update_single_app_icon)
        # 新增菜单项：清除所有图标缓存
        self.clear_cache_action = QAction(self.tr("🧹 Clear icon cache and refresh all apps"), self)
        self.menu.addAction(self.clear_cache_action)
        self.clear_cache_action.triggered.connect(self.clear_icon_cache_and_refresh)

        self.menu.addSeparator()

        # 新增菜单项：始终隐藏dock
        self.always_hide_dock_action = QAction(self.tr("🌀 Always hide Dock"), self)
        self.menu.addAction(self.always_hide_dock_action)
        self.always_hide_dock_action.setCheckable(True)
        self.always_hide_dock_action.triggered.connect(self.always_hide_dock)
        self._always_hide_dock_file = os.path.expanduser("~/.raspberry_hide_dock")
        self._always_hide_dock = self.read_always_hide_dock_setting()
        self.always_hide_dock_action.setChecked(self._always_hide_dock)
        # 新增 Show Dock 开关
        self.show_dock_action = QAction(self.tr("🪟 Always show Dock"), self)
        self.show_dock_action.setCheckable(True)
        self.show_dock_action.setChecked(False)  # 默认不勾选
        self.show_dock_action.triggered.connect(self.toggle_show_dock)
        self.menu.addAction(self.show_dock_action)
        self._show_dock_file = os.path.expanduser("~/.raspberry_show_dock")
        self._force_show_dock = self.read_show_dock_setting()
        if self.read_show_dock_setting() == True:
            self.show_dock_action.setChecked(True)
        else:
            self.show_dock_action.setChecked(False)
        # 保证互斥
        if self._force_show_dock and self._always_hide_dock:
            # 默认优先 show
            self._always_hide_dock = False
            self.always_hide_dock_action.setChecked(False)
            self.write_always_hide_dock_setting(False)
        # login
        self.action10 = QAction(self.tr("🛠️ Start on login"))
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
        self.action8 = QAction(self.tr("🔁 Click to restart"))
        self.menu.addAction(self.action8)
        self.action8.triggered.connect(self.restart_app)

        self.menu.addSeparator()

        self.compact_mode_action = QAction(self.tr("🗜 Compact Mode"), self)
        self.compact_mode_action.setCheckable(True)
        self.compact_mode_action.setChecked(self.compact_mode)
        self.compact_mode_action.triggered.connect(self.toggle_compact_mode)
        self.menu.addAction(self.compact_mode_action)

        self.auto_compact_mode_action = QAction(self.tr("🧠 Auto Compact Mode"), self)
        self.auto_compact_mode_action.setCheckable(True)
        self.auto_compact_mode_action.setChecked(self.read_auto_compact_mode_setting())
        self.auto_compact_mode_action.triggered.connect(self.toggle_auto_compact_mode)
        self.menu.addAction(self.auto_compact_mode_action)

        # 动画速度初始值
        self.page_anim_speed = self.read_anim_speed_setting()
        # 创建 slider 放进菜单
        slider_widget = QWidget()
        slider_layout = QHBoxLayout()
        slider_layout.setContentsMargins(10, 0, 10, 0)
        slider_label = QLabel(self.tr("Flipping speed:"))
        self.anim_speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.anim_speed_slider.setMinimum(5000)
        self.anim_speed_slider.setMaximum(10000)
        self.anim_speed_slider.setValue(self.page_anim_speed)
        self.anim_speed_slider.setTickInterval(500)
        self.anim_speed_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.anim_speed_slider.setFixedWidth(120)
        self.anim_speed_value_label = QLabel(str(self.page_anim_speed))
        self.anim_speed_value_label.setFixedWidth(50)
        slider_layout.addWidget(slider_label)
        slider_layout.addWidget(self.anim_speed_slider)
        slider_layout.addWidget(self.anim_speed_value_label)
        slider_widget.setLayout(slider_layout)

        slider_action = QWidgetAction(self)
        slider_action.setDefaultWidget(slider_widget)
        self.menu.addAction(slider_action)

        self.anim_speed_slider.valueChanged.connect(self.on_anim_speed_changed)

        self.menu.addSeparator()

        # 新增菜单项：运行 lporg
        self.run_lporg_action = QAction(self.tr("▶️ Back up Launchpad groups to Raspberry"), self)
        self.menu.addAction(self.run_lporg_action)
        self.run_lporg_action.triggered.connect(self.run_lporg)
        # 新增菜单项：备份 group
        self.backup_groups_action = QAction(self.tr("🗂️ Backup current groups"), self)
        self.menu.addAction(self.backup_groups_action)
        self.backup_groups_action.triggered.connect(self.backup_groups)
        # 新增菜单项：恢复备份
        self.restore_backup_action = QAction(self.tr("🔄 Restore backups"), self)
        self.menu.addAction(self.restore_backup_action)
        self.restore_backup_action.triggered.connect(self.restore_backup)

        # 新增 About 菜单
        self.about_menu = self.menu_bar.addMenu(self.tr("Info"))
        # 示例：添加 About 菜单项
        self.about_action = QAction(self.tr("🆕 Check for Updates"), self)
        self.win_update = WindowUpdate()
        self.about_action.triggered.connect(self.win_update.activate)
        self.about_menu.addAction(self.about_action)

        self.help_action = QAction(self.tr("ℹ️ About this app"), self)
        self.win_about = WindowAbout()
        self.help_action.triggered.connect(self.win_about.activate)
        self.about_menu.addAction(self.help_action)

        self.website_action = QAction(self.tr("🔤 Guide and Support"), self)
        self.win_permission = PermissionInfoWidget()
        self.website_action.triggered.connect(self.win_permission.show_window)
        self.about_menu.addAction(self.website_action)

        # Add Language Menu
        self.lang_menu = self.menu_bar.addMenu(self.tr("Language"))

        for code, label in [("en", "English"),
                            ("zh_CN", "简体中文"),
                            ("ja_JP", "日本語")]:
            act = QAction(label, self)
            act.setCheckable(True)
            act.triggered.connect(lambda _, c=code: self.change_language(c))
            self.lang_menu.addAction(act)

        self.clear_cache_worker = None

        # 你已有的 self.win_update = WindowUpdate()
        #self.win_update = WindowUpdate()
        # 启动自动更新线程（24h = 86400秒）
        self.update_check_worker = UpdateCheckWorker(current_version='v' + VERSION, interval_seconds=86400)
        self.update_check_worker.update_available.connect(self.on_update_available)  # 主线程槽
        self.update_check_worker.checked_ok.connect(self.on_update_checked_ok)  # 可选：日志或无感刷新
        self.update_check_worker.checked_error.connect(self.on_update_checked_error)  # 可选：日志
        self.update_check_worker.start()

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

        # 触控板滑动相关变量
        self._touchpad_swipe_active = False
        self._touchpad_swipe_accum = 0
        self._touchpad_swipe_direction = None
        self._touchpad_swipe_btns = []
        self._touchpad_swipe_anim = None
        self._is_animating = False

        self._last_screen_width = None
        self._last_screen_key = None

        self.setFocus()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 组窗口显示时，点击组窗口外部关闭组窗口
            if self.group_widget and self.group_widget.isVisible():
                if self.traditional_mode:
                    group_geo = self.group_widget.geometry()
                    if not group_geo.contains(event.position().toPoint()):
                        self.close_group_widget()
                        return
            # else:
            #     if self.traditional_mode:
            #         pos = event.position().toPoint()
            #         widget = self.childAt(pos)
            #         # 判断是否在 grid_widget 区域
            #         if widget == self.main_content.grid_widget:
            #             # 再判断是否在 grid_widget 的空白区域
            #             local_pos = self.main_content.grid_widget.mapFromParent(pos)
            #             child = self.main_content.grid_widget.childAt(local_pos)
            #             # 如果不是在任何按钮上
            #             if child is None:
            #                 self.close_main_window()
            #                 return
            #         # 如果直接点到 EmptyButton
            #         elif isinstance(widget, EmptyButton):
            #             self.close_main_window()
            #             return
            #         # 如果点到主窗口其它空白区域
            #         elif widget is None:
            #             self.close_main_window()
            #             return
            else:
                if self.traditional_mode:
                    pos = event.position().toPoint()
                    # 判断是否在 grid_widget 区域
                    grid_rect = self.main_content.grid_widget.geometry()
                    # 注意 grid_widget 的坐标是相对于 parent 的
                    grid_top_left = self.main_content.grid_widget.mapTo(self, QPoint(0, 0))
                    grid_rect_global = QRect(grid_top_left, self.main_content.grid_widget.size())
                    if not grid_rect_global.contains(pos):
                        self.close_main_window()
                        return
                    else:
                        # 在 grid_widget 区域内，再判断是否点到空白
                        local_pos = self.main_content.grid_widget.mapFromParent(pos)
                        child = self.main_content.grid_widget.childAt(local_pos)
                        if child is None or isinstance(child, EmptyButton):
                            self.close_main_window()
                            return
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
        grid_widget = self.main_content.grid_widget

        # 先移除布局项
        for i in reversed(range(grid_layout.count())):
            w = grid_layout.itemAt(i).widget()
            try:
                if w is not None:
                    w.setParent(None)
                    w.deleteLater()
            except RuntimeError:
                pass

        # 再保险：删除 grid_widget 下残留子控件，但跳过 overlay
        for w in grid_widget.findChildren(QWidget):
            if w is grid_widget:
                continue
            if w.objectName() == "insertOverlay":
                continue
            try:
                w.setParent(None)
                w.deleteLater()
            except RuntimeError:
                pass

        start = page * self.items_per_page
        end = start + self.items_per_page

        is_searching = bool(self.main_content.search_bar.text().strip())
        if is_searching:
            page_items = [('app', app) for app in apps[start:end]]
        else:
            page_items = self.main_order[start:end]

        # 常量
        MAX_COLS = 7
        ICON_W = 140
        MAX_ROWS = 5
        MIN_HGAP, MAX_HGAP = 10, ICON_W

        n = min(len(page_items), MAX_COLS * MAX_ROWS)
        used_cols = min(MAX_COLS, max(1, n))
        m = grid_layout.contentsMargins()
        top_m, bot_m = m.top(), m.bottom()
        avail_w = max(0, grid_widget.width() - m.left() - m.right())

        # 1) 基准 hgap：始终按“满一行”来计算（不会因为搜索变少而改变）
        if MAX_COLS > 1:
            possible_gap_full = max(MIN_HGAP, (avail_w - MAX_COLS * ICON_W) // (MAX_COLS - 1))
            hgap_base = min(MAX_HGAP, possible_gap_full)
        else:
            hgap_base = MIN_HGAP

        if getattr(self, 'compact_mode', False):
            hgap = hgap_base
            content_w = MAX_COLS * ICON_W + (MAX_COLS - 1) * hgap
            side_margin = max(0, (grid_widget.width() - content_w) // 2)
            grid_layout.setContentsMargins(side_margin, top_m, side_margin, bot_m)
            grid_layout.setHorizontalSpacing(hgap)
            # if is_searching and used_cols < MAX_COLS:
            #     # 搜索且不满一行：靠左对齐 + 用满行的基准间距
            #     hgap = hgap_base
            #     grid_layout.setContentsMargins(0, top_m, 0, bot_m)
            #     grid_layout.setHorizontalSpacing(hgap)
            # else:
            #     # 非搜索或满一行：内容居中
            #     hgap = hgap_base
            #     content_w = used_cols * ICON_W + (used_cols - 1) * hgap
            #     side_margin = max(0, (grid_widget.width() - content_w) // 2)
            #     grid_layout.setContentsMargins(side_margin, top_m, side_margin, bot_m)
            #     grid_layout.setHorizontalSpacing(hgap)
        else:
            # 正常模式
            m = grid_layout.contentsMargins()
            grid_layout.setContentsMargins(0, m.top(), 0, m.bottom())
            grid_layout.setHorizontalSpacing(-1)

        # 摆放按钮
        for idx, (typ, obj) in enumerate(page_items):
            row, col = divmod(idx, MAX_COLS)
            if row >= MAX_ROWS:
                break
            if typ == 'group':
                btn = GroupButton(obj, self.main_content.grid_widget, main_window=self)
            else:
                btn = AppButton(obj, self.main_content.grid_widget, main_window=self)
            grid_layout.addWidget(btn, row, col)

        # 补齐空白按钮
        total = len(page_items)
        for idx in range(total, MAX_COLS * MAX_ROWS):
            row, col = divmod(idx, MAX_COLS)
            if row >= MAX_ROWS:
                break
            btn = EmptyButton(main_window=self, parent=self.main_content.grid_widget)
            grid_layout.addWidget(btn, row, col)

        # 指示器数量
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
        # 先从所有分组移除该 app，防止重复
        for g in self.groups:
            if app_btn.app_info in g['apps']:
                g['apps'].remove(app_btn.app_info)
                g['icon'] = create_group_icon(g['apps'])
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
        is_searching = bool(self.main_content.search_bar.text().strip())
        if is_searching:
            self.main_content.search_bar.setText('')

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
        # 如果组窗口还开着，刷新组窗口
        if self.group_widget:
            # 只刷新当前显示的组
            self.group_widget.display_apps(self.group_widget.group['apps'], self.group_widget.current_page)

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
        # 新增：首次初始化 main_order
        if not self.main_order:
            # 先加所有分组
            self.main_order = [('group', g) for g in self.groups]
            # 再加所有未分组 app
            self.main_order += [('app', a) for a in self.apps if not any(a in g['apps'] for g in self.groups)]
        if new_apps:
            self.apps.extend(new_apps)
            self.apps = self.dedup_apps(self.apps)
            self.apply_display_aliases(refresh=False)
            # 新增：自动加到 main_order 顺序末尾
            for a in new_apps:
                # 只加未分组的 app
                if not any(a in g['apps'] for g in self.groups):
                    already_in_main = any((typ == 'app' and obj['path'] == a['path']) for typ, obj in self.main_order)
                    if not already_in_main:
                        self.main_order.append(('app', a))
                    # 新增：加入 filtered_apps
                    already_in_filtered = any(a['path'] == fa['path'] for fa in self.filtered_apps)
                    if not already_in_filtered:
                        self.filtered_apps.append(a)
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
            # self.save_current_order()
        save_app_order([a['path'] for a in self.filtered_apps])  # save again
        self.save_current_order()
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
        if getattr(self, "new_keyboard_mode", True):
            return self._handle_key_event_new_mode(event)
        if event.key() == Qt.Key.Key_Escape:
            self.close_main_window()
            return True
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

    def _handle_key_event_new_mode(self, event):
        key = event.key()
        modifiers = event.modifiers()
        swap_mod = modifiers & (Qt.KeyboardModifier.ControlModifier |
                                Qt.KeyboardModifier.AltModifier |
                                Qt.KeyboardModifier.MetaModifier)
        shift_mod = modifiers & Qt.KeyboardModifier.ShiftModifier

        if key == Qt.Key.Key_Escape:
            self.close_main_window()
            return True
        if swap_mod and key == Qt.Key.Key_Left:
            self.move_focused_btn_left()
            return True
        if swap_mod and key == Qt.Key.Key_Right:
            self.move_focused_btn_right()
            return True
        if shift_mod and key == Qt.Key.Key_Left:
            self.goto_page(max(self.current_page - 1, 0))
            return True
        if shift_mod and key == Qt.Key.Key_Right:
            self.goto_page(min(self.current_page + 1, self.total_pages() - 1))
            return True
        if key == Qt.Key.Key_Left:
            self.focus_prev_btn()
            return True
        if key == Qt.Key.Key_Right:
            self.focus_next_btn()
            return True
        if key == Qt.Key.Key_Up:
            self.focus_up_btn()
            return True
        if key == Qt.Key.Key_Down:
            self.focus_down_btn()
            return True
        if key == Qt.Key.Key_Space:
            if shift_mod:
                self.focus_prev_btn()
            else:
                self.focus_next_btn()
            return True
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.focused_btn is None:
                return False
            if shift_mod:
                pos = self.focused_btn.rect().center()
                self.focused_btn.show_context_menu(pos)
            else:
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

        # 如果仍在其他组，就不放回主界面
        in_other_group = any(app_info in g['apps'] for g in self.groups if g is not group)

        if not in_other_group:
            # 确保主界面的“未分组软件列表”里有它（追加到末尾）
            if app_info not in self.filtered_apps:
                self.filtered_apps.append(app_info)

            # 先从 main_order 移除该 app（避免重复）
            self.main_order = [
                (typ, obj) for (typ, obj) in self.main_order
                if not (typ == 'app' and obj == app_info)
            ]

            # 计算插入点：放到“所有 group 之后、所有 app 的末尾”
            last_group_idx = -1
            last_app_idx = -1
            for idx, (typ, obj) in enumerate(self.main_order):
                if typ == 'group':
                    last_group_idx = idx
                elif typ == 'app':
                    last_app_idx = idx

            if last_app_idx < last_group_idx:
                # 没有 app 的情况，让 last_app_idx 退回到最后一个 group
                last_app_idx = last_group_idx

            insert_idx = last_app_idx + 1
            self.main_order.insert(insert_idx, ('app', app_info))

            self.save_current_order()

        # 刷新视图
        self.display_apps(self.filtered_apps, self.current_page)

        # 如果组窗口还开着，刷新组窗口
        if self.group_widget and self.group_widget.group is group:
            self.group_widget.display_apps(group['apps'], self.group_widget.current_page)

    def clear_icon_cache_and_refresh(self):
        if self.clear_cache_worker and self.clear_cache_worker.isRunning():
            #QMessageBox.information(self, "请稍候", "正在清除缓存和刷新应用，请勿重复操作。")
            msg = CustomMessageBox(self.tr("Clearing cache and refreshing the app, please do not repeat the operation."), parent=self, buttons=(self.tr("OK"),))
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
            msg = CustomMessageBox(error_msg, parent=self, buttons=(self.tr("OK"),))
            msg.exec()
            return
        self.apps = apps
        self.groups = groups
        self.filtered_apps = filtered_apps
        self.current_page = 0
        self.display_apps(self.filtered_apps, self.current_page)
        #QMessageBox.information(self, "完成", "图标缓存已清除，应用已刷新。")
        msg = RestartMessageBox(self.tr("Icon cache cleared, app refreshed.\nRaspberry will restart."), parent=self, buttons=(self.tr("OK"), self.tr("Later")))
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
        rendered = self.adapt_to_screen()  # 每次 show 都刷新几何
        if not rendered:
            self.display_apps(self.filtered_apps, self.current_page)
        self.prepare_icons_for_animation()
        if getattr(self, '_force_show_dock', False):
            self.show_dock()
        else:
            self.hide_dock()
        QTimer.singleShot(10, self.animate_icons_in)  # 动画延迟触发
        QTimer.singleShot(2000, self.start_background_scan)  # 新增：主UI展示后2秒再扫描一次

    def close_main_window(self):
        if getattr(self, "clear_search_on_close", False) and self.main_content.search_bar.text().strip():
            # 清除搜索并恢复默认布局，避免下次打开仍停留在搜索结果
            self.main_content.search_bar.setText('')
        if not self.isVisible():
            return
        # 防止重复动画
        if hasattr(self, "_fade_anim") and self._fade_anim is not None and self._fade_anim.state() == QPropertyAnimation.State.Running:
            return
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(350)  # 动画时长（毫秒）
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self._after_fade_out)
        self._fade_anim.start()

    def _after_fade_out(self):
        self.hide()
        self.setWindowOpacity(1.0)  # 恢复透明度，便于下次show
        self._fade_anim = None

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
                        msg = CustomMessageBox(self.tr(f"Failed to parse Info.plist: %n").replace('%n', str(e)), parent=self, buttons=(self.tr("OK"),))
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
                        msg = CustomMessageBox(self.tr(f"Failed to parse iTunesMetadata.plist: %n").replace('%n', str(e)), parent=self, buttons=(self.tr("OK"),))
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
                    msg = CustomMessageBox(self.tr("Unable to retrieve the icon for this app."), parent=self, buttons=(self.tr("OK"),))
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
                    msg = CustomMessageBox(self.tr(f"The icon cache for %n has been updated.").replace('%n', name), parent=self, buttons=(self.tr("OK"),))
                    msg.exec()
                    #QMessageBox.information(self, "完成", f"{name} 的图标缓存已更新。")
                else:
                    msg = CustomMessageBox(self.tr(f"The icon of %n has been cached, but the app is not in the main interface list.").replace('%n', name), parent=self, buttons=(self.tr("OK"),))
                    msg.exec()
                    #QMessageBox.information(self, "提示", f"已缓存 {name} 的图标，但该App不在主界面列表中。")

    def always_hide_dock(self):
        self._always_hide_dock = self.always_hide_dock_action.isChecked()
        self.write_always_hide_dock_setting(self._always_hide_dock)
        if self._always_hide_dock:
            # 互斥：取消 always show
            self._force_show_dock = False
            self.show_dock_action.setChecked(False)
            self.write_show_dock_setting(False)

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
        if getattr(self, '_force_show_dock', False):
            return  # 如果强制显示 Dock，则不执行
        try:
            toggle_dock_script = '''
                tell application "System Events" to set the autohide of dock preferences to true
            '''
            subprocess.run(["osascript", "-e", toggle_dock_script], env=clean_env_for_child())
        except Exception as e:
            pass

    def show_dock(self):
        # if getattr(self, '_force_show_dock', False):
        #     return  # 如果强制显示 Dock，则不执行
        try:
            toggle_dock_script = '''
                tell application "System Events" to set the autohide of dock preferences to false
            '''
            subprocess.run(["osascript", "-e", toggle_dock_script], env=clean_env_for_child())
        except Exception as e:
            pass

    def wheelEvent(self, event):
        # 动画期间禁翻，避免状态冲突
        if getattr(self, "_is_animating", False):
            event.accept()
            return

        pixel_delta = event.pixelDelta()
        angle_delta = event.angleDelta()
        dx = pixel_delta.x() if pixel_delta.x() != 0 else int(angle_delta.x() / 2)

        if dx != 0:
            # 初始化触控板滑动会话
            if not getattr(self, "_touchpad_swipe_active", False):
                self._touchpad_swipe_active = True
                self._touchpad_swipe_accum = 0
                self._touchpad_swipe_btns = []
                grid_layout = self.main_content.grid_layout
                for i in range(grid_layout.count()):
                    w = grid_layout.itemAt(i).widget()
                    if isinstance(w, (AppButton, GroupButton)):
                        self._touchpad_swipe_btns.append(w)
                for btn in self._touchpad_swipe_btns:
                    if sip.isdeleted(btn):
                        continue
                    btn._orig_pos = btn.pos()

            # 累计位移
            self._touchpad_swipe_accum += dx

            page_w = self.main_content.grid_widget.width()
            threshold = page_w // 2

            # 实时越阈值：立刻触发（不等松手）
            if abs(self._touchpad_swipe_accum) >= threshold:
                direction = "left" if self._touchpad_swipe_accum < 0 else "right"
                is_first_page = (self.current_page == 0)
                is_last_page = (self.current_page == self.total_pages() - 1)

                # 首页右滑 / 末页左滑：四分之一页回弹
                if (direction == "right" and is_first_page) or (direction == "left" and is_last_page):
                    group = QParallelAnimationGroup(self)
                    for btn in self._touchpad_swipe_btns:
                        if sip.isdeleted(btn):
                            continue
                        orig = getattr(btn, "_orig_pos", btn.pos())
                        anim = QPropertyAnimation(btn, b"pos", self)
                        anim.setDuration(180)
                        anim.setStartValue(btn.pos())
                        anim.setEndValue(orig)
                        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                        group.addAnimation(anim)

                    def after_bounce():
                        # 彻底复位滑动状态
                        self._touchpad_swipe_active = False
                        self._touchpad_swipe_accum = 0
                        self._touchpad_swipe_direction = None
                        self._touchpad_swipe_btns = []

                    # 停掉迟到的“松手计时器”
                    if hasattr(self, "_touchpad_swipe_timer") and self._touchpad_swipe_timer.isActive():
                        self._touchpad_swipe_timer.stop()

                    group.finished.connect(after_bounce)
                    group.start()
                    self._touchpad_swipe_anim = group
                    event.accept()
                    return

                # 正常翻页（每次只翻一页）
                if direction == "left":
                    target_page = min(self.current_page + 1, self.total_pages() - 1)
                    remaining = -page_w - self._touchpad_swipe_accum
                else:
                    target_page = max(self.current_page - 1, 0)
                    remaining = page_w - self._touchpad_swipe_accum

                # 若有旧动画在跑，停掉，避免僵尸动画阻塞 finished
                try:
                    if hasattr(self, "anim") and self.anim is not None:
                        self.anim.stop()
                except Exception:
                    pass

                self._is_animating = True

                group = QParallelAnimationGroup(self)
                for btn in self._touchpad_swipe_btns:
                    if sip.isdeleted(btn):
                        continue
                    anim = QPropertyAnimation(btn, b"pos", self)
                    # 时长上限，避免异常起点导致的超长动画
                    duration = min(240, 160 + int(min(abs(remaining), page_w) * 0.25))
                    anim.setDuration(duration)
                    anim.setStartValue(btn.pos())
                    anim.setEndValue(btn.pos() + QPoint(remaining, 0))
                    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                    group.addAnimation(anim)

                def after_swipe_out():
                    # 核心：直接切页，不再进 goto_page → animate_page_transition 的第二段过场
                    self.goto_page_immediate(target_page)

                    # 彻底清理状态，确保下一次滑动正常
                    self._is_animating = False
                    self._touchpad_swipe_active = False
                    self._touchpad_swipe_accum = 0
                    self._touchpad_swipe_direction = None
                    self._touchpad_swipe_btns = []

                # 停掉迟到的“松手计时器”，防止回调叠加
                if hasattr(self, "_touchpad_swipe_timer") and self._touchpad_swipe_timer.isActive():
                    self._touchpad_swipe_timer.stop()

                group.finished.connect(after_swipe_out)
                group.start()
                self._touchpad_swipe_anim = group

                event.accept()
                return

            # 未越阈值：跟手移动
            for btn in self._touchpad_swipe_btns:
                if sip.isdeleted(btn):
                    continue
                orig = getattr(btn, "_orig_pos", btn.pos())
                btn.move(orig + QPoint(self._touchpad_swipe_accum, 0))

            self._touchpad_swipe_direction = "left" if self._touchpad_swipe_accum < 0 else "right"

            # “松手回弹”的兜底计时器（若中断输入，仍能回弹）
            if hasattr(self, "_touchpad_swipe_timer") and self._touchpad_swipe_timer.isActive():
                self._touchpad_swipe_timer.stop()
            else:
                self._touchpad_swipe_timer = QTimer(self)
                self._touchpad_swipe_timer.setSingleShot(True)
                self._touchpad_swipe_timer.timeout.connect(self._on_touchpad_swipe_release)
            self._touchpad_swipe_timer.start(300)

            event.accept()
            return

        # 正在触控板滑动会话时，忽略垂直滚动，避免干扰
        if getattr(self, "_touchpad_swipe_active", False):
            event.accept()
            return

        # 传统滚轮垂直翻页保留
        dy = angle_delta.y()
        if dy > 0:
            self.goto_page(max(self.current_page - 1, 0))
        elif dy < 0:
            self.goto_page(min(self.current_page + 1, self.total_pages() - 1))
        event.accept()

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
        subprocess.Popen(['osascript', '-e', applescript], env=clean_env_for_child())

    def find_matching_paths(self, item_name, all_paths):
        matches = []
        item_lower = _normalize_display_name(item_name).lower()
        display_map = getattr(self, "display_name_map", load_display_name_map())
        for path in all_paths:
            basename = os.path.basename(path)
            display_name = _normalize_display_name(display_map.get(path) or get_finder_display_name(path))
            if display_name.lower() == item_lower:
                matches.append(path)
                continue
            if basename.endswith('.app'):
                app_main_name = basename[:-4].lower()
                if app_main_name == item_lower:
                    matches.append(path)
        return matches

    def yml_to_json(self, yml_data, match_json_data):
        yml_obj = yaml.safe_load(yml_data)
        apps_pages = yml_obj['apps']['pages']

        all_paths = json.loads(match_json_data)

        result = []
        # 修改：遍历所有 page
        for page in apps_pages:
            for folder_entry in page['items']:
                # 只处理有 'folder' 键的字典
                if isinstance(folder_entry, dict) and 'folder' in folder_entry:
                    folder_name = folder_entry['folder']
                    app_set = set()
                    for subpage in folder_entry.get('pages', []):
                        for item in subpage.get('items', []):
                            matches = self.find_matching_paths(item, all_paths)
                            app_set.update(matches)
                    result.append({
                        "name": folder_name,
                        "apps": sorted(app_set)
                    })
                # 如果不是 folder 字典，直接跳过
        return result

    def reload_groups(self):
        self.groups = load_groups(self.apps)
        self.group_dict = {g['name']: g for g in self.groups}

        saved = load_main_order()
        seen = set()

        saved_groups = []  # [('group', g), ...]
        saved_apps = []  # [('app', a), ...]

        # 先按已保存顺序分类装桶（仅装得上的）
        for oid in saved:
            if oid in self.group_dict and oid not in seen:
                saved_groups.append(('group', self.group_dict[oid]))
                seen.add(oid)
            elif oid in self.app_dict and oid not in seen:
                a = self.app_dict[oid]
                # 只加入“未分组 app”
                if not any(a in g['apps'] for g in self.groups):
                    saved_apps.append(('app', a))
                    seen.add(oid)

        # 再补全缺失的组到组桶
        in_groups_bucket = {obj['name'] for typ, obj in saved_groups if typ == 'group'}
        for g in self.groups:
            if g['name'] not in in_groups_bucket:
                saved_groups.append(('group', g))

        # 再补全缺失的“未分组 app”到 app 桶
        in_apps_bucket = {obj['path'] for typ, obj in saved_apps if typ == 'app'}
        for a in self.apps:
            if (a['path'] not in in_apps_bucket) and (not any(a in g['apps'] for g in self.groups)):
                saved_apps.append(('app', a))

        # 最终“组在前，app 在后”
        self.main_order = saved_groups + saved_apps

        # 只保留未分组 app 用于主网格
        self.filtered_apps = [a for a in self.apps if not any(a in g['apps'] for g in self.groups)]
        self.current_page = 0
        self.display_apps(self.filtered_apps, self.current_page)
        self.save_current_order()

    def run_lporg(self):
        lporg_filename = 'lporg'
        lporg_path = BasePath + lporg_filename
        if not os.path.exists(lporg_path):
            msg = CustomMessageBox(self.tr(f"lporg not found at %n").replace('%n', lporg_path), parent=self, buttons=(self.tr("OK"),))
            msg.exec()
            return
        # 确保 display/alias 映射最新
        self.apply_display_aliases(refresh=False)
        base_dir_str = str(Path.home()) + "/Library/Application\\\ Support/com.ryanthehito.raspberry/Resources/lporg"
        lporg_cmd = base_dir_str + ' save'
        applescript = f'do shell script "{lporg_cmd}"'
        #print(applescript)
        try:
            result = subprocess.run(
                ["osascript", "-e", applescript],
                capture_output=True, text=True, env=clean_env_for_child()
            )
            output = result.stdout.strip()
            if result.returncode == 0:
                lporg_yml_dir = Path.home() / "Library/Application Support" / 'lporg' / 'config.yml'
                with open(lporg_yml_dir, "r", encoding="utf-8") as f:
                    yml_data = f.read()
                with open(APP_PATHS_FILE, "r", encoding="utf-8") as f:
                    match_json_data = f.read()
                result = self.yml_to_json(yml_data, match_json_data)
                with open(GROUPS_FILE, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                self.reload_groups()
                self.save_current_order()
                if output:
                    dlg = RestartMessageBox(self.tr(f"Executed successfully.\nOutput:\n%n.\nRaspberry will restart.").replace('%n', output), parent=self,
                                           buttons=(self.tr("OK"), self.tr("Later")))
                    dlg.exec()
                    # if dlg.exec() == 0:  # 用户点了 Restart
                    #     QTimer.singleShot(0, self.restart_app)
                else:
                    dlg = RestartMessageBox(self.tr("Executed successfully.\nRaspberry will restart."), parent=self,
                                           buttons=(self.tr("OK"), self.tr("Later")))
                    dlg.exec()
                    # if dlg.exec() == 0:  # 用户点了 Restart
                    #     QTimer.singleShot(0, self.restart_app)
            else:
                try:  # 尝试直接找对应的文件，因为之前可能已经备份过
                    lporg_yml_dir = Path.home() / "Library/Application Support" / 'lporg' / 'config.yml'
                    with open(lporg_yml_dir, "r", encoding="utf-8") as f:
                        yml_data = f.read()
                    with open(APP_PATHS_FILE, "r", encoding="utf-8") as f:
                        match_json_data = f.read()
                    result = self.yml_to_json(yml_data, match_json_data)
                    with open(GROUPS_FILE, "w", encoding="utf-8") as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    self.reload_groups()
                    dlg = RestartMessageBox(self.tr("Executed successfully.\nRaspberry will restart."), parent=self,
                                            buttons=(self.tr("OK"), self.tr("Later")))
                    dlg.exec()
                except Exception as e:  # 如果还是找不到，再尝试恢复为苹果默认格式
                    try:
                        lporg_yml_dir = Path.home() / "Library/Application Support" / 'com.ryanthehito.raspberry' / 'Resources' / 'config.yml'
                        with open(lporg_yml_dir, "r", encoding="utf-8") as f:
                            yml_data = f.read()
                        with open(APP_PATHS_FILE, "r", encoding="utf-8") as f:
                            match_json_data = f.read()
                        result = self.yml_to_json(yml_data, match_json_data)
                        with open(GROUPS_FILE, "w", encoding="utf-8") as f:
                            json.dump(result, f, ensure_ascii=False, indent=2)
                        self.reload_groups()
                        dlg = RestartMessageBox(self.tr("Executed successfully. (Back to default mode)\nRaspberry will restart."),
                                                parent=self,
                                                buttons=(self.tr("OK"), self.tr("Later")))
                        dlg.exec()
                    except Exception as e:
                        msg = CustomMessageBox(self.tr(f"Execution failed.\nOutput:\n%n").replace('%n', output), parent=self, buttons=(self.tr("OK"),))
                        msg.exec()
        except Exception as e:
            try:  # 尝试直接找对应的文件，因为之前可能已经备份过
                lporg_yml_dir = Path.home() / "Library/Application Support" / 'lporg' / 'config.yml'
                with open(lporg_yml_dir, "r", encoding="utf-8") as f:
                    yml_data = f.read()
                with open(APP_PATHS_FILE, "r", encoding="utf-8") as f:
                    match_json_data = f.read()
                result = self.yml_to_json(yml_data, match_json_data)
                with open(GROUPS_FILE, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                self.reload_groups()
                dlg = RestartMessageBox(self.tr("Executed successfully.\nRaspberry will restart."), parent=self,
                                        buttons=(self.tr("OK"), self.tr("Later")))
                dlg.exec()
            except Exception as e:  # 如果还是找不到，再尝试恢复为苹果默认格式
                try:
                    lporg_yml_dir = Path.home() / "Library/Application Support" / 'com.ryanthehito.raspberry' / 'Resources' / 'config.yml'
                    with open(lporg_yml_dir, "r", encoding="utf-8") as f:
                        yml_data = f.read()
                    with open(APP_PATHS_FILE, "r", encoding="utf-8") as f:
                        match_json_data = f.read()
                    result = self.yml_to_json(yml_data, match_json_data)
                    with open(GROUPS_FILE, "w", encoding="utf-8") as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    self.reload_groups()
                    dlg = RestartMessageBox(
                        self.tr("Executed successfully. (Back to default mode)\nRaspberry will restart."),
                        parent=self,
                        buttons=(self.tr("OK"), self.tr("Later")))
                    dlg.exec()
                except Exception as e:
                    msg = CustomMessageBox(self.tr(f"Execution failed.\nOutput:\n%n").replace('%n', output),
                                           parent=self, buttons=(self.tr("OK"),))
                    msg.exec()

    def animate_page_transition(self, next_page_items, direction="left"):
        # 动画重入保护
        if getattr(self, "_is_animating", False):
            return
        self._is_animating = True

        grid_layout = self.main_content.grid_layout
        old_btns = []
        for i in range(grid_layout.count()):
            w = grid_layout.itemAt(i).widget()
            if isinstance(w, (AppButton, GroupButton)):
                old_btns.append(w)

        if not next_page_items:
            for btn in old_btns:
                safe_delete_widget(btn)
            self._is_animating = False
            return

        screen_width = self.width()
        speed = self.page_anim_speed  # slider 可调速度
        anim_group_out = QParallelAnimationGroup(self)

        for btn in old_btns:
            if sip.isdeleted(btn):
                continue
            start_pos = btn.pos()
            if direction == "left":
                end_pos = QPoint(-btn.width(), start_pos.y())
                distance = start_pos.x() + btn.width()
            else:
                end_pos = QPoint(screen_width + btn.width(), start_pos.y())
                distance = screen_width - start_pos.x() + btn.width()
            duration = max(80, int(distance / max(1000, speed) * 1000))
            duration = min(duration, 350)  # 关键：强制上限，避免“超长等待”
            anim = QPropertyAnimation(btn, b"pos", self)
            anim.setDuration(duration)
            anim.setStartValue(start_pos)
            anim.setEndValue(end_pos)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim_group_out.addAnimation(anim)

        def cleanup_old_btns():
            for btn in old_btns:
                safe_delete_widget(btn)
            # 动画结束后再统一刷新本页（next_page_items: [('group'|'app', obj), ...]）
            self.display_apps([obj for typ, obj in next_page_items if typ == 'app'], self.current_page)
            self._is_animating = False

        anim_group_out.finished.connect(cleanup_old_btns)
        anim_group_out.start()
        self.anim = anim_group_out  # 防止被回收

    def backup_groups(self):
        # 备份目录
        backup_base = Path.home() / "Library/Application Support/com.ryanthehito.raspberry/RaspberryAppPath/Backups"
        backup_base.mkdir(parents=True, exist_ok=True)
        # 时间戳文件夹
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = backup_base / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)

        # 要备份的文件和文件夹
        files = [
            Path(GROUPS_FILE),
            Path(APP_ORDER_FILE),
            Path(APP_PATHS_FILE),
            Path(MAIN_ORDER_FILE),
        ]
        icon_cache_src = Path(ICON_CACHE_DIR)
        icon_cache_dst = backup_dir / ".launchpad_icon_cache"

        # 复制文件
        for f in files:
            if f.exists():
                shutil.copy2(f, backup_dir / f.name)
        # 复制文件夹
        if icon_cache_src.exists():
            shutil.copytree(icon_cache_src, icon_cache_dst, dirs_exist_ok=True)

        # 提示
        msg = CustomMessageBox(self.tr("Backup completed!"), parent=self, buttons=(self.tr("OK"),))
        msg.exec()

    def restore_backup(self):
        # 选择备份文件夹
        backup_base = str(
            Path.home() / "Library/Application Support/com.ryanthehito.raspberry/RaspberryAppPath/Backups")
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setDirectory(backup_base)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dialog.setWindowTitle(self.tr("Select a backup folder to restore"))
        if dialog.exec():
            selected_dirs = dialog.selectedFiles()
            if selected_dirs:
                backup_dir = Path(selected_dirs[0])
                # 检查文件
                files = [
                    ".launchpad_groups.json",
                    ".launchpad_app_order.json",
                    ".launchpad_app_paths.json",
                    ".launchpad_main_order.json",
                    ".raspberry_display_names.json",
                    ".raspberry_alias_names.json",
                ]
                icon_cache_src = backup_dir / ".launchpad_icon_cache"
                required = files[:4]  # 前四个是必需
                missing_required = [f for f in required if not (backup_dir / f).exists()]
                if missing_required:
                    msg = CustomMessageBox(self.tr(f"Missing files: %n").replace('%n', ', '.join(missing_required)), parent=self, buttons=(self.tr("OK"),))
                    msg.exec()
                    return
                # 覆盖文件
                for f in files:
                    src = backup_dir / f
                    if src.exists():
                        shutil.copy2(src, Path.home() / f"{f}")
                # 覆盖 icon cache
                icon_cache_dst = Path(ICON_CACHE_DIR)
                if icon_cache_src.exists():
                    # 先删除原有
                    if icon_cache_dst.exists():
                        shutil.rmtree(icon_cache_dst)
                    shutil.copytree(icon_cache_src, icon_cache_dst, dirs_exist_ok=True)
                # 重新加载内存状态，避免立刻写回覆盖
                self.apps = get_applications()
                self.groups = load_groups(self.apps)
                self.app_dict = {a['path']: a for a in self.apps}
                self.group_dict = {g['name']: g for g in self.groups}
                saved_main = load_main_order()
                self.main_order = []
                for oid in saved_main:
                    if oid in self.group_dict:
                        self.main_order.append(('group', self.group_dict[oid]))
                    elif oid in self.app_dict:
                        self.main_order.append(('app', self.app_dict[oid]))
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
                self.apply_display_aliases(refresh=False)
                self.current_page = 0
                self.display_apps(self.filtered_apps, self.current_page)
                dlg = RestartMessageBox(self.tr("Executed successfully.\nRaspberry will restart."), parent=self,
                                        buttons=(self.tr("OK"), self.tr("Later")))
                if dlg.exec() == 0:
                    self.restart_app()

    def adapt_to_screen(self):
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        geo: QRect = screen.geometry()
        screen_width = geo.width()
        screen_height = geo.height()
        screen_key = f"{screen.name() or 'Unknown'}|{screen_width}x{screen_height}"

        geometry_changed = geo != self.geometry()
        key_changed = (self._last_screen_key != screen_key)

        # 命中缓存时：仅同步几何（如有需要），并通过 check_and_apply_compact_mode 用缓存直接刷新一次
        cache = load_display_profile_cache()
        if screen_key in cache:
            if geometry_changed:
                self.setGeometry(geo)
                self.main_content.setGeometry(self.rect())
                if self.group_widget and self.group_widget.isVisible():
                    gw = self.group_widget
                    gw.move((self.width() - gw.width()) // 2,
                            (self.height() - gw.height()) // 2)
            self._last_screen_width = screen_width
            self._last_screen_key = screen_key
            rendered = self.check_and_apply_compact_mode()  # 利用缓存直接应用/刷新
            return bool(rendered)

        if geometry_changed:
            self.setGeometry(geo)
            self.main_content.setGeometry(self.rect())
            if self.group_widget and self.group_widget.isVisible():
                gw = self.group_widget
                gw.move((self.width() - gw.width()) // 2,
                        (self.height() - gw.height()) // 2)
        # 屏幕信息发生变化（包含分辨率或屏幕名称）时才重新计算/应用
        already_rendered = False
        if key_changed or self._last_screen_width != screen_width or geometry_changed:
            self._last_screen_width = screen_width
            self._last_screen_key = screen_key
            already_rendered = self.check_and_apply_compact_mode()
        if geometry_changed and not already_rendered:
            self.display_apps(self.filtered_apps, self.current_page)
        return bool(already_rendered)

    def change_language(self, code):
        # 1) 记录到配置
        cfg_file = Path.home() / ".raspberry_lang"
        cfg_file.write_text(code, encoding="utf-8")
        # 2) 提示用户重启
        msg = RestartMessageBox(self.tr("Language will apply after restart."),
                               parent=self, buttons=(self.tr("OK"),))
        msg.exec()

    def read_traditional_mode(self):
        if not os.path.exists(self.TRADITIONAL_MODE_FILE):
            # 默认开启
            with open(self.TRADITIONAL_MODE_FILE, "w", encoding="utf-8") as f:
                f.write("1")
            return True
        try:
            with open(self.TRADITIONAL_MODE_FILE, "r", encoding="utf-8") as f:
                val = f.read().strip()
                return val == "1"
        except Exception:
            return True  # 读取失败也默认开启

    def write_traditional_mode(self, enabled: bool):
        try:
            with open(self.TRADITIONAL_MODE_FILE, "w", encoding="utf-8") as f:
                f.write("1" if enabled else "0")
        except Exception:
            pass

    def toggle_traditional_mode(self):
        self.traditional_mode = self.traditional_mode_action.isChecked()
        self.write_traditional_mode(self.traditional_mode)

    def reset_all_data_and_restart(self):
        # 需要删除的文件列表
        files_to_delete = [
            os.path.expanduser("~/.launchpad_main_order.json"),
            os.path.expanduser("~/.launchpad_groups.json"),
            os.path.expanduser("~/.launchpad_app_paths.json"),
            os.path.expanduser("~/.launchpad_app_order.json"),
        ]
        for f in files_to_delete:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception as e:
                print(f"Failed to delete {f}: {e}")
        # 重启应用
        self.restart_app()

    def toggle_show_dock(self):
        self._force_show_dock = self.show_dock_action.isChecked()
        self.write_show_dock_setting(self._force_show_dock)
        if self._force_show_dock:
            # 互斥：取消 always hide
            self._always_hide_dock = False
            self.always_hide_dock_action.setChecked(False)
            self.write_always_hide_dock_setting(False)
            self.show_dock()
        else:
            if self.isVisible():
                self.hide_dock()

    def read_show_dock_setting(self):
        try:
            if os.path.exists(self._show_dock_file):
                with open(self._show_dock_file, "r", encoding="utf-8") as f:
                    val = f.read().strip()
                    return val == "1"
        except Exception:
            pass
        return False  # 默认不勾选

    def write_show_dock_setting(self, enabled: bool):
        try:
            with open(self._show_dock_file, "w", encoding="utf-8") as f:
                f.write("1" if enabled else "0")
        except Exception:
            pass

    def read_always_hide_dock_setting(self):
        try:
            if os.path.exists(self._always_hide_dock_file):
                with open(self._always_hide_dock_file, "r", encoding="utf-8") as f:
                    val = f.read().strip()
                    return val == "1"
        except Exception:
            pass
        return False  # 默认不勾选

    def write_always_hide_dock_setting(self, enabled: bool):
        try:
            with open(self._always_hide_dock_file, "w", encoding="utf-8") as f:
                f.write("1" if enabled else "0")
        except Exception:
            pass

    @pyqtSlot(str)
    def on_update_available(self, latest: str):
        # 这里只在主线程里创建窗口或弹窗
        # 你可以复用已有的 WindowUpdate 或者弹一个你的自定义对话框
        # 例：用你已有的 RestartMessageBox/CustomMessageBox 风格
        msg = CustomMessageBox(
            self.tr(f"New version %n is available. Open release note page?").replace('%n', latest),
            parent=self,
            buttons=(self.tr("Open"), self.tr("Later"))
        )
        res = msg.exec()
        if res == 0:
            webbrowser.open('https://github.com/Ryan-the-hito/Raspberry/releases')

        # 或者你也可以这样：仅在有更新时展示现有的 WindowUpdate 小窗
        #self.win_update.show()  # 它会 show() 并 checkupdate()，但建议只 show，然后把 latest 显示出来

    @pyqtSlot(str)
    def on_update_checked_ok(self, latest: str):
        # 可选：比如在日志里记录或更新某个状态标签（主线程里的标签）
        #print(f"Checked latest: {latest}")
        pass

    @pyqtSlot(str)
    def on_update_checked_error(self, err: str):
        # 可选：记录错误，不弹框打扰用户
        #print(f"Check update error: {err}")
        pass

    def _clear_main_grid(self):
        grid_layout = self.main_content.grid_layout
        # 清布局里的
        for i in reversed(range(grid_layout.count())):
            w = grid_layout.itemAt(i).widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        # 保险：再清 grid_widget 的子控件
        for w in self.main_content.grid_widget.findChildren(QWidget):
            if w is self.main_content.grid_widget:
                continue
            w.setParent(None)
            w.deleteLater()

    def apply_display_aliases(self, refresh: bool = True):
        """
        Refresh app names using Finder display name + custom aliases.
        """
        self.display_name_map = load_display_name_map()
        self.alias_name_map = load_alias_name_map()
        display_dirty = False
        alias_dirty = False
        seen = set()
        for app in self.apps:
            path = app['path']
            seen.add(path)
            display_name = _normalize_display_name(self.display_name_map.get(path) or get_finder_display_name(path))
            if _normalize_display_name(self.display_name_map.get(path, "")) != display_name:
                display_dirty = True
                self.display_name_map[path] = display_name
            alias_raw = self.alias_name_map.get(path)
            alias = _normalize_display_name(alias_raw) if alias_raw else display_name
            if alias_raw and alias != alias_raw:
                alias_dirty = True
                self.alias_name_map[path] = alias
            app['display_name'] = display_name
            app['name'] = alias
        for stale in list(self.display_name_map.keys()):
            if stale not in seen:
                display_dirty = True
                self.display_name_map.pop(stale, None)
        for stale in list(self.alias_name_map.keys()):
            if stale not in seen:
                alias_dirty = True
                self.alias_name_map.pop(stale, None)
        if display_dirty:
            save_display_name_map(self.display_name_map)
        if alias_dirty:
            save_alias_name_map(self.alias_name_map)
        if refresh:
            self.filtered_apps = [a for a in self.apps if not any(a in g['apps'] for g in self.groups)]
            self.display_apps(self.filtered_apps, self.current_page)
            self.save_current_order()

    def sort_ungrouped_apps_alphabetically(self):
        """
        Sort ungrouped apps alphabetically (one-time action).
        """
        ungrouped_apps = [a for a in self.apps if not any(a in g['apps'] for g in self.groups)]
        if not ungrouped_apps:
            return
        sorted_apps = sorted(ungrouped_apps, key=lambda a: a.get('name', '').lower())
        # 保留当前 group 顺序，仅替换 app 段
        groups_in_order = [obj for typ, obj in self.main_order if typ == 'group']
        self.main_order = [('group', g) for g in groups_in_order] + [('app', a) for a in sorted_apps]
        self.filtered_apps = sorted_apps
        self.current_page = 0
        save_app_order([a['path'] for a in sorted_apps])
        self.save_current_order()
        self.display_apps(self.filtered_apps, self.current_page)

    def prompt_set_alias(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select application"),
            "/Applications",
            "Applications (*.app)"
        )
        if not path:
            return
        display_name = get_finder_display_name(path)
        current_alias_raw = self.alias_name_map.get(path, display_name)
        current_alias = _normalize_display_name(current_alias_raw)
        dlg = CustomInputDialog(
            self.tr("Set alias"),
            self.tr("Alias for %n").replace('%n', display_name),
            default_text=current_alias,
            parent=self,
            buttons=(self.tr("OK"), self.tr("Cancel")),
            default=0
        )
        res = dlg.exec()
        if res != 0:  # cancel or close
            return
        alias = dlg.text.strip()
        if alias:
            self.alias_name_map[path] = alias
        else:
            self.alias_name_map.pop(path, None)
        # 同步 display name
        self.display_name_map[path] = display_name
        save_display_name_map(self.display_name_map)
        save_alias_name_map(self.alias_name_map)
        self.apply_display_aliases(refresh=True)

    def reset_aliases_to_finder(self):
        self.alias_name_map = {}
        save_alias_name_map(self.alias_name_map)
        self.apply_display_aliases(refresh=True)

    def toggle_keyboard_mode(self):
        self.new_keyboard_mode = self.new_keyboard_mode_action.isChecked()
        self.write_keyboard_mode_setting(self.new_keyboard_mode)

    def read_keyboard_mode_setting(self):
        path = os.path.expanduser("~/.raspberry_keyboard_mode")
        try:
            if os.path.exists(path):
                return open(path, "r", encoding="utf-8").read().strip() != "0"
        except Exception:
            pass
        # 默认启用新键盘映射
        return True

    def write_keyboard_mode_setting(self, enabled: bool):
        path = os.path.expanduser("~/.raspberry_keyboard_mode")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("1" if enabled else "0")
        except Exception:
            pass

    def toggle_clear_search_on_close(self):
        self.clear_search_on_close = self.clear_search_on_close_action.isChecked()
        self.write_clear_search_on_close_setting(self.clear_search_on_close)

    def read_clear_search_on_close_setting(self):
        path = os.path.expanduser("~/.raspberry_clear_search_on_close")
        try:
            if os.path.exists(path):
                return open(path, "r", encoding="utf-8").read().strip() == "1"
        except Exception:
            pass
        # 默认关闭
        return False

    def write_clear_search_on_close_setting(self, enabled: bool):
        path = os.path.expanduser("~/.raspberry_clear_search_on_close")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("1" if enabled else "0")
        except Exception:
            pass

    def toggle_compact_mode(self):
        self.compact_mode = self.compact_mode_action.isChecked()
        self.write_compact_mode_setting(self.compact_mode)
        self.display_apps(self.filtered_apps, self.current_page)

    # 仅保存 bool，别保存边距
    def read_compact_mode_setting(self):
        path = os.path.expanduser("~/.raspberry_compact_mode")
        try:
            if os.path.exists(path):
                return open(path, "r", encoding="utf-8").read().strip() == "1"
        except Exception:
            pass
        return False

    def write_compact_mode_setting(self, enabled: bool):
        path = os.path.expanduser("~/.raspberry_compact_mode")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("1" if enabled else "0")
        except Exception:
            pass

    def _first_app_global_index(self):
        """
        返回 main_order 中第一个 ('app', ...) 的全局索引；若没有，返回 len(groups)
        """
        for i, (typ, obj) in enumerate(self.main_order):
            if typ == 'app':
                return i
        # 全是 group 的情况：apps 段从 len(groups) 开始
        groups_count = sum(1 for typ, _ in self.main_order if typ == 'group')
        return groups_count

    def _last_app_global_index(self):
        idx = -1
        for i, (typ, obj) in enumerate(self.main_order):
            if typ == 'app':
                idx = i
        return idx

    def on_drop_reorder_in_main(self, app_path: str, slot_index_on_page: int):
        """
        在当前页 slot_index_on_page 处插入 app（仅限 apps 段），保证：所有 group 在前。
        允许跨页（slot 索引为“页内索引”）
        """
        # 找源 app
        src_app = None
        for a in self.apps:
            if a['path'] == app_path:
                src_app = a
                break
        if not src_app:
            return

        # 计算目标“页内 -> 全局 apps 段”位置
        page_start = self.current_page * self.items_per_page
        # 当前页 items（含 group + app 或仅 app）
        is_searching = bool(self.main_content.search_bar.text().strip())
        if is_searching:
            page_items = [('app', a) for a in self.filtered_apps[page_start:page_start + self.items_per_page]]
        else:
            page_items = self.main_order[page_start:page_start + self.items_per_page]

        # 求出当前页内 apps 段的“起始全局索引”
        first_app_global = self._first_app_global_index()
        # 计算 slot_index_on_page 相对于“page_start”的偏移，转成全局 slot
        target_global_slot = page_start + slot_index_on_page

        # 约束：不能落到 groups 段
        if target_global_slot < first_app_global:
            target_global_slot = first_app_global

        # 将“目标全局 slot”转换为“目标在 apps 段中的绝对插入索引”
        apps_global_positions = [i for i, (typ, obj) in enumerate(self.main_order) if typ == 'app']
        if not apps_global_positions:
            # 当前没有 apps：追加到 group 之后
            insert_pos_global = first_app_global
        else:
            # 根据 target_global_slot 定位 apps 段中的插入位置（前驱/后继）
            insert_pos_global = first_app_global
            for gi in apps_global_positions:
                if gi < target_global_slot:
                    insert_pos_global = gi + 1

        # 从 main_order 中移除源 app
        self.main_order = [(typ, obj) for (typ, obj) in self.main_order if not (typ == 'app' and obj is src_app)]
        # 重新计算“现在”的 first_app_global（移除后 groups 段长度不变）
        first_app_global = self._first_app_global_index()
        last_app_global = self._last_app_global_index()
        if insert_pos_global < first_app_global:
            insert_pos_global = first_app_global
        if last_app_global >= 0 and insert_pos_global > last_app_global + 1:
            insert_pos_global = last_app_global + 1

        # 插入
        self.main_order.insert(insert_pos_global, ('app', src_app))
        self.save_current_order()

        # 维护 filtered_apps：保证未分组 apps 的列表顺序与 main_order 中 apps 顺序一致
        ordered_paths = [obj['path'] for typ, obj in self.main_order if typ == 'app']
        path_to_app = {a['path']: a for a in self.apps if a['path'] in ordered_paths}
        self.filtered_apps = [path_to_app[p] for p in ordered_paths if p in path_to_app]

        # 刷新当前页
        self.display_apps(self.filtered_apps, self.current_page)

    def read_anim_speed_setting(self):
        path = os.path.expanduser("~/.raspberry_anim_speed")
        try:
            if os.path.exists(path):
                return int(open(path, "r", encoding="utf-8").read().strip())
        except Exception:
            pass
        return 8000  # 默认值

    def write_anim_speed_setting(self, val):
        path = os.path.expanduser("~/.raspberry_anim_speed")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(str(val))
        except Exception:
            pass

    def on_anim_speed_changed(self, val):
        self.page_anim_speed = val
        self.anim_speed_value_label.setText(str(val))
        self.write_anim_speed_setting(val)

    def _on_touchpad_swipe_release(self):
        page_w = self.main_content.grid_widget.width()
        threshold = page_w // 2
        accum = self._touchpad_swipe_accum
        direction = self._touchpad_swipe_direction
        btns = self._touchpad_swipe_btns

        # 新增：首末页判断
        is_first_page = self.current_page == 0
        is_last_page = self.current_page == self.total_pages() - 1

        # 如果是首页且向右滑（accum>0），只允许滑动四分之一页
        if is_first_page and accum > 0:
            max_accum = page_w // 4
            if accum > max_accum:
                accum = max_accum
            # 回弹动画
            group = QParallelAnimationGroup(self)
            for btn in btns:
                if sip.isdeleted(btn):
                    continue
                orig = getattr(btn, "_orig_pos", btn.pos())
                anim = QPropertyAnimation(btn, b"pos", self)
                anim.setDuration(200)
                anim.setStartValue(btn.pos())
                anim.setEndValue(orig)
                anim.setEasingCurve(QEasingCurve.Type.InBounce)
                group.addAnimation(anim)
            group.start()
            self._touchpad_swipe_anim = group
            # 清理状态
            self._touchpad_swipe_active = False
            self._touchpad_swipe_accum = 0
            self._touchpad_swipe_direction = None
            self._touchpad_swipe_btns = []
            return

        # 如果是末页且向左滑（accum<0），只允许滑动四分之一页
        if is_last_page and accum < 0:
            min_accum = -page_w // 4
            if accum < min_accum:
                accum = min_accum
            # 回弹动画
            group = QParallelAnimationGroup(self)
            for btn in btns:
                if sip.isdeleted(btn):
                    continue
                orig = getattr(btn, "_orig_pos", btn.pos())
                anim = QPropertyAnimation(btn, b"pos", self)
                anim.setDuration(200)
                anim.setStartValue(btn.pos())
                anim.setEndValue(orig)
                anim.setEasingCurve(QEasingCurve.Type.InBounce)
                group.addAnimation(anim)
            group.start()
            self._touchpad_swipe_anim = group
            # 清理状态
            self._touchpad_swipe_active = False
            self._touchpad_swipe_accum = 0
            self._touchpad_swipe_direction = None
            self._touchpad_swipe_btns = []
            return

        # 正常翻页逻辑
        if abs(accum) < threshold:
            # 回弹
            group = QParallelAnimationGroup(self)
            for btn in btns:
                if sip.isdeleted(btn):
                    continue
                orig = getattr(btn, "_orig_pos", btn.pos())
                anim = QPropertyAnimation(btn, b"pos", self)
                anim.setDuration(200)
                anim.setStartValue(btn.pos())
                anim.setEndValue(orig)
                anim.setEasingCurve(QEasingCurve.Type.InBounce)
                group.addAnimation(anim)
            group.start()
            self._touchpad_swipe_anim = group
        else:
            # 继续补完翻页距离（从当前位置继续）
            if direction == "left":
                target_page = min(self.current_page + 1, self.total_pages() - 1)
                remaining = -page_w - accum
            else:
                target_page = max(self.current_page - 1, 0)
                remaining = page_w - accum

            group = QParallelAnimationGroup(self)
            for btn in btns:
                if sip.isdeleted(btn):
                    continue
                anim = QPropertyAnimation(btn, b"pos", self)
                anim.setDuration(200)
                anim.setStartValue(btn.pos())
                anim.setEndValue(btn.pos() + QPoint(remaining, 0))
                anim.setEasingCurve(QEasingCurve.Type.InBounce)
                group.addAnimation(anim)

            # 动画开始时就刷新页面
            def on_anim_start():
                self.goto_page(target_page)

            group.stateChanged.connect(
                lambda new, old: on_anim_start() if new == QAbstractAnimation.State.Running else None
            )
            group.start()
            self._touchpad_swipe_anim = group

        # 清理状态
        self._touchpad_swipe_active = False
        self._touchpad_swipe_accum = 0
        self._touchpad_swipe_direction = None
        self._touchpad_swipe_btns = []

    def goto_page_immediate(self, page: int):
        total_pages = self.total_pages()
        if page < 0 or page >= total_pages:
            return
        self.current_page = page
        # 同步小圆点
        self.update_page_indicator(
            len(self.main_order) if not self.main_content.search_bar.text().strip()
            else len(self.filtered_apps)
        )
        # 立刻上新，无过场
        self.display_apps(self.filtered_apps, self.current_page)

    def read_auto_compact_mode_setting(self):
        path = os.path.expanduser("~/.raspberry_auto_compact_mode")
        try:
            if os.path.exists(path):
                return open(path, "r", encoding="utf-8").read().strip() == "1"
        except Exception:
            pass
        return True  # 默认自动

    def write_auto_compact_mode_setting(self, enabled: bool):
        path = os.path.expanduser("~/.raspberry_auto_compact_mode")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("1" if enabled else "0")
        except Exception:
            pass

    def toggle_auto_compact_mode(self):
        enabled = self.auto_compact_mode_action.isChecked()
        self.write_auto_compact_mode_setting(enabled)
        # 立即判断一次
        rendered = self.check_and_apply_compact_mode()
        if not rendered:
            self.display_apps(self.filtered_apps, self.current_page)

    def check_and_apply_compact_mode(self):
        if not self.read_auto_compact_mode_setting():
            return False

        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        cache = load_display_profile_cache()
        cache_key = None
        screen_name = "Unknown"
        screen_width = screen_height = 0

        if screen:
            geo = screen.geometry()
            screen_name = screen.name() or "Unknown"
            screen_width = geo.width()
            screen_height = geo.height()
            cache_key = f"{screen_name}|{screen_width}x{screen_height}"
            cached_profile = cache.get(cache_key)
            # 如果有缓存，直接应用，不再计算
            if cached_profile and "compact_mode" in cached_profile:
                self.compact_mode = bool(cached_profile.get("compact_mode", False))
                self.compact_mode_action.setChecked(self.compact_mode)
                self.write_compact_mode_setting(self.compact_mode)
                self.display_apps(self.filtered_apps, self.current_page)
                return True

        # 先用正常模式布局
        self.compact_mode = False
        self.compact_mode_action.setChecked(False)
        self.write_compact_mode_setting(False)
        self.display_apps(self.filtered_apps, self.current_page)
        QApplication.processEvents()  # 强制刷新布局
        gap_normal = self.get_actual_icon_gap()

        # 再用紧凑模式布局
        self.compact_mode = True
        self.compact_mode_action.setChecked(True)
        self.write_compact_mode_setting(True)
        self.display_apps(self.filtered_apps, self.current_page)
        QApplication.processEvents()
        gap_compact = self.get_actual_icon_gap()

        # 比较实际间距
        if gap_compact > gap_normal:
            # 紧凑模式间距反而更大，关闭紧凑模式
            self.compact_mode = False
            self.compact_mode_action.setChecked(False)
            self.write_compact_mode_setting(False)
            self.display_apps(self.filtered_apps, self.current_page)
        else:
            # 紧凑模式间距更小，保持紧凑模式
            self.compact_mode = True
            self.compact_mode_action.setChecked(True)
            self.write_compact_mode_setting(True)
            self.display_apps(self.filtered_apps, self.current_page)

        if cache_key:
            cache[cache_key] = {
                "screen_name": screen_name,
                "width": screen_width,
                "height": screen_height,
                "compact_mode": self.compact_mode,
                "updated_at": datetime.datetime.now().isoformat()
            }
            save_display_profile_cache(cache)
        return True

    def get_actual_icon_gap(self):
        grid_layout = self.main_content.grid_layout
        btns = []
        for i in range(grid_layout.count()):
            w = grid_layout.itemAt(i).widget()
            if isinstance(w, (AppButton, GroupButton)):
                btns.append(w)
        if len(btns) < 2:
            return 0
        # 取第一个和第二个按钮的 x 坐标
        x0 = btns[0].pos().x()
        x1 = btns[1].pos().x()
        return x1 - x0


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
        lbl1 = QLabel(self.tr(f'Version %n').replace('%n', VERSION), self)
        blay3 = QHBoxLayout()
        blay3.setContentsMargins(0, 0, 0, 0)
        blay3.addStretch()
        blay3.addWidget(lbl1)
        blay3.addStretch()
        widg3.setLayout(blay3)

        widg4 = QWidget()
        lbl2 = QLabel(self.tr('Thanks for your love🤟.'), self)
        blay4 = QHBoxLayout()
        blay4.setContentsMargins(0, 0, 0, 0)
        blay4.addStretch()
        blay4.addWidget(lbl2)
        blay4.addStretch()
        widg4.setLayout(blay4)

        widg5 = QWidget()
        lbl3 = QLabel(self.tr('For more of my works, please visit the homepage🥰.'), self)
        blay5 = QHBoxLayout()
        blay5.setContentsMargins(0, 0, 0, 0)
        blay5.addStretch()
        blay5.addWidget(lbl3)
        blay5.addStretch()
        widg5.setLayout(blay5)

        widg6 = QWidget()
        lbl4 = QLabel(self.tr('Special thanks to ut.code(); of the University of Tokyo❤️.'), self)
        blay6 = QHBoxLayout()
        blay6.setContentsMargins(0, 0, 0, 0)
        blay6.addStretch()
        blay6.addWidget(lbl4)
        blay6.addStretch()
        widg6.setLayout(blay6)

        widg7 = QWidget()
        lbl5 = QLabel(self.tr('This app is under the protection of GPL-3.0 license.'), self)
        blay7 = QHBoxLayout()
        blay7.setContentsMargins(0, 0, 0, 0)
        blay7.addStretch()
        blay7.addWidget(lbl5)
        blay7.addStretch()
        widg7.setLayout(blay7)

        widg8 = QWidget()
        widg8.setFixedHeight(50)
        bt1 = WhiteButton(self.tr('The Author'))
        bt1.setMinimumWidth(100)
        bt1.clicked.connect(self.intro)
        bt2 = WhiteButton(self.tr('Github Page'))
        bt2.setMinimumWidth(100)
        bt2.clicked.connect(self.homepage)
        blay8 = QHBoxLayout()
        blay8.setContentsMargins(0, 0, 0, 0)
        blay8.addStretch()
        blay8.addWidget(bt1)
        blay8.addWidget(bt2)
        blay8.addStretch()
        widg8.setLayout(blay8)

        bt7 = WhiteButton(self.tr('Buy me a cup of coffee☕'))
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
        self.setWindowTitle(self.tr("Thank you for your support!"))
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

        m1 = QLabel(self.tr('Thank you for your kind support! 😊'), self)
        m2 = QLabel(self.tr('I will write more interesting apps! 🥳'), self)

        widg_c = QWidget()
        widg_c.setFixedHeight(50)
        bt1 = WhiteButton(self.tr('Thank you!'))
        #bt1.setMaximumHeight(20)
        bt1.setMinimumWidth(100)
        bt1.clicked.connect(self.cancel)
        bt2 = WhiteButton(self.tr('Neither one above? Buy me a coffee~'))
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
        self.setWindowTitle(self.tr("Thank you for your support!"))
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

        m1 = QLabel(self.tr('Thank you for your kind support! 😊'), self)
        m2 = QLabel(self.tr('I will write more interesting apps! 🥳'), self)

        widg_c = QWidget()
        widg_c.setFixedHeight(50)
        bt1 = WhiteButton(self.tr('Thank you!'))
        #bt1.setMaximumHeight(20)
        bt1.setMinimumWidth(100)
        bt1.clicked.connect(self.cancel)
        bt2 = WhiteButton(self.tr('Neither one above? Buy me a coffee~'))
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
        self.setWindowTitle(self.tr("Thank you for your support!"))
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

        m1 = QLabel(self.tr('Thank you for your kind support! 😊'), self)
        m2 = QLabel(self.tr('I will write more interesting apps! 🥳'), self)

        widg_c = QWidget()
        widg_c.setFixedHeight(50)
        bt1 = WhiteButton(self.tr('Thank you!'))
        #bt1.setMaximumHeight(20)
        bt1.setMinimumWidth(100)
        bt1.clicked.connect(self.cancel)
        bt2 = WhiteButton(self.tr('Neither one above? Buy me a coffee~'))
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
        self.setWindowTitle(self.tr("Thank you for your support!"))
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

        m1 = QLabel(self.tr('Thank you for your kind support! 😊'), self)
        m2 = QLabel(self.tr('I will write more interesting apps! 🥳'), self)

        widg_c = QWidget()
        widg_c.setFixedHeight(50)
        bt1 = WhiteButton(self.tr('Thank you!'))
        #bt1.setMaximumHeight(20)
        bt1.setMinimumWidth(100)
        bt1.clicked.connect(self.cancel)
        bt2 = WhiteButton(self.tr('Neither one above? Buy me a coffee~'))
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
        self.setFixedSize(280, 220)
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

        title = QLabel(self.tr("<h2>Raspberry Update</h2>"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        widg5 = QWidget()
        lbl1 = QLabel(self.tr('Latest version:'), self)
        self.lbl2 = QLabel('', self)
        blay5 = QHBoxLayout()
        blay5.setContentsMargins(0, 0, 0, 0)
        # blay5.addStretch()
        blay5.addWidget(lbl1)
        blay5.addWidget(self.lbl2)
        blay5.addStretch()
        widg5.setLayout(blay5)

        widg3 = QWidget()
        self.lbl = QLabel(self.tr(f'Current version: v%n').replace('%n', VERSION), self)
        blay3 = QHBoxLayout()
        blay3.setContentsMargins(0, 0, 0, 0)
        # blay3.addStretch()
        blay3.addWidget(self.lbl)
        blay3.addStretch()
        widg3.setLayout(blay3)

        widg4 = QWidget()
        widg4.setFixedHeight(50)
        lbl0 = QLabel(self.tr('Check release:'), self)
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
        main_h_box.addWidget(title)
        main_h_box.addSpacing(5)
        main_h_box.addWidget(widg5)
        main_h_box.addSpacing(5)
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
            nowversion = 'v' + VERSION
            if result == nowversion:
                alertupdate = result + self.tr(' (up-to-date)')
                self.lbl2.setText(alertupdate)
                self.lbl2.adjustSize()
            else:
                alertupdate = result + self.tr(' is ready!')
                self.lbl2.setText(alertupdate)
                self.lbl2.adjustSize()
        except:
            alertupdate = self.tr('No Intrenet')
            self.lbl2.setText(alertupdate)
            self.lbl2.adjustSize()

    @staticmethod
    def fetch_latest_version_text():
        # 返回页面纯文本，或直接返回最新版本字符串
        targetURL = 'https://github.com/Ryan-the-hito/Raspberry/releases'
        try:
            urllib3.disable_warnings()
            logging.captureWarnings(True)
            s = requests.session()
            s.keep_alive = False
            response = s.get(targetURL, verify=False, timeout=15)
            response.encoding = 'utf-8'
            html_content = response.text

            soup = BeautifulSoup(html_content, "html.parser")
            for img in soup.find_all("img"):
                img.decompose()
            text_maker = html2text.HTML2Text()
            text_maker.ignore_links = True
            text_maker.ignore_images = True
            plain_text = text_maker.handle(str(soup))
            plain_text_utf8 = plain_text.encode(response.encoding).decode("utf-8")

            for _ in range(10):
                plain_text_utf8 = (plain_text_utf8
                                   .replace('\n\n\n\n', '\n\n')
                                   .replace('\n\n\n', '\n\n')
                                   .replace('   ', ' ')
                                   .replace('  ', ' '))
            return plain_text_utf8
        except Exception:
            return None

    @staticmethod
    def extract_latest_tag(plain_text_utf8: str) -> str | None:
        # 返回类似 'v0.0.12' 的字符串
        if not plain_text_utf8:
            return None
        pattern2 = re.compile(r'(v\d+\.\d+\.\d+)\sLatest')
        result = pattern2.findall(plain_text_utf8)
        if result:
            return result[0]
        return None


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

        title = QLabel(self.tr("<h2>Permissions Required</h2>"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        info_text = (self.tr(
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
        ))

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

    lang_file = Path.home() / ".raspberry_lang"
    if lang_file.exists():
        lang = lang_file.read_text(encoding="utf-8").strip()
    else:
        lang = "system"  # 默认：跟随系统
    load_translation(app, lang)

    win = None  # 全局主窗口变量

    # Dock delegate 必须在主线程入口设置
    if sys.platform == "darwin":
        class _DockClickDelegate(NSObject):
            def applicationShouldHandleReopen_hasVisibleWindows_(self, app, flag):
                if win is not None:
                    if win.isVisible():
                        QTimer.singleShot(0, win.close_main_window)
                    else:
                        QTimer.singleShot(0, win.show_main_window)
                return False
        dock_delegate = _DockClickDelegate.alloc().init()
        NSApp.setDelegate_(dock_delegate)

    # 索引提示窗口
    indexing_dialog = IndexingDialog()
    indexing_dialog.show()
    app.processEvents()  # 保证窗口及时显示

    def bring_main_window_to_front():
        pass
        # if win is not None:
        #     win.show_main_window()
        # win.showNormal()  # 如果窗口被最小化
        # win.raise_()  # 提到最前
        # win.activateWindow()  # 获取焦点

    _server = QLocalServer()
    QLocalServer.removeServer(SINGLETON)
    _server.listen(SINGLETON)
    _server.newConnection.connect(lambda: bring_main_window_to_front())

    def on_index_finished(apps):
        indexing_dialog.close()
        permission = PermissionInfoWidget()
        permission.first_show_window()
        global win
        win = LaunchpadWindow(apps)
        win.setAutoFillBackground(True)
        p = win.palette()
        p.setColor(win.backgroundRole(), QColor('#ECECEC'))
        win.setPalette(p)
        win.hide()
        app.setStyleSheet(style_sheet_ori)

    index_worker = AppIndexWorker()
    index_worker.finished.connect(on_index_finished)
    index_worker.start()
    
    sys.exit(app.exec())
