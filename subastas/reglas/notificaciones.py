from datetime import datetime

from django.db.models import TextChoices

from .. import reloj
from ..mensajes import ErrorDeNegocio
from .pagos import DIAS_PARA_PAGAR


class Canal(TextChoices):
    APP = "APP", "Dentro de la aplicación"
    CORREO = "CORREO", "Correo electrónico"


# RN-10
CANALES_AVISO_GANADOR = (Canal.APP, Canal.CORREO)
MENSAJE_AVISO_GANADOR = "MSG-37"


def datos_aviso_ganador(
    *, hay_adjudicacion: bool, articulo: str, precio_final: int, fecha_limite_pago: datetime
) -> dict:
    """RN-10. Lanza ERR-10 si la subasta no cerró con ganador."""
    if not hay_adjudicacion:
        raise ErrorDeNegocio("ERR-10")
    return {
        "articulo": articulo,
        "precio": precio_final,
        "dias": DIAS_PARA_PAGAR,
        "limite": reloj.formato(fecha_limite_pago),
    }
