"""CU-11 Retirar su puja (Comprador)."""
from django.urls import reverse

from subastas.models import Puja

from .base import PruebaSubastas


class CU11RetirarPuja(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(costo_salida=1000, duracion_horas=24)
        self.client.force_login(self.crear_comprador())
        self.detalle = reverse("detalle_subasta", args=[self.subasta.pk])
        self.client.post(reverse("pujar", args=[self.subasta.pk]), {"monto": "1200"})

    def test_ca_11_1_con_la_subasta_abierta_la_puja_se_retira(self):
        """CA-11.1 Con la subasta abierta la puja se retira (MSG-14) y queda registrada como «Retirada»."""
        self.client.post(reverse("retirar_puja", args=[self.subasta.pk]))
        self.assertContains(self.client.get(self.detalle), "MSG-14")
        self.assertEqual(Puja.objects.get().estado, Puja.Estado.RETIRADA)

    def test_ca_11_2_al_retirarse_el_precio_actual_regresa(self):
        """CA-11.2 Al retirar la puja más alta, el precio actual regresa al precio de salida (S-03)."""
        self.client.post(reverse("retirar_puja", args=[self.subasta.pk]))
        self.assertContains(self.client.get(self.detalle), "Puja mínima 1,001 fichas")

    def test_ca_11_3_con_la_subasta_cerrada_no_se_retira(self):
        """CA-11.3 Después del cierre la puja ya no se puede retirar (RN-07)."""
        self.reloj.avanzar(hours=24)
        respuesta = self.client.post(reverse("retirar_puja", args=[self.subasta.pk]), follow=True, **self.desde(self.detalle))
        self.assertContains(respuesta, "ERR-07")
        self.assertEqual(Puja.objects.get().estado, Puja.Estado.ACTIVA)
