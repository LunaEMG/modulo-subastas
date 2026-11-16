from django.conf import settings
from django.db import models

from .. import reloj
from ..reglas.notificaciones import Canal
from .base import ModeloConservado


class Notificacion(ModeloConservado):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="notificaciones"
    )
    # MSG-xx
    tipo = models.CharField(max_length=10)
    asunto = models.CharField(max_length=120)
    mensaje = models.TextField()
    subasta = models.ForeignKey(
        "subastas.Subasta", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    fecha_creacion = models.DateTimeField(default=reloj.ahora)
    leida_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notificacion"
        ordering = ["-fecha_creacion", "-id"]


class EntregaNotificacion(ModeloConservado):
    class Estado(models.TextChoices):
        ENVIADA = "ENVIADA", "Enviada"
        FALLIDA = "FALLIDA", "Fallida"

    notificacion = models.ForeignKey(
        Notificacion, on_delete=models.PROTECT, related_name="entregas"
    )
    canal = models.CharField(max_length=10, choices=Canal.choices)
    estado = models.CharField(max_length=10, choices=Estado.choices)
    fecha = models.DateTimeField(default=reloj.ahora)

    class Meta:
        db_table = "entrega_notificacion"
        constraints = [
            models.UniqueConstraint(
                fields=["notificacion", "canal"], name="entrega_unica_por_canal"
            ),
        ]
