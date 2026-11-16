from ..mensajes import ErrorDeNegocio

# RN-04 no fija precio máximo. S-32: el tope es el mayor entero que PositiveIntegerField guarda en
# cualquier base de datos de Django; vale para todo monto en fichas (precios, pujas, decrementos).
PRECIO_MAXIMO = 2_147_483_647


def precio_minimo_avalado(
    *, costo_salida: int, requiere_valuacion: bool, es_autentico: bool, precio_avalado: int | None
) -> int:
    """RN-04. Lanza ERR-04 si el valuador no lo avaló; sin valuador (S-09) vale el propuesto."""
    if not requiere_valuacion:
        return costo_salida
    if not es_autentico or precio_avalado is None:
        raise ErrorDeNegocio("ERR-04")
    return precio_avalado
