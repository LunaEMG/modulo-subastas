"""CU-08 Buscar subastas, filtrar y consultar el detalle (Comprador)."""
from django.urls import reverse

from .base import PruebaSubastas


class CU08BuscarSubastas(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(costo_salida=1000, tipo="COMPRA_INMEDIATA", precio_compra_inmediata=5000)
        self.client.force_login(self.crear_comprador())

    def test_ca_08_1_se_listan_y_filtran_las_subastas_abiertas(self):
        """CA-08.1 La búsqueda lista las subastas abiertas y filtra por texto, categoría y tipo."""
        buscar = reverse("buscar_subastas")
        self.assertContains(self.client.get(buscar), "Reloj de prueba")
        self.assertContains(self.client.get(buscar, {"texto": "reloj"}), "Reloj de prueba")
        self.assertNotContains(self.client.get(buscar, {"categoria": "Videojuegos"}), "Reloj de prueba")
        self.assertNotContains(self.client.get(buscar, {"tipo": "HOLANDESA"}), "Reloj de prueba")

    def test_ca_08_2_las_subastas_vencidas_no_aparecen(self):
        """CA-08.2 Una subasta cuya fecha de cierre ya pasó no aparece en la búsqueda."""
        self.reloj.avanzar(hours=25)
        self.assertNotContains(self.client.get(reverse("buscar_subastas")), "Reloj de prueba")

    def test_ca_08_3_el_detalle_muestra_precio_actual_y_puja_minima(self):
        """CA-08.3 El detalle muestra la puja mínima aceptada y la opción de comprar ya."""
        detalle = self.client.get(reverse("detalle_subasta", args=[self.subasta.pk]))
        self.assertContains(detalle, "Mínimo 1,001 fichas")
        self.assertContains(detalle, "Comprar ya por 5,000")
