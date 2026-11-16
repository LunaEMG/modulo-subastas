from django.conf import settings

from .models import Rol
from .servicios import notificaciones


def sesion_actual(request):
    usuario = request.user
    if not usuario.is_authenticated:
        return {"modo_desarrollo": settings.DEBUG}
    return {
        "modo_desarrollo": settings.DEBUG,
        "es_vendedor": usuario.tiene_rol(Rol.VENDEDOR),
        "es_comprador": usuario.tiene_rol(Rol.COMPRADOR),
        "es_gestor": usuario.tiene_rol(Rol.GESTOR),
        "es_moderador": usuario.tiene_rol(Rol.MODERADOR),
        "avisos_sin_leer": notificaciones.sin_leer(usuario),
    }
