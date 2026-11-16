from django.shortcuts import redirect, render

from .. import subastas_tipos as tipos
from ..forms.articulos import FormularioArticulo, FormularioPropuesta
from ..mensajes import ErrorDeNegocio
from ..models import Rol
from ..reglas.duracion import ESTADOS_ANALIZADOS
from ..reglas.estados import EstadoArticulo
from ..servicios import articulos as servicio_articulos
from ..servicios import consultas
from .comunes import avisar, avisar_error, requiere_rol


# CU-05
@requiere_rol(Rol.VENDEDOR)
def mis_articulos(request):
    articulos = request.user.articulos.select_related("categoria").prefetch_related("subastas")
    return render(request, "subastas/vendedor_articulos.html", {"articulos": articulos})


# CU-03
@requiere_rol(Rol.VENDEDOR)
def registrar_articulo(request):
    formulario = FormularioArticulo(request.POST or None, request.FILES or None)
    if request.method == "POST" and formulario.is_valid():
        try:
            articulo = servicio_articulos.registrar_articulo(
                vendedor=request.user, **formulario.datos_para_servicio()
            )
        except ErrorDeNegocio as error:
            avisar_error(request, error)
        else:
            avisar(request, "MSG-05")
            return redirect("detalle_articulo", articulo_id=articulo.pk)
    return render(
        request,
        "subastas/vendedor_articulo_formulario.html",
        {"formulario": formulario, "titulo": "Registrar artículo", "boton": "Registrar"},
    )


# CU-03, flujo alterno
@requiere_rol(Rol.VENDEDOR)
def corregir_articulo(request, articulo_id):
    articulo = servicio_articulos.articulo_propio(request.user, articulo_id)
    iniciales = {
        "categoria": articulo.categoria.nombre,
        "titulo": articulo.titulo,
        "descripcion": articulo.descripcion,
        "anio": articulo.anio,
        "costo_salida": articulo.costo_salida,
    }
    formulario = FormularioArticulo(request.POST or None, request.FILES or None, initial=iniciales)
    if request.method == "POST" and formulario.is_valid():
        try:
            servicio_articulos.corregir_articulo(
                vendedor=request.user, articulo_id=articulo.pk, **formulario.datos_para_servicio()
            )
        except ErrorDeNegocio as error:
            avisar_error(request, error)
        else:
            avisar(request, "MSG-06")
            return redirect("detalle_articulo", articulo_id=articulo.pk)
    return render(
        request,
        "subastas/vendedor_articulo_formulario.html",
        {
            "formulario": formulario,
            "articulo": articulo,
            "titulo": "Corregir artículo",
            "boton": "Guardar y reenviar",
        },
    )


# CU-05
@requiere_rol(Rol.VENDEDOR)
def detalle_articulo(request, articulo_id):
    articulo = servicio_articulos.articulo_propio(request.user, articulo_id)
    subastas = [
        {
            "subasta": subasta,
            "tipo": tipos.obtener(subasta.tipo),
            "abierta": consultas.esta_abierta(subasta),
            "precio_actual": consultas.precio_actual(subasta) if subasta.fecha_inicio else None,
            "adjudicacion": getattr(subasta, "adjudicacion", None),
        }
        for subasta in articulo.subastas.order_by("-id")
    ]
    return render(
        request,
        "subastas/vendedor_articulo_detalle.html",
        {
            "articulo": articulo,
            "subastas": subastas,
            "puede_corregir": articulo.estado == EstadoArticulo.RECHAZADO,
            "puede_proponer": articulo.estado in ESTADOS_ANALIZADOS,
        },
    )


# CU-04
@requiere_rol(Rol.VENDEDOR)
def proponer_subasta(request, articulo_id):
    articulo = servicio_articulos.articulo_propio(request.user, articulo_id)
    formulario = FormularioPropuesta(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        try:
            servicio_articulos.proponer_subasta(
                vendedor=request.user, articulo_id=articulo.pk, **formulario.cleaned_data
            )
        except ErrorDeNegocio as error:
            avisar_error(request, error)
        else:
            avisar(request, "MSG-07")
            return redirect("detalle_articulo", articulo_id=articulo.pk)
    return render(
        request,
        "subastas/vendedor_propuesta.html",
        {
            "formulario": formulario,
            "articulo": articulo,
            "precio_minimo": consultas.precio_minimo_avalado(articulo),
            "tipos": tipos.todos(),
        },
    )
