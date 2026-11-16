"""CU-03 Registrar artículo (Vendedor), con el flujo alterno de corregir un rechazado."""
from django.urls import reverse

from subastas.models import Articulo
from subastas.reglas.estados import EstadoArticulo

from .base import PruebaSubastas, fotografia


class CU03RegistrarArticulo(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.preparar_actores()
        self.client.force_login(self.vendedor)

    def test_ca_03_1_el_articulo_completo_se_registra_con_sus_fotografias(self):
        """CA-03.1 Un artículo con datos completos y fotografías se registra en estado «Registrado» (MSG-05)."""
        respuesta = self.client.post(reverse("registrar_articulo"), {
            "categoria": "Relojes", "titulo": "Reloj por pantalla", "descripcion": "Automático",
            "anio": "2018", "costo_salida": "2500",
            "fotografias": [fotografia("a.png"), fotografia("b.png")],
        })
        articulo = Articulo.objects.get()
        self.assertRedirects(respuesta, reverse("detalle_articulo", args=[articulo.pk]), fetch_redirect_response=False)
        self.assertEqual((articulo.estado, articulo.fotografias.count()), (EstadoArticulo.REGISTRADO, 2))
        self.assertContains(self.client.get(reverse("detalle_articulo", args=[articulo.pk])), "MSG-05")

    def test_ca_03_2_sin_fotografias_se_rechaza_con_err_02(self):
        """CA-03.2 Sin al menos una fotografía el registro se rechaza con ERR-02 (RN-02)."""
        respuesta = self.client.post(reverse("registrar_articulo"), {
            "categoria": "Relojes", "titulo": "X", "descripcion": "Y", "anio": "2018", "costo_salida": "10",
        })
        self.assertContains(respuesta, "ERR-02")
        self.assertFalse(Articulo.objects.exists())

    def test_ca_03_3_los_campos_mal_capturados_muestran_su_error_del_catalogo(self):
        """CA-03.3 Un campo vacío o mal capturado muestra su ERR-xx del catálogo (ERR-55, ERR-56)."""
        respuesta = self.client.post(reverse("registrar_articulo"), {"categoria": "Relojes", "titulo": "", "anio": "dos mil"})
        self.assertContains(respuesta, "ERR-55")
        self.assertContains(respuesta, "ERR-56")

    def test_ca_03_4_un_articulo_rechazado_se_corrige_y_regresa_a_revision(self):
        """CA-03.4 El vendedor ve el motivo del rechazo, corrige el artículo y vuelve a «Registrado» (MSG-06)."""
        articulo = self.registrar_articulo()
        self.client.force_login(self.gestor)
        self.client.post(reverse("rechazar_articulo", args=[articulo.pk]), {"motivo": "Foto borrosa"})
        self.client.force_login(self.vendedor)
        self.assertContains(self.client.get(reverse("corregir_articulo", args=[articulo.pk])), "Foto borrosa")
        respuesta = self.client.post(reverse("corregir_articulo", args=[articulo.pk]), {
            "categoria": "Relojes", "titulo": "Corregido", "descripcion": "Mejor", "anio": "2015", "costo_salida": "1000",
        }, follow=True)
        self.assertContains(respuesta, "MSG-06")
        articulo.refresh_from_db()
        self.assertEqual(articulo.estado, EstadoArticulo.REGISTRADO)

    def test_ca_03_5_solo_se_corrige_un_articulo_rechazado_err_50(self):
        """CA-03.5 Un artículo que no fue rechazado no se puede corregir (ERR-50)."""
        articulo = self.registrar_articulo()
        url = reverse("detalle_articulo", args=[articulo.pk])
        respuesta = self.client.post(reverse("corregir_articulo", args=[articulo.pk]), {
            "categoria": "Relojes", "titulo": "Otro", "descripcion": "Otra", "anio": "2015", "costo_salida": "1000",
        }, follow=True, **self.desde(url))
        self.assertContains(respuesta, "ERR-50")

    def test_ca_03_6_sin_sesion_se_pide_entrar(self):
        """CA-03.6 Sin sesión iniciada, las pantallas del vendedor piden entrar."""
        self.client.logout()
        respuesta = self.client.get(reverse("mis_articulos"))
        self.assertRedirects(respuesta, reverse("entrar") + "?next=" + reverse("mis_articulos"))
