"""RN-01: solo se subastan automóviles, relojes, videojuegos y artículos de oficina. (CU-03)"""
from subastas.models import Articulo
from subastas.reglas import articulos as reglas_articulos
from subastas.reglas.articulos import ARTICULOS_DE_OFICINA, AUTOMOVILES, RELOJES, VIDEOJUEGOS

from .base import PruebaSubastas


class RN01Categorias(PruebaSubastas):
    def test_valido_las_cuatro_categorias_se_registran(self):
        for categoria in (AUTOMOVILES, RELOJES, VIDEOJUEGOS, ARTICULOS_DE_OFICINA):
            with self.subTest(categoria=categoria):
                articulo = self.registrar_articulo(categoria=categoria)
                self.assertEqual(articulo.categoria.nombre, categoria)

    def test_invalido_otra_categoria_se_rechaza(self):
        error = self.assertErrorDeNegocio("ERR-01", self.registrar_articulo, categoria="Joyería")
        self.assertIn("Joyería", error.mensaje)
        self.assertEqual(Articulo.objects.count(), 0)

    def test_regla_pura(self):
        reglas_articulos.validar_categoria(RELOJES)
        self.assertErrorDeNegocio("ERR-01", reglas_articulos.validar_categoria, "Arte")
