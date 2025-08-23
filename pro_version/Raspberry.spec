# -*- mode: python ; coding: utf-8 -*-


block_cipher = None

__version__ = '0.0.4'

info_plist = {
    'LSUIElement': False,
    #'LSBackgroundOnly': True,
    'NSHumanReadableCopyright': 'Copyright © 2025 Yixiang SHEN. All rights reserved.',
    'CFBundleVersion': '4',
    'CFBundleShortVersionString': '0.0.4',
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
    pathex=['/Users/ryanshenefield/Downloads/Raspberry.py'],
    binaries=[],
    datas=[('Raspberry_desk.icns', '.'), ('Raspberry_menu.png', '.'), ('wechat50.png', '.'), ('wechat20.png', '.'), ('wechat10.png', '.'), ('wechat5.png', '.'), ('alipay50.png', '.'), ('alipay20.png', '.'), ('alipay10.png', '.'), ('alipay5.png', '.'), ('com.ryanthehito.raspberry.plist', '.'), ('lporg', '.')],
    hiddenimports=['subprocess', 'AppKit', 'PyQt6.sip'],
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
