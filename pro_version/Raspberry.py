#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -*- encoding:UTF-8 -*-
# coding=utf-8
# coding:utf-8

import sys
# Started by another AI app as its MCP server (shared/APP_MCP_SPEC.md): no window, only the bridge that
# forwards to the tools of the family's apps on this Mac. Before anything else (also before the
# single-instance check), so stdout stays clean.
if '--mcp-stdio' in sys.argv[1:]:
    import app_mcp_host
    sys.exit(app_mcp_host.main())

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
from PyQt6.QtCore import Qt, QObject, QPropertyAnimation, QVariantAnimation, QRect, pyqtSignal, QSize, QPoint, QRectF, QTimer, QThread, QEasingCurve, QParallelAnimationGroup, QAbstractAnimation, QEvent, QPointF, QCoreApplication, QElapsedTimer, QEventLoop, QTranslator, QLocale, QLibraryInfo, pyqtSlot, QMargins, QMimeData
import hashlib
import sys
import threading
import atexit
import weakref
from PIL import Image, ImageFilter, ImageQt
from pathlib import Path
import shutil
import webbrowser
import logging
import re
from PyQt6 import sip
# requests / bs4 / html2text: loaded by the update check when it runs (about 0.35 s less at every start)
if sys.platform == "darwin":
    import objc
    from Foundation import NSBundle, NSObject, NSNotificationCenter, NSSelectorFromString, NSDistributedNotificationCenter, NSUserDefaults, NSFileManager, NSAppleEventManager
    from AppKit import NSWorkspace, NSImage, NSApp
    from PyQt6.QtGui import QImage


# ── where Raspberry keeps its things (Ryan 2026-11-16: like Broccoli, the places Apple recommends) ──
#   data      ~/Library/Application Support/com.ryanthehito.raspberry/RaspberryAppPath/
#   settings  …/RaspberryAppPath/Settings/           (one small file per switch)
#   backups   …/RaspberryAppPath/Backups/
#   cache     ~/Library/Caches/com.ryanthehito.raspberry/   (the icon pictures: can be made again)
# Until 0.0.16 all of it lay loose in the home folder as hidden files (~/.launchpad_… / ~/.raspberry_…).
# The first start of this version moves them (move_legacy_data below): a copy goes to Backups first,
# then each file is moved and is gone from the home folder. Nothing reads the old places afterwards.
BUNDLE_ID = 'com.ryanthehito.raspberry'
APP_SUPPORT_DIR = os.path.join(os.path.expanduser("~/Library/Application Support"), BUNDLE_ID)
DATA_DIR = os.path.join(APP_SUPPORT_DIR, 'RaspberryAppPath')
SETTINGS_DIR = os.path.join(DATA_DIR, 'Settings')
BACKUPS_DIR = os.path.join(DATA_DIR, 'Backups')
CACHE_DIR = os.path.join(os.path.expanduser("~/Library/Caches"), BUNDLE_ID)
MOVE_NOTICE_FILE = os.path.join(DATA_DIR, '.moved_notice_pending')


def data_path(name) -> str:
    return os.path.join(DATA_DIR, name)


def setting_path(name) -> str:
    return os.path.join(SETTINGS_DIR, name)


# (name in the home folder until 0.0.16, where it is now); also how a backup folder's files are named
LEGACY_DATA_FILES = [
    ('.launchpad_groups.json', data_path('groups.json')),
    ('.launchpad_app_order.json', data_path('app_order.json')),
    ('.launchpad_app_paths.json', data_path('app_paths.json')),
    ('.launchpad_main_order.json', data_path('main_order.json')),
    ('.raspberry_display_names.json', data_path('display_names.json')),
    ('.raspberry_alias_names.json', data_path('alias_names.json')),
    ('.raspberry_display_profiles.json', data_path('display_profiles.json')),
    ('.raspberry_user_apps_places.json', data_path('user_apps_places.json')),
]
LEGACY_SETTING_FILES = [('.raspberry_' + name, setting_path(name)) for name in (
    'hide_dock', 'show_dock', 'clean_wallpaper', 'keyboard_mode', 'clear_search_on_close', 'compact_mode',
    'anim_speed', 'auto_compact_mode', 'user_apps', 'lang')]
LEGACY_ICON_CACHE = '.launchpad_icon_cache'


def merge_auto_compact_setting():
    """Once: "Auto Compact Mode" is gone (Ryan 2026-11-19: one switch). Whoever had it on wanted the
    narrower spacing wherever there is one — that is what Compact Mode itself does now — so Compact
    Mode is switched on for them; the old switch's file and its per-screen record are removed."""
    auto, record = setting_path('auto_compact_mode'), data_path('display_profiles.json')
    try:
        if os.path.isfile(auto):
            with open(auto, encoding='utf-8') as handle:
                was_on = handle.read().strip() == '1'
            if was_on:
                with open(setting_path('compact_mode'), 'w', encoding='utf-8') as handle:
                    handle.write('1')
            os.remove(auto)
        if os.path.isfile(record):
            os.remove(record)
    except Exception:
        pass


def move_legacy_data(home=None):
    """Once, on the first start of this version: everything Raspberry kept loose in the home folder
    goes to its new place. Returns the old names that were moved (empty: nothing was there).
    A copy of the files is kept in Backups/before_move_<time> first. A file that already exists at
    the new place wins: the old one only goes into that backup. The icon cache is moved, not copied
    (it can be made again); if moving it fails it is simply dropped."""
    home = home or os.path.expanduser("~")
    for folder in (DATA_DIR, SETTINGS_DIR, BACKUPS_DIR, CACHE_DIR):
        os.makedirs(folder, exist_ok=True)
    found = [(old, new) for old, new in LEGACY_DATA_FILES + LEGACY_SETTING_FILES
             if os.path.isfile(os.path.join(home, old))]
    old_cache = os.path.join(home, LEGACY_ICON_CACHE)
    moved = []
    if found:
        backup = os.path.join(BACKUPS_DIR, 'before_move_' + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
        os.makedirs(backup, exist_ok=True)
        for old, new in found:
            source = os.path.join(home, old)
            try:
                shutil.copy2(source, os.path.join(backup, old))
                if not os.path.exists(new):
                    os.makedirs(os.path.dirname(new), exist_ok=True)
                    shutil.move(source, new)
                else:
                    os.remove(source)
                moved.append(old)
            except Exception as error:
                print(f"Could not move {source}: {error}")
    if os.path.isdir(old_cache):
        target = os.path.join(CACHE_DIR, 'icon_cache')
        try:
            if os.path.isdir(target) and os.listdir(target):
                shutil.rmtree(old_cache)
            else:
                if os.path.isdir(target):
                    os.rmdir(target)
                shutil.move(old_cache, target)
            moved.append(LEGACY_ICON_CACHE)
        except Exception as error:
            print(f"Could not move {old_cache}: {error}")
            shutil.rmtree(old_cache, ignore_errors=True)
    if moved:
        try:
            with open(MOVE_NOTICE_FILE, 'w', encoding='utf-8') as f:
                f.write(datetime.datetime.now().isoformat())
        except Exception:
            pass
    return moved


DATA_MOVED = move_legacy_data()
merge_auto_compact_setting()

GROUPS_FILE = data_path('groups.json')
ICON_CACHE_DIR = os.path.join(CACHE_DIR, 'icon_cache')
os.makedirs(ICON_CACHE_DIR, exist_ok=True)
APP_PATHS_FILE = data_path('app_paths.json')
APP_ORDER_FILE = data_path('app_order.json')
MAIN_ORDER_FILE = data_path('main_order.json')
DISPLAY_NAME_MAP_FILE = data_path('display_names.json')
ALIAS_NAME_MAP_FILE = data_path('alias_names.json')
LANG_FILE = setting_path('lang')
HIDDEN_APPS_FILE = data_path('hidden_apps.json')
PAGES_FILE = data_path('pages.json')      # with separate pages: which page each icon is on
VERSION = "0.0.20"
NAME = 'Raspberry'      # one Raspberry now: no "Pro" in any name (Ryan 2026-11-18)

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

# The system's new design (Liquid Glass title bars, the new traffic lights) for this run only, declared
# before the QApplication exists (style book 5.7.2). Nothing is written to the settings.
if sys.platform == "darwin":
    try:
        NSUserDefaults.standardUserDefaults().registerDefaults_(
            {'com.apple.SwiftUI.IgnoreSolariumLinkedOnCheck': True})
    except Exception:
        pass

# ── "Show on all Spaces" over full-screen apps (Ryan 2026-11-19; measured on macOS 27) ───────────────
# A window of an app WITH a Dock icon is kept off other apps' full-screen Spaces — unless its marks
# (join all Spaces + full-screen auxiliary) were put on while the app had no Dock icon; then they hold
# after the icon is there, for as long as they are not switched off and on again. So, with the switch
# on, Raspberry starts without its Dock icon, builds its windows and marks them, and then shows the
# icon once (show_dock_icon). Nothing is flipped later: each flip makes the Dock jump.
def all_spaces_setting_on() -> bool:
    try:
        return open(setting_path("show_on_all_spaces"), "r", encoding="utf-8").read().strip() == "1"
    except Exception:
        return False


def start_without_dock_icon() -> bool:
    """Before the QApplication exists: this run starts as an app without a Dock icon."""
    if sys.platform != "darwin":
        return False
    try:
        os.environ['QT_MAC_DISABLE_FOREGROUND_APPLICATION_TRANSFORM'] = '1'   # Qt must not bring the icon itself
        NSBundle.mainBundle().infoDictionary()['LSUIElement'] = '1'
        return True
    except Exception:
        return False


def dock_icon_shown() -> bool:
    try:
        return sys.platform != "darwin" or int(NSApp.activationPolicy()) == 0
    except Exception:
        return True


def show_dock_icon() -> None:
    """The Dock icon appears (once; harmless when it is there already)."""
    try:
        if sys.platform == "darwin" and int(NSApp.activationPolicy()) != 0:
            NSApp.setActivationPolicy_(0)
    except Exception:
        pass


# only the real program starts hidden (__main__); whoever loads this file otherwise decides for itself
STARTED_WITHOUT_DOCK_ICON = __name__ == "__main__" and all_spaces_setting_on() and start_without_dock_icon()

app = QApplication(sys.argv)
if __name__ == "__main__" and not STARTED_WITHOUT_DOCK_ICON:
    show_dock_icon()        # the packaged app is declared icon-less (Raspberry.spec): switch off → icon at once

# UI STYLE BOOK: /Users/ryanshen/Documents/A-workingfilewithp3.11/UI_STYLEBOOK_macOS27.md (section 5.13).
# The glass functions are Broccoli's, in glass_kit.py; Raspberry's own parts are in raspberry_ui.py.
import glass_kit
import raspberry_ui
from glass_kit import WhiteButton, MacNormalButton, on_theme_changed, install_theme_observer
from raspberry_ui import make_native_glass_window, install_native_glass_window_class

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


# ── The Dock's auto-hide, set through System Events ─────────────────────────────────────────────────
# One call takes about 0.18 s, and the launcher made it inside every open and every close, before its
# first frame — even when the Dock was already as wanted (measured 2026-11-22). Now: off the main
# thread, one at a time, the newest wish wins, and nothing is sent when the Dock is already so.
_DOCK_JOB = {'want': None, 'running': False}
_DOCK_LOCK = threading.Lock()


def dock_autohide_now():
    """The Dock's auto-hide as its settings say (True / False), or None when it cannot be read."""
    try:
        from CoreFoundation import CFPreferencesAppSynchronize, CFPreferencesCopyAppValue
        CFPreferencesAppSynchronize('com.apple.dock')
        value = CFPreferencesCopyAppValue('autohide', 'com.apple.dock')
        return bool(value) if value is not None else False    # never set = the Dock stays
    except Exception:
        return None


def _dock_worker():
    done = None
    while True:
        with _DOCK_LOCK:
            want = _DOCK_JOB['want']
            if want == done:
                _DOCK_JOB['running'] = False
                return
        try:
            if dock_autohide_now() != want:
                script = 'tell application "System Events" to set the autohide of dock preferences to %s' % (
                    'true' if want else 'false')
                subprocess.run(["osascript", "-e", script], env=clean_env_for_child())
        except Exception:
            pass
        done = want


def set_dock_autohide(hidden: bool):
    """Ask for the Dock hidden (True) or kept showing (False); returns at once."""
    with _DOCK_LOCK:
        _DOCK_JOB['want'] = bool(hidden)
        if _DOCK_JOB['running']:
            return
        _DOCK_JOB['running'] = True
    try:
        threading.Thread(target=_dock_worker, daemon=True, name='raspberry-dock').start()
    except Exception:
        with _DOCK_LOCK:
            _DOCK_JOB['running'] = False


def wait_for_dock(timeout=3.0):
    """At quit: let a Dock change that is under way finish (the Dock must not stay hidden)."""
    end = time.time() + timeout
    while time.time() < end:
        with _DOCK_LOCK:
            if not _DOCK_JOB['running']:
                return True
        time.sleep(0.02)
    return False


atexit.register(wait_for_dock)


def _four_cc(code: str) -> int:
    return int.from_bytes(code.encode('ascii'), 'big')


def launched_by_user(event) -> bool:
    """From the Apple event macOS starts an app with: True when the user opened it (Dock, Finder,
    Spotlight, `open`), False when macOS started it at login (a login item or a service item) or when
    it cannot be told."""
    try:
        if event is None or event.eventClass() != _four_cc('aevt') or event.eventID() != _four_cc('oapp'):
            return False
        prop = event.paramDescriptorForKeyword_(_four_cc('prdt'))          # keyAEPropData
        if prop is not None and prop.enumCodeValue() in (_four_cc('lgit'),  # keyAELaunchedAsLogInItem
                                                         _four_cc('lgsi')): # keyAELaunchedAsServiceItem
            return False
        return True
    except Exception:
        return False

# ── Raspberry's functions for an assistant app (Ryan 2026-11-23: 「所有的功能挂载在 Broccoli」) ──
# The way in is the same for every app (app_mcp_host.py: a service on this Mac only + a card in the
# family's folder); raspberry_mcp.py is the list of Raspberry's tools. 2026-11-24 (Ryan: "接口通用，别的也能
# 接"): always started, assistant app or not; any other AI app reaches it through the bridge (Raspberry
# started with --mcp-stdio; the menu's "Use in other AI apps…" copies the setup).
_ASSISTANT_HOST = {'host': None, 'bridge': None}


def start_assistant_tools(window, card_dir=None) -> bool:
    try:
        import raspberry_mcp
        from PyQt6.QtCore import QObject, pyqtSignal, Qt

        class _MainThreadBridge(QObject):
            asked = pyqtSignal(object)

            def __init__(self):
                super().__init__()
                self.asked.connect(self._run, Qt.ConnectionType.QueuedConnection)

            def _run(self, job):
                fn, box, done = job
                try:
                    box['value'] = fn()
                except BaseException as exc:        # handed to the thread that asked
                    box['error'] = exc
                done.set()

        bridge = _MainThreadBridge()

        def run_on_main(fn):
            box, done = {}, threading.Event()
            bridge.asked.emit((fn, box, done))
            done.wait()
            if 'error' in box:
                raise box['error']
            return box.get('value')

        launch = None
        if getattr(sys, 'frozen', False):           # the built app can be opened again; quietly ("autostart")
            bundle = str(Path(sys.executable).parent.parent.parent)
            if bundle.endswith('.app'):
                launch = {'bundle_id': 'com.ryanthehito.raspberry', 'path': bundle, 'args': ['autostart']}
        host = raspberry_mcp.build_host(globals(), window)
        if not host.start(run_on_main=run_on_main, launch=launch, card_dir=card_dir):
            return False
        _ASSISTANT_HOST.update(host=host, bridge=bridge)
        return True
    except Exception:
        logging.exception('assistant tools not started')
        return False


def stop_assistant_tools():
    host, _ASSISTANT_HOST['host'] = _ASSISTANT_HOST['host'], None
    if host is not None:
        try:
            host.stop()
        except Exception:
            pass


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

# ── where apps are looked for ──
# Always: the Mac's Applications folders. On request (menu, off by default — Ryan 2026-11-16: 「加进来，
# 但默认关着」): the user's own ~/Applications too (apps installed for this user only, web apps the
# browsers "install", launchers of tools — and little helper apps, which is why it is not on by default).
SYSTEM_APP_DIRS = ["/Applications", "/System/Applications", "/System/Volumes/Preboot/Cryptexes/App/System/Applications"]
USER_APPS_DIR = os.path.expanduser("~/Applications")
USER_APPS_SETTING_FILE = setting_path("user_apps")
USER_APPS_MEMORY_FILE = data_path("user_apps_places.json")


def user_apps_enabled() -> bool:
    try:
        with open(USER_APPS_SETTING_FILE, "r") as f:
            return f.read().strip() == "1"
    except Exception:
        return False


def write_user_apps_enabled(enabled: bool):
    try:
        with open(USER_APPS_SETTING_FILE, "w") as f:
            f.write("1" if enabled else "0")
    except Exception:
        pass


def is_user_app_path(path) -> bool:
    return str(path).startswith(USER_APPS_DIR.rstrip('/') + '/')


def app_scan_dirs():
    dirs = list(SYSTEM_APP_DIRS)
    if user_apps_enabled() and os.path.isdir(USER_APPS_DIR):
        dirs.append(USER_APPS_DIR)
    return dirs


def load_hidden_apps() -> list:
    """The apps the user does not want to see in Raspberry (Ryan 2026-11-16: 「黑名单……加入黑名单的
    软件不会显示在表面」): their paths, in the order they were hidden."""
    try:
        with open(HIDDEN_APPS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [p for p in data if isinstance(p, str)] if isinstance(data, list) else []
    except Exception:
        return []


def save_hidden_apps(paths):
    try:
        with open(HIDDEN_APPS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(dict.fromkeys(paths)), f, ensure_ascii=False)
    except Exception:
        pass


def allowed_app_paths(paths):
    """The paths Raspberry shows: without the hidden apps, and without the user's own Applications
    folder while that is switched off."""
    hidden = set(load_hidden_apps())
    user = user_apps_enabled()
    return [p for p in paths if p not in hidden and (user or not is_user_app_path(p))]


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


# The bundle name names the app's icon file in the cache. Reading it meant opening and parsing every
# app's Info.plist at each start: about 0.6 s for 330 apps (measured 2026-11-22, "一点开…非常慢").
# Kept here with the plist's size and modification time; the plist is read again only when it changed.
BUNDLE_NAME_MEMO_FILE = os.path.join(CACHE_DIR, 'bundle_names.json')


def load_bundle_name_memo() -> dict:
    try:
        with open(BUNDLE_NAME_MEMO_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_bundle_name_memo(memo: dict):
    try:
        tmp = BUNDLE_NAME_MEMO_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(memo, f, ensure_ascii=False)
        os.replace(tmp, BUNDLE_NAME_MEMO_FILE)
    except Exception:
        pass


def bundle_name(app_path, memo=None):
    """(name, memo entry): the app's name from its Info.plist (or an iOS app's iTunesMetadata.plist),
    else its folder name. With `memo`, an unchanged plist is not opened."""
    info_plist = os.path.join(app_path, 'Contents', 'Info.plist')
    itunes_plist = os.path.join(app_path, 'Wrapper', 'iTunesMetadata.plist')
    stamp = None
    for kind, plist_path in (('info', info_plist), ('itunes', itunes_plist)):
        try:
            st = os.stat(plist_path)
        except OSError:
            continue
        stamp = [kind, st.st_size, st.st_mtime_ns]
        break
    entry = (memo or {}).get(app_path)
    if (stamp is not None and isinstance(entry, list) and len(entry) == 2 and entry[1] == stamp
            and isinstance(entry[0], str) and entry[0]):
        return entry[0], entry
    name = None
    if stamp is not None and stamp[0] == 'info':     # 1. 优先 Info.plist
        try:
            with open(info_plist, 'rb') as f:
                plist = plistlib.load(f)
            name = plist.get('CFBundleDisplayName') or plist.get('CFBundleName') or os.path.basename(app_path)[:-4]
        except Exception as e:
            print(f"Failed to parse Info.plist for {app_path}: {e}")
    elif stamp is not None:                          # 2. iOS 应用的 iTunesMetadata.plist
        try:
            with open(itunes_plist, 'rb') as f:
                plist = plistlib.load(f)
            name = plist.get('title') or plist.get('itemName') or os.path.basename(app_path)[:-4]
        except Exception as e:
            print(f"Failed to parse iTunesMetadata.plist for {app_path}: {e}")
    if not name:                                     # 3. 都没有就用文件夹名
        name = os.path.basename(app_path)[:-4]
    return name, ([name, stamp] if stamp is not None else None)


def get_applications():  # 兼容加载检查iOS软件
    sync_app_paths()
    app_paths = allowed_app_paths(load_app_paths())
    if not app_paths:
        app_paths = allowed_app_paths(find_top_level_apps(app_scan_dirs()))
        save_app_paths(app_paths)
    display_name_map = load_display_name_map()
    alias_name_map = load_alias_name_map()
    display_dirty = False
    alias_dirty = False
    old_memo = load_bundle_name_memo()
    new_memo = {}
    apps = []
    seen_paths = set()
    for app_path in app_paths:
        seen_paths.add(app_path)
        name, memo_entry = bundle_name(app_path, old_memo)
        if memo_entry is not None:
            new_memo[app_path] = memo_entry
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
    if new_memo != old_memo:
        save_bundle_name_memo(new_memo)
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
            w.hide()            # first: else Qt's pending "show" makes it a window of its own
            w.setParent(None)
            w.deleteLater()
    except RuntimeError:
        pass


# 拖拽排序常量（与你现有布局一致）
GRID_COLS = 7
GRID_ROWS = 5
CELL_FULL = 140               # an icon's cell (icon 100 + its name) when the screen has the room
CELL_MIN = 88                 # never smaller than this
ICON_W = 140                  # the cell in use now (set_cell_size): the 7 × 5 cells always fit the screen
ICON_H = 140


def cell_size() -> int:
    return ICON_W


def set_cell_size(value) -> bool:
    """The cell every icon is built with from now on. True when it changed."""
    global ICON_W, ICON_H
    value = max(CELL_MIN, min(CELL_FULL, int(value)))
    changed = value != ICON_W
    ICON_W = ICON_H = value
    return changed


def icon_side(cell=None) -> int:
    """The icon's square in a cell: the cell minus the room of the two lines of its name."""
    return max(40, (cell_size() if cell is None else int(cell)) - 40)


def tile_side(cell=None) -> int:
    """A group's glass tile: 80 in a full cell (an app icon's visible size)."""
    return int(round(icon_side(cell) * raspberry_ui.TILE_SIZE / 100.0))


def tile_radius(cell=None) -> float:
    return tile_side(cell) * raspberry_ui.TILE_RADIUS / float(raspberry_ui.TILE_SIZE)


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
        pen = QPen(raspberry_ui.accent_color(), 3)
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
                  accept_groups=True, clamp_to_app_zone=False, enable_drag=True, cell_rect=None):
        self._cell_rect_provider = cell_rect      # (row, col) → QRect, where the host knows its cells
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
        self._dragging_group = event.mimeData().text().startswith(GROUP_DRAG_PREFIX)
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
        self._dragging_group = event.mimeData().text().startswith(GROUP_DRAG_PREFIX)
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
            leading = 0                      # the page's groups stand first
            for typ, _obj in items[:GRID_COLS * GRID_ROWS]:
                if typ != 'group':
                    break
                leading += 1
            if getattr(self, '_dragging_group', False):
                best_idx = max(0, min(best_idx, leading))
            else:
                best_idx = max(leading, min(best_idx, n))
            if best_idx >= GRID_COLS * GRID_ROWS:      # after the page's last cell
                last = self._cell_rect(GRID_ROWS - 1, GRID_COLS - 1)
                return best_idx, last.right(), last.top(), last.bottom()
            target_cell = self._cell_rect(best_idx // GRID_COLS, best_idx % GRID_COLS)

        line_x = target_cell.left()
        return best_idx, line_x, target_cell.top(), target_cell.bottom()

    def _cell_rect(self, row: int, col: int) -> QRect:
        """
        使用网格内现有小部件的几何与布局间距推断单元格位置。
        为稳妥：以第一行已有的任意控件为基准推算格子宽高与间距。
        如该行为空，则使用默认 ICON_W/H 和布局 spacing。
        """
        provider = getattr(self, '_cell_rect_provider', None)
        if provider is not None:
            rect = provider(row, col)
            if rect is not None:
                return rect
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


class AppIndexWorker(QThread):
    finished = pyqtSignal(object)  # apps

    def run(self):
        apps = get_applications()
        self.finished.emit(apps)


class IndexingDialog(raspberry_ui.BusyCard):
    """The small glass card shown while the applications are indexed (style book 5.13)."""

    def __init__(self, parent=None):
        super().__init__(QCoreApplication.translate(
            "IndexingDialog",
            "Raspberry is indexing applications, please wait and do not close this app. Raspberry will be ready after this window disappers."),
            parent)


class EmptyButton(QPushButton):
    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.main_window = main_window          # 保存主窗引用
        self.setFixedSize(cell_size(), cell_size())  # exactly an icon's cell: every row is the same height
        # macOS lays a push button out by a rectangle a few points off its own (differently for flat ones):
        # rows with icons and rows of blanks then got different heights — use the widget's own rectangle
        self.setAttribute(Qt.WidgetAttribute.WA_LayoutUsesWidgetRect, True)
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
    """The launcher's search (style book 5.5 A / 5.13): a glass capsule 36 high with the drawn magnifier
    and the field's own clear button; 500 wide, 750 while it has the focus. The glass lies under the
    text (the window is transparent); without glass the field fills its capsule itself."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._base_width = 500
        self._expanded_width = int(self._base_width * 1.5)
        self.setFixedHeight(raspberry_ui.SEARCH_HEIGHT)
        self.setFixedWidth(self._base_width)
        self._anim = QPropertyAnimation(self, b"minimumWidth")
        self._anim.setDuration(250)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        glass_kit.add_search_glyph(self)
        self.setClearButtonEnabled(True)
        self.apply_theme()

    def apply_theme(self, dark=None):
        if dark is None:
            dark = is_dark_theme(None)
        self.setStyleSheet(raspberry_ui.search_field_stylesheet(dark, raspberry_ui.glass_active(self)))

    def showEvent(self, event):
        super().showEvent(event)
        if not raspberry_ui.glass_active(self) and raspberry_ui.under_glass(
                self, raspberry_ui.SEARCH_HEIGHT / 2.0) is not None:
            self.apply_theme()

    def focusInEvent(self, event):
        self._anim.stop()
        self._anim.setStartValue(self.width())
        self._anim.setEndValue(self._expanded_width)
        self._anim.start()
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event):
        self._anim.stop()
        self._anim.setStartValue(self.width())
        self._anim.setEndValue(self._base_width)
        self._anim.start()
        super().focusOutEvent(event)
        self.update()

    def setMinimumWidth(self, w):
        self.setFixedWidth(w)
        self.update()

    def minimumWidth(self):
        return self.width()


def _alert_parts(text):
    """(title, message) for the system alert: the first line is the title, the rest the message."""
    text = str(text or '')
    first, _, rest = text.partition('\n')
    if not rest and len(first) > 90:
        return 'Raspberry', first
    return first, rest.strip()


def relaunch_raspberry():
    """Quit Raspberry and open it again (what the "… will restart" notices do on OK)."""
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


class CustomMessageBox:
    """A notice or a question as the system alert (style book 5.7). Used as before:
    CustomMessageBox(text, parent=…, buttons=(…)).exec() → the index of the button chosen."""

    def __init__(self, text, parent=None, icon=None, buttons=("OK",), default=0):
        self.text = text
        self.parent = parent
        self.buttons = [str(b) for b in buttons] or ["OK"]
        self.default = max(0, min(int(default), len(self.buttons) - 1))
        self.result = None

    def _ask(self):
        title, message = _alert_parts(self.text)
        chosen = glass_kit.ask_broccoli_message(self.parent, title, message, list(self.buttons),
                                                self.buttons[self.default])
        return self.buttons.index(chosen) if chosen in self.buttons else self.default

    def exec(self):
        self.result = self._ask()
        return self.result


class RestartMessageBox(CustomMessageBox):
    """The same alert; its first button restarts Raspberry."""

    def exec(self):
        self.result = self._ask()
        if self.result == 0:
            relaunch_raspberry()
        return self.result


class CustomInputDialog:
    """One line of text asked in a glass dialog (style book 5.13). exec() → 0 = OK, 1 = cancelled;
    `text` holds what was typed."""

    def __init__(self, title, message, default_text="", parent=None, buttons=("OK", "Cancel"), default=0):
        self.title = title
        self.message = message
        self.text = default_text
        self.parent = parent
        self.buttons = [str(b) for b in buttons]
        self.result = None

    def exec(self):
        ok_text = self.buttons[0] if self.buttons else None
        cancel_text = self.buttons[1] if len(self.buttons) > 1 else None
        text, accepted = raspberry_ui.ask_text(self.parent, self.title, self.message, self.text,
                                               ok_text=ok_text, cancel_text=cancel_text)
        if accepted:
            self.text = text
        self.result = 0 if accepted else 1
        return self.result


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
        known_paths = set(allowed_app_paths(load_app_paths()))
        app_dirs = app_scan_dirs()
        display_name_map = load_display_name_map()
        alias_name_map = load_alias_name_map()
        display_dirty = False
        alias_dirty = False
        found_paths = set()
        new_apps = []
        all_app_paths = allowed_app_paths(find_top_level_apps(app_dirs))
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
    def __init__(self, app_info, parent=None, parent_group=None, main_window=None, cell=None):
        super().__init__(parent)
        self.app_info = app_info
        self.parent_group = parent_group
        self.main_window = main_window
        cell = cell_size() if cell is None else int(cell)
        side = icon_side(cell)
        self.setStyleSheet("background: transparent; border: none;")
        self.setFixedSize(cell, cell)
        # macOS lays a push button out by a rectangle a few points off its own (differently for flat ones):
        # rows with icons and rows of blanks then got different heights — use the widget's own rectangle
        self.setAttribute(Qt.WidgetAttribute.WA_LayoutUsesWidgetRect, True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.icon_label.setFixedSize(side, side)
        pix = app_info['icon'].pixmap(side, side)
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
        max_width = cell - 10
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
        window = self.main_window
        # in the main grid: the lists of groups come in at both sides for as long as the icon is held
        rails = window is not None and self.parent_group is None and hasattr(window, 'show_drag_rails')
        if rails:
            window.show_drag_rails(self)
        try:
            drag.exec(Qt.DropAction.MoveAction)
        finally:
            if rails:
                window.hide_drag_rails()

    def show_context_menu(self, pos):
        menu = QMenu(self)
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
            for group in self.main_window.groups_in_display_order():
                if self.parent_group and group is self.parent_group:
                    continue
                move_menu.addAction(group['name'], lambda g=group: self.main_window.move_app_to_group(self, g))
            menu.addMenu(move_menu)
            menu.addAction(self.tr("Put it back to the main interface"), self.move_out_of_group)
        if not self.parent_group:
            group_menu = QMenu(self.tr("Combine into a group"), self)
            for group in self.main_window.groups_in_display_order():
                group_menu.addAction(group['name'], lambda g=group: self.main_window.combine_app_to_group(self, g))
            group_menu.addAction(self.tr("🆕 New group"), lambda: self.main_window.combine_app_to_group(self, None))
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
        menu.addAction(self.tr("Hide in Raspberry"), self.hide_in_raspberry)
        menu.addAction(self.tr("Move to the trash can"), self.move_to_trash)
        menu.setProperty('broccoliNativeMenu', True)  # the system's own menu (style book 5.5)
        menu.exec(self.mapToGlobal(pos))

    def move_out_of_group(self):
        if self.main_window and self.parent_group:
            self.main_window.move_app_out_of_group(self.app_info, self.parent_group)

    def hide_in_raspberry(self):
        if self.main_window:
            self.main_window.hide_app(self.app_info)

    def move_to_trash(self):
        subprocess.Popen(
            ['osascript', '-e', f'tell app "Finder" to move POSIX file "{self.app_info["path"]}" to trash'],
            env=clean_env_for_child()
        )
        if self.main_window:
            self.main_window.remove_app(self.app_info)

class GroupTile(QLabel):
    """A group's icon in the grid (style book 5.13): a glass tile 80 × 80 (corner 18, an app icon's
    shape) with up to 3 × 3 small icons on it. The glass lies under the Qt content and never shows
    beyond the grid it slides in; without glass the tile paints a translucent square of the same shape."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._glass = None
        self._glass_tried = False
        self._opacity = 1.0
        self._veil = 0.0
        self._side = tile_side()
        self._radius = tile_radius()

    def tile_rect(self):
        side = self._side
        return QRectF((self.width() - side) / 2.0, (self.height() - side) / 2.0, side, side)

    def showEvent(self, event):
        super().showEvent(event)
        if self._glass_tried:
            return
        self._glass_tried = True
        grid = self.parentWidget()
        while grid is not None and not isinstance(grid, AppGridWidget):
            grid = grid.parentWidget()
        self._glass = raspberry_ui.under_glass(self, self._radius,
                                               inset=(self.width() - self._side) / 2.0, clip=grid)
        if self._glass is not None:
            self._glass.set_opacity(self._opacity * (1.0 - self._veil))

    def set_glass_opacity(self, value):
        """The tile fades with its button (the entrance animation)."""
        self._opacity = float(value)
        if self._glass is not None:
            self._glass.set_opacity(self._opacity * (1.0 - self._veil))

    def set_veil(self, level):
        """An open group blurs what is behind it: the sharp glass fades out as the blurred picture
        (with this tile in it) fades in."""
        self._veil = max(0.0, min(1.0, float(level)))
        if self._glass is not None:
            self._glass.set_opacity(self._opacity * (1.0 - self._veil))

    def paintEvent(self, event):
        if not raspberry_ui.glass_active(self):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(QPen(QColor(255, 255, 255, 90), 1.0))
            painter.setBrush(QColor(255, 255, 255, 40))
            painter.drawRoundedRect(self.tile_rect().adjusted(0.5, 0.5, -0.5, -0.5), self._radius, self._radius)
            painter.end()
        super().paintEvent(event)


GROUP_DRAG_PREFIX = 'raspberry-group:'     # what a dragged group carries (an app carries its path)


class GroupButton(QPushButton):
    def __init__(self, group, parent=None, main_window=None):
        super().__init__(parent)
        self.group = group
        self.main_window = main_window
        cell = cell_size()
        side = icon_side(cell)
        self.setFixedSize(cell, cell)
        # macOS lays a push button out by a rectangle a few points off its own (differently for flat ones):
        # rows with icons and rows of blanks then got different heights — use the widget's own rectangle
        self.setAttribute(Qt.WidgetAttribute.WA_LayoutUsesWidgetRect, True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.icon_label = GroupTile()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.icon_label.setFixedSize(side, side)
        pix = group['icon'].pixmap(tile_side(cell), tile_side(cell))
        self.icon_label.setPixmap(pix)
        layout.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.text_label = QLabel()

        name = group['name']
        font = self.text_label.font()
        max_width = cell - 10
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

    def bind_fade(self, effect):
        """The glass tile follows the button's opacity effect."""
        tile = self.icon_label
        tile.set_glass_opacity(effect.opacity())
        effect.opacityChanged.connect(tile.set_glass_opacity)

    # A group's icon is sorted by dragging like an app's (Ryan 2026-11-18: 「drag drop 主界面的分组为什么
    # 无法调整顺序」): held and moved a few points = a drag, let go where it was pressed = open the group.
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position()
            self._dragging = False
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, '_press_pos', None) is not None and not self._dragging:
            if (event.position() - self._press_pos).manhattanLength() > QApplication.startDragDistance():
                self._dragging = True
                self.startDrag()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pressed, dragged = getattr(self, '_press_pos', None), getattr(self, '_dragging', False)
            self._press_pos = None
            self._dragging = False
            if pressed is not None and not dragged and self.main_window is not None:
                self.main_window.show_group_widget(self.group, group_btn=self)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def startDrag(self):
        window = self.main_window
        if window is None or window._is_searching():
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(GROUP_DRAG_PREFIX + self.group['name'])
        drag.setMimeData(mime)
        drag.setPixmap(self.group['icon'].pixmap(64, 64))
        window.show_drag_rails(self, dragging_group=True)
        try:
            drag.exec(Qt.DropAction.MoveAction)
        finally:
            self._press_pos = None
            self._dragging = False
            window.hide_drag_rails()

    def show_context_menu(self, pos):
        menu = QMenu(self)
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
        menu.setProperty('broccoliNativeMenu', True)  # the system's own menu (style book 5.5)
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
    """The small icons of a group, up to 3 × 3, on a transparent square. The tile under them is system
    glass (GroupTile, style book 5.13) — the painted translucent square and its two white highlight
    strokes are gone."""
    size = 240
    icon_size = 56
    spacing = 8
    grid = 3

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    total_icons = min(9, len(apps))
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


ENTRANCE_MS = 420      # the icons coming in when the launcher opens …
ENTRANCE_SHIFT = 26    # … each from this far (at most) nearer the middle
ENTRANCE_STAGGER = 0.22   # … the outermost starts after this share of the time
RAIL_WIDTH = 72        # the lists at the two sides while an icon is dragged (DragRail)
RAIL_ITEM_H = 80      # tile 44 + name, and the same 6.5 pt of highlight on all four sides of them
RAIL_TILE = 44
RAIL_PAD = 8
RAIL_RADIUS = 16
RAIL_MS = 220
ICON_FLY_MS = 380      # an icon flying into / out of a group
VANISH_MS = 260        # an icon that leaves for good (Trash, a dissolved group) shrinking away
REFLOW_MS = 300        # the other icons closing up
PAGE_GAP = 0           # the main grid spans the window: a page travels one whole screen, its own margins
                       # (80 + 80) are the gap between two pages (Ryan 2026-11-16: 「页与页之间留的缝隙大一点」)
PAGE_GAP_GROUP = 80    # the same inside a group's panel


class DragRail(QWidget):
    """While an app icon is dragged in the main grid, a list stands at each side of the screen, in the
    margin beside the icons (Ryan 2026-11-16: 「在左侧显示所有的文件夹的 list，然后拖入对应的文件夹就
    可以直接分组……也应该是液态玻璃的，你设计一下」): one strip of system glass (corner 16), in it the
    groups one under the other — each its small tile and its name — and "new group" last. Dropping the
    icon on one puts the app into that group; the grid itself stays for sorting. Too many to fit: the
    list moves by itself while the icon is held near its top / bottom end."""

    def __init__(self, launcher, side):
        super().__init__(launcher)
        self.launcher = launcher
        self.side = side              # -1: left of the grid, +1: right
        self.items = []               # {'kind': 'group', 'group': g} / {'kind': 'new'}
        self._hover = -1
        self._scroll = 0
        self._alpha = 1.0
        self._home = QPoint(0, 0)
        self._showing = False
        self.setAcceptDrops(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(RAIL_MS)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_slide)
        self._anim.finished.connect(self._on_slide_finished)
        self._scroll_timer = QTimer(self)
        self._scroll_timer.setInterval(16)
        self._scroll_timer.timeout.connect(self._auto_scroll)
        self._scroll_dir = 0
        self.hide()

    # ── content ──
    def set_items(self, items):
        self.items = list(items)
        self._hover = -1
        self._scroll = 0
        self.update()

    def content_height(self) -> int:
        return RAIL_PAD * 2 + len(self.items) * RAIL_ITEM_H

    def max_scroll(self) -> int:
        return max(0, self.content_height() - self.height())

    def item_rect(self, index) -> QRect:
        return QRect(0, RAIL_PAD + index * RAIL_ITEM_H - self._scroll, self.width(), RAIL_ITEM_H)

    def item_at(self, pos) -> int:
        index = (pos.y() + self._scroll - RAIL_PAD) // RAIL_ITEM_H
        return int(index) if 0 <= index < len(self.items) and 0 <= pos.x() < self.width() else -1

    def hover_index(self) -> int:
        return self._hover

    # ── coming / going ──
    def place(self, home: QPoint, height: int):
        self._home = QPoint(home)
        self.setFixedSize(RAIL_WIDTH, max(RAIL_ITEM_H + RAIL_PAD * 2, int(height)))

    def _away(self) -> QPoint:
        return QPoint(self._home.x() + self.side * (RAIL_WIDTH + 24), self._home.y())

    def slide_in(self):
        self._showing = True
        start = self._anim.currentValue() if self._anim.state() == QAbstractAnimation.State.Running else 0.0
        self._anim.blockSignals(True)
        self._anim.stop()
        self._anim.setStartValue(float(start or 0.0))
        self._anim.setEndValue(1.0)
        self._anim.blockSignals(False)
        self._on_slide(float(start or 0.0))
        self.show()
        self.raise_()
        glass = raspberry_ui.under_glass(self, RAIL_RADIUS)
        if glass is not None:
            glass.set_opacity(self._alpha)
        self._anim.start()

    def slide_out(self):
        if not self.isVisible():
            return
        self._showing = False
        self._scroll_timer.stop()
        self._hover = -1
        self._anim.blockSignals(True)
        self._anim.stop()
        self._anim.setStartValue(float(self._alpha))
        self._anim.setEndValue(0.0)
        self._anim.blockSignals(False)
        self._anim.start()

    def _on_slide(self, value):
        t = max(0.0, min(1.0, float(value)))
        self._alpha = t
        away = self._away()
        self.move(int(round(away.x() + (self._home.x() - away.x()) * t)), self._home.y())
        glass = getattr(self, '_broccoli_child_glass', None)
        if glass is not None:
            glass.set_opacity(t)
        self.update()

    def _on_slide_finished(self):
        if not self._showing:
            self.hide()

    # ── the drag ──
    def dragEnterEvent(self, event):
        if event.mimeData().hasText() and self._showing:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        pos = event.position().toPoint()
        self._scroll_dir = 0
        if self.max_scroll() > 0:
            if pos.y() < 36 and self._scroll > 0:
                self._scroll_dir = -1
            elif pos.y() > self.height() - 36 and self._scroll < self.max_scroll():
                self._scroll_dir = 1
        if self._scroll_dir and not self._scroll_timer.isActive():
            self._scroll_timer.start()
        elif not self._scroll_dir:
            self._scroll_timer.stop()
        self._last_pos = pos
        self._set_hover(self.item_at(pos))
        if self._hover >= 0:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._scroll_timer.stop()
        self._set_hover(-1)
        event.accept()

    def dropEvent(self, event):
        self._scroll_timer.stop()
        pos = event.position().toPoint()
        index = self.item_at(pos)
        self._set_hover(-1)
        if index < 0:
            event.ignore()
            return
        event.acceptProposedAction()
        self.launcher.rail_drop(self.items[index], event.mimeData().text(), self.mapTo(self.launcher, pos))

    def _auto_scroll(self):
        self._scroll = max(0, min(self.max_scroll(), self._scroll + self._scroll_dir * 8))
        self._set_hover(self.item_at(getattr(self, '_last_pos', QPoint(-1, -1))))
        self.update()
        if self._scroll in (0, self.max_scroll()):
            self._scroll_timer.stop()

    def _set_hover(self, index):
        if index != self._hover:
            self._hover = index
            self.update()

    # ── looks ──
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setOpacity(self._alpha)
        palette = raspberry_ui.ui_palette()
        dark = palette['dark']
        whole = QRectF(self.rect())
        shape = QPainterPath()
        shape.addRoundedRect(whole, RAIL_RADIUS, RAIL_RADIUS)
        if not raspberry_ui.glass_active(self):          # no system glass: the same shape, painted
            painter.setPen(QPen(palette['border'], 1.0))
            painter.setBrush(palette['capsule'])
            painter.drawRoundedRect(whole.adjusted(0.5, 0.5, -0.5, -0.5), RAIL_RADIUS, RAIL_RADIUS)
        painter.setClipPath(shape)
        font = painter.font()
        font.setPixelSize(10)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        accent = raspberry_ui.accent_color()
        for index, item in enumerate(self.items):
            rect = self.item_rect(index)
            if rect.bottom() < 0 or rect.top() > self.height():
                continue
            hot = index == self._hover
            if hot:                                       # where the icon would go: the accent colour
                wash = QColor(accent)
                wash.setAlpha(60 if dark else 46)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(wash)
                # as wide a band of it left and right of the tile as above it and under the name
                painter.drawRoundedRect(QRectF(rect).adjusted(5, 1.5, -5, -4), 13, 13)
            side = RAIL_TILE + (4 if hot else 0)
            tile = QRectF(rect.left() + (rect.width() - side) / 2.0, rect.top() + 10 - (2 if hot else 0), side, side)
            radius = side * 0.225
            painter.setPen(QPen(accent, 1.5) if hot else QPen(QColor(255, 255, 255, 70 if dark else 110), 1.0))
            painter.setBrush(QColor(255, 255, 255, 30 if dark else 62))
            painter.drawRoundedRect(tile, radius, radius)
            if item['kind'] == 'group':
                pixmap = item['group']['icon'].pixmap(int(side * 2), int(side * 2))
                painter.drawPixmap(tile.toRect(), pixmap)
                name = item['group']['name']
            elif item['kind'] == 'page':
                number_font = QFont(font)
                number_font.setPixelSize(20)
                number_font.setBold(item['page'] == self.launcher.current_page)   # the page on screen: bold
                painter.setFont(number_font)
                painter.setPen(QColor(palette['text']))
                painter.drawText(tile.toRect(), int(Qt.AlignmentFlag.AlignCenter), str(item['page'] + 1))
                painter.setFont(font)
                name = self.launcher.page_label(item['page'])
            else:
                pen = QPen(QColor(palette['text']), 2.0)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                c, arm = tile.center(), side * 0.2
                painter.drawLine(QPointF(c.x() - arm, c.y()), QPointF(c.x() + arm, c.y()))
                painter.drawLine(QPointF(c.x(), c.y() - arm), QPointF(c.x(), c.y() + arm))
                name = self.launcher.new_group_label() if item['kind'] == 'new' else self.launcher.page_label()
            painter.setPen(QColor(palette['text']))
            text = metrics.elidedText(name, Qt.TextElideMode.ElideRight, self.width() - 14)
            painter.drawText(QRect(rect.left() + 7, rect.top() + 10 + RAIL_TILE + 5, rect.width() - 14, 14),
                             int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop), text)
        # more above / below: the list fades out at that end
        for more, top in ((self._scroll > 0, True), (self._scroll < self.max_scroll(), False)):
            if more:
                painter.setPen(QColor(palette['secondary']))
                y = 6 if top else self.height() - 6
                painter.drawText(QRect(0, y - 6, self.width(), 12), int(Qt.AlignmentFlag.AlignCenter), '⌃' if top else '⌄')
        painter.end()


class PageSlide(QObject):
    """Turning a page the way the system's launcher does (Ryan 2026-11-16: 「整体向左移，右边新的页面
    一起进来」): the page on screen and the page coming in are one strip. Both move together — under the
    fingers, or on their own — and the page that comes in is made of the real buttons, which simply
    stay when the strip stops (nothing is swapped at the end, so nothing jumps).

    The host (the launcher / an open group) gives:
      current_page, slide_page_count(), slide_duration(width), slide_gap(),
      slide_start()            → the buttons of the page on screen (at their places),
      slide_build(page)        → the buttons of another page, at their places, not shown yet,
      slide_commit(page, btns) → that page is now the page on screen, made of these buttons."""

    FOLLOW_RELEASE_MS = 300   # no more wheel events for this long = the fingers are off

    def __init__(self, host, grid):
        super().__init__(host)
        self.host, self.grid = host, grid
        self._old = []          # (button, home) of the page on screen
        self._near = {}         # +1 (the page after) / -1 (the page before) → [(button, home)]
        self._near_page = {}
        self._offset = 0.0      # how far the strip is from rest; negative = moved left
        self._accum = 0
        self._width = 0
        self._active = False
        self._target = None     # (direction, page) while the strip runs to another page
        self._anim = QVariantAnimation(self)
        self._anim.valueChanged.connect(self._on_value)
        self._anim.finished.connect(self._on_finished)
        self._release = QTimer(self)
        self._release.setSingleShot(True)
        self._release.timeout.connect(self.release)

    # ── state ──
    def active(self) -> bool:
        return self._active

    def running(self) -> bool:
        return self._anim.state() == QAbstractAnimation.State.Running

    def offset(self) -> float:
        return self._offset

    def page_width(self) -> int:
        return self._width or self.grid.width()

    def incoming(self, direction):
        return [button for button, _home in self._near.get(direction, ())]

    @staticmethod
    def _alive(button) -> bool:
        return button is not None and not sip.isdeleted(button)

    def _begin(self):
        if self._active:
            return
        self._active = True
        # one page = the grid's width + the gap the host wants between two pages
        self._width = max(1, self.grid.width() + int(self.host.slide_gap()))
        self._offset, self._accum = 0.0, 0
        self._old = [(button, button.pos()) for button in self.host.slide_start() if self._alive(button)]

    def _ensure(self, direction, page=None) -> bool:
        """The page on that side exists as buttons (built the first time the strip moves that way)."""
        if page is None:
            page = self.host.current_page + direction
        if direction in self._near:
            if self._near_page.get(direction) == page:
                return True
            self._drop(direction)
        if not 0 <= page < self.host.slide_page_count():
            return False
        buttons = [button for button in (self.host.slide_build(page) or []) if self._alive(button)]
        if not buttons:
            return False
        items = [(button, button.pos()) for button in buttons]
        shift = int(round(self._offset)) + direction * self._width
        for button, home in items:
            button.move(home.x() + shift, home.y())
            button.show()
        self._near[direction], self._near_page[direction] = items, page
        return True

    def _drop(self, direction):
        for button, _home in self._near.pop(direction, ()):
            if self._alive(button):
                safe_delete_widget(button)
        self._near_page.pop(direction, None)

    def _place(self):
        x = int(round(self._offset))
        for button, home in self._old:
            if self._alive(button):
                button.move(home.x() + x, home.y())
        for direction, items in self._near.items():
            shift = x + direction * self._width
            for button, home in items:
                if self._alive(button):
                    button.move(home.x() + shift, home.y())
        # the system glass under the group tiles moves at once, what Qt draws only on its next turn:
        # draw now, so that the two stay together
        if self.grid.isVisible():
            self.grid.repaint()

    def _reset(self):
        self._anim.stop()
        self._release.stop()
        for direction in list(self._near):
            self._drop(direction)
        self._old = []
        self._offset, self._accum = 0.0, 0
        self._active = False
        self._target = None
        self.host._is_animating = False

    def abandon(self):
        """The page is being laid out again by someone else: forget the strip (the buttons of the page
        on screen are the caller's business, the ones coming in are removed)."""
        if self._active or self._near or self.running():
            self._reset()

    # ── under the fingers ──
    def wheel(self, dx, momentum=False):
        if self._target is not None or self.running():
            return
        if not self._active and momentum:
            return              # what is left of the last flick: not the start of a new drag
        self._begin()
        self._accum += int(dx)
        direction = 1 if self._accum < 0 else -1
        if abs(self._accum) >= self.grid.width() // 2:
            # half a page: go on by itself (one page at a time); at the first / last page, back
            self._release.stop()
            self._offset = float(self._accum)
            if not self._ensure(direction):
                self._animate(0.0, 180, QEasingCurve.Type.OutCubic)
            else:
                remaining = abs(-direction * self._width - self._accum)
                self._run(direction, min(240, 160 + int(min(remaining, self._width) * 0.25)))
            return
        if self._accum:
            self._ensure(direction)
        self._offset = float(self._accum)
        self._place()
        self._release.start(self.FOLLOW_RELEASE_MS)

    def release(self):
        """The fingers are off before half a page: back to where it was."""
        if not self._active or self._target is not None or self.running():
            return
        self._animate(0.0, 200, QEasingCurve.Type.InBounce)

    # ── on its own ──
    def go(self, page, direction) -> bool:
        """Slide to `page`, which comes in from the right (direction +1) or the left (-1)."""
        if self._target is not None:
            return False
        self._anim.stop()
        self._release.stop()
        self._begin()
        if not self._ensure(direction, page):
            self._reset()
            return False
        self._run(direction, self.host.slide_duration(self._width))
        return True

    def _run(self, direction, duration):
        self._target = (direction, self._near_page[direction])
        self.host._is_animating = True
        self._animate(float(-direction * self._width), duration, QEasingCurve.Type.OutCubic)

    def _animate(self, end, duration, easing):
        start = float(self._offset)
        # (setting up an animation that has run before reports values of the old run: not ours)
        self._anim.blockSignals(True)
        self._anim.stop()
        self._anim.setDuration(max(1, int(duration)))
        self._anim.setEasingCurve(easing)
        self._anim.setStartValue(start)
        self._anim.setEndValue(float(end))
        self._anim.setCurrentTime(0)
        self._anim.blockSignals(False)
        self._offset = start
        self._anim.start()

    def _on_value(self, value):
        if not self._active:
            return
        self._offset = float(value)
        self._place()

    def _on_finished(self):
        if not self._active:
            return
        target = self._target
        if target is None:      # came back: the page on screen stays, the neighbours go
            self._offset = 0.0
            self._place()
            self._reset()
            return
        direction, page = target
        items = self._near.pop(direction, [])
        self._near_page.pop(direction, None)
        buttons = []
        for button, home in items:
            if self._alive(button):
                button.move(home)
                buttons.append(button)
        self._reset()
        self.host.slide_commit(page, buttons)


GROUP_CHROME_LEVELS = (          # (above the title, the title, under the dots, at the sides)
    (40, 100, 60, 60),            # roomy: as designed
    (24, 64, 34, 44),
    (12, 44, 18, 28),             # tight: small screens
)
GROUP_DOTS_ROOM = 40              # the page dots' row
GROUP_CELL_MIN = 64


def group_panel_fit(room_w, room_h, count, wanted_cell):
    """How an open group is laid out in a room of room_w × room_h for `count` apps: the icons' cell,
    the rows shown at once, and the panel's own measures. Tries, in this order, to keep: every row on
    one page, the roomy title and edges, the launcher's icon size."""
    wanted_rows = max(1, min((count + GRID_COLS - 1) // GRID_COLS, GRID_ROWS))

    def cell_for(rows, level):
        top, title, bottom, side = level
        chrome = top + title + GROUP_DOTS_ROOM + bottom
        by_height = (room_h - chrome) // rows - 10
        by_width = int(((room_w - 2 * side) * CELL_FULL) // (GRID_COLS * 120 + (GRID_COLS - 1) * 32))
        return min(int(wanted_cell), by_height, by_width), chrome

    best = None
    for rows in range(wanted_rows, 0, -1):
        for level in GROUP_CHROME_LEVELS:
            cell, chrome = cell_for(rows, level)
            if cell >= GROUP_CELL_MIN:
                # roomy measures only when they do not cost icon size
                if best is None or cell > best['cell']:
                    best = dict(rows=rows, cell=cell, chrome=chrome, top=level[0], title=level[1],
                                bottom=level[2], side=level[3], wanted_rows=wanted_rows)
                if cell >= int(wanted_cell):
                    return best
        if best is not None:
            return best
    level = GROUP_CHROME_LEVELS[-1]
    cell, chrome = cell_for(1, level)
    return dict(rows=1, cell=max(40, cell), chrome=chrome, top=level[0], title=level[1], bottom=level[2],
                side=level[3], wanted_rows=wanted_rows)


class GroupWidget(QWidget):
    closed = pyqtSignal()
    def __init__(self, group, parent=None, main_window=None, close_group_widget=None):
        super().__init__(parent)
        self.group = group
        self.main_window = main_window
        self.close_group_widget = close_group_widget
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # The panel fits the room it has (Ryan 2026-11-16, like Broccoli's window: 「组的框框会太大然后
        # 显示不全……希望能自动适配」): the window without the Dock / the menu bar. Its icons are the
        # launcher's size when that fits; else, in this order: smaller icons, a tighter title and edges,
        # fewer rows per page (the rest on further pages) — never a panel larger than the room.
        if main_window is not None and hasattr(main_window, 'group_available_rect'):
            room = main_window.group_available_rect().size()
        else:
            room = (main_window.size() if main_window is not None else QGuiApplication.primaryScreen().availableGeometry().size())
        fit = group_panel_fit(room.width(), room.height(), len(group['apps']), cell_size())
        apps_per_row = GRID_COLS
        padding_lr = fit['side']
        rows = fit['rows']
        cell = fit['cell']
        chrome_height = fit['chrome']
        self._fit = fit
        self._cell = cell
        self._btn_pitch = int(round(152 * cell / float(CELL_FULL)))
        self._row_height = cell + 10
        row_height = self._row_height
        content_width = (apps_per_row - 1) * self._btn_pitch + int(round(120 * cell / float(CELL_FULL)))
        group_width = content_width + 2 * padding_lr
        group_height = chrome_height + rows * row_height
        self._full_size = QSize(group_width, group_height)
        self._morph_t = 1.0
        self._morph_picture = None
        self.setFixedSize(group_width, group_height)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(padding_lr-8, fit['top'], padding_lr-8, fit['bottom'])
        self.layout.setSpacing(0)
        self.name_label = QLabel(group['name'])
        self.name_label.setFont(QFont("Arial", 20 if fit['title'] >= 64 else 16))
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setFixedHeight(fit['title'])
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
        self.grid_widget.setMinimumHeight(rows * row_height)
        self.grid_widget.setMinimumWidth(content_width)
        self.layout.addWidget(self.grid_widget)

        self.grid_layout = QGridLayout(self.grid_widget)

        self.page_indicator = QHBoxLayout()
        self.page_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_indicator.setContentsMargins(0, 0, 0, 0)

        self.page_indicator_widget = QWidget()
        self.page_indicator_widget.setStyleSheet('''
            background-color: transparent;
            border: 0px;
        ''')
        self.page_indicator_widget.setLayout(self.page_indicator)
        self.page_indicator_widget.setMaximumWidth(content_width)
        self.page_indicator_widget.setFixedHeight(40)
        self.page_indicator_widget.setMinimumWidth(60)
        # the page dots: one glass capsule (style book 5.13)
        self.dots = raspberry_ui.PageDots()
        self.dots.set_max_width(content_width)
        self.dots.pageClicked.connect(self.goto_page)
        self.page_indicator.addWidget(self.dots)
        self.layout.addWidget(self.page_indicator_widget, alignment=Qt.AlignmentFlag.AlignHCenter)

        # the panel itself is drawn by this widget (paintEvent): system glass under it, or the frosted
        # fallback; the content sits in a plain container
        w3 = QWidget(self)
        w3.setLayout(self.layout)
        w3.setGeometry(0, 0, group_width, group_height)  # no layout around it: the panel can be any size
        self._content = w3                               # while it grows / shrinks (begin_morph)
        self._panel_glass = None
        self._frost = None

        self.current_page = 0
        self.items_per_page = GRID_COLS * (GRID_ROWS if fit['rows'] >= fit['wanted_rows'] else fit['rows'])
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
        self._is_animating = False
        self._page_slide = PageSlide(self, self.grid_widget)

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

    def paintEvent(self, event):
        painter = QPainter(self)
        raspberry_ui.paint_folder_panel(self, painter, self._frost)
        if self._morph_picture is not None:
            # growing / shrinking: the content as one picture, scaled with the panel; it comes in after
            # the panel has started to grow and is gone before it has shrunk into the tile
            alpha = max(0.0, min(1.0, (self._morph_t - 0.25) / 0.6))
            if alpha > 0.0:
                painter.setOpacity(alpha)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                painter.drawPixmap(self.rect(), self._morph_picture)
        painter.end()

    # ── growing out of the group's tile / shrinking back into it ──
    def full_size(self) -> QSize:
        return QSize(self._full_size)

    def morph_radius(self) -> float:
        """The corner now: the tile's at the start, the panel's when open."""
        start = tile_radius()
        return start + (raspberry_ui.PANEL_GLASS_RADIUS - start) * max(0.0, min(1.0, self._morph_t))

    def begin_morph(self, progress):
        """From now the panel may have any size: its content is shown as one scaled picture."""
        full = self._full_size
        self._content.setGeometry(0, 0, full.width(), full.height())
        if self._content.layout() is not None:
            self._content.layout().activate()
        # the content alone on a clear background (grab() would paint the window's background under it)
        ratio = max(1.0, float(self.devicePixelRatioF()))
        picture = QPixmap(int(full.width() * ratio), int(full.height() * ratio))
        picture.setDevicePixelRatio(ratio)
        picture.fill(Qt.GlobalColor.transparent)
        self._content.render(picture, QPoint(0, 0), QRegion(), QWidget.RenderFlag.DrawChildren)
        self._morph_picture = picture
        self._content.hide()
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        self._morph_t = float(progress)
        self.update()

    def set_morph(self, progress):
        self._morph_t = max(0.0, min(1.0, float(progress)))
        if self._panel_glass is not None:
            self._panel_glass.set_progress(self._morph_t)
        self.update()

    def end_morph(self):
        """Open: the real content takes over from its picture."""
        self._morph_t = 1.0
        self._morph_picture = None
        if self._panel_glass is not None:
            self._panel_glass.set_progress(1.0)
        self.setFixedSize(self._full_size)
        self._content.setGeometry(0, 0, self._full_size.width(), self._full_size.height())
        self._content.show()
        self.update()

    def is_morphing(self) -> bool:
        return self._morph_picture is not None

    def attach_panel_glass(self):
        """System glass under the panel, with the picture of the dimmed icons right under the glass
        (style book 5.13). Without glass: the blurred picture of the icons for the painted panel."""
        launcher = self.main_window
        if self._panel_glass is not None or launcher is None:
            return
        sources = [launcher.main_content]
        self._panel_glass = raspberry_ui.FolderPanelGlass(self, launcher, sources, picture=launcher.scrim.picture())
        if not self._panel_glass.active():
            self._frost = raspberry_ui.frosted_under(launcher, sources, launcher.group_panel_rect(self))

    def refresh_panel_glass(self):
        """The grid behind the panel was rebuilt: take its picture again, and keep the panel's glass
        (and the glass of what is on the panel) above the glass of the new icons."""
        if self._panel_glass is None or not self._panel_glass.active():
            return
        self._panel_glass.retake(picture=self.main_window.scrim.picture())
        self._panel_glass.raise_views()
        for child in self.findChildren(QWidget):
            helper = getattr(child, '_broccoli_child_glass', None)
            if helper is not None and hasattr(helper, 'raise_views'):
                helper.raise_views()

    def display_apps(self, apps, page=0, prebuilt=None):
        """Lay the page out. `prebuilt`: the page's buttons already exist (they slid in): keep them."""
        grid_layout = self.grid_layout
        grid_widget = self.grid_widget
        slide = getattr(self, '_page_slide', None)
        if slide is not None and prebuilt is None:
            slide.abandon()
        keep = set(id(w) for w in (prebuilt or ()))

        # 先移除布局项
        for i in reversed(range(grid_layout.count())):
            w = grid_layout.itemAt(i).widget()
            try:
                if w is not None:
                    w.hide()            # first: else Qt's pending "show" makes it a window of its own
                    w.setParent(None)
                    w.deleteLater()
            except RuntimeError:
                pass

        # 再保险：删除 grid_widget 下残留子控件，但跳过 overlay
        for w in grid_widget.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
            if w.objectName() == "insertOverlay" or id(w) in keep:
                continue
            try:
                w.hide()            # first: else Qt's pending "show" makes it a window of its own
                w.setParent(None)
                w.deleteLater()
            except RuntimeError:
                pass
        if prebuilt is None:
            for btn in self._make_page_buttons(apps, page):
                btn.show()
        self.update_page_indicator(len(apps))

        self.focus_index = -1
        self.focused_btn = None

    def display_apps_animated(self, apps, page):
        """An icon left the group: the ones after it slide into the gap."""
        before = {}
        for button in self.grid_widget.findChildren(AppButton):
            if button.isVisible():
                before[button.app_info['path']] = button.pos()
        page = max(0, min(page, (len(apps) - 1) // self.items_per_page if apps else 0))
        self.current_page = page
        self.display_apps(apps, page)
        self._reflow = []
        for button in self.grid_widget.findChildren(AppButton):
            old = before.get(button.app_info['path'])
            if old is None or old == button.pos():
                continue
            anim = QPropertyAnimation(button, b"pos", button)
            anim.setDuration(REFLOW_MS)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.setStartValue(old)
            anim.setEndValue(button.pos())
            button.move(old)
            anim.start()
            self._reflow.append(anim)

    def _make_page_buttons(self, apps, page):
        """The buttons of one page, each at its place in the grid (not shown yet)."""
        apps_per_row = 7
        start = page * self.items_per_page
        buttons = []
        for idx, app in enumerate(apps[start:start + self.items_per_page]):
            row, col = divmod(idx, apps_per_row)
            btn = AppButton(app, self, parent_group=self.group, main_window=self.main_window, cell=self._cell)
            btn.setParent(self.grid_widget)
            btn.move(col * self._btn_pitch, row * self._row_height)
            buttons.append(btn)
        return buttons

    def update_page_indicator(self, total_items):
        total_pages = max(1, (total_items + self.items_per_page - 1) // self.items_per_page)
        self.dots.set_pages(total_pages, self.current_page)
        self.page_indicator_widget.setFixedWidth(max(60, self.dots.width()))

    def goto_page(self, page):
        total_pages = self.slide_page_count()
        if page < 0 or page >= total_pages or page == self.current_page:
            return
        if getattr(self, "_is_animating", False):
            return
        direction = 1 if page > self.current_page else -1
        if not self.isVisible() or not self._page_slide.go(page, direction):
            self.goto_page_immediate(page)
            return
        # as before, the page counts as turned from the start of the slide
        self.current_page = page
        self.update_page_indicator(len(self.group['apps']))

    # ── what the page strip (PageSlide) asks of this panel ──
    def slide_page_count(self):
        return max(1, (len(self.group['apps']) + self.items_per_page - 1) // self.items_per_page)

    def slide_duration(self, width):
        return max(160, min(300, int(width / 6000 * 1000)))

    def slide_gap(self):
        return PAGE_GAP_GROUP

    def slide_start(self):
        return [w for w in self.grid_widget.findChildren(AppButton)]

    def slide_build(self, page):
        return self._make_page_buttons(self.group['apps'], page)

    def slide_commit(self, page, buttons):
        self.current_page = page
        self.display_apps(self.group['apps'], page, prebuilt=buttons)

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
        if self.main_window:
            new_name = self.main_window.unique_group_name(new_name, self.group)
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
            raspberry_ui.focus_ring_qss()
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
            raspberry_ui.focus_ring_qss()
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
            raspberry_ui.focus_ring_qss()
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
            raspberry_ui.focus_ring_qss()
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
            # the page on screen and the one coming in move together under the fingers (PageSlide)
            self._page_slide.wheel(dx, event.phase() == Qt.ScrollPhase.ScrollMomentum)
            event.accept()
            return

        # 正在触控板滑动会话时，忽略垂直滚动，避免干扰
        if self._page_slide.active():
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
        self.main_window.refresh_group_tile(self.group)
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
        self.main_window.refresh_group_tile(self.group)
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
                raspberry_ui.focus_ring_qss()
            )
            self.focus_index = rel_idx
            self.setFocus()

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

    def goto_page_immediate(self, page: int):
        total_pages = max(1, (len(self.group['apps']) + self.items_per_page - 1) // self.items_per_page)
        if page < 0 or page >= total_pages:
            return
        self.current_page = page
        self.display_apps(self.group['apps'], self.current_page)


class MainContentWidget(QWidget):
    def set_content_margins(self, margins):
        """(left, top, right, bottom) around the content. The grid itself spans the whole width of the
        window — a page that is turned slides right to the edge of the screen before it is gone (Ryan
        2026-11-16) — so the left / right margins are kept inside the grid (grid_side_insets)."""
        left, top, right, bottom = [int(v) for v in margins]
        self.side_margins = (left, right)
        self.content_layout.setContentsMargins(0, top, 0, bottom)
        grid_margins = self.grid_layout.contentsMargins()
        self.grid_layout.setContentsMargins(left, grid_margins.top(), right, grid_margins.bottom())

    def content_margins(self):
        m = self.content_layout.contentsMargins()
        return QMargins(self.side_margins[0], m.top(), self.side_margins[1], m.bottom())

    def __init__(self, parent, apps, groups, main_window):
        super().__init__(parent)
        self.setGeometry(parent.geometry())
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
        # the five rows share the grid's height equally, whatever is in them (fit_cells / display_apps)
        _gm = self.grid_layout.contentsMargins()
        self.grid_layout.setContentsMargins(_gm.left(), 0, _gm.right(), 0)
        self.grid_side_margin = max(_gm.left(), _gm.right())
        self.grid_layout.setVerticalSpacing(0)

        self.page_indicator = QHBoxLayout()
        self.page_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.page_indicator_widget = QWidget()
        self.page_indicator_widget.setLayout(self.page_indicator)
        self.page_indicator_widget.setMaximumWidth(800)
        self.page_indicator_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        # the page dots: one glass capsule (style book 5.13)
        self.dots = raspberry_ui.PageDots()
        self.dots.set_max_width(760)
        self.dots.pageClicked.connect(main_window.goto_page)
        self.page_indicator.addWidget(self.dots)

        # the launcher's backdrop (the blurred clean wallpaper) lies under everything; this is a plain,
        # transparent container
        w3 = QWidget()
        blay3 = QVBoxLayout()
        self.content_layout = blay3  # the bottom / side margins follow the Dock (apply_dock_insets)
        self.side_margins = (0, 0)
        self.set_content_margins(raspberry_ui.content_margins((0, 0, 0)))
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
            return self.main_window._page_items(self.main_window.current_page)

        def _cell_rect(row, col):
            item = self.grid_layout.itemAtPosition(row, col)
            widget = item.widget() if item is not None else None
            return QRect(widget.geometry()) if widget is not None else None

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
            enable_drag=True,  # dropping an icon between two others sorts it there (Ryan 2026-11-16)
            cell_rect=_cell_rect
        )


class LaunchpadWindow(QWidget):
    def __init__(self, apps):
        super().__init__()
        self.compact_mode = self.read_compact_mode_setting()  # or False

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(1)
        self._mouse_press_pos = None
        self._mouse_move_pos = None

        self.apps = apps
        self.display_name_map = load_display_name_map()
        self.alias_name_map = load_alias_name_map()
        self.groups = load_groups(self.apps)
        self.current_page = 0
        self.items_per_page = 35
        self._page_sizes = None
        try:
            with open(setting_path("independent_pages"), "r") as f:
                self.independent_pages = f.read().strip() == "1"
        except Exception:
            self.independent_pages = False
        try:
            with open(PAGES_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self._saved_pages = {k: v for k, v in loaded.items() if isinstance(v, int)} if isinstance(loaded, dict) else {}
        except Exception:
            self._saved_pages = {}
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
        # the backdrop: the blurred clean wallpaper (style book 5.13); the dimming behind an open group
        self.backdrop = raspberry_ui.LauncherBackdrop(self)
        self.backdrop.clean = self.read_clean_wallpaper_setting()
        self.backdrop.changed.connect(self.update)
        # the system menu bar is covered while the launcher is up (Ryan 2026-11-21: as the system's Launchpad)
        self.menu_bar_cover = raspberry_ui.MenuBarCover(self, self.backdrop)
        self.scrim = raspberry_ui.FolderScrim(self)
        self.scrim.levelChanged.connect(self._veil_group_tiles)
        self.scrim.levelChanged.connect(lambda _level: self.menu_bar_cover.set_dim(self.scrim.colour()))
        QTimer.singleShot(1500, raspberry_ui.warm_panel_shadow)
        raspberry_ui.on_theme(self._on_theme_changed)
        # a Dock that is showing: the content keeps clear of it (Ryan 2026-11-16)
        self._dock_insets = (0, 0, 0)
        for _screen in QGuiApplication.screens():
            self._watch_screen(_screen)
        QGuiApplication.instance().screenAdded.connect(self._watch_screen)
        # the wallpaper of the screen the mouse is on is fetched now, in the background: the first opening
        # of the launcher does not wait for it
        _start_screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        if _start_screen is not None:
            self.backdrop.warm(_start_screen.geometry())
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

        # the backdrop: only the wallpaper, or whatever is behind the window
        self.clean_wallpaper_action = QAction(self.tr("🖼 Blur the wallpaper only"), self)
        self.clean_wallpaper_action.setCheckable(True)
        self.clean_wallpaper_action.setChecked(self.backdrop.clean)
        self.clean_wallpaper_action.triggered.connect(self.toggle_clean_wallpaper)
        self.menu.addAction(self.clean_wallpaper_action)

        # apps in the user's own Applications folder (off unless switched on)
        self.user_apps_action = QAction(self.tr("👤 Also show apps in my own Applications folder"), self)
        self.user_apps_action.setCheckable(True)
        self.user_apps_action.setChecked(user_apps_enabled())
        self.user_apps_action.triggered.connect(self.toggle_user_apps)
        self.menu.addAction(self.user_apps_action)

        # every page keeps its own icons / one long row cut into pages
        self.independent_pages_action = QAction(self.tr("📄 Keep every page on its own"), self)
        self.independent_pages_action.setCheckable(True)
        self.independent_pages_action.setChecked(self.independent_pages)
        self.independent_pages_action.triggered.connect(self.toggle_independent_pages)
        self.menu.addAction(self.independent_pages_action)

        # the apps hidden from the launcher (right-click an app › Hide in Raspberry): show them again here
        self.hidden_apps_menu = QMenu(self.tr("🙈 Hidden apps"), self)
        self.hidden_apps_menu.aboutToShow.connect(self.fill_hidden_apps_menu)
        self.menu.addMenu(self.hidden_apps_menu)
        self.fill_hidden_apps_menu()

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
        self._always_hide_dock_file = setting_path("hide_dock")
        self._always_hide_dock = self.read_always_hide_dock_setting()
        self.always_hide_dock_action.setChecked(self._always_hide_dock)
        # 新增 Show Dock 开关
        self.show_dock_action = QAction(self.tr("🪟 Always show Dock"), self)
        self.show_dock_action.setCheckable(True)
        self.show_dock_action.setChecked(False)  # 默认不勾选
        self.show_dock_action.triggered.connect(self.toggle_show_dock)
        self.menu.addAction(self.show_dock_action)
        self._show_dock_file = setting_path("show_dock")
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
        # every Space (as Broccoli's "Show on all Spaces"; Ryan 2026-11-19)
        self.all_spaces_action = QAction(self.tr("🖥 Show on all Spaces"), self)
        self.all_spaces_action.setCheckable(True)
        self._show_on_all_spaces = self.read_all_spaces_setting()
        self.all_spaces_action.setChecked(self._show_on_all_spaces)
        self.all_spaces_action.triggered.connect(self.toggle_show_on_all_spaces)
        self.menu.addAction(self.all_spaces_action)
        raspberry_ui.set_all_spaces(self._show_on_all_spaces)
        # True while the marks are the ones put on before the Dock icon appeared (they reach full-screen Spaces)
        self._spaces_marks_from_birth = False
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
        # Raspberry's tools in any other AI app that speaks MCP (2026-11-24): copies the setup lines
        self.menu.addSeparator()
        self.ai_apps_action = QAction(self.tr("🔌 Use in other AI apps…"), self)
        self.menu.addAction(self.ai_apps_action)
        self.ai_apps_action.triggered.connect(self.copy_ai_apps_setup)

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

        # a newer version? asked 3 s after the start and once a day (in a background thread); the update
        # window comes up by itself when one is out, or when the last install left something to say
        self.update_check_timer = QTimer(self)
        self.update_check_timer.setInterval(86400 * 1000)
        self.update_check_timer.timeout.connect(lambda: self.win_update.checkupdate(popup_when_ready=True))
        self.update_check_timer.start()
        QTimer.singleShot(3000, lambda: self.win_update.checkupdate(popup_when_ready=True))

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
        self._page_slide = PageSlide(self, self.main_content.grid_widget)
        self._flyers = []     # icons on their way into / out of a group
        self._drag_rails = []  # the lists at the two sides while an icon is dragged
        self._entrance = None
        self._reflow = []     # icons sliding to their new places


        self.setFocus()

    # ── the backdrop, light / dark (style book 5.13) ──
    def paint_backdrop(self, painter, rect):
        self.backdrop.paint_fallback(painter, rect)

    def paintEvent(self, event):
        painter = QPainter(self)
        self.paint_backdrop(painter, self.rect())
        painter.end()

    def read_clean_wallpaper_setting(self):
        try:
            with open(setting_path("clean_wallpaper"), "r") as f:
                return f.read().strip() != "0"
        except Exception:
            return True

    def write_clean_wallpaper_setting(self, enabled: bool):
        try:
            with open(setting_path("clean_wallpaper"), "w") as f:
                f.write("1" if enabled else "0")
        except Exception:
            pass

    def toggle_clean_wallpaper(self):
        enabled = self.clean_wallpaper_action.isChecked()
        self.write_clean_wallpaper_setting(enabled)
        self.backdrop.clean = enabled
        if self.isVisible():
            self.backdrop.prepare(self.geometry())
        else:
            self.backdrop.set_clean(enabled)

    # ── the user's own Applications folder ──
    def toggle_user_apps(self):
        enabled = self.user_apps_action.isChecked()
        write_user_apps_enabled(enabled)
        if enabled:
            self.start_background_scan()      # finds them; on_new_apps_found puts them back in place
        else:
            self._remove_user_apps()

    @staticmethod
    def _load_user_app_places():
        try:
            with open(USER_APPS_MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _remove_user_apps(self):
        """Switched off: the apps of ~/Applications leave the grid and the groups (their places are
        written down, so that switching on again puts each one back)."""
        self.take_out_apps([a for a in self.apps if is_user_app_path(a['path'])])

    def take_out_apps(self, gone):
        """Apps leave the launcher without being uninstalled (hidden by the user / their folder
        switched off). Where each one was — its group, what stood before it — is written down first;
        when it is found again (put_back_apps) it returns to that place."""
        gone = [a for a in gone if a in self.apps]
        if not gone:
            return
        places = self._load_user_app_places()
        records = dict(places.get('apps') or {})
        main_ids = [obj['name'] if typ == 'group' else obj['path'] for typ, obj in self.main_order]
        for app_info in gone:
            group = next((g for g in self.groups if app_info in g['apps']), None)
            records[app_info['path']] = {
                'group': group['name'] if group is not None else None,
                'in_group': [a['path'] for a in group['apps']] if group is not None else [],
                'main': main_ids,
            }
        try:
            with open(USER_APPS_MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(dict(places, apps=records), f, ensure_ascii=False)
        except Exception:
            pass
        gone_ids = set(id(a) for a in gone)
        self.apps = [a for a in self.apps if id(a) not in gone_ids]
        self.app_dict = {a['path']: a for a in self.apps}
        for group in self.groups:
            if any(id(a) in gone_ids for a in group['apps']):
                group['apps'] = [a for a in group['apps'] if id(a) not in gone_ids]
                group['icon'] = create_group_icon(group['apps'])
        emptied = [g for g in self.groups if not g['apps']]
        self.groups[:] = [g for g in self.groups if g['apps']]
        self.main_order = [(typ, obj) for typ, obj in self.main_order
                           if not (typ == 'app' and id(obj) in gone_ids) and not (typ == 'group' and any(obj is g for g in emptied))]
        self.filtered_apps = [a for a in self.filtered_apps if id(a) not in gone_ids]
        save_app_paths(allowed_app_paths(load_app_paths()))
        if self.group_widget is not None and any(self.group_widget.group is g for g in emptied):
            self.close_group_widget()
        self.current_page = min(self.current_page, self.total_pages() - 1)
        self.sync_group_order()
        before = self._grid_snapshot() if self.isVisible() else None
        self.display_apps(self.filtered_apps, self.current_page)
        if before is not None:
            self._animate_reflow(before)
        if self.group_widget is not None:
            self.group_widget.display_apps_animated(self.group_widget.group['apps'], self.group_widget.current_page)

    @staticmethod
    def _insert_after_neighbour(sequence, ids, item, item_id, remembered):
        """Put `item` into `sequence` (whose ids are `ids`, same length) where the remembered order has
        it: right after the nearest thing before it that is still there (at the front if none is)."""
        try:
            at = remembered.index(item_id)
        except ValueError:
            return False
        for earlier in reversed(remembered[:at]):
            if earlier in ids:
                sequence.insert(ids.index(earlier) + 1, item)
                return True
        sequence.insert(0, item)
        return True

    def _restore_user_apps(self, new_apps):
        self.put_back_apps(new_apps)

    def put_back_apps(self, new_apps):
        """Apps that were taken out and are found again: each to its remembered group and place (a
        group that held nothing else and went with them comes back too). An app with nothing
        remembered stays where a new app goes (the end)."""
        places = self._load_user_app_places()
        records = dict(places.get('apps') or {})
        back = [a for a in new_apps if a['path'] in records]
        if not back:
            return
        for app_info in back:
            path = app_info['path']
            record = records.pop(path)
            remembered_main = list(record.get('main') or [])
            group_name = record.get('group')
            if group_name:
                group = next((g for g in self.groups if g['name'] == group_name), None)
                if group is None:
                    group = {'name': group_name, 'apps': [], 'icon': create_group_icon([])}
                    self.groups.append(group)
                    ids = [obj['name'] if typ == 'group' else obj['path'] for typ, obj in self.main_order]
                    if not self._insert_after_neighbour(self.main_order, ids, ('group', group), group_name, remembered_main):
                        self.main_order.append(('group', group))
                if app_info not in group['apps']:
                    ids = [a['path'] for a in group['apps']]
                    if not self._insert_after_neighbour(group['apps'], ids, app_info, path, list(record.get('in_group') or [])):
                        group['apps'].append(app_info)
                    group['icon'] = create_group_icon(group['apps'])
                self.main_order = [(typ, obj) for typ, obj in self.main_order if not (typ == 'app' and obj is app_info)]
                self.filtered_apps = [a for a in self.filtered_apps if a is not app_info]
            elif path in remembered_main:
                self.main_order = [(typ, obj) for typ, obj in self.main_order if not (typ == 'app' and obj is app_info)]
                ids = [obj['name'] if typ == 'group' else obj['path'] for typ, obj in self.main_order]
                self._insert_after_neighbour(self.main_order, ids, ('app', app_info), path, remembered_main)
        self.group_dict = {g['name']: g for g in self.groups}
        save_groups(self.groups)
        try:
            with open(USER_APPS_MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(dict(places, apps=records), f, ensure_ascii=False)
        except Exception:
            pass

    # ── hidden apps (the blacklist) ──
    def hide_app(self, app_info):
        """This app is not shown in Raspberry any more (it stays installed). Undo: menu › Hidden apps."""
        save_hidden_apps(load_hidden_apps() + [app_info['path']])
        names = self._load_hidden_names()
        names[app_info['path']] = app_info.get('name') or os.path.basename(app_info['path'])[:-4]
        self._save_hidden_names(names)
        self.take_out_apps([app_info])

    def unhide_apps(self, paths=None):
        """Show hidden apps again (all of them without `paths`): the next scan finds them and each
        returns to where it was."""
        hidden = load_hidden_apps()
        back = set(hidden if paths is None else paths)
        save_hidden_apps([p for p in hidden if p not in back])
        self._save_hidden_names({p: n for p, n in self._load_hidden_names().items() if p not in back})
        self.start_background_scan()

    def _load_hidden_names(self) -> dict:
        data = self._load_user_app_places().get('hidden_names')
        return dict(data) if isinstance(data, dict) else {}

    def _save_hidden_names(self, names):
        places = self._load_user_app_places()
        places['hidden_names'] = names
        try:
            with open(USER_APPS_MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(places, f, ensure_ascii=False)
        except Exception:
            pass

    def fill_hidden_apps_menu(self):
        """Menu › Hidden apps: one line per hidden app (choosing it shows the app again), then "all"."""
        menu = self.hidden_apps_menu
        menu.clear()
        hidden = load_hidden_apps()
        names = self._load_hidden_names()
        if not hidden:
            nothing = menu.addAction(self.tr("No hidden apps"))
            nothing.setEnabled(False)
            return
        for path in hidden:
            label = names.get(path) or os.path.basename(path)[:-4]
            menu.addAction(label, lambda p=path: self.unhide_apps([p]))
        menu.addSeparator()
        menu.addAction(self.tr("Show all of them again"), lambda: self.unhide_apps(None))

    def _on_theme_changed(self, dark):
        self.backdrop.retheme()
        self.main_content.search_bar.apply_theme(dark)
        for btn in self.findChildren(QPushButton):
            if btn is getattr(self, 'focused_btn', None) and hasattr(btn, 'icon_label'):
                btn.icon_label.setStyleSheet(raspberry_ui.focus_ring_qss())
        self._refresh_group_glass()
        self.update()

    def group_available_rect(self) -> QRect:
        """The part of the window an open group may use: not under the menu bar, not under a Dock
        that is showing, and a little air to the edges."""
        left, bottom, right = getattr(self, '_dock_insets', (0, 0, 0))
        top = 0
        try:
            screen = self.screen() or QGuiApplication.primaryScreen()
            top = max(0, screen.availableGeometry().top() - screen.geometry().top())
        except Exception:
            pass
        air = 14
        rect = self.rect().adjusted(left + air, top + air, -(right + air), -(bottom + air))
        return rect if rect.width() > 200 and rect.height() > 200 else self.rect()

    def group_panel_rect(self, panel):
        """Where the open group ends up: the middle of the room it has."""
        size = panel.full_size()
        room = self.group_available_rect()
        return QRect(room.x() + (room.width() - size.width()) // 2, room.y() + (room.height() - size.height()) // 2,
                     size.width(), size.height())

    def refit_group_panel(self):
        """The room changed while a group is open (another screen size, the Dock came or went): the
        panel is built again for the new room, at once, on the page it was on."""
        panel = self.group_widget
        if panel is None or not panel.isVisible() or getattr(self, '_closing', False):
            return
        self._sync_scrim()
        room = self.group_available_rect().size()
        fit = group_panel_fit(room.width(), room.height(), len(panel.group['apps']), cell_size())
        centred = self.group_panel_rect(panel)
        if all(fit[k] == panel._fit[k] for k in ('rows', 'cell', 'chrome', 'side')):
            if not panel.is_morphing() and panel.geometry() != centred:
                panel.setGeometry(centred)
            return
        group, first_shown = panel.group, panel.current_page * panel.items_per_page
        self.show_group_widget(group)
        if self.anim is not None:
            self.anim.setCurrentTime(self.anim.duration())     # no growing again: it is simply there
        panel = self.group_widget
        if panel is not None:
            panel.goto_page_immediate(min(first_shown // panel.items_per_page, panel.slide_page_count() - 1))

    def _refresh_group_glass(self):
        panel = self.group_widget
        try:
            if panel is not None and panel.isVisible():
                self.scrim.set_picture(self._blurred_behind_group())
                self._veil_group_tiles(self.scrim.level())
                panel.refresh_panel_glass()
        except RuntimeError:
            pass

    def _glass_behind_group(self):
        """(widget, its glass) for every piece of glass under the content behind an open group: the
        search capsule, the groups' tiles, the page dots."""
        found = []
        for widget in self.main_content.findChildren(QWidget):
            helper = getattr(widget, '_broccoli_child_glass', None)
            if helper is not None and hasattr(helper, 'set_opacity') and hasattr(helper, '_frame'):
                found.append((widget, helper))
        return found

    def _blurred_behind_group(self):
        """The blurred picture of the search, the icons and the dots (style book 5.13: an open group
        blurs what is behind it). System glass is in no widget's picture: each piece goes in as a plate."""
        plates = []
        for widget, helper in self._glass_behind_group():
            try:
                if widget.isVisible():
                    frame = helper._frame()
                    plates.append((QRectF(frame.origin.x, frame.origin.y, frame.size.width, frame.size.height),
                                   float(helper._current_radius())))
            except Exception:
                continue
        return raspberry_ui.blurred_content(self, [self.main_content], plates)

    def _veil_group_tiles(self, level):
        """The sharp glass behind an open group fades out as its blurred picture fades in."""
        for widget, helper in self._glass_behind_group():
            try:
                if isinstance(widget, GroupTile):
                    widget.set_veil(level)
                else:
                    helper.set_opacity(1.0 - max(0.0, min(1.0, float(level))))
            except Exception:
                continue

    # ── the Dock ──
    def apply_dock_insets(self, insets=None, geometry=None):
        """Keep the content (the page dots first of all) clear of a Dock that is showing: the margins
        follow the Dock's size at this moment. `insets`: (left, bottom, right) when already known."""
        if insets is None:
            insets = raspberry_ui.dock_insets(geometry if geometry is not None else self.geometry())
        insets = tuple(int(value) for value in insets)
        if insets == self._dock_insets:
            return False
        sides_changed = (insets[0], insets[2]) != (self._dock_insets[0], self._dock_insets[2])
        self._dock_insets = insets
        layout = self.main_content.content_layout
        self.main_content.set_content_margins(raspberry_ui.content_margins(insets))
        layout.activate()
        if self.isVisible():
            # compact: its gap follows the grid's height, and its own side margins were just reset
            if self.fit_cells() or sides_changed or getattr(self, 'compact_mode', False):
                self._finish_reflow()        # an animation still running holds the buttons about to go
                self.display_apps(self.filtered_apps, self.current_page)  # other cells / columns by width
            elif self.group_widget is not None:
                QTimer.singleShot(0, self._refresh_group_glass)
            if self.group_widget is not None:
                QTimer.singleShot(0, self.refit_group_panel)
        return True

    def fit_cells(self) -> bool:
        """Set the icons' cell so that 7 columns × 5 rows fit between the search field and the page
        dots on this screen (Ryan 2026-11-16: the icons must not push into each other). True = changed.
        The room is what the layout really gives the grid, not an estimate."""
        content = self.main_content
        try:
            if content.size() != self.size():
                content.setGeometry(self.rect())
            if content.layout() is not None:
                content.layout().activate()
            content.content_layout.activate()
        except RuntimeError:
            return False
        grid = content.grid_widget
        room_h = grid.height()
        room_w = grid.width() - sum(content.side_margins) - 2 * content.grid_side_margin - (GRID_COLS - 1) * 10
        if room_h < 5 * 40 or room_w < 7 * 40:   # not laid out yet: the next display fits it
            return False
        return set_cell_size(min(CELL_FULL, room_h // GRID_ROWS, room_w // GRID_COLS))

    def _refit_after_layout(self):
        """The layout settled after a display: if the room turned out different, lay the icons out again."""
        if not self.isVisible():
            return
        changed = self.fit_cells()
        if not changed and getattr(self, 'compact_mode', False):     # the compact gap follows the room too
            grid = self.main_content.grid_widget
            room = (max(0, grid.width() - sum(self.main_content.side_margins)), grid.height())
            changed = room != getattr(self, '_compact_room', None)
        if changed:
            self.display_apps(self.filtered_apps, self.current_page)

    @staticmethod
    def compact_column_gap(avail_w, grid_h, cell=None) -> int:
        """Compact mode's gap between two columns for a grid this wide (between its side margins) and
        this high: the narrower of the usual gap between columns and the gap between rows; at least 10."""
        cell = cell or cell_size()
        # the layout shares what the icons leave free equally between them and at both ends:
        # across, 10 between columns comes first (measured on a 2056 × 1329 screen: 117 and 59)
        usual = (avail_w - GRID_COLS * cell - (GRID_COLS - 1) * 10) / float(GRID_COLS + 1) + 10
        rows = (grid_h - GRID_ROWS * cell) / float(GRID_ROWS + 1)
        if grid_h < GRID_ROWS * 40:                              # not laid out yet
            rows = usual
        return int(max(10, min(usual, rows)))

    def _recheck_dock(self):
        if self.isVisible():
            self.apply_dock_insets()

    def _on_available_geometry_changed(self, *_args):
        QTimer.singleShot(0, self._recheck_dock)

    def _watch_screen(self, screen):
        screen.availableGeometryChanged.connect(self._on_available_geometry_changed)
        # another resolution while the launcher is up (Ryan 2026-11-27): followed at once, not at the next opening
        screen.geometryChanged.connect(lambda *_args, screen=screen: QTimer.singleShot(
            0, lambda: self._follow_screen_size() if self.isVisible() and self.screen() is screen else None))

    def _follow_screen_size(self, geometry=None) -> bool:
        """The launcher is up and its screen has another size now: the window, the wallpaper, the icons and
        an open group with its dimmed background all go to the new size. True = something was changed."""
        if not self.isVisible():
            return False
        if geometry is None:
            screen = self.screen() or QGuiApplication.primaryScreen()
            geometry = screen.geometry()
        if QRect(geometry) == self.geometry():
            return False
        self._show_serial = getattr(self, '_show_serial', 0) + 1     # the check after showing looked at the old size
        self.setGeometry(QRect(geometry))
        self.main_content.setGeometry(self.rect())
        self.backdrop.prepare(self.geometry())
        self.apply_dock_insets()
        self._finish_reflow()
        self.fit_cells()
        self.display_apps(self.filtered_apps, self.current_page)
        self._refit_open_group()
        return True

    def _sync_scrim(self) -> bool:
        """The dimmed, blurred layer behind an open group covers the whole window at the size it has now
        (it used to be measured only when the group opened: after another resolution it kept the old
        size and the old picture). True = it was resized."""
        scrim = getattr(self, 'scrim', None)
        if scrim is None or not scrim.isVisible() or scrim.geometry() == self.rect():
            return False
        scrim.setGeometry(self.rect())
        return True

    def _refit_open_group(self):
        """An open group after the window changed its size: the layer behind it, the panel and the
        blurred picture, now (not queued: nothing of the old size is seen)."""
        panel = self.group_widget
        if panel is None or not panel.isVisible():
            return
        self._sync_scrim()
        self.refit_group_panel()
        self._refresh_group_glass()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._sync_scrim():
            QTimer.singleShot(0, self._refresh_group_glass)     # its picture, once the layout has settled

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

    # ── pages ──
    # Two ways (menu › "Keep every page on its own", off by default — Ryan 2026-11-16):
    #   off: one long row of icons cut into pages of 35; taking one away pulls everything after it up.
    #   on:  every page keeps its own icons. Taking one away leaves that page one short, the other
    #        pages do not move; a page that is full hands its last icon on to the next; an empty page
    #        goes. Which page an icon is on is its '_page' (kept in pages.json by name / path).
    def _is_searching(self) -> bool:
        return bool(self.main_content.search_bar.text().strip())

    def pages_are_separate(self) -> bool:
        return bool(getattr(self, 'independent_pages', False))

    @staticmethod
    def _order_id(typ, obj):
        return obj['name'] if typ == 'group' else obj['path']

    def _normalise_pages(self):
        """Bring main_order and the pages into line (separate pages only): every item has a page, the
        items of a page stand together, no page holds more than 35, no page is empty."""
        if not self.pages_are_separate():
            self._page_sizes = None
            return
        per_page = self.items_per_page
        saved = getattr(self, '_saved_pages', None) or {}
        previous = 0
        for typ, obj in self.main_order:
            if not isinstance(obj.get('_page'), int):
                known = saved.get(self._order_id(typ, obj))
                # new here: the page it was saved on, else the page of what stands before it
                obj['_page'] = int(known) if isinstance(known, int) else previous
            previous = obj['_page']
        pages = {}
        for item in self.main_order:
            pages.setdefault(item[1]['_page'], []).append(item)
        ordered = [pages[number] for number in sorted(pages)]
        index = 0
        while index < len(ordered):                     # a full page hands its last icons on
            if len(ordered[index]) > per_page:
                spill = ordered[index][per_page:]
                ordered[index] = ordered[index][:per_page]
                if index + 1 < len(ordered):
                    ordered[index + 1] = spill + ordered[index + 1]
                else:
                    ordered.append(spill)
            index += 1
        ordered = [page for page in ordered if page] or [[]]
        self.main_order = []
        for number, page in enumerate(ordered):
            for typ, obj in page:
                obj['_page'] = number
                self.main_order.append((typ, obj))
        self._page_sizes = [len(page) for page in ordered]

    def _separate_now(self) -> bool:
        return self.pages_are_separate() and not self._is_searching() and bool(getattr(self, '_page_sizes', None))

    def page_start(self, page) -> int:
        if self._separate_now():
            return sum(self._page_sizes[:max(0, page)])
        return page * self.items_per_page

    def page_len(self, page) -> int:
        if self._separate_now():
            return self._page_sizes[page] if 0 <= page < len(self._page_sizes) else 0
        total = len(self.filtered_apps) if self._is_searching() else len(self.main_order)
        return max(0, min(self.items_per_page, total - page * self.items_per_page))

    def page_of_index(self, index) -> int:
        if self._separate_now():
            running = 0
            for number, size in enumerate(self._page_sizes):
                running += size
                if index < running:
                    return number
            return max(0, len(self._page_sizes) - 1)
        return index // self.items_per_page

    def total_pages(self):
        if self._separate_now():
            return max(1, len(self._page_sizes))
        return max(1, (len(self.groups) + len(self.filtered_apps) + self.items_per_page - 1) // self.items_per_page)

    def toggle_independent_pages(self):
        on = self.independent_pages_action.isChecked()
        self.independent_pages = on
        try:
            with open(setting_path("independent_pages"), "w") as f:
                f.write("1" if on else "0")
        except Exception:
            pass
        before = self._grid_snapshot() if self.isVisible() else None
        if on:      # as it stands now: nothing moves
            for index, (_typ, obj) in enumerate(self.main_order):
                obj['_page'] = index // self.items_per_page
        else:       # one long row again: everything closes up
            for _typ, obj in self.main_order:
                obj.pop('_page', None)
        self._saved_pages = {}
        self._normalise_pages()
        self.current_page = min(self.current_page, self.total_pages() - 1)
        self.save_current_order()
        self.display_apps(self.filtered_apps, self.current_page)
        if before is not None:
            self._animate_reflow(before)

    def move_app_to_page(self, app_info, page, kind='app'):
        """Separate pages: the app goes to that page, in front of that page's other apps (after the
        groups standing first there); a group (kind='group') to the same place = last of that page's
        groups. `page` one past the last: a new page."""
        if not self.pages_are_separate() or not any(obj is app_info for _t, obj in self.main_order):
            return False
        before = self._grid_snapshot() if self.isVisible() else None
        self.main_order = [(typ, obj) for typ, obj in self.main_order if obj is not app_info]
        page = max(0, min(int(page), len(self._page_sizes or [0])))
        at = len(self.main_order)
        for index, (typ, obj) in enumerate(self.main_order):
            if obj.get('_page', 0) > page:
                at = index
                break
            if obj.get('_page', 0) == page and typ == 'app':
                at = index
                break
        app_info['_page'] = page
        self.main_order.insert(at, (kind, app_info))
        self._after_main_order_changed(before)
        return True

    def _after_main_order_changed(self, before=None):
        """main_order was rearranged by hand: pages, the list of loose apps, the files, the screen."""
        self._normalise_pages()
        loose = [obj for typ, obj in self.main_order if typ == 'app']
        self.filtered_apps = loose + [a for a in self.filtered_apps if not any(a is b for b in loose)]
        self.current_page = min(self.current_page, self.total_pages() - 1)
        self.sync_group_order()
        self.display_apps(self.filtered_apps, self.current_page)
        if before is not None:
            self._animate_reflow(before)

    def display_apps(self, apps, page=0, prebuilt=None):
        """Lay the page out. `prebuilt`: the page's 35 buttons already exist (they slid in): keep them."""
        grid_layout = self.main_content.grid_layout
        grid_widget = self.main_content.grid_widget
        slide = getattr(self, '_page_slide', None)
        if slide is not None and prebuilt is None:
            slide.abandon()
        keep = set(id(w) for w in (prebuilt or ()))

        # 先移除布局项
        for i in reversed(range(grid_layout.count())):
            w = grid_layout.itemAt(i).widget()
            try:
                if w is not None:
                    w.hide()            # first: else Qt's pending "show" makes it a window of its own
                    w.setParent(None)
                    w.deleteLater()
            except RuntimeError:
                pass

        # 再保险：删除 grid_widget 下残留子控件，但跳过 overlay
        for w in grid_widget.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
            if w.objectName() == "insertOverlay" or id(w) in keep:
                continue
            try:
                w.hide()            # first: else Qt's pending "show" makes it a window of its own
                w.setParent(None)
                w.deleteLater()
            except RuntimeError:
                pass

        self._normalise_pages()
        is_searching = bool(self.main_content.search_bar.text().strip())
        if not is_searching and page > self.total_pages() - 1:
            page = self.current_page = self.total_pages() - 1
        start = self.page_start(page)
        end = start + (self.page_len(page) if self._separate_now() else self.items_per_page)

        if is_searching:
            page_items = [('app', app) for app in apps[start:end]]
        else:
            page_items = self.main_order[start:end]

        # 常量
        MAX_COLS = 7
        MAX_ROWS = 5
        # the cell that lets 7 × 5 fit this screen (smaller screens, a Dock in the way: smaller icons,
        # never icons pushed into each other); every row and column the same size
        if self.fit_cells() and prebuilt:
            for w in prebuilt:      # made for another cell size: make them again
                safe_delete_widget(w)
            prebuilt = None
        for _row in range(MAX_ROWS):
            grid_layout.setRowMinimumHeight(_row, cell_size())
            grid_layout.setRowStretch(_row, 1)
        for _col in range(MAX_COLS):
            grid_layout.setColumnMinimumWidth(_col, cell_size())
            grid_layout.setColumnStretch(_col, 1)
        m = grid_layout.contentsMargins()
        top_m, bot_m = m.top(), m.bottom()
        side_l, side_r = self.main_content.side_margins      # the grid spans the window: its own margins
        avail_w = max(0, grid_widget.width() - side_l - side_r)

        if getattr(self, 'compact_mode', False):
            # Compact (Ryan 2026-11-19: 「我的本意是让它取最窄的」; chosen: the gap between columns = the
            # gap between rows): of the two gaps the icons have on this screen — left-right and
            # up-down — the narrower one is used for both, and the icons stand as one block in the
            # middle. Never wider than without it (the old rule, "at most 140", was wider on screens
            # whose usual gap is smaller than that). Worked out from the screen in use, each time.
            hgap = self.compact_column_gap(avail_w, grid_widget.height())
            self._compact_room = (avail_w, grid_widget.height())
            content_w = MAX_COLS * ICON_W + (MAX_COLS - 1) * hgap
            side_margin = max(0, (avail_w - content_w) // 2)
            grid_layout.setContentsMargins(side_l + side_margin, top_m, side_r + side_margin, bot_m)
            grid_layout.setHorizontalSpacing(hgap)
        else:
            # 正常模式
            m = grid_layout.contentsMargins()
            grid_layout.setContentsMargins(side_l, m.top(), side_r, m.bottom())
            # a fixed gap: the system's own (-1) depends on what kind of button is next to which, so
            # the columns sat up to 3 points differently from page to page — seen now that a page
            # slides in and stays
            grid_layout.setHorizontalSpacing(10)

        # 摆放按钮（不足的格子补空白按钮）
        buttons = prebuilt if prebuilt else self._make_page_buttons(page_items)
        for idx, btn in enumerate(buttons):
            row, col = divmod(idx, MAX_COLS)
            grid_layout.addWidget(btn, row, col)

        # 指示器数量
        if is_searching:
            self.update_page_indicator(len(apps))
        else:
            self.update_page_indicator(len(self.main_order))
        self.focus_index = -1
        self.focused_btn = None
        QTimer.singleShot(0, self._refit_after_layout)
        # an open group floats on this grid: its glass shows the new icons and stays above theirs
        if self.group_widget is not None:
            QTimer.singleShot(0, self._refresh_group_glass)

    def _make_page_buttons(self, page_items):
        """The 35 buttons of one page in slot order (icons, groups, then blanks); not in the layout yet."""
        grid_widget = self.main_content.grid_widget
        buttons = []
        for typ, obj in page_items[:GRID_COLS * GRID_ROWS]:
            if typ == 'group':
                buttons.append(GroupButton(obj, grid_widget, main_window=self))
            else:
                buttons.append(AppButton(obj, grid_widget, main_window=self))
        while len(buttons) < GRID_COLS * GRID_ROWS:
            buttons.append(EmptyButton(main_window=self, parent=grid_widget))
        return buttons

    def _page_items(self, page):
        start = self.page_start(page)
        if self.main_content.search_bar.text().strip():
            return [('app', app) for app in self.filtered_apps[start:start + self.items_per_page]]
        if self._separate_now():
            return self.main_order[start:start + self.page_len(page)]
        return self.main_order[start:start + self.items_per_page]

    def update_page_indicator(self, total_items):
        self.main_content.dots.set_pages(self.total_pages(), self.current_page)

    def goto_page(self, page):
        total_pages = self.total_pages()
        if page < 0 or page >= total_pages or page == self.current_page:
            return
        if getattr(self, "_is_animating", False):
            return
        direction = 1 if page > self.current_page else -1
        is_searching = bool(self.main_content.search_bar.text().strip())
        # (no animation when searching, as before)
        if is_searching or not self.isVisible() or not self._page_slide.go(page, direction):
            self.goto_page_immediate(page)
            return
        # as before, the page counts as turned (and the dots show it) from the start of the slide
        self.current_page = page
        self.main_content.dots.set_pages(total_pages, page)

    # ── what the page strip (PageSlide) asks of the launcher ──
    def slide_page_count(self):
        return self.total_pages()

    def slide_duration(self, width):
        # the menu's "Flipping speed" (points per second) over one page
        return max(140, min(400, int(width / max(1000, self.page_anim_speed) * 1000)))

    def slide_gap(self):
        return PAGE_GAP

    def slide_start(self):
        """The icons on screen; and where each of the 35 slots is, for the page that comes in."""
        self._finish_reflow()
        grid_layout = self.main_content.grid_layout
        homes, moving = [], []
        for idx in range(GRID_COLS * GRID_ROWS):
            item = grid_layout.itemAtPosition(*divmod(idx, GRID_COLS))
            w = item.widget() if item is not None else None
            homes.append(w.pos() if w is not None else None)
            if isinstance(w, (AppButton, GroupButton)):
                moving.append(w)
        self._slide_homes = homes
        return moving

    def slide_build(self, page):
        homes = getattr(self, '_slide_homes', None) or []
        page_items = self._page_items(page)
        if not page_items or len(homes) < GRID_COLS * GRID_ROWS or any(home is None for home in homes):
            return []
        buttons = self._make_page_buttons(page_items)
        for btn, home in zip(buttons, homes):
            btn.move(home)
        return buttons

    def slide_commit(self, page, buttons):
        self.current_page = page
        self.display_apps(self.filtered_apps, page, prebuilt=buttons)

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

    # ── an icon goes into a group / comes out of one: it flies there, the others close up ──
    @staticmethod
    def _reflow_key(button):
        if isinstance(button, GroupButton):
            return ('group', id(button.group))
        if isinstance(button, AppButton):
            return ('app', button.app_info['path'])
        return None

    def _grid_snapshot(self):
        """Where every icon of the page is now (before the grid is laid out again)."""
        self._finish_reflow()
        places = {}
        for button in self.main_content.grid_widget.findChildren(QPushButton, options=Qt.FindChildOption.FindDirectChildrenOnly):
            key = self._reflow_key(button)
            if key is not None and button.isVisible():
                places[key] = button.pos()
        return places

    def _settle_grid(self):
        """The grid was just laid out again: put every icon at its final place now (the layout leaves
        out what is not shown yet, and new buttons are only shown on Qt's next turn)."""
        grid = self.main_content.grid_widget
        if not grid.isVisible():
            return
        for button in grid.findChildren(QPushButton, options=Qt.FindChildOption.FindDirectChildrenOnly):
            if not button.isVisible():
                button.show()
        self.main_content.grid_layout.activate()
        for button in grid.findChildren(QPushButton, options=Qt.FindChildOption.FindDirectChildrenOnly):
            if button.layout() is not None:
                button.layout().activate()

    def _animate_reflow(self, before, fade_new=True):
        """The grid was laid out again: every icon that was on the page before slides from its old
        place to its new one (instead of jumping)."""
        self._finish_reflow()
        grid = self.main_content.grid_widget
        self._settle_grid()
        moving = []
        for button in grid.findChildren(QPushButton, options=Qt.FindChildOption.FindDirectChildrenOnly):
            key = self._reflow_key(button)
            old = before.get(key)
            if old is None and key is not None and fade_new:
                # it was not on the page before (it came out of a group, a new group …): it fades in
                effect = QGraphicsOpacityEffect(button)
                effect.setOpacity(0.0)
                button.setGraphicsEffect(effect)
                if isinstance(button, GroupButton):
                    button.bind_fade(effect)
                fade = QPropertyAnimation(effect, b"opacity", button)
                fade.setDuration(REFLOW_MS)
                fade.setStartValue(0.0)
                fade.setEndValue(1.0)

                def shown(button=button, effect=effect):
                    try:
                        if not sip.isdeleted(button) and button.graphicsEffect() is effect:
                            if isinstance(button, GroupButton):
                                button.icon_label.set_glass_opacity(1.0)
                            button.setGraphicsEffect(None)
                    except RuntimeError:
                        pass

                fade.finished.connect(shown)
                moving.append(fade)
                continue
            if old is None or old == button.pos():
                continue
            anim = QPropertyAnimation(button, b"pos", button)
            anim.setDuration(REFLOW_MS)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.setStartValue(old)
            anim.setEndValue(button.pos())
            button.move(old)
            moving.append(anim)
        self._reflow = moving
        if moving:
            # the glass under the group tiles moves at once, Qt draws on its next turn: draw with it
            moving[0].valueChanged.connect(lambda _value, grid=grid: grid.repaint() if not sip.isdeleted(grid) else None)
        for anim in moving:
            anim.start()

    def _finish_reflow(self):
        entrance = getattr(self, '_entrance', None)
        if entrance is not None:
            self._entrance = None
            try:
                if not sip.isdeleted(entrance) and entrance.state() == QAbstractAnimation.State.Running:
                    entrance.setCurrentTime(entrance.totalDuration())
            except RuntimeError:
                pass
        for anim in getattr(self, '_reflow', None) or []:
            try:
                if not sip.isdeleted(anim) and anim.state() == QAbstractAnimation.State.Running:
                    anim.setCurrentTime(anim.duration())
                    anim.stop()
                    anim.finished.emit()
            except RuntimeError:
                pass
        self._reflow = []

    def _icon_rect(self, button):
        """The icon of a button, in this window."""
        try:
            label = button.icon_label
            if isinstance(label, GroupTile):
                tile = label.tile_rect().toRect()
                return QRect(label.mapTo(self, tile.topLeft()), tile.size())
            return QRect(label.mapTo(self, QPoint(0, 0)), label.size())
        except (RuntimeError, AttributeError):
            return None

    def _app_button(self, app_info, in_panel):
        if in_panel and (self.group_widget is None or not self.group_widget.isVisible()):
            return None
        holder = self.group_widget.grid_widget if in_panel else self.main_content.grid_widget
        for button in holder.findChildren(AppButton):
            try:
                if button.app_info is app_info:      # (just laid out: not shown yet, but in place)
                    return button
            except RuntimeError:
                continue
        return None

    def _side_of_page(self, typ, obj):
        """-1 / +1: the page this item is on lies before / after the page on screen (0: on it or nowhere)."""
        for idx, (kind, item) in enumerate(self.main_order):
            if kind == typ and item is obj:
                page = self.page_of_index(idx)
                return (page > self.current_page) - (page < self.current_page)
        return 0

    def _group_landing(self, group):
        """(rect, lands_on_its_place): where an icon that goes into this group ends — its own small
        place on the group's tile; a tile with more than nine shows no more: the middle of the tile."""
        for button in self.main_content.grid_widget.findChildren(GroupButton):
            try:
                if button.group is group:
                    tile = self._icon_rect(button)
                    scale = tile.width() / 240.0            # create_group_icon draws on 240 × 240
                    index = len(group['apps']) - 1
                    if 0 <= index < 9:
                        row, col = divmod(index, 3)
                        return QRect(int(tile.x() + (28 + col * 64) * scale), int(tile.y() + (28 + row * 64) * scale),
                                     max(1, int(56 * scale)), max(1, int(56 * scale))), True
                    side = max(1, int(56 * scale))
                    return QRect(tile.center().x() - side // 2, tile.center().y() - side // 2, side, side), False
            except RuntimeError:
                continue
        return None, False

    def _vanish_icon(self, icon, rect):
        """Something leaves for good (to the Trash, a group dissolved): its picture shrinks a little
        where it stood and fades away."""
        if rect is None:
            return None
        w, h = int(rect.width() * 0.7), int(rect.height() * 0.7)
        end = QRect(rect.center().x() - w // 2, rect.center().y() - h // 2, w, h)
        return self._fly_icon({'icon': icon}, rect, end, fade=True, duration=VANISH_MS)

    def _fly_icon(self, app_info, start, end, fade, side=0, duration=None):
        """The app's icon flies from `start` to `end` (rectangles in this window), changing size on the
        way. `fade`: it melts away as it arrives (it lands behind the blur, or on a page that is not on
        screen: `end` None and `side` -1 / +1 = towards that edge)."""
        if start is None or not self.isVisible():
            return None
        if end is None:
            half = max(8, start.width() // 2)
            x = -half if side < 0 else (self.width() if side > 0 else start.center().x() - half // 2)
            end, fade = QRect(x, start.center().y() - half // 2, half, half), True
        flyer = QLabel(self)
        flyer.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        flyer.setStyleSheet("background: transparent; border: none;")
        flyer.setScaledContents(True)
        big = max(start.width(), end.width())
        flyer.setPixmap(app_info['icon'].pixmap(big, big))
        flyer.setGeometry(start)
        effect = QGraphicsOpacityEffect(flyer)
        effect.setOpacity(1.0)
        flyer.setGraphicsEffect(effect)
        flyer.fly_start, flyer.fly_end, flyer.fly_fade = QRect(start), QRect(end), bool(fade)
        flyer.show()
        flyer.raise_()
        anim = QVariantAnimation(flyer)
        anim.setDuration(int(duration or ICON_FLY_MS))
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)

        def step(t, flyer=flyer, effect=effect, start=QRectF(start), end=QRectF(end), fade=fade):
            if sip.isdeleted(flyer):
                return
            flyer.setGeometry(self._rect_between(start, end, float(t)))
            if fade:
                effect.setOpacity(max(0.0, min(1.0, (1.0 - float(t)) / 0.4)))

        def done(flyer=flyer):
            if flyer in self._flyers:
                self._flyers.remove(flyer)
            if not sip.isdeleted(flyer):
                flyer.hide()
                flyer.deleteLater()

        anim.valueChanged.connect(step)
        anim.finished.connect(done)
        flyer.fly_anim = anim
        self._flyers.append(flyer)
        anim.start()
        return flyer

    # ── the lists at the two sides while an icon is dragged ──
    def page_label(self, number=None) -> str:
        if number is None:
            return QCoreApplication.translate('LaunchpadWindow', "New page")
        return QCoreApplication.translate('LaunchpadWindow', "Page %1").replace('%1', str(number + 1))

    def new_group_label(self) -> str:
        return QCoreApplication.translate('AppButton', '🆕 New group').replace('🆕', '').strip()

    def drag_rail_items(self, side, dragging_group=False):
        """What a side's list holds. The groups, in the grid's order, then "new group" — on both sides,
        unless every page keeps its own icons: then the right side lists the pages (drop = to the
        front of that page's apps), then "new page"."""
        if side > 0 and self._separate_now():
            return [{'kind': 'page', 'page': number} for number in range(self.total_pages())] + [{'kind': 'newpage'}]
        if dragging_group:       # a group does not go into a group: no list of groups
            return []
        return [{'kind': 'group', 'group': g} for g in self.groups_in_display_order()] + [{'kind': 'new'}]

    def show_drag_rails(self, app_btn=None, dragging_group=False):
        if self.group_widget is not None and self.group_widget.isVisible():
            return
        if not self._drag_rails:
            self._drag_rails = [DragRail(self, -1), DragRail(self, +1)]
        grid = self.main_content.grid_widget
        top = grid.mapTo(self, QPoint(0, 0)).y()
        margins = self.main_content.content_margins()
        for rail in self._drag_rails:
            rail.set_items(self.drag_rail_items(rail.side, dragging_group))
            if not rail.items:
                rail.hide()
                continue
            height = min(rail.content_height(), grid.height())
            room = margins.left() if rail.side < 0 else margins.right()
            inset = max(4, (room - RAIL_WIDTH) // 2)
            x = inset if rail.side < 0 else self.width() - inset - RAIL_WIDTH
            rail.place(QPoint(x, top + (grid.height() - height) // 2), height)
            rail.slide_in()

    def hide_drag_rails(self):
        for rail in self._drag_rails:
            rail.slide_out()

    def rail_drop(self, item, app_path, where):
        """An icon was dropped on a group (or on "new group") in a side list: into that group; it flies
        from where it was let go to the group's tile in the grid."""
        if app_path.startswith(GROUP_DRAG_PREFIX):
            group = next((g for g in self.groups if g['name'] == app_path[len(GROUP_DRAG_PREFIX):]), None)
            if group is not None and item['kind'] in ('page', 'newpage'):
                self.move_app_to_page(group, item['page'] if item['kind'] == 'page' else self.total_pages(),
                                      kind='group')
            return
        app_info = next((a for a in self.apps if a['path'] == app_path), None)
        if app_info is None or any(app_info in g['apps'] for g in self.groups):
            return
        if item['kind'] in ('page', 'newpage'):
            self.move_app_to_page(app_info, item['page'] if item['kind'] == 'page' else self.total_pages())
            return
        from types import SimpleNamespace
        start = QRect(where.x() - 32, where.y() - 32, 64, 64)
        self.combine_app_to_group(SimpleNamespace(app_info=app_info), item.get('group'), start_rect=start)

    def combine_app_to_group(self, app_btn, group, start_rect=None):
        start = start_rect if start_rect is not None else self._icon_rect(app_btn)
        was_searching = bool(self.main_content.search_bar.text().strip())
        before = None if was_searching else self._grid_snapshot()
        moved_app = app_btn.app_info
        # 先从所有分组移除该 app，防止重复
        for g in self.groups:
            if app_btn.app_info in g['apps']:
                g['apps'].remove(app_btn.app_info)
                g['icon'] = create_group_icon(g['apps'])
        if group is None:
            group = {'name': self.unique_group_name(self.new_group_label()), 'apps': [app_btn.app_info],
                     'icon': create_group_icon([app_btn.app_info])}
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
        self.filtered_apps = [a for a in self.apps if not any(a in g['apps'] for g in self.groups)]
        self.display_apps(self.filtered_apps, self.current_page)
        self.sync_group_order()
        is_searching = bool(self.main_content.search_bar.text().strip())
        if is_searching:
            self.main_content.search_bar.setText('')
        # the icon flies onto its small place on the group's tile; the icons after it close up
        self._settle_grid()
        landing, exact = self._group_landing(group)
        if before is not None:
            self._animate_reflow(before)
        self._fly_icon(moved_app, start, landing, fade=not exact, side=self._side_of_page('group', group))

    def move_app_to_group(self, app_btn, target_group):
        # 只允许从组内移动到其他组
        start = self._icon_rect(app_btn)
        moved_app = app_btn.app_info
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
            self.group_widget.display_apps_animated(from_group['apps'], self.group_widget.current_page)
        # the icon flies to the other group's tile (behind the blur: it melts away as it arrives)
        self._settle_grid()
        landing, _exact = self._group_landing(target_group)
        self._fly_icon(moved_app, start, landing, fade=True, side=self._side_of_page('group', target_group))

    def group_tile_rect(self, group):
        """Where this group's glass tile is in the window right now — what its panel grows out of and
        shrinks back into. Not on this page (or no tile): a small square in the middle."""
        for button in self.main_content.grid_widget.findChildren(GroupButton):
            try:
                if button.group is group and button.isVisible():
                    tile = button.icon_label
                    rect = tile.tile_rect()
                    return QRectF(QPointF(tile.mapTo(self, QPoint(0, 0))) + rect.topLeft(), rect.size())
            except RuntimeError:
                continue
        side = float(tile_side())
        return QRectF((self.width() - side) / 2.0, (self.height() - side) / 2.0, side, side)

    @staticmethod
    def _rect_between(start: QRectF, end: QRectF, t: float) -> QRect:
        left = start.left() + (end.left() - start.left()) * t
        top = start.top() + (end.top() - start.top()) * t
        right = start.right() + (end.right() - start.right()) * t
        bottom = start.bottom() + (end.bottom() - start.bottom()) * t
        return QRect(round(left), round(top), max(2, round(right - left)), max(2, round(bottom - top)))

    def _move_group_panel(self, panel, rect: QRect, progress: float):
        """One step of the panel growing / shrinking. The glass under the panel moves at once (a system
        view); what Qt draws — the hole for the glass, the content's picture, the blurred icons around —
        is drawn right now as well, not at the next turn of the event loop: otherwise the glass runs a
        frame ahead of its own content."""
        before = panel.geometry()
        panel.set_morph(progress)
        panel.setGeometry(rect)
        self.repaint(before.united(rect).adjusted(-4, -4, 4, 4))

    def _stop_group_animation(self):
        animation = getattr(self, 'anim', None)
        self.anim = None
        if animation is not None:
            try:
                animation.stop()
                animation.deleteLater()
            except RuntimeError:
                pass

    def show_group_widget(self, group, group_btn=None):
        """Open a group (style book 5.13): its panel grows out of the group's own tile — position, size
        and corner in one movement — while what is behind blurs; the content comes in as it grows."""
        self._stop_group_animation()
        if self.group_widget:
            self.group_widget.hide()
            self.group_widget.deleteLater()
            self.group_widget = None
        # the search, the grid and the dots stay where they are: blurred and a little darker, not clickable
        self.scrim.set_picture(self._blurred_behind_group())
        self.scrim.fade_in()
        self.scrim.raise_()
        panel = GroupWidget(group, self, main_window=self, close_group_widget=self.close_group_widget)
        panel.setParent(self)
        self.group_widget = panel
        start = self.group_tile_rect(group)
        end = QRectF(self.group_panel_rect(panel))
        panel.begin_morph(0.0)
        panel.setGeometry(self._rect_between(start, end, 0.0))
        panel.attach_panel_glass()
        panel.set_morph(0.0)
        panel.raise_()
        panel.show()

        animation = QVariantAnimation(self)
        animation.setDuration(raspberry_ui.GROUP_OPEN_MS)
        animation.setEasingCurve(QEasingCurve.Type.OutQuart)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)

        def step(value, panel=panel, start=start, end=end):
            try:
                self._move_group_panel(panel, self._rect_between(start, end, float(value)), float(value))
            except RuntimeError:
                pass

        def done(panel=panel, end=end):
            try:
                if self.group_widget is panel:
                    panel.setGeometry(end.toRect())
                    panel.end_morph()
            except RuntimeError:
                pass

        animation.valueChanged.connect(step)
        animation.finished.connect(done)
        self.anim = animation
        animation.start()

    def close_group_widget(self):
        """Close the group: the panel shrinks back into its tile — where that tile is now — and what
        is behind turns sharp again."""
        panel = self.group_widget
        if not panel or getattr(panel, '_closing', False):
            return
        panel._closing = True
        self._stop_group_animation()
        start = QRectF(panel.geometry())
        end = self.group_tile_rect(panel.group)
        progress = panel._morph_t if panel.is_morphing() else 1.0
        if not panel.is_morphing():
            panel.begin_morph(1.0)

        animation = QVariantAnimation(self)
        animation.setDuration(raspberry_ui.GROUP_CLOSE_MS)
        animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)

        def step(value, panel=panel, start=start, end=end, progress=progress):
            try:
                self._move_group_panel(panel, self._rect_between(start, end, float(value)),
                                       progress * (1.0 - float(value)))
            except RuntimeError:
                pass

        animation.valueChanged.connect(step)
        animation.finished.connect(self._close_group_widget)
        self.anim = animation
        animation.start()
        self.scrim.fade_out()

    def _close_group_widget(self):
        if self.group_widget is None:
            return
        self.group_widget.hide()
        self.group_widget.deleteLater()
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
        self.sync_group_order()

    def groups_in_display_order(self):
        """The groups in the order they stand in the grid — the one order of groups (Ryan 2026-11-16:
        「组的顺序和现在用户手动排序的顺序不一致……必须动态一致」): menus list them this way, and the
        groups file is kept this way."""
        ordered = [obj for typ, obj in self.main_order if typ == 'group']
        seen = set(id(g) for g in ordered)
        return ordered + [g for g in self.groups if id(g) not in seen]

    def sync_group_order(self):
        """After anything that moves, renames, adds or removes a group: the list of groups follows the
        grid, and both files (the groups, the order — which knows a group by its name) are written."""
        self.groups[:] = self.groups_in_display_order()
        self.group_dict = {g['name']: g for g in self.groups}
        save_groups(self.groups)
        self.save_current_order()

    def unique_group_name(self, wanted, group=None):
        """The saved order knows a group by its name: two groups never share one."""
        taken = set(g['name'] for g in self.groups if g is not group)
        if wanted not in taken:
            return wanted
        number = 2
        while '%s %d' % (wanted, number) in taken:
            number += 1
        return '%s %d' % (wanted, number)

    def refresh_group_tile(self, group):
        """The group's small icons changed (their order inside the group): its tile in the grid shows it now."""
        for button in self.main_content.grid_widget.findChildren(GroupButton):
            try:
                if button.group is group:
                    side = tile_side(button.width())
                    button.icon_label.setPixmap(group['icon'].pixmap(side, side))
            except RuntimeError:
                continue

    def remove_app(self, app_info):
        # the icon shrinks away where it stood, the others close up (Ryan 2026-11-16: these too animate)
        in_panel = self._app_button(app_info, in_panel=True)
        in_grid = self._app_button(app_info, in_panel=False)
        leaving = self._icon_rect(in_panel if in_panel is not None else in_grid) if (in_panel or in_grid) else None
        before = self._grid_snapshot() if self.isVisible() else None
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
        if before is not None:
            self._animate_reflow(before)
        # 如果组窗口还开着，刷新组窗口
        if self.group_widget:
            # 只刷新当前显示的组
            self.group_widget.display_apps_animated(self.group_widget.group['apps'], self.group_widget.current_page)
        self._vanish_icon(app_info['icon'], leaving)

    def disband_group(self, group):
        # the group's tile shrinks away, the icons close up, its apps fade in where they land
        tile_button = next((b for b in self.main_content.grid_widget.findChildren(GroupButton) if b.group is group), None)
        leaving = self._icon_rect(tile_button) if tile_button is not None else None
        before = self._grid_snapshot() if self.isVisible() else None
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
        if before is not None:
            self._animate_reflow(before)
        self._vanish_icon(group['icon'], leaving)

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
        before = self._scan_fingerprint()
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
            self.app_dict = {a['path']: a for a in self.apps}
            self._restore_user_apps([a for a in self.apps if any(a['path'] == n['path'] for n in new_apps)])
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
        # The scan runs every 20 seconds (and 2 seconds after the launcher opens). Laying the icons
        # out again each time deleted every button under whatever was going on — an open right-click
        # menu (Ryan's crash 2026-11-16), a page sliding, a drag. Only when something changed:
        if self._scan_fingerprint() != before:
            self._display_after_scan()

    def _scan_fingerprint(self):
        """What the icon grid is made of (to tell whether a scan changed anything)."""
        return ([a['path'] for a in self.apps], [a['path'] for a in self.filtered_apps],
                [(typ, obj.get('path') or obj.get('name')) for typ, obj in self.main_order],
                [[a['path'] for a in g['apps']] for g in self.groups])

    def _display_after_scan(self):
        """Lay the icons out again for what the scan found — once no system menu is open over them."""
        if glass_kit._ACTIVE_NATIVE_MENU.get('menu') is not None:
            QTimer.singleShot(400, self._display_after_scan)
            return
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
            raspberry_ui.focus_ring_qss()
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
            raspberry_ui.focus_ring_qss()
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
            raspberry_ui.focus_ring_qss()
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
            raspberry_ui.focus_ring_qss()
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
        source = self._app_button(app_info, in_panel=True)
        start = self._icon_rect(source) if source is not None else None
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
            self.group_widget.display_apps_animated(group['apps'], self.group_widget.current_page)
        # the icon flies out of the panel to its new place in the grid (behind the blur: it melts
        # away as it arrives; on another page: towards that side)
        self._settle_grid()
        target = self._app_button(app_info, in_panel=False)
        self._fly_icon(app_info, start, self._icon_rect(target) if target is not None else None, fade=True,
                       side=self._side_of_page('app', app_info))

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

    SHOW_LANDING_CHECK_MS = 450

    def _check_show_landing(self, serial, wanted):
        """Stage Manager (2026-11-25): something moved the launcher or made it smaller after it was shown →
        back over the whole screen, once per showing."""
        if serial != getattr(self, '_show_serial', 0) or not self.isVisible():
            return 'stale'
        got = self.geometry()
        if (abs(got.x() - wanted.x()) <= 8 and abs(got.y() - wanted.y()) <= 8
                and got.width() >= wanted.width() - 8 and got.height() >= wanted.height() - 8):
            return 'in place'
        logging.info('Main window was moved after it was shown: wanted %dx%d at (%d,%d), found %dx%d at (%d,%d) -> put back once',
                     wanted.width(), wanted.height(), wanted.x(), wanted.y(), got.width(), got.height(), got.x(), got.y())
        self.setGeometry(QRect(wanted))
        self.main_content.setGeometry(self.rect())
        self._show_put_back = getattr(self, '_show_put_back', 0) + 1
        return 'put back'

    def show_main_window(self):
        if not self.isVisible():
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def showEvent(self, event):
        super().showEvent(event)
        self.apply_show_on_all_spaces()     # before the window is put on the screen
        # the Dock: unless it is kept showing, this window hides it in a moment (hide_dock below) → no
        # room is kept for it; then the real state is read again once the Dock has settled
        _screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        if getattr(self, '_force_show_dock', False) and _screen is not None:
            self.apply_dock_insets(geometry=_screen.geometry())
        else:
            self.apply_dock_insets((0, 0, 0))
        for _delay in (350, 900, 1800):
            QTimer.singleShot(_delay, self._recheck_dock)
        _size_before = self.size()
        rendered = self.adapt_to_screen()  # 每次 show 都刷新几何
        # the Stage Manager mark: with the marks from the start it is already on (mark_windows_at_birth);
        # touching the window's marks now, with the Dock icon there, would take the launcher off other
        # apps' full-screen Spaces (tried on the real screen 2026-11-26: only the normal desktop was left)
        if not self._spaces_marks_from_birth:
            raspberry_ui.keep_out_of_stage_manager(self)
        # … and once it is up: still covering the screen it was put on? (put back once, nothing is fought over)
        self._show_serial = getattr(self, '_show_serial', 0) + 1
        QTimer.singleShot(self.SHOW_LANDING_CHECK_MS, lambda serial=self._show_serial, wanted=QRect(self.geometry()): self._check_show_landing(serial, wanted))
        self.backdrop.prepare(self.geometry())  # this screen's clean wallpaper, blurred
        self.menu_bar_cover.start()             # over the menu bar until this window is hidden
        if not rendered:
            self.display_apps(self.filtered_apps, self.current_page)
        if self.size() != _size_before:
            # the screen has another size than at the last opening and a group was left open: it is
            # fitted here, before the window is on the screen (it used to be queued → the old look showed)
            self._refit_open_group()
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
        self.menu_bar_cover.follow()            # gone with the launcher, at once
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
                status, name = self.refresh_app_icon(selected_files[0])
                if status == 'info_plist_error':
                    text = self.tr(f"Failed to parse Info.plist: %n").replace('%n', name)
                elif status == 'itunes_plist_error':
                    text = self.tr(f"Failed to parse iTunesMetadata.plist: %n").replace('%n', name)
                elif status == 'no_icon':
                    text = self.tr("Unable to retrieve the icon for this app.")
                elif status == 'updated':
                    text = self.tr(f"The icon cache for %n has been updated.").replace('%n', name)
                else:
                    text = self.tr(f"The icon of %n has been cached, but the app is not in the main interface list.").replace('%n', name)
                msg = CustomMessageBox(text, parent=self, buttons=(self.tr("OK"),))
                msg.exec()

    def refresh_app_icon(self, app_path):
        """One app's icon is read again and cached (the menu's "Update the specified app icon cache" and
        an assistant app's tool both use it; no notice here). Returns (status, text): 'updated' /
        'cached_only' (not in the list) / 'no_icon' with the app's name, or 'info_plist_error' /
        'itunes_plist_error' with the error."""
        # the dialog hands an app over as a folder ("/Applications/X.app/"): the list knows it
        # without the last slash, and "X.app/"[:-4] would not be its name either
        app_path = os.path.normpath(app_path)
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
                return 'info_plist_error', str(e)
        # 2. iOS 应用的 iTunesMetadata.plist
        elif os.path.exists(itunes_plist):
            try:
                with open(itunes_plist, 'rb') as f:
                    plist = plistlib.load(f)
                name = plist.get('title') or plist.get('itemName') or os.path.basename(app_path)[:-4]
            except Exception as e:
                return 'itunes_plist_error', str(e)
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
            return 'no_icon', name
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
            return 'updated', name
        return 'cached_only', name

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
        set_dock_autohide(True)

    def show_dock(self):
        # if getattr(self, '_force_show_dock', False):
        #     return  # 如果强制显示 Dock，则不执行
        set_dock_autohide(False)

    def wheelEvent(self, event):
        # 动画期间禁翻，避免状态冲突
        if getattr(self, "_is_animating", False):
            event.accept()
            return
        # an open group floats on the grid: the pages behind it stay where they are
        if self.group_widget is not None and self.group_widget.isVisible():
            event.accept()
            return

        pixel_delta = event.pixelDelta()
        angle_delta = event.angleDelta()
        dx = pixel_delta.x() if pixel_delta.x() != 0 else int(angle_delta.x() / 2)

        if dx != 0:
            # the page on screen and the one coming in move together under the fingers (PageSlide)
            self._page_slide.wheel(dx, event.phase() == Qt.ScrollPhase.ScrollMomentum)
            event.accept()
            return

        # 正在触控板滑动会话时，忽略垂直滚动，避免干扰
        if self._page_slide.active():
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
            if isinstance(btn, GroupButton):
                btn.bind_fade(effect)

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

    def animate_icons_in(self):
        """The launcher opens (Ryan 2026-11-16: 「从屏幕中间向四周放射性淡入，不用路程很长，就一点点
        就行」): every icon fades in while it moves a short way outwards, away from the middle of the
        grid, to its place; the ones further out start a moment later."""
        self._finish_reflow()
        self._settle_grid()
        grid = self.main_content.grid_widget
        centre = QPointF(grid.width() / 2.0, grid.height() / 2.0)
        buttons = [w for w in grid.findChildren(QPushButton, options=Qt.FindChildOption.FindDirectChildrenOnly)
                   if isinstance(w, (AppButton, GroupButton))]
        reach = max([math.hypot(b.x() + b.width() / 2.0 - centre.x(), b.y() + b.height() / 2.0 - centre.y())
                     for b in buttons] + [1.0])
        anim_group = QParallelAnimationGroup(self)
        effects = []
        for btn in buttons:
            final = btn.pos()
            dx = final.x() + btn.width() / 2.0 - centre.x()
            dy = final.y() + btn.height() / 2.0 - centre.y()
            dist = math.hypot(dx, dy)
            shift = min(float(ENTRANCE_SHIFT), dist * 0.12)
            start = final if dist < 1.0 else QPoint(int(round(final.x() - dx / dist * shift)),
                                                    int(round(final.y() - dy / dist * shift)))
            wait = ENTRANCE_STAGGER * dist / reach          # the share of the time it waits first
            effect = btn.graphicsEffect()
            if not isinstance(effect, QGraphicsOpacityEffect):
                effect = QGraphicsOpacityEffect(btn)
                btn.setGraphicsEffect(effect)
                if isinstance(btn, GroupButton):
                    btn.bind_fade(effect)
            effect.setOpacity(0.0)
            effects.append((btn, effect))
            btn.move(start)

            opacity_anim = QPropertyAnimation(effect, b"opacity", anim_group)
            opacity_anim.setDuration(ENTRANCE_MS)
            opacity_anim.setKeyValueAt(0.0, 0.0)
            opacity_anim.setKeyValueAt(wait, 0.0)
            opacity_anim.setKeyValueAt(min(1.0, wait + 0.6), 1.0)
            opacity_anim.setKeyValueAt(1.0, 1.0)

            pos_anim = QPropertyAnimation(btn, b"pos", anim_group)
            pos_anim.setDuration(ENTRANCE_MS)
            pos_anim.setKeyValueAt(0.0, start)
            pos_anim.setKeyValueAt(wait, start)
            pos_anim.setKeyValueAt(1.0, final)
            pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

            anim_group.addAnimation(opacity_anim)
            anim_group.addAnimation(pos_anim)

        def done(effects=effects):
            # the icons are drawn directly again (an opacity effect draws each through a picture)
            for btn, effect in effects:
                try:
                    if not sip.isdeleted(btn) and btn.graphicsEffect() is effect:
                        if isinstance(btn, GroupButton):
                            btn.icon_label.set_glass_opacity(1.0)
                        btn.setGraphicsEffect(None)
                except RuntimeError:
                    pass

        anim_group.finished.connect(done)
        # the glass under the group tiles moves at once, Qt draws on its next turn: draw with it
        if buttons:
            driver = QVariantAnimation(anim_group)
            driver.setDuration(ENTRANCE_MS)
            driver.setStartValue(0.0)
            driver.setEndValue(1.0)
            driver.valueChanged.connect(lambda _v, grid=grid: grid.repaint() if not sip.isdeleted(grid) and grid.isVisible() else None)
            anim_group.addAnimation(driver)
        anim_group.start()
        self._entrance = anim_group

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
        self._swap_in_main_order(idx, idx - 1)
        self.sync_group_order()
        # 计算新页码
        new_page = self.page_of_index(idx - 1)
        self.current_page = new_page
        self.display_apps(self.filtered_apps, self.current_page)
        # 聚焦到新位置
        self.focus_index = (idx - 1) - self.page_start(new_page)
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
        self._swap_in_main_order(idx, idx + 1)
        self.sync_group_order()
        new_page = self.page_of_index(idx + 1)
        self.current_page = new_page
        self.display_apps(self.filtered_apps, self.current_page)
        self.focus_index = (idx + 1) - self.page_start(new_page)
        self.set_focus_by_global_index(idx + 1)

    def _swap_in_main_order(self, a, b):
        """Two neighbours change places (with separate pages: also their pages, when they are on two)."""
        order = self.main_order
        order[a], order[b] = order[b], order[a]
        if self.pages_are_separate():
            page_a, page_b = order[a][1].get('_page'), order[b][1].get('_page')
            order[a][1]['_page'], order[b][1]['_page'] = page_b, page_a
            self._normalise_pages()

    def set_focus_by_global_index(self, global_idx):
        # 在当前页找到对应按钮并聚焦
        grid_layout = self.main_content.grid_layout
        page_start = self.page_start(self.current_page)
        rel_idx = global_idx - page_start
        btns = []
        for i in range(grid_layout.count()):
            w = grid_layout.itemAt(i).widget()
            if isinstance(w, (AppButton, GroupButton)):
                btns.append(w)
        if 0 <= rel_idx < len(btns):
            self.focused_btn = btns[rel_idx]
            self.focused_btn.icon_label.setStyleSheet(
                raspberry_ui.focus_ring_qss()
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
        if self.pages_are_separate():
            self._saved_pages = {self._order_id(typ, obj): obj['_page'] for typ, obj in self.main_order
                                 if isinstance(obj.get('_page'), int)}
            try:
                with open(PAGES_FILE, "w", encoding="utf-8") as f:
                    json.dump(self._saved_pages, f, ensure_ascii=False)
            except Exception:
                pass

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

    def copy_ai_apps_setup(self):
        """The lines an AI app's MCP settings take (the bridge: this program with --mcp-stdio), to the clipboard."""
        import app_mcp_host
        QGuiApplication.clipboard().setText(app_mcp_host.bridge_setup_json())
        raspberry_ui.raspberry_alert(self, self.tr(
            "The setup is copied. Paste it into the MCP settings of your AI app (for example Claude Desktop or Cursor). "
            "The AI app can then use the tools of Raspberry and of your other apps on this Mac."),
            self.tr("Use in other AI apps"))

    def backup_groups(self):
        self.write_backup()
        # 提示
        msg = CustomMessageBox(self.tr("Backup completed!"), parent=self, buttons=(self.tr("OK"),))
        msg.exec()

    def write_backup(self):
        """The backup itself, without the notice (the menu and an assistant app's tool both use it).
        Returns the new backup folder."""
        # 备份目录
        backup_base = Path(BACKUPS_DIR)
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
            Path(DISPLAY_NAME_MAP_FILE),
            Path(ALIAS_NAME_MAP_FILE),
            Path(HIDDEN_APPS_FILE),
        ]
        icon_cache_src = Path(ICON_CACHE_DIR)
        icon_cache_dst = backup_dir / "icon_cache"

        # 复制文件
        for f in files:
            if f.exists():
                shutil.copy2(f, backup_dir / f.name)
        # 复制文件夹
        if icon_cache_src.exists():
            shutil.copytree(icon_cache_src, icon_cache_dst, dirs_exist_ok=True)
        return backup_dir

    def restore_backup(self):
        # 选择备份文件夹
        backup_base = str(BACKUPS_DIR)
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setDirectory(backup_base)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dialog.setWindowTitle(self.tr("Select a backup folder to restore"))
        if dialog.exec():
            selected_dirs = dialog.selectedFiles()
            if selected_dirs:
                backup_dir = Path(selected_dirs[0])
                # a backup made before the data moved holds the files under their old names
                # (".launchpad_groups.json" …), a newer one under today's ("groups.json" …): both restore
                wanted = [(new, old) for old, new in LEGACY_DATA_FILES[:6]] + [(HIDDEN_APPS_FILE, None)]
                found = {}
                for new, old in wanted:
                    for name in (os.path.basename(new), old):
                        if name and (backup_dir / name).exists():
                            found[new] = backup_dir / name
                            break
                missing_required = [os.path.basename(new) for new, _old in wanted[:4] if new not in found]
                if missing_required:
                    msg = CustomMessageBox(self.tr(f"Missing files: %n").replace('%n', ', '.join(missing_required)), parent=self, buttons=(self.tr("OK"),))
                    msg.exec()
                    return
                # 覆盖文件
                for new, src in found.items():
                    shutil.copy2(src, new)
                # 覆盖 icon cache
                icon_cache_src = backup_dir / "icon_cache"
                if not icon_cache_src.exists():
                    icon_cache_src = backup_dir / LEGACY_ICON_CACHE
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
        """Take the screen the mouse is on. True = the icons were laid out here (never now: the
        caller does it)."""
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        geo: QRect = screen.geometry()
        if geo != self.geometry():
            self.setGeometry(geo)
            self.main_content.setGeometry(self.rect())
            if self.group_widget and self.group_widget.isVisible():
                QTimer.singleShot(0, self.refit_group_panel)
        return False

    def change_language(self, code):
        # 1) 记录到配置
        cfg_file = Path(LANG_FILE)
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
        files_to_delete = [MAIN_ORDER_FILE, GROUPS_FILE, APP_PATHS_FILE, APP_ORDER_FILE]
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
    def _clear_main_grid(self):
        grid_layout = self.main_content.grid_layout
        # 清布局里的
        for i in reversed(range(grid_layout.count())):
            w = grid_layout.itemAt(i).widget()
            if w:
                w.hide()            # first: else Qt's pending "show" makes it a window of its own
                w.setParent(None)
                w.deleteLater()
        # 保险：再清 grid_widget 的子控件
        for w in self.main_content.grid_widget.findChildren(QWidget):
            if w is self.main_content.grid_widget:
                continue
            w.hide()            # first: else Qt's pending "show" makes it a window of its own
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
        path = setting_path("keyboard_mode")
        try:
            if os.path.exists(path):
                return open(path, "r", encoding="utf-8").read().strip() != "0"
        except Exception:
            pass
        # 默认启用新键盘映射
        return True

    def write_keyboard_mode_setting(self, enabled: bool):
        path = setting_path("keyboard_mode")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("1" if enabled else "0")
        except Exception:
            pass

    def toggle_clear_search_on_close(self):
        self.clear_search_on_close = self.clear_search_on_close_action.isChecked()
        self.write_clear_search_on_close_setting(self.clear_search_on_close)

    def read_clear_search_on_close_setting(self):
        path = setting_path("clear_search_on_close")
        try:
            if os.path.exists(path):
                return open(path, "r", encoding="utf-8").read().strip() == "1"
        except Exception:
            pass
        # 默认关闭
        return False

    def write_clear_search_on_close_setting(self, enabled: bool):
        path = setting_path("clear_search_on_close")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("1" if enabled else "0")
        except Exception:
            pass

    def toggle_compact_mode(self):
        self.compact_mode = self.compact_mode_action.isChecked()
        self.write_compact_mode_setting(self.compact_mode)
        before = self._grid_snapshot() if self.isVisible() else None
        self.display_apps(self.filtered_apps, self.current_page)
        if before is not None:          # the icons slide together / apart
            self._settle_grid()
            self._animate_reflow(before)

    # ── "Show on all Spaces" (learnt from Broccoli's main window) ──
    def read_all_spaces_setting(self):
        try:
            return open(setting_path("show_on_all_spaces"), "r", encoding="utf-8").read().strip() == "1"
        except Exception:
            return False        # off, as in Broccoli

    def write_all_spaces_setting(self, enabled: bool):
        try:
            with open(setting_path("show_on_all_spaces"), "w", encoding="utf-8") as f:
                f.write("1" if enabled else "0")
        except Exception:
            pass

    def _native_ns_window(self):
        """This window's NSWindow (None before it exists / off the Mac screen)."""
        if sys.platform != 'darwin' or QGuiApplication.platformName() != 'cocoa':
            return None
        if not self.testAttribute(Qt.WidgetAttribute.WA_WState_Created):
            return None
        try:
            return objc.objc_object(c_void_p=int(self.winId())).window()
        except Exception:
            return None

    def apply_show_on_all_spaces(self, enabled=None) -> bool:
        """On: the launcher is on every Space (it follows when you switch) and can open over another
        app's full-screen Space. Off: it stays on the Space it was opened on. Set on the NSWindow, so
        it is set again at every show."""
        if enabled is not None:
            self._show_on_all_spaces = bool(enabled)
        return raspberry_ui.apply_space_behavior(self._native_ns_window(), self._show_on_all_spaces)

    def mark_windows_at_birth(self) -> bool:
        """At the start, while Raspberry has no Dock icon yet: the launcher and the windows that live as
        long as it does (update, About, guide) get their marks now — these reach other apps'
        full-screen Spaces. Returns whether that was done."""
        if not self._show_on_all_spaces or dock_icon_shown():
            return False
        done = self.apply_show_on_all_spaces()
        raspberry_ui.keep_out_of_stage_manager(self)     # now, not at each show (see showEvent)
        for name in ('win_update', 'win_about', 'win_permission'):
            window = getattr(self, name, None)
            if window is not None:
                window.winId()                    # its system window is made now
                raspberry_ui.follow_all_spaces(window)
        self._spaces_marks_from_birth = bool(done)
        return self._spaces_marks_from_birth

    def toggle_show_on_all_spaces(self, checked=None):
        enabled = bool(self.all_spaces_action.isChecked())
        self.write_all_spaces_setting(enabled)
        self.apply_show_on_all_spaces(enabled)
        raspberry_ui.set_all_spaces(enabled)      # the windows opened beside it follow
        # marks switched on while the Dock icon is there reach the other desktops, not full-screen
        # apps; the ones from the start are gone as soon as the switch was off once
        self._spaces_marks_from_birth = False
        if enabled:
            self.ask_restart_for_full_screen()

    def ask_restart_for_full_screen(self):
        RestartMessageBox(self.tr("Show on all Spaces is on.\nTo open over full-screen apps too, Raspberry will restart."),
                          parent=self, buttons=(self.tr("OK"), self.tr("Later"))).exec()

    # 仅保存 bool，别保存边距
    def read_compact_mode_setting(self):
        path = setting_path("compact_mode")
        try:
            if os.path.exists(path):
                return open(path, "r", encoding="utf-8").read().strip() == "1"
        except Exception:
            pass
        return False

    def write_compact_mode_setting(self, enabled: bool):
        path = setting_path("compact_mode")
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
        """An app's icon was dropped between two icons of the page on screen: it goes there (among the
        apps: the grid keeps a page's groups in front, see AppGridWidget). With separate pages it now
        belongs to this page. While searching nothing is sorted."""
        if self._is_searching():
            return
        if app_path.startswith(GROUP_DRAG_PREFIX):
            self.on_drop_group_in_main(app_path[len(GROUP_DRAG_PREFIX):], slot_index_on_page)
            return
        src_app = next((a for a in self.apps if a['path'] == app_path), None)
        old_index = next((i for i, (typ, obj) in enumerate(self.main_order) if typ == 'app' and obj is src_app), None)
        if src_app is None or old_index is None:
            return
        before = self._grid_snapshot() if self.isVisible() else None
        page = self.current_page
        start = self.page_start(page)
        target = start + max(0, int(slot_index_on_page))
        del self.main_order[old_index]
        if old_index < target:
            target -= 1
        if old_index < start:
            start -= 1
        if self.pages_are_separate():
            on_page = sum(1 for _typ, obj in self.main_order if obj.get('_page') == page)
        else:
            on_page = max(0, min(self.items_per_page, len(self.main_order) - start))
        target = max(start, min(target, start + on_page, len(self.main_order)))
        if self.pages_are_separate():
            src_app['_page'] = page
        self.main_order.insert(target, ('app', src_app))
        self._after_main_order_changed(before)

    def on_drop_group_in_main(self, group_name: str, slot_index_on_page: int):
        """A group's icon was dropped between two icons of the page on screen: it goes there, among
        the groups standing first (groups stay in front of the apps). With separate pages it now
        belongs to this page."""
        old_index = next((i for i, (typ, obj) in enumerate(self.main_order)
                          if typ == 'group' and obj['name'] == group_name), None)
        if old_index is None:
            return
        group = self.main_order[old_index][1]
        before = self._grid_snapshot() if self.isVisible() else None
        page = self.current_page
        start = self.page_start(page)
        target = start + max(0, int(slot_index_on_page))
        del self.main_order[old_index]
        if old_index < target:
            target -= 1
        if old_index < start:
            start -= 1
        if self.pages_are_separate():
            end = start
            while end < len(self.main_order) and self.main_order[end][0] == 'group' \
                    and self.main_order[end][1].get('_page') == page:
                end += 1
            group['_page'] = page
        else:                                   # one long row: all the groups stand first
            end = 0
            while end < len(self.main_order) and self.main_order[end][0] == 'group':
                end += 1
            start = min(start, end)
        target = max(start, min(target, end))
        self.main_order.insert(target, ('group', group))
        self._after_main_order_changed(before)

    def read_anim_speed_setting(self):
        path = setting_path("anim_speed")
        try:
            if os.path.exists(path):
                return int(open(path, "r", encoding="utf-8").read().strip())
        except Exception:
            pass
        return 8000  # 默认值

    def write_anim_speed_setting(self, val):
        path = setting_path("anim_speed")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(str(val))
        except Exception:
            pass

    def on_anim_speed_changed(self, val):
        self.page_anim_speed = val
        self.anim_speed_value_label.setText(str(val))
        self.write_anim_speed_setting(val)

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


class WindowAbout(QWidget):  # 增加说明页面(About)
    def __init__(self):
        super().__init__()
        self.init_ui()
        make_native_glass_window(self)   # system traffic lights + window glass (style book 5.7.2)

    def init_ui(self):
        self.setUpMainWindow()
        self.setFixedSize(400, 600)
        self.center()
        self.setFocus()

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
        make_native_glass_window(self, kind=Qt.WindowType.Dialog)
        self.setFixedSize(440, 430)

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
        make_native_glass_window(self, kind=Qt.WindowType.Dialog)
        self.setFixedSize(440, 430)

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
        make_native_glass_window(self, kind=Qt.WindowType.Dialog)
        self.setFixedSize(440, 430)

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
        make_native_glass_window(self, kind=Qt.WindowType.Dialog)
        self.setFixedSize(440, 430)

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


# ---- One-click in-app update: download → verify → install → relaunch (Broccoli's, 2026-11-18;
# Ryan: 「有没有和 broccoli 一样做更新机制？想做成一样的」) ----
# Every release ships one notarized DMG on GitHub (the asset's `digest` = its sha256).
#  1. WindowUpdate downloads it into ~/Library/Caches/com.ryanthehito.raspberry/Updates with a progress
#     bar (a .part file, resumed with an HTTP Range request), then checks size + sha256.
#  2. It mounts the DMG read-only ("Y" answers a licence agreement), copies Raspberry.app into a hidden
#     folder NEXT TO the running bundle (same volume → the swap is a rename) and requires the copy to
#     satisfy RASPBERRY_UPDATE_CODE_REQUIREMENT (Developer ID + this team + this bundle id).
#  3. Raspberry quits normally. AFTER app.exec() returns, this process swaps the bundles (macOS App
#     Management lets an app modify apps signed by its own Team ID). Groups, order and settings live
#     outside the app (Application Support/<bundle id>), so the swap keeps them.
#  4. A detached waiter reopens the app once this PID is gone; the new build deletes the previous
#     bundle on its first start and reports the result.
def _ut(text: str) -> str:
    """The update texts, all in WindowUpdate's translation context."""
    return QCoreApplication.translate("WindowUpdate", text)


RASPBERRY_UPDATE_LATEST_API = 'https://api.github.com/repos/Ryan-the-hito/Raspberry/releases/latest'
RASPBERRY_UPDATE_RELEASES_URL = 'https://github.com/Ryan-the-hito/Raspberry/releases'
RASPBERRY_UPDATE_BUNDLE_ID = BUNDLE_ID
RASPBERRY_UPDATE_TEAM_ID = '49C7YMHM5Q'
RASPBERRY_UPDATE_CODE_REQUIREMENT = (
    'anchor apple generic and identifier "%s"'
    ' and certificate 1[field.1.2.840.113635.100.6.2.6] exists'      # Developer ID CA
    ' and certificate leaf[field.1.2.840.113635.100.6.1.13] exists'  # Developer ID Application
    ' and certificate leaf[subject.OU] = "%s"' % (RASPBERRY_UPDATE_BUNDLE_ID, RASPBERRY_UPDATE_TEAM_ID))
RASPBERRY_UPDATE_CACHE_DIR = os.path.join(CACHE_DIR, 'Updates')
RASPBERRY_UPDATE_RESULT_PATH = os.path.join(RASPBERRY_UPDATE_CACHE_DIR, 'last_install.json')
RASPBERRY_UPDATE_STAGING_DIRNAME = '.Raspberry-update'
RASPBERRY_UPDATE_SPARE_BYTES = 512 * 1024 * 1024   # free space kept beyond the copy itself
_RASPBERRY_UPDATE_FS_LOCK = threading.Lock()   # staging vs. the startup cleanup of the same folder
_RASPBERRY_PENDING_UPDATE_INSTALL = None        # set right before quitting for an install


class RaspberryUpdateError(Exception):
    """A user-presentable reason the update stopped (already translated)."""


class RaspberryUpdateCanceled(RaspberryUpdateError):
    pass


def raspberry_parse_version(text):
    match = re.search(r'(\d+)\.(\d+)\.(\d+)', str(text or ''))
    return tuple(int(part) for part in match.groups()) if match else None


def raspberry_is_newer_version(candidate, current) -> bool:
    newer, older = raspberry_parse_version(candidate), raspberry_parse_version(current)
    return bool(newer and older and newer > older)


def raspberry_running_app_bundle():
    """The .app bundle this process runs from (packaged builds only)."""
    if not getattr(sys, 'frozen', False):
        return None
    try:
        bundle = Path(sys.executable).resolve().parents[2]
    except Exception:
        return None
    if bundle.suffix != '.app' or not (bundle / 'Contents' / 'Info.plist').is_file():
        return None
    return bundle


def raspberry_update_install_blocker(bundle) -> str:
    """Why this copy cannot replace itself ('' when it can)."""
    if sys.platform != 'darwin':
        return _ut('automatic install needs macOS')
    if bundle is None:
        return _ut('Raspberry is not running from an installed app')
    if '/AppTranslocation/' in str(bundle):
        return _ut('macOS is running Raspberry from a temporary copy; move it into Applications first')
    # renaming the bundle into another folder needs write access to it and its parent
    if not os.access(str(bundle.parent), os.W_OK) or not os.access(str(bundle), os.W_OK):
        return _ut('no permission to replace {path}').format(path=str(bundle))
    return ''


def raspberry_fetch_latest_release():
    """Latest release from the GitHub API: tag, version and its DMG asset
    (dmg_* fields stay empty when the release carries no DMG)."""
    import requests
    response = requests.get(RASPBERRY_UPDATE_LATEST_API, timeout=(4, 6),
                            headers={'Accept': 'application/vnd.github+json'})
    if not response.ok:
        return None
    data = response.json() or {}
    tag = str(data.get('tag_name', '') or '').strip()
    if not re.fullmatch(r'v\d+\.\d+\.\d+', tag):
        return None
    info = {'tag': tag, 'version': tag[1:], 'dmg_name': '', 'dmg_url': '', 'dmg_size': 0, 'dmg_sha256': ''}
    dmgs = [asset for asset in (data.get('assets') or []) if isinstance(asset, dict)
            and str(asset.get('name', '')).lower().endswith('.dmg')
            and str(asset.get('state', 'uploaded')) == 'uploaded'
            and str(asset.get('browser_download_url', '')).startswith('https://')]
    dmgs.sort(key=lambda asset: not str(asset.get('name', '')).lower().startswith('raspberry'))
    if dmgs:
        asset = dmgs[0]
        digest = str(asset.get('digest') or '')
        info.update(dmg_name=str(asset.get('name')),
                    dmg_url=str(asset.get('browser_download_url')),
                    dmg_size=int(asset.get('size') or 0),
                    dmg_sha256=digest[7:].lower() if digest.lower().startswith('sha256:') else '')
    return info


def _raspberry_sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(4 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def _raspberry_update_file_matches(path: str, size: int, sha256: str) -> bool:
    try:
        if size and os.path.getsize(path) != size:
            return False
        return not sha256 or _raspberry_sha256_file(path) == sha256
    except OSError:
        return False


def raspberry_download_update_dmg(info: dict, progress, cancel_event, status=None) -> str:
    """Download the release DMG into the cache (resuming an earlier .part), verify size + sha256 and
    return its path. progress(done, total) and status(text) run on the calling worker thread;
    cancel_event aborts between chunks and keeps the .part for the next attempt."""
    status = status or (lambda _text: None)
    url = str(info.get('dmg_url') or '')
    if not url:
        raise RaspberryUpdateError(_ut('This release has no installer package.'))
    size = int(info.get('dmg_size') or 0)
    sha256 = str(info.get('dmg_sha256') or '').lower()
    os.makedirs(RASPBERRY_UPDATE_CACHE_DIR, exist_ok=True)
    name = re.sub(r'[^A-Za-z0-9._-]+', '_', str(info.get('dmg_name') or '')).strip('.') or 'Raspberry-update.dmg'
    final_path = os.path.join(RASPBERRY_UPDATE_CACHE_DIR, name)
    part_path = final_path + '.part'
    if os.path.isfile(final_path):
        status(_ut('Verifying the download…'))
        if _raspberry_update_file_matches(final_path, size, sha256):
            return final_path
        os.remove(final_path)
    have = os.path.getsize(part_path) if os.path.isfile(part_path) else 0
    if size and have > size:
        os.remove(part_path)
        have = 0
    if not size or have < size:
        headers = {'Range': 'bytes=%d-' % have} if have else {}
        import requests
        try:
            with requests.get(url, stream=True, timeout=(10, 60), headers=headers) as response:
                if have and response.status_code == 206:
                    mode = 'ab'
                elif response.status_code == 200:
                    mode, have = 'wb', 0
                else:
                    raise RaspberryUpdateError(
                        _ut('Download failed (HTTP {code}).').format(code=response.status_code))
                total = size or (have + int(response.headers.get('Content-Length') or 0))
                progress(have, total)
                with open(part_path, mode) as handle:
                    for chunk in response.iter_content(chunk_size=1 << 20):
                        if cancel_event.is_set():
                            raise RaspberryUpdateCanceled(_ut('Download canceled.'))
                        if chunk:
                            handle.write(chunk)
                            have += len(chunk)
                            progress(have, total)
        except RaspberryUpdateError:
            raise
        except Exception as exc:
            if cancel_event.is_set():
                raise RaspberryUpdateCanceled(_ut('Download canceled.')) from exc
            raise RaspberryUpdateError(_ut('Download interrupted: {err}').format(err=exc)) from exc
    status(_ut('Verifying the download…'))
    if not _raspberry_update_file_matches(part_path, size, sha256):
        try:
            os.remove(part_path)
        except OSError:
            pass
        raise RaspberryUpdateError(_ut('The download is damaged (checksum mismatch). Please try again.'))
    os.replace(part_path, final_path)
    return final_path


def _raspberry_attach_dmg(dmg_path: str, mountpoint: str) -> None:
    env = dict(os.environ, PAGER='/bin/cat')
    commands = (
        ['/usr/bin/hdiutil', 'attach', '-nobrowse', '-readonly', '-noautoopen', '-noverify',
         '-mountpoint', mountpoint, dmg_path],
        # hdiutil is deprecated from macOS 27 on; diskutil image is its successor
        ['/usr/sbin/diskutil', 'image', 'attach', '--mountOptions', 'nobrowse', '--readOnly',
         '--mountPoint', mountpoint, dmg_path],
    )
    for command in commands:
        if not os.path.exists(command[0]):
            continue
        try:
            # a release DMG may show a licence agreement before mounting; "Y" accepts it
            subprocess.run(command, input=b'Y\n', capture_output=True, timeout=300, env=env)
        except Exception:
            continue
        if os.path.ismount(mountpoint):
            return
    raise RaspberryUpdateError(_ut('Could not open the downloaded installer.'))


def _raspberry_detach_dmg(mountpoint: str) -> None:
    for command in (['/usr/bin/hdiutil', 'detach', mountpoint, '-quiet'],
                    ['/usr/bin/hdiutil', 'detach', mountpoint, '-force', '-quiet'],
                    ['/usr/sbin/diskutil', 'eject', mountpoint]):
        if not os.path.ismount(mountpoint):
            break
        if not os.path.exists(command[0]):
            continue
        try:
            subprocess.run(command, capture_output=True, timeout=60)
        except Exception:
            pass
    if not os.path.ismount(mountpoint):
        try:
            os.rmdir(mountpoint)
        except OSError:
            pass


def _raspberry_bundle_info(bundle) -> dict:
    try:
        with open(Path(bundle) / 'Contents' / 'Info.plist', 'rb') as handle:
            data = plistlib.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _raspberry_tree_size(root) -> int:
    total = 0
    for folder, _dirs, files in os.walk(str(root)):
        for name in files:
            try:
                total += os.lstat(os.path.join(folder, name)).st_size
            except OSError:
                pass
    return total


def raspberry_verify_update_bundle(bundle) -> str:
    """Return the bundle's version once its whole signature satisfies
    RASPBERRY_UPDATE_CODE_REQUIREMENT; raise RaspberryUpdateError otherwise."""
    info = _raspberry_bundle_info(bundle)
    if info.get('CFBundleIdentifier') != RASPBERRY_UPDATE_BUNDLE_ID:
        raise RaspberryUpdateError(_ut('The installer does not contain Raspberry.'))
    try:
        result = subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict',
                                 '-R=' + RASPBERRY_UPDATE_CODE_REQUIREMENT, str(bundle)],
                                capture_output=True, timeout=900)
    except Exception as exc:
        raise RaspberryUpdateError(_ut('Could not check the signature: {err}').format(err=exc)) from exc
    if result.returncode != 0:
        logging.warning('Update bundle rejected by codesign: %s',
                        result.stderr.decode('utf-8', 'replace')[-800:])
        raise RaspberryUpdateError(
            _ut('The update is not signed by the Raspberry developer, so it was not installed.'))
    return str(info.get('CFBundleShortVersionString') or '')


def raspberry_stage_update(dmg_path: str, target, status=None) -> dict:
    """Copy the DMG's Raspberry.app into <target's folder>/.Raspberry-update and verify the copy.
    Returns the pending-install record applied after the event loop ends
    (raspberry_apply_pending_update_install)."""
    import tempfile
    status = status or (lambda _text: None)
    target = Path(target)
    staging_root = target.parent / RASPBERRY_UPDATE_STAGING_DIRNAME
    staged = staging_root / target.name
    with _RASPBERRY_UPDATE_FS_LOCK:
        try:
            if staging_root.exists():
                shutil.rmtree(staging_root, ignore_errors=True)
            staging_root.mkdir(parents=True, exist_ok=True)
            os.makedirs(RASPBERRY_UPDATE_CACHE_DIR, exist_ok=True)
            mountpoint = tempfile.mkdtemp(prefix='mnt-', dir=RASPBERRY_UPDATE_CACHE_DIR)
            try:
                status(_ut('Opening the installer…'))
                _raspberry_attach_dmg(dmg_path, mountpoint)
                source = next((entry for entry in sorted(Path(mountpoint).iterdir())
                               if entry.suffix == '.app' and entry.is_dir() and not entry.is_symlink()
                               and _raspberry_bundle_info(entry).get('CFBundleIdentifier') == RASPBERRY_UPDATE_BUNDLE_ID),
                              None)
                if source is None:
                    raise RaspberryUpdateError(_ut('The installer does not contain Raspberry.'))
                # the copy sits next to the installed app until the swap: room for it first
                need = _raspberry_tree_size(source) + RASPBERRY_UPDATE_SPARE_BYTES
                free = shutil.disk_usage(str(staging_root)).free
                if free < need:
                    raise RaspberryUpdateError(
                        _ut('Not enough disk space: the update needs about {need} GB free ({free} GB now).').format(
                            need='%.1f' % (need / 1e9), free='%.1f' % (free / 1e9)))
                status(_ut('Copying the new version…'))
                copied = subprocess.run(['/usr/bin/ditto', str(source), str(staged)],
                                        capture_output=True, timeout=1800)
                if copied.returncode != 0 or not staged.is_dir():
                    raise RaspberryUpdateError(_ut('Could not copy the new version: {err}').format(
                        err=copied.stderr.decode('utf-8', 'replace').strip()[-300:]))
            finally:
                _raspberry_detach_dmg(mountpoint)
            subprocess.run(['/usr/bin/xattr', '-dr', 'com.apple.quarantine', str(staged)],
                           capture_output=True, timeout=300)
            status(_ut('Checking the developer signature…'))
            version = raspberry_verify_update_bundle(staged)
            if raspberry_is_newer_version(VERSION, version):
                raise RaspberryUpdateError(
                    _ut('The installer holds an older version (v{v}); nothing was changed.').format(v=version))
        except Exception as exc:
            shutil.rmtree(staging_root, ignore_errors=True)
            if isinstance(exc, RaspberryUpdateError):
                raise
            raise RaspberryUpdateError(_ut('Could not prepare the update: {err}').format(err=exc)) from exc
    return {'target': str(target), 'staged': str(staged),
            'backup': str(staging_root / ('previous-' + target.name)),
            'version': version, 'dmg': str(dmg_path)}


def _raspberry_write_update_result(record: dict) -> None:
    try:
        os.makedirs(RASPBERRY_UPDATE_CACHE_DIR, exist_ok=True)
        with open(RASPBERRY_UPDATE_RESULT_PATH, 'w', encoding='utf-8') as handle:
            json.dump(record, handle, ensure_ascii=False)
    except Exception:
        pass


def raspberry_take_last_update_result() -> dict:
    """The record the previous run left after an install attempt (read once)."""
    try:
        with open(RASPBERRY_UPDATE_RESULT_PATH, 'r', encoding='utf-8') as handle:
            record = json.load(handle)
    except Exception:
        return {}
    try:
        os.remove(RASPBERRY_UPDATE_RESULT_PATH)
    except OSError:
        pass
    return record if isinstance(record, dict) else {}


def _raspberry_spawn_relauncher(app_path: str) -> None:
    """Reopen app_path once this process has exited (force-kill after ~60 s if it hangs).
    Double-forked: the waiter is reparented to launchd."""
    waiter = ('pid=$1; app=$2; n=0; '
              'while kill -0 "$pid" 2>/dev/null; do '
              'n=$((n+1)); if [ "$n" -ge 300 ]; then kill -9 "$pid" 2>/dev/null; sleep 1; break; fi; '
              'sleep 0.2; done; sleep 0.5; /usr/bin/open "$app"')
    try:
        subprocess.Popen(['/bin/sh', '-c', '(' + waiter + ') </dev/null >/dev/null 2>&1 &',
                         'raspberry-relaunch', str(os.getpid()), str(app_path)],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True, close_fds=True).wait(timeout=10)
    except Exception:
        pass


def raspberry_apply_pending_update_install() -> None:
    """Runs as Raspberry quits: swap the staged bundle in, record the outcome, schedule the relaunch
    (Raspberry's files live outside the app: nothing to carry). A failed rename rolls back and reopens
    the old build, which then shows the reason (WindowUpdate's startup note).
    Called from the app delegate's applicationWillTerminate_ — Raspberry's own delegate (Dock clicks)
    replaces Qt's, so on Quit macOS ends the process right after that call and app.exec() never returns
    (found 2026-11-22: the install placed after app.exec() never ran). Once only."""
    global _RASPBERRY_PENDING_UPDATE_INSTALL
    pending = _RASPBERRY_PENDING_UPDATE_INSTALL
    _RASPBERRY_PENDING_UPDATE_INSTALL = None
    if not pending:
        return
    target, staged, backup = Path(pending['target']), Path(pending['staged']), Path(pending['backup'])
    record = {'status': 'failed', 'version': str(pending.get('version') or ''), 'previous': VERSION,
              'dmg': str(pending.get('dmg') or ''), 'reason': '', 'time': time.time()}
    try:
        # exit hooks (pending writes) run now, while every file of the running build is still in place
        atexit._run_exitfuncs()
    except Exception:
        pass
    launch = target
    try:
        if not staged.is_dir():
            raise FileNotFoundError(str(staged))
        if backup.exists():
            shutil.rmtree(backup, ignore_errors=True)
        os.rename(target, backup)
        try:
            os.rename(staged, target)
        except OSError:
            try:
                os.rename(backup, target)
            except OSError:
                launch = backup
            raise
        record['status'] = 'installed'
    except Exception as exc:
        record['reason'] = '%s: %s' % (type(exc).__name__, exc)
    _raspberry_write_update_result(record)
    _raspberry_spawn_relauncher(str(launch))


def raspberry_cleanup_update_leftovers() -> None:
    """Startup (background thread): drop the previous bundle kept by the last swap or a stale staged
    copy, stale mounts, and cached installers this build has already reached. A failed install keeps
    its DMG for the retry."""
    with _RASPBERRY_UPDATE_FS_LOCK:
        bundle = raspberry_running_app_bundle()
        if bundle is not None:
            staging_root = bundle.parent / RASPBERRY_UPDATE_STAGING_DIRNAME
            if staging_root.is_dir():
                shutil.rmtree(staging_root, ignore_errors=True)
        if not os.path.isdir(RASPBERRY_UPDATE_CACHE_DIR):
            return
        for name in os.listdir(RASPBERRY_UPDATE_CACHE_DIR):
            path = os.path.join(RASPBERRY_UPDATE_CACHE_DIR, name)
            try:
                if name.startswith('mnt-') and os.path.isdir(path):
                    _raspberry_detach_dmg(path)
                elif name.endswith(('.dmg', '.dmg.part')) and not raspberry_is_newer_version(name, VERSION):
                    os.remove(path)
            except Exception:
                pass


class _UpdateProgressBar(QWidget):
    """Slim rounded track for the update window. busy=True sweeps an indeterminate segment
    (mount / copy / signature check have no percentage). (Broccoli's, unchanged.)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fraction = 0.0
        self._busy = False
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._advance)
        self.setFixedHeight(6)

    def fraction(self) -> float:
        return self._fraction

    def is_busy(self) -> bool:
        return self._busy

    def set_fraction(self, fraction: float):
        self._busy = False
        self._timer.stop()
        self._fraction = max(0.0, min(1.0, float(fraction)))
        self.update()

    def set_busy(self, busy: bool = True):
        self._busy = bool(busy)
        if self._busy and self.isVisible():
            self._timer.start()
        else:
            self._timer.stop()
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        if self._busy:
            self._timer.start()

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def _advance(self):
        self._phase = (self._phase + 0.015) % 1.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        radius = rect.height() / 2.0
        dark = raspberry_ui.ui_palette()['dark']
        track = QPainterPath()
        track.addRoundedRect(rect, radius, radius)
        painter.fillPath(track, QColor('#3A3A3C') if dark else QColor('#E5E5EA'))
        if self._busy:
            segment = rect.width() * 0.3
            fill_rect = QRectF(rect.left() - segment + (rect.width() + segment) * self._phase,
                               rect.top(), segment, rect.height())
        else:
            fill_rect = QRectF(rect.left(), rect.top(), rect.width() * self._fraction, rect.height())
        if fill_rect.width() > 0:
            fill = QPainterPath()
            fill.addRoundedRect(fill_rect, radius, radius)
            painter.setClipPath(track)
            painter.fillPath(fill, QColor('#0A84FF') if dark else QColor('#007AFF'))


class _UpdateStatusLabel(QLabel):
    """The update window's status line; tells the window when its text changes (the window shows the
    line only while it says something, and fits its height to it)."""
    text_changed = None

    def setText(self, text):
        super().setText(text)
        if callable(self.text_changed):
            self.text_changed()


class WindowUpdate(QWidget):  # 增加更新页面（Check for Updates）
    """Broccoli's update window (2026-11-09, same layout and size: 320 wide, as tall as its content): the
    release check runs in a background thread, and
    "Update Now" downloads, verifies and installs the new version, then relaunches Raspberry."""
    # (result_text, update_ready, popup_when_ready, release_info) from the fetch thread.
    update_check_finished = pyqtSignal(str, bool, bool, object)
    # one-click install worker → GUI thread
    install_progress = pyqtSignal(object, object)   # (done_bytes, total_bytes)
    install_status = pyqtSignal(str)                # a phase without percentage
    install_failed = pyqtSignal(str)
    install_ready = pyqtSignal(object)              # pending-install record

    def __init__(self):
        super().__init__()
        self._check_inflight = False
        self._release_info = None
        self._update_available = False
        self._install_busy = False
        self._install_can_cancel = False
        self._install_cancel = None
        self._download_started_at = 0.0
        self._download_started_bytes = 0
        self._startup_note = self._read_startup_note()
        self.update_check_finished.connect(self._on_update_check_finished)
        self.install_progress.connect(self._on_install_progress)
        self.install_status.connect(self._on_install_status)
        self.install_failed.connect(self._on_install_failed)
        self.install_ready.connect(self._on_install_ready)
        self.initUI()

    def initUI(self):  # 说明页面内信息
        self.setUpMainWindow()
        make_native_glass_window(self)   # system traffic lights + window glass (style book 5.7.2)
        QWidget.layout(self).setContentsMargins(20, glass_kit.NATIVE_TITLEBAR_HEIGHT, 20, 20)
        self.setFixedWidth(320)   # Broccoli's update window
        self._fit_height()
        self.center()
        self.setFocus()

    def _fit_height(self):
        """As tall as the content: no empty band at the bottom. While a download runs the progress bar
        and the status line appear under the buttons and the window grows by that much."""
        layout = QWidget.layout(self)
        if layout is None:
            return
        busy = not self.install_progress_bar.isHidden() or bool(self.install_status_lbl.text().strip())
        self._progress_block.setVisible(busy)
        layout.activate()
        width = self.width() or 320
        height = layout.totalHeightForWidth(width) if layout.hasHeightForWidth() else layout.totalSizeHint().height()
        self.setFixedHeight(max(1, int(height)))

    def setUpMainWindow(self):
        # Broccoli's update window: centred lines, then one row per action sharing a label column
        title = QLabel(_ut("<h2>Raspberry Update</h2>"), self)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl = QLabel(_ut('Current version: v{v}').format(v=VERSION), self)
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        widg5 = QWidget()
        lbl1 = QLabel(_ut('Latest version:'), self)
        self.lbl2 = QLabel('', self)
        blay5 = QHBoxLayout()
        blay5.setContentsMargins(0, 0, 0, 0)
        blay5.setSpacing(4)
        blay5.addStretch(1)
        blay5.addWidget(lbl1)
        blay5.addWidget(self.lbl2)
        blay5.addStretch(1)
        widg5.setLayout(blay5)

        lbl0 = QLabel(_ut('Check release:'), self)
        bt1 = WhiteButton(_ut('Github'))
        bt1.setFixedWidth(120)
        bt1.clicked.connect(self.upd)
        # one-click update: download with progress → verify → install → relaunch
        lbl_install = QLabel(_ut('Install update:'), self)
        self.install_btn = WhiteButton(_ut('Update Now'))
        self.install_btn.setFixedWidth(120)
        self.install_btn.setEnabled(False)
        self.install_btn.clicked.connect(self.start_install)
        label_width = max(lbl0.sizeHint().width(), lbl_install.sizeHint().width())
        action_rows = []
        for label, button in ((lbl0, bt1), (lbl_install, self.install_btn)):
            label.setFixedWidth(label_width)
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row = QWidget()
            row.setFixedHeight(50)   # About's button rows
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)
            row_layout.addStretch(1)
            row_layout.addWidget(label)
            row_layout.addWidget(button)
            row_layout.addStretch(1)
            action_rows.append(row)

        # progress bar + status line: only while there is something to show
        self._progress_block = QWidget()
        progress_layout = QVBoxLayout(self._progress_block)
        progress_layout.setContentsMargins(0, 6, 0, 0)
        progress_layout.setSpacing(10)
        self.install_progress_bar = _UpdateProgressBar(self._progress_block)
        self.install_progress_bar.hide()
        self.install_status_lbl = _UpdateStatusLabel(self._progress_block)
        self.install_status_lbl.setWordWrap(True)
        self.install_status_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.install_status_lbl.text_changed = lambda: QTimer.singleShot(0, self._fit_height)
        progress_layout.addWidget(self.install_progress_bar)
        progress_layout.addWidget(self.install_status_lbl)
        self.install_progress_bar.installEventFilter(self)
        self._progress_block.hide()

        main_h_box = QVBoxLayout()
        main_h_box.setContentsMargins(20, glass_kit.NATIVE_TITLEBAR_HEIGHT, 20, 20)
        main_h_box.addSpacing(10)
        main_h_box.addWidget(title)
        main_h_box.addSpacing(5)
        main_h_box.addWidget(self.lbl)
        main_h_box.addSpacing(5)
        main_h_box.addWidget(widg5)
        main_h_box.addSpacing(16)
        for row in action_rows:
            main_h_box.addWidget(row)
        main_h_box.addWidget(self._progress_block)
        main_h_box.addSpacing(10)
        self.setLayout(main_h_box)

    def upd(self):
        webbrowser.open(RASPBERRY_UPDATE_RELEASES_URL)

    def eventFilter(self, obj, event):
        if obj is getattr(self, 'install_progress_bar', None) and event.type() in (QEvent.Type.Show, QEvent.Type.Hide):
            QTimer.singleShot(0, self._fit_height)
        return super().eventFilter(obj, event)

    def center(self):  # 设置窗口居中
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def activate(self):  # 设置窗口显示
        self.show()
        self.checkupdate()

    @staticmethod
    def _read_startup_note() -> str:
        """What the previous run's install attempt left behind, shown once with the startup check."""
        record = raspberry_take_last_update_result()
        if record.get('status') == 'installed' and not raspberry_is_newer_version(record.get('version'), VERSION):
            return _ut('Raspberry was updated to v{v}.').format(v=VERSION)
        if record.get('status') == 'failed':
            return _ut('The last update could not be installed ({reason}). Click Update Now to try again.').format(
                reason=str(record.get('reason') or '?'))
        return ''

    def checkupdate(self, *, popup_when_ready: bool = False):
        """Start the release check WITHOUT touching the network on the GUI thread (the old check
        fetched github.com right here and froze the window while GitHub was slow or unreachable)."""
        if self._check_inflight:
            return
        self._check_inflight = True
        self.lbl2.setText(_ut('Checking…'))
        self.lbl2.adjustSize()

        def worker():
            alertupdate = _ut('No Internet')
            ready = False
            info = None
            try:
                info = self.fetch_latest_release_info()
                result = (info or {}).get('tag')
                if result:
                    # only a strictly NEWER release is an update (the old check offered any release
                    # that differed — a newer build was offered a "downgrade")
                    if raspberry_is_newer_version(result, VERSION):
                        alertupdate = _ut('{tag} is ready!').format(tag=result)
                        ready = True
                    else:
                        alertupdate = _ut('{tag} (up-to-date)').format(tag=result)
            except Exception:
                pass
            try:
                self.update_check_finished.emit(alertupdate, ready, popup_when_ready, info)
            except RuntimeError:
                pass   # window destroyed during shutdown

        threading.Thread(target=worker, daemon=True, name='raspberry-update-check').start()

    def _on_update_check_finished(self, alertupdate: str, ready: bool, popup_when_ready: bool, info):
        self._check_inflight = False
        self.lbl2.setText(str(alertupdate or ''))
        self.lbl2.adjustSize()
        if not self._install_busy:
            self._update_available = bool(ready)
            self._release_info = dict(info) if (ready and isinstance(info, dict)) else None
            has_package = bool((self._release_info or {}).get('dmg_url'))
            self.install_btn.setEnabled(has_package)
            if ready and not has_package:
                self.install_status_lbl.setText(_ut('This release has no installer package; use the Github button.'))
        note = self._startup_note if popup_when_ready else ''
        if note and not self._install_busy:
            self._startup_note = ''
            self.install_status_lbl.setText(note)
        if popup_when_ready and (ready or note) and not self.isVisible():
            self.show()

    # ---- one-click install ----------------------------------------------------
    def start_install(self):
        if self._install_busy:
            # the same button reads "Cancel" while the download runs
            if self._install_can_cancel and self._install_cancel is not None:
                self._install_cancel.set()
                self.install_btn.setEnabled(False)
                self.install_status_lbl.setText(_ut('Canceling…'))
            return
        info = dict(self._release_info or {})
        if not info.get('dmg_url'):
            return
        self._install_busy = True
        self._install_can_cancel = True
        self._install_cancel = threading.Event()
        self._download_started_at = 0.0
        self._download_started_bytes = 0
        self.install_btn.setText(_ut('Cancel'))
        self.install_progress_bar.set_fraction(0.0)
        self.install_progress_bar.show()
        self.install_status_lbl.setText(_ut('Connecting…'))
        threading.Thread(target=self._install_worker, args=(info, self._install_cancel),
                         daemon=True, name='raspberry-update-install').start()

    def _install_worker(self, info: dict, cancel_event):
        last_emit = [0.0]

        def progress(done, total):
            now = time.monotonic()
            if now - last_emit[0] >= 0.1 or (total and done >= total):
                last_emit[0] = now
                self.install_progress.emit(int(done), int(total))

        try:
            dmg_path = raspberry_download_update_dmg(info, progress, cancel_event,
                                                      status=self.install_status.emit)
            bundle = raspberry_running_app_bundle()
            blocker = raspberry_update_install_blocker(bundle)
            if blocker:
                # can't swap this copy: hand the verified DMG to Finder instead
                subprocess.Popen(['/usr/bin/open', dmg_path],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.install_ready.emit({'manual': True, 'reason': blocker, 'dmg': dmg_path})
                return
            self.install_ready.emit(raspberry_stage_update(dmg_path, bundle, status=self.install_status.emit))
        except RaspberryUpdateError as exc:
            self.install_failed.emit(str(exc))
        except Exception as exc:
            logging.exception('One-click update failed.')
            self.install_failed.emit(_ut('Update failed: {err}').format(err=exc))

    def _on_install_progress(self, done, total):
        done, total = int(done or 0), int(total or 0)
        now = time.monotonic()
        if not self._download_started_at:
            self._download_started_at, self._download_started_bytes = now, done
        mb = 1024 * 1024
        text = _ut('Downloading… {done} / {total} MB').format(
            done='%.1f' % (done / mb), total=('%.1f' % (total / mb)) if total else '?')
        elapsed = now - self._download_started_at
        if elapsed >= 1.0 and done > self._download_started_bytes:
            text += ' · %.1f MB/s' % ((done - self._download_started_bytes) / mb / elapsed)
        self.install_progress_bar.set_fraction(done / total if total else 0.0)
        if not (self._install_cancel is not None and self._install_cancel.is_set()):
            self.install_status_lbl.setText(text)

    def _on_install_status(self, text: str):
        # verify / mount / copy / signature: no percentage and no way back
        self._install_can_cancel = False
        self.install_btn.setEnabled(False)
        self.install_btn.setText(_ut('Installing…'))
        self.install_progress_bar.set_busy(True)
        self.install_status_lbl.setText(str(text or ''))

    def _reset_install_controls(self):
        self._install_busy = False
        self._install_can_cancel = False
        self._install_cancel = None
        self.install_progress_bar.set_busy(False)
        self.install_progress_bar.hide()
        self.install_btn.setText(_ut('Update Now'))
        self.install_btn.setEnabled(self._update_available and bool((self._release_info or {}).get('dmg_url')))

    def _on_install_failed(self, message: str):
        self._reset_install_controls()
        self.install_status_lbl.setText(str(message or ''))
        if not self.isVisible():
            self.show()

    def _on_install_ready(self, pending):
        pending = dict(pending or {})
        if pending.get('manual'):
            self._reset_install_controls()
            self.install_status_lbl.setText(
                _ut("Can't install automatically ({reason}). The installer is open: drag Raspberry into Applications.")
                .format(reason=pending.get('reason', '')))
            return
        global _RASPBERRY_PENDING_UPDATE_INSTALL
        _RASPBERRY_PENDING_UPDATE_INSTALL = pending
        self.install_progress_bar.set_fraction(1.0)
        self.install_status_lbl.setText(_ut('Restarting Raspberry to finish the update…'))
        if not self.isVisible():
            self.show()
        QTimer.singleShot(800, self._quit_for_install)

    def _quit_for_install(self):
        # the event loop ends; the swap itself runs after app.exec() returns
        QApplication.instance().quit()

    @classmethod
    def fetch_latest_release_info(cls):
        """Release info (tag + DMG asset) from the API; when the API is unavailable, the tag alone from
        the releases page (no one-click install then — the Github button still works)."""
        try:
            info = raspberry_fetch_latest_release()
            if info:
                return info
        except Exception:
            pass
        tag = cls.extract_latest_tag(cls.fetch_latest_version_text())
        return {'tag': tag} if tag else None

    @staticmethod
    def fetch_latest_version_text():
        try:
            import requests
            from bs4 import BeautifulSoup
            import html2text
            s = requests.session()
            s.keep_alive = False
            response = s.get(RASPBERRY_UPDATE_RELEASES_URL, timeout=(4, 8))
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, "html.parser")
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
    def extract_latest_tag(plain_text_utf8):
        if not plain_text_utf8:
            return None
        result = re.compile(r'(v\d+\.\d+\.\d+)\sLatest').findall(plain_text_utf8)
        return result[0] if result else None



def announce_data_move(parent=None):
    """Said once, after the first start that moved Raspberry's files out of the home folder (Ryan
    2026-11-16: 「迁移完有一个弹窗告诉用户，已经迁移完毕了，这个升级没法回滚，不然以前的版本读不到数据」)."""
    if not os.path.exists(MOVE_NOTICE_FILE):
        return False
    try:
        os.remove(MOVE_NOTICE_FILE)
    except Exception:
        pass
    text = QCoreApplication.translate(
        'LaunchpadWindow',
        "Raspberry has moved its data to the folder macOS recommends:\n%1\n\n"
        "Your groups, the order of your apps and your settings are all there.\n"
        "This upgrade cannot be undone: an earlier version of Raspberry can no longer read the data.")
    shown = os.path.join("~/Library/Application Support", BUNDLE_ID)
    raspberry_ui.raspberry_alert(parent, text.replace('%1', shown),
                                 QCoreApplication.translate('LaunchpadWindow', "Data moved"))
    return True


class PermissionInfoWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        make_native_glass_window(self)   # system traffic lights + window glass (style book 5.7.2)

    def init_ui(self):
        self.setUpMainWindow()
        self.setFixedSize(400, 600)
        self.center()
        self.setFocus()

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


glass_kit.install_glass_button_class(WhiteButton)  # white capsules become glass (before any window is built)
for _glass_window_cls in (WindowAbout, CustomDialog, CustomDialog2, CustomDialog3, CustomDialog4, WindowUpdate,
                          PermissionInfoWidget):
    install_native_glass_window_class(_glass_window_cls)


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

    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    lang_file = Path(LANG_FILE)
    if lang_file.exists():
        lang = lang_file.read_text(encoding="utf-8").strip()
    else:
        lang = "system"  # 默认：跟随系统
    load_translation(app, lang)

    # light / dark, live (style book 5.8)
    on_theme_changed(raspberry_ui.apply_raspberry_theme)
    install_theme_observer()
    raspberry_ui.apply_raspberry_theme()

    win = None  # 全局主窗口变量
    launch = {'by_user': False}     # opened by the user (not at login): the launcher opens once it is ready

    # Dock delegate 必须在主线程入口设置
    if sys.platform == "darwin":
        class _DockClickDelegate(NSObject):
            def applicationDidFinishLaunching_(self, notification):
                # "Start on login" is a LaunchAgent that runs the program with "autostart": that start has
                # no login mark, and AppKit then makes up an "open app" event itself (tried 2026-11-23)
                launch['by_user'] = ('autostart' not in sys.argv[1:] and launched_by_user(
                    NSAppleEventManager.sharedAppleEventManager().currentAppleEvent()))

            def applicationWillTerminate_(self, notification):
                # macOS ends the process right after this (app.exec() does not return): a Dock change
                # under way finishes first, so the Dock is not left hidden; a scan for new apps stops
                # (one ended in the middle of saving an icon can crash on the way out)
                try:
                    worker = getattr(win, 'scan_worker', None)
                    if worker is not None and worker.isRunning():
                        worker.stop()
                        worker.wait(1500)
                except Exception:
                    pass
                stop_assistant_tools()      # the card for the assistant app: no longer running
                wait_for_dock()
                # one-click update: the new version is swapped in now (nothing after app.exec() runs)
                raspberry_apply_pending_update_install()

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
        win.hide()
        win.mark_windows_at_birth()     # "Show on all Spaces": before the Dock icon is there
        show_dock_icon()
        QTimer.singleShot(600, lambda: announce_data_move(None))
        QTimer.singleShot(1500, lambda: start_assistant_tools(win))   # for an assistant app, if there is one
        # started by the user (Dock, Finder, Spotlight): open as soon as it is ready — not at login, and
        # not over the first-run notice, the data-moved notice, or the note of an update just installed
        # (the restart after an update is an ordinary start too) (Ryan 2026-11-22)
        if (launch['by_user'] and not permission.isVisible() and not os.path.exists(MOVE_NOTICE_FILE)
                and not getattr(win.win_update, '_startup_note', '')):
            QTimer.singleShot(0, win.show_main_window)

    index_worker = AppIndexWorker()
    index_worker.finished.connect(on_index_finished)
    QTimer.singleShot(20000, show_dock_icon)    # never without an icon for long, whatever the indexing does
    index_worker.start()
    
    # one-click update: drop what the last update left. The version the user chose to install is swapped
    # in by the delegate's applicationWillTerminate_ (macOS ends the process there); the call after
    # app.exec() only covers a run without that delegate (it does nothing a second time)
    threading.Thread(target=raspberry_cleanup_update_leftovers, daemon=True, name='raspberry-update-cleanup').start()
    exit_code = app.exec()
    raspberry_apply_pending_update_install()
    sys.exit(exit_code)
