from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..forms.articulos import FormularioMotivo
from ..mensajes import ErrorDeNegocio
from ..models import Articulo, Rol
from ..reglas.estados import ESTADOS_PREVIOS_A_PUBLICAR, EstadoArticulo
from ..servicios import consultas, cuentas, moderacion
from .comunes import avisar, requiere_rol


@requiere_rol(Rol.MODERADOR)
def bandeja(request):
    participantes = (
        get_user_model()
        .objects.filter(roles__nombre__in=[Rol.VENDEDOR, Rol.COMPRADOR])
        .distinct()
        .order_by("nombre")
    )
    return render(
        request,
        "subastas/moderador_bandeja.html",
        {
            "pendientes": moderacion.pendientes_de_revision(),
            "publicadas": consultas.subastas_abiertas(),
            "participantes": [
                {"usuario": usuario, "estado": cuentas.estado_de_cuenta(usuario)}
                for usuario in participantes
            ],
        },
    )


# CU-18, CU-19
@requiere_rol(Rol.MODERADOR)
def revisar_articulo(request, articulo_id):
    articulo = get_object_or_404(Articulo.objects.select_related("categoria", "vendedor"), pk=articulo_id)
    return render(
        request,
        "subastas/moderador_articulo.html",
        {
            "articulo": articulo,
            "formulario": FormularioMotivo(),
            "revisable": articulo.estado in ESTADOS_PREVIOS_A_PUBLICAR,
            "aprobado": moderacion.contenido_aprobado(articulo),
            "publicado": articulo.estado == EstadoArticulo.EN_SUBASTA,
            "revisiones": articulo.revisiones_contenido.select_related("moderador"),
        },
    )


@require_POST
@requiere_rol(Rol.MODERADOR)
def aprobar_contenido(request, articulo_id):
    moderacion.aprobar_contenido(moderador=request.user, articulo_id=articulo_id)
    avisar(request, "MSG-18")
    return redirect("moderador_bandeja")


@require_POST
@requiere_rol(Rol.MODERADOR)
def rechazar_contenido(request, articulo_id):
    moderacion.rechazar_contenido(
        moderador=request.user, articulo_id=articulo_id, motivo=request.POST.get("motivo", "")
    )
    avisar(request, "MSG-18")
    return redirect("moderador_bandeja")


@require_POST
@requiere_rol(Rol.MODERADOR)
def retirar_publicacion(request, articulo_id):
    moderacion.retirar_publicacion(
        moderador=request.user, articulo_id=articulo_id, motivo=request.POST.get("motivo", "")
    )
    avisar(request, "MSG-19")
    return redirect("moderador_bandeja")


# CU-20
@requiere_rol(Rol.MODERADOR)
def usuario(request, usuario_id):
    sancionado = get_object_or_404(get_user_model(), pk=usuario_id)
    try:
        nivel = moderacion.nivel_siguiente(sancionado)
    except ErrorDeNegocio:
        nivel = None  # Ya tiene la baja definitiva: no hay siguiente nivel.
    return render(
        request,
        "subastas/moderador_usuario.html",
        {
            "sancionado": sancionado,
            "estado": cuentas.estado_de_cuenta(sancionado),
            "sanciones": moderacion.historial_de_sanciones(sancionado),
            "nivel": nivel,
            "formulario": FormularioMotivo(),
        },
    )


@require_POST
@requiere_rol(Rol.MODERADOR)
def sancionar(request, usuario_id):
    sancion = moderacion.sancionar(
        moderador=request.user,
        usuario_id=usuario_id,
        motivo=request.POST.get("motivo", ""),
        nivel=request.POST.get("nivel") or None,
    )
    avisar(request, "MSG-20", nivel=sancion.nivel, nombre=sancion.usuario.nombre)
    return redirect("moderador_usuario", usuario_id=usuario_id)
