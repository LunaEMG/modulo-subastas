from .base import TipoSubasta


class SubastaInglesa(TipoSubasta):
    codigo = "INGLESA"
    nombre = "Inglesa"
    descripcion = "Los compradores suben el precio; al cierre gana la puja más alta."
