"""Nadie importa un simulador: se pide el servicio con obtener("pagos") según settings.INTEGRACIONES."""
from django.conf import settings
from django.utils.module_loading import import_string

_instancias: dict[str, object] = {}


def obtener(nombre: str):
    if nombre not in _instancias:
        _instancias[nombre] = import_string(settings.INTEGRACIONES[nombre])()
    return _instancias[nombre]


def reemplazar(nombre: str, instancia) -> None:
    """Para las pruebas; restaurar() deshace la sustitución."""
    _instancias[nombre] = instancia


def restaurar() -> None:
    _instancias.clear()
