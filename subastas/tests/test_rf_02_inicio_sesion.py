"""RF-02: inicio de sesión con correo, contraseña y código al móvil. (CU-02)
Los criterios de aceptación están en test_cu_02_iniciar_sesion.py."""

from subastas.models import CodigoVerificacion
from subastas.servicios import autenticacion

from .base import CONTRASENA, PruebaSubastas

class RF02InicioDeSesion(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.usuario = self.crear_comprador()

    def _primer_paso(self):
        return autenticacion.iniciar_sesion(correo=self.usuario.correo, contrasena=CONTRASENA)

    def test_valido_correo_contrasena_y_codigo(self):
        self._primer_paso()
        telefono, codigo = self.codigo_movil.enviados[-1]
        self.assertEqual(telefono, self.usuario.telefono)
        self.assertEqual(len(codigo), autenticacion.LONGITUD_CODIGO)
        autenticacion.verificar_codigo(usuario=self.usuario, codigo=codigo)

    def test_invalido_contrasena_incorrecta(self):
        self.assertErrorDeNegocio(
            "ERR-30", autenticacion.iniciar_sesion, correo=self.usuario.correo, contrasena="otra"
        )
        self.assertEqual(self.codigo_movil.enviados, [])

    def test_invalido_correo_inexistente(self):
        self.assertErrorDeNegocio(
            "ERR-30", autenticacion.iniciar_sesion, correo="nadie@prueba.test", contrasena=CONTRASENA
        )

    def test_invalido_codigo_incorrecto(self):
        self._primer_paso()
        equivocado = "000000" if self.codigo_movil.ultimo_codigo != "000000" else "111111"
        self.assertErrorDeNegocio(
            "ERR-31", autenticacion.verificar_codigo, usuario=self.usuario, codigo=equivocado
        )

    def test_invalido_codigo_vencido(self):
        self._primer_paso()
        self.reloj.avanzar(minutes=5, seconds=1)
        self.assertErrorDeNegocio(
            "ERR-31",
            autenticacion.verificar_codigo,
            usuario=self.usuario,
            codigo=self.codigo_movil.ultimo_codigo,
        )

    def test_invalido_codigo_ya_usado(self):
        self._primer_paso()
        codigo = self.codigo_movil.ultimo_codigo
        autenticacion.verificar_codigo(usuario=self.usuario, codigo=codigo)
        self.assertErrorDeNegocio(
            "ERR-31", autenticacion.verificar_codigo, usuario=self.usuario, codigo=codigo
        )

    def test_un_codigo_nuevo_anula_el_anterior(self):
        self._primer_paso()
        primero = self.codigo_movil.ultimo_codigo
        self._primer_paso()
        segundo = self.codigo_movil.ultimo_codigo
        if primero != segundo:
            self.assertErrorDeNegocio(
                "ERR-31", autenticacion.verificar_codigo, usuario=self.usuario, codigo=primero
            )
        autenticacion.verificar_codigo(usuario=self.usuario, codigo=segundo)

    def test_el_codigo_no_se_guarda_en_claro(self):
        self._primer_paso()
        guardado = CodigoVerificacion.objects.get(usuario=self.usuario)
        self.assertNotIn(self.codigo_movil.ultimo_codigo, guardado.hash_codigo)

