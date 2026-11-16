from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils.functional import cached_property

from .. import reloj
from .base import ConjuntoConservado, ModeloConservado


class Rol(ModeloConservado):
    VENDEDOR = "VENDEDOR"
    COMPRADOR = "COMPRADOR"
    GESTOR = "GESTOR"
    MODERADOR = "MODERADOR"
    NOMBRES = [
        (VENDEDOR, "Vendedor"),
        (COMPRADOR, "Comprador"),
        (GESTOR, "Gestor de Subastas"),
        (MODERADOR, "Moderador de Contenido"),
    ]

    nombre = models.CharField(max_length=20, unique=True, choices=NOMBRES)

    class Meta:
        db_table = "rol"

    def __str__(self):
        return self.get_nombre_display()


class GestorUsuarios(BaseUserManager.from_queryset(ConjuntoConservado)):
    """Hace falta para que Django busque al usuario por correo (USERNAME_FIELD)."""


class Usuario(AbstractBaseUser, ModeloConservado):
    # Solo el hash con sal; se renombra la columna para que el esquema lo diga.
    password = models.CharField("hash de la contraseña", max_length=128, db_column="hash_contrasena")
    last_login = None

    correo = models.EmailField(unique=True)
    nombre = models.CharField(max_length=120)
    telefono = models.CharField("teléfono móvil", max_length=20)
    residencia_verificada = models.BooleanField(default=False)
    fecha_registro = models.DateTimeField(default=reloj.ahora)
    roles = models.ManyToManyField(Rol, through="UsuarioRol", related_name="usuarios")

    objects = GestorUsuarios()

    USERNAME_FIELD = "correo"

    class Meta:
        db_table = "usuario"

    def __str__(self):
        return self.nombre

    @cached_property
    def nombres_de_roles(self) -> frozenset[str]:
        return frozenset(self.roles.values_list("nombre", flat=True))

    def tiene_rol(self, nombre_rol: str) -> bool:
        return nombre_rol in self.nombres_de_roles


class UsuarioRol(ModeloConservado):
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT)

    class Meta:
        db_table = "usuario_rol"
        constraints = [
            models.UniqueConstraint(fields=["usuario", "rol"], name="usuario_rol_unico"),
        ]


class CodigoVerificacion(ModeloConservado):
    """RF-02: solo se guarda el hash del código."""

    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name="codigos")
    hash_codigo = models.CharField(max_length=64)
    expira_en = models.DateTimeField()
    usado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "codigo_verificacion"
