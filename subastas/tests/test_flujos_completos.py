"""Un flujo de punta a punta por tipo de subasta: CU-01, 03, 06, 04, 07, 09 a 12, 15 y 14 o 16."""
from subastas.models import Adjudicacion, Notificacion
from subastas.reglas.articulos import AUTOMOVILES, VIDEOJUEGOS
from subastas.reglas.estados import EstadoArticulo, EstadoSubasta
from subastas.reglas.pagos import EstadoAdjudicacion
from subastas.servicios import cierre, pujas

from .base import PruebaSubastas


class FlujoCompleto(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.ana = self.crear_comprador()
        self.beto = self.crear_comprador()

    def publicar_nuevo(self, *, categoria=AUTOMOVILES, costo_salida=10000, **propuesta):
        articulo = self.articulo_listo(categoria=categoria, costo_salida=costo_salida, titulo="Sedán 2015")
        self.assertEqual(articulo.estado, EstadoArticulo.VALUADO)
        subasta = self.publicar(articulo, self.proponer(articulo, **propuesta))
        self.assertEqual(subasta.estado, EstadoSubasta.ABIERTA)
        return subasta

    def pagar_y_comprobar(self, adjudicacion, ganador, precio):
        self.assertEqual((adjudicacion.ganador, adjudicacion.precio_final), (ganador, precio))
        self.reloj.avanzar(days=1)
        pagada = cierre.pagar(comprador=ganador, adjudicacion_id=adjudicacion.pk)
        self.assertEqual(pagada.estado, EstadoAdjudicacion.PAGADA)
        self.assertEqual(pagada.subasta.articulo.estado, EstadoArticulo.VENDIDO)
        self.assertEqual(len(self.logistica.solicitudes), 1)
        self.assertEqual(pagada.comision + pagada.monto_vendedor, precio)
        self.assertTrue(Notificacion.objects.filter(usuario=self.vendedor, tipo="MSG-41").exists())
        return pagada


    def test_inglesa_hasta_el_pago(self):
        subasta = self.publicar_nuevo(tipo="INGLESA", duracion_horas=48)
        self.assertEqual(self.valuador.solicitudes, [subasta.articulo_id])
        pujas.pujar(comprador=self.ana, subasta_id=subasta.pk, monto=11000)
        pujas.pujar(comprador=self.beto, subasta_id=subasta.pk, monto=12000)
        pujas.modificar_puja(comprador=self.ana, subasta_id=subasta.pk, nuevo_monto=12500)
        self.reloj.avanzar(hours=48)
        cierre.procesar_pendientes()
        pagada = self.pagar_y_comprobar(Adjudicacion.objects.get(), self.ana, 12500)
        self.assertEqual(pagada.comision, 3125)

    def test_inglesa_con_impago_se_resubasta_y_se_paga(self):
        subasta = self.publicar_nuevo(tipo="INGLESA", duracion_horas=24)
        pujas.pujar(comprador=self.ana, subasta_id=subasta.pk, monto=15000)
        self.reloj.avanzar(hours=24)
        cierre.procesar_pendientes()
        self.reloj.avanzar(days=3, seconds=1)
        cierre.procesar_pendientes()
        self.assertEqual(Adjudicacion.objects.get().estado, EstadoAdjudicacion.VENCIDA)
        nueva = subasta.resubastas.get()
        self.assertEqual(nueva.estado, EstadoSubasta.ABIERTA)
        pujas.pujar(comprador=self.beto, subasta_id=nueva.pk, monto=10500)
        self.reloj.avanzar(hours=24)
        cierre.procesar_pendientes()
        self.pagar_y_comprobar(nueva.adjudicacion, self.beto, 10500)


    def test_reservada_alcanzada_hasta_el_pago(self):
        subasta = self.publicar_nuevo(tipo="RESERVADA", precio_reserva=14000, duracion_horas=24)
        pujas.pujar(comprador=self.ana, subasta_id=subasta.pk, monto=13000)
        pujas.pujar(comprador=self.beto, subasta_id=subasta.pk, monto=14000)
        self.reloj.avanzar(hours=24)
        adjudicacion = cierre.cerrar_subasta(subasta.pk)
        self.pagar_y_comprobar(adjudicacion, self.beto, 14000)

    def test_reservada_no_alcanzada_queda_desierta_y_se_vuelve_a_proponer(self):
        subasta = self.publicar_nuevo(tipo="RESERVADA", precio_reserva=20000, duracion_horas=24)
        pujas.pujar(comprador=self.ana, subasta_id=subasta.pk, monto=13000)
        self.reloj.avanzar(hours=24)
        self.assertIsNone(cierre.cerrar_subasta(subasta.pk))
        articulo = subasta.articulo
        articulo.refresh_from_db()
        self.assertEqual(articulo.estado, EstadoArticulo.SIN_VENDER)
        self.assertTrue(Notificacion.objects.filter(usuario=self.vendedor, tipo="MSG-39").exists())
        # S-16: el vendedor propone otra subasta, ahora inglesa.
        segunda = self.publicar(articulo, self.proponer(articulo, tipo="INGLESA", duracion_horas=24))
        pujas.pujar(comprador=self.ana, subasta_id=segunda.pk, monto=13000)
        self.reloj.avanzar(hours=24)
        self.pagar_y_comprobar(cierre.cerrar_subasta(segunda.pk), self.ana, 13000)


    def test_holandesa_hasta_el_pago(self):
        subasta = self.publicar_nuevo(
            categoria=VIDEOJUEGOS, costo_salida=1000, tipo="HOLANDESA",
            holandesa_precio_inicial=2000, holandesa_decremento=250, holandesa_intervalo_min=30,
        )
        self.assertEqual(self.valuador.solicitudes, [])  # S-09: videojuegos sin valuador
        self.reloj.avanzar(minutes=65)
        adjudicacion = pujas.aceptar_precio_holandesa(comprador=self.beto, subasta_id=subasta.pk)
        self.pagar_y_comprobar(adjudicacion, self.beto, 1500)

    def test_holandesa_sin_aceptacion_queda_desierta(self):
        subasta = self.publicar_nuevo(
            categoria=VIDEOJUEGOS, costo_salida=1000, tipo="HOLANDESA", duracion_horas=2,
            holandesa_precio_inicial=2000, holandesa_decremento=250, holandesa_intervalo_min=30,
        )
        self.reloj.avanzar(hours=2)
        cierre.procesar_pendientes()
        subasta.refresh_from_db()
        self.assertEqual(subasta.estado, EstadoSubasta.DESIERTA)


    def test_compra_inmediata_hasta_el_pago(self):
        subasta = self.publicar_nuevo(tipo="COMPRA_INMEDIATA", precio_compra_inmediata=18000)
        pujas.pujar(comprador=self.ana, subasta_id=subasta.pk, monto=11000)
        adjudicacion = pujas.comprar_de_inmediato(comprador=self.beto, subasta_id=subasta.pk)
        self.pagar_y_comprobar(adjudicacion, self.beto, 18000)

    def test_compra_inmediata_cierra_por_tiempo_con_la_puja_mas_alta(self):
        subasta = self.publicar_nuevo(tipo="COMPRA_INMEDIATA", precio_compra_inmediata=18000, duracion_horas=24)
        pujas.pujar(comprador=self.ana, subasta_id=subasta.pk, monto=11000)
        self.reloj.avanzar(hours=24)
        self.pagar_y_comprobar(cierre.cerrar_subasta(subasta.pk), self.ana, 11000)

    def test_compra_inmediata_con_impago_se_resubasta_con_los_mismos_parametros(self):
        subasta = self.publicar_nuevo(tipo="COMPRA_INMEDIATA", precio_compra_inmediata=18000)
        adjudicacion = pujas.comprar_de_inmediato(comprador=self.ana, subasta_id=subasta.pk)
        self.reloj.avanzar(days=3, seconds=1)
        nueva = cierre.vencer_pago_y_resubastar(adjudicacion.pk)
        self.assertEqual((nueva.tipo, nueva.precio_compra_inmediata), ("COMPRA_INMEDIATA", 18000))
        self.pagar_y_comprobar(
            pujas.comprar_de_inmediato(comprador=self.beto, subasta_id=nueva.pk), self.beto, 18000
        )
