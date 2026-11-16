from abc import ABC
from dataclasses import dataclass
from datetime import datetime

from ..mensajes import ErrorDeNegocio
from ..reglas import pujas as reglas_pujas


@dataclass(frozen=True)
class ParametrosSubasta:
    precio_salida: int
    precio_reserva: int | None = None
    precio_compra_inmediata: int | None = None
    holandesa_precio_inicial: int | None = None
    holandesa_decremento: int | None = None
    holandesa_intervalo_min: int | None = None


ETIQUETAS = {
    "precio_reserva": "precio reservado",
    "precio_compra_inmediata": "precio de compra inmediata",
    "holandesa_precio_inicial": "precio inicial",
    "holandesa_decremento": "decremento",
    "holandesa_intervalo_min": "intervalo en minutos",
}


class TipoSubasta(ABC):
    codigo: str
    nombre: str
    descripcion: str
    # Los parámetros que no estén aquí deben venir vacíos.
    parametros_propios: tuple[str, ...] = ()
    admite_pujas: bool = True

    def validar_parametros(self, parametros: ParametrosSubasta) -> None:
        for campo, etiqueta in ETIQUETAS.items():
            valor = getattr(parametros, campo)
            if campo in self.parametros_propios:
                if valor is None or valor <= 0:
                    raise ErrorDeNegocio("ERR-42", detalle=f"falta el {etiqueta}")
            elif valor is not None:
                raise ErrorDeNegocio(
                    "ERR-42", detalle=f"el {etiqueta} no aplica a una subasta {self.nombre.lower()}"
                )
        self._validar_coherencia(parametros)

    def _validar_coherencia(self, parametros: ParametrosSubasta) -> None:
        """Punto de extensión: cada tipo agrega aquí sus propias validaciones."""

    def precio_actual(self, subasta, monto_mas_alto: int | None, instante: datetime) -> int:
        return reglas_pujas.precio_vigente(subasta.precio_salida, monto_mas_alto)

    def puja_ganadora_al_cierre(self, subasta, puja_mas_alta):
        """Recibe la puja más alta (RN-09); devuelve None si la subasta queda desierta."""
        return puja_mas_alta

    def precio_en_el_acto(self, subasta, precio_actual: int, instante: datetime) -> int | None:
        """Precio para quedarse el artículo en el acto (CU-09, CU-12), o None si no está disponible."""
        return None
