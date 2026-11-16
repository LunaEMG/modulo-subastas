"""CU-17"""
import logging

from django.db import transaction

from .. import eventos, integraciones, mensajes, reloj
from ..models import EntregaNotificacion, Notificacion
from ..reglas import notificaciones as reglas_notificaciones
from ..reglas import sanciones as reglas_sanciones
from ..reglas.notificaciones import Canal

registro = logging.getLogger(__name__)


def notificar(usuario, codigo: str, *, subasta=None, **datos) -> Notificacion:
    """`codigo` es un MSG-xx. Registra una entrega por canal; nunca lanza si falla el correo."""
    notificacion = Notificacion.objects.create(
        usuario=usuario,
        tipo=codigo,
        asunto=mensajes.asunto(codigo),
        mensaje=mensajes.texto(codigo, **datos),
        subasta=subasta,
    )
    EntregaNotificacion.objects.create(
        notificacion=notificacion, canal=Canal.APP, estado=EntregaNotificacion.Estado.ENVIADA
    )
    EntregaNotificacion.objects.create(
        notificacion=notificacion,
        canal=Canal.CORREO,
        estado=(
            EntregaNotificacion.Estado.ENVIADA
            if _enviar_correo(notificacion)
            else EntregaNotificacion.Estado.FALLIDA
        ),
    )
    return notificacion


def _enviar_correo(notificacion: Notificacion) -> bool:
    try:
        return integraciones.obtener("correo").enviar(
            destinatario=notificacion.usuario.correo,
            asunto=notificacion.asunto,
            cuerpo=notificacion.mensaje,
        )
    except Exception:
        # Si el correo de otro equipo falla, no debe deshacer el cierre de una subasta.
        registro.exception("No se pudo enviar el correo de la notificación %s", notificacion.pk)
        return False


def avisar_ganador(subasta) -> Notificacion:
    """RN-10. Lanza ERR-10 si la subasta no tiene adjudicación."""
    adjudicacion = getattr(subasta, "adjudicacion", None)
    datos = reglas_notificaciones.datos_aviso_ganador(
        hay_adjudicacion=adjudicacion is not None,
        articulo=subasta.articulo.titulo,
        precio_final=adjudicacion.precio_final if adjudicacion else 0,
        fecha_limite_pago=adjudicacion.fecha_limite_pago if adjudicacion else reloj.ahora(),
    )
    return notificar(
        adjudicacion.ganador,
        reglas_notificaciones.MENSAJE_AVISO_GANADOR,
        subasta=subasta,
        **datos,
    )


def sin_leer(usuario) -> int:
    return usuario.notificaciones.filter(leida_en__isnull=True).count()


# CU-17
@transaction.atomic
def marcar_leidas(usuario) -> int:
    return usuario.notificaciones.filter(leida_en__isnull=True).update(leida_en=reloj.ahora())


def _al_aprobar_articulo(articulo):
    notificar(articulo.vendedor, "MSG-30", articulo=articulo.titulo)


def _al_rechazar_articulo(articulo, motivo):
    notificar(articulo.vendedor, "MSG-31", articulo=articulo.titulo, motivo=motivo)


def _al_quedar_listo(articulo, precio):
    notificar(articulo.vendedor, "MSG-32", articulo=articulo.titulo, precio=precio)


def _al_no_avalar(articulo):
    notificar(articulo.vendedor, "MSG-33", articulo=articulo.titulo)


def _al_publicar_subasta(subasta):
    notificar(
        subasta.articulo.vendedor,
        "MSG-34",
        subasta=subasta,
        articulo=subasta.articulo.titulo,
        cierre=reloj.formato(subasta.fecha_cierre),
    )


def _al_rechazar_propuesta(subasta, motivo):
    notificar(
        subasta.articulo.vendedor,
        "MSG-35",
        subasta=subasta,
        articulo=subasta.articulo.titulo,
        motivo=motivo,
    )


def _al_superar_puja(subasta, puja_superada, precio):
    notificar(
        puja_superada.comprador,
        "MSG-36",
        subasta=subasta,
        articulo=subasta.articulo.titulo,
        precio=precio,
    )


def _al_adjudicar(adjudicacion):
    subasta = adjudicacion.subasta
    avisar_ganador(subasta)
    notificar(
        subasta.articulo.vendedor,
        "MSG-38",
        subasta=subasta,
        articulo=subasta.articulo.titulo,
        precio=adjudicacion.precio_final,
        comision=adjudicacion.comision,
        neto=adjudicacion.monto_vendedor,
    )


def _al_quedar_desierta(subasta):
    notificar(
        subasta.articulo.vendedor, "MSG-39", subasta=subasta, articulo=subasta.articulo.titulo
    )


def _al_recibir_pago(adjudicacion):
    subasta = adjudicacion.subasta
    titulo = subasta.articulo.titulo
    notificar(
        adjudicacion.ganador,
        "MSG-40",
        subasta=subasta,
        articulo=titulo,
        precio=adjudicacion.precio_final,
        envio=adjudicacion.referencia_envio,
    )
    notificar(
        subasta.articulo.vendedor,
        "MSG-41",
        subasta=subasta,
        articulo=titulo,
        neto=adjudicacion.monto_vendedor,
        envio=adjudicacion.referencia_envio,
    )


def _al_vencer_pago(adjudicacion, nueva_subasta):
    titulo = adjudicacion.subasta.articulo.titulo
    notificar(adjudicacion.ganador, "MSG-42", subasta=adjudicacion.subasta, articulo=titulo)
    notificar(
        adjudicacion.subasta.articulo.vendedor,
        "MSG-43",
        subasta=nueva_subasta,
        articulo=titulo,
        cierre=reloj.formato(nueva_subasta.fecha_cierre),
    )


def _al_rechazar_contenido(articulo, motivo):
    notificar(articulo.vendedor, "MSG-44", articulo=articulo.titulo, motivo=motivo)


def _al_retirar_publicacion(articulo, subasta, motivo, compradores):
    notificar(articulo.vendedor, "MSG-45", subasta=subasta, articulo=articulo.titulo, motivo=motivo)
    for comprador in compradores:
        notificar(comprador, "MSG-46", subasta=subasta, articulo=articulo.titulo)


def _al_sancionar(sancion):
    notificar(
        sancion.usuario,
        "MSG-47",
        nivel=sancion.nivel,
        descripcion=reglas_sanciones.DESCRIPCION_POR_NIVEL[sancion.nivel],
        motivo=sancion.motivo,
    )


def registrar_suscriptores() -> None:
    suscripciones = {
        eventos.ARTICULO_APROBADO: _al_aprobar_articulo,
        eventos.ARTICULO_RECHAZADO: _al_rechazar_articulo,
        eventos.ARTICULO_LISTO: _al_quedar_listo,
        eventos.ARTICULO_NO_AVALADO: _al_no_avalar,
        eventos.SUBASTA_PUBLICADA: _al_publicar_subasta,
        eventos.PROPUESTA_RECHAZADA: _al_rechazar_propuesta,
        eventos.PUJA_SUPERADA: _al_superar_puja,
        eventos.SUBASTA_ADJUDICADA: _al_adjudicar,
        eventos.SUBASTA_DESIERTA: _al_quedar_desierta,
        eventos.PAGO_RECIBIDO: _al_recibir_pago,
        eventos.PAGO_VENCIDO: _al_vencer_pago,
        eventos.CONTENIDO_RECHAZADO: _al_rechazar_contenido,
        eventos.PUBLICACION_RETIRADA: _al_retirar_publicacion,
        eventos.SANCION_APLICADA: _al_sancionar,
    }
    for evento, funcion in suscripciones.items():
        eventos.suscribir(evento, funcion)
