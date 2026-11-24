# -*- coding: utf-8 -*-
"""Diálogos accesibles para llamadas de voz y videollamadas de Telegram.

Incluye:
- TelegramCallDialog: ventana de llamada activa con temporizador, silencio, cámara y colgar.
- TelegramIncomingCallDialog: aviso de llamada entrante con timbrado y opciones de respuesta.
- TelegramDispositivosLlamadaDialog: selector de micrófono y cámara.
"""
import app.core.i18n
import wx
import os
import logging
from typing import Optional

from app.core.speech import speak, notificar
from app.core.event_bus import event_bus
from app.core.task_manager import task_manager
from app.services.telegram.telegram_service import telegram_service

log = logging.getLogger(__name__)


class TelegramDispositivosLlamadaDialog(wx.Dialog):
    """Diálogo accesible para seleccionar el micrófono y la cámara activa."""

    def __init__(self, parent, mic_idx: Optional[int] = 0, cam_idx: Optional[int] = 0):
        super().__init__(
            parent,
            title=_("Configuración de dispositivos de llamada"),
            size=(480, 260),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            name=_("Configuración de dispositivos de audio y vídeo")
        )
        self.CentreOnParent()

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Microfono
        lbl_mic = wx.StaticText(panel, label=_("&Micrófono de entrada:"))
        vbox.Add(lbl_mic, 0, wx.ALL, 6)

        self.mics = telegram_service.obtener_dispositivos_audio()
        opciones_mic = [m["title"] for m in self.mics] or [_("Predeterminado del sistema")]
        self.cb_mic = wx.Choice(panel, choices=opciones_mic, name=_("Seleccionar micrófono"))
        if self.mics and mic_idx is not None and 0 <= mic_idx < len(self.mics):
            self.cb_mic.SetSelection(mic_idx)
        else:
            self.cb_mic.SetSelection(0)
        vbox.Add(self.cb_mic, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        # Camara
        lbl_cam = wx.StaticText(panel, label=_("&Cámara de vídeo:"))
        vbox.Add(lbl_cam, 0, wx.ALL, 6)

        self.cams = telegram_service.obtener_dispositivos_camara()
        opciones_cam = [c["title"] for c in self.cams] or [_("Sin cámara detectada")]
        self.cb_cam = wx.Choice(panel, choices=opciones_cam, name=_("Seleccionar cámara"))
        if self.cams and cam_idx is not None and 0 <= cam_idx < len(self.cams):
            self.cb_cam.SetSelection(cam_idx)
        else:
            self.cb_cam.SetSelection(0)
        vbox.Add(self.cb_cam, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        # Botones
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_ok = wx.Button(panel, wx.ID_OK, _("&Aceptar"))
        btn_cancel = wx.Button(panel, wx.ID_CANCEL, _("&Cancelar"))
        btn_ok.SetDefault()
        btn_sizer.Add(btn_ok, 0, wx.ALL, 6)
        btn_sizer.Add(btn_cancel, 0, wx.ALL, 6)
        vbox.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        panel.SetSizer(vbox)
        vbox.Fit(self)

    def get_selected_indices(self):
        m_sel = self.cb_mic.GetSelection()
        c_sel = self.cb_cam.GetSelection()
        m_idx = m_sel if (self.mics and 0 <= m_sel < len(self.mics)) else 0
        c_idx = c_sel if (self.cams and 0 <= c_sel < len(self.cams)) else 0
        return m_idx, c_idx


class TelegramCallDialog(wx.Dialog):
    """Ventana accesible para gestionar una llamada de voz o videollamada activa."""

    def __init__(self, parent, account_id: int, chat_id: int, peer_name: str,
                 con_video: bool = False, es_entrante: bool = False):
        tipo_str = _("Videollamada") if con_video else _("Llamada")
        super().__init__(
            parent,
            title=f"{tipo_str}: {peer_name}",
            size=(620, 390),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            name=f"{tipo_str} con {peer_name}"
        )
        self.CentreOnParent()

        self.account_id = account_id
        self.chat_id = chat_id
        self.peer_name = peer_name
        self.con_video = con_video
        self.es_entrante = es_entrante

        self.mic_idx = 0
        self.cam_idx = 0
        self.silenciado = False
        self.grabando = False
        self.ruta_grabacion = None
        self.duracion_segundos = 0
        self._conectado = False
        self._colgado = False

        self._crear_ui()
        self._iniciar_temporizador()

        # Suscribir evento de finalización
        event_bus.subscribe("telegram_call_ended", self._on_call_ended_event)

        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

        # Iniciar llamada o responder en segundo plano
        self._conectar_en_segundo_plano()

    def _crear_ui(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Título / Interlocutor
        txt_tipo = _("Videollamada con {0}") if self.con_video else _("Llamada de voz con {0}")
        self.lbl_titulo = wx.StaticText(panel, label=txt_tipo.format(self.peer_name))
        font_titulo = self.lbl_titulo.GetFont()
        font_titulo.SetPointSize(font_titulo.GetPointSize() + 2)
        font_titulo.SetWeight(wx.FONTWEIGHT_BOLD)
        self.lbl_titulo.SetFont(font_titulo)
        vbox.Add(self.lbl_titulo, 0, wx.ALL, 10)

        # Estado de la conexión
        self.lbl_estado = wx.StaticText(panel, label=_("Conectando llamada..."), name=_("Estado de la llamada"))
        vbox.Add(self.lbl_estado, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Duración
        self.lbl_duracion = wx.StaticText(panel, label=_("Duración: 00:00"), name=_("Duración de la llamada"))
        font_dur = self.lbl_duracion.GetFont()
        font_dur.SetWeight(wx.FONTWEIGHT_BOLD)
        self.lbl_duracion.SetFont(font_dur)
        vbox.Add(self.lbl_duracion, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Dispositivos activos
        self.lbl_dispositivos = wx.StaticText(
            panel,
            label=_("Micrófono: Iniciando... | Vídeo: {0}").format(_("Activado") if self.con_video else _("Desactivado")),
            name=_("Dispositivos en uso")
        )
        vbox.Add(self.lbl_dispositivos, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        vbox.AddStretchSpacer(1)

        # Barra de botones de control
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Botón Silenciar / Reactivar micro (Alt+S)
        self.btn_mute = wx.Button(panel, label=_("&Silenciar micrófono (Alt+S)"), name=_("Silenciar micrófono"))
        self.btn_mute.Bind(wx.EVT_BUTTON, self._on_toggle_mute)
        self.btn_mute.Disable()
        btn_sizer.Add(self.btn_mute, 0, wx.ALL, 5)

        # Botón Alternar cámara (Alt+C)
        lbl_cam_btn = _("&Apagar cámara (Alt+C)") if self.con_video else _("&Encender cámara (Alt+C)")
        self.btn_cam = wx.Button(panel, label=lbl_cam_btn, name=_("Alternar cámara de vídeo"))
        self.btn_cam.Bind(wx.EVT_BUTTON, self._on_toggle_cam)
        self.btn_cam.Disable()
        btn_sizer.Add(self.btn_cam, 0, wx.ALL, 5)

        # Botón Grabar llamada (Alt+G)
        self.btn_grabar = wx.Button(panel, label=_("&Grabar llamada (Alt+G)"), name=_("Grabar conversación de la llamada"))
        self.btn_grabar.Bind(wx.EVT_BUTTON, self._on_toggle_grabar)
        self.btn_grabar.Disable()
        btn_sizer.Add(self.btn_grabar, 0, wx.ALL, 5)

        # Botón Carpeta de grabaciones
        self.btn_carpeta = wx.Button(panel, label=_("&Grabaciones..."), name=_("Abrir carpeta de grabaciones"))
        self.btn_carpeta.Bind(wx.EVT_BUTTON, self._on_abrir_carpeta_grabaciones)
        btn_sizer.Add(self.btn_carpeta, 0, wx.ALL, 5)

        # Botón Seleccionar dispositivos (Alt+D)
        self.btn_dispositivos = wx.Button(panel, label=_("&Dispositivos... (Alt+D)"), name=_("Configurar dispositivos"))
        self.btn_dispositivos.Bind(wx.EVT_BUTTON, self._on_config_dispositivos)
        btn_sizer.Add(self.btn_dispositivos, 0, wx.ALL, 5)

        # Botón Colgar (Alt+X / Escape)
        self.btn_colgar = wx.Button(panel, label=_("&Colgar llamada (Escape)"), name=_("Colgar y finalizar llamada"))
        self.btn_colgar.Bind(wx.EVT_BUTTON, self._on_colgar)
        self.btn_colgar.SetDefault()
        btn_sizer.Add(self.btn_colgar, 0, wx.ALL, 5)

        vbox.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        panel.SetSizer(vbox)
        self.vbox = vbox

    def _iniciar_temporizador(self):
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_timer, self.timer)

    def _on_timer(self, event):
        if not self._conectado:
            return
        self.duracion_segundos += 1
        mins = self.duracion_segundos // 60
        segs = self.duracion_segundos % 60
        self.lbl_duracion.SetLabel(_("Duración: {0:02d}:{1:02d}").format(mins, segs))

    def _conectar_en_segundo_plano(self):
        speak(_("Conectando llamada..."), interrupt=True)

        def _bg(ctx):
            if self.es_entrante:
                return telegram_service.responder_llamada(
                    self.account_id, self.chat_id, con_video=self.con_video,
                    mic_idx=self.mic_idx, cam_idx=self.cam_idx
                )
            else:
                return telegram_service.iniciar_llamada(
                    self.account_id, self.chat_id, con_video=self.con_video,
                    mic_idx=self.mic_idx, cam_idx=self.cam_idx
                )

        def _finish(res, err):
            if self._colgado:
                return
            if err:
                log.error(f"Error conectando llamada: {err}")
                self.lbl_estado.SetLabel(_("Error al conectar: {0}").format(err))
                speak(_("No se pudo conectar la llamada: {0}").format(err), interrupt=True)
                notificar(_("Error al conectar llamada: {0}").format(err))
                self.btn_colgar.SetLabel(_("&Cerrar"))
                return

            self._conectado = True
            self.timer.Start(1000)
            self.btn_mute.Enable()
            self.btn_cam.Enable()
            self.btn_grabar.Enable()

            self.lbl_estado.SetLabel(_("En llamada"))
            mic_nombre = res.get("mic", _("Predeterminado")) if isinstance(res, dict) else _("Predeterminado")
            cam_str = _("Activada") if self.con_video else _("Desactivada")
            self.lbl_dispositivos.SetLabel(_("Micrófono: {0} | Vídeo: {1}").format(mic_nombre, cam_str))

            speak(_("Llamada conectada. Duración iniciada."), interrupt=True)
            self.btn_mute.SetFocus()

        task_manager.start_task(_bg, callback=_finish, pass_context=True)

    def _on_toggle_mute(self, event):
        if not self._conectado:
            return
        nuevo_silencio = not self.silenciado

        def _bg(ctx):
            return telegram_service.silenciar_microfono(self.account_id, self.chat_id, silenciar=nuevo_silencio)

        def _finish(res, err):
            if err:
                notificar(_("Error al silenciar micrófono: {0}").format(err))
                return
            self.silenciado = nuevo_silencio
            if self.silenciado:
                self.btn_mute.SetLabel(_("&Reactivar micrófono (Alt+S)"))
                self.lbl_estado.SetLabel(_("En llamada (Micrófono silenciado)"))
                speak(_("Micrófono silenciado."), interrupt=True)
            else:
                self.btn_mute.SetLabel(_("&Silenciar micrófono (Alt+S)"))
                self.lbl_estado.SetLabel(_("En llamada"))
                speak(_("Micrófono activado."), interrupt=True)

        task_manager.start_task(_bg, callback=_finish, pass_context=True)

    def _on_toggle_cam(self, event):
        if not self._conectado:
            return
        nueva_cam = not self.con_video

        def _bg(ctx):
            return telegram_service.alternar_camara(
                self.account_id, self.chat_id, encender=nueva_cam,
                mic_idx=self.mic_idx, cam_idx=self.cam_idx
            )

        def _finish(res, err):
            if err:
                notificar(_("Error al cambiar cámara: {0}").format(err))
                return
            self.con_video = nueva_cam
            if self.con_video:
                self.btn_cam.SetLabel(_("&Apagar cámara (Alt+C)"))
                cam_str = _("Activada")
                speak(_("Cámara encendida."), interrupt=True)
            else:
                self.btn_cam.SetLabel(_("&Encender cámara (Alt+C)"))
                cam_str = _("Desactivada")
                speak(_("Cámara apagada."), interrupt=True)
            mics = telegram_service.obtener_dispositivos_audio()
            mic_nombre = mics[self.mic_idx]["title"] if (mics and 0 <= self.mic_idx < len(mics)) else _("Predeterminado")
            self.lbl_dispositivos.SetLabel(_("Micrófono: {0} | Vídeo: {1}").format(mic_nombre, cam_str))

        task_manager.start_task(_bg, callback=_finish, pass_context=True)

    def _on_config_dispositivos(self, event):
        dlg = TelegramDispositivosLlamadaDialog(self, mic_idx=self.mic_idx, cam_idx=self.cam_idx)
        if dlg.ShowModal() == wx.ID_OK:
            m_idx, c_idx = dlg.get_selected_indices()
            self.mic_idx = m_idx
            self.cam_idx = c_idx
            if self._conectado:
                speak(_("Cambiando dispositivos..."), interrupt=True)
                def _bg(ctx):
                    return telegram_service.alternar_camara(
                        self.account_id, self.chat_id, encender=self.con_video,
                        mic_idx=self.mic_idx, cam_idx=self.cam_idx
                    )
                def _finish(res, err):
                    if err:
                        notificar(_("Error al aplicar dispositivos: {0}").format(err))
                    else:
                        speak(_("Dispositivos aplicados."), interrupt=True)
                task_manager.start_task(_bg, callback=_finish, pass_context=True)
        dlg.Destroy()

    def _on_toggle_grabar(self, event):
        if not self._conectado:
            return
        if not self.grabando:
            self.btn_grabar.Disable()
            speak(_("Iniciando grabación de llamada..."), interrupt=True)
            def _bg(ctx):
                return telegram_service.iniciar_grabacion_llamada(
                    self.account_id, self.chat_id, self.peer_name
                )
            def _finish(res, err):
                self.btn_grabar.Enable()
                if err:
                    notificar(_("Error al iniciar grabación: {0}").format(err))
                    speak(_("No se pudo iniciar la grabación: {0}").format(err), interrupt=True)
                    return
                self.grabando = True
                self.ruta_grabacion = res
                self.btn_grabar.SetLabel(_("&Detener grabación (Alt+G)"))
                self.lbl_estado.SetLabel(_("En llamada (Grabando conversación...)"))
                speak(_("Grabación iniciada."), interrupt=True)
                notificar(_("Grabando llamada en: {0}").format(os.path.basename(res)))
            task_manager.start_task(_bg, callback=_finish, pass_context=True)
        else:
            self.btn_grabar.Disable()
            speak(_("Deteniendo grabación..."), interrupt=True)
            def _bg(ctx):
                return telegram_service.detener_grabacion_llamada(self.account_id, self.chat_id)
            def _finish(res, err):
                self.btn_grabar.Enable()
                self.grabando = False
                self.btn_grabar.SetLabel(_("&Grabar llamada (Alt+G)"))
                self.lbl_estado.SetLabel(_("En llamada"))
                if err:
                    notificar(_("Error al detener grabación: {0}").format(err))
                else:
                    nom = os.path.basename(self.ruta_grabacion or '')
                    speak(_("Grabación guardada: {0}").format(nom), interrupt=True)
                    notificar(_("Grabación guardada: {0}").format(nom))
            task_manager.start_task(_bg, callback=_finish, pass_context=True)

    def _on_abrir_carpeta_grabaciones(self, event):
        carpeta = telegram_service.obtener_carpeta_grabaciones()
        try:
            os.startfile(carpeta)
            speak(_("Abriendo carpeta de grabaciones."), interrupt=True)
        except Exception as e:
            notificar(_("Error al abrir carpeta: {0}").format(e))

    def _on_colgar(self, event):
        if self._colgado:
            self.Destroy()
            return
        self._colgado = True
        if hasattr(self, "timer") and self.timer.IsRunning():
            self.timer.Stop()

        if self.grabando:
            try:
                telegram_service.detener_grabacion_llamada(self.account_id, self.chat_id)
            except Exception:
                pass
            self.grabando = False

        speak(_("Colgando llamada..."), interrupt=True)

        def _bg(ctx):
            telegram_service.colgar_llamada(self.account_id, self.chat_id)
            return True

        def _finish(res, err):
            if self.ruta_grabacion:
                nom = os.path.basename(self.ruta_grabacion)
                speak(_("Llamada finalizada. Grabación guardada: {0}").format(nom), interrupt=True)
            else:
                speak(_("Llamada finalizada."), interrupt=True)
            self._limpiar_y_cerrar()

        task_manager.start_task(_bg, callback=_finish, pass_context=True)

    def _on_call_ended_event(self, account_id: int, chat_id: int, **kwargs):
        if account_id == self.account_id and chat_id == self.chat_id:
            wx.CallAfter(self._cerrar_por_evento_remoto)

    def _cerrar_por_evento_remoto(self):
        if self._colgado:
            return
        self._colgado = True
        if hasattr(self, "timer") and self.timer.IsRunning():
            self.timer.Stop()
        if self.grabando:
            try:
                telegram_service.detener_grabacion_llamada(self.account_id, self.chat_id)
            except Exception:
                pass
            self.grabando = False
        self.lbl_estado.SetLabel(_("Llamada terminada por el interlocutor"))
        speak(_("La llamada ha terminado."), interrupt=True)
        self._limpiar_y_cerrar()

    def _limpiar_y_cerrar(self):
        event_bus.unsubscribe("telegram_call_ended", self._on_call_ended_event)
        if hasattr(self, "timer") and self.timer.IsRunning():
            self.timer.Stop()
        if self.IsModal():
            self.EndModal(wx.ID_OK)
        else:
            self.Destroy()

    def _on_char_hook(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_ESCAPE:
            self._on_colgar(None)
            return
        elif event.AltDown() and key in (ord('G'), ord('g')):
            self._on_toggle_grabar(None)
            return
        elif event.AltDown() and key in (ord('S'), ord('s'), ord('M'), ord('m')):
            self._on_toggle_mute(None)
            return
        elif event.AltDown() and key in (ord('C'), ord('c')):
            self._on_toggle_cam(None)
            return
        elif event.AltDown() and key in (ord('D'), ord('d')):
            self._on_config_dispositivos(None)
            return
        event.Skip()

    def _on_close(self, event):
        self._on_colgar(None)


class TelegramIncomingCallDialog(wx.Dialog):
    """Diálogo accesible para alertar de una llamada entrante."""

    def __init__(self, parent, account_id: int, chat_id: int, peer_name: str):
        super().__init__(
            parent,
            title=_("Llamada entrante: {0}").format(peer_name),
            size=(480, 220),
            style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP,
            name=_("Llamada entrante de Telegram")
        )
        self.CentreOnScreen()

        self.account_id = account_id
        self.chat_id = chat_id
        self.peer_name = peer_name
        self._respondida = False

        self._crear_ui()

        # Anunciar y timbrar
        speak(_("Llamada entrante de {0}. Pulse Enter para responder con audio o Escape para rechazar.").format(peer_name), interrupt=True)
        event_bus.emit("sound_trigger", "notification")

        # Temporizador de timbre continuo cada 3.5 segundos
        self.timer_timbre = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_timbre, self.timer_timbre)
        self.timer_timbre.Start(3500)

        # Escuchar si cuelga antes de responder
        event_bus.subscribe("telegram_call_ended", self._on_remote_ended)

        self.Bind(wx.EVT_CLOSE, self._on_rechazar)
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

    def _crear_ui(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        lbl_aviso = wx.StaticText(panel, label=_("Llamada entrante de:\n{0}").format(self.peer_name))
        font = lbl_aviso.GetFont()
        font.SetPointSize(font.GetPointSize() + 2)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        lbl_aviso.SetFont(font)
        vbox.Add(lbl_aviso, 0, wx.ALL, 15)

        lbl_instruccion = wx.StaticText(
            panel,
            label=_("Elija una opción para responder o rechace la llamada.")
        )
        vbox.Add(lbl_instruccion, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        vbox.AddStretchSpacer(1)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Responder con audio (Default / Enter)
        self.btn_audio = wx.Button(panel, label=_("&Responder con audio (Enter)"), name=_("Responder con audio"))
        self.btn_audio.SetDefault()
        self.btn_audio.Bind(wx.EVT_BUTTON, self._on_responder_audio)
        btn_sizer.Add(self.btn_audio, 0, wx.ALL, 6)

        # Responder con vídeo
        self.btn_video = wx.Button(panel, label=_("Responder con &vídeo (Alt+V)"), name=_("Responder con vídeo"))
        self.btn_video.Bind(wx.EVT_BUTTON, self._on_responder_video)
        btn_sizer.Add(self.btn_video, 0, wx.ALL, 6)

        # Rechazar
        self.btn_rechazar = wx.Button(panel, label=_("Re&chazar (Escape)"), name=_("Rechazar llamada"))
        self.btn_rechazar.Bind(wx.EVT_BUTTON, self._on_rechazar)
        btn_sizer.Add(self.btn_rechazar, 0, wx.ALL, 6)

        vbox.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        panel.SetSizer(vbox)

    def _on_timbre(self, event):
        event_bus.emit("sound_trigger", "notification")

    def _detener_timbre(self):
        if hasattr(self, "timer_timbre") and self.timer_timbre.IsRunning():
            self.timer_timbre.Stop()
        event_bus.unsubscribe("telegram_call_ended", self._on_remote_ended)

    def _on_responder_audio(self, event):
        self._detener_timbre()
        self._respondida = True
        parent = self.GetParent()
        acc_id = self.account_id
        c_id = self.chat_id
        p_name = self.peer_name
        self.Destroy()

        # Abrir la ventana de llamada activa
        dlg = TelegramCallDialog(parent, acc_id, c_id, p_name, con_video=False, es_entrante=True)
        dlg.Show()

    def _on_responder_video(self, event):
        self._detener_timbre()
        self._respondida = True
        parent = self.GetParent()
        acc_id = self.account_id
        c_id = self.chat_id
        p_name = self.peer_name
        self.Destroy()

        dlg = TelegramCallDialog(parent, acc_id, c_id, p_name, con_video=True, es_entrante=True)
        dlg.Show()

    def _on_rechazar(self, event):
        self._detener_timbre()
        if not self._respondida:
            speak(_("Llamada rechazada."), interrupt=True)
            def _bg(ctx):
                telegram_service.colgar_llamada(self.account_id, self.chat_id)
                return True
            task_manager.start_task(_bg, pass_context=True)
        self.Destroy()

    def _on_remote_ended(self, account_id: int, chat_id: int, **kwargs):
        if account_id == self.account_id and chat_id == self.chat_id:
            wx.CallAfter(self._cerrar_cancelada)

    def _cerrar_cancelada(self):
        self._detener_timbre()
        speak(_("Llamada perdida de {0}.").format(self.peer_name), interrupt=True)
        self.Destroy()

    def _on_char_hook(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_ESCAPE:
            self._on_rechazar(None)
            return
        elif key == wx.WXK_RETURN:
            self._on_responder_audio(None)
            return
        event.Skip()
