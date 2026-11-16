"""RN-03. Estas tablas son el único lugar que dice qué cambio de estado se permite;
los servicios cambian estados solo a través de servicios/transiciones.py."""
from django.db.models import TextChoices

from ..mensajes import ErrorDeNegocio


class EstadoArticulo(TextChoices):
    REGISTRADO = "REGISTRADO", "Registrado, en revisión del gestor"
    RECHAZADO = "RECHAZADO", "Rechazado, pendiente de corrección"
    EN_VALUACION = "EN_VALUACION", "En valuación"
    NO_AVALADO = "NO_AVALADO", "No avalado por el valuador"
    VALUADO = "VALUADO", "Analizado, falta proponer la subasta"
    DURACION_PROPUESTA = "DURACION_PROPUESTA", "Subasta propuesta, en validación"
    EN_SUBASTA = "EN_SUBASTA", "En subasta"
    ADJUDICADO = "ADJUDICADO", "Adjudicado, pendiente de pago"
    VENDIDO = "VENDIDO", "Vendido"
    SIN_VENDER = "SIN_VENDER", "Sin vender"
    RETIRADO = "RETIRADO", "Retirado por moderación"


class EstadoSubasta(TextChoices):
    PROPUESTA = "PROPUESTA", "Propuesta por el vendedor"
    RECHAZADA = "RECHAZADA", "Rechazada por el gestor"
    ABIERTA = "ABIERTA", "Abierta"
    CERRADA_CON_GANADOR = "CERRADA_CON_GANADOR", "Cerrada con ganador"
    DESIERTA = "DESIERTA", "Desierta"
    CANCELADA = "CANCELADA", "Cancelada"


A = EstadoArticulo
S = EstadoSubasta

# RN-03
TRANSICIONES_ARTICULO: dict[str, frozenset[str]] = {
    # Directo a VALUADO cuando la categoría no pasa por valuador (S-09).
    A.REGISTRADO: frozenset({A.EN_VALUACION, A.VALUADO, A.RECHAZADO}),
    A.RECHAZADO: frozenset({A.REGISTRADO}),
    A.EN_VALUACION: frozenset({A.VALUADO, A.NO_AVALADO, A.RECHAZADO}),
    A.NO_AVALADO: frozenset(),
    A.VALUADO: frozenset({A.DURACION_PROPUESTA, A.RECHAZADO}),
    A.DURACION_PROPUESTA: frozenset({A.EN_SUBASTA, A.VALUADO, A.RECHAZADO}),
    A.EN_SUBASTA: frozenset({A.ADJUDICADO, A.SIN_VENDER, A.RETIRADO}),
    # EN_SUBASTA otra vez: resubasta por impago (RN-12).
    A.ADJUDICADO: frozenset({A.VENDIDO, A.EN_SUBASTA}),
    # S-16
    A.SIN_VENDER: frozenset({A.DURACION_PROPUESTA}),
    A.VENDIDO: frozenset(),
    A.RETIRADO: frozenset(),
}

TRANSICIONES_SUBASTA: dict[str, frozenset[str]] = {
    S.PROPUESTA: frozenset({S.ABIERTA, S.RECHAZADA}),
    S.ABIERTA: frozenset({S.CERRADA_CON_GANADOR, S.DESIERTA, S.CANCELADA}),
    S.RECHAZADA: frozenset(),
    S.CERRADA_CON_GANADOR: frozenset(),
    S.DESIERTA: frozenset(),
    S.CANCELADA: frozenset(),
}

# S-10: el moderador revisa el contenido en estos estados.
ESTADOS_PREVIOS_A_PUBLICAR = frozenset(
    {A.REGISTRADO, A.EN_VALUACION, A.VALUADO, A.DURACION_PROPUESTA}
)


def _validar(tabla: dict, enumeracion, actual: str, nuevo: str) -> None:
    if nuevo not in tabla.get(actual, frozenset()):
        raise ErrorDeNegocio(
            "ERR-03",
            actual=enumeracion(actual).label,
            nuevo=enumeracion(nuevo).label,
        )


# RN-03
def validar_transicion_articulo(actual: str, nuevo: str) -> None:
    _validar(TRANSICIONES_ARTICULO, EstadoArticulo, actual, nuevo)


# RN-03
def validar_transicion_subasta(actual: str, nuevo: str) -> None:
    _validar(TRANSICIONES_SUBASTA, EstadoSubasta, actual, nuevo)
