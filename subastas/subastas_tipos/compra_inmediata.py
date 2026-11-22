from datetime import datetime

from ..mensajes import ErrorDeNegocio
from .base import ParametrosSubasta, TipoSubasta


class SubastaCompraInmediata(TipoSubasta):
    """S-07. La descripción recuerda RN-11: quien compra de inmediato gana y tiene 3 días para pagar."""

    codigo = "COMPRA_INMEDIATA"
    nombre = "Con compra inmediata"
    descripcion = (
        "Como la inglesa, con un precio fijo adicional: quien lo acepta gana la "
        "subasta y tiene 3 días para pagarla."
    )
    parametros_propios = ("precio_compra_inmediata",)

    def _validar_coherencia(self, parametros: ParametrosSubasta) -> None:
        if parametros.precio_compra_inmediata <= parametros.precio_salida:
            raise ErrorDeNegocio(
                "ERR-42",
                detalle="el precio de compra inmediata debe ser mayor al precio mínimo",
            )

    def precio_en_el_acto(self, subasta, precio_actual: int, instante: datetime) -> int | None:
        # S-07: deja de ofrecerse cuando una puja iguala o supera el precio.
        if precio_actual >= subasta.precio_compra_inmediata:
            return None
        return subasta.precio_compra_inmediata
