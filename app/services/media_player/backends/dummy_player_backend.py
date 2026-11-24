# -*- coding: utf-8 -*-
"""Backend mudo de reserva cuando no hay un motor de audio instalado."""

from .base_player_backend import BasePlayerBackend


class DummyPlayerBackend(BasePlayerBackend):
    def __init__(self):
        self._volumen = 0.8
        self._velocidad = 1.0
        self._posicion = 0.0
        self._duracion = 0.0
        self._estado = "detenido"

    def cargar(self, ruta_o_url: str) -> bool:
        return True

    def reproducir(self):
        self._estado = "reproduciendo"

    def pausar(self):
        self._estado = "pausado"

    def detener(self):
        self._estado = "detenido"
        self._posicion = 0.0

    def seek(self, segundos: float):
        self._posicion = max(0.0, segundos)

    def obtener_posicion(self) -> float:
        return self._posicion

    def obtener_duracion(self) -> float:
        return self._duracion

    def obtener_estado(self) -> str:
        return self._estado

    def establecer_volumen(self, vol: float):
        self._volumen = max(0.0, min(1.0, vol))

    def obtener_volumen(self) -> float:
        return self._volumen

    def establecer_velocidad(self, speed: float):
        self._velocidad = speed

    def obtener_velocidad(self) -> float:
        return self._velocidad

    def cerrar(self):
        self._estado = "detenido"

    def establecer_ecualizador(self, ganancias, preamp_db: float = 0.0):
        pass

    def liberar(self):
        self._estado = "detenido"
