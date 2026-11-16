"""RF-01: cuatro tipos de subasta y la validación de sus parámetros. (CU-04)"""
from subastas import subastas_tipos as tipos

from .base import PruebaSubastas


class RF01TiposDeSubasta(PruebaSubastas):
    def test_existen_los_cuatro_tipos(self):
        self.assertEqual(
            {tipo.codigo for tipo in tipos.todos()},
            {"INGLESA", "RESERVADA", "HOLANDESA", "COMPRA_INMEDIATA"},
        )

    def test_err_42_tipo_desconocido(self):
        self.assertErrorDeNegocio("ERR-42", tipos.obtener, "SUBIDA")

    def test_valido_cada_tipo_con_sus_parametros(self):
        casos = {
            "INGLESA": {},
            "RESERVADA": {"precio_reserva": 1500},
            "COMPRA_INMEDIATA": {"precio_compra_inmediata": 3000},
            "HOLANDESA": {
                "holandesa_precio_inicial": 2000,
                "holandesa_decremento": 100,
                "holandesa_intervalo_min": 30,
            },
        }
        for tipo, parametros in casos.items():
            with self.subTest(tipo=tipo):
                subasta = self.proponer(self.articulo_listo(costo_salida=1000), tipo=tipo, **parametros)
                self.assertEqual(subasta.tipo, tipo)
                self.assertEqual(subasta.precio_salida, 1000)

    def test_invalido_parametros_faltantes_ajenos_o_incoherentes(self):
        casos = [
            ("RESERVADA", {}),
            ("RESERVADA", {"precio_reserva": 500}),
            ("INGLESA", {"precio_reserva": 1500}),
            ("COMPRA_INMEDIATA", {"precio_compra_inmediata": 1000}),
            ("HOLANDESA", {"holandesa_precio_inicial": 2000}),
            (
                "HOLANDESA",
                {"holandesa_precio_inicial": 900, "holandesa_decremento": 10, "holandesa_intervalo_min": 5},
            ),
        ]
        articulo = self.articulo_listo(costo_salida=1000)
        for tipo, parametros in casos:
            with self.subTest(tipo=tipo, parametros=parametros):
                self.assertErrorDeNegocio("ERR-42", self.proponer, articulo, tipo=tipo, **parametros)

    def test_invalido_rn13_montos_no_enteros(self):
        articulo = self.articulo_listo(costo_salida=1000)
        self.assertErrorDeNegocio(
            "ERR-13", self.proponer, articulo, tipo="RESERVADA", precio_reserva="1500.5"
        )
