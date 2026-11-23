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

    def test_ca_04_6_paso_1_solo_pide_elegir_el_tipo(self):
        """CA-04.6 La propuesta se hace en dos pasos: primero se elige el tipo de subasta entre los cuatro, con su descripción; después se piden la duración y solo los parámetros de ese tipo.

        Paso 1: sin tipo elegido, la pantalla muestra los cuatro tipos con su descripción y ningún campo."""
        pantalla = self.client.get(reverse("proponer_subasta", args=[self.articulo.pk]))
        self.assertContains(pantalla, "Paso 1 de 2")
        self.assertContains(pantalla, 'type="radio" name="tipo"', count=4)
        self.assertNotContains(pantalla, 'name="duracion_horas"')

    def test_ca_04_6_paso_2_muestra_solo_los_campos_del_tipo(self):
        """CA-04.6 La propuesta se hace en dos pasos: primero se elige el tipo de subasta entre los cuatro, con su descripción; después se piden la duración y solo los parámetros de ese tipo.

        Paso 2: con el tipo elegido, solo aparecen la duración y los parámetros de ese tipo."""
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

    def test_ca_04_3_un_error_regresa_al_paso_2_del_mismo_tipo(self):
        """CA-04.3 Los parámetros que no corresponden al tipo se rechazan con ERR-42 (RF-01).

        Al rechazarse la propuesta se vuelve a pintar el paso 2 del tipo enviado."""
        url = reverse("proponer_subasta", args=[self.articulo.pk])
        respuesta = self.client.post(url, {"tipo": "RESERVADA", "duracion_horas": "48"})
        self.assertContains(respuesta, "ERR-42")
        self.assertContains(respuesta, 'name="precio_reserva"')
        self.assertNotContains(respuesta, 'name="holandesa_decremento"')
        self.assertFalse(Subasta.objects.exists())

    def test_s38_un_intervalo_holandes_enorme_es_error_de_formulario(self):
        """S-38 Un intervalo de la holandesa mayor a 43,200 minutos (como 10^20) se rechaza en el formulario con ERR-42, sin error del servidor."""
        url = reverse("proponer_subasta", args=[self.articulo.pk])
        datos = {"tipo": "HOLANDESA", "duracion_horas": "48", "holandesa_precio_inicial": "5000", "holandesa_decremento": "100"}
        respuesta = self.client.post(url, {**datos, "holandesa_intervalo_min": str(10**20)})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "ERR-42")
        self.assertContains(respuesta, "43,200 minutos")
        self.assertFalse(Subasta.objects.exists())
        self.client.post(url, {**datos, "holandesa_intervalo_min": "43200"})
        self.assertTrue(Subasta.objects.exists())

    def test_abrir_la_propuesta_sin_valuacion_regresa_a_la_ficha_sin_err_04(self):
        """Abrir por su dirección la propuesta de un artículo que aún no se valúa regresa a su ficha en «Mis artículos», sin ERR-04."""
        pendiente = self.registrar_articulo()
        respuesta = self.client.get(reverse("proponer_subasta", args=[pendiente.pk]), follow=True)
        self.assertRedirects(respuesta, reverse("detalle_articulo", args=[pendiente.pk]))
        self.assertNotContains(respuesta, "ERR-04")
        # Si el valuador no lo avaló, ERR-04 sí describe la situación y se conserva.
        self.valuador.avala = False
        no_avalado = self.articulo_listo()
        self.assertContains(self.client.get(reverse("proponer_subasta", args=[no_avalado.pk]), follow=True), "ERR-04")

    def test_rnf_02_los_tipos_se_anuncian_por_su_nombre(self):
        """RNF-02 Cada radio de tipo de subasta se anuncia con su nombre legible y su descripción, no con el valor interno."""
        html = self.client.get(reverse("proponer_subasta", args=[self.articulo.pk])).content.decode()
        self.assertIn('value="COMPRA_INMEDIATA" required aria-labelledby="nombre-tipo-', html)
        self.assertRegex(html, r'<strong id="nombre-tipo-\d">Con compra inmediata</strong>')

    def test_las_pantallas_del_vendedor_llevan_migas_de_regreso(self):
        """Registrar, corregir y proponer llevan migas de regreso, como «Validar propuesta» del gestor."""
        self.assertContains(self.client.get(reverse("registrar_articulo")), f'<p class="migas"><a href="{reverse("mis_articulos")}">← Mis artículos</a></p>')
        regreso = f'<p class="migas"><a href="{reverse("detalle_articulo", args=[self.articulo.pk])}">← Volver al artículo</a></p>'
        self.assertContains(self.client.get(reverse("proponer_subasta", args=[self.articulo.pk])), regreso)
        self.assertContains(self.client.get(reverse("corregir_articulo", args=[self.articulo.pk])), regreso)
