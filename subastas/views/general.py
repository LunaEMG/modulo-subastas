from django.conf import settings
from django.http import Http404
from django.shortcuts import render

from ..integraciones import simulados


def inicio(request):
    return render(request, "subastas/inicio.html")


def bandeja_simulada(request):
    if not settings.DEBUG:
        raise Http404
    return render(
        request, "subastas/desarrollo_bandeja.html", {"envios": simulados.leer_bandeja()}
    )
