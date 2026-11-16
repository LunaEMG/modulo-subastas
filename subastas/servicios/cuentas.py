from .. import reloj
from ..mensajes import ErrorDeNegocio
from ..reglas import sanciones as reglas_sanciones
from ..reglas import usuarios as reglas_usuarios

ACTIVA = "Activa"
SUSPENDIDA = "Suspendida"
BAJA = "Baja definitiva"


def sancion_vigente(usuario, instante=None):
    """El estado de la cuenta no se guarda; se deduce de esta sanción (o None)."""
    instante = instante or reloj.ahora()
    for sancion in usuario.sanciones.order_by("-nivel"):
        if reglas_sanciones.esta_vigente(
            fecha_inicio=sancion.fecha_inicio, fecha_fin=sancion.fecha_fin, instante=instante
        ):
            return sancion
    return None


def estado_de_cuenta(usuario, instante=None) -> str:
    sancion = sancion_vigente(usuario, instante)
    if sancion is None:
        return ACTIVA
    return BAJA if sancion.fecha_fin is None else SUSPENDIDA


def exigir_cuenta_activa(usuario) -> None:
    sancion = sancion_vigente(usuario)
    if sancion is None:
        return
    if sancion.fecha_fin is None:
        raise ErrorDeNegocio("ERR-34")
    raise ErrorDeNegocio("ERR-33", hasta=reloj.formato(sancion.fecha_fin))


def exigir_rol(usuario, nombre_rol: str) -> None:
    if not usuario.tiene_rol(nombre_rol):
        raise ErrorDeNegocio("ERR-32")


def exigir_participacion(usuario, nombre_rol: str) -> None:
    exigir_rol(usuario, nombre_rol)
    # RN-15
    reglas_usuarios.validar_residencia(acreditada=usuario.residencia_verificada)
    exigir_cuenta_activa(usuario)
