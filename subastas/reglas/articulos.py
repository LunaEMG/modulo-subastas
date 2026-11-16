from ..mensajes import ErrorDeNegocio

AUTOMOVILES = "Automóviles"
RELOJES = "Relojes"
VIDEOJUEGOS = "Videojuegos"
ARTICULOS_DE_OFICINA = "Artículos de oficina"

# RN-01. El valor dice si la categoría pasa por el valuador (S-09).
CATEGORIAS_PERMITIDAS: dict[str, bool] = {
    AUTOMOVILES: True,
    RELOJES: True,
    VIDEOJUEGOS: False,
    ARTICULOS_DE_OFICINA: False,
}

# S-22
ANIO_MINIMO = 1800


# RN-01
def validar_categoria(nombre_categoria: str) -> None:
    if nombre_categoria not in CATEGORIAS_PERMITIDAS:
        raise ErrorDeNegocio("ERR-01", categoria=nombre_categoria)


# RN-02
def validar_datos_articulo(
    *, descripcion: str, anio: int | None, costo_salida: int | None, numero_fotografias: int
) -> None:
    faltantes = []
    if not (descripcion or "").strip():
        faltantes.append("descripción")
    if anio is None:
        faltantes.append("año")
    if costo_salida is None or costo_salida <= 0:
        faltantes.append("costo de salida mayor a cero")
    if numero_fotografias < 1:
        faltantes.append("al menos una fotografía")
    if faltantes:
        raise ErrorDeNegocio("ERR-02", faltantes=", ".join(faltantes))


# S-22
def validar_anio(anio: int, anio_en_curso: int) -> None:
    if not ANIO_MINIMO <= anio <= anio_en_curso:
        raise ErrorDeNegocio("ERR-52", minimo=ANIO_MINIMO, maximo=anio_en_curso)
