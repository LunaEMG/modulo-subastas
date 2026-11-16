"""CU-15 Cerrar subasta y determinar ganador (actor Tiempo)."""
from io import StringIO

from django.core.management import call_command
from django.urls import reverse

from subastas.models import Adjudicacion
from subastas.reglas.estados import EstadoSubasta
from subastas.servicios import pujas

from .base import PruebaSubastas


class CU15CerrarSubasta(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(costo_salida=1000, duracion_horas=24)
        self.comprador = self.crear_comprador()
        pujas.pujar(comprador=self.comprador, subasta_id=self.subasta.pk, monto=1500)

    def test_ca_15_1_al_abrir_cualquier_pagina_se_cierra_lo_vencido(self):
        """CA-15.1 Al llegar la fecha de cierre, la siguiente petición cierra la subasta con la puja más alta como ganadora."""
        self.reloj.avanzar(hours=24)
        self.client.get(reverse("inicio"))
        self.subasta.refresh_from_db()
        self.assertEqual(self.subasta.estado, EstadoSubasta.CERRADA_CON_GANADOR)
        self.assertEqual(Adjudicacion.objects.get().ganador, self.comprador)

    def test_ca_15_2_antes_del_cierre_la_subasta_sigue_abierta(self):
        """CA-15.2 Antes de la fecha de cierre la subasta no se cierra (RN-09)."""
        self.reloj.avanzar(hours=23, minutes=59)
        self.client.get(reverse("inicio"))
        self.subasta.refresh_from_db()
        self.assertEqual(self.subasta.estado, EstadoSubasta.ABIERTA)

    def test_ca_15_3_el_comando_procesar_subastas_cierra_lo_vencido(self):
        """CA-15.3 El comando procesar_subastas cierra las subastas vencidas (para programarlo con cron)."""
        self.reloj.avanzar(hours=24)
        salida = StringIO()
        call_command("procesar_subastas", stdout=salida)
        self.assertIn("Subastas cerradas: 1", salida.getvalue())

    def test_ca_15_4_el_ganador_y_el_vendedor_reciben_su_aviso(self):
        """CA-15.4 Al cerrar con ganador, el ganador recibe MSG-37 y el vendedor MSG-38 (RN-10)."""
        self.reloj.avanzar(hours=24)
        self.client.get(reverse("inicio"))
        self.assertTrue(self.comprador.notificaciones.filter(tipo="MSG-37").exists())
        self.assertTrue(self.vendedor.notificaciones.filter(tipo="MSG-38").exists())
