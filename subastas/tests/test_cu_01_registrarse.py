"""CU-01 Registrarse acreditando residencia en México (Vendedor o Comprador)."""
from django.urls import reverse

from subastas.integraciones.puertos import DocumentosIdentidad
from subastas.models import Rol, Usuario
from subastas.servicios import autenticacion

from .base import CONTRASENA, PruebaSubastas

FORMULARIO = {
    "nombre": "Nueva Persona",
    "correo": "nueva@prueba.test",
    "telefono": "5599990000",
    "codigo_postal": "07738",
    "contrasena": CONTRASENA,
    "roles": ["VENDEDOR"],
}


class CU01Registrarse(PruebaSubastas):
    def _registrar(self, **cambios):
        datos = {
            "correo": "ana@prueba.test",
            "contrasena": CONTRASENA,
            "nombre": "Ana",
            "telefono": "5511112222",
            "codigo_postal": "07738",
            "roles": [Rol.COMPRADOR],
        }
        datos.update(cambios)
        return autenticacion.registrar_usuario(**datos)

    def test_ca_01_1_con_residencia_acreditada_la_cuenta_se_crea_y_pasa_a_entrar(self):
        """CA-01.1 Con residencia acreditada se crea la cuenta y se envía a «Entrar» (MSG-01)."""
        respuesta = self.client.post(reverse("registro"), FORMULARIO, follow=True)
        self.assertRedirects(respuesta, reverse("entrar"))
        self.assertContains(respuesta, "MSG-01")
        usuario = Usuario.objects.get(correo="nueva@prueba.test")
        self.assertTrue(usuario.residencia_verificada)
        self.assertTrue(usuario.tiene_rol(Rol.VENDEDOR))

    def test_ca_01_2_sin_residencia_acreditada_se_rechaza_con_err_15(self):
        """CA-01.2 Si el validador de identidad no acredita la residencia, se rechaza con ERR-15."""
        self.identidad.acredita = False
        respuesta = self.client.post(reverse("registro"), dict(FORMULARIO, codigo_postal="00000"))
        self.assertContains(respuesta, "ERR-15")
        self.assertFalse(Usuario.objects.exists())

    def test_ca_01_3_un_correo_ya_registrado_se_rechaza_con_err_35(self):
        """CA-01.3 Un correo ya registrado (sin importar mayúsculas ni espacios) se rechaza con ERR-35."""
        self._registrar()
        self.assertErrorDeNegocio("ERR-35", self._registrar, correo=" ANA@prueba.test ")

    def test_ca_01_4_una_contrasena_corta_se_rechaza_con_err_51(self):
        """CA-01.4 Una contraseña de menos de 8 caracteres se rechaza con ERR-51 (S-23)."""
        self.assertErrorDeNegocio("ERR-51", self._registrar, contrasena="corta")

    def test_ca_01_5_solo_se_registran_vendedores_y_compradores_err_54(self):
        """CA-01.5 Nadie se registra solo como gestor o moderador, ni sin rol (ERR-54, S-26)."""
        self.assertErrorDeNegocio("ERR-54", self._registrar, roles=[Rol.GESTOR])
        self.assertErrorDeNegocio("ERR-54", self._registrar, roles=[])

    def test_ca_01_6_la_contrasena_se_guarda_como_hash(self):
        """CA-01.6 La contraseña nunca se guarda en claro."""
        usuario = self._registrar()
        self.assertNotEqual(usuario.password, CONTRASENA)
        self.assertTrue(usuario.check_password(CONTRASENA))

    def test_ca_01_7_una_persona_puede_ser_vendedor_y_comprador(self):
        """CA-01.7 Una misma cuenta puede tener los roles de vendedor y comprador."""
        usuario = self._registrar(roles=[Rol.VENDEDOR, Rol.COMPRADOR])
        self.assertEqual(usuario.nombres_de_roles, {Rol.VENDEDOR, Rol.COMPRADOR})

    def test_ca_01_8_los_documentos_de_identidad_se_reenvian_al_validador(self):
        """CA-01.8 Si llegan documentos de identidad, se reenvían al validador sin guardarse (S-31)."""
        documentos = DocumentosIdentidad(curp="AAAA000101HDFRRR09")
        self._registrar(documentos=documentos)
        self.assertEqual(self.identidad.consultas[-1], ("Ana", "07738", documentos))

    def test_ca_01_9_hoy_el_registro_solo_envia_el_codigo_postal(self):
        """CA-01.9 El registro por pantalla solo envía nombre y código postal al validador (S-31)."""
        self.client.post(reverse("registro"), FORMULARIO)
        self.assertEqual(self.identidad.consultas, [("Nueva Persona", "07738", None)])

    def test_audit_los_campos_declaran_su_proposito_wcag_1_3_5(self):
        """Audit (WCAG 1.3.5) Registro y entrar declaran autocomplete; teléfono y código postal abren teclado numérico."""
        registro = self.client.get(reverse("registro")).content.decode()
        for atributo in ('autocomplete="name"', 'autocomplete="email"', 'type="tel"', 'autocomplete="tel"',
                         'inputmode="numeric"', 'autocomplete="postal-code"', 'autocomplete="new-password"'):
            self.assertIn(atributo, registro)
        entrar = self.client.get(reverse("entrar")).content.decode()
        self.assertIn('autocomplete="email"', entrar)
        self.assertIn('autocomplete="current-password"', entrar)
