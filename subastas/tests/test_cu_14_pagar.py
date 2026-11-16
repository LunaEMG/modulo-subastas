"""CU-14 Pagar una subasta ganada dentro del plazo (Comprador), con la solicitud a logística."""
from django.urls import reverse

from subastas.models import Adjudicacion
from subastas.reglas.pagos import EstadoAdjudicacion
from subastas.servicios import pujas

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

    def test_pagar_pasa_por_revisa_y_confirma(self):
        """Rediseño (fase C): «Pagar» lleva a una confirmación con monto y fecha límite; mostrarla no cobra."""
        confirmar = reverse("confirmar_pago", args=[self.adjudicacion.pk])
        self.assertContains(self.client.get(reverse("historial")), confirmar)
        pantalla = self.client.get(confirmar)
        self.assertContains(pantalla, "Revisa y confirma")
        self.assertContains(pantalla, "Pagar 1,500 fichas")
        self.assertContains(pantalla, "Fecha límite")
        self.adjudicacion.refresh_from_db()
        self.assertEqual(self.adjudicacion.estado, EstadoAdjudicacion.PENDIENTE_PAGO)

    def test_la_confirmacion_de_pago_es_solo_del_ganador_y_solo_si_falta_pagar(self):
        """Rediseño (fase C): otro comprador recibe 404; una adjudicación pagada regresa al historial."""
        confirmar = reverse("confirmar_pago", args=[self.adjudicacion.pk])
        self.client.post(reverse("pagar", args=[self.adjudicacion.pk]))
        self.assertRedirects(self.client.get(confirmar), reverse("historial"))
        self.client.force_login(self.crear_comprador())
        self.assertEqual(self.client.get(confirmar).status_code, 404)
