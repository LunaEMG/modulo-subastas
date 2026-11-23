from datetime import datetime, timedelta

from ..mensajes import ErrorDeNegocio
from .estados import EstadoArticulo

# S-14
DURACION_MINIMA_HORAS = 1
DURACION_MAXIMA_HORAS = 30 * 24
# S-38: el intervalo de la holandesa no pasa de la duración máxima; uno mayor nunca bajaría el precio.
INTERVALO_HOLANDESA_MAXIMO_MIN = DURACION_MAXIMA_HORAS * 60

# El artículo ya fue «recibido y analizado» cuando está en alguno de estos estados.
ESTADOS_ANALIZADOS = frozenset({EstadoArticulo.VALUADO, EstadoArticulo.SIN_VENDER})


def validar_propuesta_duracion(*, estado_articulo: str, duracion_horas: int) -> None:
    """RN-05. La otra mitad de la regla (que el gestor valide) la garantiza RN-03."""
    if estado_articulo not in ESTADOS_ANALIZADOS:
        raise ErrorDeNegocio("ERR-05")
    if not DURACION_MINIMA_HORAS <= duracion_horas <= DURACION_MAXIMA_HORAS:
        raise ErrorDeNegocio(
            "ERR-40", minimo=DURACION_MINIMA_HORAS, maximo=DURACION_MAXIMA_HORAS
        )


def calcular_fecha_cierre(fecha_inicio: datetime, duracion_horas: int) -> datetime:
    return fecha_inicio + timedelta(hours=duracion_horas)
