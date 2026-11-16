"""CU-04 Proponer tipo, parámetros y duración de la subasta (Vendedor)."""
from django.urls import reverse

from subastas.models import Subasta
from subastas.reglas.estados import EstadoArticulo, EstadoSubasta
from subastas.servicios import articulos

from .base import PruebaSubastas


class CU04ProponerSubasta(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.articulo = self.articulo_listo(costo_salida=2500)
        self.client.force_login(self.vendedor)

    def test_ca_04_1_la_propuesta_arranca_en_el_precio_minimo_avalado(self):
        """CA-04.1 La pantalla muestra el precio mínimo avalado y la propuesta queda «Propuesta» con ese precio de salida (MSG-07)."""
        url = reverse("proponer_subasta", args=[self.articulo.pk])
        self.assertContains(self.client.get(url), "Precio mínimo avalado")
        respuesta = self.client.post(url, {"tipo": "INGLESA", "duracion_horas": "48"}, follow=True)
        self.assertContains(respuesta, "MSG-07")
        subasta = Subasta.objects.get()
        self.assertEqual((subasta.estado, subasta.precio_salida, subasta.duracion_horas), (EstadoSubasta.PROPUESTA, 2500, 48))
        self.articulo.refresh_from_db()
        self.assertEqual(self.articulo.estado, EstadoArticulo.DURACION_PROPUESTA)

    def test_ca_04_2_una_duracion_fuera_de_limites_se_rechaza_con_err_40(self):
        """CA-04.2 Una duración fuera de 1 a 720 horas se rechaza con ERR-40 (RN-05, S-14)."""
        self.assertErrorDeNegocio("ERR-40", self.proponer, self.articulo, duracion_horas=0)
        self.assertErrorDeNegocio("ERR-40", self.proponer, self.articulo, duracion_horas=721)

    def test_ca_04_3_los_parametros_del_tipo_se_validan_err_42(self):
        """CA-04.3 Los parámetros que no corresponden al tipo se rechazan con ERR-42 (RF-01)."""
        self.assertErrorDeNegocio("ERR-42", self.proponer, self.articulo, tipo="RESERVADA")

    def test_ca_04_4_no_se_propone_sobre_un_articulo_ajeno_err_43(self):
        """CA-04.4 Un vendedor no puede proponer la subasta de un artículo de otro (ERR-43)."""
        self.assertErrorDeNegocio(
            "ERR-43", articulos.proponer_subasta, vendedor=self.crear_vendedor(),
            articulo_id=self.articulo.pk, tipo="INGLESA", duracion_horas=24,
        )

    def test_ca_04_5_un_articulo_sin_analizar_no_admite_propuesta_err_05(self):
        """CA-04.5 Un artículo que aún no pasa la revisión ni la valuación no admite propuesta (ERR-05, RN-05)."""
        self.assertErrorDeNegocio("ERR-05", self.proponer, self.registrar_articulo())
