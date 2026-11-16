"""CU-09 Pujar (Comprador), con el flujo alterno de aceptar el precio en la holandesa."""
from django.urls import reverse

from subastas.models import Puja
from subastas.servicios import pujas

from .base import PruebaSubastas


class CU09Pujar(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(costo_salida=1000)
        self.client.force_login(self.crear_comprador())
        self.detalle = reverse("detalle_subasta", args=[self.subasta.pk])

    def test_ca_09_1_una_puja_mayor_al_precio_actual_se_acepta(self):
        """CA-09.1 Una puja mayor al precio actual se acepta (MSG-12) y el comprador ve que va ganando."""
        self.client.post(reverse("pujar", args=[self.subasta.pk]), {"monto": "1200"})
        detalle = self.client.get(self.detalle)
        self.assertContains(detalle, "MSG-12")
        self.assertContains(detalle, "Vas ganando")
        self.assertEqual(Puja.objects.get().monto, 1200)

    def test_ca_09_2_una_puja_que_no_supera_el_precio_se_rechaza_con_err_06(self):
        """CA-09.2 Una puja que no supera el precio actual se rechaza con ERR-06 (RN-06)."""
        respuesta = self.client.post(reverse("pujar", args=[self.subasta.pk]), {"monto": "900"}, follow=True, **self.desde(self.detalle))
        self.assertContains(respuesta, "ERR-06")
        self.assertFalse(Puja.objects.exists())

    def test_ca_09_3_quien_es_superado_recibe_un_aviso(self):
        """CA-09.3 Al ser superada su puja, el comprador anterior recibe el aviso MSG-36 (S-28)."""
        primero = self.crear_comprador()
        pujas.pujar(comprador=primero, subasta_id=self.subasta.pk, monto=1100)
        self.client.post(reverse("pujar", args=[self.subasta.pk]), {"monto": "1200"})
        self.assertTrue(primero.notificaciones.filter(tipo="MSG-36").exists())

    def test_ca_09_4_en_la_holandesa_se_acepta_el_precio_vigente(self):
        """CA-09.4 En la holandesa el comprador acepta el precio vigente y gana en el acto (MSG-15, S-01)."""
        holandesa = self.subasta_abierta(
            costo_salida=1000, tipo="HOLANDESA",
            holandesa_precio_inicial=2000, holandesa_decremento=100, holandesa_intervalo_min=30,
        )
        url = reverse("detalle_subasta", args=[holandesa.pk])
        detalle = self.client.get(url)
        self.assertContains(detalle, "Aceptar 2,000 fichas")
        self.assertContains(detalle, "Próxima bajada")
        self.client.post(reverse("aceptar_precio_holandesa", args=[holandesa.pk]))
        self.assertContains(self.client.get(url), "Ganaste")

    def test_ca_09_5_el_vendedor_no_puede_pujar_en_su_subasta(self):
        """CA-09.5 El vendedor ve su subasta sin opción de pujar (ERR-41, S-13)."""
        self.client.force_login(self.vendedor)
        self.assertContains(self.client.get(self.detalle), "no puedes pujar")
