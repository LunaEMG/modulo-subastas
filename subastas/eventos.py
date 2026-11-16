"""Observer: los servicios publican lo que ocurrió sin saber quién avisa ni por qué canal."""
from collections import defaultdict
from collections.abc import Callable

ARTICULO_APROBADO = "articulo_aprobado"
ARTICULO_RECHAZADO = "articulo_rechazado"
ARTICULO_LISTO = "articulo_listo"
ARTICULO_NO_AVALADO = "articulo_no_avalado"
SUBASTA_PUBLICADA = "subasta_publicada"
PROPUESTA_RECHAZADA = "propuesta_rechazada"
PUJA_SUPERADA = "puja_superada"
SUBASTA_ADJUDICADA = "subasta_adjudicada"
SUBASTA_DESIERTA = "subasta_desierta"
PAGO_RECIBIDO = "pago_recibido"
PAGO_VENCIDO = "pago_vencido"
CONTENIDO_RECHAZADO = "contenido_rechazado"
PUBLICACION_RETIRADA = "publicacion_retirada"
SANCION_APLICADA = "sancion_aplicada"

_suscriptores: dict[str, list[Callable]] = defaultdict(list)


def suscribir(evento: str, funcion: Callable) -> None:
    if funcion not in _suscriptores[evento]:
        _suscriptores[evento].append(funcion)


def publicar(evento: str, **datos) -> None:
    for funcion in _suscriptores[evento]:
        funcion(**datos)
