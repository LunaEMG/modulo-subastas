from ..mensajes import ErrorDeNegocio

# RN-04 no fija precio máximo. S-32: es el mayor entero que PositiveIntegerField guarda en cualquier
# base de Django; un monto mayor (precio, puja o decremento) se rechaza antes de llegar a la columna.
LIMITE_TECNICO_FICHAS = 2_147_483_647


def precio_minimo_avalado(
    *, costo_salida: int, requiere_valuacion: bool, es_autentico: bool, precio_avalado: int | None
) -> int:
    """RN-04. Lanza ERR-04 si el valuador no lo avaló; sin valuador (S-09) vale el propuesto."""
    if not requiere_valuacion:
        return costo_salida
    if not es_autentico or precio_avalado is None:
        raise ErrorDeNegocio("ERR-04")
    return precio_avalado
