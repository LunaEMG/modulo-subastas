from django.db import transaction

from .. import reloj
from .. import subastas_tipos as tipos
from ..mensajes import ErrorDeNegocio
from ..models import Articulo, Categoria, Fotografia, Rol, Subasta
from ..reglas import articulos as reglas_articulos
from ..reglas import dinero as reglas_dinero
from ..reglas import duracion as reglas_duracion
from ..reglas.estados import EstadoArticulo, EstadoSubasta
from ..subastas_tipos import ParametrosSubasta
from . import consultas, cuentas
from .transiciones import cambiar_estado_articulo


def articulo_propio(vendedor, articulo_id: int) -> Articulo:
    articulo = Articulo.objects.select_related("categoria", "vendedor").get(pk=articulo_id)
    if articulo.vendedor_id != vendedor.pk:
        raise ErrorDeNegocio("ERR-43")
    return articulo


def _validar_datos(*, categoria: str, descripcion, anio, costo_salida, numero_fotografias) -> Categoria:
    # RN-01
    reglas_articulos.validar_categoria(categoria)
    # RN-02
    reglas_articulos.validar_datos_articulo(
        descripcion=descripcion,
        anio=anio,
        costo_salida=costo_salida,
        numero_fotografias=numero_fotografias,
    )
    # RN-13
    reglas_dinero.validar_monto_fichas(costo_salida)
    # S-22
    reglas_articulos.validar_anio(anio, reloj.ahora().year)
    return Categoria.objects.get(nombre=categoria)


def _guardar_fotografias(articulo: Articulo, fotografias) -> None:
    for orden, archivo in enumerate(fotografias):
        Fotografia.objects.create(articulo=articulo, archivo=archivo, orden=orden)


# CU-03
@transaction.atomic
def registrar_articulo(
    *, vendedor, categoria: str, titulo: str, descripcion: str, anio, costo_salida, fotografias
) -> Articulo:
    cuentas.exigir_participacion(vendedor, Rol.VENDEDOR)
    fotografias = list(fotografias or [])
    categoria_registrada = _validar_datos(
        categoria=categoria,
        descripcion=descripcion,
        anio=anio,
        costo_salida=costo_salida,
        numero_fotografias=len(fotografias),
    )
    articulo = Articulo.objects.create(
        vendedor=vendedor,
        categoria=categoria_registrada,
        titulo=titulo.strip(),
        descripcion=descripcion.strip(),
        anio=anio,
        costo_salida=costo_salida,
    )
    _guardar_fotografias(articulo, fotografias)
    return articulo


@transaction.atomic
def corregir_articulo(
    *,
    vendedor,
    articulo_id: int,
    categoria: str,
    titulo: str,
    descripcion: str,
    anio,
    costo_salida,
    fotografias=None,
) -> Articulo:
    """CU-03, flujo alterno. Las fotografías nuevas sustituyen a las anteriores, que se conservan ocultas (RNF-01)."""
    cuentas.exigir_participacion(vendedor, Rol.VENDEDOR)
    articulo = articulo_propio(vendedor, articulo_id)
    if articulo.estado != EstadoArticulo.RECHAZADO:
        raise ErrorDeNegocio("ERR-50")
    fotografias = list(fotografias or [])
    categoria_registrada = _validar_datos(
        categoria=categoria,
        descripcion=descripcion,
        anio=anio,
        costo_salida=costo_salida,
        numero_fotografias=len(fotografias) or articulo.fotografias_visibles.count(),
    )
    if fotografias:
        articulo.fotografias_visibles.update(retirada=True)
        _guardar_fotografias(articulo, fotografias)
    articulo.categoria = categoria_registrada
    articulo.titulo = titulo.strip()
    articulo.descripcion = descripcion.strip()
    articulo.anio = anio
    articulo.costo_salida = costo_salida
    # S-10: invalida la aprobación previa del moderador.
    articulo.fecha_ultimo_envio = reloj.ahora()
    articulo.save()
    cambiar_estado_articulo(articulo, EstadoArticulo.REGISTRADO)
    return articulo


# CU-04
@transaction.atomic
def proponer_subasta(
    *,
    vendedor,
    articulo_id: int,
    tipo: str,
    duracion_horas: int,
    precio_reserva=None,
    precio_compra_inmediata=None,
    holandesa_precio_inicial=None,
    holandesa_decremento=None,
    holandesa_intervalo_min=None,
) -> Subasta:
    cuentas.exigir_participacion(vendedor, Rol.VENDEDOR)
    articulo = articulo_propio(vendedor, articulo_id)
    # RN-05
    reglas_duracion.validar_propuesta_duracion(
        estado_articulo=articulo.estado, duracion_horas=duracion_horas
    )
    # RN-04
    parametros = ParametrosSubasta(
        precio_salida=consultas.precio_minimo_avalado(articulo),
        precio_reserva=_monto_opcional(precio_reserva),
        precio_compra_inmediata=_monto_opcional(precio_compra_inmediata),
        holandesa_precio_inicial=_monto_opcional(holandesa_precio_inicial),
        holandesa_decremento=_monto_opcional(holandesa_decremento),
        holandesa_intervalo_min=holandesa_intervalo_min,
    )
    # RF-01
    tipos.obtener(tipo).validar_parametros(parametros)

    subasta = Subasta.objects.create(
        articulo=articulo,
        tipo=tipo,
        estado=EstadoSubasta.PROPUESTA,
        duracion_horas=duracion_horas,
        precio_salida=parametros.precio_salida,
        precio_reserva=parametros.precio_reserva,
        precio_compra_inmediata=parametros.precio_compra_inmediata,
        holandesa_precio_inicial=parametros.holandesa_precio_inicial,
        holandesa_decremento=parametros.holandesa_decremento,
        holandesa_intervalo_min=parametros.holandesa_intervalo_min,
    )
    cambiar_estado_articulo(articulo, EstadoArticulo.DURACION_PROPUESTA)
    return subasta


def _monto_opcional(valor):
    """RN-13, pero acepta vacío (None)."""
    return None if valor in (None, "") else reglas_dinero.validar_monto_fichas(valor)
