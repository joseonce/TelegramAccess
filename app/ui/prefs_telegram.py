# -*- coding: utf-8 -*-
"""Paneles de preferencias: sección Telegram y Telegram Drive (mixin).
"""
import builtins
import app.core.i18n
import wx
from app.core.config_manager import config
from .accessible_controls import AccessibleTextCtrl


class _PrefTelegramMixin:
    def _panel_telegram_root(self, parent) -> wx.Panel:
        panel = wx.ScrolledWindow(parent)
        panel.SetScrollRate(0, 10)
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(panel, label=_("Intervalo de actualización de Telegram (segundos, mínimo 10):")), 0, wx.ALL, 5)
        self.txt_telegram_interval = AccessibleTextCtrl(
            panel, value=str(config.get("telegram", "update_interval", 60)),
            name=_("Intervalo actualización Telegram"),
            ayuda_texto=_("Segundos entre comprobaciones automáticas de los chats."))
        sizer.Add(self.txt_telegram_interval, 0, wx.EXPAND | wx.ALL, 5)

        from app.services.telegram.telegram_service import telegram_service

        sizer.Add(wx.StaticText(panel, label=_(
            "Para usar Telegram necesita un api_id y api_hash propios.\n"
            "Obténgalos gratis iniciando sesión en https://my.telegram.org, sección 'API development tools'."
        )), 0, wx.ALL, 5)

        api_id, api_hash = telegram_service.get_api_credentials()

        sizer.Add(wx.StaticText(panel, label=_("api_id (numérico):")), 0, wx.ALL, 5)
        self.txt_tg_api_id = AccessibleTextCtrl(
            panel,
            value=str(api_id or ""),
            name=_("api_id de Telegram"),
            ayuda_texto=_("Identificador numérico de su aplicación de Telegram obtenido en my.telegram.org.")
        )
        sizer.Add(self.txt_tg_api_id, 0, wx.EXPAND | wx.ALL, 5)

        sizer.Add(wx.StaticText(panel, label=_("api_hash:")), 0, wx.ALL, 5)
        self.txt_tg_api_hash = AccessibleTextCtrl(
            panel,
            value=api_hash or "",
            style=wx.TE_PASSWORD,
            name=_("api_hash de Telegram"),
            ayuda_texto=_("Cadena secreta de su aplicación de Telegram. Se guarda de forma segura.")
        )
        sizer.Add(self.txt_tg_api_hash, 0, wx.EXPAND | wx.ALL, 5)

        # Carpeta de descargas
        sizer.Add(wx.StaticText(panel, label=_("Carpeta de descargas de Telegram:")), 0, wx.ALL, 5)
        self.txt_tg_downloads = AccessibleTextCtrl(
            panel,
            value=config.get("telegram", "download_dir", ""),
            name=_("Carpeta de descargas de Telegram"),
            ayuda_texto=_("Ruta donde se guardarán fotos, audios y documentos descargados. Vacío usa data/downloads.")
        )
        sizer.Add(self.txt_tg_downloads, 0, wx.EXPAND | wx.ALL, 5)

        # Organizar descargas en subcarpetas
        self.cb_tg_subdirs = wx.CheckBox(panel, label=_("Organizar descargas en subcarpetas por chat y tipo"), name=_("Organizar descargas en subcarpetas"))
        self.cb_tg_subdirs.SetValue(config.get("telegram", "download_subdirs", True))
        sizer.Add(self.cb_tg_subdirs, 0, wx.ALL, 5)

        # Anunciar mensajes nuevos
        self.cb_tg_announce = wx.CheckBox(
            panel, label=_("Anunciar por voz los mensajes nuevos (solo de usuarios, no de grupos, supergrupos ni canales)"),
            name=_("Anunciar mensajes nuevos de Telegram"))
        self.cb_tg_announce.SetValue(config.get("telegram", "announce_new", True))
        self.cb_tg_announce.SetToolTip(_(
            "Lee en voz el remitente y el texto de los mensajes directos de una persona. No se "
            "anuncian los mensajes de grupos, supergrupos ni canales."))
        sizer.Add(self.cb_tg_announce, 0, wx.ALL, 5)

        # Reproducir automáticamente las notas de voz / audios
        self.cb_tg_autoplay_voice = wx.CheckBox(
            panel, label=_("Reproducir automáticamente las notas de voz y audios que lleguen al chat abierto"),
            name=_("Reproducir automáticamente las notas de voz"))
        self.cb_tg_autoplay_voice.SetValue(bool(config.get("telegram", "autoplay_voice", False)))
        self.cb_tg_autoplay_voice.SetToolTip(_(
            "Si lo activas, las notas de voz y audios se reproducen en cadena: al terminar uno pasa "
            "solo al siguiente hasta que no quede ninguno. Pausas y reanudas con Espacio."))
        sizer.Add(self.cb_tg_autoplay_voice, 0, wx.ALL, 5)

        # Marcar mensajes como leídos al pasar el foco por ellos
        self.cb_tg_mark_read = wx.CheckBox(
            panel, label=_("Marcar los mensajes como leídos al pasar por ellos"),
            name=_("Marcar leídos al navegar"))
        self.cb_tg_mark_read.SetValue(bool(config.get("telegram", "mark_read_on_focus", True)))
        self.cb_tg_mark_read.SetToolTip(_(
            "Al situarte sobre un mensaje se marca como leído, y al salir se guarda hasta dónde llegaste."))
        sizer.Add(self.cb_tg_mark_read, 0, wx.ALL, 5)

        # Señalar "(nuevo)" delante de mensajes sin leer
        self.cb_tg_unread_marker = wx.CheckBox(
            panel, label=_("Señalar con \"(nuevo)\" los mensajes sin leer"),
            name=_("Marcar los mensajes sin leer"))
        self.cb_tg_unread_marker.SetValue(bool(config.get("telegram", "show_unread_marker", True)))
        sizer.Add(self.cb_tg_unread_marker, 0, wx.ALL, 5)

        # Fila separadora "Mensajes no leídos"
        self.cb_tg_unread_divider = wx.CheckBox(
            panel, label=_("Poner una marca \"Mensajes no leídos\" antes del primero sin leer"),
            name=_("Marca de mensajes no leídos"))
        self.cb_tg_unread_divider.SetValue(bool(config.get("telegram", "show_unread_divider", True)))
        self.cb_tg_unread_divider.SetToolTip(_(
            "Al abrir un chat con mensajes sin leer, inserta una línea separadora justo antes del primero que no has leído."))
        sizer.Add(self.cb_tg_unread_divider, 0, wx.ALL, 5)

        # Sincronizar TODO el historial al abrir
        self.cb_tg_sync_todo = wx.CheckBox(
            panel, label=_("Sincronizar TODO el historial al abrir un chat (traer todo del servidor)"),
            name=_("Sincronizar todo el historial al abrir"))
        self.cb_tg_sync_todo.SetValue(bool(config.get("telegram", "sincronizar_todo_al_abrir", False)))
        self.cb_tg_sync_todo.SetToolTip(_(
            "Al abrir un chat, trae todo su historial desde el servidor de Telegram. En chats muy grandes puede tardar más."))
        sizer.Add(self.cb_tg_sync_todo, 0, wx.ALL, 5)

        # Máximo de mensajes en caché
        sizer.Add(wx.StaticText(panel, label=_("Máximo de mensajes en caché por chat (0 = sin límite):")), 0, wx.LEFT | wx.TOP, 10)
        self.spin_max_tg_msgs = wx.SpinCtrl(panel, min=0, max=100000, initial=int(config.get("telegram", "max_messages_per_chat", 0)), name=_("Máximo de mensajes por chat de Telegram"))
        sizer.Add(self.spin_max_tg_msgs, 0, wx.LEFT | wx.BOTTOM, 10)

        # Botonera de acciones bajo la lista de chats
        self.cb_tg_buttons = wx.CheckBox(panel, label=_("Mostrar la botonera de acciones bajo la lista de chats"), name=_("Mostrar botonera de acciones en Telegram"))
        self.cb_tg_buttons.SetValue(bool(config.get("telegram", "show_action_buttons", False)))
        sizer.Add(self.cb_tg_buttons, 0, wx.LEFT | wx.BOTTOM, 10)

        panel.SetSizer(sizer)
        return panel

    def _panel_telegram_drive(self, parent) -> wx.Panel:
        """Subsección de Telegram: opciones de Telegram Drive (la nube personal)."""
        panel = wx.ScrolledWindow(parent)
        panel.SetScrollRate(0, 10)
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(panel, label=_(
            "Telegram Drive guarda tus archivos en un canal privado de Telegram (solo tuyo). Se "
            "abre desde el menú Telegram → «Telegram Drive (tu nube personal)...».")), 0, wx.ALL, 8)

        sizer.Add(wx.StaticText(panel, label=_("Carpeta de descargas de la nube (vacío = carpeta por defecto):")), 0, wx.ALL, 5)
        self.txt_tgdrive_downloads = AccessibleTextCtrl(
            panel, value=config.get("telegram_drive", "carpeta_descargas", ""),
            name=_("Carpeta de descargas de Telegram Drive"))
        sizer.Add(self.txt_tgdrive_downloads, 0, wx.EXPAND | wx.ALL, 5)

        sizer.Add(wx.StaticText(panel, label=_("Transferencias simultáneas (1 = una a una; hasta 10 a la vez):")), 0, wx.ALL, 5)
        self.spin_tgdrive_simult = wx.SpinCtrl(panel, min=1, max=10,
            initial=int(config.get("telegram_drive", "max_simultaneas", 1)),
            name=_("Transferencias simultáneas de Telegram Drive"))
        sizer.Add(self.spin_tgdrive_simult, 0, wx.LEFT | wx.BOTTOM, 10)

        sizer.Add(wx.StaticText(panel, label=_("Al repetirse un nombre al subir:")), 0, wx.ALL, 5)
        self._tgdrive_conf_valores = ["preguntar", "reemplazar", "ambos", "omitir"]
        self.choice_tgdrive_conflicto = wx.Choice(panel, choices=[
            _("Preguntar siempre"), _("Reemplazar"), _("Conservar ambos"), _("Omitir")],
            name=_("Política ante nombres repetidos"))
        pol = config.get("telegram_drive", "politica_conflicto", "preguntar")
        self.choice_tgdrive_conflicto.SetSelection(
            self._tgdrive_conf_valores.index(pol) if pol in self._tgdrive_conf_valores else 0)
        sizer.Add(self.choice_tgdrive_conflicto, 0, wx.LEFT | wx.BOTTOM, 10)

        sizer.Add(wx.StaticText(panel, label=_("Días que se conservan los elementos en la papelera (0 = para siempre):")), 0, wx.ALL, 5)
        self.spin_tgdrive_papelera = wx.SpinCtrl(panel, min=0, max=3650,
            initial=int(config.get("telegram_drive", "retencion_papelera_dias", 30)),
            name=_("Días de retención de la papelera de Telegram Drive"))
        sizer.Add(self.spin_tgdrive_papelera, 0, wx.LEFT | wx.BOTTOM, 10)

        self.cb_tgdrive_confirmar = wx.CheckBox(panel, label=_("Pedir confirmación antes de enviar a la papelera"),
            name=_("Confirmar borrado en Telegram Drive"))
        self.cb_tgdrive_confirmar.SetValue(bool(config.get("telegram_drive", "confirmar_borrado", True)))
        sizer.Add(self.cb_tgdrive_confirmar, 0, wx.LEFT | wx.BOTTOM, 10)

        self.cb_tgdrive_limpiar = wx.CheckBox(panel, label=_("Limpiar los archivos temporales al terminar cada transferencia"),
            name=_("Limpiar temporales de Telegram Drive"))
        self.cb_tgdrive_limpiar.SetValue(bool(config.get("telegram_drive", "limpiar_temporales", True)))
        sizer.Add(self.cb_tgdrive_limpiar, 0, wx.LEFT | wx.BOTTOM, 10)

        sizer.Add(wx.StaticText(panel, label=_("Anunciar el progreso cada (segundos):")), 0, wx.ALL, 5)
        self.spin_tgdrive_progreso = wx.SpinCtrl(panel, min=1, max=60,
            initial=int(config.get("telegram_drive", "frecuencia_progreso_seg", 5)),
            name=_("Frecuencia de anuncio de progreso de Telegram Drive"))
        sizer.Add(self.spin_tgdrive_progreso, 0, wx.LEFT | wx.BOTTOM, 10)

        panel.SetSizer(sizer)
        return panel
