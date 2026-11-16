"""RN-06: una puja debe incrementar el precio actual. (CU-09)"""
from subastas.models import MovimientoPuja, Puja
from subastas.reglas import pujas as reglas_pujas
from subastas.servicios import consultas, pujas

from .base import PruebaSubastas


class RN06Pujar(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(costo_salida=1000)
        self.comprador = self.crear_comprador()

    def _pujar(self, monto, comprador=None):
        return pujas.pujar(comprador=comprador or self.comprador, subasta_id=self.subasta.pk, monto=monto)

    def test_valido_puja_de_1001_sobre_precio_actual_de_1000(self):
        puja = self._pujar(1001)
        self.assertEqual(puja.estado, Puja.Estado.ACTIVA)
        self.assertEqual(consultas.precio_actual(self.subasta), 1001)
        self.assertEqual(
            list(puja.movimientos.values_list("tipo", "monto_nuevo")),
            [(MovimientoPuja.Tipo.CREACION, 1001)],
        )

    def test_invalido_puja_igual_al_precio_actual(self):
        error = self.assertErrorDeNegocio("ERR-06", self._pujar, 1000)
        self.assertIn("1,001", error.mensaje)
        self.assertEqual(Puja.objects.count(), 0)

    def test_invalido_puja_que_no_supera_a_la_mas_alta(self):
        self._pujar(1500)
        self.assertErrorDeNegocio("ERR-06", self._pujar, 1500, self.crear_comprador())

    def test_valido_rn04_no_hay_precio_maximo(self):
        self._pujar(9_999_999)
        self.assertEqual(consultas.precio_actual(self.subasta), 9_999_999)

    def test_invalido_rn13_monto_con_decimales(self):
        self.assertErrorDeNegocio("ERR-13", self._pujar, "1500.5")

    def test_err_38_una_sola_puja_activa_por_comprador(self):
        self._pujar(1100)
        self.assertErrorDeNegocio("ERR-38", self._pujar, 1200)

    def test_err_41_s13_el_vendedor_no_puja_en_su_subasta(self):
        self.vendedor.roles.add(*self.comprador.roles.all())
        self.vendedor = type(self.vendedor).objects.get(pk=self.vendedor.pk)
        self.assertErrorDeNegocio("ERR-41", self._pujar, 1100, self.vendedor)

    def test_err_36_no_se_puja_despues_del_cierre(self):
        self.reloj.avanzar(hours=24)
        self.assertErrorDeNegocio("ERR-36", self._pujar, 1100)

    def test_s12_se_puede_pujar_un_segundo_antes_del_cierre(self):
        self.reloj.avanzar(hours=23, minutes=59, seconds=59)
        self._pujar(1100)
        self.subasta.refresh_from_db()
        self.assertEqual(self.subasta.duracion_horas, 24)

    def test_err_32_solo_los_compradores_pujan(self):
        self.assertErrorDeNegocio("ERR-32", self._pujar, 1100, self.gestor)

    def test_el_comprador_superado_recibe_aviso(self):
        self._pujar(1100)
        otro = self.crear_comprador()
        self._pujar(1200, otro)
        aviso = self.comprador.notificaciones.get(tipo="MSG-36")
        self.assertIn("1,200", aviso.mensaje)
        self.assertFalse(otro.notificaciones.filter(tipo="MSG-36").exists())

    def test_regla_pura(self):
        reglas_pujas.validar_puja(monto=1001, precio_actual=1000)
        self.assertErrorDeNegocio("ERR-06", reglas_pujas.validar_puja, monto=1000, precio_actual=1000)
