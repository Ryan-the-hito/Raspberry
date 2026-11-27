# -*- mode: python ; coding: utf-8 -*-


block_cipher = None

# Last synced from the source folder 2026-11-27: Raspberry/pro/Raspberry_v0.0.20.py (+ glass_kit.py,
# raspberry_ui.py, smooth_widgets.py, app_mcp_host.py, raspberry_mcp.py, i18n/*.qm).
# Replaced files: ~/Downloads/Raspberrynew_backup_20261127.

# The version comes from Raspberry.py's VERSION (same folder): the one-click update compares the
# installed app's version with the release, so the two must never differ.
import os, re
with open(os.path.join(SPECPATH, 'Raspberry.py'), encoding='utf-8') as _handle:
    __version__ = re.search(r'^VERSION\s*=\s*["\']([0-9.]+)["\']', _handle.read(), re.M).group(1)

info_plist = {
    # no Dock icon at the very start: Raspberry shows it itself (show_dock_icon) — at once, or, with
    # "Show on all Spaces" on, after its windows are marked (they then reach full-screen Spaces)
    'LSUIElement': True,
    #'LSBackgroundOnly': True,
    'NSHumanReadableCopyright': 'Copyright © 2025 Yixiang SHEN. All rights reserved.',
    # the build number follows the version's last number, as before (0.0.16 was build 16)
    'CFBundleVersion': __version__.split('.')[-1],
    'CFBundleShortVersionString': __version__,
    "LSApplicationCategoryType": "public.app-category.productivity",
    "com.apple.security.app-sandbox": True,
    "NSPrincipalClass": "NSApplication",
    "LSMinimumSystemVersion": "15.0",
    'NSHighResolutionCapable': True,
    "ITSAppUsesNonExemptEncryption": False,
    "CFBundleDisplayName": "Raspberry", 
    "CFBundleName": "Raspberry", 
    'NSAppleEventsUsageDescription': 'This app sends AppleEvents to control other applications.'
}

a = Analysis(
    ['Raspberry.py'],
    pathex=[SPECPATH],
    binaries=[],
    datas=[('Raspberry_desk.icns', '.'), ('Raspberry_menu.png', '.'), ('wechat50.png', '.'), ('wechat20.png', '.'), ('wechat10.png', '.'), ('wechat5.png', '.'), ('alipay50.png', '.'), ('alipay20.png', '.'), ('alipay10.png', '.'), ('alipay5.png', '.'), ('com.ryanthehito.raspberry.plist', '.'), ('lporg', '.'),
           # the translations go to Resources/i18n (Raspberry copies that folder out on every start); config.yml is lporg's
           ('zh_CN.qm', 'i18n'), ('ja_JP.qm', 'i18n'), ('config.yml', '.')],
    # 2026-11-16 (Liquid Glass): glass_kit.py, raspberry_ui.py and smooth_widgets.py lie next to Raspberry.py
    # (the main file imports them).
    hiddenimports=['subprocess', 'AppKit', 'Quartz', 'Foundation', 'objc', 'PyQt6.sip', 'glass_kit', 'raspberry_ui', 'smooth_widgets',
                   # 2026-11-23: the tools for an assistant app (imported inside a function at start; app_mcp_host is
                   # also the --mcp-stdio bridge, imported at the very top of Raspberry.py)
                   'app_mcp_host', 'raspberry_mcp',
                   'PyQt6.QtTest'],   # glass_kit lets go of the right mouse button after a native menu with it
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', '_tkinter', 'tcl', 'tk'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Raspberry',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Raspberry',
)
app = BUNDLE(
    coll,
    name='Raspberry.app',
    icon='Raspberry_desk.icns',
    info_plist=info_plist,
    bundle_identifier='com.ryanthehito.raspberry',
    version=__version__,
)
