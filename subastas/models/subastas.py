from django.conf import settings
from django.db import models
from django.db.models import Q

from .. import reloj
from ..reglas import dinero
from ..reglas.estados import EstadoSubasta
from ..reglas.pagos import EstadoAdjudicacion
from .base import ModeloConservado


class TipoDeSubasta(models.TextChoices):
    INGLESA = "INGLESA", "Inglesa"
    RESERVADA = "RESERVADA", "Con precio reservado"
    HOLANDESA = "HOLANDESA", "Holandesa"
    COMPRA_INMEDIATA = "COMPRA_INMEDIATA", "Con compra inmediata"


def _solo_en(tipo: str, *campos: str) -> Q:
    """Los campos son obligatorios en ese tipo de subasta y nulos en los demás."""
    con_valor = Q(tipo=tipo)
    sin_valor = ~Q(tipo=tipo)
    for campo in campos:
        con_valor &= Q(**{f"{campo}__isnull": False})
        sin_valor &= Q(**{f"{campo}__isnull": True})
    return con_valor | sin_valor


class Subasta(ModeloConservado):
    articulo = models.ForeignKey(
        "subastas.Articulo", on_delete=models.PROTECT, related_name="subastas"
    )
    tipo = models.CharField(max_length=20, choices=TipoDeSubasta.choices)
    estado = models.CharField(
        max_length=20, choices=EstadoSubasta.choices, default=EstadoSubasta.PROPUESTA
    )
    precio_salida = models.PositiveIntegerField()
    precio_reserva = models.PositiveIntegerField(null=True, blank=True)
    precio_compra_inmediata = models.PositiveIntegerField(null=True, blank=True)
    holandesa_precio_inicial = models.PositiveIntegerField(null=True, blank=True)
    holandesa_decremento = models.PositiveIntegerField(null=True, blank=True)
    holandesa_intervalo_min = models.PositiveIntegerField(null=True, blank=True)
    duracion_horas = models.PositiveIntegerField()
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    # RN-12
    subasta_origen = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="resubastas"
    )

    class Meta:
        db_table = "subasta"
        ordering = ["fecha_cierre", "id"]
        constraints = [
            models.CheckConstraint(
                condition=_solo_en(TipoDeSubasta.RESERVADA, "precio_reserva"),
                name="subasta_reserva_solo_en_reservada",
            ),
            models.CheckConstraint(
                condition=_solo_en(TipoDeSubasta.COMPRA_INMEDIATA, "precio_compra_inmediata"),
                name="subasta_compra_solo_en_compra_inmediata",
            ),
            models.CheckConstraint(
                condition=_solo_en(
                    TipoDeSubasta.HOLANDESA,
                    "holandesa_precio_inicial",
                    "holandesa_decremento",
                    "holandesa_intervalo_min",
                ),
                name="subasta_parametros_solo_en_holandesa",
            ),
            models.CheckConstraint(
                condition=Q(precio_salida__gt=0), name="subasta_precio_salida_positivo"
            ),
        ]
        indexes = [models.Index(fields=["estado", "fecha_cierre"])]

    def __str__(self):
        return f"Subasta {self.pk} de {self.articulo}"


class Puja(ModeloConservado):
    class Estado(models.TextChoices):
        ACTIVA = "ACTIVA", "Activa"
        RETIRADA = "RETIRADA", "Retirada"

    subasta = models.ForeignKey(Subasta, on_delete=models.PROTECT, related_name="pujas")
    comprador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pujas"
    )
    monto = models.PositiveIntegerField()
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVA)
    fecha_creacion = models.DateTimeField(default=reloj.ahora)
    fecha_actualizacion = models.DateTimeField(default=reloj.ahora)

    class Meta:
        db_table = "puja"
        ordering = ["-monto", "id"]
        constraints = [
            # S-27: para subir su oferta, el comprador modifica su puja.
            models.UniqueConstraint(
                fields=["subasta", "comprador"],
                condition=Q(estado="ACTIVA"),
                name="puja_activa_unica_por_comprador",
            ),
            models.CheckConstraint(condition=Q(monto__gt=0), name="puja_monto_positivo"),
        ]


class MovimientoPuja(ModeloConservado):
    class Tipo(models.TextChoices):
        CREACION = "CREACION", "Creación"
        MODIFICACION = "MODIFICACION", "Modificación"
        RETIRO = "RETIRO", "Retiro"

    puja = models.ForeignKey(Puja, on_delete=models.PROTECT, related_name="movimientos")
    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    monto_anterior = models.PositiveIntegerField(null=True, blank=True)
    monto_nuevo = models.PositiveIntegerField(null=True, blank=True)
    fecha = models.DateTimeField(default=reloj.ahora)

    class Meta:
        db_table = "movimiento_puja"
        ordering = ["fecha", "id"]


class Adjudicacion(ModeloConservado):
    subasta = models.OneToOneField(Subasta, on_delete=models.PROTECT, related_name="adjudicacion")
    ganador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="adjudicaciones"
    )
    precio_final = models.PositiveIntegerField()
    comision = models.PositiveIntegerField()
    fecha_limite_pago = models.DateTimeField()
    estado = models.CharField(
        max_length=15,
        choices=EstadoAdjudicacion.choices,
        default=EstadoAdjudicacion.PENDIENTE_PAGO,
    )
    referencia_pago = models.CharField(max_length=60, blank=True)
    referencia_envio = models.CharField(max_length=60, blank=True)
    fecha = models.DateTimeField(default=reloj.ahora)

    class Meta:
        db_table = "adjudicacion"
        ordering = ["-fecha", "-id"]
        indexes = [models.Index(fields=["estado", "fecha_limite_pago"])]

    def save(self, *args, **kwargs):
        # RN-14
        dinero.validar_comision(precio_final=self.precio_final, comision=self.comision)
        super().save(*args, **kwargs)

    @property
    def monto_vendedor(self) -> int:
        return dinero.calcular_monto_vendedor(self.precio_final, self.comision)
