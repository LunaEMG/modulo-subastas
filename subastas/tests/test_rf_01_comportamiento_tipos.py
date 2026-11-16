"""RF-01: comportamiento de cada tipo de subasta al pujar (S-01, S-02, S-07, S-19). (CU-09, CU-12)"""
from datetime import timedelta

from subastas.reglas.estados import EstadoArticulo, EstadoSubasta
from subastas.servicios import consultas, pujas

from .base import INICIO, PruebaSubastas

HOLANDESA = {
    "tipo": "HOLANDESA",
    "holandesa_precio_inicial": 2000,
    "holandesa_decremento": 300,
    "holandesa_intervalo_min": 60,
}


class SubastaHolandesa(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(costo_salida=1000, duracion_horas=24, **{
            k: v for k, v in HOLANDESA.items() if k != "tipo"
        }, tipo="HOLANDESA")
        self.comprador = self.crear_comprador()

    def test_s01_el_precio_baja_cada_intervalo_hasta_el_minimo(self):
        esperados = [(0, 2000), (59, 2000), (60, 1700), (120, 1400), (180, 1100), (240, 1000), (600, 1000)]
        for minutos, precio in esperados:
            with self.subTest(minutos=minutos):
                self.assertEqual(
                    consultas.precio_actual(self.subasta, INICIO + timedelta(minutes=minutos)), precio
                )

    def test_s01_gana_el_primero_que_acepta_el_precio_vigente(self):
        self.reloj.avanzar(minutes=130)
        adjudicacion = pujas.aceptar_precio_holandesa(comprador=self.comprador, subasta_id=self.subasta.pk)
        self.assertEqual((adjudicacion.ganador, adjudicacion.precio_final), (self.comprador, 1400))
        self.assertEqual(adjudicacion.comision, 350)
        self.subasta.refresh_from_db()
        self.assertEqual(self.subasta.estado, EstadoSubasta.CERRADA_CON_GANADOR)
        self.assertEqual(self.subasta.articulo.estado, EstadoArticulo.ADJUDICADO)
        # El segundo ya no puede aceptar.
        self.assertErrorDeNegocio(
            "ERR-36", pujas.aceptar_precio_holandesa, comprador=self.crear_comprador(), subasta_id=self.subasta.pk
        )

    def test_s19_la_aceptacion_es_definitiva(self):
        pujas.aceptar_precio_holandesa(comprador=self.comprador, subasta_id=self.subasta.pk)
        self.assertErrorDeNegocio(
            "ERR-07", pujas.retirar_puja, comprador=self.comprador, subasta_id=self.subasta.pk
        )

    def test_err_39_en_holandesa_no_se_puja_al_alza(self):
        self.assertErrorDeNegocio(
            "ERR-39", pujas.pujar, comprador=self.comprador, subasta_id=self.subasta.pk, monto=2500
        )

    def test_err_39_en_una_inglesa_no_se_acepta_precio_holandes(self):
        inglesa = self.subasta_abierta()
        self.assertErrorDeNegocio(
            "ERR-39", pujas.aceptar_precio_holandesa, comprador=self.comprador, subasta_id=inglesa.pk
        )


class SubastaCompraInmediata(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(
            costo_salida=1000, tipo="COMPRA_INMEDIATA", precio_compra_inmediata=3000
        )
        self.ana = self.crear_comprador()
        self.beto = self.crear_comprador()

    def test_s07_comprar_ya_adjudica_al_precio_fijo(self):
        pujas.pujar(comprador=self.ana, subasta_id=self.subasta.pk, monto=1500)
        adjudicacion = pujas.comprar_de_inmediato(comprador=self.beto, subasta_id=self.subasta.pk)
        self.assertEqual((adjudicacion.ganador, adjudicacion.precio_final), (self.beto, 3000))
        self.assertEqual(adjudicacion.monto_vendedor, 2250)
        self.assertErrorDeNegocio(
            "ERR-36", pujas.pujar, comprador=self.ana, subasta_id=self.subasta.pk, monto=4000
        )

    def test_s07_quien_ya_pujo_tambien_puede_comprar_ya(self):
        pujas.pujar(comprador=self.ana, subasta_id=self.subasta.pk, monto=1500)
        adjudicacion = pujas.comprar_de_inmediato(comprador=self.ana, subasta_id=self.subasta.pk)
        self.assertEqual(adjudicacion.precio_final, 3000)

    def test_s07_deja_de_ofrecerse_cuando_una_puja_lo_alcanza(self):
        pujas.pujar(comprador=self.ana, subasta_id=self.subasta.pk, monto=3000)
        self.assertErrorDeNegocio(
            "ERR-39", pujas.comprar_de_inmediato, comprador=self.beto, subasta_id=self.subasta.pk
        )
        # Sigue siendo una subasta inglesa.
        pujas.pujar(comprador=self.beto, subasta_id=self.subasta.pk, monto=3100)

    def test_err_39_otro_tipo_no_ofrece_compra_inmediata(self):
        inglesa = self.subasta_abierta()
        self.assertErrorDeNegocio(
            "ERR-39", pujas.comprar_de_inmediato, comprador=self.ana, subasta_id=inglesa.pk
        )

    def test_ganador_y_vendedor_reciben_aviso(self):
        pujas.comprar_de_inmediato(comprador=self.ana, subasta_id=self.subasta.pk)
        self.assertTrue(self.ana.notificaciones.filter(tipo="MSG-37").exists())
        self.assertTrue(self.vendedor.notificaciones.filter(tipo="MSG-38").exists())


class SubastaReservada(PruebaSubastas):
    def test_s02_el_precio_reservado_no_se_muestra_solo_si_se_alcanzo(self):
        subasta = self.subasta_abierta(costo_salida=1000, tipo="RESERVADA", precio_reserva=2000)
        comprador = self.crear_comprador()
        resumen = consultas.resumen_subasta(subasta, comprador)
        self.assertEqual(resumen["precio_actual"], 1000)
        self.assertFalse(resumen["reserva_alcanzada"])
        pujas.pujar(comprador=comprador, subasta_id=subasta.pk, monto=2000)
        self.assertTrue(consultas.resumen_subasta(subasta, comprador)["reserva_alcanzada"])
