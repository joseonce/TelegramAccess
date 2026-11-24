# -*- coding: utf-8 -*-
"""
Módulo para la gestión y resolución de rutas de TelegramAccess.
Soporta ejecución desde código fuente y empaquetado (cx_Freeze / PyInstaller).
"""

import sys
import os
from pathlib import Path
from typing import Optional

IS_FROZEN = getattr(sys, "frozen", False)

if IS_FROZEN:
    ROOT_DIR = Path(sys.executable).parent.resolve()
else:
    ROOT_DIR = Path(__file__).parent.parent.parent.resolve()

_DATA_OVERRIDE = os.environ.get("TELEGRAM_ACCESSIBLE_DATA_DIR", "").strip()
if _DATA_OVERRIDE:
    DATA_DIR = Path(_DATA_OVERRIDE).expanduser().resolve()
else:
    DATA_DIR = ROOT_DIR / "data"

RESOURCES_DIR = DATA_DIR
LOCALES_DIR = DATA_DIR / "locales"

def get_resource_path(relative_path: str) -> Path:
    return RESOURCES_DIR / relative_path

def get_locales_path(relative_path: str = "") -> Path:
    return LOCALES_DIR / relative_path if relative_path else LOCALES_DIR

def get_data_path(relative_path: str) -> Path:
    return DATA_DIR / relative_path

def get_bin_path() -> Path:
    return DATA_DIR / "bin"

def get_grabaciones_path() -> Path:
    p = DATA_DIR / "grabaciones"
    p.mkdir(parents=True, exist_ok=True)
    return p

def asegurar_bin_en_path():
    bin_dir = get_bin_path()
    try:
        bin_dir.mkdir(parents=True, exist_ok=True)
        ruta = str(bin_dir)
        actual = os.environ.get("PATH", "")
        if ruta not in actual.split(os.pathsep):
            os.environ["PATH"] = ruta + os.pathsep + actual
    except Exception:
        pass

def get_ffmpeg_path() -> Optional[str]:
    exe = get_bin_path() / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    return str(exe) if exe.exists() else None

def limpiar_temp():
    import shutil
    temp_dir = get_data_path("temp")
    if not temp_dir.exists():
        return
    for elemento in temp_dir.iterdir():
        try:
            if elemento.is_dir():
                shutil.rmtree(elemento, ignore_errors=True)
            else:
                elemento.unlink()
        except Exception:
            pass

def inicializar_directorios():
    carpetas_data = [
        "config",
        "logs",
        "database",
        "sounds",
        "docs",
        "bin",
        "temp",
        "sessions",
        "downloads",
        "backups",
        "grabaciones",
    ]
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for c in carpetas_data:
        get_data_path(c).mkdir(parents=True, exist_ok=True)
