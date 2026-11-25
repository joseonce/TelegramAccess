# -*- coding: utf-8 -*-
"""
Diálogo de actualización de TelegramAccess.

Muestra información de la nueva versión disponible en GitHub, descarga el paquete
ZIP con seguimiento de progreso, verifica su firma/hash SHA-256, lo extrae,
reproduce el sonido de espera durante todo el proceso y reinicia la aplicación.
La base de datos (telegram.db), sesiones, credenciales y grabaciones nunca se tocan.
"""

import os
import logging
import threading
import winsound
from pathlib import Path

import wx

from app.core.speech import speak
from app.core.paths import get_resource_path
from app.services.updater import update_service as upd
from .accessible_controls import mostrar_info

log = logging.getLogger(__name__)


class DialogoActualizacion(wx.Dialog):
    """Diálogo accesible para descargar e instalar una actualización de TelegramAccess."""

    def __init__(self, frame, version_remota, notas=""):
        super().__init__(
            frame,
            title=_("Actualización disponible de TelegramAccess"),
            style=wx.DEFAULT_DIALOG_STYLE,
            name=_("Diálogo de actualización")
        )
        self._frame = frame
        self._version = version_remota
        self._notas = notas
        self._cancelado = False
        self._trabajando = False
        self._sonido_en_curso = False

        self._init_ui()
        self.CenterOnParent()
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self.btn_instalar.SetFocus()

    def _init_ui(self):
        s = wx.BoxSizer(wx.VERTICAL)

        info_txt = _(
            "Hay una nueva versión de TelegramAccess disponible en GitHub.\n\n"
            "Versión actual: {actual}\n"
            "Versión nueva: {nueva}\n"
        ).format(actual=upd.version_local(), nueva=self._version)

        if self._notas:
            info_txt += _("\nNovedades de esta versión:\n{notas}\n").format(notas=self._notas)

        info_txt += _("\n¿Deseas descargarla e instalarla ahora? La aplicación se reiniciará automáticamente.")

        self.lbl = wx.StaticText(self, label=info_txt, name=_("Información de actualización"))
        s.Add(self.lbl, 0, wx.ALL | wx.EXPAND, 12)

        self.gauge = wx.Gauge(self, range=100, size=(-1, 24), name=_("Barra de progreso de descarga"))
        self.gauge.Hide()
        s.Add(self.gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        self.lbl_prog = wx.StaticText(self, label="", name=_("Detalle de progreso"))
        self.lbl_prog.Hide()
        s.Add(self.lbl_prog, 0, wx.ALL, 12)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_instalar = wx.Button(self, label=_("&Instalar ahora"), name=_("Iniciar instalación"))
        self.btn_instalar.Bind(wx.EVT_BUTTON, self._on_instalar)
        self.btn_instalar.SetDefault()
        btns.Add(self.btn_instalar, 0, wx.ALL, 5)

        self.btn_cerrar = wx.Button(self, wx.ID_CANCEL, _("&Ahora no"), name=_("Cerrar sin actualizar"))
        self.btn_cerrar.Bind(wx.EVT_BUTTON, self._on_boton_cerrar)
        btns.Add(self.btn_cerrar, 0, wx.ALL, 5)

        s.Add(btns, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizerAndFit(s)

    def _iniciar_sonido_espera(self):
        """Reproduce en bucle el sonido de espera (updating.wav)."""
        try:
            ruta_sound = get_resource_path("sounds/default/updating.wav")
            if ruta_sound.exists():
                self._sonido_en_curso = True
                winsound.PlaySound(str(ruta_sound), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
        except Exception as e:
            log.debug(f"Aviso al reproducir sonido de espera: {e}")

    def _detener_sonido_espera(self):
        """Detiene cualquier sonido en bucle."""
        if self._sonido_en_curso:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
            self._sonido_en_curso = False

    def _on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            if not self._trabajando:
                self.EndModal(wx.ID_CANCEL)
            return
        event.Skip()

    def _on_boton_cerrar(self, event):
        if self._trabajando:
            self._cancelado = True
            self.btn_cerrar.Disable()
            self.lbl.SetLabel(_("Cancelando actualización..."))
        else:
            self._detener_sonido_espera()
            self.EndModal(wx.ID_CANCEL)

    def _on_close(self, event):
        if self._trabajando:
            return
        self._detener_sonido_espera()
        self.EndModal(wx.ID_CANCEL)

    def _ui_estado(self, texto):
        if self:
            self.lbl.SetLabel(texto)
            self.Layout()

    def _ui_progreso(self, valor, texto):
        if not self:
            return
        if not self.gauge.IsShown():
            self.gauge.Show()
            self.lbl_prog.Show()
            self.Layout()
        if valor is None:
            self.gauge.Pulse()
        else:
            self.gauge.SetValue(max(0, min(100, int(valor))))
        if texto:
            self.lbl_prog.SetLabel(texto)

    @staticmethod
    def _fmt(n):
        if n < 1024:
            return f"{n} B"
        if n < 1024 * 1024:
            return f"{n / 1024:.1f} KB"
        return f"{n / (1024 * 1024):.1f} MB"

    def _on_instalar(self, event):
        if not upd.actualizacion_disponible_para_instalar():
            mostrar_info(
                self,
                _("La actualización automática en caliente está diseñada para el ejecutable empaquetado de TelegramAccess (TelegramAccess.exe).\n\n"
                  "Para probar la actualización completa con descarga, sonido de espera e instalación desatendida, abre el ejecutable en 'dist/TelegramAccess/TelegramAccess.exe'."),
                _("Versión no empaquetada")
            )
            return

        self._trabajando = True
        self.btn_instalar.Disable()
        self.btn_cerrar.SetLabel(_("&Cancelar"))
        speak(_("Iniciando descarga de la actualización..."), interrupt=True)
        self._iniciar_sonido_espera()

        threading.Thread(target=self._trabajo_descarga_e_instalacion, daemon=True).start()

    def _trabajo_descarga_e_instalacion(self):
        ruta_base = upd.ruta_base_instalacion()
        ruta_zip = os.path.join(ruta_base, upd.NOMBRE_ZIP_DESCARGA)
        ruta_temp = os.path.join(ruta_base, upd.NOMBRE_CARPETA_TEMP)

        try:
            # 1. Descarga con progreso
            def _prog_descarga(leido, total):
                if total > 0:
                    pct = int(leido / total * 100)
                    wx.CallAfter(self._ui_progreso, pct, _("Descargando: {0} de {1} ({2}%)").format(
                        self._fmt(leido), self._fmt(total), pct))
                else:
                    wx.CallAfter(self._ui_progreso, None, _("Descargando: {0}").format(self._fmt(leido)))

            wx.CallAfter(self._ui_estado, _("Descargando TelegramAccess v{0}...").format(self._version))
            upd.descargar_zip(self._version, ruta_zip, progreso=_prog_descarga, cancelado=lambda: self._cancelado)

            # 2. Verificación de hash SHA-256
            wx.CallAfter(self._ui_estado, _("Verificando la integridad del paquete..."))
            info = upd.obtener_info_remota() or {}
            upd.verificar_zip(ruta_zip, info.get("sha256", ""))

            # 3. Extracción de archivos
            wx.CallAfter(self._ui_estado, _("Extrayendo archivos de la actualización..."))

            def _prog_extra(hechos, total):
                pct = int(hechos / total * 100) if total else 0
                wx.CallAfter(self._ui_progreso, pct, _("Extrayendo: {0} de {1}").format(hechos, total))

            upd.extraer_zip(ruta_zip, ruta_temp, progreso=_prog_extra)

            # 4. Creación del script por lotes con sonido de espera
            wx.CallAfter(self._ui_estado, _("Preparando la instalación y reinicio..."))
            script = upd.crear_script_actualizacion(ruta_base, ruta_temp, ruta_zip)

            # 5. Confirmación final
            wx.CallAfter(self._confirmar_reinicio, script)

        except Exception as e:
            log.error(f"Error durante la actualización: {e}", exc_info=True)
            self._detener_sonido_espera()
            try:
                if os.path.exists(ruta_temp):
                    import shutil
                    shutil.rmtree(ruta_temp, ignore_errors=True)
                if os.path.exists(ruta_zip):
                    os.remove(ruta_zip)
            except Exception:
                pass
            wx.CallAfter(self._fallo, str(e))

    def _fallo(self, err):
        self._trabajando = False
        self._detener_sonido_espera()
        if not self:
            return
        if self._cancelado:
            self._ui_estado(_("Actualización cancelada."))
        else:
            self._ui_estado(_("No se pudo completar la actualización."))
            mostrar_info(
                self,
                _("No se pudo completar la actualización:\n\n{0}").format(err),
                _("Error de actualización")
            )
        self.btn_instalar.Enable()
        self.btn_cerrar.Enable()
        self.btn_cerrar.SetLabel(_("&Cerrar"))
        self._cancelado = False

    def _confirmar_reinicio(self, script_path):
        if not self:
            return
        self._detener_sonido_espera()
        self._ui_progreso(100, _("Descarga y verificación completadas con éxito."))
        mostrar_info(
            self,
            _(
                "La nueva versión se ha descargado y verificado correctamente.\n\n"
                "La aplicación se cerrará ahora para completar la actualización.\n"
                "Escucharás un sonido continuo de espera mientras se instalan los archivos "
                "hasta que TelegramAccess se abra automáticamente en su nueva versión.\n\n"
                "Pulsa Aceptar para reiniciar."
            ),
            _("Actualización lista")
        )
        try:
            self.EndModal(wx.ID_OK)
        except Exception:
            pass
        self._frame._lanzar_y_salir_actualizacion(script_path)
