# -*- coding: utf-8 -*-
"""Paneles de preferencias: Sonidos, Micrófono, Traducción y Proxy (mixin).
"""
import builtins
import app.core.i18n
import wx
import logging
from app.core.config_manager import config
from app.core.speech import speak, notificar
from .accessible_controls import AccessibleSlider, AccessibleTextCtrl, AccessibleCheckListBox

log = logging.getLogger(__name__)


class _PrefAvanzadoMixin:
    def _crear_panel_sounds(self, parent) -> wx.Panel:
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Volumen
        sizer.Add(wx.StaticText(panel, label=_("Volumen general de sonidos de interacción:")), 0, wx.ALL, 5)
        vol_actual = int(config.get("audio", "volume", 0.8) * 100)
        self.slider_volume = AccessibleSlider(
            panel,
            value=vol_actual,
            minValue=0,
            maxValue=100,
            name=_("Volumen de sonidos"),
            unidad="%"
        )
        sizer.Add(self.slider_volume, 0, wx.EXPAND | wx.ALL, 5)

        # Mute global
        self.cb_mute = wx.CheckBox(
            panel,
            label=_("Silenciar todos los sonidos (Mute)"),
            name=_("Silenciar sonidos")
        )
        self.cb_mute.SetValue(config.get("audio", "mute", False))
        sizer.Add(self.cb_mute, 0, wx.ALL, 10)

        # Paquete de sonidos
        sizer.Add(wx.StaticText(panel, label=_("Paquete de sonidos:")), 0, wx.ALL, 5)
        try:
            from app.services.audio.sound_manager import sound_manager
            self._paquetes_sonido = sound_manager.listar_paquetes_sonido() if hasattr(sound_manager, "listar_paquetes_sonido") else ["default"]
        except Exception:
            self._paquetes_sonido = ["default"]
        self.choice_sound_pack = wx.Choice(panel, choices=self._paquetes_sonido, name=_("Paquete de sonidos"))
        pack_actual = config.get("audio", "sound_pack", "default")
        self.choice_sound_pack.SetSelection(self._paquetes_sonido.index(pack_actual) if pack_actual in self._paquetes_sonido else 0)
        sizer.Add(self.choice_sound_pack, 0, wx.EXPAND | wx.ALL, 5)

        # Dispositivo de salida de audio
        sizer.Add(wx.StaticText(panel, label=_("Dispositivo de salida de audio:")), 0, wx.ALL, 5)
        try:
            from app.services.audio.sound_manager import sound_manager
            self._dispositivos_salida = sound_manager.listar_dispositivos_salida() if hasattr(sound_manager, "listar_dispositivos_salida") else []
        except Exception:
            self._dispositivos_salida = []
        opciones_dev = [_("Predeterminado del sistema")] + self._dispositivos_salida
        self.choice_output_device = wx.Choice(panel, choices=opciones_dev, name=_("Dispositivo de salida de audio"))
        actual_dev = config.get("audio", "output_device", "")
        if actual_dev in self._dispositivos_salida:
            self.choice_output_device.SetSelection(self._dispositivos_salida.index(actual_dev) + 1)
        else:
            self.choice_output_device.SetSelection(0)
        self.choice_output_device.SetToolTip(_("Cambiar el dispositivo requiere reiniciar la aplicación."))
        sizer.Add(self.choice_output_device, 0, wx.EXPAND | wx.ALL, 5)

        # Lista de sonidos individuales
        sizer.Add(wx.StaticText(panel, label=_("Activar o desactivar sonidos individuales:")), 0, wx.ALL, 5)

        self.sound_event_keys = [
            "app_start", "app_exit", "focus_changed", "buffer_changed",
            "connection_ok", "connection_error", "telegram_new_message",
            "operation_done", "warning", "error", "player_opened",
            "status_has_media", "status_direct"
        ]

        descriptions = [
            _("Inicio de aplicación"),
            _("Salida de aplicación"),
            _("Cambio de enfoque"),
            _("Cambio de chat o buffer"),
            _("Conexión establecida"),
            _("Error de conexión"),
            _("Nuevo mensaje en Telegram"),
            _("Operación completada"),
            _("Advertencia"),
            _("Error general"),
            _("Reproductor multimedia abierto"),
            _("Mensaje con multimedia"),
            _("Mensaje directo recibido")
        ]

        self.clb_sounds = AccessibleCheckListBox(
            panel,
            choices=descriptions,
            size=(-1, 150),
            name=_("Lista de sonidos individuales")
        )

        disabled = config.get("audio", "disabled_events", [])
        for idx, key in enumerate(self.sound_event_keys):
            self.clb_sounds.Check(idx, key not in disabled)

        sizer.Add(self.clb_sounds, 1, wx.EXPAND | wx.ALL, 5)

        # Botón para probar sonidos
        self.btn_probar_sonidos = wx.Button(panel, label=_("Pro&bar sonidos..."), name=_("Abrir diálogo de prueba de sonidos"))
        self.btn_probar_sonidos.Bind(wx.EVT_BUTTON, self._on_probar_sonidos)
        sizer.Add(self.btn_probar_sonidos, 0, wx.ALL, 5)

        panel.SetSizer(sizer)
        return panel

    def _on_probar_sonidos(self, event):
        from .sound_test_dialog import SoundTestDialog
        dlg = SoundTestDialog(self)
        dlg.ShowModal()
        dlg.Destroy()

    def _panel_microfono(self, parent) -> wx.Panel:
        """Panel del micrófono para notas de voz."""
        panel = wx.ScrolledWindow(parent)
        panel.SetScrollRate(0, 10)
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(panel, label=_("Micrófono para grabar notas de voz:")), 0, wx.ALL, 5)
        self.choice_mic = wx.Choice(panel, name=_("Selector de micrófono"))
        sizer.Add(self.choice_mic, 0, wx.EXPAND | wx.ALL, 5)
        self._mics = []
        self._cargar_microfonos()

        btn_mic_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_refresh_mic = wx.Button(panel, label=_("&Actualizar lista de micrófonos"), name=_("Volver a detectar micrófonos"))
        self.btn_refresh_mic.Bind(wx.EVT_BUTTON, lambda e: self._cargar_microfonos())
        btn_mic_sizer.Add(self.btn_refresh_mic, 0, wx.ALL, 5)
        self.btn_test_mic = wx.Button(panel, label=_("&Probar micrófono"), name=_("Grabar una prueba y reproducirla"))
        self.btn_test_mic.Bind(wx.EVT_BUTTON, self._on_probar_microfono)
        btn_mic_sizer.Add(self.btn_test_mic, 0, wx.ALL, 5)
        sizer.Add(btn_mic_sizer, 0, wx.ALL, 2)

        sizer.Add(wx.StaticText(panel, label=_("Volumen del micrófono (porcentaje):")), 0, wx.ALL, 5)
        from app.services.audio import microphone
        _dev, _vol = microphone.config_microfono()
        self.slider_mic_vol = AccessibleSlider(
            panel, value=int(float(_vol) * 100),
            minValue=0, maxValue=200, name=_("Volumen del micrófono"), unidad="%"
        )
        sizer.Add(self.slider_mic_vol, 0, wx.EXPAND | wx.ALL, 5)

        panel.SetSizer(sizer)
        return panel

    def _cargar_microfonos(self):
        """Detecta los micrófonos disponibles y rellena el selector."""
        from app.services.audio import microphone
        try:
            self._mics = microphone.listar_microfonos()
        except Exception:
            self._mics = []
        opciones = [_("(Predeterminado del sistema)")] + self._mics
        self.choice_mic.SetItems(opciones)
        guardado = microphone.config_microfono()[0]
        if guardado and guardado in self._mics:
            self.choice_mic.SetSelection(self._mics.index(guardado) + 1)
        else:
            self.choice_mic.SetSelection(0)

    def _mic_seleccionado(self) -> str:
        idx = self.choice_mic.GetSelection()
        if idx <= 0:
            return ""
        return self._mics[idx - 1]

    def _on_probar_microfono(self, event):
        from app.core.task_manager import task_manager
        from app.services.audio import microphone
        from app.services.media_player.player_service import player_service
        dispositivo = self._mic_seleccionado()
        volumen = self.slider_mic_vol.GetValue() / 100.0
        speak(_("Grabando 4 segundos de prueba. Hable ahora..."), interrupt=True)
        self.btn_test_mic.Disable()

        def _bg(ctx):
            return microphone.grabar_prueba(dispositivo or None, volumen, segundos=4)

        def _finish(res, err):
            self.btn_test_mic.Enable()
            if err:
                notificar(_("Fallo en la prueba: {0}").format(err))
            else:
                speak(_("Reproduciendo la prueba grabada."), interrupt=True)
                player_service.cargar_y_reproducir(res, _("Prueba de micrófono"))

        task_manager.start_task(_bg, callback=_finish, pass_context=True)

    def _crear_panel_translation(self, parent) -> wx.Panel:
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(panel, label=_("Motor de traducción (gratuitos, sin clave):")), 0, wx.ALL, 5)
        from app.services.translation.translation_service import translation_service
        self._trad_provs = translation_service.proveedores_disponibles()
        self.choice_trad_prov = wx.Choice(panel, choices=[e for _k, e in self._trad_provs],
                                          name=_("Selector de motor de traducción"))
        actual = config.get("translation", "provider", "google_api_free")
        idx = next((i for i, (k, _e) in enumerate(self._trad_provs) if k == actual), 0)
        self.choice_trad_prov.SetSelection(idx)
        sizer.Add(self.choice_trad_prov, 0, wx.EXPAND | wx.ALL, 5)

        sizer.Add(wx.StaticText(panel, label=_("Idioma de destino predeterminado:")), 0, wx.ALL, 5)
        self.choice_target_lang = wx.Choice(panel, choices=["es", "en", "fr", "de", "it", "pt", "ru"],
                                            name=_("Idioma de destino"))
        target = config.get("translation", "default_target", "es")
        self.choice_target_lang.SetStringSelection(target)
        sizer.Add(self.choice_target_lang, 0, wx.EXPAND | wx.ALL, 5)

        self.cb_copy_translation = wx.CheckBox(
            panel, label=_("Copiar automáticamente la traducción al portapapeles"),
            name=_("Copiar traducción"))
        self.cb_copy_translation.SetValue(config.get("translation", "copy_on_translate", True))
        sizer.Add(self.cb_copy_translation, 0, wx.ALL, 8)

        self.cb_save_translation_history = wx.CheckBox(
            panel, label=_("Guardar historial de traducciones"),
            name=_("Guardar historial"))
        self.cb_save_translation_history.SetValue(config.get("translation", "save_history", True))
        sizer.Add(self.cb_save_translation_history, 0, wx.ALL, 8)

        panel.SetSizer(sizer)
        return panel

    def _crear_panel_proxy(self, parent) -> wx.Panel:
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(panel, label=_(
            "Conectar a través de un proxy de red."
        )), 0, wx.ALL, 5)

        self.cb_proxy_enabled = wx.CheckBox(
            panel, label=_("Usar un proxy para las conexiones"), name=_("Activar proxy"))
        self.cb_proxy_enabled.SetValue(config.get("proxy", "enabled", False))
        sizer.Add(self.cb_proxy_enabled, 0, wx.ALL, 10)

        sizer.Add(wx.StaticText(panel, label=_("Tipo de proxy:")), 0, wx.LEFT | wx.TOP, 5)
        self._proxy_types = ["http", "https", "socks5"]
        self.choice_proxy_type = wx.Choice(panel, choices=self._proxy_types, name=_("Tipo de proxy"))
        tipo = config.get("proxy", "type", "http")
        self.choice_proxy_type.SetSelection(self._proxy_types.index(tipo) if tipo in self._proxy_types else 0)
        sizer.Add(self.choice_proxy_type, 0, wx.ALL, 5)

        sizer.Add(wx.StaticText(panel, label=_("Servidor:")), 0, wx.LEFT | wx.TOP, 5)
        self.txt_proxy_server = AccessibleTextCtrl(
            panel, value=str(config.get("proxy", "server", "")),
            name=_("Servidor del proxy"),
            ayuda_texto=_("Dirección o nombre del servidor proxy."))
        sizer.Add(self.txt_proxy_server, 0, wx.EXPAND | wx.ALL, 5)

        sizer.Add(wx.StaticText(panel, label=_("Puerto:")), 0, wx.LEFT | wx.TOP, 5)
        self.spin_proxy_port = wx.SpinCtrl(
            panel, min=1, max=65535,
            initial=int(config.get("proxy", "port", 8080) or 8080),
            name=_("Puerto del proxy"))
        sizer.Add(self.spin_proxy_port, 0, wx.ALL, 5)

        sizer.Add(wx.StaticText(panel, label=_("Usuario (opcional):")), 0, wx.LEFT | wx.TOP, 5)
        self.txt_proxy_user = AccessibleTextCtrl(
            panel, value=str(config.get("proxy", "user", "")),
            name=_("Usuario del proxy"))
        sizer.Add(self.txt_proxy_user, 0, wx.EXPAND | wx.ALL, 5)

        sizer.Add(wx.StaticText(panel, label=_("Contraseña (opcional):")), 0, wx.LEFT | wx.TOP, 5)
        self.txt_proxy_pass = AccessibleTextCtrl(
            panel, value=str(config.get("proxy", "password", "")),
            style=wx.TE_PASSWORD,
            name=_("Contraseña del proxy"))
        sizer.Add(self.txt_proxy_pass, 0, wx.EXPAND | wx.ALL, 5)

        panel.SetSizer(sizer)
        return panel
