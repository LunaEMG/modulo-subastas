"""RF-03: al pagar se solicita la recolección al proveedor logístico. (CU-14)"""
from subastas.models import Notificacion
from subastas.servicios import cierre, pujas

from .base import PruebaSubastas


class SolicitudLogistica(PruebaSubastas):
    def setUp(self):
        super().setUp()
        subasta = self.subasta_abierta(costo_salida=1000, duracion_horas=24)
        self.ganador = self.crear_comprador()
        pujas.pujar(comprador=self.ganador, subasta_id=subasta.pk, monto=2000)
        self.reloj.avanzar(hours=24)
        self.adjudicacion = cierre.cerrar_subasta(subasta.pk)

    def test_el_pago_solicita_la_recoleccion(self):
        adjudicacion = cierre.pagar(comprador=self.ganador, adjudicacion_id=self.adjudicacion.pk)
        self.assertEqual(
            self.logistica.solicitudes, [(adjudicacion.pk, self.vendedor.pk, self.ganador.pk)]
        )
        self.assertEqual(adjudicacion.referencia_envio, "LOG-PRUEBA")
        # S-04: el vendedor recibe el precio menos la comisión.
        aviso = Notificacion.objects.get(usuario=self.vendedor, tipo="MSG-41")
        self.assertIn("1500", aviso.mensaje.replace(",", ""))

    def test_sin_pago_no_hay_recoleccion(self):
        self.pagos.aprueba = False
        self.assertErrorDeNegocio(
            "ERR-45", cierre.pagar, comprador=self.ganador, adjudicacion_id=self.adjudicacion.pk
        )
        self.assertEqual(self.logistica.solicitudes, [])
