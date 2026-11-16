"""CU-16 Vencer el plazo de pago y resubastar (actor Tiempo)."""
from django.urls import reverse

from subastas.models import Adjudicacion
from subastas.reglas.estados import EstadoSubasta
from subastas.reglas.pagos import EstadoAdjudicacion
from subastas.servicios import pujas

from .base import PruebaSubastas


class CU16VencerYResubastar(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(costo_salida=1000, duracion_horas=24)
        self.moroso = self.crear_comprador()
        pujas.pujar(comprador=self.moroso, subasta_id=self.subasta.pk, monto=1500)
        self.client.force_login(self.crear_comprador())
        self.reloj.avanzar(hours=24)
        self.client.get(reverse("inicio"))

    def test_ca_16_1_sin_pago_en_3_dias_el_articulo_vuelve_a_subasta(self):
        """CA-16.1 Sin pago pasados 3 días, la adjudicación vence y el artículo vuelve a aparecer en la búsqueda (RN-12, S-08)."""
        self.reloj.avanzar(days=3, seconds=1)
        self.assertContains(self.client.get(reverse("buscar_subastas")), "Reloj de prueba")
        self.assertEqual(Adjudicacion.objects.get().estado, EstadoAdjudicacion.VENCIDA)
        self.assertEqual(self.subasta.resubastas.get().estado, EstadoSubasta.ABIERTA)

    def test_ca_16_2_dentro_del_plazo_no_se_resubasta(self):
        """CA-16.2 Dentro de los 3 días la adjudicación sigue pendiente y no hay resubasta."""
        self.reloj.avanzar(days=3)
        self.assertNotContains(self.client.get(reverse("buscar_subastas")), "Reloj de prueba")
        self.assertEqual(Adjudicacion.objects.get().estado, EstadoAdjudicacion.PENDIENTE_PAGO)

    def test_ca_16_3_el_moroso_y_el_vendedor_reciben_su_aviso(self):
        """CA-16.3 Al resubastar, el ganador que no pagó recibe MSG-42 y el vendedor MSG-43."""
        self.reloj.avanzar(days=3, seconds=1)
        self.client.get(reverse("inicio"))
        self.assertTrue(self.moroso.notificaciones.filter(tipo="MSG-42").exists())
        self.assertTrue(self.vendedor.notificaciones.filter(tipo="MSG-43").exists())
