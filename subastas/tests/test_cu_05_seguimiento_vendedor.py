"""CU-05 Dar seguimiento a sus artículos y subastas (Vendedor), con el resultado de la venta."""
from django.urls import reverse

from subastas.servicios import cierre, pujas

from .base import PruebaSubastas


class CU05Seguimiento(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(costo_salida=1000, duracion_horas=24)
        self.client.force_login(self.vendedor)
        self.url = reverse("detalle_articulo", args=[self.subasta.articulo_id])

    def test_ca_05_1_el_vendedor_ve_sus_articulos_y_el_estado_de_cada_uno(self):
        """CA-05.1 «Mis artículos» lista los artículos del vendedor y el detalle muestra la subasta «Abierta»."""
        self.assertContains(self.client.get(reverse("mis_articulos")), "Reloj de prueba")
        self.assertContains(self.client.get(self.url), "Abierta")

    def test_ca_05_2_al_venderse_ve_precio_final_comision_y_monto_neto(self):
        """CA-05.2 Al adjudicarse, el detalle muestra precio final, comisión del 25 % y lo que recibirá (RN-14, S-04)."""
        pujas.pujar(comprador=self.crear_comprador(), subasta_id=self.subasta.pk, monto=2000)
        self.reloj.avanzar(hours=24)
        cierre.procesar_pendientes()
        detalle = self.client.get(self.url)
        self.assertContains(detalle, "Comisión (25 %)")
        self.assertContains(detalle, "500 fichas")
        self.assertContains(detalle, "Recibirás")
        self.assertContains(detalle, "1,500 fichas")

    def test_ca_05_3_otro_vendedor_no_ve_el_articulo_err_43(self):
        """CA-05.3 Un vendedor no puede consultar el artículo de otro (ERR-43)."""
        self.client.force_login(self.crear_vendedor())
        self.assertContains(self.client.get(self.url, follow=True), "ERR-43")
