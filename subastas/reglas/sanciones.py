from datetime import datetime, timedelta

from ..mensajes import ErrorDeNegocio

NIVEL_SEMANAS = 1
NIVEL_MESES = 2
NIVEL_BAJA_DEFINITIVA = 3

# S-06. None es baja definitiva.
DURACION_POR_NIVEL: dict[int, timedelta | None] = {
    NIVEL_SEMANAS: timedelta(days=14),
    NIVEL_MESES: timedelta(days=90),
    NIVEL_BAJA_DEFINITIVA: None,
}

DESCRIPCION_POR_NIVEL = {
    NIVEL_SEMANAS: "suspensión de 14 días",
    NIVEL_MESES: "suspensión de 90 días",
    NIVEL_BAJA_DEFINITIVA: "baja definitiva",
}


def siguiente_nivel(sanciones_previas: int) -> int:
    """RN-16. Lanza ERR-47 si ya tiene la baja definitiva."""
    if sanciones_previas >= NIVEL_BAJA_DEFINITIVA:
        raise ErrorDeNegocio("ERR-47")
    return sanciones_previas + 1


# RN-16
def validar_nivel(*, nivel: int, sanciones_previas: int) -> None:
    esperado = siguiente_nivel(sanciones_previas)
    if nivel != esperado:
        raise ErrorDeNegocio("ERR-16", esperado=esperado)


def calcular_fecha_fin(nivel: int, fecha_inicio: datetime) -> datetime | None:
    duracion = DURACION_POR_NIVEL[nivel]
    return None if duracion is None else fecha_inicio + duracion


def esta_vigente(*, fecha_inicio: datetime, fecha_fin: datetime | None, instante: datetime) -> bool:
    return fecha_inicio <= instante and (fecha_fin is None or instante < fecha_fin)
