"""CU-13 Consultar historial de pujas y subastas ganadas (Comprador)."""
from django.urls import reverse

from subastas.models import Puja
from subastas.servicios import cierre, pujas

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

    def test_una_puja_en_subasta_cerrada_no_se_muestra_activa(self):
        """En una subasta cerrada, la puja que ganó dice «Ganadora» y la otra «No ganada», sin cambiar su estado guardado."""
        comprador = self.crear_comprador()
        otro = self.crear_comprador()
        subasta = self.subasta_abierta(costo_salida=1000, duracion_horas=24)
        pujas.pujar(comprador=otro, subasta_id=subasta.pk, monto=1100)
        pujas.pujar(comprador=comprador, subasta_id=subasta.pk, monto=1200)
        self.reloj.avanzar(hours=24)
        cierre.procesar_pendientes()
        self.client.force_login(comprador)
        self.assertContains(self.client.get(reverse("historial")), '<span class="sello sello-definitivo sello-ganaste">Ganadora</span>')
        self.client.force_login(otro)
        html = self.client.get(reverse("historial")).content.decode()
        self.assertIn('<span class="sello sello-definitivo">No ganada</span>', html)
        self.assertNotIn(">Activa</span>", html)
        self.assertEqual(Puja.objects.filter(estado=Puja.Estado.ACTIVA).count(), 2)

    def test_rnf_02_los_montos_del_historial_llevan_fichas(self):
        """RNF-02 Precio actual, precio final y las columnas «Antes» y «Después» llevan su unidad en fichas."""
        comprador = self.crear_comprador()
        pujas.pujar(comprador=comprador, subasta_id=self.subasta.pk, monto=1200)
        pujas.modificar_puja(comprador=comprador, subasta_id=self.subasta.pk, nuevo_monto=1300)
        self.client.force_login(comprador)
        html = self.client.get(reverse("historial")).content.decode()
        self.assertIn("· precio actual 1,300 fichas", html)
        self.assertIn('data-etiqueta="Antes">1,200 fichas</td>', html)
        self.assertIn('data-etiqueta="Después">1,300 fichas</td>', html)
        pujas.comprar_de_inmediato(comprador=comprador, subasta_id=self.subasta.pk)
        self.assertContains(self.client.get(reverse("historial")), 'data-etiqueta="Precio final">5,000 fichas</td>')
