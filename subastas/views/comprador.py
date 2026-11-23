from django.contrib.humanize.templatetags.humanize import intcomma
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .. import reloj
from .. import subastas_tipos as tipos
from ..forms.articulos import FormularioBusqueda, FormularioMonto
from ..mensajes import ErrorDeNegocio
from ..models import Adjudicacion, Puja, Rol, Subasta
from ..reglas.pagos import DIAS_PARA_PAGAR, EstadoAdjudicacion
from ..servicios import cierre, consultas, pujas
from .comunes import avisar, avisar_error, requiere_rol, requiere_sesion


# CU-08
@requiere_sesion
def buscar_subastas(request):
    formulario = FormularioBusqueda(request.GET or None)
    filtros = {}
    if formulario.is_valid():
        datos = formulario.cleaned_data
        filtros = {
            "texto": datos["texto"].strip(),
            "categoria": datos["categoria"].nombre if datos["categoria"] else "",
            "tipo": datos["tipo"],
        }
    resultados = [
        consultas.resumen_subasta(subasta, request.user)
        for subasta in consultas.subastas_abiertas(**filtros)
    ]
    return render(
        request, "subastas/comprador_buscar.html", {"formulario": formulario, "resultados": resultados}
    )


# CU-08
@requiere_sesion
def detalle_subasta(request, subasta_id, formulario=None):
    subasta = get_object_or_404(
        consultas.subastas_visibles(request.user).select_related(
            "articulo__categoria", "articulo__vendedor"
        ),
        pk=subasta_id,
    )
    contexto = consultas.resumen_subasta(subasta, request.user)
    contexto["formulario"] = formulario or FormularioMonto()
    contexto["es_comprador"] = request.user.tiene_rol(Rol.COMPRADOR)
    contexto["es_su_vendedor"] = subasta.articulo.vendedor_id == request.user.pk
    return render(request, "subastas/comprador_subasta.html", contexto)


def _monto(formulario) -> int:
    if not formulario.is_valid():
        raise ErrorDeNegocio("ERR-13")
    return formulario.cleaned_data["monto"]


def _puja_con_error(request, subasta_id, formulario, error: ErrorDeNegocio):
    """Vuelve a la ficha con el monto escrito y el error junto al campo, no solo arriba de la página."""
    avisar_error(request, error)
    if not formulario.errors:
        formulario.add_error("monto", f"{error.codigo}: {error.mensaje}")
    formulario.fields["monto"].widget.attrs["aria-describedby"] = "error-monto ayuda-monto"
    return detalle_subasta(request, subasta_id, formulario=formulario)


def _de_vuelta_a_la_ficha(subasta_id):
    return redirect(reverse("detalle_subasta", args=[subasta_id]) + "#contenido")


# CU-09
@require_POST
@requiere_rol(Rol.COMPRADOR)
def pujar(request, subasta_id):
    formulario = FormularioMonto(request.POST)
    try:
        puja = pujas.pujar(comprador=request.user, subasta_id=subasta_id, monto=_monto(formulario))
    except ErrorDeNegocio as error:
        return _puja_con_error(request, subasta_id, formulario, error)
    avisar(request, "MSG-12", monto=puja.monto)
    return _de_vuelta_a_la_ficha(subasta_id)


# CU-10
@require_POST
@requiere_rol(Rol.COMPRADOR)
def modificar_puja(request, subasta_id):
    formulario = FormularioMonto(request.POST)
    try:
        puja = pujas.modificar_puja(
            comprador=request.user, subasta_id=subasta_id, nuevo_monto=_monto(formulario)
        )
    except ErrorDeNegocio as error:
        return _puja_con_error(request, subasta_id, formulario, error)
    avisar(request, "MSG-13", monto=puja.monto)
    return _de_vuelta_a_la_ficha(subasta_id)


# CU-11
@require_POST
@requiere_rol(Rol.COMPRADOR)
def retirar_puja(request, subasta_id):
    pujas.retirar_puja(comprador=request.user, subasta_id=subasta_id)
    avisar(request, "MSG-14")
    return redirect("detalle_subasta", subasta_id=subasta_id)


# CU-12
@require_POST
@requiere_rol(Rol.COMPRADOR)
def comprar_de_inmediato(request, subasta_id):
    adjudicacion = pujas.comprar_de_inmediato(comprador=request.user, subasta_id=subasta_id)
    avisar(request, "MSG-15", monto=adjudicacion.precio_final, dias=DIAS_PARA_PAGAR)
    return redirect("detalle_subasta", subasta_id=subasta_id)


# CU-09, flujo alterno (S-01)
@require_POST
@requiere_rol(Rol.COMPRADOR)
def aceptar_precio_holandesa(request, subasta_id):
    adjudicacion = pujas.aceptar_precio_holandesa(comprador=request.user, subasta_id=subasta_id)
    avisar(request, "MSG-15", monto=adjudicacion.precio_final, dias=DIAS_PARA_PAGAR)
    return redirect("detalle_subasta", subasta_id=subasta_id)


# CU-13
@requiere_rol(Rol.COMPRADOR)
def historial(request):
    mis_pujas = (
        request.user.pujas.select_related("subasta__articulo", "subasta__adjudicacion")
        .prefetch_related("movimientos")
        .order_by("-fecha_actualizacion", "-id")
    )
    filas = []
    for puja in mis_pujas:
        abierta = consultas.esta_abierta(puja.subasta)
        estado = puja.get_estado_display()
        if puja.estado == Puja.Estado.ACTIVA and not abierta:
            # Solo para mostrar: la puja sigue ACTIVA en la base de datos.
            adjudicacion = getattr(puja.subasta, "adjudicacion", None)
            ganada = adjudicacion is not None and adjudicacion.ganador_id == request.user.pk
            estado = "Ganadora" if ganada else "No ganada"
        filas.append(
            {
                "puja": puja,
                "tipo": tipos.obtener(puja.subasta.tipo),
                "abierta": abierta,
                "estado": estado,
                "precio_actual": consultas.precio_actual(puja.subasta),
                # Solo importa mientras la subasta sigue abierta.
                "soy_lider": abierta and consultas.puja_mas_alta(puja.subasta) == puja,
            }
        )
    ganadas = request.user.adjudicaciones.select_related("subasta__articulo")
    return render(
        request, "subastas/comprador_historial.html", {"filas": filas, "ganadas": ganadas}
    )


# CU-14
@require_POST
@requiere_rol(Rol.COMPRADOR)
def pagar(request, adjudicacion_id):
    adjudicacion = cierre.pagar(comprador=request.user, adjudicacion_id=adjudicacion_id)
    avisar(request, "MSG-16", referencia=adjudicacion.referencia_pago)
    return redirect("historial")


# Páginas «Revisa y confirma»: solo muestran; la acción la hace el mismo POST de siempre.
def _oferta_en_el_acto(request, subasta_id, *, holandesa: bool):
    """La subasta y su precio en el acto, o None si la oferta ya no aplica para este usuario."""
    subasta = get_object_or_404(Subasta.objects.select_related("articulo"), pk=subasta_id)
    resumen = consultas.resumen_subasta(subasta, request.user)
    vigente = (
        resumen["precio_en_el_acto"]
        and (subasta.tipo == "HOLANDESA") == holandesa
        and subasta.articulo.vendedor_id != request.user.pk
    )
    return (subasta, resumen) if vigente else (subasta, None)


def _confirmacion_de_compra(request, subasta, resumen, *, accion, boton, consecuencias):
    detalle = reverse("detalle_subasta", args=[subasta.pk])
    return render(
        request,
        "subastas/confirmar_accion.html",
        {
            "asunto": subasta.articulo.titulo,
            "monto_etiqueta": "Pagarías",
            "monto": resumen["precio_en_el_acto"],
            "datos": [("Tipo de subasta", resumen["tipo"].nombre)],
            "consecuencias": consecuencias,
            "accion_url": reverse(accion, args=[subasta.pk]),
            "boton_texto": boton,
            "volver_url": detalle,
            "volver_texto": "Volver a la subasta",
        },
    )


# CU-12
@requiere_rol(Rol.COMPRADOR)
def confirmar_compra_inmediata(request, subasta_id):
    subasta, resumen = _oferta_en_el_acto(request, subasta_id, holandesa=False)
    if resumen is None:
        return redirect("detalle_subasta", subasta_id=subasta_id)
    precio = intcomma(resumen["precio_en_el_acto"])
    return _confirmacion_de_compra(
        request,
        subasta,
        resumen,
        accion="comprar_de_inmediato",
        boton=f"Comprar ya por {precio} fichas",
        consecuencias=[
            f"La subasta se cierra y el artículo se te adjudica por {precio} fichas; nadie más puede pujar.",
            f"Tendrás {DIAS_PARA_PAGAR} días para pagar; si no pagas a tiempo, el artículo vuelve a subastarse.",
            "La compra no se puede deshacer.",
        ],
    )


# CU-09, flujo alterno (S-01)
@requiere_rol(Rol.COMPRADOR)
def confirmar_aceptar_holandesa(request, subasta_id):
    subasta, resumen = _oferta_en_el_acto(request, subasta_id, holandesa=True)
    if resumen is None:
        return redirect("detalle_subasta", subasta_id=subasta_id)
    precio = intcomma(resumen["precio_en_el_acto"])
    return _confirmacion_de_compra(
        request,
        subasta,
        resumen,
        accion="aceptar_precio_holandesa",
        boton=f"Aceptar {precio} fichas",
        consecuencias=[
            "Gana el primero que acepta: la subasta se cierra y el artículo es tuyo.",
            "El precio solo baja: si baja antes de que confirmes, pagas el precio nuevo, que es menor.",
            f"Tendrás {DIAS_PARA_PAGAR} días para pagar; si no pagas a tiempo, el artículo vuelve a subastarse.",
            "La aceptación no se puede deshacer.",
        ],
    )


# CU-14
@requiere_rol(Rol.COMPRADOR)
def confirmar_pago(request, adjudicacion_id):
    adjudicacion = get_object_or_404(
        Adjudicacion.objects.select_related("subasta__articulo"),
        pk=adjudicacion_id,
    )
    # Mismas verificaciones y en el mismo orden que cierre.pagar (CA-14.4 y CA-14.6).
    if adjudicacion.ganador_id != request.user.pk:
        raise ErrorDeNegocio("ERR-43")
    if adjudicacion.estado != EstadoAdjudicacion.PENDIENTE_PAGO:
        raise ErrorDeNegocio("ERR-44")
    precio = intcomma(adjudicacion.precio_final)
    return render(
        request,
        "subastas/confirmar_accion.html",
        {
            "asunto": adjudicacion.subasta.articulo.titulo,
            "monto_etiqueta": "Vas a pagar",
            "monto": adjudicacion.precio_final,
            "datos": [("Fecha límite", reloj.formato(adjudicacion.fecha_limite_pago))],
            "consecuencias": [
                f"Se cobran {precio} fichas con el servicio de pagos.",
                "Al aprobarse el pago se solicita la recolección del artículo y recibes la referencia de envío.",
            ],
            "accion_url": reverse("pagar", args=[adjudicacion.pk]),
            "boton_texto": f"Pagar {precio} fichas",
            "volver_url": reverse("historial"),
            "volver_texto": "Mi historial",
        },
    )
