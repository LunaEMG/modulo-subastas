from django.conf import settings

from .models import Rol
from .servicios import consultas, notificaciones


# Sección del menú a la que pertenece cada página; la primera de cada lista es la portada de la sección.
SECCIONES = {
    "subastas": ["buscar_subastas", "detalle_subasta", "confirmar_compra_inmediata", "confirmar_aceptar_holandesa"],
    "historial": ["historial", "confirmar_pago"],
    "articulos": ["mis_articulos", "registrar_articulo", "detalle_articulo", "corregir_articulo", "proponer_subasta"],
    "gestor": ["gestor_bandeja", "gestor_articulo", "gestor_propuesta"],
    "moderacion": [
        "moderador_bandeja", "moderador_articulo", "moderador_usuario", "confirmar_retiro", "confirmar_sancion",
    ],
    "avisos": ["avisos"],
    "entrar": ["entrar", "verificar_codigo"],
    "registro": ["registro"],
    "bandeja": ["bandeja_simulada"],
}


def pagina_actual(request) -> dict:
    """{sección: valor de aria-current}: «page» en la portada de la sección y «true» en sus páginas internas."""
    coincidencia = getattr(request, "resolver_match", None)
    nombre = coincidencia.url_name if coincidencia else None
    for seccion, paginas in SECCIONES.items():
        if nombre in paginas:
            return {seccion: "page" if nombre == paginas[0] else "true"}
    return {}


def sesion_actual(request):
    usuario = request.user
    if not usuario.is_authenticated:
        return {"modo_desarrollo": settings.DEBUG, "actual": pagina_actual(request)}
    return {
        "modo_desarrollo": settings.DEBUG,
        "actual": pagina_actual(request),
        "es_vendedor": usuario.tiene_rol(Rol.VENDEDOR),
        "es_comprador": usuario.tiene_rol(Rol.COMPRADOR),
        "es_gestor": usuario.tiene_rol(Rol.GESTOR),
        "es_moderador": usuario.tiene_rol(Rol.MODERADOR),
        "avisos_sin_leer": notificaciones.sin_leer(usuario),
        "pendientes_rol": consultas.pendientes_por_rol(usuario),
    }
