"""CU-06 Revisar artículo y aprobarlo o rechazarlo (Gestor), con la solicitud al valuador."""
from django.urls import reverse

from subastas.reglas.articulos import AUTOMOVILES
from subastas.reglas.estados import EstadoArticulo

from .base import PruebaSubastas


class CU06RevisarArticulo(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.articulo = self.registrar_articulo()
        self.client.force_login(self.gestor)

    def test_ca_06_1_el_gestor_ve_el_articulo_pendiente_y_lo_aprueba(self):
        """CA-06.1 El artículo registrado aparece en «Pendientes» y al aprobarlo queda listo para proponer (MSG-08)."""
        self.assertContains(self.client.get(reverse("gestor_bandeja")), self.articulo.titulo)
        self.assertContains(self.client.get(reverse("gestor_articulo", args=[self.articulo.pk])), "Aprobar")
        respuesta = self.client.post(reverse("aprobar_articulo", args=[self.articulo.pk]), follow=True)
        self.assertContains(respuesta, "MSG-08")
        self.articulo.refresh_from_db()
        self.assertEqual(self.articulo.estado, EstadoArticulo.VALUADO)

    def test_ca_06_2_las_categorias_que_lo_requieren_pasan_por_el_valuador(self):
        """CA-06.2 Al aprobar un automóvil se pide el dictamen al valuador y se registra (S-09)."""
        automovil = self.registrar_articulo(categoria=AUTOMOVILES)
        self.client.post(reverse("aprobar_articulo", args=[automovil.pk]))
        self.assertEqual(self.valuador.solicitudes, [automovil.pk])
        self.assertTrue(automovil.valuaciones.exists())

    def test_ca_06_3_el_rechazo_exige_motivo_err_49(self):
        """CA-06.3 Rechazar sin motivo se impide con ERR-49."""
        url = reverse("gestor_articulo", args=[self.articulo.pk])
        respuesta = self.client.post(reverse("rechazar_articulo", args=[self.articulo.pk]), {"motivo": ""}, follow=True, **self.desde(url))
        self.assertContains(respuesta, "ERR-49")

    def test_ca_06_4_el_rechazo_con_motivo_regresa_el_articulo_al_vendedor(self):
        """CA-06.4 Al rechazar con motivo el artículo queda «Rechazado» (MSG-09) y el vendedor recibe el aviso MSG-31."""
        respuesta = self.client.post(reverse("rechazar_articulo", args=[self.articulo.pk]), {"motivo": "Foto borrosa"}, follow=True)
        self.assertContains(respuesta, "MSG-09")
        self.articulo.refresh_from_db()
        self.assertEqual(self.articulo.estado, EstadoArticulo.RECHAZADO)
        self.assertTrue(self.vendedor.notificaciones.filter(tipo="MSG-31").exists())

    def test_ca_06_5_solo_el_gestor_entra_a_sus_pendientes_err_32(self):
        """CA-06.5 Un vendedor no puede abrir los pendientes del gestor (ERR-32)."""
        self.client.force_login(self.vendedor)
        self.assertContains(self.client.get(reverse("gestor_bandeja"), follow=True), "ERR-32")
