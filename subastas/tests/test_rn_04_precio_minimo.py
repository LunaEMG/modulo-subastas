"""RN-04: precio mínimo propuesto por el vendedor y avalado por el valuador; sin precio máximo. (CU-06)"""
from subastas.reglas import precios
from subastas.reglas.estados import EstadoArticulo

from .base import PruebaSubastas


class RN04PrecioMinimo(PruebaSubastas):
    def test_valido_precio_avalado_es_el_precio_de_salida(self):
        subasta = self.subasta_abierta(costo_salida=5000)
        self.assertEqual(subasta.precio_salida, 5000)

    def test_valido_no_existe_precio_maximo(self):
        self.assertIsNone(precios.PRECIO_MAXIMO)
        # Una puja altísima no se rechaza por ser alta: se prueba en RN-06.

    def test_invalido_articulo_no_autentico_no_se_subasta(self):
        self.valuador.es_autentico = False
        articulo = self.articulo_listo()
        self.assertEqual(articulo.estado, EstadoArticulo.NO_AVALADO)
        self.assertErrorDeNegocio("ERR-05", self.proponer, articulo)
        self.assertIn("MSG-33", self.vendedor.notificaciones.values_list("tipo", flat=True))

    def test_invalido_precio_no_avalado_no_se_subasta(self):
        self.valuador.avala = False
        articulo = self.articulo_listo()
        self.assertEqual(articulo.estado, EstadoArticulo.NO_AVALADO)

    def test_regla_pura(self):
        self.assertEqual(
            precios.precio_minimo_avalado(
                costo_salida=1000, requiere_valuacion=True, es_autentico=True, precio_avalado=900
            ),
            900,
        )
        self.assertEqual(
            precios.precio_minimo_avalado(
                costo_salida=1000, requiere_valuacion=False, es_autentico=False, precio_avalado=None
            ),
            1000,
        )
        self.assertErrorDeNegocio(
            "ERR-04",
            precios.precio_minimo_avalado,
            costo_salida=1000,
            requiere_valuacion=True,
            es_autentico=False,
            precio_avalado=None,
        )
