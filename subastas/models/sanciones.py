from django.conf import settings
from django.db import models

from .. import reloj
from ..reglas import sanciones as reglas_sanciones
from .base import ModeloConservado


class Sancion(ModeloConservado):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sanciones"
    )
    moderador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    nivel = models.PositiveSmallIntegerField()
    motivo = models.TextField()
    revision_contenido = models.ForeignKey(
        "subastas.RevisionContenido",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sanciones",
    )
    fecha_inicio = models.DateTimeField(default=reloj.ahora)
    # NULL es baja definitiva.
    fecha_fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "sancion"
        ordering = ["fecha_inicio", "id"]
        constraints = [
            # RN-16
            models.UniqueConstraint(fields=["usuario", "nivel"], name="sancion_nivel_unico"),
            models.CheckConstraint(
                condition=models.Q(nivel__in=[1, 2, 3]), name="sancion_nivel_valido"
            ),
        ]

    @property
    def descripcion(self) -> str:
        return reglas_sanciones.DESCRIPCION_POR_NIVEL[self.nivel]
