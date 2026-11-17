"""CU-19 Retirar una publicación que viola los términos (Moderador)."""
from django.urls import reverse

from subastas.models import Notificacion, Puja, RevisionContenido
from subastas.reglas.estados import EstadoArticulo, EstadoSubasta
from subastas.servicios import moderacion, pujas

from .base import PruebaSubastas


class CU19RetirarPublicacion(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(duracion_horas=24)
        self.ana = self.crear_comprador()
        pujas.pujar(comprador=self.ana, subasta_id=self.subasta.pk, monto=1200)
        self.client.force_login(self.moderador)
        self.url = reverse("moderador_articulo", args=[self.subasta.articulo_id])

    def test_ca_19_1_retirar_cancela_la_subasta_y_anula_las_pujas(self):
        """CA-19.1 Retirar con motivo cancela la subasta, anula las pujas y deja el artículo «Retirado» (MSG-19, S-30)."""
        self.assertContains(self.client.get(self.url), "Retirar publicación")
        respuesta = self.client.post(reverse("retirar_publicacion", args=[self.subasta.articulo_id]), {"motivo": "Artículo robado"}, follow=True)
        self.assertContains(respuesta, "MSG-19")
        self.subasta.refresh_from_db()
        self.assertEqual((self.subasta.estado, self.subasta.articulo.estado), (EstadoSubasta.CANCELADA, EstadoArticulo.RETIRADO))
        self.assertEqual(Puja.objects.get().estado, Puja.Estado.RETIRADA)
        self.assertEqual(RevisionContenido.objects.latest("id").decision, "RETIRADO")

    def test_ca_19_2_se_avisa_al_vendedor_y_a_quienes_pujaron(self):
        """CA-19.2 El vendedor recibe MSG-45 y cada comprador con puja activa MSG-46."""
        self.client.post(reverse("retirar_publicacion", args=[self.subasta.articulo_id]), {"motivo": "Viola términos"})
        self.assertTrue(Notificacion.objects.filter(usuario=self.vendedor, tipo="MSG-45").exists())
        self.assertTrue(Notificacion.objects.filter(usuario=self.ana, tipo="MSG-46").exists())

    def test_ca_19_3_retirar_exige_motivo_err_49(self):
        """CA-19.3 Retirar sin motivo se impide con ERR-49."""
        respuesta = self.client.post(reverse("retirar_publicacion", args=[self.subasta.articulo_id]), {"motivo": ""}, follow=True, **self.desde(self.url))
        self.assertContains(respuesta, "ERR-49")

    def test_ca_19_4_sin_publicacion_activa_no_hay_que_retirar_err_53(self):
        """CA-19.4 Si la subasta ya cerró no hay publicación activa que retirar (ERR-53)."""
        self.reloj.avanzar(hours=24)
        self.assertErrorDeNegocio(
            "ERR-53", moderacion.retirar_publicacion,
            moderador=self.moderador, articulo_id=self.subasta.articulo_id, motivo="Tarde",
        )

    def test_ca_19_5_retirar_pasa_por_revisa_y_confirma(self):
        """CA-19.5 «Retirar publicación» lleva a «Revisa y confirma» con el motivo y cuántas pujas activas quedan sin efecto; mostrar la confirmación no retira nada."""
        articulo_id = self.subasta.articulo_id
        self.assertContains(self.client.get(self.url), reverse("confirmar_retiro", args=[articulo_id]))
        pantalla = self.client.post(reverse("confirmar_retiro", args=[articulo_id]), {"motivo": "Artículo robado"})
        self.assertContains(pantalla, "Revisa y confirma")
        self.assertContains(pantalla, "Artículo robado")
        self.assertContains(pantalla, "Las pujas activas (1) quedan sin efecto.")
        self.assertContains(pantalla, reverse("retirar_publicacion", args=[articulo_id]))
        self.subasta.refresh_from_db()
        self.assertEqual(self.subasta.estado, EstadoSubasta.ABIERTA)

    def test_ca_19_3_la_confirmacion_de_retiro_exige_el_motivo(self):
        """CA-19.3 Retirar sin motivo se impide con ERR-49.

        Sin motivo no se llega a la confirmación; se regresa al artículo."""
        respuesta = self.client.post(
            reverse("confirmar_retiro", args=[self.subasta.articulo_id]), {"motivo": ""}, follow=True, **self.desde(self.url)
        )
        self.assertContains(respuesta, "ERR-49")
        self.assertRedirects(self.client.get(reverse("confirmar_retiro", args=[self.subasta.articulo_id])), self.url)
