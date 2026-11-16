"""Numeración del catálogo:

- ERR-01 a ERR-16: rechazo de la RN del mismo número (además, RN-05 usa ERR-40 y RN-16 ERR-47).
- ERR-30 a ERR-54 y ERR-64 en adelante: errores que no vienen de una RN.
- ERR-55 a ERR-63: forma de la entrada en formularios.
- MSG-01 a MSG-29: confirmaciones en pantalla; MSG-30 en adelante: avisos (con asunto).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Mensaje:
    texto: str
    asunto: str = ""


CATALOGO: dict[str, Mensaje] = {
    "ERR-01": Mensaje(
        "La categoría «{categoria}» no se subasta en esta casa. Se aceptan "
        "automóviles, relojes, videojuegos y artículos de oficina."
    ),
    "ERR-02": Mensaje("Faltan datos obligatorios del artículo: {faltantes}."),
    "ERR-03": Mensaje(
        "No se puede pasar de «{actual}» a «{nuevo}»: no es el siguiente paso del "
        "flujo de publicación."
    ),
    "ERR-04": Mensaje(
        "El artículo no puede subastarse: el valuador no avaló su autenticidad o "
        "su precio mínimo."
    ),
    "ERR-05": Mensaje(
        "Aún no se puede proponer la subasta: el artículo no ha sido recibido y "
        "analizado."
    ),
    "ERR-06": Mensaje(
        "La puja debe ser mayor al precio actual ({precio_actual:,} fichas). "
        "Monto mínimo aceptado: {minimo:,} fichas."
    ),
    "ERR-07": Mensaje("La puja ya no puede retirarse porque la subasta cerró."),
    "ERR-08": Mensaje(
        "La modificación debe ser mayor a la oferta actual ({precio_actual:,} "
        "fichas) y a tu puja anterior ({anterior:,} fichas), y la subasta debe "
        "seguir abierta."
    ),
    "ERR-09": Mensaje("La subasta todavía no llega a su fecha de cierre ({cierre})."),
    "ERR-10": Mensaje(
        "No hay ganador a quien avisar: la subasta no cerró con una adjudicación."
    ),
    "ERR-11": Mensaje("El plazo de {dias} días para pagar venció el {limite}."),
    "ERR-12": Mensaje(
        "El artículo no se vuelve a subastar: la adjudicación ya fue pagada o su "
        "plazo de pago sigue vigente."
    ),
    "ERR-13": Mensaje("El monto debe ser un número entero positivo de fichas."),
    "ERR-14": Mensaje(
        "La comisión de {comision:,} fichas no corresponde al {porcentaje} % del "
        "precio final ({esperada:,} fichas)."
    ),
    "ERR-15": Mensaje(
        "No se acreditó la residencia en México; no es posible participar."
    ),
    "ERR-16": Mensaje(
        "La sanción que corresponde es de nivel {esperado}; las sanciones son "
        "escalonadas y no se salta ni se repite nivel."
    ),
    "ERR-30": Mensaje("Correo o contraseña incorrectos."),
    "ERR-31": Mensaje("El código de verificación es incorrecto o ya venció."),
    "ERR-32": Mensaje("Tu rol no permite realizar esta acción."),
    "ERR-33": Mensaje("Tu cuenta está suspendida hasta el {hasta}."),
    "ERR-34": Mensaje("Tu cuenta fue dada de baja de forma definitiva."),
    "ERR-35": Mensaje("Ya existe una cuenta registrada con ese correo."),
    "ERR-36": Mensaje("La subasta no está abierta."),
    "ERR-37": Mensaje("No tienes una puja activa en esta subasta."),
    "ERR-38": Mensaje(
        "Ya tienes una puja activa en esta subasta; modifícala en lugar de crear otra."
    ),
    "ERR-39": Mensaje("Este tipo de subasta no admite esa operación en este momento."),
    "ERR-40": Mensaje(
        "La duración debe estar entre {minimo} y {maximo} horas."
    ),
    "ERR-41": Mensaje("El vendedor no puede pujar en su propia subasta."),
    "ERR-42": Mensaje("Parámetros de la subasta no válidos: {detalle}."),
    "ERR-43": Mensaje("Este registro no te pertenece."),
    "ERR-44": Mensaje("La adjudicación no está pendiente de pago."),
    "ERR-45": Mensaje("El servicio de pagos rechazó el cobro. Intenta de nuevo."),
    "ERR-46": Mensaje(
        "Los registros no se eliminan: deben conservarse por lo menos dos años."
    ),
    "ERR-47": Mensaje(
        "El usuario ya fue dado de baja de forma definitiva; no admite más sanciones."
    ),
    "ERR-48": Mensaje(
        "La subasta no puede publicarse: el moderador aún no aprueba la "
        "descripción y las fotografías."
    ),
    "ERR-49": Mensaje("Debes indicar el motivo."),
    "ERR-50": Mensaje("El artículo solo puede corregirse cuando fue rechazado."),
    "ERR-51": Mensaje("La contraseña debe tener al menos {minimo} caracteres."),
    "ERR-52": Mensaje("El año debe estar entre {minimo} y {maximo}."),
    "ERR-53": Mensaje("El artículo no tiene una publicación activa que retirar."),
    "ERR-54": Mensaje("Solo es posible registrarse como vendedor o como comprador."),
    "ERR-64": Mensaje(
        "El contenido solo se revisa antes de publicar; para una publicación activa "
        "usa «Retirar publicación»."
    ),
    "ERR-65": Mensaje("Solo se sanciona a vendedores y compradores."),
    "ERR-55": Mensaje("Este campo es obligatorio."),
    "ERR-56": Mensaje("Escribe un número entero."),
    "ERR-57": Mensaje("El valor debe ser al menos {limit_value}."),
    "ERR-58": Mensaje("Elige una opción válida."),
    "ERR-59": Mensaje("Escribe un correo electrónico válido."),
    "ERR-60": Mensaje("El archivo no es una imagen válida."),
    "ERR-61": Mensaje("Sube como máximo {maximo} fotografías."),
    "ERR-62": Mensaje("Cada fotografía debe pesar menos de {maximo} MB."),
    "ERR-63": Mensaje("El texto es demasiado largo (máximo {limit_value} caracteres)."),
    "MSG-01": Mensaje("Cuenta creada. Ya puedes iniciar sesión."),
    "MSG-02": Mensaje("Enviamos un código de verificación a tu dispositivo móvil."),
    "MSG-03": Mensaje("Sesión iniciada. Hola, {nombre}."),
    "MSG-04": Mensaje("Sesión cerrada."),
    "MSG-05": Mensaje("Artículo registrado. Quedó en espera de revisión."),
    "MSG-06": Mensaje("Artículo corregido y enviado de nuevo a revisión."),
    "MSG-07": Mensaje("Propuesta de subasta enviada al gestor para su validación."),
    "MSG-08": Mensaje("Artículo aprobado. Estado actual: {estado}."),
    "MSG-09": Mensaje("Artículo rechazado."),
    "MSG-10": Mensaje("Subasta publicada. Cierra el {cierre}."),
    "MSG-11": Mensaje("Propuesta de subasta rechazada."),
    "MSG-12": Mensaje("Puja registrada por {monto:,} fichas."),
    "MSG-13": Mensaje("Puja modificada a {monto:,} fichas."),
    "MSG-14": Mensaje("Puja retirada."),
    "MSG-15": Mensaje(
        "Compra realizada por {monto:,} fichas. Tienes {dias} días para pagar."
    ),
    "MSG-16": Mensaje("Pago recibido. Referencia: {referencia}."),
    "MSG-17": Mensaje("Notificaciones marcadas como leídas."),
    "MSG-18": Mensaje("Revisión de contenido registrada."),
    "MSG-19": Mensaje("Publicación retirada."),
    "MSG-20": Mensaje("Sanción de nivel {nivel} aplicada a {nombre}."),
    "MSG-30": Mensaje(
        "El gestor aprobó tu artículo «{articulo}».",
        asunto="Tu artículo fue aprobado",
    ),
    "MSG-31": Mensaje(
        "El gestor rechazó tu artículo «{articulo}». Motivo: {motivo}. Puedes "
        "corregirlo y enviarlo de nuevo.",
        asunto="Tu artículo fue rechazado",
    ),
    "MSG-32": Mensaje(
        "Tu artículo «{articulo}» quedó listo con un precio mínimo de "
        "{precio:,} fichas. Ya puedes proponer el tipo y la duración de la subasta.",
        asunto="Tu artículo está listo para subastarse",
    ),
    "MSG-33": Mensaje(
        "El valuador no avaló tu artículo «{articulo}», por lo que no puede "
        "subastarse.",
        asunto="Tu artículo no fue avalado",
    ),
    "MSG-34": Mensaje(
        "La subasta de «{articulo}» ya está publicada y cierra el {cierre}.",
        asunto="Tu subasta fue publicada",
    ),
    "MSG-35": Mensaje(
        "El gestor rechazó la propuesta de subasta de «{articulo}». Motivo: "
        "{motivo}. Puedes enviar otra propuesta.",
        asunto="Tu propuesta de subasta fue rechazada",
    ),
    "MSG-36": Mensaje(
        "Tu puja en «{articulo}» fue superada. El precio actual es de "
        "{precio:,} fichas.",
        asunto="Superaron tu puja",
    ),
    "MSG-37": Mensaje(
        "Ganaste la subasta de «{articulo}». El precio final es de {precio:,} "
        "fichas. Tienes {dias} días para pagar: la fecha límite es el {limite}.",
        asunto="Ganaste la subasta",
    ),
    "MSG-38": Mensaje(
        "La subasta de «{articulo}» cerró con ganador. Precio final: {precio:,} "
        "fichas; comisión de la casa: {comision:,}; recibirás {neto:,} fichas "
        "cuando el comprador pague.",
        asunto="Tu subasta cerró con ganador",
    ),
    "MSG-39": Mensaje(
        "La subasta de «{articulo}» cerró sin ganador. Puedes proponer una nueva "
        "subasta.",
        asunto="Tu subasta quedó desierta",
    ),
    "MSG-40": Mensaje(
        "Recibimos tu pago de {precio:,} fichas por «{articulo}». El proveedor "
        "logístico gestionará la entrega (referencia {envio}).",
        asunto="Pago confirmado",
    ),
    "MSG-41": Mensaje(
        "El comprador pagó «{articulo}». Te corresponden {neto:,} fichas. El "
        "proveedor logístico pasará a recolectarlo (referencia {envio}).",
        asunto="Tu artículo fue pagado",
    ),
    "MSG-42": Mensaje(
        "Venció el plazo para pagar «{articulo}» y perdiste la adjudicación.",
        asunto="Venció tu plazo de pago",
    ),
    "MSG-43": Mensaje(
        "El ganador no pagó «{articulo}» dentro del plazo. El artículo se volvió "
        "a subastar y la nueva subasta cierra el {cierre}.",
        asunto="Tu artículo se volvió a subastar",
    ),
    "MSG-44": Mensaje(
        "El moderador rechazó la descripción o las fotografías de «{articulo}». "
        "Motivo: {motivo}. Puedes corregirlo y enviarlo de nuevo.",
        asunto="El contenido de tu artículo fue rechazado",
    ),
    "MSG-45": Mensaje(
        "El moderador retiró la publicación de «{articulo}». Motivo: {motivo}.",
        asunto="Tu publicación fue retirada",
    ),
    "MSG-46": Mensaje(
        "La subasta de «{articulo}» fue cancelada y tu puja quedó sin efecto.",
        asunto="Subasta cancelada",
    ),
    "MSG-47": Mensaje(
        "Se aplicó a tu cuenta una sanción de nivel {nivel}: {descripcion}. "
        "Motivo: {motivo}.",
        asunto="Sanción aplicada a tu cuenta",
    ),
}


def texto(codigo: str, **datos) -> str:
    return CATALOGO[codigo].texto.format(**datos)


def asunto(codigo: str) -> str:
    return CATALOGO[codigo].asunto


class ErrorDeNegocio(Exception):
    def __init__(self, codigo: str, **datos):
        self.codigo = codigo
        self.datos = datos
        self.mensaje = texto(codigo, **datos)
        super().__init__(f"{codigo}: {self.mensaje}")
