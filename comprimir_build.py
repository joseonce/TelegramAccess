# -*- coding: utf-8 -*-
"""
Script para empaquetar y preparar una Release de TelegramAccess para GitHub.

Uso:
    python comprimir_build.py

Acciones:
1. Comprime la carpeta compilada (dist/TelegramAccess) en un archivo ZIP con compresión óptima:
   dist/TelegramAccess_v<version>.zip
2. Calcula el hash criptográfico SHA-256 del archivo ZIP.
3. Genera el manifiesto dist/version.json con la información de la versión, tamaño y hash.
4. Muestra las instrucciones para publicar la Release en https://github.com/joseonce/TelegramAccess
"""

import os
import re
import sys
import json
import hashlib
import zipfile
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
ORIGEN = BASE_DIR / "dist" / "TelegramAccess"
NOMBRE_BASE = "TelegramAccess"
GITHUB_USER = "joseonce"
GITHUB_REPO = "TelegramAccess"


def obtener_version():
    """Lee la versión actual desde app/core/version.py."""
    v_file = BASE_DIR / "app" / "core" / "version.py"
    if v_file.exists():
        src = v_file.read_text(encoding="utf-8")
        m = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', src)
        if m:
            return m.group(1)
    return "1.0.0"


def calcular_sha256(ruta_archivo):
    """Calcula el SHA-256 de un archivo en bloques."""
    h = hashlib.sha256()
    with open(ruta_archivo, "rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def main():
    print("=" * 65)
    print("      Empaquetador de Release para GitHub - TelegramAccess")
    print("=" * 65)

    if not ORIGEN.is_dir():
        print(f"\n[ERROR] No se encontró el directorio compilado: {ORIGEN}")
        print("Compila primero ejecutando: python build_exe.py\n")
        return 1

    version = obtener_version()
    dist_dir = BASE_DIR / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)

    zip_nombre = f"{NOMBRE_BASE}_v{version}.zip"
    zip_destino = dist_dir / zip_nombre
    json_destino = dist_dir / "version.json"

    if zip_destino.exists():
        print(f"\n - Eliminando paquete previo: {zip_nombre}")
        zip_destino.unlink()

    print(f"\n[1/3] Comprimiendo {ORIGEN} -> {zip_destino.name} (excluyendo datos personales)...")
    archivos_totales = 0
    # Carpetas bajo data/ que contienen datos personales del usuario y NUNCA deben incluirse en la release
    CARPETAS_PERSONALES = {"sessions", "database", "config", "logs", "backups", "downloads", "grabaciones", "temp"}
    EXTS_PERSONALES = {".session", ".session-journal", ".db", ".db-shm", ".db-wal", ".db-journal", ".enc", ".key", ".log", ".jsonl"}

    with zipfile.ZipFile(zip_destino, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for raiz, _dirs, archivos in os.walk(ORIGEN):
            for archivo in archivos:
                ruta_completa = Path(raiz) / archivo
                rel = ruta_completa.relative_to(ORIGEN)
                partes = rel.parts

                # Filtro de privacidad y datos de usuario:
                if len(partes) >= 2 and partes[0].lower() == "data":
                    sub_data = partes[1].lower()
                    if sub_data in CARPETAS_PERSONALES:
                        continue
                    if ruta_completa.suffix.lower() in EXTS_PERSONALES:
                        continue
                if ruta_completa.suffix.lower() in EXTS_PERSONALES:
                    continue

                # Dentro del ZIP, la carpeta raíz es "TelegramAccess"
                ruta_en_zip = Path(NOMBRE_BASE) / rel
                zf.write(ruta_completa, str(ruta_en_zip))
                archivos_totales += 1

        # Asegurar que las carpetas de datos existan vacías en el ZIP mediante entradas de directorio
        for sub in sorted(CARPETAS_PERSONALES):
            dir_zip = f"{NOMBRE_BASE}/data/{sub}/"
            zinfo = zipfile.ZipInfo(dir_zip)
            zf.writestr(zinfo, "")

    tam_bytes = zip_destino.stat().st_size
    tam_mb = tam_bytes / (1024 * 1024)
    print(f" - Empaquetado completado: {archivos_totales} archivos ({tam_mb:.1f} MB).")

    print("\n[2/3] Calculando SHA-256...")
    sha256_hash = calcular_sha256(zip_destino)
    print(f" - SHA-256: {sha256_hash}")

    print("\n[3/3] Generando manifiesto version.json...")
    manifiesto = {
        "version": version,
        "date": str(date.today()),
        "name": zip_nombre,
        "size": tam_bytes,
        "sha256": sha256_hash,
        "url": f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/download/v{version}/{zip_nombre}",
        "notes": f"Actualización de TelegramAccess v{version}: Activación automática de primer plano y foco en la lista de chats al iniciar/actualizar, y reducción del volumen del sonido de espera."
    }

    json_destino.write_text(json.dumps(manifiesto, indent=4, ensure_ascii=False), encoding="utf-8")
    print(f" - Manifiesto guardado en: {json_destino}")

    print("\n" + "=" * 65)
    print("                      ¡RELEASE PREPARADA!")
    print("=" * 65)
    print(f"Para publicar la versión en GitHub:")
    print(f"1. Accede a: https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/new")
    print(f"2. Etiqueta (Tag): v{version}")
    print(f"3. Título de la Release: TelegramAccess v{version}")
    print(f"4. Adjunta estos DOS archivos situados en la carpeta dist/:")
    print(f"   • {zip_destino.name}")
    print(f"   • version.json")
    print("5. Pulsa 'Publish release'.")
    print("=" * 65 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
