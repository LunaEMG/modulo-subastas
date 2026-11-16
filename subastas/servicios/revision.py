from django.db import transaction

from .. import eventos, integraciones, reloj
from ..mensajes import ErrorDeNegocio
from ..models import Articulo, RevisionGestor, Rol, Subasta, Valuacion
from ..models.articulos import Decision
from ..reglas import duracion as reglas_duracion
from ..reglas.estados import EstadoArticulo, EstadoSubasta
from . import consultas, cuentas, moderacion
from .transiciones import cambiar_estado_articulo, cambiar_estado_subasta


def _exigir_motivo(motivo: str) -> str:
    motivo = (motivo or "").strip()
    if not motivo:
        raise ErrorDeNegocio("ERR-49")
    return motivo


def _exigir_pendiente_de_revision(articulo: Articulo, nuevo_estado: str) -> None:
    """RN-03. La tabla de transiciones sola permitiría «aprobar» un artículo con propuesta pendiente."""
    if articulo.estado != EstadoArticulo.REGISTRADO:
        raise ErrorDeNegocio(
            "ERR-03",
            actual=EstadoArticulo(articulo.estado).label,
            nuevo=EstadoArticulo(nuevo_estado).label,
        )


def _registrar_revision(articulo, gestor, etapa, decision, observaciones) -> None:
    RevisionGestor.objects.create(
        articulo=articulo,
        gestor=gestor,
        etapa=etapa,
        decision=decision,
        observaciones=(observaciones or "").strip(),
    )


# CU-06
@transaction.atomic
def aprobar_articulo(*, gestor, articulo_id: int, observaciones: str = "") -> Articulo:
    cuentas.exigir_rol(gestor, Rol.GESTOR)
    articulo = Articulo.objects.select_related("categoria", "vendedor").get(pk=articulo_id)
    _exigir_pendiente_de_revision(articulo, EstadoArticulo.EN_VALUACION)
    if articulo.categoria.requiere_valuacion:
        cambiar_estado_articulo(articulo, EstadoArticulo.EN_VALUACION)
    else:
        # S-09: la aprobación del gestor avala el precio propuesto.
        cambiar_estado_articulo(articulo, EstadoArticulo.VALUADO)
    _registrar_revision(
        articulo, gestor, RevisionGestor.Etapa.DATOS, Decision.APROBADO, observaciones
    )
    eventos.publicar(eventos.ARTICULO_APROBADO, articulo=articulo)
    if articulo.estado == EstadoArticulo.EN_VALUACION:
        solicitar_valuacion(articulo)
    else:
        eventos.publicar(
            eventos.ARTICULO_LISTO, articulo=articulo, precio=articulo.costo_salida
        )
    return articulo


def solicitar_valuacion(articulo: Articulo) -> Valuacion:
    dictamen = integraciones.obtener("valuador").valuar(
        articulo_id=articulo.pk,
        categoria=articulo.categoria.nombre,
        descripcion=articulo.descripcion,
        anio=articulo.anio,
        precio_propuesto=articulo.costo_salida,
    )
    valuacion = Valuacion.objects.create(
        articulo=articulo,
        precio_propuesto=articulo.costo_salida,
        es_autentico=dictamen.es_autentico,
        precio_avalado=dictamen.precio_avalado,
        referencia_externa=dictamen.referencia,
    )
    try:
        # RN-04
        precio = consultas.precio_minimo_avalado(articulo)
    except ErrorDeNegocio:
        cambiar_estado_articulo(articulo, EstadoArticulo.NO_AVALADO)
        eventos.publicar(eventos.ARTICULO_NO_AVALADO, articulo=articulo)
    else:
        cambiar_estado_articulo(articulo, EstadoArticulo.VALUADO)
        eventos.publicar(eventos.ARTICULO_LISTO, articulo=articulo, precio=precio)
    return valuacion


# CU-06, flujo alterno
@transaction.atomic
def rechazar_articulo(*, gestor, articulo_id: int, motivo: str) -> Articulo:
    cuentas.exigir_rol(gestor, Rol.GESTOR)
    motivo = _exigir_motivo(motivo)
    articulo = Articulo.objects.select_related("vendedor").get(pk=articulo_id)
    _exigir_pendiente_de_revision(articulo, EstadoArticulo.RECHAZADO)
    cambiar_estado_articulo(articulo, EstadoArticulo.RECHAZADO)
    _registrar_revision(articulo, gestor, RevisionGestor.Etapa.DATOS, Decision.RECHAZADO, motivo)
    eventos.publicar(eventos.ARTICULO_RECHAZADO, articulo=articulo, motivo=motivo)
    return articulo


# CU-07
@transaction.atomic
def validar_duracion(*, gestor, subasta_id: int) -> Subasta:
    cuentas.exigir_rol(gestor, Rol.GESTOR)
    subasta = Subasta.objects.select_related("articulo__vendedor").get(pk=subasta_id)
    instante = reloj.ahora()
    if subasta.estado == EstadoSubasta.PROPUESTA:
        # S-10
        moderacion.exigir_contenido_aprobado(subasta.articulo)
    # Antes de tocar las fechas, para no dejarlas a medias si la transición se rechaza.
    cambiar_estado_subasta(subasta, EstadoSubasta.ABIERTA)
    subasta.fecha_inicio = instante
    subasta.fecha_cierre = reglas_duracion.calcular_fecha_cierre(instante, subasta.duracion_horas)
    subasta.save(update_fields=["fecha_inicio", "fecha_cierre"])
    cambiar_estado_articulo(subasta.articulo, EstadoArticulo.EN_SUBASTA)
    _registrar_revision(
        subasta.articulo, gestor, RevisionGestor.Etapa.DURACION, Decision.APROBADO, ""
    )
    eventos.publicar(eventos.SUBASTA_PUBLICADA, subasta=subasta)
    return subasta


# CU-07, flujo alterno
@transaction.atomic
def rechazar_duracion(*, gestor, subasta_id: int, motivo: str) -> Subasta:
    cuentas.exigir_rol(gestor, Rol.GESTOR)
    motivo = _exigir_motivo(motivo)
    subasta = Subasta.objects.select_related("articulo__vendedor").get(pk=subasta_id)
    cambiar_estado_subasta(subasta, EstadoSubasta.RECHAZADA)
    cambiar_estado_articulo(subasta.articulo, EstadoArticulo.VALUADO)
    _registrar_revision(
        subasta.articulo, gestor, RevisionGestor.Etapa.DURACION, Decision.RECHAZADO, motivo
    )
    eventos.publicar(eventos.PROPUESTA_RECHAZADA, subasta=subasta, motivo=motivo)
    return subasta
