"""CU-07 Validar la duración y publicar o rechazar la subasta (Gestor)."""
from datetime import timedelta

from django.urls import reverse

from subastas.reglas.estados import EstadoArticulo, EstadoSubasta

from .base import PruebaSubastas


class CU07ValidarDuracion(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.articulo = self.articulo_listo()
        self.subasta = self.proponer(self.articulo, duracion_horas=48)
        self.client.force_login(self.gestor)
        self.url = reverse("gestor_propuesta", args=[self.subasta.pk])

    def test_ca_07_1_con_contenido_aprobado_la_subasta_se_publica(self):
        """CA-07.1 Con el contenido aprobado por el moderador, validar la duración abre la subasta (MSG-10)."""
        self.assertContains(self.client.get(self.url), "48 horas")
        self.aprobar_para_publicar(self.articulo)
        respuesta = self.client.post(reverse("validar_duracion", args=[self.subasta.pk]), follow=True)
        self.assertContains(respuesta, "MSG-10")
        self.subasta.refresh_from_db()
        self.assertEqual(self.subasta.estado, EstadoSubasta.ABIERTA)
        self.assertEqual(self.subasta.fecha_cierre - self.subasta.fecha_inicio, timedelta(hours=self.subasta.duracion_horas))

    def test_ca_07_2_sin_aprobacion_del_moderador_no_se_publica_err_48(self):
        """CA-07.2 Sin la aprobación del moderador la pantalla lo advierte y publicar se rechaza con ERR-48 (S-10)."""
        self.assertContains(self.client.get(self.url), "ERR-48")
        respuesta = self.client.post(reverse("validar_duracion", args=[self.subasta.pk]), follow=True, **self.desde(self.url))
        self.assertContains(respuesta, "ERR-48")
        self.subasta.refresh_from_db()
        self.assertEqual(self.subasta.estado, EstadoSubasta.PROPUESTA)

    def test_ca_07_3_rechazar_la_propuesta_regresa_el_articulo_para_proponer_otra(self):
        """CA-07.3 Rechazar la propuesta con motivo la deja «Rechazada» y el artículo vuelve a «Valuado» (MSG-11)."""
        respuesta = self.client.post(reverse("rechazar_duracion", args=[self.subasta.pk]), {"motivo": "Muy larga"}, follow=True)
        self.assertContains(respuesta, "MSG-11")
        self.subasta.refresh_from_db()
        self.articulo.refresh_from_db()
        self.assertEqual((self.subasta.estado, self.articulo.estado), (EstadoSubasta.RECHAZADA, EstadoArticulo.VALUADO))

    def test_ca_07_4_una_subasta_publicada_no_se_publica_dos_veces_err_03(self):
        """CA-07.4 Una subasta ya abierta no se vuelve a validar (ERR-03, RN-03)."""
        self.aprobar_para_publicar(self.articulo)
        self.client.post(reverse("validar_duracion", args=[self.subasta.pk]))
        respuesta = self.client.post(reverse("validar_duracion", args=[self.subasta.pk]), follow=True, **self.desde(self.url))
        self.assertContains(respuesta, "ERR-03")

    def test_sin_aprobacion_no_se_ofrece_validar_y_se_explica_lo_que_falta(self):
        """Rediseño (fase C): sin la aprobación del moderador no aparece «Validar y publicar»; aparece qué falta."""
        pantalla = self.client.get(self.url)
        self.assertNotContains(pantalla, "Validar y publicar")
        self.assertContains(pantalla, "falta que el moderador apruebe el contenido")
        self.aprobar_para_publicar(self.articulo)
        self.assertContains(self.client.get(self.url), "Validar y publicar")
