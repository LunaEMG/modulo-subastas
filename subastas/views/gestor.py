from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .. import reloj
from .. import subastas_tipos as tipos
from ..forms.articulos import FormularioMotivo
from ..models import Articulo, Rol, Subasta
from ..reglas.estados import EstadoArticulo, EstadoSubasta
from ..servicios import consultas, moderacion, revision
from .comunes import avisar, motivo_enviado, requiere_rol


@requiere_rol(Rol.GESTOR)
def bandeja(request):
    return render(
        request,
        "subastas/gestor_bandeja.html",
        {
            "articulos": consultas.articulos_por_revisar().select_related("categoria", "vendedor"),
            "propuestas": consultas.propuestas_por_validar().select_related("articulo__vendedor"),
        },
    )


# CU-06
@requiere_rol(Rol.GESTOR)
def revisar_articulo(request, articulo_id):
    articulo = get_object_or_404(Articulo.objects.select_related("categoria", "vendedor"), pk=articulo_id)
    return render(
        request,
        "subastas/gestor_articulo.html",
        {
            "articulo": articulo,
            "formulario": FormularioMotivo(),
            "pendiente": articulo.estado == EstadoArticulo.REGISTRADO,
        },
    )


@require_POST
@requiere_rol(Rol.GESTOR)
def aprobar_articulo(request, articulo_id):
    articulo = revision.aprobar_articulo(
        gestor=request.user, articulo_id=articulo_id, observaciones=motivo_enviado(request)
    )
    avisar(request, "MSG-08", estado=articulo.get_estado_display())
    return redirect("gestor_bandeja")


@require_POST
@requiere_rol(Rol.GESTOR)
def rechazar_articulo(request, articulo_id):
    revision.rechazar_articulo(
        gestor=request.user, articulo_id=articulo_id, motivo=motivo_enviado(request)
    )
    avisar(request, "MSG-09")
    return redirect("gestor_bandeja")


# CU-07
@requiere_rol(Rol.GESTOR)
def revisar_propuesta(request, subasta_id):
    subasta = get_object_or_404(Subasta.objects.select_related("articulo__vendedor"), pk=subasta_id)
    return render(
        request,
        "subastas/gestor_propuesta.html",
        {
            "subasta": subasta,
            "tipo": tipos.obtener(subasta.tipo),
            "formulario": FormularioMotivo(),
            "pendiente": subasta.estado == EstadoSubasta.PROPUESTA,
            "contenido_aprobado": moderacion.contenido_aprobado(subasta.articulo),
        },
    )


@require_POST
@requiere_rol(Rol.GESTOR)
def validar_duracion(request, subasta_id):
    subasta = revision.validar_duracion(gestor=request.user, subasta_id=subasta_id)
    avisar(request, "MSG-10", cierre=reloj.formato(subasta.fecha_cierre))
    return redirect("gestor_bandeja")


@require_POST
@requiere_rol(Rol.GESTOR)
def rechazar_duracion(request, subasta_id):
    revision.rechazar_duracion(
        gestor=request.user, subasta_id=subasta_id, motivo=motivo_enviado(request)
    )
    avisar(request, "MSG-11")
    return redirect("gestor_bandeja")
