from datetime import datetime, timedelta

from django.db.models import TextChoices

from .. import reloj
from ..mensajes import ErrorDeNegocio

# RN-11
DIAS_PARA_PAGAR = 3


class EstadoAdjudicacion(TextChoices):
    PENDIENTE_PAGO = "PENDIENTE_PAGO", "Pendiente de pago"
    PAGADA = "PAGADA", "Pagada"
    VENCIDA = "VENCIDA", "Vencida por falta de pago"


def calcular_fecha_limite_pago(fecha_adjudicacion: datetime) -> datetime:
    """RN-11: el plazo corre desde la adjudicación, no desde el aviso."""
    return fecha_adjudicacion + timedelta(days=DIAS_PARA_PAGAR)


def plazo_vencido(*, fecha_limite_pago: datetime, instante: datetime) -> bool:
    return instante > fecha_limite_pago


# RN-11: el último instante del plazo todavía es válido.
def validar_pago_en_plazo(*, fecha_limite_pago: datetime, instante: datetime) -> None:
    if plazo_vencido(fecha_limite_pago=fecha_limite_pago, instante=instante):
        raise ErrorDeNegocio(
            "ERR-11", dias=DIAS_PARA_PAGAR, limite=reloj.formato(fecha_limite_pago)
        )


# RN-12
def validar_resubasta(*, estado: str, fecha_limite_pago: datetime, instante: datetime) -> None:
    sin_pagar = estado == EstadoAdjudicacion.PENDIENTE_PAGO
    if not (sin_pagar and plazo_vencido(fecha_limite_pago=fecha_limite_pago, instante=instante)):
        raise ErrorDeNegocio("ERR-12")
