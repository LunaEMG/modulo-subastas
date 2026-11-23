"""CU-06 Revisar artículo y aprobarlo o rechazarlo (Gestor), con la solicitud al valuador."""
from django.urls import reverse

from subastas.reglas.articulos import AUTOMOVILES, VIDEOJUEGOS
from subastas.reglas.estados import EstadoArticulo
from subastas.servicios import consultas

from .base import PruebaSubastas


class CU06RevisarArticulo(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.articulo = self.registrar_articulo()
        self.client.force_login(self.gestor)

    def test_ca_06_6_el_menu_cuenta_los_articulos_por_revisar(self):
        """CA-06.6 El menú del gestor cuenta los artículos por revisar y la tarjeta de inicio dice cuántos son (S-34)."""
        self.assertEqual(
            consultas.pendientes_por_rol(self.gestor),
            {"gestor_articulos": 1, "gestor_propuestas": 0, "gestor": 1},
        )
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, '<span class="contador por-atender">1</span> artículo por revisar')

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

    def test_un_articulo_que_no_existe_responde_404(self):
        """Aprobar por POST un id que no existe responde 404, no un error del servidor."""
        self.assertEqual(self.client.post(reverse("aprobar_articulo", args=[999999])).status_code, 404)

    def test_s39_un_motivo_demasiado_largo_se_rechaza_err_63(self):
        """S-39 Un motivo de rechazo de más de 1,000 caracteres se rechaza con ERR-63 y el artículo no cambia."""
        url = reverse("gestor_articulo", args=[self.articulo.pk])
        respuesta = self.client.post(
            reverse("rechazar_articulo", args=[self.articulo.pk]), {"motivo": "x" * 1001}, follow=True, **self.desde(url)
        )
        self.assertContains(respuesta, "ERR-63")
        self.articulo.refresh_from_db()
        self.assertEqual(self.articulo.estado, EstadoArticulo.REGISTRADO)

    def test_rnf_02_la_ficha_del_gestor_no_muestra_s_09(self):
        """RNF-02 La ficha del gestor explica que la categoría no pasa por valuador sin mostrar S-09."""
        articulo = self.registrar_articulo(categoria=VIDEOJUEGOS)
        respuesta = self.client.get(reverse("gestor_articulo", args=[articulo.pk]))
        self.assertContains(respuesta, "Esta categoría no pasa por valuador: al aprobar")
        self.assertNotContains(respuesta, "S-09")
