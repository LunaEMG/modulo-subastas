import logging

from django.db import transaction
from django.shortcuts import get_object_or_404

from .. import eventos, integraciones, reloj
from .. import subastas_tipos as tipos
from ..mensajes import ErrorDeNegocio
from ..models import Adjudicacion, Puja, Subasta
from ..reglas import cierre as reglas_cierre
from ..reglas import dinero as reglas_dinero
from ..reglas import duracion as reglas_duracion
from ..reglas import pagos as reglas_pagos
from ..reglas.estados import EstadoArticulo, EstadoSubasta
from ..reglas.pagos import EstadoAdjudicacion
from .transiciones import cambiar_estado_articulo, cambiar_estado_subasta

registro = logging.getLogger(__name__)


def adjudicar(subasta, puja) -> Adjudicacion:
    """RN-09, RN-11, RN-14. Debe llamarse dentro de una transacción."""
    instante = reloj.ahora()
    cambiar_estado_subasta(subasta, EstadoSubasta.CERRADA_CON_GANADOR)
    adjudicacion = Adjudicacion.objects.create(
        subasta=subasta,
        ganador=puja.comprador,
        precio_final=puja.monto,
        comision=reglas_dinero.calcular_comision(puja.monto),
        fecha_limite_pago=reglas_pagos.calcular_fecha_limite_pago(instante),
        fecha=instante,
    )
    cambiar_estado_articulo(subasta.articulo, EstadoArticulo.ADJUDICADO)
    eventos.publicar(eventos.SUBASTA_ADJUDICADA, adjudicacion=adjudicacion)
    return adjudicacion


@transaction.atomic
def cerrar_subasta(subasta_id: int):
    """CU-15. Devuelve None si la subasta quedó desierta."""
    subasta = Subasta.objects.select_related("articulo__vendedor").get(pk=subasta_id)
    if subasta.estado != EstadoSubasta.ABIERTA:
        raise ErrorDeNegocio("ERR-36")
    # RN-09
    reglas_cierre.validar_llego_el_cierre(fecha_cierre=subasta.fecha_cierre, instante=reloj.ahora())
    activas = list(subasta.pujas.filter(estado=Puja.Estado.ACTIVA).select_related("comprador"))
    puja_mas_alta = reglas_cierre.determinar_puja_ganadora(activas)
    # En la reservada, la más alta gana solo si alcanza la reserva.
    ganadora = tipos.obtener(subasta.tipo).puja_ganadora_al_cierre(subasta, puja_mas_alta)
    if ganadora is not None:
        return adjudicar(subasta, ganadora)
    cambiar_estado_subasta(subasta, EstadoSubasta.DESIERTA)
    # S-16
    cambiar_estado_articulo(subasta.articulo, EstadoArticulo.SIN_VENDER)
    eventos.publicar(eventos.SUBASTA_DESIERTA, subasta=subasta)
    return None


# CU-14
@transaction.atomic
def pagar(*, comprador, adjudicacion_id: int) -> Adjudicacion:
    adjudicacion = get_object_or_404(
        Adjudicacion.objects.select_related("subasta__articulo__vendedor"), pk=adjudicacion_id
    )
    if adjudicacion.ganador_id != comprador.pk:
        raise ErrorDeNegocio("ERR-43")
    if adjudicacion.estado != EstadoAdjudicacion.PENDIENTE_PAGO:
        raise ErrorDeNegocio("ERR-44")
    # RN-11
    reglas_pagos.validar_pago_en_plazo(
        fecha_limite_pago=adjudicacion.fecha_limite_pago, instante=reloj.ahora()
    )
    articulo = adjudicacion.subasta.articulo
    resultado = integraciones.obtener("pagos").cobrar(
        comprador_id=comprador.pk,
        monto_fichas=adjudicacion.precio_final,
        concepto=f"Subasta {adjudicacion.subasta_id}: {articulo.titulo}",
    )
    if not resultado.aprobado:
        raise ErrorDeNegocio("ERR-45")
    adjudicacion.estado = EstadoAdjudicacion.PAGADA
    adjudicacion.referencia_pago = resultado.referencia
    # RF-03
    adjudicacion.referencia_envio = integraciones.obtener("logistica").solicitar_recoleccion(
        adjudicacion_id=adjudicacion.pk,
        vendedor_id=articulo.vendedor_id,
        comprador_id=comprador.pk,
    )
    adjudicacion.save(update_fields=["estado", "referencia_pago", "referencia_envio"])
    cambiar_estado_articulo(articulo, EstadoArticulo.VENDIDO)
    eventos.publicar(eventos.PAGO_RECIBIDO, adjudicacion=adjudicacion)
    return adjudicacion


@transaction.atomic
def vencer_pago_y_resubastar(adjudicacion_id: int) -> Subasta:
    """CU-16. S-08: misma configuración, sin repetir revisión, valuación ni validación."""
    adjudicacion = Adjudicacion.objects.select_related("subasta__articulo__vendedor").get(
        pk=adjudicacion_id
    )
    instante = reloj.ahora()
    # RN-12
    reglas_pagos.validar_resubasta(
        estado=adjudicacion.estado,
        fecha_limite_pago=adjudicacion.fecha_limite_pago,
        instante=instante,
    )
    adjudicacion.estado = EstadoAdjudicacion.VENCIDA
    adjudicacion.save(update_fields=["estado"])

    original = adjudicacion.subasta
    nueva = Subasta.objects.create(
        articulo=original.articulo,
        tipo=original.tipo,
        precio_salida=original.precio_salida,
        precio_reserva=original.precio_reserva,
        precio_compra_inmediata=original.precio_compra_inmediata,
        holandesa_precio_inicial=original.holandesa_precio_inicial,
        holandesa_decremento=original.holandesa_decremento,
        holandesa_intervalo_min=original.holandesa_intervalo_min,
        duracion_horas=original.duracion_horas,
        subasta_origen=original,
    )
    cambiar_estado_subasta(nueva, EstadoSubasta.ABIERTA)
    nueva.fecha_inicio = instante
    nueva.fecha_cierre = reglas_duracion.calcular_fecha_cierre(instante, nueva.duracion_horas)
    nueva.save(update_fields=["fecha_inicio", "fecha_cierre"])
    cambiar_estado_articulo(original.articulo, EstadoArticulo.EN_SUBASTA)
    eventos.publicar(eventos.PAGO_VENCIDO, adjudicacion=adjudicacion, nueva_subasta=nueva)
    return nueva


def procesar_pendientes() -> dict:
    """CU-15 y CU-16 para todo lo vencido, uno por transacción.

    Lo que otra petición ya procesó lo rechaza su regla y se omite.
    """
    instante = reloj.ahora()
    resultado = {"cerradas": 0, "resubastadas": 0}
    por_cerrar = Subasta.objects.filter(
        estado=EstadoSubasta.ABIERTA, fecha_cierre__lte=instante
    ).values_list("pk", flat=True)
    for subasta_id in list(por_cerrar):
        try:
            cerrar_subasta(subasta_id)
            resultado["cerradas"] += 1
        except ErrorDeNegocio as error:
            registro.info("Subasta %s omitida al cerrar: %s", subasta_id, error)
    vencidas = Adjudicacion.objects.filter(
        estado=EstadoAdjudicacion.PENDIENTE_PAGO, fecha_limite_pago__lt=instante
    ).values_list("pk", flat=True)
    for adjudicacion_id in list(vencidas):
        try:
            vencer_pago_y_resubastar(adjudicacion_id)
            resultado["resubastadas"] += 1
        except ErrorDeNegocio as error:
            registro.info("Adjudicación %s omitida al vencer: %s", adjudicacion_id, error)
    return resultado
