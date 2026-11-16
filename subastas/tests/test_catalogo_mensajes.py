"""El catálogo central es la única fuente de mensajes: todo ID usado existe y
todo ID del catálogo se usa en algún lugar del código o las plantillas."""
import re
from pathlib import Path

from django.test import SimpleTestCase

from subastas import mensajes

RAIZ = Path(mensajes.__file__).resolve().parent
PATRON = re.compile(r"\b(?:ERR|MSG)-\d{2}\b")


def _archivos():
    for ruta in RAIZ.rglob("*"):
        if ruta.suffix in {".py", ".html"} and "tests" not in ruta.parts and ruta.name != "mensajes.py":
            yield ruta


class CatalogoDeMensajes(SimpleTestCase):
    def test_todo_id_usado_existe_en_el_catalogo(self):
        for ruta in _archivos():
            for codigo in PATRON.findall(ruta.read_text(encoding="utf-8")):
                with self.subTest(archivo=ruta.name, codigo=codigo):
                    self.assertIn(codigo, mensajes.CATALOGO)

    def test_todo_id_del_catalogo_se_usa(self):
        usados = set()
        for ruta in _archivos():
            usados.update(PATRON.findall(ruta.read_text(encoding="utf-8")))
        sin_uso = sorted(set(mensajes.CATALOGO) - usados)
        self.assertEqual(sin_uso, [], "IDs del catálogo que nadie usa")

    def test_error_desconocido_falla(self):
        with self.assertRaises(KeyError):
            mensajes.ErrorDeNegocio("ERR-99")
