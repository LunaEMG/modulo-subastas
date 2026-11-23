from datetime import datetime

from django.conf import settings
from django.http import Http404
from django.shortcuts import render

from ..integraciones import simulados


def inicio(request):
    return render(request, "subastas/inicio.html")


def bandeja_simulada(request):
    if not settings.DEBUG:
        raise Http404
    envios = simulados.leer_bandeja()
    for envio in envios:
        # La bandeja guarda la fecha en ISO; la plantilla la muestra en hora local.
        envio["fecha"] = datetime.fromisoformat(envio["fecha"])
    return render(request, "subastas/desarrollo_bandeja.html", {"envios": envios})
