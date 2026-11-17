"""CU-18 Revisar descripción y fotografías de un artículo (Moderador), S-10."""
from datetime import timedelta

from django.urls import reverse

from subastas.models import Notificacion
from subastas.reglas import moderacion as reglas
from subastas.reglas.estados import EstadoArticulo, EstadoSubasta
from subastas.servicios import articulos as servicio_articulos
from subastas.servicios import consultas, moderacion

from .base import INICIO, PruebaSubastas


class ReglaContenidoAprobado(PruebaSubastas):
    """La regla de S-10 aislada: qué aprobación cubre el contenido actual."""

    def test_ca_18_r1_una_aprobacion_posterior_al_ultimo_envio_cubre_el_contenido(self):
        """CA-18.R1 Una aprobación igual o posterior al último envío cubre el contenido."""
        self.assertTrue(reglas.contenido_aprobado(ultima_decision="APROBADO", fecha_decision=INICIO, fecha_ultimo_envio=INICIO))

    def test_ca_18_r2_sin_revision_no_hay_aprobacion_err_48(self):
        """CA-18.R2 Sin ninguna revisión del moderador el contenido no está aprobado (ERR-48)."""
        self.assertErrorDeNegocio("ERR-48", reglas.validar_contenido_aprobado, ultima_decision=None, fecha_decision=None, fecha_ultimo_envio=INICIO)

    def test_ca_18_r3_una_aprobacion_anterior_a_una_correccion_ya_no_vale_err_48(self):
        """CA-18.R3 Una aprobación anterior a la última corrección del vendedor ya no vale (ERR-48)."""
        self.assertErrorDeNegocio(
            "ERR-48", reglas.validar_contenido_aprobado,
            ultima_decision="APROBADO", fecha_decision=INICIO, fecha_ultimo_envio=INICIO + timedelta(minutes=1),
        )


class CU18RevisarContenido(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.moderador = self.crear_moderador()
        self.articulo = self.articulo_listo()
        self.client.force_login(self.moderador)
        self.url = reverse("moderador_articulo", args=[self.articulo.pk])

    def test_ca_18_7_el_contador_del_moderador_coincide_con_su_bandeja(self):
        """CA-18.7 El menú del moderador cuenta el contenido por revisar, también dentro de su bandeja (S-34).

        El contador es el número de artículos que la bandeja lista por revisar."""
        total = len(moderacion.pendientes_de_revision())
        self.assertGreater(total, 0)
        self.assertEqual(consultas.pendientes_por_rol(self.moderador), {"moderador": total})

    def test_ca_18_7_dentro_de_la_bandeja_sigue_el_contador(self):
        """CA-18.7 El menú del moderador cuenta el contenido por revisar, también dentro de su bandeja (S-34).

        Dentro de su bandeja el moderador sigue viendo el contador junto a «Moderación»."""
        total = len(moderacion.pendientes_de_revision())
        respuesta = self.client.get(reverse("moderador_bandeja"))
        self.assertContains(respuesta, f'class="contador por-atender">{total}<span class="solo-lector"> pendientes')

    def test_ca_18_1_el_contenido_pendiente_aparece_y_se_aprueba(self):
        """CA-18.1 El artículo sin aprobar aparece en «Moderación» y al aprobarlo sale de la lista (MSG-18)."""
        self.assertContains(self.client.get(reverse("moderador_bandeja")), "Reloj de prueba")
        self.assertContains(self.client.get(self.url), "Aprobar contenido")
        respuesta = self.client.post(reverse("aprobar_contenido", args=[self.articulo.pk]), follow=True)
        self.assertContains(respuesta, "MSG-18")
        self.assertContains(respuesta, "No hay contenido por revisar")
        self.assertTrue(moderacion.contenido_aprobado(self.articulo))

    def test_ca_18_2_el_rechazo_exige_motivo_err_49(self):
        """CA-18.2 Rechazar el contenido sin motivo se impide con ERR-49."""
        respuesta = self.client.post(reverse("rechazar_contenido", args=[self.articulo.pk]), {"motivo": ""}, follow=True, **self.desde(self.url))
        self.assertContains(respuesta, "ERR-49")

    def test_ca_18_3_el_rechazo_regresa_el_articulo_y_rechaza_su_propuesta(self):
        """CA-18.3 Al rechazar, el artículo vuelve al vendedor (MSG-44) y su propuesta pendiente queda rechazada."""
        subasta = self.proponer(self.articulo)
        self.client.post(reverse("rechazar_contenido", args=[self.articulo.pk]), {"motivo": "Foto ajena"})
        self.articulo.refresh_from_db()
        subasta.refresh_from_db()
        self.assertEqual((self.articulo.estado, subasta.estado), (EstadoArticulo.RECHAZADO, EstadoSubasta.RECHAZADA))
        self.assertTrue(Notificacion.objects.filter(usuario=self.vendedor, tipo="MSG-44").exists())

    def test_ca_18_4_una_correccion_del_vendedor_pide_nueva_aprobacion(self):
        """CA-18.4 Si el vendedor corrige el artículo, vuelve a la lista del moderador aunque ya estuviera aprobado."""
        moderacion.aprobar_contenido(moderador=self.moderador, articulo_id=self.articulo.pk)
        moderacion.rechazar_contenido(moderador=self.moderador, articulo_id=self.articulo.pk, motivo="Texto ofensivo")
        self.reloj.avanzar(minutes=5)
        servicio_articulos.corregir_articulo(
            vendedor=self.vendedor, articulo_id=self.articulo.pk, categoria="Relojes",
            titulo="Reloj corregido", descripcion="Descripción nueva.", anio=2015, costo_salida=1000,
        )
        self.articulo.refresh_from_db()
        self.assertIn(self.articulo, moderacion.pendientes_de_revision())

    def test_ca_18_5_lo_publicado_no_se_revisa_se_retira_err_64(self):
        """CA-18.5 Una publicación activa no se revisa con este caso de uso (ERR-64): se usa CU-19."""
        subasta = self.subasta_abierta()
        self.assertErrorDeNegocio("ERR-64", moderacion.aprobar_contenido, moderador=self.moderador, articulo_id=subasta.articulo_id)

    def test_ca_18_6_solo_el_moderador_revisa_contenido_err_32(self):
        """CA-18.6 Otro rol no puede revisar contenido (ERR-32)."""
        self.assertErrorDeNegocio("ERR-32", moderacion.aprobar_contenido, moderador=self.gestor, articulo_id=self.articulo.pk)
        self.client.force_login(self.crear_comprador())
        self.assertContains(self.client.get(reverse("moderador_bandeja"), follow=True), "ERR-32")
