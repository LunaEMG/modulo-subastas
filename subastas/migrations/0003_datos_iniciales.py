"""Catálogos fijos: los cuatro roles y las cuatro categorías que se subastan."""
from django.db import migrations

from subastas.reglas.articulos import CATEGORIAS_PERMITIDAS

ROLES = ["VENDEDOR", "COMPRADOR", "GESTOR", "MODERADOR"]


def cargar(apps, schema_editor):
    Rol = apps.get_model("subastas", "Rol")
    Categoria = apps.get_model("subastas", "Categoria")
    for nombre in ROLES:
        Rol.objects.get_or_create(nombre=nombre)
    # RN-01 y S-09: las categorías y su paso por el valuador salen de la regla.
    for nombre, requiere_valuacion in CATEGORIAS_PERMITIDAS.items():
        Categoria.objects.get_or_create(
            nombre=nombre, defaults={"requiere_valuacion": requiere_valuacion}
        )


class Migration(migrations.Migration):
    dependencies = [("subastas", "0002_fotografia_retirada")]

    operations = [migrations.RunPython(cargar, migrations.RunPython.noop)]
