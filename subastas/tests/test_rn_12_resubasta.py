"""RN-12: si el ganador no paga en el plazo, el artículo se resubasta. (CU-16)"""
from datetime import timedelta

from subastas.models import Notificacion, Subasta
from subastas.reglas import pagos as reglas
from subastas.reglas.estados import EstadoArticulo, EstadoSubasta
from subastas.reglas.pagos import EstadoAdjudicacion
from subastas.servicios import cierre, pujas

from .base import INICIO, PruebaSubastas


class ReglaResubasta(PruebaSubastas):
    def test_se_resubasta_lo_no_pagado_y_vencido(self):
        reglas.validar_resubasta(
            estado=EstadoAdjudicacion.PENDIENTE_PAGO,
            fecha_limite_pago=INICIO, instante=INICIO + timedelta(seconds=1),
        )

    def test_err_12_no_se_resubasta_dentro_del_plazo(self):
        self.assertErrorDeNegocio(
            "ERR-12", reglas.validar_resubasta,
            estado=EstadoAdjudicacion.PENDIENTE_PAGO, fecha_limite_pago=INICIO, instante=INICIO,
        )

    def test_err_12_no_se_resubasta_lo_pagado(self):
        self.assertErrorDeNegocio(
            "ERR-12", reglas.validar_resubasta,
            estado=EstadoAdjudicacion.PAGADA,
            fecha_limite_pago=INICIO, instante=INICIO + timedelta(days=9),
        )


class VencerYResubastar(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(costo_salida=1000, duracion_horas=24)
        self.ganador = self.crear_comprador()
        pujas.pujar(comprador=self.ganador, subasta_id=self.subasta.pk, monto=1500)
        self.reloj.avanzar(hours=24)
        self.adjudicacion = cierre.cerrar_subasta(self.subasta.pk)

    def test_al_vencer_se_abre_una_nueva_subasta_igual(self):
        self.reloj.avanzar(days=3, seconds=1)
        nueva = cierre.vencer_pago_y_resubastar(self.adjudicacion.pk)
        self.adjudicacion.refresh_from_db()
        self.assertEqual(self.adjudicacion.estado, EstadoAdjudicacion.VENCIDA)
        self.assertEqual(nueva.subasta_origen, self.subasta)
        self.assertEqual((nueva.estado, nueva.tipo, nueva.precio_salida), (EstadoSubasta.ABIERTA, "INGLESA", 1000))
        self.assertEqual(nueva.fecha_cierre, nueva.fecha_inicio + timedelta(hours=24))
        self.assertEqual(nueva.articulo.estado, EstadoArticulo.EN_SUBASTA)
        self.assertTrue(Notificacion.objects.filter(usuario=self.ganador, tipo="MSG-42").exists())
        self.assertTrue(Notificacion.objects.filter(usuario=self.vendedor, tipo="MSG-43").exists())

    def test_el_moroso_ya_no_puede_pagar(self):
        self.reloj.avanzar(days=3, seconds=1)
        cierre.vencer_pago_y_resubastar(self.adjudicacion.pk)
        self.assertErrorDeNegocio(
            "ERR-44", cierre.pagar, comprador=self.ganador, adjudicacion_id=self.adjudicacion.pk
        )

    def test_err_12_dentro_del_plazo_no_se_resubasta(self):
        self.reloj.avanzar(days=3)
        self.assertErrorDeNegocio("ERR-12", cierre.vencer_pago_y_resubastar, self.adjudicacion.pk)
        self.assertEqual(Subasta.objects.count(), 1)

    def test_procesar_pendientes_resubasta_sin_reloj_real(self):
        self.reloj.avanzar(days=3, seconds=1)
        self.assertEqual(cierre.procesar_pendientes(), {"cerradas": 0, "resubastadas": 1})
        self.assertEqual(cierre.procesar_pendientes(), {"cerradas": 0, "resubastadas": 0})
