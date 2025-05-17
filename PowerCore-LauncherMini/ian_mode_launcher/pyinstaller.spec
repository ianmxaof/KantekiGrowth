# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

a = Analysis([
    'ian_mode_launcher_gui.py',
],
    pathex=['.'],
    binaries=[],
    datas=[('ian_mode.json', '.'), ('plugin_registry.json', '.'), ('ian_mode.next.json', '.'), ('ian_mode.changelog.json', '.'), ('prompts.txt', '.'), ('requirements.txt', '.'), ('logs', 'logs')],
    hiddenimports=collect_submodules('telebot') + collect_submodules('psutil'),
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='IAN_MODE_LAUNCHER_GUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon='E:/projects/icon_placeholders/favicon.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='IAN_MODE_LAUNCHER_GUI'
) 