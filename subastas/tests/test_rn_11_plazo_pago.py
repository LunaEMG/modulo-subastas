"""RN-11: el ganador tiene 3 días para pagar. (CU-14)"""
from datetime import timedelta

from subastas.reglas import pagos as reglas
from subastas.reglas.estados import EstadoArticulo
from subastas.reglas.pagos import EstadoAdjudicacion
from subastas.servicios import cierre, pujas

from .base import INICIO, PruebaSubastas


class ReglaPlazo(PruebaSubastas):
    def test_la_fecha_limite_es_tres_dias_despues_del_cierre(self):
        self.assertEqual(reglas.calcular_fecha_limite_pago(INICIO), INICIO + timedelta(days=3))

    def test_se_acepta_en_el_ultimo_instante(self):
        reglas.validar_pago_en_plazo(fecha_limite_pago=INICIO, instante=INICIO)

    def test_err_11_un_segundo_despues_se_rechaza(self):
        self.assertErrorDeNegocio(
            "ERR-11", reglas.validar_pago_en_plazo,
            fecha_limite_pago=INICIO, instante=INICIO + timedelta(seconds=1),
        )


class PagarAdjudicacion(PruebaSubastas):
    def setUp(self):
        super().setUp()
        subasta = self.subasta_abierta(costo_salida=1000, duracion_horas=24)
        self.ganador = self.crear_comprador()
        pujas.pujar(comprador=self.ganador, subasta_id=subasta.pk, monto=1500)
        self.reloj.avanzar(hours=24)
        self.adjudicacion = cierre.cerrar_subasta(subasta.pk)

    def _pagar(self, comprador=None):
        return cierre.pagar(comprador=comprador or self.ganador, adjudicacion_id=self.adjudicacion.pk)

    def test_pago_al_segundo_dia(self):
        self.reloj.avanzar(days=2)
        adjudicacion = self._pagar()
        self.assertEqual(adjudicacion.estado, EstadoAdjudicacion.PAGADA)
        self.assertEqual(adjudicacion.referencia_pago, "PAG-PRUEBA")
        self.assertEqual(self.pagos.cobros, [(self.ganador.pk, 1500)])
        self.assertEqual(adjudicacion.subasta.articulo.estado, EstadoArticulo.VENDIDO)

    def test_pago_justo_a_los_tres_dias(self):
        self.reloj.avanzar(days=3)
        self.assertEqual(self._pagar().estado, EstadoAdjudicacion.PAGADA)

    def test_err_11_tres_dias_y_un_segundo_despues(self):
        self.reloj.avanzar(days=3, seconds=1)
        self.assertErrorDeNegocio("ERR-11", self._pagar)
        self.assertEqual(self.pagos.cobros, [])

    def test_err_43_otro_comprador_no_paga_lo_ajeno(self):
        self.assertErrorDeNegocio("ERR-43", self._pagar, self.crear_comprador())

    def test_err_44_no_se_paga_dos_veces(self):
        self._pagar()
        self.assertErrorDeNegocio("ERR-44", self._pagar)
        self.assertEqual(len(self.pagos.cobros), 1)

    def test_err_45_cobro_rechazado_deja_la_adjudicacion_pendiente(self):
        self.pagos.aprueba = False
        self.assertErrorDeNegocio("ERR-45", self._pagar)
        self.adjudicacion.refresh_from_db()
        self.assertEqual(self.adjudicacion.estado, EstadoAdjudicacion.PENDIENTE_PAGO)
        self.assertEqual(self.logistica.solicitudes, [])
