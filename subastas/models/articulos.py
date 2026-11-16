from django.conf import settings
from django.db import models

from .. import reloj
from ..reglas.estados import EstadoArticulo
from .base import ModeloConservado


class Decision(models.TextChoices):
    APROBADO = "APROBADO", "Aprobado"
    RECHAZADO = "RECHAZADO", "Rechazado"
    RETIRADO = "RETIRADO", "Publicación retirada"


class Categoria(ModeloConservado):
    nombre = models.CharField(max_length=40, unique=True)
    requiere_valuacion = models.BooleanField(default=True)

    class Meta:
        db_table = "categoria"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Articulo(ModeloConservado):
    vendedor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="articulos"
    )
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="articulos")
    titulo = models.CharField("título", max_length=120)
    descripcion = models.TextField("descripción")
    anio = models.PositiveIntegerField("año")
    # S-02: el precio mínimo que propone el vendedor.
    costo_salida = models.PositiveIntegerField("costo de salida")
    estado = models.CharField(
        max_length=20, choices=EstadoArticulo.choices, default=EstadoArticulo.REGISTRADO
    )
    fecha_registro = models.DateTimeField(default=reloj.ahora)
    # S-10: una aprobación del moderador anterior a esta fecha ya no cubre el contenido.
    fecha_ultimo_envio = models.DateTimeField(default=reloj.ahora)

    class Meta:
        db_table = "articulo"
        ordering = ["-fecha_registro", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(costo_salida__gt=0), name="articulo_costo_salida_positivo"
            ),
        ]

    def __str__(self):
        return self.titulo

    @property
    def fotografias_visibles(self):
        return self.fotografias.filter(retirada=False)

    @property
    def portada(self):
        return self.fotografias_visibles.first()


class Fotografia(ModeloConservado):
    articulo = models.ForeignKey(Articulo, on_delete=models.PROTECT, related_name="fotografias")
    archivo = models.ImageField(upload_to="articulos/%Y/%m/")
    orden = models.PositiveSmallIntegerField(default=0)
    # RNF-01: las fotos sustituidas al corregir se conservan, ocultas.
    retirada = models.BooleanField(default=False)

    class Meta:
        db_table = "fotografia"
        ordering = ["orden", "id"]


class RevisionGestor(ModeloConservado):
    class Etapa(models.TextChoices):
        DATOS = "DATOS", "Revisión del artículo"
        DURACION = "DURACION", "Validación de la duración"

    articulo = models.ForeignKey(
        Articulo, on_delete=models.PROTECT, related_name="revisiones_gestor"
    )
    gestor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    etapa = models.CharField(max_length=10, choices=Etapa.choices)
    decision = models.CharField(max_length=10, choices=Decision.choices)
    observaciones = models.TextField(blank=True)
    fecha = models.DateTimeField(default=reloj.ahora)

    class Meta:
        db_table = "revision_gestor"
        ordering = ["-fecha", "-id"]


class RevisionContenido(ModeloConservado):
    articulo = models.ForeignKey(
        Articulo, on_delete=models.PROTECT, related_name="revisiones_contenido"
    )
    moderador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    decision = models.CharField(max_length=10, choices=Decision.choices)
    motivo = models.TextField(blank=True)
    fecha = models.DateTimeField(default=reloj.ahora)

    class Meta:
        db_table = "revision_contenido"
        ordering = ["-fecha", "-id"]


class Valuacion(ModeloConservado):
    articulo = models.ForeignKey(Articulo, on_delete=models.PROTECT, related_name="valuaciones")
    precio_propuesto = models.PositiveIntegerField()
    es_autentico = models.BooleanField()
    precio_avalado = models.PositiveIntegerField(null=True, blank=True)
    referencia_externa = models.CharField(max_length=60, blank=True)
    fecha = models.DateTimeField(default=reloj.ahora)

    class Meta:
        db_table = "valuacion"
        ordering = ["-fecha", "-id"]
