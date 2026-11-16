"""RN-03: ningún servicio asigna `estado` directamente; todo cambio pasa por aquí."""
from ..reglas import estados as reglas_estados


def cambiar_estado_articulo(articulo, nuevo_estado: str) -> None:
    reglas_estados.validar_transicion_articulo(articulo.estado, nuevo_estado)
    articulo.estado = nuevo_estado
    articulo.save(update_fields=["estado"])


def cambiar_estado_subasta(subasta, nuevo_estado: str) -> None:
    reglas_estados.validar_transicion_subasta(subasta.estado, nuevo_estado)
    subasta.estado = nuevo_estado
    subasta.save(update_fields=["estado"])
