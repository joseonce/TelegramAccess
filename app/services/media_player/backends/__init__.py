# -*- coding: utf-8 -*-
"""Motores de reproducción multimedia."""

import logging
from app.core.plataforma import ES_WINDOWS
from .base_player_backend import BasePlayerBackend, BANDAS_EQ, VELOCIDAD_MIN, VELOCIDAD_MAX

log = logging.getLogger(__name__)


def crear_backend() -> BasePlayerBackend:
    if ES_WINDOWS:
        try:
            from .basskit_player_backend import BasskitPlayerBackend
            return BasskitPlayerBackend()
        except ImportError as e:
            log.warning(f"basskit no disponible: {e}. Usando backend de audio alternativo.")
            from .dummy_player_backend import DummyPlayerBackend
            return DummyPlayerBackend()

    try:
        from .gstreamer_player_backend import GStreamerPlayerBackend
        return GStreamerPlayerBackend()
    except Exception as e:
        log.warning(f"GStreamer no disponible: {e}. Usando backend mudo.")
        from .dummy_player_backend import DummyPlayerBackend
        return DummyPlayerBackend()
