# -*- coding: utf-8 -*-
"""Diálogo de preferencias para TelegramAccess: ensamblador de los mixins de panel por sección.
Organizado en árbol accesible a la izquierda y panel de opciones a la derecha.
"""
import builtins
import app.core.i18n
import wx
import logging
from app.core.config_manager import config
from app.core.event_bus import event_bus
from .prefs_general import _PrefGeneralMixin
from .prefs_accesibilidad import _PrefAccMixin
from .prefs_telegram import _PrefTelegramMixin
from .prefs_avanzado import _PrefAvanzadoMixin

log = logging.getLogger(__name__)


class PreferencesDialog(_PrefGeneralMixin, _PrefAccMixin, _PrefTelegramMixin, _PrefAvanzadoMixin, wx.Dialog):
    """Ventana de configuración accesible organizada en un árbol de secciones y
    subsecciones a la izquierda y el panel de opciones correspondiente a la derecha."""

    def __init__(self, parent):
        super().__init__(
            parent,
            title=_("Preferencias de la aplicación"),
            size=(680, 560),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            name=_("Diálogo de preferencias")
        )
        self._init_ui()
        self.CenterOnParent()

    def _init_ui(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Navegación por árbol a la izquierda y contenido a la derecha
        cont = wx.BoxSizer(wx.HORIZONTAL)
        self.tree_cfg = wx.TreeCtrl(
            self,
            style=wx.TR_HAS_BUTTONS | wx.TR_HIDE_ROOT | wx.TR_LINES_AT_ROOT | wx.TR_SINGLE | wx.TR_FULL_ROW_HIGHLIGHT,
            size=(230, -1), name=_("Secciones de configuración")
        )
        self.book = wx.Simplebook(self, name=_("Contenido de la sección"))

        spec = [
            (0, _("General"), self._panel_general_root),
            (1, _("Ventana y bandeja"), self._panel_general_ventana),
            (1, _("Actualización automática"), self._panel_general_actualizacion),
            (1, _("Presentación"), self._panel_general_presentacion),
            (0, _("Accesibilidad"), self._panel_acc_root),
            (1, _("Avisos de multimedia"), self._panel_acc_multimedia),
            (1, _("Presentación del texto"), self._panel_acc_texto),
            (1, _("Navegación por columnas"), self._panel_acc_columnas),
            (0, _("Telegram"), self._panel_telegram_root),
            (1, _("Telegram Drive (nube personal)"), self._panel_telegram_drive),
            (0, _("Sonidos"), self._crear_panel_sounds),
            (1, _("Micrófono"), self._panel_microfono),
            (0, _("Traducción"), self._crear_panel_translation),
            (0, _("Proxy"), self._crear_panel_proxy),
        ]

        raiz = self.tree_cfg.AddRoot("root")
        seccion_actual = None
        primer_item = None
        for nivel, etiqueta, builder in spec:
            panel = builder(self.book)
            idx = self.book.GetPageCount()
            self.book.AddPage(panel, etiqueta)
            if nivel == 0:
                seccion_actual = self.tree_cfg.AppendItem(raiz, etiqueta, data=idx)
                if primer_item is None:
                    primer_item = seccion_actual
            else:
                self.tree_cfg.AppendItem(seccion_actual, etiqueta, data=idx)

        self.tree_cfg.ExpandAll()
        if primer_item:
            self.tree_cfg.SelectItem(primer_item)
            self.tree_cfg.SetFocus()

        self.tree_cfg.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_tree_sel)

        cont.Add(self.tree_cfg, 0, wx.EXPAND | wx.ALL, 5)
        cont.Add(self.book, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(cont, 1, wx.EXPAND | wx.ALL, 5)

        # Botonera inferior: Guardar y Cancelar
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_guardar = wx.Button(self, wx.ID_OK, label=_("&Guardar"), name=_("Guardar cambios"))
        self.btn_guardar.SetDefault()
        self.btn_guardar.Bind(wx.EVT_BUTTON, self._on_save)
        btn_sizer.Add(self.btn_guardar, 0, wx.ALL, 5)

        self.btn_cancelar = wx.Button(self, wx.ID_CANCEL, label=_("&Cancelar"), name=_("Cancelar cambios"))
        btn_sizer.Add(self.btn_cancelar, 0, wx.ALL, 5)

        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(sizer)

    def _on_tree_sel(self, event):
        try:
            if not self or not hasattr(self, "tree_cfg") or not self.tree_cfg:
                return
            item = event.GetItem()
            if item.IsOk():
                idx = self.tree_cfg.GetItemData(item)
                if idx is not None and 0 <= idx < self.book.GetPageCount():
                    self.book.ChangeSelection(idx)
                    # Mantener el foco en el árbol para que el usuario pueda seguir
                    # navegando con las flechas entre categorías sin perder su posición.
                    # El usuario pasará a las opciones de la página pulsando Tab.
                    if bool(self.tree_cfg):
                        self.tree_cfg.SetFocus()
                    wx.CallAfter(self._garantizar_foco_arbol)
        except Exception:
            pass

    def _garantizar_foco_arbol(self):
        try:
            if hasattr(self, "tree_cfg") and self.tree_cfg and bool(self.tree_cfg):
                self.tree_cfg.SetFocus()
        except Exception:
            pass

    def _on_save(self, event):
        """Valida, guarda los cambios en config_manager y cierra."""
        config.begin_batch()
        try:
            self._recoger_preferencias_en_lote()
        finally:
            config.end_batch()
        log.info("Nuevas preferencias guardadas por el usuario.")

        event_bus.emit("sound_trigger", "operation_done")
        if self.IsModal():
            self.EndModal(wx.ID_OK)
        else:
            self.Close()

    def _recoger_preferencias_en_lote(self):
        """Lee todos los controles y los vuelca a la configuración."""
        # General
        if hasattr(self, "choice_lang"):
            try:
                config.set("general", "language", self._lang_codigos[self.choice_lang.GetSelection()])
            except Exception:
                config.set("general", "language", "es")
        if hasattr(self, "cb_confirm_exit"):
            config.set("general", "confirm_exit", self.cb_confirm_exit.GetValue())
        if hasattr(self, "cb_ready_sound"):
            config.set("general", "ready_sound", self.cb_ready_sound.GetValue())
        if hasattr(self, "cb_menus_cat"):
            config.set("general", "menus_categorizados", self.cb_menus_cat.GetValue())
        if hasattr(self, "choice_log_level"):
            config.set("general", "log_level", self.choice_log_level.GetStringSelection())
        if hasattr(self, "choice_spell_lang"):
            try:
                config.set("general", "spell_language", self._spell_langs[self.choice_spell_lang.GetSelection()][0])
            except Exception:
                pass

        # Ventana y bandeja
        if hasattr(self, "cb_minimize_tray"):
            config.set("general", "minimize_to_tray", self.cb_minimize_tray.GetValue())
        if hasattr(self, "cb_start_minimized"):
            config.set("general", "start_minimized", self.cb_start_minimized.GetValue())
        if hasattr(self, "cb_run_at_startup"):
            quiere = self.cb_run_at_startup.GetValue()
            from app.core import windows_startup
            if quiere != windows_startup.esta_activado():
                windows_startup.aplicar(quiere)
            config.set("general", "run_at_startup", quiere)

        # Actualización
        if hasattr(self, "cb_auto_update"):
            config.set("general", "auto_update_enabled", self.cb_auto_update.GetValue())
        if hasattr(self, "cb_check_updates"):
            config.set("general", "check_updates_on_start", self.cb_check_updates.GetValue())

        # Presentación
        if hasattr(self, "cb_relative_times"):
            config.set("general", "relative_times", self.cb_relative_times.GetValue())
        if hasattr(self, "choice_order"):
            config.set("general", "newest_first", (self.choice_order.GetSelection() == 0))

        # Accesibilidad - Principal
        if hasattr(self, "cb_screen_reader"):
            config.set("accessibility", "screen_reader_mode", self.cb_screen_reader.GetValue())
        if hasattr(self, "cb_sounds"):
            config.set("accessibility", "enable_sounds", self.cb_sounds.GetValue())
        if hasattr(self, "cb_speech"):
            config.set("accessibility", "speech_announcements", self.cb_speech.GetValue())
        if hasattr(self, "cb_contador_vivo"):
            config.set("accessibility", "contador_en_vivo", self.cb_contador_vivo.GetValue())
        if hasattr(self, "choice_modo_avisos"):
            sel = self.choice_modo_avisos.GetSelection()
            if 0 <= sel < len(self._modos_avisos):
                config.set("accessibility", "modo_avisos", self._modos_avisos[sel])
        if hasattr(self, "cb_toast"):
            config.set("accessibility", "toast_windows", self.cb_toast.GetValue())
        if hasattr(self, "cb_invisible"):
            config.set("accessibility", "interfaz_invisible", self.cb_invisible.GetValue())
        if hasattr(self, "cb_invisible_solo_oculta"):
            config.set("accessibility", "invisible_solo_oculta", self.cb_invisible_solo_oculta.GetValue())
        if hasattr(self, "cb_invisible_posicion"):
            config.set("accessibility", "invisible_anunciar_posicion", self.cb_invisible_posicion.GetValue())
        if hasattr(self, "cb_braille"):
            config.set("accessibility", "braille_announcements", self.cb_braille.GetValue())
        if hasattr(self, "spin_speech_delay"):
            config.set("accessibility", "speech_delay_ms", int(self.spin_speech_delay.GetValue()))

        # Accesibilidad - Avisos de multimedia
        if hasattr(self, "cb_indicate_image"):
            config.set("accessibility", "indicate_image", self.cb_indicate_image.GetValue())
        if hasattr(self, "cb_indicate_audio"):
            config.set("accessibility", "indicate_audio", self.cb_indicate_audio.GetValue())
        if hasattr(self, "cb_sonido_dm_buffer"):
            config.set("accessibility", "direct_sound_in_dm_buffer", self.cb_sonido_dm_buffer.GetValue())
        if hasattr(self, "cb_auto_read"):
            config.set("accessibility", "auto_read_new", self.cb_auto_read.GetValue())

        # Accesibilidad - Presentación del texto
        if hasattr(self, "cb_show_usernames"):
            config.set("accessibility", "show_screen_names", self.cb_show_usernames.GetValue())
        if hasattr(self, "cb_hide_emojis"):
            config.set("accessibility", "hide_emojis", self.cb_hide_emojis.GetValue())
        if hasattr(self, "cb_hide_emojis_names"):
            config.set("accessibility", "hide_emojis_names", self.cb_hide_emojis_names.GetValue())
        if hasattr(self, "cb_expand_cw"):
            config.set("accessibility", "expand_cw", self.cb_expand_cw.GetValue())

        # Accesibilidad - Navegación por columnas
        if hasattr(self, "cb_colnav_row"):
            config.set("accessibility", "colnav_row_num", self.cb_colnav_row.GetValue())
        if hasattr(self, "cb_colnav_header"):
            config.set("accessibility", "colnav_col_header", self.cb_colnav_header.GetValue())
        if hasattr(self, "cb_colnav_value"):
            config.set("accessibility", "colnav_cell_value", self.cb_colnav_value.GetValue())

        # Telegram
        if hasattr(self, "txt_telegram_interval"):
            try:
                val = max(10, int(self.txt_telegram_interval.GetValue().strip() or "60"))
                config.set("telegram", "update_interval", val)
            except Exception:
                pass
        if hasattr(self, "txt_tg_api_id") and hasattr(self, "txt_tg_api_hash"):
            api_id = self.txt_tg_api_id.GetValue().strip()
            api_hash = self.txt_tg_api_hash.GetValue().strip()
            from app.services.telegram.telegram_service import telegram_service
            if api_id and api_hash:
                telegram_service.set_api_credentials(api_id, api_hash)
        if hasattr(self, "txt_tg_downloads"):
            config.set("telegram", "download_dir", self.txt_tg_downloads.GetValue().strip())
        if hasattr(self, "cb_tg_subdirs"):
            config.set("telegram", "download_subdirs", self.cb_tg_subdirs.GetValue())
        if hasattr(self, "cb_tg_announce"):
            config.set("telegram", "announce_new", self.cb_tg_announce.GetValue())
        if hasattr(self, "cb_tg_autoplay_voice"):
            config.set("telegram", "autoplay_voice", self.cb_tg_autoplay_voice.GetValue())
        if hasattr(self, "cb_tg_mark_read"):
            config.set("telegram", "mark_read_on_focus", self.cb_tg_mark_read.GetValue())
        if hasattr(self, "cb_tg_unread_marker"):
            config.set("telegram", "show_unread_marker", self.cb_tg_unread_marker.GetValue())
        if hasattr(self, "cb_tg_unread_divider"):
            config.set("telegram", "show_unread_divider", self.cb_tg_unread_divider.GetValue())
        if hasattr(self, "cb_tg_sync_todo"):
            config.set("telegram", "sincronizar_todo_al_abrir", self.cb_tg_sync_todo.GetValue())
        if hasattr(self, "spin_max_tg_msgs"):
            config.set("telegram", "max_messages_per_chat", int(self.spin_max_tg_msgs.GetValue()))
        if hasattr(self, "cb_tg_buttons"):
            config.set("telegram", "show_action_buttons", self.cb_tg_buttons.GetValue())

        # Telegram Drive
        if hasattr(self, "txt_tgdrive_downloads"):
            config.set("telegram_drive", "carpeta_descargas", self.txt_tgdrive_downloads.GetValue().strip())
        if hasattr(self, "spin_tgdrive_simult"):
            config.set("telegram_drive", "max_simultaneas", int(self.spin_tgdrive_simult.GetValue()))
        if hasattr(self, "choice_tgdrive_conflicto") and hasattr(self, "_tgdrive_conf_valores"):
            sel = self.choice_tgdrive_conflicto.GetSelection()
            if 0 <= sel < len(self._tgdrive_conf_valores):
                config.set("telegram_drive", "politica_conflicto", self._tgdrive_conf_valores[sel])
        if hasattr(self, "spin_tgdrive_papelera"):
            config.set("telegram_drive", "retencion_papelera_dias", int(self.spin_tgdrive_papelera.GetValue()))
        if hasattr(self, "cb_tgdrive_confirmar"):
            config.set("telegram_drive", "confirmar_borrado", self.cb_tgdrive_confirmar.GetValue())
        if hasattr(self, "cb_tgdrive_limpiar"):
            config.set("telegram_drive", "limpiar_temporales", self.cb_tgdrive_limpiar.GetValue())
        if hasattr(self, "spin_tgdrive_progreso"):
            config.set("telegram_drive", "frecuencia_progreso_seg", int(self.spin_tgdrive_progreso.GetValue()))

        # Sonidos
        if hasattr(self, "slider_volume"):
            config.set("audio", "volume", float(self.slider_volume.GetValue() / 100.0))
        if hasattr(self, "cb_mute"):
            config.set("audio", "mute", self.cb_mute.GetValue())
        if hasattr(self, "choice_sound_pack") and hasattr(self, "_paquetes_sonido"):
            sel = self.choice_sound_pack.GetSelection()
            if 0 <= sel < len(self._paquetes_sonido):
                config.set("audio", "sound_pack", self._paquetes_sonido[sel])
        if hasattr(self, "choice_output_device") and hasattr(self, "_dispositivos_salida"):
            sel_dev = self.choice_output_device.GetSelection()
            if sel_dev <= 0 or sel_dev > len(self._dispositivos_salida):
                config.set("audio", "output_device", "")
            else:
                config.set("audio", "output_device", self._dispositivos_salida[sel_dev - 1])
        if hasattr(self, "clb_sounds") and hasattr(self, "sound_event_keys"):
            disabled = []
            for idx, key in enumerate(self.sound_event_keys):
                if not self.clb_sounds.IsChecked(idx):
                    disabled.append(key)
            config.set("audio", "disabled_events", disabled)

        # Micrófono
        if hasattr(self, "choice_mic") and hasattr(self, "slider_mic_vol"):
            config.set("audio", "mic_device", self._mic_seleccionado())
            config.set("audio", "mic_volume", self.slider_mic_vol.GetValue() / 100.0)

        # Traducción
        if hasattr(self, "choice_trad_prov") and getattr(self, "_trad_provs", None):
            sel = self.choice_trad_prov.GetSelection()
            if 0 <= sel < len(self._trad_provs):
                config.set("translation", "provider", self._trad_provs[sel][0])
        if hasattr(self, "choice_target_lang"):
            config.set("translation", "default_target", self.choice_target_lang.GetStringSelection())
        if hasattr(self, "cb_copy_translation"):
            config.set("translation", "copy_on_translate", self.cb_copy_translation.GetValue())
        if hasattr(self, "cb_save_translation_history"):
            config.set("translation", "save_history", self.cb_save_translation_history.GetValue())

        # Proxy
        if hasattr(self, "cb_proxy_enabled"):
            config.set("proxy", "enabled", self.cb_proxy_enabled.GetValue())
        if hasattr(self, "choice_proxy_type") and hasattr(self, "_proxy_types"):
            sel = self.choice_proxy_type.GetSelection()
            if 0 <= sel < len(self._proxy_types):
                config.set("proxy", "type", self._proxy_types[sel])
        if hasattr(self, "txt_proxy_server"):
            config.set("proxy", "server", self.txt_proxy_server.GetValue().strip())
        if hasattr(self, "spin_proxy_port"):
            config.set("proxy", "port", int(self.spin_proxy_port.GetValue()))
        if hasattr(self, "txt_proxy_user"):
            config.set("proxy", "user", self.txt_proxy_user.GetValue().strip())
        if hasattr(self, "txt_proxy_pass"):
            config.set("proxy", "password", self.txt_proxy_pass.GetValue())
        try:
            from app.core.net import aplicar_configuracion_proxy
            aplicar_configuracion_proxy()
        except Exception:
            pass
