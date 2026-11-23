"""CU-07 Validar la duración y publicar o rechazar la subasta (Gestor)."""
from datetime import timedelta

from django.urls import reverse

from subastas.reglas.estados import EstadoArticulo, EstadoSubasta
from subastas.servicios import consultas

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
        self.assertContains(self.client.get(self.url), "<span class=\"sello sello-detenido\">Sin aprobación del moderador</span>")
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

    def test_ca_07_5_el_menu_cuenta_las_propuestas_por_validar(self):
        """CA-07.5 El menú del gestor cuenta las propuestas por validar y la tarjeta de inicio dice cuántas son (S-34)."""
        self.assertEqual(
            consultas.pendientes_por_rol(self.gestor),
            {"gestor_articulos": 0, "gestor_propuestas": 1, "gestor": 1},
        )
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, '<span class="contador por-atender">1</span> propuesta por validar')

    def test_ca_07_2_sin_aprobacion_no_se_ofrece_validar_y_se_explica_lo_que_falta(self):
        """CA-07.2 Sin la aprobación del moderador la pantalla lo advierte y publicar se rechaza con ERR-48 (S-10).

        No aparece «Validar y publicar»; aparece qué falta."""
        pantalla = self.client.get(self.url)
        self.assertNotContains(pantalla, "Validar y publicar")
        self.assertContains(pantalla, "falta que el moderador apruebe el contenido")
        self.aprobar_para_publicar(self.articulo)
        self.assertContains(self.client.get(self.url), "Validar y publicar")

    def test_rnf_02_la_bandeja_y_la_propuesta_sin_identificadores_internos(self):
        """RNF-02 La bandeja del gestor no muestra CU-06 ni CU-07 en sus títulos y el precio de salida lleva fichas; la duración pluraliza horas."""
        html = self.client.get(reverse("gestor_bandeja")).content.decode()
        self.assertNotIn("(CU-06)", html)
        self.assertNotIn("(CU-07)", html)
        self.assertIn('data-etiqueta="Precio de salida">1,000 fichas</td>', html)
        self.assertContains(self.client.get(self.url), "<dd>48 horas</dd>")
        una_hora = self.proponer(self.articulo_listo(), duracion_horas=1)
        self.assertContains(self.client.get(reverse("gestor_propuesta", args=[una_hora.pk])), "<dd>1 hora</dd>")

    def test_rnf_02_validar_propuesta_coincide_en_pestana_y_titulo(self):
        """RNF-02 La pantalla se llama «Validar propuesta» en la pestaña y en el título."""
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, "<title>Validar propuesta · Casa de Subastas</title>")
        self.assertContains(respuesta, "<h1>Validar propuesta</h1>")
