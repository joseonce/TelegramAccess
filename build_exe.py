# -*- coding: utf-8 -*-
"""
Script de compilación y empaquetado para TelegramAccess.
Ejecuta PyInstaller usando TelegramAccess.spec y copia los recursos
iniciales necesarios (sonidos, documentación, binarios de ffmpeg) en la
carpeta dist/TelegramAccess/data/.
"""

import sys
import os
import shutil
import stat
import argparse
from pathlib import Path


def safe_rmtree(path):
    """Elimina directorios asegurando permisos de escritura en Windows."""
    def _on_error(func, p, excinfo):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except Exception:
            pass
    if Path(path).exists():
        shutil.rmtree(path, onerror=_on_error)


def compilar(console: bool = False, clean: bool = True):
    base_dir = Path(__file__).parent.resolve()
    os.chdir(base_dir)

    print("=" * 60)
    print("           Iniciando compilación de TelegramAccess")
    print("=" * 60)

    try:
        import PyInstaller.__main__
    except ImportError:
        print("\n[ERROR] PyInstaller no está instalado en este entorno.")
        print("Instálalo ejecutando: python -m pip install pyinstaller\n")
        return False

    spec_file = base_dir / "TelegramAccess.spec"
    if not spec_file.exists():
        print(f"\n[ERROR] No se encontró el archivo spec: {spec_file}")
        return False

    # Argumentos para PyInstaller
    pyinstaller_args = [
        str(spec_file),
        "--noconfirm",
    ]

    dist_root = base_dir / "dist"
    build_root = base_dir / "build"
    dist_dir = dist_root / "TelegramAccess"
    dist_data = dist_dir / "data"

    # RESPALDO DE SEGURIDAD: Mover la carpeta data fuera de dist/TelegramAccess para protegerla de PyInstaller
    temp_backup_data = base_dir / ".backup_data_dist"
    if dist_data.exists():
        print("\n[SEGURIDAD] Protegiendo datos de usuario existentes de dist/TelegramAccess/data...")
        temp_backup_data.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copytree(dist_data, temp_backup_data, dirs_exist_ok=True)
            print(" - Datos de usuario salvaguardados fuera del directorio de compilación.")
        except Exception as e:
            print(f" - Aviso al proteger datos: {e}")

    if clean:
        import time
        # Limpiar directorio build y dist_dir (habiéndose salvado data previamente)
        # Esto evita que PyInstaller intente eliminar dist_dir con errores de acceso denegado en Windows
        print("\n[LIMPIEZA] Limpiando directorios temporales de compilación previa...")
        safe_rmtree(build_root)
        safe_rmtree(dist_dir)
        time.sleep(1)

    print("\n[1/3] Ejecutando PyInstaller...")
    try:
        PyInstaller.__main__.run(pyinstaller_args)
    except SystemExit as e:
        if temp_backup_data.exists() and not dist_data.exists():
            try:
                shutil.copytree(temp_backup_data, dist_data, dirs_exist_ok=True)
            except Exception:
                pass
        if e.code != 0:
            print(f"\n[ERROR] La compilación falló con código {e.code}")
            return False
    except Exception as e:
        if temp_backup_data.exists() and not dist_data.exists():
            try:
                shutil.copytree(temp_backup_data, dist_data, dirs_exist_ok=True)
            except Exception:
                pass
        print(f"\n[ERROR] Error durante la compilación: {e}")
        return False

    dist_dir = base_dir / "dist" / "TelegramAccess"
    if not dist_dir.exists():
        print(f"\n[ERROR] El directorio de salida no existe: {dist_dir}")
        return False

    print("\n[2/3] Copiando recursos y estructura de datos...")
    dist_data = dist_dir / "data"
    dist_data.mkdir(parents=True, exist_ok=True)

    # 1. Sonidos predeterminados
    src_sounds = base_dir / "data" / "sounds" / "default"
    dest_sounds = dist_data / "sounds" / "default"
    if src_sounds.exists():
        dest_sounds.parent.mkdir(parents=True, exist_ok=True)
        safe_rmtree(dest_sounds)
        shutil.copytree(src_sounds, dest_sounds)
        print(f" - Sonidos copiados a: {dest_sounds.relative_to(base_dir)}")

    # 2. Documentación interna
    src_docs = base_dir / "data" / "docs"
    dest_docs = dist_data / "docs"
    if src_docs.exists():
        dest_docs.parent.mkdir(parents=True, exist_ok=True)
        safe_rmtree(dest_docs)
        shutil.copytree(src_docs, dest_docs)
        print(f" - Documentación interna copiada a: {dest_docs.relative_to(base_dir)}")

    # 2b. Idiomas y traducciones (locales)
    src_locales = base_dir / "data" / "locales"
    dest_locales = dist_data / "locales"
    if src_locales.exists():
        dest_locales.parent.mkdir(parents=True, exist_ok=True)
        safe_rmtree(dest_locales)
        shutil.copytree(src_locales, dest_locales)
        print(f" - Locales copiados a: {dest_locales.relative_to(base_dir)}")

    # 3. Binarios (ffmpeg.exe, complementos, etc.)
    src_bin = base_dir / "data" / "bin"
    dest_bin = dist_data / "bin"
    if src_bin.exists():
        dest_bin.mkdir(parents=True, exist_ok=True)
        for item in src_bin.iterdir():
            if item.is_file():
                dest_file = dest_bin / item.name
                if not dest_file.exists():
                    shutil.copy2(item, dest_file)
                    print(f" - {item.name} copiado a bin.")

    # 4. Manuales en raíz de dist
    for doc_name in ["MANUAL.md", "TECLAS.md", "README.md"]:
        src_md = base_dir / doc_name
        if src_md.exists():
            shutil.copy2(src_md, dist_dir / doc_name)
            print(f" - {doc_name} copiado a dist.")

    # 5. Carpetas de datos vacías para asegurar existencia
    for sub in ["config", "logs", "database", "sessions", "downloads", "temp", "backups", "grabaciones"]:
        (dist_data / sub).mkdir(parents=True, exist_ok=True)

    # 6. Restaurar datos de usuario respaldados (base de datos, sesiones, credenciales, grabaciones)
    if temp_backup_data.exists():
        print("\n[SEGURIDAD] Restaurando y preservando datos de usuario en dist/TelegramAccess/data...")
        for root_src, dirs, files in os.walk(temp_backup_data):
            rel_path = Path(root_src).relative_to(temp_backup_data)
            target_dir = dist_data / rel_path
            target_dir.mkdir(parents=True, exist_ok=True)
            for f in files:
                src_file = Path(root_src) / f
                target_file = target_dir / f
                if not target_file.exists() or any(k in str(rel_path).lower() for k in ["database", "config", "sessions", "grabaciones"]):
                    shutil.copy2(src_file, target_file)
        safe_rmtree(temp_backup_data)
        print(" - Datos de usuario preservados y restaurados con éxito.")

    # 7. Sincronizar datos existentes desde data raíz si no estuvieran presentes en dist
    for sub in ["database", "config", "sessions"]:
        src_sub = base_dir / "data" / sub
        dst_sub = dist_data / sub
        if src_sub.exists():
            for f in src_sub.rglob("*"):
                if f.is_file():
                    rel = f.relative_to(src_sub)
                    target = dst_sub / rel
                    if not target.exists():
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(f, target)

    print("\n[3/3] Compilación finalizada con éxito.")
    print("=" * 60)
    print(f"Ejecutable generado en:\n  {dist_dir / 'TelegramAccess.exe'}")
    print("=" * 60)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compilador de TelegramAccess")
    parser.add_argument("--no-clean", action="store_true", help="No limpiar temporales antes de compilar")
    parser.add_argument("--console", action="store_true", help="Mostrar consola de depuración")
    args = parser.parse_args()

    exito = compilar(console=args.console, clean=not args.no_clean)
    sys.exit(0 if exito else 1)
