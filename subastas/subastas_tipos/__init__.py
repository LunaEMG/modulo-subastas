"""RF-01"""
from ..mensajes import ErrorDeNegocio
from .base import ParametrosSubasta, TipoSubasta
from .compra_inmediata import SubastaCompraInmediata
from .holandesa import SubastaHolandesa
from .inglesa import SubastaInglesa
from .reservada import SubastaReservada

_TIPOS = {
    tipo.codigo: tipo
    for tipo in (
        SubastaInglesa(),
        SubastaReservada(),
        SubastaHolandesa(),
        SubastaCompraInmediata(),
    )
}


def obtener(codigo: str) -> TipoSubasta:
    try:
        return _TIPOS[codigo]
    except KeyError:
        raise ErrorDeNegocio("ERR-42", detalle=f"tipo de subasta desconocido «{codigo}»") from None


def todos() -> list[TipoSubasta]:
    return list(_TIPOS.values())


__all__ = ["ParametrosSubasta", "TipoSubasta", "obtener", "todos"]
