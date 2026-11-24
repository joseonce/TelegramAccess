# -*- coding: utf-8 -*-
"""
Gestión y persistencia de configuraciones para TelegramAccess.
"""

import json
import logging
import os
import threading
from contextlib import contextmanager
from typing import Any, Dict
from .paths import get_data_path

log = logging.getLogger(__name__)

DEFAULTS: Dict[str, Any] = {
    "general": {
        "language": "es",
        "confirm_exit": True,
        "minimize_to_tray": False,
        "start_minimized": False,
        "theme": "oscuro",
        "font_size": 11,
        "relative_times": True,
        "spell_language": "es",
        "log_level": "INFO",
        "ready_sound": True,
        "ready_message": True,
        "service_order": ["telegram"],
        "servicios_desactivados": [],
    },
    "proxy": {
        "enabled": False,
        "type": "http",
        "server": "",
        "port": 8080,
        "user": "",
        "password": ""
    },
    "accessibility": {
        "screen_reader_mode": True,
        "enable_sounds": True,
        "speech_announcements": True,
        "modo_avisos": "voz",
        "toast_windows": False,
        "speech_delay_ms": 120,
        "verbal_confirmations": True,
        "sound_confirmations": True,
        "braille_announcements": True,
        "contador_en_vivo": True,
        "interfaz_invisible": False,
        "invisible_solo_oculta": False,
        "invisible_anunciar_posicion": True,
        "indicate_image": False,
        "indicate_audio": False,
        "direct_sound_in_dm_buffer": False,
        "auto_read_new": False,
        "show_screen_names": False,
        "hide_emojis": False,
        "hide_emojis_names": False,
        "expand_cw": False,
        "colnav_row_num": True,
        "colnav_col_header": True,
        "colnav_cell_value": True,
        "telegram_chat": "",
        "telegram_message": "",
        "telegram_miembro": "",
        "tgdrive_items": "",
    },
    "audio": {
        "sound_pack": "default",
        "volume": 0.8,
        "mute": False,
        "output_device": "",
        "mic_device": "",
        "mic_volume": 1.0,
        "event_sounds": {},
        "disabled_events": []
    },
    "media_player": {
        "backend": "basskit",
        "save_progress": True,
        "default_step_forward": 10.0,
        "default_step_backward": 10.0,
        "speed": 1.0,
        "volume": 0.8,
    },
    "ai": {
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "gemini_api_key": "",
        "gemini_api_keys": [],
        "openai_api_keys": [],
        "cache_responses": True,
        "prompt_image_description": "Describe esta imagen detalladamente en español para una persona ciega. Sé descriptivo pero conciso.",
    },
    "translation": {
        "provider": "google_api_free",
        "default_source": "auto",
        "default_target": "es",
        "auto_detect": True,
        "save_history": True,
        "copy_on_translate": True,
        "tts_playback": False
    },
    "telegram": {
        "update_interval": 60,
        "download_dir": "",
        "download_subdirs": True,
        "announce_new": True,
        "autoplay_voice": False,
        "mark_read_on_focus": True,
        "show_unread_marker": True,
        "show_unread_divider": True,
        "max_messages_per_chat": 0,
        "show_action_buttons": False,
        "hidden_buffers": [],
        "buffer_order": ["all", "unread", "private", "bot", "group", "supergroup", "channel", "contacts"]
    },
    "telegram_drive": {
        "carpeta_descargas": "",
        "max_simultaneas": 1,
        "tam_bloque": 1048576,
        "politica_conflicto": "preguntar",
        "retencion_papelera_dias": 30,
        "confirmar_borrado": True,
        "limpiar_temporales": True,
        "cifrado": False,
        "frecuencia_progreso_seg": 5
    },
    "shortcuts": {
        "mappings": {}
    }
}


def limite_render(red: str = "telegram", clave: str = "max_chats_list") -> int:
    return 500


class ConfigManager:
    def __init__(self, filename: str = "config/settings.json"):
        self.filepath = get_data_path(filename)
        self.lock = threading.Lock()
        self._batch_depth = 0
        self._dirty_in_batch = False
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self):
        with self.lock:
            import copy
            self._data = copy.deepcopy(DEFAULTS)
            if self.filepath.exists():
                try:
                    with open(self.filepath, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                    if isinstance(loaded, dict):
                        for section, values in loaded.items():
                            if isinstance(values, dict) and section in self._data:
                                self._data[section].update(values)
                            elif section not in self._data:
                                self._data[section] = values
                except Exception as e:
                    log.error(f"Error cargando settings.json: {e}")
            else:
                self._save_unlocked()

    def get(self, section: str, key: str, default: Any = None) -> Any:
        with self.lock:
            sec = self._data.get(section, {})
            if isinstance(sec, dict):
                return sec.get(key, default)
            return default

    def set(self, section: str, key: str, value: Any):
        with self.lock:
            if section not in self._data or not isinstance(self._data[section], dict):
                self._data[section] = {}
            self._data[section][key] = value
            if self._batch_depth > 0:
                self._dirty_in_batch = True
            else:
                self._save_unlocked()

    def save(self):
        with self.lock:
            self._save_unlocked()

    def _save_unlocked(self):
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.filepath.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4, ensure_ascii=False)
            if self.filepath.exists():
                os.replace(temp_path, self.filepath)
            else:
                temp_path.rename(self.filepath)
        except Exception as e:
            log.error(f"Error guardando settings.json: {e}")

    def begin_batch(self):
        with self.lock:
            self._batch_depth += 1

    def end_batch(self):
        with self.lock:
            self._batch_depth = max(0, self._batch_depth - 1)
            if self._batch_depth == 0 and self._dirty_in_batch:
                self._dirty_in_batch = False
                self._save_unlocked()

    @contextmanager
    def batch(self):
        with self.lock:
            self._batch_depth += 1
        try:
            yield
        finally:
            with self.lock:
                self._batch_depth -= 1
                if self._batch_depth == 0 and self._dirty_in_batch:
                    self._dirty_in_batch = False
                    self._save_unlocked()


config = ConfigManager()
