"""CU-10 Modificar su puja (Comprador)."""
from django.urls import reverse

from subastas.models import Puja

from .base import PruebaSubastas


class CU10ModificarPuja(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(costo_salida=1000)
        self.client.force_login(self.crear_comprador())
        self.detalle = reverse("detalle_subasta", args=[self.subasta.pk])
        self.client.post(reverse("pujar", args=[self.subasta.pk]), {"monto": "1200"})

    def test_ca_10_1_subir_la_propia_puja_se_acepta(self):
        """CA-10.1 Subir la propia puja por encima de la anterior se acepta y queda una sola puja activa (MSG-13)."""
        self.client.post(reverse("modificar_puja", args=[self.subasta.pk]), {"monto": "1300"})
        self.assertContains(self.client.get(self.detalle), "MSG-13")
        self.assertEqual(Puja.objects.get().monto, 1300)

    def test_ca_10_2_bajar_la_puja_se_rechaza_con_err_08(self):
        """CA-10.2 Un nuevo monto que no supera la puja anterior se rechaza con ERR-08 (RN-08)."""
        respuesta = self.client.post(reverse("modificar_puja", args=[self.subasta.pk]), {"monto": "1100"}, follow=True, **self.desde(self.detalle))
        self.assertContains(respuesta, "ERR-08")
        self.assertEqual(Puja.objects.get().monto, 1200)

    def test_ca_10_3_sin_puja_activa_no_hay_que_modificar_err_37(self):
        """CA-10.3 Quien no tiene puja activa no puede modificarla (ERR-37)."""
        self.client.force_login(self.crear_comprador())
        respuesta = self.client.post(reverse("modificar_puja", args=[self.subasta.pk]), {"monto": "1500"}, follow=True, **self.desde(self.detalle))
        self.assertContains(respuesta, "ERR-37")
