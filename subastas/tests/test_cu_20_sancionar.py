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
