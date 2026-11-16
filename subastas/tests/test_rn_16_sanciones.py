"""RN-16: sanciones escalonadas (semanas, meses, baja definitiva). (CU-20)"""
from datetime import timedelta

from subastas.models import Notificacion, Puja
from subastas.reglas import sanciones as reglas
from subastas.servicios import autenticacion, cuentas, moderacion, pujas

from .base import CONTRASENA, INICIO, PruebaSubastas


class ReglaSanciones(PruebaSubastas):
    def test_el_orden_es_semanas_meses_baja(self):
        self.assertEqual([reglas.siguiente_nivel(n) for n in range(3)], [1, 2, 3])

    def test_err_47_despues_de_la_baja_no_hay_mas_niveles(self):
        self.assertErrorDeNegocio("ERR-47", reglas.siguiente_nivel, 3)

    def test_err_16_no_se_salta_nivel(self):
        self.assertErrorDeNegocio("ERR-16", reglas.validar_nivel, nivel=3, sanciones_previas=0)

    def test_err_16_no_se_repite_nivel(self):
        self.assertErrorDeNegocio("ERR-16", reglas.validar_nivel, nivel=1, sanciones_previas=1)

    def test_s06_duraciones(self):
        self.assertEqual(reglas.calcular_fecha_fin(1, INICIO), INICIO + timedelta(days=14))
        self.assertEqual(reglas.calcular_fecha_fin(2, INICIO), INICIO + timedelta(days=90))
        self.assertIsNone(reglas.calcular_fecha_fin(3, INICIO))

    def test_vigencia(self):
        fin = INICIO + timedelta(days=14)
        self.assertTrue(reglas.esta_vigente(fecha_inicio=INICIO, fecha_fin=fin, instante=INICIO))
        self.assertFalse(reglas.esta_vigente(fecha_inicio=INICIO, fecha_fin=fin, instante=fin))
        self.assertTrue(reglas.esta_vigente(fecha_inicio=INICIO, fecha_fin=None, instante=INICIO + timedelta(days=9999)))


class Sancionar(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.moderador = self.crear_moderador()
        self.infractor = self.crear_comprador()

    def _sancionar(self, **otros):
        datos = {"moderador": self.moderador, "usuario_id": self.infractor.pk, "motivo": "Fotos engañosas"}
        datos.update(otros)
        return moderacion.sancionar(**datos)

    def test_escala_completa_y_estado_de_la_cuenta(self):
        primera = self._sancionar()
        self.assertEqual((primera.nivel, primera.fecha_fin), (1, INICIO + timedelta(days=14)))
        self.assertEqual(cuentas.estado_de_cuenta(self.infractor), cuentas.SUSPENDIDA)
        self.reloj.avanzar(days=14)
        self.assertEqual(cuentas.estado_de_cuenta(self.infractor), cuentas.ACTIVA)
        self.assertEqual(self._sancionar().nivel, 2)
        self.reloj.avanzar(days=90)
        tercera = self._sancionar()
        self.assertEqual((tercera.nivel, tercera.fecha_fin), (3, None))
        self.assertEqual(cuentas.estado_de_cuenta(self.infractor), cuentas.BAJA)
        self.assertEqual([s.nivel for s in moderacion.historial_de_sanciones(self.infractor)], [1, 2, 3])
        self.assertEqual(Notificacion.objects.filter(usuario=self.infractor, tipo="MSG-47").count(), 3)

    def test_err_47_no_se_sanciona_a_quien_ya_tiene_la_baja(self):
        for _ in range(3):
            self._sancionar()
        self.assertErrorDeNegocio("ERR-47", self._sancionar)

    def test_err_16_el_nivel_visto_en_pantalla_ya_no_corresponde(self):
        self._sancionar(nivel=1)
        self.assertErrorDeNegocio("ERR-16", self._sancionar, nivel=1)

    def test_err_49_la_sancion_requiere_motivo(self):
        self.assertErrorDeNegocio("ERR-49", self._sancionar, motivo="  ")

    def test_err_65_no_se_sanciona_al_personal(self):
        self.assertErrorDeNegocio("ERR-65", self._sancionar, usuario_id=self.crear_gestor().pk)

    def test_err_32_solo_el_moderador_sanciona(self):
        self.assertErrorDeNegocio("ERR-32", self._sancionar, moderador=self.crear_gestor())

    def test_err_33_el_suspendido_no_entra_ni_puja(self):
        subasta = self.subasta_abierta()
        self._sancionar()
        self.assertErrorDeNegocio(
            "ERR-33", autenticacion.iniciar_sesion, correo=self.infractor.correo, contrasena=CONTRASENA
        )
        self.assertErrorDeNegocio(
            "ERR-33", pujas.pujar, comprador=self.infractor, subasta_id=subasta.pk, monto=1500
        )

    def test_s20_al_suspender_se_retiran_sus_pujas_activas(self):
        subasta = self.subasta_abierta()
        otro = self.crear_comprador()
        pujas.pujar(comprador=otro, subasta_id=subasta.pk, monto=1200)
        pujas.pujar(comprador=self.infractor, subasta_id=subasta.pk, monto=1500)
        self._sancionar()
        self.assertEqual(Puja.objects.get(comprador=self.infractor).estado, Puja.Estado.RETIRADA)
        self.assertEqual(Puja.objects.get(comprador=otro).estado, Puja.Estado.ACTIVA)
