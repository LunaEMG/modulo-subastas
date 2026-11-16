"""RN-14: la casa cobra 25 % de comisión sobre el precio final (con S-21 y S-04)."""
from django.test import SimpleTestCase

from subastas.mensajes import ErrorDeNegocio
from subastas.reglas import dinero


class RN14Comision(SimpleTestCase):
    def test_valido_precio_1000_comision_250_vendedor_750(self):
        comision = dinero.calcular_comision(1000)
        self.assertEqual(comision, 250)
        self.assertEqual(dinero.calcular_monto_vendedor(1000, comision), 750)
        dinero.validar_comision(precio_final=1000, comision=250)

    def test_valido_s21_precio_1001_comision_250_vendedor_751(self):
        """S-21: el 25 % de 1 001 es 250.25; se redondea hacia abajo y la diferencia es del vendedor."""
        comision = dinero.calcular_comision(1001)
        self.assertEqual(comision, 250)
        self.assertEqual(dinero.calcular_monto_vendedor(1001, comision), 751)

    def test_valido_comision_mas_vendedor_suma_el_precio_final(self):
        for precio in (1, 3, 999, 1001, 1003, 123457):
            with self.subTest(precio=precio):
                comision = dinero.calcular_comision(precio)
                self.assertEqual(comision + dinero.calcular_monto_vendedor(precio, comision), precio)

    def test_invalido_comision_distinta_del_25_por_ciento(self):
        with self.assertRaises(ErrorDeNegocio) as contexto:
            dinero.validar_comision(precio_final=1000, comision=100)
        self.assertEqual(contexto.exception.codigo, "ERR-14")
