from datetime import datetime, timedelta

from ..mensajes import ErrorDeNegocio
from .base import ParametrosSubasta, TipoSubasta


class SubastaHolandesa(TipoSubasta):
    """S-01"""

    codigo = "HOLANDESA"
    nombre = "Holandesa"
    descripcion = (
        "El precio empieza alto y baja cada cierto tiempo hasta el precio mínimo; "
        "gana el primer comprador que acepta el precio vigente."
    )
    parametros_propios = (
        "holandesa_precio_inicial",
        "holandesa_decremento",
        "holandesa_intervalo_min",
    )
    admite_pujas = False

    def _validar_coherencia(self, parametros: ParametrosSubasta) -> None:
        if parametros.holandesa_precio_inicial <= parametros.precio_salida:
            raise ErrorDeNegocio(
                "ERR-42", detalle="el precio inicial debe ser mayor al precio mínimo"
            )

    def precio_actual(self, subasta, monto_mas_alto: int | None, instante: datetime) -> int:
        if monto_mas_alto is not None:
            return monto_mas_alto
        return self._precio_descendente(subasta, instante)

    def precio_en_el_acto(self, subasta, precio_actual: int, instante: datetime) -> int | None:
        return self._precio_descendente(subasta, instante)

    def proxima_bajada(self, subasta, instante: datetime):
        """None cuando el precio ya llegó al mínimo."""
        if self._precio_descendente(subasta, instante) <= subasta.precio_salida:
            return None
        intervalo = subasta.holandesa_intervalo_min * 60
        transcurrido = max((instante - subasta.fecha_inicio).total_seconds(), 0)
        bajadas = int(transcurrido // intervalo) + 1
        return subasta.fecha_inicio + timedelta(seconds=bajadas * intervalo)

    def puja_ganadora_al_cierre(self, subasta, puja_mas_alta):
        # Quien acepta gana en el acto, así que llegar al cierre significa que nadie aceptó.
        return puja_mas_alta

    @staticmethod
    def _precio_descendente(subasta, instante: datetime) -> int:
        transcurrido = max((instante - subasta.fecha_inicio).total_seconds(), 0)
        bajadas = int(transcurrido // (subasta.holandesa_intervalo_min * 60))
        precio = subasta.holandesa_precio_inicial - bajadas * subasta.holandesa_decremento
        return max(precio, subasta.precio_salida)
