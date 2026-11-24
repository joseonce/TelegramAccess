# -*- coding: utf-8 -*-
"""
Gestor central de atajos de teclado para TelegramAccess.
"""

import wx
import logging
from typing import Dict, Tuple, List, Optional
from app.core.config_manager import config

log = logging.getLogger(__name__)

SEC_GENERALES = "Generales"
SEC_TELEGRAM = "Telegram"
SEC_REPRODUCTOR = "Reproductores de audio"

CATALOGO: List[Tuple[str, str, str, str]] = [
    ("actualizar_buffer", "Actualizar lista de chats", SEC_GENERALES, "F5"),
    ("buscar_global", "Búsqueda global de mensajes", SEC_GENERALES, "Ctrl+Shift+F"),
    ("leer_barra_estado", "Leer en voz la barra de estado", SEC_GENERALES, "Ctrl+Shift+B"),
    ("cuenta_siguiente", "Cuenta siguiente", SEC_GENERALES, "Ctrl+Tab"),
    ("cuenta_anterior", "Cuenta anterior", SEC_GENERALES, "Ctrl+Shift+Tab"),
    ("preferencias", "Abrir Preferencias", SEC_GENERALES, "Ctrl+P"),

    ("tg_abrir_chat", "Abrir conversación", SEC_TELEGRAM, "Enter"),
    ("tg_marcar_leido", "Marcar como leído o no leído", SEC_TELEGRAM, "Ctrl+M"),
    ("tg_fijar_chat", "Fijar o desfijar chat", SEC_TELEGRAM, "Ctrl+B"),
    ("tg_drive", "Telegram Drive (tu nube personal)", SEC_TELEGRAM, "Ctrl+Shift+U"),
    ("tg_buscar_chats", "Buscar usuarios, grupos y canales", SEC_TELEGRAM, "Ctrl+Shift+S"),
    ("tg_buscar_canales", "Buscar publicaciones de canales por hashtag", SEC_TELEGRAM, "Ctrl+Shift+K"),
    ("tg_guardados", "Abrir chat de Mensajes guardados", SEC_TELEGRAM, "Ctrl+Shift+G"),
    ("tg_mi_perfil", "Ver y editar mi perfil", SEC_TELEGRAM, "Ctrl+Shift+P"),
    ("tg_resumen", "Resumen de Telegram", SEC_TELEGRAM, "Ctrl+Shift+T"),
    ("insertar_fragmento", "Insertar un fragmento de texto al redactar", SEC_GENERALES, "Ctrl+Shift+J"),

    ("media_retroceder", "Retroceder en la reproducción", SEC_REPRODUCTOR, "F1"),
    ("media_play_pausa", "Reproducir o pausar", SEC_REPRODUCTOR, "F2"),
    ("media_avanzar", "Avanzar en la reproducción", SEC_REPRODUCTOR, "F3"),
    ("media_detener", "Detener la reproducción", SEC_REPRODUCTOR, "F4"),
    ("media_bajar_volumen", "Bajar el volumen", SEC_REPRODUCTOR, "F9"),
    ("media_subir_volumen", "Subir el volumen", SEC_REPRODUCTOR, "F10"),
    ("media_bajar_velocidad", "Reducir la velocidad", SEC_REPRODUCTOR, "F7"),
    ("media_subir_velocidad", "Aumentar la velocidad", SEC_REPRODUCTOR, "F8"),
]

ACCIONES_REPRODUCTOR: List[str] = [acc for acc, _et, sec, _t in CATALOGO if sec == SEC_REPRODUCTOR]

DEFAULT_SHORTCUTS: Dict[str, str] = {acc: tecla for acc, _et, _sec, tecla in CATALOGO}
EXTRA_DEFAULTS: Dict[str, str] = {
    "ayuda_contexto": "Ctrl+H",
}
DEFAULT_SHORTCUTS.update(EXTRA_DEFAULTS)

_ETIQUETAS: Dict[str, str] = {acc: et for acc, et, _sec, _tecla in CATALOGO}
_SECCION: Dict[str, str] = {acc: sec for acc, _et, sec, _tecla in CATALOGO}

TECLAS_RESERVADAS = {
    "alt+1", "alt+2", "alt+3", "alt+4", "alt+5", "alt+6", "alt+7", "alt+8", "alt+9",
    "space", "ctrl+space", "left", "right", "up", "down",
    "ctrl+q", "alt+f4"
}

_MOD_LEGIBLE = {"ctrl": "Ctrl", "shift": "Mayús", "alt": "Alt"}
_TECLA_LEGIBLE = {
    "SPACE": "Espacio", "RIGHT": "Flecha derecha", "LEFT": "Flecha izquierda",
    "UP": "Flecha arriba", "DOWN": "Flecha abajo", "ENTER": "Intro", "RETURN": "Intro",
    "ESCAPE": "Escape", "ESC": "Escape", "TAB": "Tabulador",
}


class ShortcutManager:
    def __init__(self):
        self._shortcuts: Dict[str, str] = {}
        self._cache_media: Optional[Dict[Tuple[int, int], str]] = None
        self.load()

    def load(self):
        self._cache_media = None
        custom = config.get("shortcuts", "mappings", {})
        self._shortcuts = dict(DEFAULT_SHORTCUTS)
        if isinstance(custom, dict):
            for k, v in custom.items():
                if k in DEFAULT_SHORTCUTS and isinstance(v, str) and v:
                    self._shortcuts[k] = v

    def save(self):
        self._cache_media = None
        custom = {k: v for k, v in self._shortcuts.items()
                  if DEFAULT_SHORTCUTS.get(k) != v}
        config.set("shortcuts", "mappings", custom)

    def obtener_atajo(self, action: str) -> str:
        return self._shortcuts.get(action, DEFAULT_SHORTCUTS.get(action, ""))

    def es_personalizado(self, action: str) -> bool:
        return self.obtener_atajo(action) != DEFAULT_SHORTCUTS.get(action, "")

    def etiqueta(self, action: str) -> str:
        return _ETIQUETAS.get(action, action)

    def secciones(self) -> List[str]:
        return [SEC_GENERALES, SEC_TELEGRAM, SEC_REPRODUCTOR]

    def acciones_de(self, seccion: str) -> List[str]:
        return [acc for acc, _et, sec, _t in CATALOGO if sec == seccion]

    def combo_legible(self, action: str) -> str:
        return self.combo_a_legible(self.obtener_atajo(action))

    @staticmethod
    def combo_a_legible(combo: str) -> str:
        if not combo:
            return ""
        partes = combo.split("+")
        mods = [_MOD_LEGIBLE.get(p.lower(), p) for p in partes[:-1]]
        tecla = partes[-1]
        tecla_leg = _TECLA_LEGIBLE.get(tecla.upper(), tecla.upper() if len(tecla) == 1 else tecla)
        return "+".join(mods + [tecla_leg])

    def conflicto(self, action: str, key_combo: str) -> Optional[str]:
        objetivo = key_combo.lower()
        for acc in DEFAULT_SHORTCUTS:
            if acc != action and self.obtener_atajo(acc).lower() == objetivo:
                return acc
        return None

    def es_reservada(self, key_combo: str) -> bool:
        return key_combo.lower() in TECLAS_RESERVADAS

    @staticmethod
    def es_accion_reproductor(action: str) -> bool:
        return action in ACCIONES_REPRODUCTOR

    @staticmethod
    def combo_valido_reproductor(key_combo: str) -> bool:
        combo = (key_combo or "").strip()
        if not combo:
            return False
        partes = combo.split("+")
        if len(partes) > 1:
            return True
        tecla = partes[0].upper()
        return tecla.startswith("F") and tecla[1:].isdigit() and 1 <= int(tecla[1:]) <= 12

    def _mapa_reproductor(self) -> Dict[Tuple[int, int], str]:
        cache = getattr(self, "_cache_media", None)
        if cache is not None:
            return cache
        cache = {}
        for accion in ACCIONES_REPRODUCTOR:
            tpl = self.combo_to_wx(self.obtener_atajo(accion), 0)
            if not tpl:
                continue
            flags, keycode, _mid = tpl
            mods = 0
            if flags & wx.ACCEL_CTRL:
                mods |= wx.MOD_CONTROL
            if flags & wx.ACCEL_SHIFT:
                mods |= wx.MOD_SHIFT
            if flags & wx.ACCEL_ALT:
                mods |= wx.MOD_ALT
            cache[(mods, keycode)] = accion
        self._cache_media = cache
        return cache

    def accion_reproductor_de_evento(self, event) -> Optional[str]:
        mapa = self._mapa_reproductor()
        if not mapa:
            return None
        kc = event.GetKeyCode()
        mods = 0
        if event.ControlDown():
            mods |= wx.MOD_CONTROL
        if event.ShiftDown():
            mods |= wx.MOD_SHIFT
        if event.AltDown():
            mods |= wx.MOD_ALT
        return mapa.get((mods, kc))

    @staticmethod
    def combo_to_wx(combo: str, id_accel: int) -> Optional[Tuple[int, int, int]]:
        if not combo:
            return None
        partes = combo.split("+")
        mods = partes[:-1]
        tecla = partes[-1].strip()

        flags = wx.ACCEL_NORMAL
        for m in mods:
            ml = m.strip().lower()
            if ml in ("ctrl", "control"):
                flags |= wx.ACCEL_CTRL
            elif ml in ("shift", "mayus", "mayús"):
                flags |= wx.ACCEL_SHIFT
            elif ml == "alt":
                flags |= wx.ACCEL_ALT

        tu = tecla.upper()
        keycode = None
        if len(tecla) == 1:
            keycode = ord(tecla.upper())
        elif tu.startswith("F") and tu[1:].isdigit() and 1 <= int(tu[1:]) <= 24:
            f_num = int(tu[1:])
            keycode = getattr(wx, f"WXK_F{f_num}", None)
        else:
            mapa_especiales = {
                "TAB": wx.WXK_TAB, "ENTER": wx.WXK_RETURN, "RETURN": wx.WXK_RETURN,
                "ESC": wx.WXK_ESCAPE, "ESCAPE": wx.WXK_ESCAPE, "SPACE": wx.WXK_SPACE,
                "DELETE": wx.WXK_DELETE, "SUPR": wx.WXK_DELETE, "BACK": wx.WXK_BACK,
                "HOME": wx.WXK_HOME, "END": wx.WXK_END, "PAGEUP": wx.WXK_PAGEUP,
                "PAGEDOWN": wx.WXK_PAGEDOWN, "LEFT": wx.WXK_LEFT, "RIGHT": wx.WXK_RIGHT,
                "UP": wx.WXK_UP, "DOWN": wx.WXK_DOWN, "INSERT": wx.WXK_INSERT,
            }
            keycode = mapa_especiales.get(tu)

        if keycode is None:
            return None
        return (flags, keycode, id_accel)

    def establecer_atajo(self, action: str, key_combo: str):
        self._shortcuts[action] = key_combo
        self.save()

    def restaurar_defecto(self, action: str):
        if action in DEFAULT_SHORTCUTS:
            self._shortcuts[action] = DEFAULT_SHORTCUTS[action]
            self.save()

    def restaurar_seccion(self, seccion: str):
        for acc in self.acciones_de(seccion):
            if acc in DEFAULT_SHORTCUTS:
                self._shortcuts[acc] = DEFAULT_SHORTCUTS[acc]
        self.save()

    def restaurar_todo(self):
        self._shortcuts = dict(DEFAULT_SHORTCUTS)
        self.save()

    def construir_tabla(self, ventana: wx.Window, mapa_handlers: Dict[str, callable]) -> wx.AcceleratorTable:
        entradas = []
        for accion, handler in mapa_handlers.items():
            combo = self.obtener_atajo(accion)
            if not combo:
                continue
            item_id = wx.NewIdRef()
            tpl = self.combo_to_wx(combo, item_id)
            if tpl:
                flags, keycode, mid = tpl
                entradas.append(wx.AcceleratorEntry(flags, keycode, mid))
                ventana.Bind(wx.EVT_MENU, handler, id=mid)
        return wx.AcceleratorTable(entradas)

    def evento_coincide(self, action: str, event) -> bool:
        """True si el evento de teclado coincide con la tecla configurada para 'action'. Para atajos
        que NO van por la tabla de aceleradores sino por un EVT_CHAR_HOOK (p. ej. en los campos de
        redacción), de modo que respeten la tecla que el usuario haya puesto en el editor."""
        try:
            combo = self.obtener_atajo(action)
            if not combo:
                return False
            tpl = self.combo_to_wx(combo, 0)
            if not tpl:
                return False
            flags, keycode, _mid = tpl
            mods = 0
            if flags & wx.ACCEL_CTRL:
                mods |= wx.MOD_CONTROL
            if flags & wx.ACCEL_SHIFT:
                mods |= wx.MOD_SHIFT
            if flags & wx.ACCEL_ALT:
                mods |= wx.MOD_ALT
            return event.GetModifiers() == mods and event.GetKeyCode() == keycode
        except Exception:
            return False


shortcut_manager = ShortcutManager()
