"""El precio actual se lee dentro de la transacción: con IMMEDIATE (settings.py), si dos
compradores pujan a la vez el segundo espera y ve el precio que dejó el primero."""
from django.db import transaction

from .. import eventos, reloj
from .. import subastas_tipos as tipos
from ..mensajes import ErrorDeNegocio
from ..models import MovimientoPuja, Puja, Rol, Subasta
from ..reglas import dinero as reglas_dinero
from ..reglas import pujas as reglas_pujas
from . import cierre, consultas, cuentas


def _subasta(subasta_id: int) -> Subasta:
    return Subasta.objects.select_related("articulo__vendedor").get(pk=subasta_id)


def _exigir_abierta(subasta: Subasta) -> None:
    if not consultas.esta_abierta(subasta):
        raise ErrorDeNegocio("ERR-36")


def _puja_activa_propia(subasta: Subasta, comprador) -> Puja:
    puja = subasta.pujas.filter(comprador=comprador, estado=Puja.Estado.ACTIVA).first()
    if puja is None:
        raise ErrorDeNegocio("ERR-37")
    return puja


def _registrar_movimiento(puja: Puja, tipo: str, anterior=None, nuevo=None) -> None:
    MovimientoPuja.objects.create(
        puja=puja, tipo=tipo, monto_anterior=anterior, monto_nuevo=nuevo, fecha=reloj.ahora()
    )


def _avisar_si_superada(subasta: Subasta, anterior_mas_alta: Puja | None, comprador) -> None:
    if anterior_mas_alta is not None and anterior_mas_alta.comprador_id != comprador.pk:
        eventos.publicar(
            eventos.PUJA_SUPERADA,
            subasta=subasta,
            puja_superada=anterior_mas_alta,
            precio=consultas.precio_actual(subasta),
        )


def _preparar_oferta(comprador, subasta: Subasta) -> None:
    cuentas.exigir_participacion(comprador, Rol.COMPRADOR)
    # S-13
    reglas_pujas.validar_no_es_vendedor(
        comprador_id=comprador.pk, vendedor_id=subasta.articulo.vendedor_id
    )


# CU-09
@transaction.atomic
def pujar(*, comprador, subasta_id: int, monto) -> Puja:
    monto = reglas_dinero.validar_monto_fichas(monto)
    subasta = _subasta(subasta_id)
    _preparar_oferta(comprador, subasta)
    _exigir_abierta(subasta)
    if not tipos.obtener(subasta.tipo).admite_pujas:
        raise ErrorDeNegocio("ERR-39")
    if subasta.pujas.filter(comprador=comprador, estado=Puja.Estado.ACTIVA).exists():
        raise ErrorDeNegocio("ERR-38")

    anterior_mas_alta = consultas.puja_mas_alta(subasta)
    # RN-06
    reglas_pujas.validar_puja(monto=monto, precio_actual=consultas.precio_actual(subasta))

    instante = reloj.ahora()
    puja = Puja.objects.create(
        subasta=subasta,
        comprador=comprador,
        monto=monto,
        fecha_creacion=instante,
        fecha_actualizacion=instante,
    )
    _registrar_movimiento(puja, MovimientoPuja.Tipo.CREACION, nuevo=monto)
    _avisar_si_superada(subasta, anterior_mas_alta, comprador)
    return puja


# CU-10
@transaction.atomic
def modificar_puja(*, comprador, subasta_id: int, nuevo_monto) -> Puja:
    nuevo_monto = reglas_dinero.validar_monto_fichas(nuevo_monto)
    subasta = _subasta(subasta_id)
    cuentas.exigir_participacion(comprador, Rol.COMPRADOR)
    puja = _puja_activa_propia(subasta, comprador)
    anterior_mas_alta = consultas.puja_mas_alta(subasta)
    # RN-08
    reglas_pujas.validar_modificacion(
        nuevo_monto=nuevo_monto,
        precio_actual=consultas.precio_actual(subasta),
        monto_anterior=puja.monto,
        subasta_abierta=consultas.esta_abierta(subasta),
    )
    monto_anterior = puja.monto
    puja.monto = nuevo_monto
    puja.fecha_actualizacion = reloj.ahora()
    puja.save(update_fields=["monto", "fecha_actualizacion"])
    _registrar_movimiento(puja, MovimientoPuja.Tipo.MODIFICACION, monto_anterior, nuevo_monto)
    _avisar_si_superada(subasta, anterior_mas_alta, comprador)
    return puja


@transaction.atomic
def retirar_puja(*, comprador, subasta_id: int) -> Puja:
    """CU-11. S-03: el precio no se toca; se recalcula de las pujas activas."""
    subasta = _subasta(subasta_id)
    cuentas.exigir_rol(comprador, Rol.COMPRADOR)
    puja = _puja_activa_propia(subasta, comprador)
    # RN-07
    reglas_pujas.validar_retiro(subasta_abierta=consultas.esta_abierta(subasta))
    puja.estado = Puja.Estado.RETIRADA
    puja.fecha_actualizacion = reloj.ahora()
    puja.save(update_fields=["estado", "fecha_actualizacion"])
    _registrar_movimiento(puja, MovimientoPuja.Tipo.RETIRO, anterior=puja.monto)
    return puja


def _adjudicar_en_el_acto(comprador, subasta_id: int, tipo_esperado: str):
    """S-19: compra inmediata y aceptación en holandesa son definitivas."""
    subasta = _subasta(subasta_id)
    _preparar_oferta(comprador, subasta)
    _exigir_abierta(subasta)
    estrategia = tipos.obtener(subasta.tipo)
    precio = estrategia.precio_en_el_acto(subasta, consultas.precio_actual(subasta), reloj.ahora())
    if subasta.tipo != tipo_esperado or precio is None:
        raise ErrorDeNegocio("ERR-39")

    instante = reloj.ahora()
    puja = subasta.pujas.filter(comprador=comprador, estado=Puja.Estado.ACTIVA).first()
    if puja is None:
        puja = Puja.objects.create(
            subasta=subasta,
            comprador=comprador,
            monto=precio,
            fecha_creacion=instante,
            fecha_actualizacion=instante,
        )
        _registrar_movimiento(puja, MovimientoPuja.Tipo.CREACION, nuevo=precio)
    else:
        anterior = puja.monto
        puja.monto = precio
        puja.fecha_actualizacion = instante
        puja.save(update_fields=["monto", "fecha_actualizacion"])
        _registrar_movimiento(puja, MovimientoPuja.Tipo.MODIFICACION, anterior, precio)
    return cierre.adjudicar(subasta, puja)


# CU-12
@transaction.atomic
def comprar_de_inmediato(*, comprador, subasta_id: int):
    return _adjudicar_en_el_acto(comprador, subasta_id, "COMPRA_INMEDIATA")


# CU-09, flujo alterno (S-01)
@transaction.atomic
def aceptar_precio_holandesa(*, comprador, subasta_id: int):
    return _adjudicar_en_el_acto(comprador, subasta_id, "HOLANDESA")
