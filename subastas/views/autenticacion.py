from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from ..forms.autenticacion import FormularioCodigo, FormularioEntrar, FormularioRegistro
from ..mensajes import ErrorDeNegocio
from ..models import Usuario
from ..servicios import autenticacion
from .comunes import avisar, avisar_error

USUARIO_PENDIENTE = "usuario_pendiente"
INTENTOS_DE_CODIGO = "intentos_de_codigo"
SIGUIENTE = "siguiente"
BACKEND = "django.contrib.auth.backends.ModelBackend"


def registro(request):
    formulario = FormularioRegistro(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        try:
            autenticacion.registrar_usuario(**formulario.cleaned_data)
        except ErrorDeNegocio as error:
            avisar_error(request, error)
        else:
            avisar(request, "MSG-01")
            return redirect("entrar")
    return render(request, "subastas/cuenta_registro.html", {"formulario": formulario})


def entrar(request):
    formulario = FormularioEntrar(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        try:
            usuario = autenticacion.iniciar_sesion(**formulario.cleaned_data)
        except ErrorDeNegocio as error:
            avisar_error(request, error)
        else:
            request.session[USUARIO_PENDIENTE] = usuario.pk
            request.session[INTENTOS_DE_CODIGO] = 0
            request.session[SIGUIENTE] = request.GET.get("next", "")
            avisar(request, "MSG-02")
            return redirect("verificar_codigo")
    return render(request, "subastas/cuenta_entrar.html", {"formulario": formulario})


def verificar_codigo(request):
    usuario = Usuario.objects.filter(pk=request.session.get(USUARIO_PENDIENTE)).first()
    if usuario is None:
        return redirect("entrar")
    formulario = FormularioCodigo(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        try:
            autenticacion.verificar_codigo(usuario=usuario, codigo=formulario.cleaned_data["codigo"])
        except ErrorDeNegocio as error:
            avisar_error(request, error)
            request.session[INTENTOS_DE_CODIGO] = request.session.get(INTENTOS_DE_CODIGO, 0) + 1
            if request.session[INTENTOS_DE_CODIGO] >= autenticacion.MAXIMO_INTENTOS_CODIGO:
                autenticacion.anular_codigos(usuario)
                request.session.pop(USUARIO_PENDIENTE, None)
                return redirect("entrar")
        else:
            destino = request.session.pop(SIGUIENTE, "")
            login(request, usuario, backend=BACKEND)
            avisar(request, "MSG-03", nombre=usuario.nombre)
            # Evita redirecciones abiertas a otros sitios.
            if url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
                return redirect(destino)
            return redirect("inicio")
    return render(request, "subastas/cuenta_codigo.html", {"formulario": formulario})


@require_POST
def salir(request):
    logout(request)
    avisar(request, "MSG-04")
    return redirect("inicio")
