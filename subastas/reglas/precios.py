from ..mensajes import ErrorDeNegocio

# RN-04: no hay precio máximo; la constante lo deja explícito.
PRECIO_MAXIMO = None


def precio_minimo_avalado(
    *, costo_salida: int, requiere_valuacion: bool, es_autentico: bool, precio_avalado: int | None
) -> int:
    """RN-04. Lanza ERR-04 si el valuador no lo avaló; sin valuador (S-09) vale el propuesto."""
    if not requiere_valuacion:
        return costo_salida
    if not es_autentico or precio_avalado is None:
        raise ErrorDeNegocio("ERR-04")
    return precio_avalado
