"""CU-13 Consultar historial de pujas y subastas ganadas (Comprador)."""
from django.urls import reverse

from .base import PruebaSubastas


class CU13Historial(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(costo_salida=1000, tipo="COMPRA_INMEDIATA", precio_compra_inmediata=5000)
        self.client.force_login(self.crear_comprador())

    def test_ca_13_1_el_historial_muestra_la_bitacora_de_cada_puja(self):
        """CA-13.1 El historial muestra cada puja con su bitácora de creación y modificaciones."""
        self.client.post(reverse("pujar", args=[self.subasta.pk]), {"monto": "1200"})
        self.client.post(reverse("modificar_puja", args=[self.subasta.pk]), {"monto": "1300"})
        historial = self.client.get(reverse("historial"))
        self.assertContains(historial, "Creación")
        self.assertContains(historial, "Modificación")

    def test_ca_13_2_las_subastas_ganadas_aparecen_con_su_estado_de_pago(self):
        """CA-13.2 Las subastas ganadas aparecen como «Pendiente de pago» con su fecha límite."""
        self.client.post(reverse("comprar_de_inmediato", args=[self.subasta.pk]))
        historial = self.client.get(reverse("historial"))
        self.assertContains(historial, "Pendiente de pago")
        self.assertContains(historial, "límite")
