"""S-10: un supuesto, no una regla del enunciado (ver SUPUESTOS.md)."""
from datetime import datetime

from ..mensajes import ErrorDeNegocio
from .estados import ESTADOS_PREVIOS_A_PUBLICAR


def validar_revisable(estado_articulo: str) -> None:
    if estado_articulo not in ESTADOS_PREVIOS_A_PUBLICAR:
        raise ErrorDeNegocio("ERR-64")


def contenido_aprobado(
    *, ultima_decision: str | None, fecha_decision: datetime | None, fecha_ultimo_envio: datetime
) -> bool:
    """Una aprobación anterior a la última corrección del vendedor ya no cubre el contenido."""
    return (
        ultima_decision == "APROBADO"
        and fecha_decision is not None
        and fecha_decision >= fecha_ultimo_envio
    )


def validar_contenido_aprobado(**datos) -> None:
    if not contenido_aprobado(**datos):
        raise ErrorDeNegocio("ERR-48")
