"""RN-08: la modificación debe superar la oferta actual y la puja propia anterior. (CU-10)"""
from subastas.reglas import pujas as reglas_pujas
from subastas.servicios import consultas, pujas

from .base import PruebaSubastas


class RN08Modificacion(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(costo_salida=900)
        self.ana = self.crear_comprador()
        self.beto = self.crear_comprador()
        pujas.pujar(comprador=self.ana, subasta_id=self.subasta.pk, monto=1000)
        pujas.pujar(comprador=self.beto, subasta_id=self.subasta.pk, monto=1200)

    def _modificar(self, comprador, monto):
        return pujas.modificar_puja(comprador=comprador, subasta_id=self.subasta.pk, nuevo_monto=monto)

    def test_valido_propia_1000_actual_1200_nueva_1300(self):
        puja = self._modificar(self.ana, 1300)
        self.assertEqual(puja.monto, 1300)
        self.assertEqual(consultas.precio_actual(self.subasta), 1300)
        movimiento = puja.movimientos.last()
        self.assertEqual((movimiento.tipo, movimiento.monto_anterior, movimiento.monto_nuevo), ("MODIFICACION", 1000, 1300))
        # Beto quedó superado y se le avisa.
        self.assertTrue(self.beto.notificaciones.filter(tipo="MSG-36").exists())

    def test_invalido_propia_1000_actual_1200_nueva_1100(self):
        self.assertErrorDeNegocio("ERR-08", self._modificar, self.ana, 1100)

    def test_invalido_el_lider_no_repite_su_monto(self):
        self.assertErrorDeNegocio("ERR-08", self._modificar, self.beto, 1200)

    def test_valido_el_lider_sube_su_propia_puja(self):
        self.assertEqual(self._modificar(self.beto, 1250).monto, 1250)

    def test_invalido_modificar_con_la_subasta_cerrada(self):
        self.reloj.avanzar(hours=25)
        self.assertErrorDeNegocio("ERR-08", self._modificar, self.ana, 5000)

    def test_err_37_sin_puja_activa_no_se_modifica(self):
        self.assertErrorDeNegocio("ERR-37", self._modificar, self.crear_comprador(), 5000)

    def test_regla_pura(self):
        reglas_pujas.validar_modificacion(
            nuevo_monto=1300, precio_actual=1200, monto_anterior=1000, subasta_abierta=True
        )
        for caso in (
            {"nuevo_monto": 1100, "precio_actual": 1200, "monto_anterior": 1000, "subasta_abierta": True},
            {"nuevo_monto": 1300, "precio_actual": 1200, "monto_anterior": 1000, "subasta_abierta": False},
        ):
            with self.subTest(caso=caso):
                self.assertErrorDeNegocio("ERR-08", reglas_pujas.validar_modificacion, **caso)
