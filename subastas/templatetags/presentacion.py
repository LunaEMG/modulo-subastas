"""Filtros de presentación (RNF-02). No deciden nada del negocio: solo dan formato a datos que ya existen.

El tiempo restante se calcula con reloj.ahora(), no con timezone.now(), para que respete
`adelantar_reloj` en la demostración y el RelojFijo de las pruebas. El umbral de urgencia
(menos de un día) es una decisión de presentación, no una regla de negocio.
"""
from datetime import datetime, timedelta

from django import template

from subastas import reloj

register = template.Library()

UMBRAL_URGENCIA = timedelta(days=1)


def _restante(fecha_cierre: datetime | None) -> timedelta | None:
    if fecha_cierre is None:
        return None
    restante = fecha_cierre - reloj.ahora()
    return restante if restante > timedelta(0) else None


@register.filter
def tiempo_restante(fecha_cierre: datetime | None) -> str:
    """«quedan 2 d 4 h», «quedan 5 h 10 min» o «quedan 12 min». Sin fecha o ya vencida: cadena vacía."""
    restante = _restante(fecha_cierre)
    if restante is None:
        return ""
    minutos_totales = int(restante.total_seconds() // 60)
    dias, resto = divmod(minutos_totales, 24 * 60)
    horas, minutos = divmod(resto, 60)
    if dias:
        return f"quedan {dias} d {horas} h"
    if horas:
        return f"quedan {horas} h {minutos} min"
    if minutos:
        return f"quedan {minutos} min"
    return "quedan menos de 1 min"


@register.filter
def es_urgente(fecha_cierre: datetime | None) -> bool:
    """Verdadero si falta menos de un día para el cierre (y todavía no cierra)."""
    restante = _restante(fecha_cierre)
    return restante is not None and restante < UMBRAL_URGENCIA


@register.filter
def fecha_completa(instante: datetime | None) -> str:
    """dd/mm/AAAA HH:MM en hora local, el mismo formato que usa el resto del módulo."""
    return reloj.formato(instante) if instante else ""


@register.simple_tag
def estatico_versionado(ruta: str) -> str:
    """La URL de un archivo estático con su fecha de modificación (?v=…).

    El servidor de desarrollo no manda Cache-Control, así que el navegador puede seguir usando una
    hoja vieja después de un cambio. Con la versión en la URL, cada cambio obliga a pedirla de nuevo.
    """
    from os import path

    from django.contrib.staticfiles import finders
    from django.templatetags.static import static

    archivo = finders.find(ruta)
    url = static(ruta)
    return f"{url}?v={int(path.getmtime(archivo))}" if archivo else url


# Único lugar del ícono de cada categoría (archivos de static/subastas/iconos/). Una categoría que no
# esté aquí usa ICONO_GENERICO, así que una categoría nueva funciona sin tocar plantillas ni CSS.
ICONOS_CATEGORIA = {
    "Automóviles": "car",
    "Relojes": "watch",
    "Videojuegos": "gamepad-2",
    "Artículos de oficina": "lamp-desk",
}
ICONO_GENERICO = "tag"

# Único lugar de la foto de portada de cada categoría (static/subastas/categorias/). Cada archivo es un
# recorte 4:3 de una foto real de fotos_demo/ (categorias/CREDITOS.md). Una categoría que no esté aquí
# muestra en la portada su tinte con su ícono grande, así que una categoría nueva funciona sin fotos.
FOTOS_CATEGORIA = {
    "Automóviles": "automoviles.jpg",
    "Relojes": "relojes.jpg",
    "Videojuegos": "videojuegos.jpg",
    "Artículos de oficina": "articulos-de-oficina.jpg",
}


@register.filter
def icono_categoria(categoria) -> str:
    """URL del ícono de una categoría (objeto o nombre); el genérico si no tiene uno propio."""
    from django.templatetags.static import static

    nombre = getattr(categoria, "nombre", categoria)
    return static(f"subastas/iconos/{ICONOS_CATEGORIA.get(nombre, ICONO_GENERICO)}.svg")


@register.filter
def foto_categoria(categoria) -> str:
    """URL de la foto de portada de una categoría (objeto o nombre); cadena vacía si no tiene."""
    from django.templatetags.static import static

    archivo = FOTOS_CATEGORIA.get(getattr(categoria, "nombre", categoria))
    return static(f"subastas/categorias/{archivo}") if archivo else ""


@register.inclusion_tag("subastas/_tarjetas_categoria.html")
def tarjetas_categoria(entrar=False):
    """Portada: una tarjeta con foto por categoría registrada hacia el buscador (CU-08) con ?categoria=.

    Con `entrar`, la tarjeta lleva a Entrar y `next` devuelve al listado ya filtrado.
    """
    from subastas.models import Categoria

    return {"categorias": Categoria.objects.all(), "entrar": entrar}


@register.inclusion_tag("subastas/_accesos_categoria.html")
def accesos_categoria(activa="", entrar=False):
    """Listado (CU-08): un chip por categoría registrada hacia el buscador con ?categoria=<nombre>.

    Con `entrar`, el chip lleva a Entrar y `next` devuelve al listado ya filtrado. `activa` es el
    nombre de la categoría filtrada: su chip se marca con aria-current.
    """
    from subastas.models import Categoria

    return {"categorias": Categoria.objects.all(), "activa": activa or "", "entrar": entrar}
