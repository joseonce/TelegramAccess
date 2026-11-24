# -*- mode: python ; coding: utf-8 -*-
"""
Especificación de PyInstaller para TelegramAccess.
Empaqueta la aplicación en modo directorio (onedir) con todas las dependencias
de accesibilidad, audio (basskit / BASS DLLs), MTProto (Kurigram/Pyrogram) y UI (wxPython).
"""

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# Paquetes con componentes dinámicos, librerías compartidas (DLLs) o metadatos
packages_to_collect = [
    'basskit',
    'accessible_output2',
    'pyrogram',
    'kuricrypt',
    'cryptography',
    'qrcode',
    'ntgcalls',
    'pytgcalls',
    'py_tgcalls',
]

datas = []
binaries = []
hiddenimports = [
    'wx',
    'wx.adv',
    'wx.core',
    'kuricrypt',
    'pycryptodome',
    'Crypto',
    'Crypto.Cipher',
    'Crypto.Cipher.AES',
    'sqlite3',
    'ssl',
    'asyncio',
]

# Incluir todos los submódulos internos de la aplicación
hiddenimports += collect_submodules('app')

for pkg in packages_to_collect:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as e:
        print(f"Aviso al recolectar {pkg}: {e}")

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'numpy', 'IPython'],
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
    name='TelegramAccess',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
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
    upx=False,
    upx_exclude=[],
    name='TelegramAccess',
)
