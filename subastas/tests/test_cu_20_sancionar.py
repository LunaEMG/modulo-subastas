"""CU-20 Aplicar sanción escalonada a un usuario (Moderador), con su historial.
La escala (RN-16) y S-20 están en test_rn_16_sanciones.py."""
from django.urls import reverse

from subastas.models import Sancion

from .base import PruebaSubastas


class CU20Sancionar(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.moderador = self.crear_moderador()
        self.infractor = self.crear_comprador()
        self.client.force_login(self.moderador)
        self.url = reverse("moderador_usuario", args=[self.infractor.pk])

    def test_rnf_02_el_correo_del_participante_no_se_parte(self):
        """RNF-02 En la tabla apilada el correo va completo bajo su etiqueta, no partido a media palabra."""
        self.assertContains(self.client.get(reverse("moderador_bandeja")), '<td class="celda-ancha" data-etiqueta="Correo">')

    def test_ca_20_1_la_pantalla_muestra_el_siguiente_nivel_y_lo_aplica(self):
        """CA-20.1 La pantalla indica el siguiente nivel y al aplicarlo queda en el historial (MSG-20)."""
        self.assertContains(self.client.get(self.url), "nivel 1")
        respuesta = self.client.post(reverse("sancionar", args=[self.infractor.pk]), {"motivo": "Spam", "nivel": "1"}, follow=True)
        self.assertContains(respuesta, "MSG-20")
        self.assertContains(respuesta, "suspensión de 14 días")
        self.assertContains(respuesta, "nivel 2")

    def test_ca_20_2_un_doble_envio_no_repite_el_nivel_err_16(self):
        """CA-20.2 Volver a enviar el mismo nivel se rechaza con ERR-16 y no se duplica la sanción."""
        self.client.post(reverse("sancionar", args=[self.infractor.pk]), {"motivo": "Spam", "nivel": "1"})
        respuesta = self.client.post(reverse("sancionar", args=[self.infractor.pk]), {"motivo": "Spam", "nivel": "1"}, follow=True, **self.desde(self.url))
        self.assertContains(respuesta, "ERR-16")
        self.assertEqual(Sancion.objects.count(), 1)

    def test_ca_20_3_el_sancionado_pierde_la_sesion(self):
        """CA-20.3 El usuario suspendido pierde la sesión y ve ERR-33 al intentar usar el sistema."""
        self.client.post(reverse("sancionar", args=[self.infractor.pk]), {"motivo": "Spam"})
        self.client.force_login(self.infractor)
        self.assertContains(self.client.get(reverse("inicio"), follow=True), "ERR-33")

    def test_ca_20_4_tras_la_baja_definitiva_ya_no_se_ofrece_sancionar(self):
        """CA-20.4 Tras la tercera sanción (baja definitiva) la pantalla ya no ofrece sancionar (ERR-47)."""
        for nivel in (1, 2, 3):
            self.client.post(reverse("sancionar", args=[self.infractor.pk]), {"motivo": "Reincide", "nivel": str(nivel)})
        self.assertContains(self.client.get(self.url), "dado de baja de forma definitiva")
        self.assertEqual(Sancion.objects.filter(usuario=self.infractor).count(), 3)

    def test_ca_20_5_el_personal_no_se_sanciona_err_65(self):
        """CA-20.5 A un gestor o moderador no se le puede sancionar (ERR-65, S-29)."""
        gestor = self.crear_gestor()
        respuesta = self.client.post(reverse("sancionar", args=[gestor.pk]), {"motivo": "X"}, follow=True, **self.desde(reverse("moderador_usuario", args=[gestor.pk])))
        self.assertContains(respuesta, "ERR-65")

    def test_ca_20_6_sancionar_pasa_por_revisa_y_confirma(self):
        """CA-20.6 La sanción pasa por «Revisa y confirma», que muestra el nivel, la duración y el motivo; mostrar la confirmación no sanciona."""
        self.assertContains(self.client.get(self.url), reverse("confirmar_sancion", args=[self.infractor.pk]))
        pantalla = self.client.post(reverse("confirmar_sancion", args=[self.infractor.pk]), {"motivo": "Spam", "nivel": "1"})
        self.assertContains(pantalla, "Revisa y confirma")
        self.assertContains(pantalla, "Nivel 1: suspensión de 14 días")
        self.assertContains(pantalla, "Aplicar sanción de nivel 1")
        self.assertContains(pantalla, reverse("sancionar", args=[self.infractor.pk]))
        self.assertFalse(Sancion.objects.exists())

    def test_ca_20_7_sancionar_exige_motivo_err_49(self):
        """CA-20.7 Sancionar sin motivo se impide con ERR-49 (S-33).

        Sin motivo no se llega a la confirmación; se regresa al usuario."""
        respuesta = self.client.post(
            reverse("confirmar_sancion", args=[self.infractor.pk]), {"motivo": " ", "nivel": "1"}, follow=True, **self.desde(self.url)
        )
        self.assertContains(respuesta, "ERR-49")
        self.assertFalse(Sancion.objects.exists())

    def test_review_la_confirmacion_no_se_ofrece_para_el_personal_err_65(self):
        """La confirmación aplica la misma regla que la sanción; con el personal regresa con ERR-65."""
        gestor = self.crear_gestor()
        origen = reverse("moderador_usuario", args=[gestor.pk])
        respuesta = self.client.post(
            reverse("confirmar_sancion", args=[gestor.pk]), {"motivo": "X", "nivel": "1"}, follow=True, **self.desde(origen)
        )
        self.assertContains(respuesta, "ERR-65")
        self.assertNotContains(respuesta, "Revisa y confirma")

    def test_review_una_confirmacion_con_el_nivel_ya_superado_se_rechaza_err_16(self):
        """Si otro moderador sancionó antes, la confirmación de la página vieja se rechaza con ERR-16."""
        self.client.post(reverse("sancionar", args=[self.infractor.pk]), {"motivo": "Spam", "nivel": "1"})
        respuesta = self.client.post(
            reverse("confirmar_sancion", args=[self.infractor.pk]), {"motivo": "Spam", "nivel": "1"}, follow=True, **self.desde(self.url)
        )
        self.assertContains(respuesta, "ERR-16")
        self.assertNotContains(respuesta, "Revisa y confirma")
        self.assertEqual(Sancion.objects.count(), 1)

    def test_la_ficha_del_personal_no_ofrece_sancionar(self):
        """La ficha de un gestor o moderador no muestra el formulario de sanción (S-29)."""
        gestor = self.crear_gestor()
        respuesta = self.client.get(reverse("moderador_usuario", args=[gestor.pk]))
        self.assertNotContains(respuesta, "Aplicar sanción")
        self.assertNotContains(respuesta, reverse("confirmar_sancion", args=[gestor.pk]))

    def test_rnf_02_la_moderacion_sin_identificadores_internos(self):
        """RNF-02 Los títulos de la bandeja y de la ficha de usuario no muestran CU-18, CU-19, CU-20 ni RN-16."""
        bandeja = self.client.get(reverse("moderador_bandeja")).content.decode()
        ficha = self.client.get(self.url).content.decode()
        for codigo in ("CU-18", "CU-19", "CU-20", "RN-16"):
            self.assertNotIn(codigo, bandeja)
            self.assertNotIn(codigo, ficha)
        self.assertIn("<title>Moderación · Casa de Subastas</title>", bandeja)
        self.assertIn("<h1>Moderación</h1>", bandeja)
