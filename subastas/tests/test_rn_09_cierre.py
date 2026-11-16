"""RN-09: al llegar el cierre gana la puja más alta y fija el precio final. (CU-15)"""
from datetime import timedelta

from subastas.models import Adjudicacion, Puja
from subastas.reglas import cierre as reglas
from subastas.reglas.estados import EstadoArticulo, EstadoSubasta
from subastas.servicios import cierre, pujas

from .base import INICIO, PruebaSubastas


class ReglaCierre(PruebaSubastas):
    def test_gana_la_puja_mas_alta(self):
        ofertas = [Puja(monto=1200), Puja(monto=1500), Puja(monto=1300)]
        self.assertEqual(reglas.determinar_puja_ganadora(ofertas).monto, 1500)

    def test_sin_pujas_no_hay_ganador(self):
        self.assertIsNone(reglas.determinar_puja_ganadora([]))

    def test_err_09_no_se_cierra_antes_de_tiempo(self):
        self.assertErrorDeNegocio(
            "ERR-09", reglas.validar_llego_el_cierre,
            fecha_cierre=INICIO + timedelta(hours=1), instante=INICIO,
        )

    def test_se_cierra_justo_en_la_fecha(self):
        reglas.validar_llego_el_cierre(fecha_cierre=INICIO, instante=INICIO)


class CerrarSubasta(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(costo_salida=1000, duracion_horas=24)
        self.ana = self.crear_comprador()
        self.beto = self.crear_comprador()

    def test_al_cierre_la_puja_mas_alta_fija_el_precio_final(self):
        pujas.pujar(comprador=self.ana, subasta_id=self.subasta.pk, monto=1200)
        pujas.pujar(comprador=self.beto, subasta_id=self.subasta.pk, monto=1500)
        self.reloj.avanzar(hours=24)
        adjudicacion = cierre.cerrar_subasta(self.subasta.pk)
        self.assertEqual((adjudicacion.ganador, adjudicacion.precio_final), (self.beto, 1500))
        self.assertEqual(adjudicacion.comision, 375)
        self.assertEqual(adjudicacion.fecha, INICIO + timedelta(hours=24))
        self.subasta.refresh_from_db()
        self.assertEqual(self.subasta.estado, EstadoSubasta.CERRADA_CON_GANADOR)
        self.assertEqual(self.subasta.articulo.estado, EstadoArticulo.ADJUDICADO)

    def test_una_puja_retirada_no_gana(self):
        pujas.pujar(comprador=self.ana, subasta_id=self.subasta.pk, monto=1200)
        pujas.pujar(comprador=self.beto, subasta_id=self.subasta.pk, monto=1500)
        pujas.retirar_puja(comprador=self.beto, subasta_id=self.subasta.pk)
        self.reloj.avanzar(hours=24)
        self.assertEqual(cierre.cerrar_subasta(self.subasta.pk).ganador, self.ana)

    def test_sin_pujas_queda_desierta_y_el_articulo_sin_vender(self):
        self.reloj.avanzar(hours=24)
        self.assertIsNone(cierre.cerrar_subasta(self.subasta.pk))
        self.subasta.refresh_from_db()
        self.assertEqual(self.subasta.estado, EstadoSubasta.DESIERTA)
        self.assertEqual(self.subasta.articulo.estado, EstadoArticulo.SIN_VENDER)
        self.assertFalse(Adjudicacion.objects.exists())

    def test_err_09_antes_del_cierre_no_se_cierra(self):
        pujas.pujar(comprador=self.ana, subasta_id=self.subasta.pk, monto=1200)
        self.reloj.avanzar(hours=23, minutes=59)
        self.assertErrorDeNegocio("ERR-09", cierre.cerrar_subasta, self.subasta.pk)
        self.subasta.refresh_from_db()
        self.assertEqual(self.subasta.estado, EstadoSubasta.ABIERTA)

    def test_err_36_no_se_cierra_dos_veces(self):
        self.reloj.avanzar(hours=24)
        cierre.cerrar_subasta(self.subasta.pk)
        self.assertErrorDeNegocio("ERR-36", cierre.cerrar_subasta, self.subasta.pk)

    def test_err_36_despues_del_cierre_ya_no_se_puja(self):
        self.reloj.avanzar(hours=24)
        self.assertErrorDeNegocio(
            "ERR-36", pujas.pujar, comprador=self.ana, subasta_id=self.subasta.pk, monto=1200
        )

    def test_procesar_pendientes_solo_cierra_lo_vencido(self):
        otra = self.subasta_abierta(duracion_horas=48)
        self.reloj.avanzar(hours=24)
        self.assertEqual(cierre.procesar_pendientes(), {"cerradas": 1, "resubastadas": 0})
        otra.refresh_from_db()
        self.assertEqual(otra.estado, EstadoSubasta.ABIERTA)
        # Una segunda pasada no vuelve a cerrar nada.
        self.assertEqual(cierre.procesar_pendientes(), {"cerradas": 0, "resubastadas": 0})
