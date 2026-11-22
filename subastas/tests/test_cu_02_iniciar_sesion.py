"""CU-02 Iniciar sesión con correo, contraseña y código al móvil (todos los actores).
Las reglas del código están en test_rf_02_inicio_sesion.py."""
from datetime import timedelta

from django.conf import settings
from django.contrib.sessions.models import Session
from django.urls import reverse
from django.utils import timezone

from subastas.servicios import autenticacion

from .base import CONTRASENA, PruebaSubastas


class CU02IniciarSesion(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.usuario = self.crear_comprador()

    def _entrar(self, contrasena=CONTRASENA):
        return self.client.post(reverse("entrar"), {"correo": self.usuario.correo, "contrasena": contrasena})

    def test_ca_02_1_correo_y_contrasena_correctos_piden_el_codigo_sin_abrir_sesion(self):
        """CA-02.1 Con correo y contraseña correctos se envía el código y aún no se abre la sesión (MSG-02)."""
        respuesta = self._entrar()
        self.assertRedirects(respuesta, reverse("verificar_codigo"))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(len(self.codigo_movil.enviados), 1)

    def test_ca_02_2_contrasena_incorrecta_se_rechaza_con_err_30(self):
        """CA-02.2 Una contraseña incorrecta se rechaza con ERR-30 y no se envía código."""
        self.assertContains(self._entrar("equivocada"), "ERR-30")
        self.assertEqual(self.codigo_movil.enviados, [])

    def test_ca_02_3_el_codigo_correcto_abre_la_sesion_y_salir_la_cierra(self):
        """CA-02.3 El código correcto abre la sesión (MSG-03) y «Salir» la cierra (MSG-04)."""
        self._entrar()
        respuesta = self.client.post(reverse("verificar_codigo"), {"codigo": self.codigo_movil.ultimo_codigo})
        self.assertRedirects(respuesta, reverse("inicio"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.usuario.pk)
        self.client.post(reverse("salir"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_ca_02_4_cinco_codigos_incorrectos_obligan_a_empezar_de_nuevo(self):
        """CA-02.4 Tras 5 códigos incorrectos el código se anula y hay que volver a «Entrar» (S-23)."""
        self._entrar()
        correcto = self.codigo_movil.ultimo_codigo
        equivocado = "000000" if correcto != "000000" else "111111"
        for _ in range(autenticacion.MAXIMO_INTENTOS_CODIGO):
            respuesta = self.client.post(reverse("verificar_codigo"), {"codigo": equivocado})
        self.assertRedirects(respuesta, reverse("entrar"))
        self.assertErrorDeNegocio("ERR-31", autenticacion.verificar_codigo, usuario=self.usuario, codigo=correcto)

    def test_ca_02_5_sin_el_primer_paso_no_hay_pantalla_de_codigo(self):
        """CA-02.5 La pantalla del código no se abre sin haber pasado correo y contraseña."""
        self.assertRedirects(self.client.get(reverse("verificar_codigo")), reverse("entrar"))

    def test_s_35_con_sesion_no_se_guarda_en_cache_y_tras_salir_se_pide_entrar(self):
        """S-35 Con sesión, las páginas llevan Cache-Control: no-store; sin sesión, no.
        Tras «Salir», volver a «Buscar subastas» redirige a «Entrar»."""
        self.client.force_login(self.usuario)
        con_sesion = self.client.get(reverse("buscar_subastas"))
        self.assertEqual(con_sesion.status_code, 200)
        self.assertIn("no-store", con_sesion.get("Cache-Control", ""))

        self.client.post(reverse("salir"))
        portada = self.client.get(reverse("inicio"))
        self.assertNotIn("no-store", portada.get("Cache-Control", ""))

        tras_salir = self.client.get(reverse("buscar_subastas"))
        self.assertEqual(tras_salir.status_code, 302)
        self.assertTrue(tras_salir.url.startswith(reverse("entrar")))

    def test_s_37_la_sesion_vence_al_cerrar_el_navegador_o_tras_60_minutos_sin_actividad(self):
        """S-37 La cookie de sesión no sobrevive al navegador; cada petición renueva el plazo de 60 minutos
        y, vencido, la siguiente página privada pide «Entrar»."""
        self._entrar()
        self.client.post(reverse("verificar_codigo"), {"codigo": self.codigo_movil.ultimo_codigo})
        cookie = self.client.cookies[settings.SESSION_COOKIE_NAME]
        self.assertEqual(cookie["max-age"], "")
        self.assertEqual(cookie["expires"], "")
        self.assertEqual(self.client.session.get_expiry_age(), 60 * 60)

        sesion = Session.objects.filter(session_key=cookie.value)
        sesion.update(expire_date=timezone.now() + timedelta(minutes=1))
        self.assertEqual(self.client.get(reverse("buscar_subastas")).status_code, 200)
        self.assertGreater(sesion.get().expire_date, timezone.now() + timedelta(minutes=59))

        sesion.update(expire_date=timezone.now() - timedelta(seconds=1))
        vencida = self.client.get(reverse("buscar_subastas"))
        self.assertEqual(vencida.status_code, 302)
        self.assertTrue(vencida.url.startswith(reverse("entrar")))
