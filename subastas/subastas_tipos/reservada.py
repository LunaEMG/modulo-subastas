from ..mensajes import ErrorDeNegocio
from .base import ParametrosSubasta, TipoSubasta


class SubastaReservada(TipoSubasta):
    """S-02"""

    codigo = "RESERVADA"
    nombre = "Con precio reservado"
    descripcion = (
        "Como la inglesa, pero el vendedor fija un precio reservado oculto: si la "
        "puja más alta no lo alcanza, el artículo no se vende."
    )
    parametros_propios = ("precio_reserva",)

    def _validar_coherencia(self, parametros: ParametrosSubasta) -> None:
        if parametros.precio_reserva < parametros.precio_salida:
            raise ErrorDeNegocio(
                "ERR-42", detalle="el precio reservado no puede ser menor al precio mínimo"
            )

    def reserva_alcanzada(self, subasta, precio_actual: int) -> bool:
        return precio_actual >= subasta.precio_reserva

    def puja_ganadora_al_cierre(self, subasta, puja_mas_alta):
        if puja_mas_alta is None or not self.reserva_alcanzada(subasta, puja_mas_alta.monto):
            return None
        return puja_mas_alta
