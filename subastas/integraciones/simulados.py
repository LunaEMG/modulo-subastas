"""Comportamiento fijo y predecible, descrito en el README, mientras los otros equipos terminan."""
import json
import uuid

from django.conf import settings

from .. import reloj
from .puertos import (
    Dictamen,
    EnviadorCodigoMovil,
    EnviadorCorreo,
    ProveedorLogistico,
    ResultadoPago,
    ServicioPagos,
    ValidadorIdentidad,
    ValuadorBienes,
)

MAXIMO_EN_BANDEJA = 50


def _referencia(prefijo: str) -> str:
    return f"{prefijo}-{uuid.uuid4().hex[:10].upper()}"


def _dejar_en_bandeja(*, canal: str, destino: str, asunto: str, cuerpo: str) -> None:
    registro = {
        "fecha": reloj.ahora().isoformat(),
        "canal": canal,
        "destino": destino,
        "asunto": asunto,
        "cuerpo": cuerpo,
    }
    settings.BANDEJA_SIMULADA.parent.mkdir(parents=True, exist_ok=True)
    with settings.BANDEJA_SIMULADA.open("a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
    print(f"[{canal} simulado] para {destino}: {asunto} — {cuerpo}")


def leer_bandeja() -> list[dict]:
    try:
        lineas = settings.BANDEJA_SIMULADA.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    registros = []
    for linea in lineas[-MAXIMO_EN_BANDEJA:]:
        try:
            registros.append(json.loads(linea))
        except ValueError:
            continue
    return registros[::-1]


class PagosSimulado(ServicioPagos):
    def cobrar(self, *, comprador_id: int, monto_fichas: int, concepto: str) -> ResultadoPago:
        return ResultadoPago(aprobado=True, referencia=_referencia("PAG"))


class ValuadorSimulado(ValuadorBienes):
    """Rechaza si la descripción menciona «réplica» o «imitación»; si no, avala lo propuesto."""

    PALABRAS_NO_AUTENTICO = ("réplica", "replica", "imitación", "imitacion")

    def valuar(
        self, *, articulo_id: int, categoria: str, descripcion: str, anio: int, precio_propuesto: int
    ) -> Dictamen:
        texto = descripcion.lower()
        if any(palabra in texto for palabra in self.PALABRAS_NO_AUTENTICO):
            return Dictamen(es_autentico=False, precio_avalado=None, referencia=_referencia("VAL"))
        return Dictamen(
            es_autentico=True, precio_avalado=precio_propuesto, referencia=_referencia("VAL")
        )


class LogisticaSimulada(ProveedorLogistico):
    def solicitar_recoleccion(
        self, *, adjudicacion_id: int, vendedor_id: int, comprador_id: int
    ) -> str:
        return _referencia("LOG")


class IdentidadSimulada(ValidadorIdentidad):
    """Acepta códigos postales de 5 dígitos distintos de 00000; ignora los documentos (S-31)."""

    def acredita_residencia_en_mexico(
        self, *, nombre: str, codigo_postal: str, documentos=None
    ) -> bool:
        codigo_postal = codigo_postal.strip()
        return len(codigo_postal) == 5 and codigo_postal.isdecimal() and codigo_postal != "00000"


class CodigoMovilSimulado(EnviadorCodigoMovil):
    def enviar(self, *, telefono: str, codigo: str) -> None:
        _dejar_en_bandeja(
            canal="SMS",
            destino=telefono,
            asunto="Código de verificación",
            cuerpo=f"Tu código para entrar a la casa de subastas es {codigo}",
        )


class CorreoSimulado(EnviadorCorreo):
    def enviar(self, *, destinatario: str, asunto: str, cuerpo: str) -> bool:
        _dejar_en_bandeja(canal="CORREO", destino=destinatario, asunto=asunto, cuerpo=cuerpo)
        return True
