"""RN-03: orden de publicación registro → gestor → valuador → duración → validación. (CU-06, CU-07)"""
from subastas.reglas import estados
from subastas.reglas.articulos import VIDEOJUEGOS
from subastas.reglas.estados import EstadoArticulo as A
from subastas.reglas.estados import EstadoSubasta as S
from subastas.servicios import revision

from .base import PruebaSubastas


class RN03FlujoDePublicacion(PruebaSubastas):
    def test_valido_flujo_completo_en_orden(self):
        articulo = self.registrar_articulo()
        self.assertEqual(articulo.estado, A.REGISTRADO)

        revision.aprobar_articulo(gestor=self.gestor, articulo_id=articulo.pk)
        articulo.refresh_from_db()
        # Relojes pasa por el valuador (S-09), que lo avala en el acto.
        self.assertEqual(self.valuador.solicitudes, [articulo.pk])
        self.assertEqual(articulo.estado, A.VALUADO)

        subasta = self.proponer(articulo)
        articulo.refresh_from_db()
        self.assertEqual((articulo.estado, subasta.estado), (A.DURACION_PROPUESTA, S.PROPUESTA))

        subasta = self.publicar(articulo, subasta)
        articulo.refresh_from_db()
        self.assertEqual((articulo.estado, subasta.estado), (A.EN_SUBASTA, S.ABIERTA))

    def test_invalido_saltar_de_registrado_a_en_subasta(self):
        self.assertErrorDeNegocio(
            "ERR-03", estados.validar_transicion_articulo, A.REGISTRADO, A.EN_SUBASTA
        )

    def test_invalido_proponer_subasta_antes_de_la_revision(self):
        articulo = self.registrar_articulo()
        self.assertErrorDeNegocio("ERR-05", self.proponer, articulo)

    def test_invalido_el_gestor_no_aprueba_dos_veces(self):
        articulo = self.articulo_listo()
        self.assertErrorDeNegocio(
            "ERR-03", revision.aprobar_articulo, gestor=self.gestor, articulo_id=articulo.pk
        )

    def test_invalido_el_gestor_no_aprueba_un_articulo_con_propuesta_pendiente(self):
        articulo = self.articulo_listo(categoria=VIDEOJUEGOS)
        self.proponer(articulo)
        self.assertErrorDeNegocio(
            "ERR-03", revision.aprobar_articulo, gestor=self.gestor, articulo_id=articulo.pk
        )

    def test_invalido_publicar_dos_veces_la_misma_subasta(self):
        subasta = self.subasta_abierta()
        self.assertErrorDeNegocio(
            "ERR-03", revision.validar_duracion, gestor=self.gestor, subasta_id=subasta.pk
        )

    def test_s09_videojuegos_no_pasa_por_el_valuador(self):
        articulo = self.articulo_listo(categoria=VIDEOJUEGOS)
        self.assertEqual(articulo.estado, A.VALUADO)
        self.assertEqual(self.valuador.solicitudes, [])

    def test_rechazo_del_gestor_permite_corregir(self):
        articulo = self.registrar_articulo()
        revision.rechazar_articulo(gestor=self.gestor, articulo_id=articulo.pk, motivo="Incompleto")
        articulo.refresh_from_db()
        self.assertEqual(articulo.estado, A.RECHAZADO)
        estados.validar_transicion_articulo(A.RECHAZADO, A.REGISTRADO)

    def test_err_49_rechazar_exige_motivo(self):
        articulo = self.registrar_articulo()
        self.assertErrorDeNegocio(
            "ERR-49", revision.rechazar_articulo, gestor=self.gestor, articulo_id=articulo.pk, motivo=" "
        )

    def test_rechazo_de_la_propuesta_regresa_a_proponer(self):
        articulo = self.articulo_listo()
        subasta = self.proponer(articulo)
        revision.rechazar_duracion(gestor=self.gestor, subasta_id=subasta.pk, motivo="Muy corta")
        articulo.refresh_from_db()
        subasta.refresh_from_db()
        self.assertEqual((articulo.estado, subasta.estado), (A.VALUADO, S.RECHAZADA))
        self.proponer(articulo, duracion_horas=72)

    def test_err_32_solo_el_gestor_revisa(self):
        articulo = self.registrar_articulo()
        self.assertErrorDeNegocio(
            "ERR-32", revision.aprobar_articulo, gestor=self.vendedor, articulo_id=articulo.pk
        )

    def test_cada_decision_queda_en_el_historial(self):
        articulo = self.articulo_listo()
        subasta = self.proponer(articulo)
        self.publicar(articulo, subasta)
        self.assertEqual(
            list(articulo.revisiones_gestor.values_list("etapa", "decision")),
            [("DURACION", "APROBADO"), ("DATOS", "APROBADO")],
        )

    def test_las_decisiones_se_avisan_al_vendedor(self):
        articulo = self.articulo_listo()
        self.assertEqual(
            list(self.vendedor.notificaciones.values_list("tipo", flat=True)), ["MSG-32", "MSG-30"]
        )
        self.assertEqual(articulo.estado, A.VALUADO)
