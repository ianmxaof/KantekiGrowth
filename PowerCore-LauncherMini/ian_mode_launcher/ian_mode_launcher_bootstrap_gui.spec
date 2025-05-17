# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

ICON_PATH = r'E:/projects/icon_placeholders/favicon.ico'

a = Analysis([
    'ian_mode_launcher_bootstrap_gui.py',
],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=collect_submodules('psutil') + collect_submodules('tkinter'),
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MAIN_LAUNCHER_GUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=ICON_PATH
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MAIN_LAUNCHER_GUI'
) 