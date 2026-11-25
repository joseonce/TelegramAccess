# -*- coding: utf-8 -*-
"""
Servicio de actualización de TelegramAccess.

Comprueba e instala las nuevas versiones publicadas en las Releases de GitHub
del repositorio oficial: https://github.com/joseonce/TelegramAccess

Flujo:
1. Comprueba la versión remota en version.json publicado en GitHub Releases.
2. Si hay versión nueva, descarga el ZIP compilado (TelegramAccess_v<version>.zip).
3. Verifica la integridad del paquete descargado mediante su hash SHA-256.
4. Extrae los archivos en una carpeta temporal segura (_actualizacion_temp).
5. Crea un script por lotes (_actualizar_telegramaccess.bat) que:
   - Inicia un bucle de sonido de espera con updating.wav en segundo plano.
   - Espera a que cierre el proceso actual de TelegramAccess.
   - Copia los nuevos binarios y recursos con robocopy sin alterar la carpeta de
     datos del usuario (telegram.db, sesiones, grabaciones, configuración).
   - Relanza TelegramAccess con la nueva versión.
   - Detiene el sonido de espera tan pronto arranca la nueva versión.
"""

import os
import re
import sys
import json
import shutil
import zipfile
import logging
import urllib.request
from pathlib import Path

from app.core.paths import ROOT_DIR, IS_FROZEN, get_resource_path
from app.core.plataforma import ES_WINDOWS
from app.core.version import APP_VERSION, APP_NAME

log = logging.getLogger(__name__)

# Repositorio GitHub del autor / desarrollador
GITHUB_USUARIO = "joseonce"
GITHUB_REPO = "TelegramAccess"
URL_GITHUB_BASE = f"https://github.com/{GITHUB_USUARIO}/{GITHUB_REPO}"
URL_GITHUB_RELEASES = f"{URL_GITHUB_BASE}/releases"
URL_GITHUB_LATEST_JSON = f"{URL_GITHUB_RELEASES}/latest/download/version.json"

_CABECERAS = {"User-Agent": "TelegramAccess-Updater/1.0"}
_TIEMPO_ESPERA = 20

# Nombres de archivos y carpetas temporales durante la actualización
NOMBRE_ZIP_DESCARGA = "_actualizacion_telegramaccess.zip"
NOMBRE_CARPETA_TEMP = "_actualizacion_temp"
NOMBRE_SCRIPT = "_actualizar_telegramaccess.bat"
NOMBRE_LOCK_SONIDO = "_actualizando.lock"

# Límites de seguridad para descompresión
_MAX_MIEMBROS_ZIP = 30000
_MAX_TAM_MIEMBRO = 1 * 1024 ** 3    # 1 GB
_MAX_TAM_TOTAL = 3 * 1024 ** 3      # 3 GB


def _parsear_version(v):
    """Convierte '1.0.30' a la tupla (1, 0, 30)."""
    numeros = re.findall(r"\d+", str(v or ""))
    return tuple(int(n) for n in numeros) if numeros else (0,)


def version_local():
    return APP_VERSION


class DescargaCancelada(Exception):
    """Excepción lanzada cuando el usuario cancela la descarga en curso."""
    pass


def _leer_manifiesto(url, timeout=_TIEMPO_ESPERA):
    """Descarga y valida el archivo version.json desde una URL remota."""
    try:
        req = urllib.request.Request(url, headers=_CABECERAS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            datos = json.loads(r.read().decode("utf-8"))
        if not isinstance(datos, dict) or not str(datos.get("version", "")).strip():
            return None
        return datos
    except Exception as e:
        log.debug(f"No se pudo leer el manifiesto de versión ({url}): {e}")
        return None


def obtener_info_remota(timeout=_TIEMPO_ESPERA):
    """Devuelve el dict contenido en version.json desde GitHub Releases, o None."""
    datos = _leer_manifiesto(URL_GITHUB_LATEST_JSON, timeout=timeout)
    return datos


def obtener_version_remota(timeout=_TIEMPO_ESPERA):
    """Devuelve el string de la versión remota disponible en GitHub, o None."""
    datos = obtener_info_remota(timeout=timeout)
    if not datos:
        return None
    v = str(datos.get("version", "")).strip()
    return v or None


def hay_actualizacion(version_remota, version_local_=None):
    """Devuelve True si la versión remota es numéricamente superior a la local."""
    if not version_remota:
        return False
    try:
        return _parsear_version(version_remota) > _parsear_version(version_local_ or APP_VERSION)
    except Exception:
        return False


def _sha256_de_archivo(ruta) -> str:
    """Calcula el SHA-256 de un archivo en bloques de 1 MB."""
    import hashlib
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def verificar_zip(ruta_zip, sha256_esperado: str):
    """Verifica que el ZIP coincida exactamente con el hash publicado en version.json."""
    esperado = (sha256_esperado or "").strip().lower()
    if not esperado:
        log.warning("version.json no especifica sha256: se continúa con la descarga sin validar hash.")
        return
    real = _sha256_de_archivo(ruta_zip)
    if real != esperado:
        raise ValueError(
            f"El hash SHA-256 del paquete descargado ({real[:12]}...) no coincide con el oficial ({esperado[:12]}...). "
            "El archivo puede estar incompleto o haber sido alterado."
        )
    log.info("Paquete de actualización verificado correctamente con SHA-256.")


def nombre_paquete(version):
    """Nombre del archivo ZIP empaquetado para una versión."""
    return f"TelegramAccess_v{version}.zip"


def url_del_zip_github(version):
    """URL de descarga directa del paquete en GitHub Releases."""
    return f"{URL_GITHUB_RELEASES}/download/v{version}/{nombre_paquete(version)}"


def url_del_zip_latest():
    """URL alternativa al release latest."""
    return f"{URL_GITHUB_RELEASES}/latest/download/{nombre_paquete(APP_VERSION)}"


def ruta_base_instalacion():
    """Ruta raíz de la instalación de TelegramAccess."""
    return str(ROOT_DIR)


def actualizacion_disponible_para_instalar():
    """Comprueba si el entorno permite la actualización en caliente (ejecutable empaquetado)."""
    return bool(IS_FROZEN)


def descargar_zip(version, ruta_destino, progreso=None, cancelado=None, timeout=180):
    """Descarga el ZIP de la release indicada desde GitHub."""
    urls = [
        url_del_zip_github(version),
        f"{URL_GITHUB_RELEASES}/latest/download/{nombre_paquete(version)}",
    ]
    ultimo_error = None
    for url in urls:
        try:
            return _descargar_de(url, ruta_destino, progreso, cancelado, timeout)
        except DescargaCancelada:
            raise
        except Exception as e:
            ultimo_error = e
            log.warning(f"Error descargando desde {url}: {e}")
    if ultimo_error:
        raise ultimo_error
    raise RuntimeError(f"No se pudo descargar la versión {version} desde GitHub.")


def _descargar_de(url, ruta_destino, progreso, cancelado, timeout):
    log.info(f"Descargando actualización desde: {url}")
    req = urllib.request.Request(url, headers=_CABECERAS)
    resp = urllib.request.urlopen(req, timeout=timeout)
    try:
        total = int(resp.headers.get("Content-Length", 0) or 0)
        leido = 0
        with open(ruta_destino, "wb") as f:
            while True:
                if cancelado and cancelado():
                    raise DescargaCancelada("Descarga cancelada por el usuario.")
                bloque = resp.read(65536)
                if not bloque:
                    break
                f.write(bloque)
                leido += len(bloque)
                if progreso:
                    progreso(leido, total)
    finally:
        resp.close()
    return ruta_destino


def extraer_zip(ruta_zip, ruta_temp, progreso=None):
    """Extrae el ZIP de forma segura a ruta_temp omitiendo el prefijo de carpeta raíz si existe."""
    if os.path.exists(ruta_temp):
        shutil.rmtree(ruta_temp, ignore_errors=True)
    os.makedirs(ruta_temp, exist_ok=True)

    with zipfile.ZipFile(ruta_zip) as zf:
        infos = zf.infolist()
        if len(infos) > _MAX_MIEMBROS_ZIP:
            raise ValueError(f"El paquete contiene demasiados archivos ({len(infos)}).")

        miembros = [i.filename for i in infos]
        total = len(miembros) or 1
        prefijo = ""
        if miembros:
            top = miembros[0].split("/")[0]
            if top and all(m == top or m.startswith(top + "/") for m in miembros):
                prefijo = top + "/"

        raiz_segura = os.path.realpath(ruta_temp)
        total_escrito = 0
        for i, info in enumerate(infos):
            miembro = info.filename
            rel = miembro[len(prefijo):] if prefijo and miembro.startswith(prefijo) else miembro
            if rel:
                destino = os.path.realpath(os.path.join(ruta_temp, rel))
                if os.path.commonpath([raiz_segura, destino]) != raiz_segura:
                    log.warning(f"Ruta no permitida en zip (omitida): {miembro}")
                    if progreso:
                        progreso(i + 1, total)
                    continue
                if miembro.endswith("/"):
                    os.makedirs(destino, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(destino), exist_ok=True)
                    escrito = 0
                    with zf.open(info) as src, open(destino, "wb") as dst:
                        while True:
                            b = src.read(1024 * 1024)
                            if not b:
                                break
                            escrito += len(b)
                            total_escrito += len(b)
                            if escrito > _MAX_TAM_MIEMBRO or total_escrito > _MAX_TAM_TOTAL:
                                raise ValueError("El paquete excede el tamaño máximo permitido.")
                            dst.write(b)
            if progreso:
                progreso(i + 1, total)

    # Verificación de integridad: el paquete extraído debe contener el ejecutable o main.py
    if not any(os.path.exists(os.path.join(ruta_temp, n)) for n in ("TelegramAccess.exe", "main.py")):
        raise ValueError("El paquete descargado no contiene los componentes válidos de TelegramAccess.")


def comando_relanzar():
    """Comando de reinicio del ejecutable o script."""
    if IS_FROZEN:
        return f'start "" "{sys.executable}"'
    script_py = os.path.abspath(sys.argv[0])
    return f'start "" "{sys.executable}" "{script_py}"'


def crear_script_actualizacion(ruta_base, ruta_temp, ruta_zip):
    """Crea el script por lotes que aplica la actualización y reproduce el sonido de espera."""
    return _crear_script_windows(ruta_base, ruta_temp, ruta_zip)


def _crear_script_windows(ruta_base, ruta_temp, ruta_zip):
    """
    Genera el archivo .bat auxiliar que:
    1. Activa un bucle invisible con PowerShell para reproducir updating.wav de forma continua.
    2. Espera a que el proceso anterior finalice por completo.
    3. Copia los archivos actualizados mediante robocopy sobre ruta_base (respetando datos de usuario).
    4. Limpia la carpeta temporal y el zip descargado.
    5. Relanza la nueva versión de TelegramAccess.
    6. Detiene el sonido de espera eliminando el archivo testigo y se autoelimina.
    """
    pid = os.getpid()
    script_path = os.path.join(ruta_base, NOMBRE_SCRIPT)
    sound_path = os.path.join(ruta_base, "data", "sounds", "default", "updating.wav")
    lock_path = os.path.join(ruta_base, NOMBRE_LOCK_SONIDO)
    error_log = os.path.join(ruta_base, "_actualizacion_error.log")

    contenido = (
        "@echo off\r\n"
        "chcp 65001 >nul 2>&1\r\n"
        f'echo 1 > "{lock_path}"\r\n'
        "\r\n"
        ":: Reproducir sonido de espera en segundo plano mientras se instala la nueva versión\r\n"
        f'start "" /B powershell -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -Command "$s = \'{sound_path}\'; if (Test-Path $s) {{ $p = New-Object System.Media.SoundPlayer($s); while (Test-Path \'{lock_path}\') {{ $p.PlaySync(); Start-Sleep -Milliseconds 450 }} }}"\r\n'
        "\r\n"
        "set /a intento=0\r\n"
        ":esperar\r\n"
        f'tasklist /FI "PID eq {pid}" 2>NUL | find /I "{pid}" >NUL\r\n'
        "if not errorlevel 1 (\r\n"
        '    set /a "intento+=1"\r\n'
        "    if %intento% gtr 30 (\r\n"
        f"        taskkill /F /PID {pid} >nul 2>&1\r\n"
        "    ) else (\r\n"
        "        ping 127.0.0.1 -n 2 >nul\r\n"
        "        goto esperar\r\n"
        "    )\r\n"
        ")\r\n"
        "\r\n"
        f'robocopy "{ruta_temp}" "{ruta_base}" /E /IS /IT /R:3 /W:1 /NFL /NDL /NJH /NJS >nul 2>&1\r\n'
        "if errorlevel 8 (\r\n"
        f'    echo robocopy fallo con codigo %errorlevel% > "{error_log}"\r\n'
        ") else (\r\n"
        f'    rmdir /s /q "{ruta_temp}" >nul 2>&1\r\n'
        f'    del /q "{ruta_zip}" >nul 2>&1\r\n'
        ")\r\n"
        "\r\n"
        "ping 127.0.0.1 -n 2 >nul\r\n"
        "\r\n"
        ":: Relanzar la aplicación con la versión nueva\r\n"
        f"{comando_relanzar()}\r\n"
        "\r\n"
        ":: Forzar activación en primer plano de TelegramAccess tras el inicio\r\n"
        'start "" /B powershell -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Milliseconds 600; $w = New-Object -ComObject WScript.Shell; $w.AppActivate(\'TelegramAccess\')"\r\n'
        "\r\n"
        ":: Detener el sonido de espera eliminando el archivo testigo\r\n"
        f'del /q "{lock_path}" >nul 2>&1\r\n'
        'del "%~f0" >nul 2>&1\r\n'
    )
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(contenido)
    return script_path
