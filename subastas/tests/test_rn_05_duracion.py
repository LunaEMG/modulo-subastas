"""RN-05: el vendedor fija la duración tras el análisis y el gestor la valida. (CU-04, CU-07)"""
from datetime import timedelta

from subastas.reglas import duracion
from subastas.reglas.estados import EstadoArticulo, EstadoSubasta

from .base import INICIO, PruebaSubastas


class RN05Duracion(PruebaSubastas):
    def test_valido_72_horas_tras_la_valuacion_y_validadas(self):
        articulo = self.articulo_listo()
        subasta = self.proponer(articulo, duracion_horas=72)
        self.assertEqual(subasta.estado, EstadoSubasta.PROPUESTA)
        self.assertIsNone(subasta.fecha_cierre)

        subasta = self.publicar(articulo, subasta)
        self.assertEqual(subasta.fecha_inicio, INICIO)
        self.assertEqual(subasta.fecha_cierre, INICIO + timedelta(hours=72))

    def test_invalido_duracion_propuesta_antes_de_la_valuacion(self):
        articulo = self.registrar_articulo()
        self.assertErrorDeNegocio("ERR-05", self.proponer, articulo, duracion_horas=72)

    def test_invalido_sin_validacion_del_gestor_la_subasta_no_abre(self):
        articulo = self.articulo_listo()
        subasta = self.proponer(articulo)
        self.reloj.avanzar(days=10)
        subasta.refresh_from_db()
        self.assertEqual(subasta.estado, EstadoSubasta.PROPUESTA)
        self.assertEqual(articulo.estado, EstadoArticulo.VALUADO)

    def test_invalido_s14_duracion_fuera_de_limites(self):
        articulo = self.articulo_listo()
        self.assertErrorDeNegocio("ERR-40", self.proponer, articulo, duracion_horas=0)
        self.assertErrorDeNegocio("ERR-40", self.proponer, articulo, duracion_horas=721)

    def test_regla_pura(self):
        duracion.validar_propuesta_duracion(estado_articulo=EstadoArticulo.VALUADO, duracion_horas=1)
        duracion.validar_propuesta_duracion(estado_articulo=EstadoArticulo.SIN_VENDER, duracion_horas=720)
        self.assertErrorDeNegocio(
            "ERR-05",
            duracion.validar_propuesta_duracion,
            estado_articulo=EstadoArticulo.EN_VALUACION,
            duracion_horas=24,
        )
