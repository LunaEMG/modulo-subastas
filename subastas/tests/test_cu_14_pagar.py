"""CU-14 Pagar una subasta ganada dentro del plazo (Comprador), con la solicitud a logística."""
from django.urls import reverse

from subastas.models import Adjudicacion
from subastas.reglas.pagos import EstadoAdjudicacion
from subastas import reloj
from subastas.servicios import cierre as cierre_servicio
from subastas.servicios import consultas, pujas

from .base import PruebaSubastas


class CU14Pagar(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(costo_salida=1000, duracion_horas=24)
        self.comprador = self.crear_comprador()
        pujas.pujar(comprador=self.comprador, subasta_id=self.subasta.pk, monto=1500)
        self.client.force_login(self.comprador)
        self.reloj.avanzar(hours=24)
        self.client.get(reverse("inicio"))  # El actor Tiempo cierra la subasta.
        self.adjudicacion = Adjudicacion.objects.get(subasta=self.subasta)

    def test_ca_14_1_dentro_del_plazo_se_paga_desde_el_historial(self):
        """CA-14.1 Dentro del plazo el ganador paga desde su historial (MSG-16) y se pide la recolección (RF-03)."""
        self.assertContains(self.client.get(reverse("historial")), "Pagar 1,500 fichas")
        respuesta = self.client.post(reverse("pagar", args=[self.adjudicacion.pk]), follow=True)
        self.assertContains(respuesta, "MSG-16")
        self.assertContains(respuesta, "LOG-PRUEBA")
        self.adjudicacion.refresh_from_db()
        self.assertEqual(self.adjudicacion.estado, EstadoAdjudicacion.PAGADA)
        self.assertEqual(len(self.logistica.solicitudes), 1)

    def test_ca_14_2_despues_del_plazo_ya_no_se_puede_pagar(self):
        """CA-14.2 Pasados los 3 días el pago se rechaza: la adjudicación ya venció (ERR-44, RN-11)."""
        self.reloj.avanzar(days=3, seconds=1)
        respuesta = self.client.post(reverse("pagar", args=[self.adjudicacion.pk]), follow=True)
        self.assertContains(respuesta, "ERR-44")
        self.assertEqual(self.pagos.cobros, [])

    def test_ca_14_3_si_el_cobro_se_rechaza_la_adjudicacion_sigue_pendiente(self):
        """CA-14.3 Si el servicio de pagos rechaza el cobro se muestra ERR-45 y se puede reintentar."""
        self.pagos.aprueba = False
        respuesta = self.client.post(reverse("pagar", args=[self.adjudicacion.pk]), follow=True, **self.desde(reverse("historial")))
        self.assertContains(respuesta, "ERR-45")
        self.adjudicacion.refresh_from_db()
        self.assertEqual(self.adjudicacion.estado, EstadoAdjudicacion.PENDIENTE_PAGO)

    def test_ca_14_4_nadie_paga_una_subasta_ajena_err_43(self):
        """CA-14.4 Otro comprador no puede pagar la adjudicación de alguien más (ERR-43)."""
        self.client.force_login(self.crear_comprador())
        respuesta = self.client.post(reverse("pagar", args=[self.adjudicacion.pk]), follow=True)
        self.assertContains(respuesta, "ERR-43")

    def test_ca_14_5_pagar_pasa_por_revisa_y_confirma(self):
        """CA-14.5 «Pagar» lleva a «Revisa y confirma» con el monto y la fecha límite; mostrar la confirmación no cobra."""
        confirmar = reverse("confirmar_pago", args=[self.adjudicacion.pk])
        self.assertContains(self.client.get(reverse("historial")), confirmar)
        pantalla = self.client.get(confirmar)
        self.assertContains(pantalla, "Revisa y confirma")
        self.assertContains(pantalla, "Pagar 1,500 fichas")
        self.assertContains(pantalla, "Fecha límite")
        self.adjudicacion.refresh_from_db()
        self.assertEqual(self.adjudicacion.estado, EstadoAdjudicacion.PENDIENTE_PAGO)

    def test_ca_14_4_la_confirmacion_de_un_pago_ajeno_se_rechaza_err_43(self):
        """CA-14.4 Otro comprador no puede pagar la adjudicación de alguien más (ERR-43).

        Tampoco llega a la confirmación del pago."""
        self.client.force_login(self.crear_comprador())
        respuesta = self.client.get(reverse("confirmar_pago", args=[self.adjudicacion.pk]), follow=True)
        self.assertContains(respuesta, "ERR-43")
        self.assertNotContains(respuesta, "Revisa y confirma")

    def test_ca_14_6_una_adjudicacion_pagada_no_se_vuelve_a_pagar_err_44(self):
        """CA-14.6 Una adjudicación ya pagada no se vuelve a pagar ni a confirmar (ERR-44)."""
        self.client.post(reverse("pagar", args=[self.adjudicacion.pk]))
        confirmacion = self.client.get(reverse("confirmar_pago", args=[self.adjudicacion.pk]), follow=True)
        self.assertContains(confirmacion, "ERR-44")
        self.assertNotContains(confirmacion, "Revisa y confirma")
        segundo_pago = self.client.post(reverse("pagar", args=[self.adjudicacion.pk]), follow=True)
        self.assertContains(segundo_pago, "ERR-44")
        self.assertEqual(len(self.logistica.solicitudes), 1)

    def test_ca_14_7_el_pago_pendiente_se_ve_en_el_menu_y_en_inicio(self):
        """CA-14.7 El ganador ve su pago pendiente con un contador junto a «Mi historial» y en la tarjeta de inicio (S-34)."""
        respuesta = self.client.get(reverse("inicio"))
        self.assertEqual(consultas.pendientes_por_rol(self.comprador), {"comprador": 1})
        self.assertContains(respuesta, 'class="contador por-atender">1<', count=2)
        self.assertContains(respuesta, "pago pendiente")

    def test_ca_14_4_y_ca_05_3_un_id_inexistente_responde_404(self):
        """CA-14.4 y CA-05.3 Una adjudicación, subasta o artículo que no existe responde 404, no un error
        del servidor; lo ajeno sigue rechazándose con ERR-43."""
        self.assertEqual(self.client.post(reverse("pagar", args=[999999])).status_code, 404)
        self.assertEqual(self.client.post(reverse("pujar", args=[999999]), {"monto": 5000}).status_code, 404)
        self.client.force_login(self.vendedor)
        self.assertEqual(self.client.get(reverse("detalle_articulo", args=[999999])).status_code, 404)
        self.client.force_login(self.crear_vendedor())
        ajeno = self.client.get(reverse("detalle_articulo", args=[self.subasta.articulo_id]), follow=True)
        self.assertContains(ajeno, "ERR-43")

    def test_la_ficha_de_la_subasta_ganada_ofrece_pagar(self):
        """Con el pago pendiente, la ficha de la subasta ganada muestra el botón «Pagar» que lleva al pago."""
        ficha = self.client.get(reverse("detalle_subasta", args=[self.subasta.pk]))
        self.assertContains(ficha, f'href="{reverse("confirmar_pago", args=[self.adjudicacion.pk])}">Pagar 1,500 fichas</a>')
        cierre_servicio.pagar(comprador=self.comprador, adjudicacion_id=self.adjudicacion.pk)
        self.assertNotContains(self.client.get(reverse("detalle_subasta", args=[self.subasta.pk])), "Pagar 1,500 fichas")

    def test_la_ficha_cerrada_muestra_solo_el_precio_final_y_la_fecha_real(self):
        """Ya cerrada, la ficha no dice «Subastas abiertas» ni «Pujas activas», muestra «Precio final» sin «Precio actual» y el cierre con la fecha de la adjudicación."""
        html = self.client.get(reverse("detalle_subasta", args=[self.subasta.pk])).content.decode()
        self.assertNotIn("← Subastas abiertas", html)
        self.assertIn(f'href="{reverse("historial")}">← Mi historial</a>', html)
        self.assertNotIn("Pujas activas", html)
        self.assertNotIn("Precio actual", html)
        self.assertEqual(html.count("Precio final"), 1)
        self.assertIn(f"<dt>Cierre</dt><dd>{reloj.formato(self.adjudicacion.fecha)}</dd>", html)
