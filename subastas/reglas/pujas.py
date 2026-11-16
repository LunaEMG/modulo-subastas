from ..mensajes import ErrorDeNegocio

# S-05: aplica también a la primera puja.
INCREMENTO_MINIMO = 1


def precio_vigente(precio_salida: int, monto_mas_alto: int | None) -> int:
    """S-03: se calcula de las pujas activas, así que al retirar la más alta regresa solo."""
    return precio_salida if monto_mas_alto is None else monto_mas_alto


# RN-06
def validar_puja(*, monto: int, precio_actual: int) -> None:
    minimo = precio_actual + INCREMENTO_MINIMO
    if monto < minimo:
        raise ErrorDeNegocio("ERR-06", precio_actual=precio_actual, minimo=minimo)


# RN-07
def validar_retiro(*, subasta_abierta: bool) -> None:
    if not subasta_abierta:
        raise ErrorDeNegocio("ERR-07")


# RN-08
def validar_modificacion(
    *, nuevo_monto: int, precio_actual: int, monto_anterior: int, subasta_abierta: bool
) -> None:
    supera_actual = nuevo_monto >= precio_actual + INCREMENTO_MINIMO
    supera_propia = nuevo_monto > monto_anterior
    if not (subasta_abierta and supera_actual and supera_propia):
        raise ErrorDeNegocio("ERR-08", precio_actual=precio_actual, anterior=monto_anterior)


# S-13
def validar_no_es_vendedor(*, comprador_id: int, vendedor_id: int) -> None:
    if comprador_id == vendedor_id:
        raise ErrorDeNegocio("ERR-41")
