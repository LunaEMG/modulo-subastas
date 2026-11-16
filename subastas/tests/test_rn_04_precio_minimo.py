"""RN-04: precio mínimo propuesto por el vendedor y avalado por el valuador; sin precio máximo. (CU-06)"""
from subastas.reglas import precios
from subastas.reglas.estados import EstadoArticulo

from .base import PruebaSubastas


class RN04PrecioMinimo(PruebaSubastas):
    def test_valido_precio_avalado_es_el_precio_de_salida(self):
        subasta = self.subasta_abierta(costo_salida=5000)
        self.assertEqual(subasta.precio_salida, 5000)

    def test_s_32_el_precio_maximo_es_el_mayor_entero_que_guarda_la_base(self):
        """S-32 RN-04 no fija precio máximo; el tope es el límite de PositiveIntegerField."""
        self.assertEqual(precios.PRECIO_MAXIMO, 2_147_483_647)

    def test_s_32_un_costo_de_salida_al_tope_se_acepta_y_uno_mayor_no(self):
        """S-32 El costo de salida puede llegar al tope; uno mayor se rechaza con ERR-66."""
        self.assertEqual(self.subasta_abierta(costo_salida=precios.PRECIO_MAXIMO).precio_salida, precios.PRECIO_MAXIMO)
        self.assertErrorDeNegocio("ERR-66", self.registrar_articulo, costo_salida=precios.PRECIO_MAXIMO + 1)

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
