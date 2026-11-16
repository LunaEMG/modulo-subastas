"""RN-15: solo participa quien acredite vivir en México. (CU-01)
Los criterios de aceptación están en test_cu_01_registrarse.py."""
from subastas.models import Rol, Usuario
from subastas.reglas import usuarios as reglas_usuarios
from subastas.servicios import autenticacion, cuentas

from .base import CONTRASENA, PruebaSubastas


class RN15Residencia(PruebaSubastas):
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

    def test_valido_residencia_acreditada_permite_registrarse(self):
        usuario = self._registrar()
        self.assertTrue(usuario.residencia_verificada)
        self.assertTrue(usuario.tiene_rol(Rol.COMPRADOR))

    def test_invalido_residencia_no_acreditada_rechaza_el_registro(self):
        self.identidad.acredita = False
        self.assertErrorDeNegocio("ERR-15", self._registrar)
        self.assertFalse(Usuario.objects.filter(correo="ana@prueba.test").exists())

    def test_invalido_sin_residencia_verificada_no_puede_participar(self):
        usuario = self._registrar()
        usuario.residencia_verificada = False
        self.assertErrorDeNegocio(
            "ERR-15", cuentas.exigir_participacion, usuario, Rol.COMPRADOR
        )

    def test_regla_pura(self):
        reglas_usuarios.validar_residencia(acreditada=True)
        self.assertErrorDeNegocio("ERR-15", reglas_usuarios.validar_residencia, acreditada=False)

