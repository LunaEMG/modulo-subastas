"""RNF-01: ningún modelo se borra físicamente; las bajas son cambios de estado."""
from django.db import models

from ..mensajes import ErrorDeNegocio


class ConjuntoConservado(models.QuerySet):
    def delete(self):
        raise ErrorDeNegocio("ERR-46")


class ModeloConservado(models.Model):
    objects = ConjuntoConservado.as_manager()

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        raise ErrorDeNegocio("ERR-46")
