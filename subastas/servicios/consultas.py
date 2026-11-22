from django.db.models import Q

from .. import reloj
from .. import subastas_tipos as tipos
from ..models import Adjudicacion, Articulo, Puja, Rol, Subasta
from ..reglas import cierre as reglas_cierre
from ..reglas import precios as reglas_precios
from ..reglas.duracion import ESTADOS_ANALIZADOS
from ..reglas.estados import EstadoArticulo, EstadoSubasta
from ..reglas.pagos import EstadoAdjudicacion
from ..reglas.pujas import INCREMENTO_MINIMO
from . import moderacion


def puja_mas_alta(subasta):
    return subasta.pujas.filter(estado=Puja.Estado.ACTIVA).order_by("-monto", "id").first()


def precio_actual(subasta, instante=None) -> int:
    mas_alta = puja_mas_alta(subasta)
    return tipos.obtener(subasta.tipo).precio_actual(
        subasta, mas_alta.monto if mas_alta else None, instante or reloj.ahora()
    )


def esta_abierta(subasta, instante=None) -> bool:
    return reglas_cierre.esta_abierta(
        estado=subasta.estado,
        fecha_cierre=subasta.fecha_cierre,
        instante=instante or reloj.ahora(),
    )


def precio_minimo_avalado(articulo) -> int:
    valuacion = articulo.valuaciones.first()
    return reglas_precios.precio_minimo_avalado(
        costo_salida=articulo.costo_salida,
        requiere_valuacion=articulo.categoria.requiere_valuacion,
        es_autentico=bool(valuacion and valuacion.es_autentico),
        precio_avalado=valuacion.precio_avalado if valuacion else None,
    )


def subastas_abiertas(*, texto: str = "", categoria: str = "", tipo: str = ""):
    """CU-08"""
    subastas = Subasta.objects.filter(
        estado=EstadoSubasta.ABIERTA, fecha_cierre__gt=reloj.ahora()
    ).select_related("articulo__categoria")
    if texto:
        subastas = subastas.filter(
            Q(articulo__titulo__icontains=texto) | Q(articulo__descripcion__icontains=texto)
        )
    if categoria:
        subastas = subastas.filter(articulo__categoria__nombre=categoria)
    if tipo:
        subastas = subastas.filter(tipo=tipo)
    return subastas.order_by("fecha_cierre", "id")


def subastas_visibles(usuario):
    """S-36: las abiertas, más aquellas en las que el usuario pujó, ganó o es el vendedor."""
    return Subasta.objects.filter(
        Q(estado=EstadoSubasta.ABIERTA)
        | Q(pujas__comprador=usuario)
        | Q(adjudicacion__ganador=usuario)
        | Q(articulo__vendedor=usuario)
    ).distinct()


def resumen_subasta(subasta, usuario=None) -> dict:
    instante = reloj.ahora()
    estrategia = tipos.obtener(subasta.tipo)
    abierta = esta_abierta(subasta, instante)
    precio = precio_actual(subasta, instante) if subasta.fecha_inicio else subasta.precio_salida
    mas_alta = puja_mas_alta(subasta)
    mi_puja = None
    if usuario is not None and usuario.is_authenticated:
        mi_puja = subasta.pujas.filter(comprador=usuario, estado=Puja.Estado.ACTIVA).first()
    resumen = {
        "subasta": subasta,
        "articulo": subasta.articulo,
        "tipo": estrategia,
        "abierta": abierta,
        "precio_actual": precio,
        "puja_minima": precio + INCREMENTO_MINIMO,
        # S-32: con el precio en el límite técnico ya no cabe ninguna puja mayor en la base de datos.
        "puja_al_tope": precio + INCREMENTO_MINIMO > reglas_precios.LIMITE_TECNICO_FICHAS,
        "numero_pujas": subasta.pujas.filter(estado=Puja.Estado.ACTIVA).count(),
        "mi_puja": mi_puja,
        "soy_lider": mi_puja is not None and mas_alta == mi_puja,
        "precio_en_el_acto": (
            estrategia.precio_en_el_acto(subasta, precio, instante) if abierta else None
        ),
        "adjudicacion": getattr(subasta, "adjudicacion", None),
    }
    if subasta.tipo == "RESERVADA":
        # S-02: el monto reservado nunca se muestra.
        resumen["reserva_alcanzada"] = estrategia.reserva_alcanzada(subasta, precio)
    if subasta.tipo == "HOLANDESA" and abierta:
        resumen["proxima_bajada"] = estrategia.proxima_bajada(subasta, instante)
    return resumen


# Pendientes por rol: lo que espera una acción de cada quien. Las bandejas usan las mismas consultas.
ESTADOS_POR_ATENDER = frozenset({EstadoArticulo.RECHAZADO}) | ESTADOS_ANALIZADOS


def articulos_por_atender(vendedor):
    """Artículos del vendedor por corregir (RECHAZADO) o por proponer en subasta."""
    return vendedor.articulos.filter(estado__in=ESTADOS_POR_ATENDER).select_related("categoria")


def articulos_por_revisar():
    return Articulo.objects.filter(estado=EstadoArticulo.REGISTRADO)


def propuestas_por_validar():
    return Subasta.objects.filter(estado=EstadoSubasta.PROPUESTA)


def pagos_pendientes(comprador):
    return Adjudicacion.objects.filter(ganador=comprador, estado=EstadoAdjudicacion.PENDIENTE_PAGO)


def pendientes_por_rol(usuario) -> dict:
    """Solo calcula los roles que tiene el usuario; los demás no aparecen en el resultado."""
    pendientes = {}
    if usuario.tiene_rol(Rol.VENDEDOR):
        pendientes["vendedor"] = articulos_por_atender(usuario).count()
    if usuario.tiene_rol(Rol.COMPRADOR):
        pendientes["comprador"] = pagos_pendientes(usuario).count()
    if usuario.tiene_rol(Rol.GESTOR):
        pendientes["gestor_articulos"] = articulos_por_revisar().count()
        pendientes["gestor_propuestas"] = propuestas_por_validar().count()
        pendientes["gestor"] = pendientes["gestor_articulos"] + pendientes["gestor_propuestas"]
    if usuario.tiene_rol(Rol.MODERADOR):
        pendientes["moderador"] = len(moderacion.pendientes_de_revision())
    return pendientes
