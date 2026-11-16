"""CU-17"""
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from ..servicios import notificaciones
from .comunes import avisar, requiere_sesion


@requiere_sesion
def lista(request):
    avisos = request.user.notificaciones.prefetch_related("entregas")
    return render(request, "subastas/avisos.html", {"avisos": avisos})


@require_POST
@requiere_sesion
def marcar_leidas(request):
    notificaciones.marcar_leidas(request.user)
    avisar(request, "MSG-17")
    return redirect("avisos")
