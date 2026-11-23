from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404

from .. import eventos, reloj
from ..mensajes import ErrorDeNegocio
from ..models import Articulo, MovimientoPuja, Puja, RevisionContenido, Rol, Sancion
from ..models.articulos import Decision
from ..reglas import cierre as reglas_cierre
from ..reglas import moderacion as reglas_moderacion
from ..reglas import sanciones as reglas_sanciones
from ..reglas.estados import ESTADOS_PREVIOS_A_PUBLICAR, EstadoArticulo, EstadoSubasta
from . import cuentas
from .transiciones import cambiar_estado_articulo, cambiar_estado_subasta


def _exigir_motivo(motivo: str) -> str:
    motivo = (motivo or "").strip()
    if not motivo:
        raise ErrorDeNegocio("ERR-49")
    return motivo


def exigir_motivo(motivo: str) -> str:
    """Las pantallas de confirmación piden el motivo antes de mostrar las consecuencias."""
    return _exigir_motivo(motivo)


def subasta_publicada(articulo):
    """CU-19: la subasta abierta que se cancelaría al retirar la publicación."""
    return articulo.subastas.filter(estado=EstadoSubasta.ABIERTA).first()


def pujas_que_retira_la_sancion(usuario, instante):
    """S-20: las pujas activas del sancionado en subastas que siguen abiertas."""
    return usuario.pujas.filter(
        estado=Puja.Estado.ACTIVA,
        subasta__estado=EstadoSubasta.ABIERTA,
        subasta__fecha_cierre__gt=instante,
    )


def _articulo(articulo_id: int) -> Articulo:
    return get_object_or_404(Articulo.objects.select_related("vendedor", "categoria"), pk=articulo_id)


def ultima_revision(articulo):
    return articulo.revisiones_contenido.order_by("-fecha", "-id").first()


def contenido_aprobado(articulo) -> bool:
    """S-10"""
    revision = ultima_revision(articulo)
    return reglas_moderacion.contenido_aprobado(
        ultima_decision=revision.decision if revision else None,
        fecha_decision=revision.fecha if revision else None,
        fecha_ultimo_envio=articulo.fecha_ultimo_envio,
    )


def exigir_contenido_aprobado(articulo) -> None:
    """S-10: lo llama el gestor antes de publicar (CU-07); lanza ERR-48."""
    revision = ultima_revision(articulo)
    reglas_moderacion.validar_contenido_aprobado(
        ultima_decision=revision.decision if revision else None,
        fecha_decision=revision.fecha if revision else None,
        fecha_ultimo_envio=articulo.fecha_ultimo_envio,
    )


def pendientes_de_revision():
    candidatos = Articulo.objects.filter(
        estado__in=ESTADOS_PREVIOS_A_PUBLICAR
    ).select_related("vendedor", "categoria")
    return [articulo for articulo in candidatos if not contenido_aprobado(articulo)]


# CU-18
@transaction.atomic
def aprobar_contenido(*, moderador, articulo_id: int) -> RevisionContenido:
    cuentas.exigir_rol(moderador, Rol.MODERADOR)
    articulo = _articulo(articulo_id)
    reglas_moderacion.validar_revisable(articulo.estado)
    return RevisionContenido.objects.create(
        articulo=articulo, moderador=moderador, decision=Decision.APROBADO, fecha=reloj.ahora()
    )


@transaction.atomic
def rechazar_contenido(*, moderador, articulo_id: int, motivo: str) -> RevisionContenido:
    """CU-18. Rechaza también la propuesta pendiente, para que no quede huérfana."""
    cuentas.exigir_rol(moderador, Rol.MODERADOR)
    motivo = _exigir_motivo(motivo)
    articulo = _articulo(articulo_id)
    reglas_moderacion.validar_revisable(articulo.estado)
    for propuesta in articulo.subastas.filter(estado=EstadoSubasta.PROPUESTA):
        cambiar_estado_subasta(propuesta, EstadoSubasta.RECHAZADA)
    cambiar_estado_articulo(articulo, EstadoArticulo.RECHAZADO)
    revision = RevisionContenido.objects.create(
        articulo=articulo,
        moderador=moderador,
        decision=Decision.RECHAZADO,
        motivo=motivo,
        fecha=reloj.ahora(),
    )
    eventos.publicar(eventos.CONTENIDO_RECHAZADO, articulo=articulo, motivo=motivo)
    return revision


def _retirar_pujas(pujas) -> list:
    """Devuelve los compradores afectados, para avisarles."""
    instante = reloj.ahora()
    compradores = []
    for puja in pujas:
        puja.estado = Puja.Estado.RETIRADA
        puja.fecha_actualizacion = instante
        puja.save(update_fields=["estado", "fecha_actualizacion"])
        MovimientoPuja.objects.create(
            puja=puja, tipo=MovimientoPuja.Tipo.RETIRO, monto_anterior=puja.monto, fecha=instante
        )
        compradores.append(puja.comprador)
    return compradores


# CU-19
@transaction.atomic
def retirar_publicacion(*, moderador, articulo_id: int, motivo: str):
    cuentas.exigir_rol(moderador, Rol.MODERADOR)
    motivo = _exigir_motivo(motivo)
    articulo = _articulo(articulo_id)
    subasta = subasta_publicada(articulo)
    if subasta is None or not reglas_cierre.esta_abierta(
        estado=subasta.estado, fecha_cierre=subasta.fecha_cierre, instante=reloj.ahora()
    ):
        raise ErrorDeNegocio("ERR-53")
    cambiar_estado_subasta(subasta, EstadoSubasta.CANCELADA)
    compradores = _retirar_pujas(
        subasta.pujas.filter(estado=Puja.Estado.ACTIVA).select_related("comprador")
    )
    cambiar_estado_articulo(articulo, EstadoArticulo.RETIRADO)
    RevisionContenido.objects.create(
        articulo=articulo,
        moderador=moderador,
        decision=Decision.RETIRADO,
        motivo=motivo,
        fecha=reloj.ahora(),
    )
    eventos.publicar(
        eventos.PUBLICACION_RETIRADA,
        articulo=articulo,
        subasta=subasta,
        motivo=motivo,
        compradores=compradores,
    )
    return subasta


def nivel_siguiente(usuario) -> int:
    """RN-16. Lanza ERR-47 si ya tiene la baja definitiva."""
    return reglas_sanciones.siguiente_nivel(usuario.sanciones.count())


def validar_sancion(usuario, nivel=None) -> int:
    """CU-20: las reglas que comparten la confirmación y la sanción, para que la pantalla no anuncie
    algo que después se rechaza. S-29: el personal no se sanciona (ERR-65). RN-16: `nivel` debe ser el
    siguiente (ERR-16) y no hay nivel tras la baja definitiva (ERR-47). Devuelve el nivel que se aplica."""
    if not (usuario.tiene_rol(Rol.VENDEDOR) or usuario.tiene_rol(Rol.COMPRADOR)):
        raise ErrorDeNegocio("ERR-65")
    previas = usuario.sanciones.count()
    nivel_esperado = reglas_sanciones.siguiente_nivel(previas)
    if nivel is not None:
        try:
            nivel = int(nivel)
        except (TypeError, ValueError):
            raise ErrorDeNegocio("ERR-16", esperado=nivel_esperado) from None
    reglas_sanciones.validar_nivel(
        nivel=nivel_esperado if nivel is None else nivel, sanciones_previas=previas
    )
    return nivel_esperado


@transaction.atomic
def sancionar(*, moderador, usuario_id: int, motivo: str, nivel: int | None = None) -> Sancion:
    """CU-20. `nivel` es el que el moderador vio en pantalla: si otro sancionó antes, ya no
    coincide y se rechaza con ERR-16."""
    cuentas.exigir_rol(moderador, Rol.MODERADOR)
    motivo = _exigir_motivo(motivo)
    usuario = get_object_or_404(get_user_model(), pk=usuario_id)
    nivel_esperado = validar_sancion(usuario, nivel)
    instante = reloj.ahora()
    sancion = Sancion.objects.create(
        usuario=usuario,
        moderador=moderador,
        nivel=nivel_esperado,
        motivo=motivo,
        fecha_inicio=instante,
        fecha_fin=reglas_sanciones.calcular_fecha_fin(nivel_esperado, instante),
    )
    # S-20
    _retirar_pujas(pujas_que_retira_la_sancion(usuario, instante).select_related("comprador"))
    eventos.publicar(eventos.SANCION_APLICADA, sancion=sancion)
    return sancion


def historial_de_sanciones(usuario):
    return usuario.sanciones.select_related("moderador").order_by("fecha_inicio", "id")
