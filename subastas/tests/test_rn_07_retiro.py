"""RN-07: una puja solo puede retirarse mientras la subasta no haya cerrado. (CU-11, S-03)"""
from subastas.models import Puja
from subastas.reglas import pujas as reglas_pujas
from subastas.servicios import consultas, pujas

from .base import PruebaSubastas


class RN07Retiro(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(costo_salida=1000)
        self.ana = self.crear_comprador()
        self.beto = self.crear_comprador()

    def _pujar(self, comprador, monto):
        return pujas.pujar(comprador=comprador, subasta_id=self.subasta.pk, monto=monto)

    def _retirar(self, comprador):
        return pujas.retirar_puja(comprador=comprador, subasta_id=self.subasta.pk)

    def test_valido_retiro_con_la_subasta_abierta(self):
        self._pujar(self.ana, 1200)
        puja = self._retirar(self.ana)
        self.assertEqual(puja.estado, Puja.Estado.RETIRADA)
        self.assertEqual(list(puja.movimientos.values_list("tipo", flat=True)), ["CREACION", "RETIRO"])

    def test_invalido_retiro_con_la_subasta_cerrada(self):
        self._pujar(self.ana, 1200)
        self.reloj.avanzar(hours=24)
        self.assertErrorDeNegocio("ERR-07", self._retirar, self.ana)
        self.assertTrue(Puja.objects.filter(estado=Puja.Estado.ACTIVA).exists())

    def test_s03_al_retirar_la_mas_alta_el_precio_vuelve_a_la_siguiente(self):
        self._pujar(self.ana, 1200)
        self._pujar(self.beto, 1500)
        self._retirar(self.beto)
        self.assertEqual(consultas.precio_actual(self.subasta), 1200)

    def test_s03_sin_pujas_el_precio_vuelve_al_de_salida(self):
        self._pujar(self.ana, 1200)
        self._retirar(self.ana)
        self.assertEqual(consultas.precio_actual(self.subasta), 1000)

    def test_tras_retirar_puede_volver_a_pujar(self):
        self._pujar(self.ana, 1200)
        self._retirar(self.ana)
        self._pujar(self.ana, 1300)

    def test_err_37_sin_puja_activa_no_hay_que_retirar(self):
        self.assertErrorDeNegocio("ERR-37", self._retirar, self.ana)

    def test_regla_pura(self):
        reglas_pujas.validar_retiro(subasta_abierta=True)
        self.assertErrorDeNegocio("ERR-07", reglas_pujas.validar_retiro, subasta_abierta=False)
