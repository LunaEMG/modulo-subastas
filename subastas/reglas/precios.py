from ..mensajes import ErrorDeNegocio

# No hay precio máximo de negocio (RN-04). S-32: límite técnico de almacenamiento, no regla de negocio.
# Es el mayor entero que PositiveIntegerField guarda en cualquier base de datos de Django; un monto en
# fichas mayor (precio, puja o decremento) no cabe en la columna, así que se rechaza antes de guardarlo.
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
