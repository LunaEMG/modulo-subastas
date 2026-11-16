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

    def test_paso_1_solo_pide_elegir_el_tipo(self):
        """Rediseño (fase D): sin tipo elegido, la pantalla muestra los cuatro tipos con su descripción y ningún campo."""
        pantalla = self.client.get(reverse("proponer_subasta", args=[self.articulo.pk]))
        self.assertContains(pantalla, "Paso 1 de 2")
        self.assertContains(pantalla, 'type="radio" name="tipo"', count=4)
        self.assertNotContains(pantalla, 'name="duracion_horas"')

    def test_paso_2_muestra_solo_los_campos_del_tipo(self):
        """Rediseño (fase D): con el tipo elegido, solo aparecen la duración y los parámetros de ese tipo."""
        parametros = {
            "INGLESA": set(),
            "RESERVADA": {"precio_reserva"},
            "COMPRA_INMEDIATA": {"precio_compra_inmediata"},
            "HOLANDESA": {"holandesa_precio_inicial", "holandesa_decremento", "holandesa_intervalo_min"},
        }
        todos = set().union(*parametros.values())
        url = reverse("proponer_subasta", args=[self.articulo.pk])
        for tipo, propios in parametros.items():
            with self.subTest(tipo=tipo):
                pantalla = self.client.get(url, {"tipo": tipo})
                self.assertContains(pantalla, "Paso 2 de 2")
                self.assertContains(pantalla, 'name="duracion_horas"')
                self.assertContains(pantalla, f'type="hidden" name="tipo" value="{tipo}"')
                for campo in todos:
                    if campo in propios:
                        self.assertContains(pantalla, f'name="{campo}"')
                    else:
                        self.assertNotContains(pantalla, f'name="{campo}"')

    def test_un_error_regresa_al_paso_2_del_mismo_tipo(self):
        """Rediseño (fase D): si el servicio rechaza la propuesta, se vuelve a pintar el paso 2 del tipo enviado."""
        url = reverse("proponer_subasta", args=[self.articulo.pk])
        respuesta = self.client.post(url, {"tipo": "RESERVADA", "duracion_horas": "48"})
        self.assertContains(respuesta, "ERR-42")
        self.assertContains(respuesta, 'name="precio_reserva"')
        self.assertNotContains(respuesta, 'name="holandesa_decremento"')
        self.assertFalse(Subasta.objects.exists())
