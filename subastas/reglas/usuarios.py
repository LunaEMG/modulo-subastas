from ..mensajes import ErrorDeNegocio


# RN-15
def validar_residencia(*, acreditada: bool) -> None:
    if not acreditada:
        raise ErrorDeNegocio("ERR-15")
