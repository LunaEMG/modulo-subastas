from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .. import reloj
from ..forms.articulos import FormularioMotivo
from ..mensajes import ErrorDeNegocio
from ..models import Articulo, Rol
from ..reglas import sanciones as reglas_sanciones
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


# «Revisa y confirma»: llega por POST con el motivo escrito; solo muestra las consecuencias.
# Por GET (por ejemplo, al volver de un error) regresa a la pantalla de origen.

# CU-19
@requiere_rol(Rol.MODERADOR)
def confirmar_retiro(request, articulo_id):
    articulo = get_object_or_404(Articulo, pk=articulo_id)
    subasta = moderacion.subasta_publicada(articulo)
    if request.method != "POST" or subasta is None:
        return redirect("moderador_articulo", articulo_id=articulo_id)
    motivo = moderacion.exigir_motivo(request.POST.get("motivo", ""))
    pujas_activas = consultas.resumen_subasta(subasta)["numero_pujas"]
    return render(
        request,
        "subastas/confirmar_accion.html",
        {
            "asunto": articulo.titulo,
            "monto": None,
            "datos": [("Pujas activas", pujas_activas), ("Motivo", motivo)],
            "consecuencias": [
                "La subasta se cancela y el artículo queda retirado por moderación.",
                f"Las pujas activas ({pujas_activas}) quedan sin efecto.",
                "Se avisa al vendedor y a quienes pujaron.",
                "El retiro no se puede deshacer.",
            ],
            "ocultos": [("motivo", motivo)],
            "accion_url": reverse("retirar_publicacion", args=[articulo.pk]),
            "boton_texto": "Retirar publicación",
            "peligro": True,
            "volver_url": reverse("moderador_articulo", args=[articulo.pk]),
            "volver_texto": "Volver al artículo",
        },
    )


# CU-20
@requiere_rol(Rol.MODERADOR)
def confirmar_sancion(request, usuario_id):
    sancionado = get_object_or_404(get_user_model(), pk=usuario_id)
    try:
        nivel = int(request.POST.get("nivel", ""))
    except ValueError:
        nivel = None
    if request.method != "POST" or nivel not in reglas_sanciones.DESCRIPCION_POR_NIVEL:
        return redirect("moderador_usuario", usuario_id=usuario_id)
    motivo = moderacion.exigir_motivo(request.POST.get("motivo", ""))
    moderacion.validar_sancion(sancionado, nivel)
    instante = reloj.ahora()
    fin = reglas_sanciones.calcular_fecha_fin(nivel, instante)
    pujas = moderacion.pujas_que_retira_la_sancion(sancionado, instante).count()
    duracion = reglas_sanciones.DESCRIPCION_POR_NIVEL[nivel]
    return render(
        request,
        "subastas/confirmar_accion.html",
        {
            "asunto": sancionado.nombre,
            "monto": None,
            "datos": [
                ("Sanción", f"Nivel {nivel}: {duracion}"),
                ("Hasta", reloj.formato(fin) if fin else "Definitiva"),
                ("Motivo", motivo),
            ],
            "consecuencias": [
                "La cuenta no podrá entrar mientras dure la sanción; si está dentro, su sesión se cierra."
                if fin
                else "La cuenta queda dada de baja de forma definitiva.",
                f"Se retiran sus pujas activas en subastas abiertas ({pujas}).",
                "La sanción queda en su historial y no se puede deshacer.",
            ],
            "ocultos": [("nivel", nivel), ("motivo", motivo)],
            "accion_url": reverse("sancionar", args=[sancionado.pk]),
            "boton_texto": f"Aplicar sanción de nivel {nivel}",
            "peligro": True,
            "volver_url": reverse("moderador_usuario", args=[sancionado.pk]),
            "volver_texto": "Volver al usuario",
        },
    )
