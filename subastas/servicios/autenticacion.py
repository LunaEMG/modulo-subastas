import secrets
from datetime import timedelta

from django.db import transaction
from django.utils.crypto import constant_time_compare, salted_hmac

from .. import integraciones, reloj
from ..mensajes import ErrorDeNegocio
from ..models import CodigoVerificacion, Rol, Usuario, UsuarioRol
from ..reglas import usuarios as reglas_usuarios
from . import cuentas

# S-23
LONGITUD_CODIGO = 6
VIGENCIA_CODIGO = timedelta(minutes=5)
MAXIMO_INTENTOS_CODIGO = 5
LONGITUD_MINIMA_CONTRASENA = 8

# S-26: gestores y moderadores son personal; no se registran solos.
ROLES_DE_REGISTRO = frozenset({Rol.VENDEDOR, Rol.COMPRADOR})


def _normalizar_correo(correo: str) -> str:
    return correo.strip().lower()


def _crear_usuario(*, correo, contrasena, nombre, telefono, roles) -> Usuario:
    correo = _normalizar_correo(correo)
    if Usuario.objects.filter(correo=correo).exists():
        raise ErrorDeNegocio("ERR-35")
    if len(contrasena) < LONGITUD_MINIMA_CONTRASENA:
        raise ErrorDeNegocio("ERR-51", minimo=LONGITUD_MINIMA_CONTRASENA)
    usuario = Usuario(
        correo=correo, nombre=nombre.strip(), telefono=telefono.strip(), residencia_verificada=True
    )
    usuario.set_password(contrasena)
    usuario.save()
    for rol in Rol.objects.filter(nombre__in=roles):
        UsuarioRol.objects.create(usuario=usuario, rol=rol)
    return usuario


@transaction.atomic
def registrar_usuario(
    *, correo, contrasena, nombre, telefono, codigo_postal, roles, documentos=None
) -> Usuario:
    """CU-01. `documentos` (DocumentosIdentidad) se reenvía al validador sin guardarse (S-31)."""
    roles = set(roles)
    if not roles or not roles <= ROLES_DE_REGISTRO:
        raise ErrorDeNegocio("ERR-54")
    acreditada = integraciones.obtener("identidad").acredita_residencia_en_mexico(
        nombre=nombre, codigo_postal=codigo_postal, documentos=documentos
    )
    # RN-15
    reglas_usuarios.validar_residencia(acreditada=acreditada)
    return _crear_usuario(
        correo=correo, contrasena=contrasena, nombre=nombre, telefono=telefono, roles=roles
    )


@transaction.atomic
def crear_personal(*, correo, contrasena, nombre, telefono, roles) -> Usuario:
    """Sin validación de identidad: el personal lo da de alta la administración."""
    return _crear_usuario(
        correo=correo, contrasena=contrasena, nombre=nombre, telefono=telefono, roles=set(roles)
    )


def _hash_del_codigo(usuario: Usuario, codigo: str) -> str:
    return salted_hmac("subastas.codigo_verificacion", f"{usuario.pk}:{codigo}").hexdigest()


@transaction.atomic
def iniciar_sesion(*, correo, contrasena) -> Usuario:
    """CU-02, primer paso: no abre la sesión, solo envía el código."""
    usuario = Usuario.objects.filter(correo=_normalizar_correo(correo)).first()
    if usuario is None or not usuario.check_password(contrasena):
        raise ErrorDeNegocio("ERR-30")
    cuentas.exigir_cuenta_activa(usuario)

    instante = reloj.ahora()
    # Un código nuevo anula los anteriores.
    usuario.codigos.filter(usado_en__isnull=True).update(usado_en=instante)
    codigo = "".join(secrets.choice("0123456789") for _ in range(LONGITUD_CODIGO))
    CodigoVerificacion.objects.create(
        usuario=usuario,
        hash_codigo=_hash_del_codigo(usuario, codigo),
        expira_en=instante + VIGENCIA_CODIGO,
    )
    integraciones.obtener("codigo_movil").enviar(telefono=usuario.telefono, codigo=codigo)
    return usuario


@transaction.atomic
def verificar_codigo(*, usuario: Usuario, codigo: str) -> None:
    """CU-02, segundo paso. Lanza ERR-31 si el código es incorrecto, ya se usó o venció."""
    instante = reloj.ahora()
    vigente = usuario.codigos.filter(usado_en__isnull=True, expira_en__gt=instante).last()
    if vigente is None or not constant_time_compare(
        vigente.hash_codigo, _hash_del_codigo(usuario, codigo.strip())
    ):
        raise ErrorDeNegocio("ERR-31")
    vigente.usado_en = instante
    vigente.save(update_fields=["usado_en"])


@transaction.atomic
def anular_codigos(usuario: Usuario) -> None:
    usuario.codigos.filter(usado_en__isnull=True).update(usado_en=reloj.ahora())
