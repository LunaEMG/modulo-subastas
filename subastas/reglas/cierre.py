from datetime import datetime

from .. import reloj
from ..mensajes import ErrorDeNegocio
from .estados import EstadoSubasta


def esta_abierta(*, estado: str, fecha_cierre: datetime | None, instante: datetime) -> bool:
    return estado == EstadoSubasta.ABIERTA and fecha_cierre is not None and instante < fecha_cierre


# RN-09
def validar_llego_el_cierre(*, fecha_cierre: datetime, instante: datetime) -> None:
    if instante < fecha_cierre:
        raise ErrorDeNegocio("ERR-09", cierre=reloj.formato(fecha_cierre))


def determinar_puja_ganadora(pujas_activas):
    """RN-09. Devuelve None si no hay pujas; no hay empates porque RN-06 exige superar el precio."""
    return max(pujas_activas, key=lambda puja: puja.monto, default=None)
