from ..mensajes import ErrorDeNegocio
from .precios import LIMITE_TECNICO_FICHAS

# RN-13
FICHAS_POR_PESO = 1

# RN-14
PORCENTAJE_COMISION = 25


# RN-13 y S-32
def validar_monto_fichas(valor) -> int:
    if isinstance(valor, bool):
        raise ErrorDeNegocio("ERR-13")
    if isinstance(valor, str):
        valor = valor.strip()
        if not valor.isdecimal():
            raise ErrorDeNegocio("ERR-13")
        valor = int(valor)
    if not isinstance(valor, int) or valor <= 0:
        raise ErrorDeNegocio("ERR-13")
    if valor > LIMITE_TECNICO_FICHAS:
        raise ErrorDeNegocio("ERR-66")
    return valor


# RN-13
def pesos_a_fichas(pesos: int) -> int:
    return validar_monto_fichas(pesos) * FICHAS_POR_PESO


def calcular_comision(precio_final: int) -> int:
    """RN-14. S-21: redondea hacia abajo; es el único lugar donde se redondea."""
    return precio_final * PORCENTAJE_COMISION // 100


# S-04: la comisión la paga el vendedor.
def calcular_monto_vendedor(precio_final: int, comision: int) -> int:
    return precio_final - comision


# RN-14
def validar_comision(*, precio_final: int, comision: int) -> None:
    esperada = calcular_comision(precio_final)
    if comision != esperada:
        raise ErrorDeNegocio(
            "ERR-14", comision=comision, porcentaje=PORCENTAJE_COMISION, esperada=esperada
        )
