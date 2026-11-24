# -*- coding: utf-8 -*-
"""
Punto de entrada principal para TelegramAccess.
Inicializa el entorno, base de datos, configuraciones, sonidos y lanza la UI.
"""

import sys
import os
import logging
import traceback
import warnings
import socket

warnings.filterwarnings("ignore", message=r".*chardet.*", module="requests")

sys.setswitchinterval(0.001)
socket.setdefaulttimeout(60)

# Asegurar ruta raíz en sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.paths import inicializar_directorios, asegurar_bin_en_path, get_data_path

log = logging.getLogger(__name__)


def main():
    inicializar_directorios()
    asegurar_bin_en_path()

    from app.core.config_manager import config
    from app.core.logger import configurar_logging
    configurar_logging(debug_mode=config.get("general", "debug", False))

    from app.core.i18n import inicializar_traducciones
    inicializar_traducciones()

    log.info("Iniciando TelegramAccess...")

    import wx
    from app.core.speech import speak

    app = wx.App(False)
    from app.ui.wx_plataforma import registrar as _registrar_wx
    _registrar_wx()

    try:
        wx_locale = wx.Locale(wx.LANGUAGE_SPANISH)
    except Exception as e:
        log.warning(f"No se pudo fijar la locale de wx a español: {e}")

    # Comprobación de instancia única
    global _instance_checker
    _instance_checker = wx.SingleInstanceChecker("TelegramAccess-" + wx.GetUserId())
    if _instance_checker.IsAnotherRunning():
        aviso = "Ya hay otra instancia de TelegramAccess en ejecución."
        log.warning(aviso)
        print(f"\n[AVISO] {aviso} Ciérrala antes de iniciar una nueva.\n")
        speak(aviso, interrupt=True)
        return

    # Aviso de inicio por voz
    speak("Iniciando TelegramAccess. Espere por favor.", interrupt=True, sync=True)

    # Migraciones de base de datos
    from app.core.migrations import ejecutar_migraciones
    try:
        ejecutar_migraciones()
    except Exception as e:
        log.critical(f"Error grave al inicializar la base de datos: {e}")
        speak("Error grave al inicializar la base de datos.", interrupt=True)
        sys.exit(1)

    # Inicializar motor de sonido
    from app.services.audio.sound_manager import sound_manager
    if not sound_manager.inicializar():
        log.warning("El sistema de audio no se pudo inicializar. La app se ejecutará sin sonidos.")

    # Crear y mostrar ventana principal
    from app.ui.main_frame import MainFrame
    frame = MainFrame()

    iniciar_en_bandeja = config.get("general", "start_minimized", False)
    if not iniciar_en_bandeja:
        frame.Show(True)

    if config.get("general", "ready_sound", True):
        sound_manager.reproducir("ready")
    if config.get("general", "ready_message", True):
        speak("TelegramAccess listo.", interrupt=False)

    app.MainLoop()


if __name__ == "__main__":
    main()
