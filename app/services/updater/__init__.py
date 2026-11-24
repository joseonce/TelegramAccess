# -*- coding: utf-8 -*-
"""Módulo del servicio de actualización de TelegramAccess."""

from .update_service import (
    obtener_version_remota,
    obtener_info_remota,
    hay_actualizacion,
    descargar_zip,
    verificar_zip,
    extraer_zip,
    crear_script_actualizacion,
    actualizacion_disponible_para_instalar,
    ruta_base_instalacion,
    version_local,
    NOMBRE_ZIP_DESCARGA,
    NOMBRE_CARPETA_TEMP,
    NOMBRE_SCRIPT,
)

__all__ = [
    "obtener_version_remota",
    "obtener_info_remota",
    "hay_actualizacion",
    "descargar_zip",
    "verificar_zip",
    "extraer_zip",
    "crear_script_actualizacion",
    "actualizacion_disponible_para_instalar",
    "ruta_base_instalacion",
    "version_local",
    "NOMBRE_ZIP_DESCARGA",
    "NOMBRE_CARPETA_TEMP",
    "NOMBRE_SCRIPT",
]
