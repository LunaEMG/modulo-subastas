from urllib.parse import urlparse

from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme

from .mensajes import ErrorDeNegocio
from .servicios import cierre, cuentas
from .views.comunes import avisar_error


class ProcesoDelTiempoMiddleware:
    """Actor Tiempo (CU-15, CU-16): procesa lo vencido en cada petición para no depender de cron."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        cierre.procesar_pendientes()
        return self.get_response(request)


class CuentaActivaMiddleware:
    """RN-16: cierra la sesión de quien fue suspendido mientras estaba dentro."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                cuentas.exigir_cuenta_activa(request.user)
            except ErrorDeNegocio as error:
                logout(request)
                avisar_error(request, error)
                return redirect("entrar")
        return self.get_response(request)


class ErroresDeNegocioMiddleware:
    """Un ErrorDeNegocio no atendido se muestra como aviso y regresa a la página de origen."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not isinstance(exception, ErrorDeNegocio):
            return None
        avisar_error(request, exception)
        origen = request.META.get("HTTP_REFERER", "")
        es_seguro = url_has_allowed_host_and_scheme(origen, allowed_hosts={request.get_host()})
        # Si falla la propia página de origen, regresar a ella sería un ciclo.
        if es_seguro and urlparse(origen).path != request.path:
            return redirect(origen)
        return redirect("inicio")
