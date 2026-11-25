"""Contratos con los servicios de otros equipos; la implementación se elige en settings.INTEGRACIONES."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ResultadoPago:
    aprobado: bool
    referencia: str = ""


@dataclass(frozen=True)
class Dictamen:
    es_autentico: bool
    # None cuando el valuador no avala el precio mínimo propuesto.
    precio_avalado: int | None
    referencia: str = ""


class ServicioPagos(ABC):
    @abstractmethod
    def cobrar(self, *, comprador_id: int, monto_fichas: int, concepto: str) -> ResultadoPago:
        """Un cobro rechazado se reporta con aprobado=False."""


class ValuadorBienes(ABC):
    @abstractmethod
    def valuar(
        self, *, articulo_id: int, categoria: str, descripcion: str, anio: int, precio_propuesto: int
    ) -> Dictamen:
        """Autentica el bien y avala (o no) su precio mínimo (RN-04)."""


class ProveedorLogistico(ABC):
    @abstractmethod
    def solicitar_recoleccion(
        self, *, adjudicacion_id: int, vendedor_id: int, comprador_id: int
    ) -> str:
        """Devuelve la referencia del envío."""


@dataclass(frozen=True)
class DocumentosIdentidad:
    """S-31: opcionales porque el registro aún no los pide; se reenvían sin guardarse.
    `tarjeta` es la referencia del módulo de pagos, nunca el número."""

    identificacion_oficial: object | None = None
    curp: str = ""
    tarjeta: str = ""
    comprobante_domicilio: object | None = None

    @property
    def vacio(self) -> bool:
        return not (
            self.identificacion_oficial or self.curp or self.tarjeta or self.comprobante_domicilio
        )


class ValidadorIdentidad(ABC):
    @abstractmethod
    def acredita_residencia_en_mexico(
        self,
        *,
        nombre: str,
        codigo_postal: str,
        documentos: DocumentosIdentidad | None = None,
    ) -> bool:
        """Hoy el registro solo envía nombre y código postal (S-31)."""


class EnviadorCodigoMovil(ABC):
    @abstractmethod
    def enviar(self, *, telefono: str, codigo: str) -> None:
        """Recibe el código en claro; es el único lugar donde sale sin hash (RF-02)."""


class EnviadorCorreo(ABC):
    @abstractmethod
    def enviar(self, *, destinatario: str, asunto: str, cuerpo: str) -> bool:
        """Puede lanzar excepción si el servicio falla; quien llama no debe deshacer su operación."""
