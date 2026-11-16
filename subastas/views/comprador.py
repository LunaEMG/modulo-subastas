from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .. import subastas_tipos as tipos
from ..forms.articulos import FormularioBusqueda, FormularioMonto
from ..mensajes import ErrorDeNegocio
from ..models import Rol, Subasta
from ..reglas.pagos import DIAS_PARA_PAGAR
from ..servicios import cierre, consultas, pujas
from .comunes import avisar, requiere_rol, requiere_sesion


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
def detalle_subasta(request, subasta_id):
    subasta = get_object_or_404(
        Subasta.objects.select_related("articulo__categoria", "articulo__vendedor"), pk=subasta_id
    )
    contexto = consultas.resumen_subasta(subasta, request.user)
    contexto["formulario"] = FormularioMonto(initial={"monto": contexto["puja_minima"]})
    contexto["es_comprador"] = request.user.tiene_rol(Rol.COMPRADOR)
    contexto["es_su_vendedor"] = subasta.articulo.vendedor_id == request.user.pk
    return render(request, "subastas/comprador_subasta.html", contexto)


def _monto(request) -> int:
    formulario = FormularioMonto(request.POST)
    if not formulario.is_valid():
        raise ErrorDeNegocio("ERR-13")
    return formulario.cleaned_data["monto"]


# CU-09
@require_POST
@requiere_rol(Rol.COMPRADOR)
def pujar(request, subasta_id):
    puja = pujas.pujar(comprador=request.user, subasta_id=subasta_id, monto=_monto(request))
    avisar(request, "MSG-12", monto=puja.monto)
    return redirect("detalle_subasta", subasta_id=subasta_id)


# CU-10
@require_POST
@requiere_rol(Rol.COMPRADOR)
def modificar_puja(request, subasta_id):
    puja = pujas.modificar_puja(
        comprador=request.user, subasta_id=subasta_id, nuevo_monto=_monto(request)
    )
    avisar(request, "MSG-13", monto=puja.monto)
    return redirect("detalle_subasta", subasta_id=subasta_id)


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
        request.user.pujas.select_related("subasta__articulo")
        .prefetch_related("movimientos")
        .order_by("-fecha_actualizacion", "-id")
    )
    filas = [
        {
            "puja": puja,
            "tipo": tipos.obtener(puja.subasta.tipo),
            "abierta": consultas.esta_abierta(puja.subasta),
            "precio_actual": consultas.precio_actual(puja.subasta),
        }
        for puja in mis_pujas
    ]
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
