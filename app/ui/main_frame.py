# -*- coding: utf-8 -*-
"""
Ventana principal de TelegramAccess.
Diseñada al 100% para el manejo ágil por teclado y lectores de pantalla (NVDA / JAWS).
"""

import logging
import json
import webbrowser
import wx
import wx.adv
from datetime import datetime

from app.core.version import APP_VERSION, APP_NAME
from app.core.config_manager import config, limite_render
from app.core.database import db
from app.core.speech import speak, notificar
from app.core.event_bus import event_bus
from app.core.task_manager import task_manager
from app.core.privacy import abrir_url
from app.core.plantillas import definicion, pulir_lectura
from .ui_helpers import formatear_tiempo_relativo, evento_sonido_media
from app.services.telegram.telegram_service import telegram_service
from app.services.media_player.player_service import player_service

from .accessible_controls import (
    AccessibleListCtrl, CustomTextEntryDialog,
    mostrar_info, mostrar_error, confirmar
)
from .shortcut_manager import shortcut_manager
from .preferences_dialog import PreferencesDialog
from .shortcuts_editor import ShortcutsEditorDialog
from .sound_test_dialog import SoundTestDialog
from .tgdrive_window import TelegramDriveFrame
from .telegram_views import (
    TelegramLoginDialog, TelegramConversationDialog,
    TelegramProfileDialog, TelegramSessionsDialog,
    TelegramCarpetasDialog, TelegramHistoriasDialog,
    TelegramChatsSugeridosDialog, TelegramPrivacidadGlobalDialog,
    TelegramAjustesCuentaDialog, TelegramMediosChatDialog,
    TelegramAdminDialog, TelegramPropiedadesDialog
)

log = logging.getLogger(__name__)


class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title=f"{APP_NAME} {APP_VERSION}", size=(980, 680))
        self.Center()

        self.active_account_id = None
        self.active_timeline_type = "all"
        self.lista_items_db_ids = []
        self._tb_icon = None

        self._init_ui()
        self._crear_menus()
        self._aplicar_atajos()
        self._suscribir_eventos()
        self._iniciar_servicios()

        # Limpiar cualquier residuo de bloqueo de actualización previa
        try:
            from app.core.paths import ROOT_DIR
            lock_p = Path(ROOT_DIR) / "_actualizando.lock"
            if lock_p.exists():
                lock_p.unlink()
        except Exception:
            pass

        # Comprobar actualizaciones al inicio si está habilitado
        if config.get("general", "check_updates_on_start", True):
            wx.CallLater(4000, lambda: self._on_buscar_actualizaciones(silencioso=True))

        self.Bind(wx.EVT_CLOSE, self._on_close)

    def _init_ui(self):
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Splitter principal: Árbol a la izquierda, Lista de chats al centro
        splitter = wx.SplitterWindow(panel, style=wx.SP_LIVE_UPDATE | wx.SP_3D)

        # 1. Panel de navegación (Árbol)
        panel_nav = wx.Panel(splitter)
        sizer_nav = wx.BoxSizer(wx.VERTICAL)
        lbl_nav = wx.StaticText(panel_nav, label="Árbol de navegación (Alt+1):")
        self.tree_nav = wx.TreeCtrl(
            panel_nav,
            style=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT | wx.TR_SINGLE,
            name="Árbol de navegación de Telegram"
        )
        sizer_nav.Add(lbl_nav, 0, wx.ALL, 4)
        sizer_nav.Add(self.tree_nav, 1, wx.EXPAND)
        panel_nav.SetSizer(sizer_nav)

        # 2. Panel central (Lista de chats)
        panel_lista = wx.Panel(splitter)
        sizer_lista = wx.BoxSizer(wx.VERTICAL)
        self.lbl_lista = wx.StaticText(panel_lista, label="Chats de Telegram (Alt+2):")
        self.lista_items = AccessibleListCtrl(
            panel_lista,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL,
            name="Lista de chats"
        )
        sizer_lista.Add(self.lbl_lista, 0, wx.ALL, 4)
        sizer_lista.Add(self.lista_items, 1, wx.EXPAND)
        panel_lista.SetSizer(sizer_lista)

        splitter.SplitVertically(panel_nav, panel_lista, 280)
        main_sizer.Add(splitter, 1, wx.EXPAND)

        # Barra de estado
        self.status_bar = self.CreateStatusBar(2)
        self.status_bar.SetStatusWidths([-3, -1])
        self.status_bar.SetStatusText("Listo.", 0)

        panel.SetSizer(main_sizer)

        # Eventos de controles
        self.tree_nav.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_tree_selection)
        self.lista_items.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_chat_activated)
        self.lista_items.Bind(wx.EVT_CONTEXT_MENU, self._on_context_menu)
        self.lista_items.Bind(wx.EVT_KEY_DOWN, self._on_list_key_down)

        # Temporizador para refresco periódico
        self.timer_sync = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_timer_sync, self.timer_sync)
        intervalo = max(10, int(config.get("telegram", "update_interval", 60))) * 1000
        self.timer_sync.Start(intervalo)

    def _crear_menus(self):
        menubar = wx.MenuBar()

        # --- ARCHIVO ---
        menu_archivo = wx.Menu()
        item_login = menu_archivo.Append(wx.ID_ANY, "Iniciar sesión en Telegram...\tCtrl+Shift+L", "Conectar una cuenta de Telegram")
        self.Bind(wx.EVT_MENU, self._on_login, item_login)

        item_cuentas = menu_archivo.Append(wx.ID_ANY, "Gestionar cuentas...", "Ver o eliminar cuentas guardadas")
        self.Bind(wx.EVT_MENU, self._on_gestionar_cuentas, item_cuentas)

        item_logout = menu_archivo.Append(wx.ID_ANY, "Cerrar sesión de la cuenta activa...", "Cerrar sesión de Telegram")
        self.Bind(wx.EVT_MENU, self._on_logout, item_logout)

        menu_archivo.AppendSeparator()
        item_drive = menu_archivo.Append(wx.ID_ANY, "Telegram Drive (tu nube personal)...\tCtrl+Shift+U", "Abrir el explorador de archivos en la nube")
        self.Bind(wx.EVT_MENU, self._on_tg_drive, item_drive)

        menu_archivo.AppendSeparator()
        item_salir = menu_archivo.Append(wx.ID_EXIT, "Salir\tAlt+F4", "Cerrar la aplicación")
        self.Bind(wx.EVT_MENU, self._on_menu_salir, item_salir)

        menubar.Append(menu_archivo, "&Archivo")

        # --- EDICIÓN ---
        menu_edicion = wx.Menu()
        item_prefs = menu_edicion.Append(wx.ID_PREFERENCES, "Preferencias...\tCtrl+P", "Configurar TelegramAccess")
        self.Bind(wx.EVT_MENU, self._on_preferencias, item_prefs)

        item_teclas = menu_edicion.Append(wx.ID_ANY, "Personalizar teclas...", "Editar atajos de teclado")
        self.Bind(wx.EVT_MENU, self._on_personalizar_teclas, item_teclas)

        menubar.Append(menu_edicion, "&Edición")

        # --- VER ---
        menu_ver = wx.Menu()
        item_refrescar = menu_ver.Append(wx.ID_REFRESH, "Actualizar lista de chats\tF5", "Recargar chats del servidor")
        self.Bind(wx.EVT_MENU, self._on_refrescar_chats, item_refrescar)

        item_marcar_todo = menu_ver.Append(wx.ID_ANY, "Marcar todos los chats como leídos", "Poner el contador de no leídos a cero")
        self.Bind(wx.EVT_MENU, self._on_marcar_todos_leidos, item_marcar_todo)

        menu_ver.AppendSeparator()
        item_ir_arbol = menu_ver.Append(wx.ID_ANY, "Ir al árbol de navegación\tAlt+1", "Enfocar el árbol")
        self.Bind(wx.EVT_MENU, lambda e: self.tree_nav.SetFocus(), item_ir_arbol)

        item_ir_lista = menu_ver.Append(wx.ID_ANY, "Ir a la lista de chats\tAlt+2", "Enfocar la lista de chats")
        self.Bind(wx.EVT_MENU, lambda e: self.lista_items.SetFocus(), item_ir_lista)

        menubar.Append(menu_ver, "&Ver")

        # --- TELEGRAM ---
        menu_tg = wx.Menu()
        item_perfil = menu_tg.Append(wx.ID_ANY, "Mi perfil...", "Ver y editar tu perfil de Telegram")
        self.Bind(wx.EVT_MENU, self._on_tg_perfil, item_perfil)

        item_sesiones = menu_tg.Append(wx.ID_ANY, "Sesiones activas...", "Ver y cerrar sesiones de Telegram")
        self.Bind(wx.EVT_MENU, self._on_tg_sesiones, item_sesiones)

        item_buscar_chats = menu_tg.Append(wx.ID_ANY, "Buscar usuarios, grupos y canales...\tCtrl+Shift+S", "Buscar por nombre o @usuario")
        self.Bind(wx.EVT_MENU, self._on_tg_buscar_chats, item_buscar_chats)

        item_buscar_msg = menu_tg.Append(wx.ID_ANY, "Búsqueda global de mensajes...\tCtrl+Shift+F", "Buscar mensajes en todos los chats")
        self.Bind(wx.EVT_MENU, self._on_tg_buscar_global, item_buscar_msg)

        item_buscar_canales = menu_tg.Append(wx.ID_ANY, "Buscar publicaciones de canales por hashtag...\tCtrl+Shift+K", "Buscar en canales públicos")
        self.Bind(wx.EVT_MENU, self._on_tg_buscar_canales, item_buscar_canales)

        item_guardados = menu_tg.Append(wx.ID_ANY, "Mensajes guardados...\tCtrl+Shift+G", "Abrir tu chat de Mensajes guardados")
        self.Bind(wx.EVT_MENU, self._on_tg_guardados, item_guardados)

        item_priv = menu_tg.Append(wx.ID_ANY, "Privacidad...", "Ajustar quién ve tu información")
        self.Bind(wx.EVT_MENU, self._on_tg_privacidad, item_priv)

        item_priv_glob = menu_tg.Append(wx.ID_ANY, "Privacidad global...", "Archivar chats nuevos, hora de lectura...")
        self.Bind(wx.EVT_MENU, self._on_tg_privacidad_global, item_priv_glob)

        item_ajustes = menu_tg.Append(wx.ID_ANY, "Ajustes de cuenta...", "Autodestrucción por inactividad, número...")
        self.Bind(wx.EVT_MENU, self._on_tg_ajustes_cuenta, item_ajustes)

        item_block = menu_tg.Append(wx.ID_ANY, "Usuarios bloqueados...", "Ver y desbloquear contactos")
        self.Bind(wx.EVT_MENU, self._on_tg_bloqueados, item_block)

        item_carpetas = menu_tg.Append(wx.ID_ANY, "Carpetas...", "Gestionar carpetas de chats")
        self.Bind(wx.EVT_MENU, self._on_tg_carpetas, item_carpetas)

        item_frecuentes = menu_tg.Append(wx.ID_ANY, "Chats frecuentes...", "Tus chats más usados")
        self.Bind(wx.EVT_MENU, self._on_tg_frecuentes, item_frecuentes)

        item_resumen = menu_tg.Append(wx.ID_ANY, "Resumen de Telegram\tCtrl+Shift+T", "Total de chats y contactos")
        self.Bind(wx.EVT_MENU, self._on_tg_resumen, item_resumen)

        item_historias = menu_tg.Append(wx.ID_ANY, "Historias...", "Ver y publicar historias")
        self.Bind(wx.EVT_MENU, self._on_tg_historias, item_historias)

        item_2fa = menu_tg.Append(wx.ID_ANY, "Verificación en dos pasos (2FA)...", "Contraseña en la nube")
        self.Bind(wx.EVT_MENU, self._on_tg_2fa, item_2fa)

        menu_tg.AppendSeparator()

        item_unir = menu_tg.Append(wx.ID_ANY, "Unirse a grupo/canal por enlace...", "Unirse por enlace o @usuario")
        self.Bind(wx.EVT_MENU, self._on_tg_unirse, item_unir)

        item_crear_grupo = menu_tg.Append(wx.ID_ANY, "Crear grupo...", "Crear un nuevo grupo")
        self.Bind(wx.EVT_MENU, self._on_tg_crear_grupo, item_crear_grupo)

        item_crear_super = menu_tg.Append(wx.ID_ANY, "Crear supergrupo...", "Crear supergrupo con temas/foros")
        self.Bind(wx.EVT_MENU, self._on_tg_crear_supergrupo, item_crear_super)

        item_crear_canal = menu_tg.Append(wx.ID_ANY, "Crear canal...", "Crear un canal de difusión")
        self.Bind(wx.EVT_MENU, self._on_tg_crear_canal, item_crear_canal)

        menu_tg.AppendSeparator()
        item_drive_m = menu_tg.Append(wx.ID_ANY, "Telegram Drive (tu nube personal)...", "Abrir la nube privada")
        self.Bind(wx.EVT_MENU, self._on_tg_drive, item_drive_m)

        menubar.Append(menu_tg, "&Telegram")

        # --- HERRAMIENTAS ---
        menu_herramientas = wx.Menu()
        item_sonidos = menu_herramientas.Append(wx.ID_ANY, "Probar efectos de sonido...", "Comprobar sonidos del sistema")
        self.Bind(wx.EVT_MENU, lambda e: SoundTestDialog(self).ShowModal(), item_sonidos)

        item_grabaciones = menu_herramientas.Append(wx.ID_ANY, "Carpeta de grabaciones de llamadas...", "Abrir la carpeta con las grabaciones de llamadas")
        self.Bind(wx.EVT_MENU, self._on_abrir_carpeta_grabaciones, item_grabaciones)
        menubar.Append(menu_herramientas, "&Herramientas")

        # --- AYUDA ---
        menu_ayuda = wx.Menu()
        item_manual = menu_ayuda.Append(wx.ID_HELP, "Manual de usuario\tF1", "Abrir el manual completo")
        self.Bind(wx.EVT_MENU, self._on_ver_manual, item_manual)

        item_ver_teclas = menu_ayuda.Append(wx.ID_ANY, "Teclas de la aplicación\tCtrl+F1", "Listado de atajos")
        self.Bind(wx.EVT_MENU, self._on_ver_teclas, item_ver_teclas)

        menu_ayuda.AppendSeparator()
        item_actualizaciones = menu_ayuda.Append(wx.ID_ANY, "Buscar actualizaciones...", "Comprobar si hay una nueva versión de TelegramAccess")
        self.Bind(wx.EVT_MENU, self._on_buscar_actualizaciones, item_actualizaciones)

        menu_ayuda.AppendSeparator()
        item_cafe = menu_ayuda.Append(wx.ID_ANY, "Invitar a un café (Donaciones)...", "Apoyar el desarrollo del software libre")
        self.Bind(wx.EVT_MENU, lambda e: abrir_url("https://www.paypal.com/paypalme/hjbcdonaciones?country.x=ES&locale.x=es_ES"), item_cafe)

        item_acerca = menu_ayuda.Append(wx.ID_ABOUT, "Acerca de Telegram Accesible...", "Créditos y versión")
        self.Bind(wx.EVT_MENU, self._on_acerca_de, item_acerca)

        menubar.Append(menu_ayuda, "A&yuda")

        self.SetMenuBar(menubar)

    def _aplicar_atajos(self):
        mapa = {
            "actualizar_buffer": lambda e: self._cargar_listado_chats(),
            "buscar_global": self._on_tg_buscar_global,
            "leer_barra_estado": lambda e: speak(self.status_bar.GetStatusText(0), interrupt=True),
            "cuenta_siguiente": self._on_cuenta_siguiente,
            "cuenta_anterior": self._on_cuenta_anterior,
            "preferencias": self._on_preferencias,
            "tg_abrir_chat": self._on_abrir_chat_actual,
            "tg_marcar_leido": self._on_toggle_leido,
            "tg_fijar_chat": self._on_toggle_fijar,
            "tg_drive": self._on_tg_drive,
            "tg_buscar_chats": self._on_tg_buscar_chats,
            "tg_buscar_canales": self._on_tg_buscar_canales,
            "tg_guardados": self._on_tg_guardados,
            "tg_mi_perfil": self._on_tg_perfil,
            "tg_resumen": self._on_tg_resumen,
            # Reproductores
            "media_play_pausa": lambda e: player_service.alternar_pausa(),
            "media_detener": lambda e: player_service.detener_con_aviso(),
            "media_avanzar": lambda e: player_service.avanzar(),
            "media_retroceder": lambda e: player_service.retroceder(),
            "media_subir_volumen": lambda e: player_service.subir_volumen(),
            "media_bajar_volumen": lambda e: player_service.bajar_volumen(),
            "media_subir_velocidad": lambda e: player_service.subir_velocidad(),
            "media_bajar_velocidad": lambda e: player_service.bajar_velocidad(),
        }
        self.SetAcceleratorTable(shortcut_manager.construir_tabla(self, mapa))

    def _suscribir_eventos(self):
        event_bus.subscribe("telegram_new_message", self._on_tg_evt_nuevo_mensaje)
        event_bus.subscribe("telegram_message_edited", self._on_tg_evt_mensaje_editado)
        event_bus.subscribe("telegram_messages_deleted", self._on_tg_evt_mensajes_borrados)
        event_bus.subscribe("telegram_typing", self._on_tg_evt_typing)
        event_bus.subscribe("telegram_user_status", self._on_tg_evt_user_status)
        event_bus.subscribe("telegram_incoming_call", self._on_tg_evt_llamada_entrante)

    def _iniciar_servicios(self):
        # Cargar cuentas de Telegram desde la base de datos
        self._construir_arbol()
        if not self.active_account_id:
            # Si no hay cuentas, avisar amablemente
            wx.CallLater(600, lambda: notificar("No hay cuentas de Telegram conectadas. Vaya al menú Archivo para Iniciar sesión."))
        else:
            self._sincronizar_en_segundo_plano(self.active_account_id, manual=False)

    def _sincronizar_en_segundo_plano(self, account_id: int, manual: bool = False):
        if not account_id:
            return

        def _worker():
            try:
                if manual:
                    wx.CallAfter(lambda: self.status_bar.SetStatusText("Sincronizando chats de Telegram...", 0))
                telegram_service.obtener_cliente(account_id)
                n = telegram_service.cargar_chats(account_id, limit=200)
                log.info(f"Sincronizados {n} chats para la cuenta {account_id}.")

                def _ui():
                    self._construir_arbol()
                    self._cargar_listado_chats()
                    self.status_bar.SetStatusText(f"Listo. {n} chats sincronizados.", 0)
                    if manual:
                        speak(f"{n} chats actualizados.", interrupt=False)
                wx.CallAfter(_ui)
            except Exception as e:
                log.error(f"Error sincronizando chats: {e}")
                wx.CallAfter(lambda: self.status_bar.SetStatusText("Error al sincronizar chats.", 0))

        import threading
        threading.Thread(target=_worker, daemon=True, name=f"SyncChats-{account_id}").start()

    def _on_refrescar_chats(self, event=None):
        if self.active_account_id:
            self._sincronizar_en_segundo_plano(self.active_account_id, manual=True)
        else:
            self._cargar_listado_chats()

    # --- NAVEGACIÓN Y ÁRBOL ---
    def _construir_arbol(self):
        self.tree_nav.Freeze()
        self.tree_nav.DeleteAllItems()
        root = self.tree_nav.AddRoot("Root")

        cuentas = db.query("SELECT id, name FROM accounts WHERE service_id = 'telegram' AND active = 1 ORDER BY position, id")
        primer_item = None

        buffer_labels = [
            ("all", "Todos los chats"),
            ("unread", "No leídos"),
            ("private", "Usuarios"),
            ("bot", "Bots"),
            ("group", "Grupos"),
            ("supergroup", "Supergrupos"),
            ("channel", "Canales"),
            ("contacts", "Contactos"),
        ]

        for acc_id, acc_name in cuentas:
            fila = db.query_one("SELECT COALESCE(SUM(unread_count), 0) FROM telegram_chats WHERE account_id = ?", (acc_id,))
            no_leidos = fila[0] if fila else 0
            badge = f" ({no_leidos} sin leer)" if no_leidos > 0 else ""
            acc_node = self.tree_nav.AppendItem(root, f"{acc_name}{badge}", data={"type": "account", "account_id": acc_id})

            for b_id, b_label in buffer_labels:
                # Contar no leídos por categoría
                extra_cond = ""
                params = [acc_id]
                if b_id == "unread":
                    extra_cond = " AND unread_count > 0"
                elif b_id in ("private", "bot", "group", "supergroup", "channel"):
                    extra_cond = " AND chat_type = ?"
                    params.append(b_id)

                if b_id != "contacts":
                    f_c = db.query_one(f"SELECT COALESCE(SUM(unread_count), 0) FROM telegram_chats WHERE account_id = ?{extra_cond}", tuple(params))
                    cnt = f_c[0] if f_c else 0
                    b_txt = f"{b_label} ({cnt})" if cnt > 0 else b_label
                else:
                    b_txt = b_label

                item = self.tree_nav.AppendItem(acc_node, b_txt, data={"type": "buffer", "account_id": acc_id, "buffer": b_id})
                if primer_item is None:
                    primer_item = item

            # Carpetas de Telegram de esta cuenta
            carpetas = db.query("SELECT folder_id, title FROM telegram_folders WHERE account_id = ? ORDER BY folder_id", (acc_id,))
            for f_id, f_title in carpetas:
                self.tree_nav.AppendItem(acc_node, f"Carpeta: {f_title}", data={"type": "buffer", "account_id": acc_id, "buffer": f"folder:{f_id}"})

            self.tree_nav.Expand(acc_node)

        self.tree_nav.Thaw()

        if primer_item:
            self.tree_nav.SelectItem(primer_item)
        elif not cuentas:
            self.lista_items.DeleteAllItems()
            self.status_bar.SetStatusText("Sin cuentas configuradas.", 0)

    def _on_tree_selection(self, event):
        item = event.GetItem()
        if not item.IsOk():
            return
        data = self.tree_nav.GetItemData(item)
        if not data:
            return

        acc_id = data.get("account_id")
        if data.get("type") == "buffer":
            self.active_account_id = acc_id
            self.active_timeline_type = data.get("buffer", "all")
            self._cargar_listado_chats()
        elif data.get("type") == "account":
            self.active_account_id = acc_id
            self.active_timeline_type = "all"
            self._cargar_listado_chats()

    # --- LISTADO DE CHATS ---
    def _cargar_listado_chats(self):
        self.lista_items.DeleteAllItems()
        self.lista_items.ClearAll()
        self.lista_items_db_ids.clear()

        if not self.active_account_id:
            return

        # Columnas
        self.lista_items.InsertColumn(0, "Chat / Título", width=220)
        self.lista_items.InsertColumn(1, "Tipo", width=100)
        self.lista_items.InsertColumn(2, "No leídos", width=80)
        self.lista_items.InsertColumn(3, "Último mensaje", width=300)
        self.lista_items.InsertColumn(4, "Fecha", width=120)
        self.lista_items.InsertColumn(5, "Estado", width=120)

        # Si el buffer es contactos
        if self.active_timeline_type == "contacts":
            self._cargar_contactos()
            return

        sql = """
        SELECT id, chat_id, title, chat_type, unread_count, last_message, last_message_date,
               COALESCE(muted,0), COALESCE(pinned,0), COALESCE(verified,0), COALESCE(protected,0), COALESCE(blocked,0)
        FROM telegram_chats WHERE account_id = ?
        """
        params = [self.active_account_id]

        if self.active_timeline_type == "unread":
            sql += " AND unread_count > 0"
        elif self.active_timeline_type in ("private", "bot", "group", "supergroup", "channel"):
            sql += " AND chat_type = ?"
            params.append(self.active_timeline_type)
        elif str(self.active_timeline_type).startswith("folder:"):
            folder_id = self.active_timeline_type.split(":", 1)[1]
            fila = db.query_one("SELECT chat_ids_json FROM telegram_folders WHERE account_id = ? AND folder_id = ?",
                                (self.active_account_id, folder_id))
            ids = []
            if fila and fila[0]:
                try:
                    ids = json.loads(fila[0])
                except Exception:
                    ids = []
            if ids:
                placeholders = ",".join("?" for _ in ids)
                sql += f" AND chat_id IN ({placeholders})"
                params.extend(ids)
            else:
                sql += " AND 0"

        sql += " ORDER BY pinned DESC, last_message_date DESC LIMIT 500"
        rows = db.query(sql, tuple(params))

        tipo_labels = {
            "private": "Privado", "bot": "Bot", "group": "Grupo",
            "supergroup": "Supergrupo", "channel": "Canal"
        }

        for idx, r in enumerate(rows):
            db_id, chat_id, title, chat_type, unread, last_msg, last_date, muted, pinned, verified, protected, blocked = r
            tipo_txt = tipo_labels.get(chat_type, chat_type or "Chat")
            fecha_rel = formatear_tiempo_relativo(str(last_date)) if last_date else ""

            flags = []
            if pinned:
                flags.append("Fijado")
            if muted:
                flags.append("Silenciado")
            if verified:
                flags.append("Verificado")
            if protected:
                flags.append("Protegido")
            if blocked:
                flags.append("Bloqueado")
            flags_txt = ", ".join(flags)

            self.lista_items.InsertItem(idx, title or "Sin título")
            self.lista_items.SetItem(idx, 1, tipo_txt)
            self.lista_items.SetItem(idx, 2, str(unread) if unread > 0 else "")
            self.lista_items.SetItem(idx, 3, (last_msg or "").replace("\n", " "))
            self.lista_items.SetItem(idx, 4, fecha_rel)
            self.lista_items.SetItem(idx, 5, flags_txt)

            # Lectura accesible completa para el lector de pantalla
            lectura = f"{title}. {tipo_txt}."
            if unread > 0:
                lectura += f" {unread} mensajes no leídos."
            if last_msg:
                lectura += f" Último mensaje: {last_msg}."
            if fecha_rel:
                lectura += f" {fecha_rel}."
            if flags_txt:
                lectura += f" {flags_txt}."
            self.lista_items.establecer_lectura(idx, lectura)

            self.lista_items_db_ids.append(f"{self.active_account_id}|{chat_id}|{title or ''}")

        total_chats = len(rows)
        self.status_bar.SetStatusText(f"Mostrando {total_chats} chats.", 0)
        self.status_bar.SetStatusText(f"Cuenta ID: {self.active_account_id}", 1)

    def _cargar_contactos(self):
        rows = db.query(
            "SELECT user_id, first_name, last_name, username, phone FROM telegram_contacts WHERE account_id = ? ORDER BY first_name, last_name",
            (self.active_account_id,)
        )
        for idx, (uid, fn, ln, uname, phone) in enumerate(rows):
            nombre = f"{fn or ''} {ln or ''}".strip() or uname or f"Usuario {uid}"
            uname_txt = f"@{uname}" if uname else ""
            self.lista_items.InsertItem(idx, nombre)
            self.lista_items.SetItem(idx, 1, "Contacto")
            self.lista_items.SetItem(idx, 2, "")
            self.lista_items.SetItem(idx, 3, uname_txt)
            self.lista_items.SetItem(idx, 4, phone or "")
            self.lista_items.SetItem(idx, 5, "")

            self.lista_items.establecer_lectura(idx, f"Contacto: {nombre}. {uname_txt}. Teléfono: {phone or 'No disponible'}.")
            self.lista_items_db_ids.append(f"{self.active_account_id}|{uid}|{nombre}")

        self.status_bar.SetStatusText(f"Mostrando {len(rows)} contactos.", 0)

    # --- ACCIONES SOBRE CHAT ---
    def _on_chat_activated(self, event):
        idx = event.GetIndex()
        self._abrir_conversacion(idx)

    def _on_abrir_chat_actual(self, event):
        idx = self.lista_items.GetFirstSelected()
        if idx != -1:
            self._abrir_conversacion(idx)

    def _abrir_conversacion(self, idx: int):
        if idx < 0 or idx >= len(self.lista_items_db_ids):
            return
        entry = self.lista_items_db_ids[idx]
        parts = entry.split("|", 2)
        if len(parts) < 3:
            return
        acc_id, chat_id_str, title = int(parts[0]), int(parts[1]), parts[2]

        fila = db.query_one("SELECT chat_type FROM telegram_chats WHERE id = ?", (f"{acc_id}:{chat_id_str}",))
        chat_type = fila[0] if fila else "private"

        dlg = TelegramConversationDialog(self, acc_id, chat_id_str, title, chat_type=chat_type)
        dlg.ShowModal()
        dlg.Destroy()

        # Refrescar listado para actualizar contador de leídos
        wx.CallLater(300, self._cargar_listado_chats)

    def _on_context_menu(self, event):
        idx = self.lista_items.GetFirstSelected()
        if idx == -1 or idx >= len(self.lista_items_db_ids):
            return

        parts = self.lista_items_db_ids[idx].split("|", 2)
        chat_id = int(parts[1])

        est = db.query_one(
            "SELECT unread_count, muted, pinned, chat_type, COALESCE(blocked,0), title FROM telegram_chats WHERE id = ?",
            (f"{self.active_account_id}:{chat_id}",)
        )
        if not est:
            return

        unread, muted, pinned, tipo, blocked, title = est
        unread = unread or 0
        muted = bool(muted)
        pinned = bool(pinned)
        blocked = bool(blocked)
        tipo = tipo or "private"
        title = title or ""

        menu = wx.Menu()

        item_abrir = menu.Append(wx.ID_ANY, "Abrir conversación (Enter)")
        self.Bind(wx.EVT_MENU, lambda e, i=idx: self._abrir_conversacion(i), item_abrir)

        if unread > 0:
            item_leido = menu.Append(wx.ID_ANY, f"Marcar como leído ({unread} sin leer)")
            self.Bind(wx.EVT_MENU, lambda e, c=chat_id: self._chat_accion(c, "leido"), item_leido)
        else:
            item_no_leido = menu.Append(wx.ID_ANY, "Marcar como no leído")
            self.Bind(wx.EVT_MENU, lambda e, c=chat_id: self._chat_accion(c, "no_leido"), item_no_leido)

        item_pin = menu.Append(wx.ID_ANY, "Desfijar de la lista" if pinned else "Fijar en la lista")
        self.Bind(wx.EVT_MENU, lambda e, c=chat_id: self._chat_accion(c, "fijar"), item_pin)

        # Archivar / Desarchivar
        sub_arch = wx.Menu()
        it_a = sub_arch.Append(wx.ID_ANY, "Archivar este chat")
        self.Bind(wx.EVT_MENU, lambda e, c=chat_id: self._chat_accion(c, "archivar"), it_a)
        it_da = sub_arch.Append(wx.ID_ANY, "Sacar del archivo")
        self.Bind(wx.EVT_MENU, lambda e, c=chat_id: self._chat_accion(c, "desarchivar"), it_da)
        menu.AppendSubMenu(sub_arch, "Archivar / desarchivar")

        # Silenciar
        if muted:
            item_mute = menu.Append(wx.ID_ANY, "Reactivar notificaciones (ahora silenciado)")
            self.Bind(wx.EVT_MENU, lambda e, c=chat_id: self._chat_accion(c, "reactivar"), item_mute)
        else:
            sub_mute = wx.Menu()
            for etiqueta, accion in (
                ("1 hora", "silenciar_min:60"),
                ("8 horas", "silenciar_min:480"),
                ("2 días", "silenciar_min:2880"),
                ("Para siempre", "silenciar_siempre")
            ):
                it = sub_mute.Append(wx.ID_ANY, etiqueta)
                self.Bind(wx.EVT_MENU, lambda e, c=chat_id, a=accion: self._chat_accion(c, a), it)
            menu.AppendSubMenu(sub_mute, "Silenciar notificaciones")

        menu.AppendSeparator()

        # Carpetas
        carpetas = db.query("SELECT folder_id, title, COALESCE(chat_ids_json, '[]') FROM telegram_folders WHERE account_id = ?", (self.active_account_id,))
        if carpetas:
            sub_carp = wx.Menu()
            for f_id, f_title, ids_json in carpetas:
                try:
                    c_ids = {str(x) for x in json.loads(ids_json or "[]")}
                except Exception:
                    c_ids = set()
                if str(chat_id) in c_ids:
                    s_del = sub_carp.Append(wx.ID_ANY, f"Quitar de «{f_title}»")
                    self.Bind(wx.EVT_MENU, lambda e, c=chat_id, fi=f_id: self._chat_carpeta(c, fi, False), s_del)
                else:
                    s_add = sub_carp.Append(wx.ID_ANY, f"Añadir a «{f_title}»")
                    self.Bind(wx.EVT_MENU, lambda e, c=chat_id, fi=f_id: self._chat_carpeta(c, fi, True), s_add)
            menu.AppendSubMenu(sub_carp, "Carpetas")

        # Acciones según tipo
        if tipo in ("private", "bot"):
            if blocked:
                it_bl = menu.Append(wx.ID_ANY, "Desbloquear usuario")
                self.Bind(wx.EVT_MENU, lambda e, c=chat_id: self._chat_accion(c, "desbloquear"), it_bl)
            else:
                it_bl = menu.Append(wx.ID_ANY, "Bloquear usuario")
                self.Bind(wx.EVT_MENU, lambda e, c=chat_id: self._chat_accion(c, "bloquear"), it_bl)
            it_del = menu.Append(wx.ID_ANY, "Borrar este chat...")
            self.Bind(wx.EVT_MENU, lambda e, c=chat_id: self._chat_accion(c, "borrar"), it_del)
        elif tipo in ("group", "supergroup"):
            it_mb = menu.Append(wx.ID_ANY, "Ver miembros...")
            self.Bind(wx.EVT_MENU, lambda e, c=chat_id: self._on_ver_miembros(c), it_mb)
            it_out = menu.Append(wx.ID_ANY, "Salir del grupo...")
            self.Bind(wx.EVT_MENU, lambda e, c=chat_id: self._chat_accion(c, "salir"), it_out)
        elif tipo == "channel":
            it_sim = menu.Append(wx.ID_ANY, "Canales similares...")
            self.Bind(wx.EVT_MENU, lambda e, c=chat_id, t=title: self._on_canales_similares(c, t), it_sim)
            it_hist = menu.Append(wx.ID_ANY, "Historias del canal...")
            self.Bind(wx.EVT_MENU, lambda e, c=chat_id, t=title: self._on_historias_canal(c, t), it_hist)
            it_out = menu.Append(wx.ID_ANY, "Dejar de seguir el canal...")
            self.Bind(wx.EVT_MENU, lambda e, c=chat_id: self._chat_accion(c, "salir"), it_out)

        menu.AppendSeparator()
        lbl_call = "Entrar al chat de voz..." if tipo in ("group", "supergroup", "channel") else "Llamar por audio..."
        it_call = menu.Append(wx.ID_ANY, lbl_call)
        self.Bind(wx.EVT_MENU, lambda e, c=chat_id, t=title: self._iniciar_llamada_ui(c, t, con_video=False), it_call)

        it_vcall = menu.Append(wx.ID_ANY, "Iniciar videollamada...")
        self.Bind(wx.EVT_MENU, lambda e, c=chat_id, t=title: self._iniciar_llamada_ui(c, t, con_video=True), it_vcall)

        menu.AppendSeparator()
        it_prop = menu.Append(wx.ID_ANY, "Propiedades del chat...")
        self.Bind(wx.EVT_MENU, lambda e, c=chat_id: self._on_chat_propiedades(c), it_prop)

        self.PopupMenu(menu)
        menu.Destroy()

    def _chat_accion(self, chat_id: int, accion: str):
        cuenta = self.active_account_id
        if not cuenta:
            return

        def _bg():
            try:
                if accion == "leido":
                    telegram_service.marcar_chat_leido(cuenta, chat_id)
                elif accion == "no_leido":
                    telegram_service.marcar_chat_no_leido(cuenta, chat_id)
                elif accion == "fijar":
                    fila = db.query_one("SELECT COALESCE(pinned, 0) FROM telegram_chats WHERE id = ?", (f"{cuenta}:{chat_id}",))
                    p = bool(fila[0]) if fila else False
                    telegram_service.fijar_chat(cuenta, chat_id, fijar=not p)
                elif accion == "archivar":
                    telegram_service.archivar_chat(cuenta, chat_id, archivar=True)
                elif accion == "desarchivar":
                    telegram_service.archivar_chat(cuenta, chat_id, archivar=False)
                elif accion == "reactivar":
                    telegram_service.silenciar_chat(cuenta, chat_id, silenciar=False)
                elif accion == "silenciar_siempre":
                    telegram_service.silenciar_chat(cuenta, chat_id, silenciar=True)
                elif accion.startswith("silenciar_min:"):
                    mins = int(accion.split(":", 1)[1])
                    telegram_service.silenciar_chat(cuenta, chat_id, silenciar=True, minutos=mins)
                elif accion == "bloquear":
                    telegram_service.bloquear_usuario(cuenta, chat_id)
                elif accion == "desbloquear":
                    telegram_service.desbloquear_usuario(cuenta, chat_id)
                elif accion == "borrar":
                    telegram_service.salir_chat(cuenta, chat_id, eliminar=True)
                elif accion == "salir":
                    telegram_service.salir_chat(cuenta, chat_id, eliminar=False)
                wx.CallAfter(self._cargar_listado_chats)
            except Exception as e:
                wx.CallAfter(lambda: mostrar_error(self, str(e), "Error en Telegram"))

        import threading
        threading.Thread(target=_bg, daemon=True).start()

    def _chat_carpeta(self, chat_id: int, folder_id: int, anadir: bool):
        cuenta = self.active_account_id
        def _bg():
            try:
                telegram_service.modificar_chat_carpeta(cuenta, chat_id, folder_id, anadir)
                wx.CallAfter(self._cargar_listado_chats)
            except Exception as e:
                wx.CallAfter(lambda: mostrar_error(self, str(e), "Error"))
        import threading
        threading.Thread(target=_bg, daemon=True).start()

    def _on_list_key_down(self, event):
        kc = event.GetKeyCode()
        if kc == wx.WXK_RETURN:
            idx = self.lista_items.GetFirstSelected()
            if idx != -1:
                self._abrir_conversacion(idx)
        elif kc in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            idx = self.lista_items.GetFirstSelected()
            if idx != -1 and confirmar(self, "¿Desea eliminar o salir de este chat?"):
                parts = self.lista_items_db_ids[idx].split("|", 2)
                self._chat_accion(int(parts[1]), "borrar")
        else:
            event.Skip()

    def _on_toggle_leido(self, event):
        idx = self.lista_items.GetFirstSelected()
        if idx != -1:
            parts = self.lista_items_db_ids[idx].split("|", 2)
            chat_id = int(parts[1])
            fila = db.query_one("SELECT unread_count FROM telegram_chats WHERE id = ?", (f"{self.active_account_id}:{chat_id}",))
            unread = (fila[0] if fila else 0) or 0
            self._chat_accion(chat_id, "no_leido" if unread == 0 else "leido")

    def _on_toggle_fijar(self, event):
        idx = self.lista_items.GetFirstSelected()
        if idx != -1:
            parts = self.lista_items_db_ids[idx].split("|", 2)
            self._chat_accion(int(parts[1]), "fijar")

    def _on_cuenta_siguiente(self, event):
        cuentas = db.query("SELECT id FROM accounts WHERE service_id = 'telegram' AND active = 1 ORDER BY position, id")
        if len(cuentas) <= 1:
            return
        ids = [c[0] for c in cuentas]
        try:
            curr_i = ids.index(self.active_account_id)
            sig = ids[(curr_i + 1) % len(ids)]
        except Exception:
            sig = ids[0]
        self.active_account_id = sig
        self._construir_arbol()

    def _on_cuenta_anterior(self, event):
        cuentas = db.query("SELECT id FROM accounts WHERE service_id = 'telegram' AND active = 1 ORDER BY position, id")
        if len(cuentas) <= 1:
            return
        ids = [c[0] for c in cuentas]
        try:
            curr_i = ids.index(self.active_account_id)
            ant = ids[(curr_i - 1) % len(ids)]
        except Exception:
            ant = ids[0]
        self.active_account_id = ant
        self._construir_arbol()

    # --- DIÁLOGOS Y GESTIÓN DE TELEGRAM ---
    def _on_login(self, event):
        dlg = TelegramLoginDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            self._construir_arbol()
            if self.active_account_id:
                self._sincronizar_en_segundo_plano(self.active_account_id, manual=True)
        dlg.Destroy()

    def _on_gestionar_cuentas(self, event):
        cuentas = db.query("SELECT id, name FROM accounts WHERE service_id = 'telegram'")
        if not cuentas:
            mostrar_info(self, "No hay cuentas registradas.")
            return
        msg = "Cuentas de Telegram registradas:\n\n"
        for cid, cname in cuentas:
            msg += f"• ID {cid}: {cname}\n"
        mostrar_info(self, msg, "Gestionar Cuentas")

    def _on_logout(self, event):
        if not self.active_account_id:
            return
        if confirmar(self, "¿Seguro que desea cerrar la sesión de esta cuenta de Telegram?"):
            try:
                telegram_service.logout(self.active_account_id)
                db.execute("DELETE FROM accounts WHERE id = ?", (self.active_account_id,))
                self.active_account_id = None
                self._construir_arbol()
                notificar("Sesión cerrada correctamente.")
            except Exception as e:
                mostrar_error(self, str(e), "Error al cerrar sesión")

    def _on_tg_drive(self, event):
        if not self.active_account_id:
            mostrar_error(self, "Inicie sesión en Telegram para usar Telegram Drive.")
            return
        frame = TelegramDriveFrame(self, self.active_account_id)
        frame.Show()

    def _on_marcar_todos_leidos(self, event):
        if not self.active_account_id:
            return
        def _bg():
            telegram_service.marcar_todos_leidos(self.active_account_id)
            wx.CallAfter(self._construir_arbol)
            wx.CallAfter(lambda: notificar("Todos los chats se han marcado como leídos."))
        import threading
        threading.Thread(target=_bg, daemon=True).start()

    def _on_tg_perfil(self, event):
        if self.active_account_id:
            TelegramProfileDialog(self, self.active_account_id).ShowModal()

    def _on_tg_sesiones(self, event):
        if self.active_account_id:
            TelegramSessionsDialog(self, self.active_account_id).ShowModal()

    def _on_tg_buscar_chats(self, event):
        if not self.active_account_id:
            return
        dlg = CustomTextEntryDialog(self, "Nombre o @usuario de la persona, grupo o canal a buscar:", "Buscar en Telegram")
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        query = dlg.GetValue().strip()
        dlg.Destroy()
        if not query:
            return

        def _bg():
            try:
                res = telegram_service.buscar_contactos(self.active_account_id, query)
                if not res:
                    wx.CallAfter(lambda: speak("Sin resultados.", interrupt=True))
                    return
                tipo_label = {"private": "Usuario", "bot": "Bot", "group": "Grupo", "supergroup": "Supergrupo", "channel": "Canal"}
                opciones = []
                for r in res:
                    etiqueta = tipo_label.get(r.get("tipo"), "")
                    usuario = r.get("username") or ""
                    opciones.append(" — ".join(p for p in [r.get("nombre", ""), etiqueta, usuario] if p))

                def _mostrar_res():
                    sel = wx.SingleChoiceDialog(self, "Resultados (Aceptar abre la conversación):", "Buscar en Telegram", opciones)
                    if sel.ShowModal() == wx.ID_OK:
                        r = res[sel.GetSelection()]
                        d = TelegramConversationDialog(self, self.active_account_id, r["id"], r["nombre"], chat_type=r.get("tipo", "private"))
                        d.ShowModal()
                        d.Destroy()
                    sel.Destroy()
                wx.CallAfter(_mostrar_res)
            except Exception as e:
                wx.CallAfter(lambda: mostrar_error(self, str(e), "Error"))

        speak("Buscando...", interrupt=True)
        import threading
        threading.Thread(target=_bg, daemon=True).start()

    def _on_tg_buscar_global(self, event):
        if not self.active_account_id:
            return
        dlg = CustomTextEntryDialog(self, "Texto a buscar en todos los chats:", "Búsqueda global en Telegram")
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        query = dlg.GetValue().strip()
        dlg.Destroy()
        if not query:
            return

        def _bg():
            try:
                res = telegram_service.buscar_global(self.active_account_id, query)
                if not res:
                    wx.CallAfter(lambda: speak("Sin resultados.", interrupt=True))
                    return
                opciones = [f"{r.get('chat_title', '')}: {r.get('text', '')}" for r in res]

                def _mostrar_res():
                    sel = wx.SingleChoiceDialog(self, "Resultados (Aceptar abre la conversación):", "Resultados", opciones)
                    if sel.ShowModal() == wx.ID_OK:
                        r = res[sel.GetSelection()]
                        d = TelegramConversationDialog(self, self.active_account_id, r["chat_id"], r["chat_title"])
                        d.ShowModal()
                        d.Destroy()
                    sel.Destroy()
                wx.CallAfter(_mostrar_res)
            except Exception as e:
                wx.CallAfter(lambda: mostrar_error(self, str(e), "Error"))

        speak("Buscando...", interrupt=True)
        import threading
        threading.Thread(target=_bg, daemon=True).start()

    def _on_tg_buscar_canales(self, event):
        if not self.active_account_id:
            return
        dlg = CustomTextEntryDialog(self, "Hashtag a buscar en canales públicos (con o sin #):", "Buscar publicaciones de canales")
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        query = dlg.GetValue().strip()
        dlg.Destroy()
        if not query:
            return

        def _bg():
            try:
                res = telegram_service.buscar_publicaciones_canales(self.active_account_id, query)
                if not res:
                    wx.CallAfter(lambda: speak("Sin resultados.", interrupt=True))
                    return
                opciones = [f"{r.get('chat_title', '')}: {r.get('text', '')[:120]}" for r in res]

                def _mostrar_res():
                    sel = wx.SingleChoiceDialog(self, "Publicaciones de canales (Aceptar abre el canal):", "Resultados", opciones)
                    if sel.ShowModal() == wx.ID_OK:
                        r = res[sel.GetSelection()]
                        d = TelegramConversationDialog(self, self.active_account_id, r["chat_id"], r.get("chat_title", ""))
                        d.ShowModal()
                        d.Destroy()
                    sel.Destroy()
                wx.CallAfter(_mostrar_res)
            except Exception as e:
                wx.CallAfter(lambda: mostrar_error(self, str(e), "Error"))

        speak("Buscando en canales públicos...", interrupt=True)
        import threading
        threading.Thread(target=_bg, daemon=True).start()

    def _on_tg_guardados(self, event):
        if not self.active_account_id:
            return
        cuenta = self.active_account_id

        def _bg(ctx):
            return telegram_service.obtener_id_guardados(cuenta)

        def _finish(res, err):
            if not self:
                return
            if err or not res:
                notificar(_("No se pudo abrir Mensajes guardados: {0}").format(err or ""))
                return
            dlg = TelegramConversationDialog(self, cuenta, res, _("Mensajes guardados"), chat_type="private")
            dlg.ShowModal()
            dlg.Destroy()
            self._cargar_listado_chats()

        speak(_("Abriendo Mensajes guardados..."), interrupt=True)
        task_manager.start_task(_bg, callback=_finish, pass_context=True)

    def _on_tg_privacidad(self, event):
        if self.active_account_id:
            mostrar_info(self, "Los ajustes de privacidad se configuran en el diálogo de Ajustes de Cuenta o desde Telegram.")

    def _on_tg_privacidad_global(self, event):
        if self.active_account_id:
            TelegramPrivacidadGlobalDialog(self, self.active_account_id).ShowModal()

    def _on_tg_ajustes_cuenta(self, event):
        if self.active_account_id:
            TelegramAjustesCuentaDialog(self, self.active_account_id).ShowModal()

    def _on_tg_bloqueados(self, event):
        if not self.active_account_id:
            return
        def _bg():
            try:
                bloqs = telegram_service.obtener_bloqueados(self.active_account_id)
                msg = f"Usuarios bloqueados ({len(bloqs)}):\n\n"
                for u in bloqs:
                    msg += f"• {u.get('name', 'Usuario')} (@{u.get('username', '')})\n"
                wx.CallAfter(lambda: mostrar_info(self, msg, "Bloqueados"))
            except Exception as e:
                wx.CallAfter(lambda: mostrar_error(self, str(e), "Error"))
        import threading
        threading.Thread(target=_bg, daemon=True).start()

    def _on_tg_carpetas(self, event):
        if self.active_account_id:
            TelegramCarpetasDialog(self, self.active_account_id).ShowModal()
            self._construir_arbol()

    def _on_tg_frecuentes(self, event):
        if self.active_account_id:
            TelegramChatsSugeridosDialog(self, self.active_account_id).ShowModal()

    def _on_tg_resumen(self, event):
        if not self.active_account_id:
            return
        n_chats = db.query_one("SELECT COUNT(1) FROM telegram_chats WHERE account_id = ?", (self.active_account_id,))[0]
        n_cont = db.query_one("SELECT COUNT(1) FROM telegram_contacts WHERE account_id = ?", (self.active_account_id,))[0]
        n_unread = db.query_one("SELECT COALESCE(SUM(unread_count), 0) FROM telegram_chats WHERE account_id = ?", (self.active_account_id,))[0]
        msg = (
            f"Resumen de su cuenta de Telegram:\n\n"
            f"• Total de chats en caché: {n_chats}\n"
            f"• Mensajes sin leer: {n_unread}\n"
            f"• Contactos sincronizados: {n_cont}"
        )
        mostrar_info(self, msg, "Resumen de Telegram")

    def _on_tg_historias(self, event):
        if self.active_account_id:
            TelegramHistoriasDialog(self, self.active_account_id).ShowModal()

    def _on_tg_2fa(self, event):
        if not self.active_account_id:
            return
        dlg = CustomTextEntryDialog(self, "Nueva contraseña 2FA en la nube:", "Verificación en dos pasos", password=True)
        if dlg.ShowModal() == wx.ID_OK:
            pwd = dlg.GetValue()
            if pwd:
                def _bg():
                    try:
                        telegram_service.activar_2fa(self.active_account_id, pwd)
                        wx.CallAfter(lambda: notificar("Contraseña 2FA configurada con éxito."))
                    except Exception as e:
                        wx.CallAfter(lambda: mostrar_error(self, str(e), "Error 2FA"))
                import threading
                threading.Thread(target=_bg, daemon=True).start()
        dlg.Destroy()

    def _on_tg_unirse(self, event):
        if not self.active_account_id:
            return
        dlg = CustomTextEntryDialog(self, "Enlace de invitación o @usuario:", "Unirse a Grupo o Canal")
        if dlg.ShowModal() == wx.ID_OK:
            link = dlg.GetValue().strip()
            if link:
                def _bg():
                    try:
                        telegram_service.unirse_por_enlace(self.active_account_id, link)
                        wx.CallAfter(lambda: notificar("Se ha unido correctamente."))
                        wx.CallAfter(self._cargar_listado_chats)
                    except Exception as e:
                        wx.CallAfter(lambda: mostrar_error(self, str(e), "Error al unirse"))
                import threading
                threading.Thread(target=_bg, daemon=True).start()
        dlg.Destroy()

    def _on_tg_crear_grupo(self, event):
        if not self.active_account_id:
            return
        dlg = CustomTextEntryDialog(self, "Nombre del nuevo grupo:", "Crear Grupo de Telegram")
        if dlg.ShowModal() == wx.ID_OK:
            titulo = dlg.GetValue().strip()
            if titulo:
                def _bg():
                    try:
                        telegram_service.crear_grupo(self.active_account_id, titulo, [])
                        wx.CallAfter(lambda: notificar("Grupo creado exitosamente."))
                        wx.CallAfter(self._cargar_listado_chats)
                    except Exception as e:
                        wx.CallAfter(lambda: mostrar_error(self, str(e), "Error creando grupo"))
                import threading
                threading.Thread(target=_bg, daemon=True).start()
        dlg.Destroy()

    def _on_tg_crear_supergrupo(self, event):
        if not self.active_account_id:
            return
        dlg = CustomTextEntryDialog(self, "Nombre del nuevo supergrupo:", "Crear Supergrupo")
        if dlg.ShowModal() == wx.ID_OK:
            titulo = dlg.GetValue().strip()
            if titulo:
                def _bg():
                    try:
                        telegram_service.crear_supergrupo(self.active_account_id, titulo, "", es_foro=False)
                        wx.CallAfter(lambda: notificar("Supergrupo creado."))
                        wx.CallAfter(self._cargar_listado_chats)
                    except Exception as e:
                        wx.CallAfter(lambda: mostrar_error(self, str(e), "Error"))
                import threading
                threading.Thread(target=_bg, daemon=True).start()
        dlg.Destroy()

    def _on_tg_crear_canal(self, event):
        if not self.active_account_id:
            return
        dlg = CustomTextEntryDialog(self, "Nombre del nuevo canal de difusión:", "Crear Canal")
        if dlg.ShowModal() == wx.ID_OK:
            titulo = dlg.GetValue().strip()
            if titulo:
                def _bg():
                    try:
                        telegram_service.crear_canal(self.active_account_id, titulo)
                        wx.CallAfter(lambda: notificar("Canal creado con éxito."))
                        wx.CallAfter(self._cargar_listado_chats)
                    except Exception as e:
                        wx.CallAfter(lambda: mostrar_error(self, str(e), "Error"))
                import threading
                threading.Thread(target=_bg, daemon=True).start()
        dlg.Destroy()

    def _on_ver_miembros(self, chat_id: int):
        def _bg():
            try:
                miembros = telegram_service.obtener_miembros(self.active_account_id, chat_id)
                msg = f"Miembros del grupo ({len(miembros)}):\n\n"
                for m in miembros:
                    msg += f"• {m.get('name', '')} (@{m.get('username', '')}) - {m.get('role', 'miembro')}\n"
                wx.CallAfter(lambda: mostrar_info(self, msg, "Miembros"))
            except Exception as e:
                wx.CallAfter(lambda: mostrar_error(self, str(e), "Error"))
        import threading
        threading.Thread(target=_bg, daemon=True).start()

    def _on_canales_similares(self, chat_id: int, titulo: str):
        def _bg():
            try:
                canales = telegram_service.obtener_canales_similares(self.active_account_id, chat_id)
                msg = f"Canales similares a {titulo} ({len(canales)}):\n\n"
                for c in canales:
                    msg += f"• {c.get('title', '')} (@{c.get('username', '')})\n"
                wx.CallAfter(lambda: mostrar_info(self, msg, "Canales similares"))
            except Exception as e:
                wx.CallAfter(lambda: mostrar_error(self, str(e), "Error"))
        import threading
        threading.Thread(target=_bg, daemon=True).start()

    def _on_historias_canal(self, chat_id: int, titulo: str):
        mostrar_info(self, f"Historias del canal {titulo}: Sin historias recientes.")

    def _on_chat_propiedades(self, chat_id: int):
        dlg = TelegramPropiedadesDialog(self, self.active_account_id, chat_id)
        dlg.ShowModal()
        dlg.Destroy()

    # --- EVENTOS EN TIEMPO REAL ---
    def _on_tg_evt_nuevo_mensaje(self, *args, **kwargs):
        acc_id = args[0] if len(args) > 0 and isinstance(args[0], int) else kwargs.get("account_id")
        if not acc_id and args and isinstance(args[0], dict):
            acc_id = args[0].get("account_id")
        if acc_id is None or acc_id == self.active_account_id:
            def _refresh():
                self._construir_arbol()
                self._cargar_listado_chats()
            wx.CallAfter(_refresh)

    def _on_tg_evt_mensaje_editado(self, *args, **kwargs):
        wx.CallAfter(self._cargar_listado_chats)

    def _on_tg_evt_mensajes_borrados(self, *args, **kwargs):
        wx.CallAfter(self._cargar_listado_chats)

    def _on_tg_evt_typing(self, *args, **kwargs):
        desc = ""
        if len(args) >= 3:
            desc = str(args[2] or "")
        elif args and isinstance(args[0], dict):
            desc = args[0].get("descripcion", "")
        elif "descripcion" in kwargs:
            desc = kwargs["descripcion"]
        if desc:
            self.status_bar.SetStatusText(desc, 0)
            wx.CallLater(3000, lambda: self.status_bar.SetStatusText("Listo.", 0))

    def _on_tg_evt_user_status(self, *args, **kwargs):
        pass

    def _iniciar_llamada_ui(self, chat_id: int, title: str, con_video: bool = False):
        from app.ui.telegram_llamada_dialog import TelegramCallDialog
        dlg = TelegramCallDialog(
            self,
            account_id=self.active_account_id,
            chat_id=chat_id,
            peer_name=title or str(chat_id),
            con_video=con_video,
            es_entrante=False
        )
        dlg.Show()

    def _on_tg_evt_llamada_entrante(self, account_id: int, chat_id: int, **kwargs):
        wx.CallAfter(self._mostrar_llamada_entrante, account_id, chat_id)

    def _mostrar_llamada_entrante(self, account_id: int, chat_id: int):
        nombre = str(chat_id)
        try:
            row = db.query_one("SELECT title FROM telegram_chats WHERE id = ?", (f"{account_id}:{chat_id}",))
            if row and row[0]:
                nombre = row[0]
        except Exception:
            pass
        from app.ui.telegram_llamada_dialog import TelegramIncomingCallDialog
        dlg = TelegramIncomingCallDialog(self, account_id, chat_id, nombre)
        dlg.Show()

    def _on_abrir_carpeta_grabaciones(self, event=None):
        import os
        carpeta = telegram_service.obtener_carpeta_grabaciones()
        try:
            os.startfile(carpeta)
            speak("Abriendo carpeta de grabaciones.", interrupt=True)
        except Exception as e:
            notificar(f"Error al abrir carpeta de grabaciones: {e}")

    def _on_timer_sync(self, event):
        # Sincronización en segundo plano periódica
        if self.active_account_id:
            self._sincronizar_en_segundo_plano(self.active_account_id, manual=False)

    # --- AYUDA Y ACERCA DE ---
    def _on_ver_manual(self, event):
        from app.core.paths import get_data_path
        manual_p = get_data_path("docs/manual_es.md")
        if manual_p.exists():
            webbrowser.open(manual_p.as_uri())
        else:
            mostrar_info(self, "Manual de usuario no encontrado.")

    def _on_ver_teclas(self, event):
        from app.core.paths import get_data_path
        teclas_p = get_data_path("docs/teclas_es.md")
        if teclas_p.exists():
            webbrowser.open(teclas_p.as_uri())
        else:
            mostrar_info(self, "Documento de teclas no encontrado.")

    def _on_acerca_de(self, event):
        texto = (
            f"TelegramAccess\n"
            f"Versión: {APP_VERSION}\n"
            "Desarrollador / Adaptador: José Manuel Fernández Cortés\n"
            "Autor original de Social RSS: Héctor J. Benítez Corredera (xebolax)\n"
            "Licencia: GPL (Licencia Pública General de GNU)\n\n"
            "Este programa es la parte referente a Telegram extraída y ampliada a partir de Social RSS, "
            "creada y programada originalmente por su autor Héctor J. Benítez Corredera (xebolax).\n\n"
            "Social RSS gestiona de forma accesible múltiples redes sociales y fuentes de información:\n"
            "• Mastodon\n"
            "• Bluesky\n"
            "• RSS / Atom / Feeds de noticias\n"
            "• X (Twitter)\n"
            "• IRC\n"
            "• Matrix\n"
            "• Reddit\n"
            "• PeerTube / Canales de vídeo y podcast\n\n"
            "Última versión oficial (Latest Release) de Social RSS por xebolax:\n"
            "https://github.com/hxebolax/SocialRSS/releases/latest\n\n"
            "Mejoras e implementaciones de TelegramAccess:\n"
            "• Llamadas de voz y videollamadas nativas (tanto 1 a 1 como en grupos y canales).\n"
            "• Grabación integrada de llamadas de audio y vídeo (Alt+G) con guardado directo en MP3.\n"
            "• Selector interactivo de dispositivos de audio y cámara web (Alt+D).\n"
            "• Telegram Drive: almacenamiento ilimitado en tu nube privada personal con carpetas y papelera.\n"
            "• Totalmente optimizado para lectores de pantalla (NVDA, JAWS) y control 100 % por teclado."
        )
        mostrar_info(self, texto, "Acerca de TelegramAccess")

    def _on_buscar_actualizaciones(self, event=None, silencioso=False):
        """Comprueba en GitHub Releases si hay una versión nueva."""
        from app.services.updater import update_service as upd
        from app.ui.update_dialog import DialogoActualizacion
        import threading

        if not silencioso:
            speak(_("Comprobando actualizaciones de TelegramAccess..."), interrupt=True)

        def _hilo():
            try:
                info = upd.obtener_info_remota()
                if not info:
                    if not silencioso:
                        wx.CallAfter(
                            mostrar_info,
                            self,
                            _("No se pudo comprobar si hay actualizaciones en este momento.\n\n"
                              "Comprueba tu conexión a Internet o inténtalo más tarde."),
                            _("Actualizaciones")
                        )
                    return

                v_remota = info.get("version", "").strip()
                if upd.hay_actualizacion(v_remota):
                    notas = info.get("notes", "")
                    def _mostrar_dlg():
                        dlg = DialogoActualizacion(self, v_remota, notas)
                        dlg.ShowModal()
                        dlg.Destroy()
                    wx.CallAfter(_mostrar_dlg)
                else:
                    if not silencioso:
                        msg = _("TelegramAccess está actualizado.\n\nTienes instalada la versión más reciente ({0}).").format(APP_VERSION)
                        wx.CallAfter(mostrar_info, self, msg, _("Actualizaciones"))
                        speak(msg, interrupt=True)
            except Exception as e:
                log.error(f"Error comprobando actualizaciones: {e}")
                if not silencioso:
                    wx.CallAfter(
                        mostrar_info,
                        self,
                        _("Ocurrió un error al consultar las actualizaciones:\n\n{0}").format(e),
                        _("Error")
                    )

        threading.Thread(target=_hilo, daemon=True).start()

    def _lanzar_y_salir_actualizacion(self, script_path):
        """Guarda configuraciones, lanza el script de actualización y cierra el proceso."""
        import sys as _sys, os as _os
        try:
            config.save()
        except Exception:
            pass
        try:
            from app.core.database import db
            db.close()
        except Exception:
            pass
        try:
            self._lanzar_script_desacoplado(script_path)
        except Exception as e:
            log.error(f"No se pudo lanzar el script de actualización: {e}")
            mostrar_info(self, _("No se pudo iniciar la actualización automáticamente."))
            return

        log.info("Lanzado el script de actualización; cerrando aplicación.")
        try:
            from app.core.logger import vaciar
            vaciar()
            _sys.stdout.flush()
            _sys.stderr.flush()
        except Exception:
            pass
        _os._exit(0)

    def _lanzar_script_desacoplado(self, script_path):
        """Lanza el archivo .bat desacoplado para que sobreviva al cierre del proceso."""
        import subprocess
        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen(
            ["cmd", "/c", script_path],
            creationflags=CREATE_NO_WINDOW,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )

    def _on_preferencias(self, event):
        dlg = PreferencesDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            self._aplicar_atajos()
            self._cargar_listado_chats()
        dlg.Destroy()

    def _on_personalizar_teclas(self, event):
        dlg = ShortcutsEditorDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            self._aplicar_atajos()
        dlg.Destroy()

    def _on_menu_salir(self, event):
        self.Close()

    def _on_close(self, event):
        if config.get("general", "confirm_exit", True):
            if not confirmar(self, "¿Desea salir de TelegramAccess?"):
                event.Veto()
                return

        if self.timer_sync.IsRunning():
            self.timer_sync.Stop()

        # Detener clientes y audio
        try:
            player_service.detener()
            telegram_service.shutdown()
        except Exception:
            pass

        self.Destroy()
