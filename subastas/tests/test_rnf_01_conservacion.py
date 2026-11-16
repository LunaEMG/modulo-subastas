"""RNF-01: los datos se conservan; ningún registro se borra físicamente."""
from django.apps import apps

from subastas.models import Usuario
from subastas.models.base import ModeloConservado

from .base import PruebaSubastas


class RNF01Conservacion(PruebaSubastas):
    def test_todos_los_modelos_del_modulo_impiden_el_borrado(self):
        for modelo in apps.get_app_config("subastas").get_models():
            with self.subTest(modelo=modelo.__name__):
                self.assertTrue(issubclass(modelo, ModeloConservado))

    def test_invalido_borrar_un_registro(self):
        usuario = self.crear_comprador()
        self.assertErrorDeNegocio("ERR-46", usuario.delete)
        self.assertTrue(Usuario.objects.filter(pk=usuario.pk).exists())

    def test_invalido_borrado_masivo(self):
        self.crear_comprador()
        self.assertErrorDeNegocio("ERR-46", Usuario.objects.all().delete)
        self.assertEqual(Usuario.objects.count(), 1)
