"""RN-10: al ganador se le avisa por correo y en la aplicación. (CU-15, CU-17)"""
from subastas.models import EntregaNotificacion, Notificacion
from subastas.reglas import notificaciones as reglas
from subastas.reglas.notificaciones import Canal
from subastas.servicios import cierre, notificaciones, pujas

from .base import INICIO, PruebaSubastas


class ReglaAvisoGanador(PruebaSubastas):
    def test_el_aviso_lleva_precio_y_plazo(self):
        datos = reglas.datos_aviso_ganador(
            hay_adjudicacion=True, articulo="Reloj", precio_final=1500, fecha_limite_pago=INICIO
        )
        self.assertEqual((datos["precio"], datos["dias"]), (1500, 3))

    def test_err_10_sin_adjudicacion_no_hay_aviso_de_ganador(self):
        self.assertErrorDeNegocio(
            "ERR-10", reglas.datos_aviso_ganador,
            hay_adjudicacion=False, articulo="Reloj", precio_final=0, fecha_limite_pago=INICIO,
        )

    def test_los_canales_son_correo_y_aplicacion(self):
        self.assertEqual(set(reglas.CANALES_AVISO_GANADOR), {Canal.APP, Canal.CORREO})


class AvisoAlCerrar(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(costo_salida=1000, duracion_horas=24)
        self.comprador = self.crear_comprador()
        pujas.pujar(comprador=self.comprador, subasta_id=self.subasta.pk, monto=1500)
        self.reloj.avanzar(hours=24)

    def _aviso_ganador(self):
        return Notificacion.objects.get(usuario=self.comprador, tipo="MSG-37")

    def test_el_ganador_recibe_el_aviso_por_los_dos_canales(self):
        cierre.cerrar_subasta(self.subasta.pk)
        aviso = self._aviso_ganador()
        self.assertIn("1500", aviso.mensaje.replace(",", ""))
        self.assertIn("3 días", aviso.mensaje)
        self.assertEqual(
            {(e.canal, e.estado) for e in aviso.entregas.all()},
            {(Canal.APP, "ENVIADA"), (Canal.CORREO, "ENVIADA")},
        )
        self.assertIn(self.comprador.correo, [d for d, _, _ in self.correo.enviados])
        self.assertEqual(notificaciones.sin_leer(self.comprador), 1)

    def test_si_falla_el_correo_la_subasta_queda_cerrada(self):
        self.correo.falla = True
        with self.assertLogs("subastas.servicios.notificaciones", level="ERROR"):
            adjudicacion = cierre.cerrar_subasta(self.subasta.pk)
        self.assertIsNotNone(adjudicacion.pk)
        entrega = self._aviso_ganador().entregas.get(canal=Canal.CORREO)
        self.assertEqual(entrega.estado, EntregaNotificacion.Estado.FALLIDA)
        # El aviso dentro de la aplicación sí llegó.
        self.assertEqual(self._aviso_ganador().entregas.get(canal=Canal.APP).estado, "ENVIADA")

    def test_err_10_una_subasta_desierta_no_avisa_ganador(self):
        desierta = self.subasta_abierta(duracion_horas=1)
        self.reloj.avanzar(hours=1)
        cierre.cerrar_subasta(desierta.pk)
        desierta.refresh_from_db()
        self.assertErrorDeNegocio("ERR-10", notificaciones.avisar_ganador, desierta)
        self.assertTrue(Notificacion.objects.filter(tipo="MSG-39", subasta=desierta).exists())

    def test_marcar_leidas(self):
        cierre.cerrar_subasta(self.subasta.pk)
        self.assertGreater(notificaciones.marcar_leidas(self.comprador), 0)
        self.assertEqual(notificaciones.sin_leer(self.comprador), 0)
