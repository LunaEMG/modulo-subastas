"""CU-12 Comprar de inmediato (Comprador)."""
from django.urls import reverse

from subastas.models import Adjudicacion

from .base import PruebaSubastas


class CU12ComprarDeInmediato(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(costo_salida=1000, tipo="COMPRA_INMEDIATA", precio_compra_inmediata=5000)
        self.comprador = self.crear_comprador()
        self.client.force_login(self.comprador)
        self.detalle = reverse("detalle_subasta", args=[self.subasta.pk])

    def test_ca_12_1_comprar_ya_adjudica_al_precio_fijo(self):
        """CA-12.1 «Comprar ya» adjudica el artículo al precio fijo y cierra la subasta (MSG-15, S-07)."""
        self.client.post(reverse("comprar_de_inmediato", args=[self.subasta.pk]))
        detalle = self.client.get(self.detalle)
        self.assertContains(detalle, "MSG-15")
        self.assertContains(detalle, "Ganaste")
        adjudicacion = Adjudicacion.objects.get()
        self.assertEqual((adjudicacion.ganador, adjudicacion.precio_final), (self.comprador, 5000))

    def test_ca_12_2_otros_tipos_no_ofrecen_comprar_ya_err_39(self):
        """CA-12.2 Una subasta que no es de compra inmediata rechaza «Comprar ya» con ERR-39."""
        inglesa = self.subasta_abierta()
        url = reverse("detalle_subasta", args=[inglesa.pk])
        respuesta = self.client.post(reverse("comprar_de_inmediato", args=[inglesa.pk]), follow=True, **self.desde(url))
        self.assertContains(respuesta, "ERR-39")

    def test_comprar_ya_pasa_por_revisa_y_confirma(self):
        """Rediseño (fase C): «Comprar ya» lleva a una confirmación con el monto; mostrarla no adjudica."""
        confirmar = reverse("confirmar_compra_inmediata", args=[self.subasta.pk])
        detalle = self.client.get(self.detalle)
        self.assertContains(detalle, confirmar)
        self.assertNotContains(detalle, f'action="{reverse("comprar_de_inmediato", args=[self.subasta.pk])}"')
        pantalla = self.client.get(confirmar)
        self.assertContains(pantalla, "Revisa y confirma")
        self.assertContains(pantalla, "Comprar ya por 5,000 fichas")
        self.assertContains(pantalla, reverse("comprar_de_inmediato", args=[self.subasta.pk]))
        self.assertFalse(Adjudicacion.objects.exists())

    def test_la_confirmacion_no_aplica_a_una_subasta_sin_compra_inmediata(self):
        """Rediseño (fase C): en una subasta sin compra inmediata, la confirmación regresa al detalle."""
        inglesa = self.subasta_abierta()
        respuesta = self.client.get(reverse("confirmar_compra_inmediata", args=[inglesa.pk]))
        self.assertRedirects(respuesta, reverse("detalle_subasta", args=[inglesa.pk]))
