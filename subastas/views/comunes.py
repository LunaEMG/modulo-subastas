from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login

from .. import mensajes
from ..forms.articulos import LONGITUD_MAXIMA_MOTIVO, FormularioMotivo
from ..mensajes import ErrorDeNegocio


def avisar(request, codigo: str, **datos) -> None:
    messages.success(request, mensajes.texto(codigo, **datos), extra_tags=codigo)


def avisar_error(request, error: ErrorDeNegocio) -> None:
    messages.error(request, error.mensaje, extra_tags=error.codigo)


def motivo_enviado(request) -> str:
    """S-39: el motivo llega por POST sin pasar por un formulario validado; aquí se revisa su longitud."""
    formulario = FormularioMotivo(request.POST)
    if not formulario.is_valid():
        raise ErrorDeNegocio("ERR-63", limit_value=LONGITUD_MAXIMA_MOTIVO)
    return formulario.cleaned_data["motivo"]


def requiere_rol(*roles: str):
    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not any(request.user.tiene_rol(rol) for rol in roles):
                raise ErrorDeNegocio("ERR-32")
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador


def requiere_sesion(vista):
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        return vista(request, *args, **kwargs)

    return envoltura
