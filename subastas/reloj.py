"""Nadie llama a timezone.now(): todo pasa por reloj.ahora(), y así las pruebas
del cierre y del plazo de pago controlan el tiempo con un RelojFijo."""
import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone
from django.utils.module_loading import import_string


class Reloj(ABC):
    @abstractmethod
    def ahora(self) -> datetime:
        """Siempre con zona horaria."""


class RelojSistema(Reloj):
    def ahora(self) -> datetime:
        return timezone.now()


class RelojFijo(Reloj):
    def __init__(self, instante: datetime):
        self._instante = instante

    def ahora(self) -> datetime:
        return self._instante

    def avanzar(self, **intervalo) -> None:
        self._instante += timedelta(**intervalo)


class RelojDemo(Reloj):
    """Reloj real más el desplazamiento de `manage.py adelantar_reloj`, para la demostración."""

    def ahora(self) -> datetime:
        return timezone.now() + timedelta(seconds=leer_desplazamiento())


def leer_desplazamiento() -> float:
    try:
        contenido = json.loads(settings.RELOJ_DEMO_ARCHIVO.read_text())
        return float(contenido["desplazamiento_segundos"])
    except (OSError, ValueError, KeyError, TypeError):
        return 0.0


def guardar_desplazamiento(segundos: float) -> None:
    settings.RELOJ_DEMO_ARCHIVO.parent.mkdir(parents=True, exist_ok=True)
    settings.RELOJ_DEMO_ARCHIVO.write_text(json.dumps({"desplazamiento_segundos": segundos}))


_reloj: Reloj | None = None


def ahora() -> datetime:
    global _reloj
    if _reloj is None:
        _reloj = import_string(settings.RELOJ)()
    return _reloj.ahora()


def establecer_reloj(reloj: Reloj | None) -> None:
    """Con None se vuelve al reloj de settings.RELOJ."""
    global _reloj
    _reloj = reloj


def formato(instante: datetime) -> str:
    return timezone.localtime(instante).strftime("%d/%m/%Y %H:%M")
