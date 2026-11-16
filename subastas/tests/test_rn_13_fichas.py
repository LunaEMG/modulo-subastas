"""RN-13: la moneda son fichas electrónicas enteras; 1 peso = 1 ficha."""
from django.test import SimpleTestCase

from subastas.mensajes import ErrorDeNegocio
from subastas.reglas import dinero


class RN13Fichas(SimpleTestCase):
    def test_valido_monto_entero_positivo(self):
        self.assertEqual(dinero.validar_monto_fichas(1500), 1500)
        self.assertEqual(dinero.validar_monto_fichas("1500"), 1500)

    def test_valido_un_peso_es_una_ficha(self):
        self.assertEqual(dinero.pesos_a_fichas(1500), 1500)

    def test_invalido_montos_con_decimales_cero_o_negativos(self):
        for monto in (1500.50, "1500.50", 0, -10, "abc", "", None, True):
            with self.subTest(monto=monto), self.assertRaises(ErrorDeNegocio) as contexto:
                dinero.validar_monto_fichas(monto)
            self.assertEqual(contexto.exception.codigo, "ERR-13")
