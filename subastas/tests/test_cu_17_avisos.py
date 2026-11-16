"""CU-17 Enviar aviso por correo y dentro de la aplicación (Servicio de Notificaciones)."""
from django.urls import reverse

from subastas.models import EntregaNotificacion
from subastas.reglas.notificaciones import Canal
from subastas.servicios import consultas, moderacion, pujas

from .base import PruebaSubastas


class CU17Avisos(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(costo_salida=1000, duracion_horas=24)
        self.comprador = self.crear_comprador()
        pujas.pujar(comprador=self.comprador, subasta_id=self.subasta.pk, monto=1500)
        self.client.force_login(self.comprador)
        self.reloj.avanzar(hours=24)

    def test_ca_17_1_cada_aviso_llega_por_la_aplicacion_y_por_correo(self):
        """CA-17.1 Cada aviso se registra con una entrega por la aplicación y otra por correo."""
        self.client.get(reverse("inicio"))
        aviso = self.comprador.notificaciones.get(tipo="MSG-37")
        self.assertEqual({e.canal for e in aviso.entregas.all()}, {Canal.APP, Canal.CORREO})
        self.assertIn(self.comprador.correo, [d for d, _, _ in self.correo.enviados])

    def test_ca_17_2_si_falla_el_correo_queda_como_fallida(self):
        """CA-17.2 Si el servicio de correo falla, la entrega queda «Fallida» y la operación no se deshace."""
        self.correo.falla = True
        with self.assertLogs("subastas.servicios.notificaciones", level="ERROR"):
            self.client.get(reverse("inicio"))
        entrega = self.comprador.notificaciones.get(tipo="MSG-37").entregas.get(canal=Canal.CORREO)
        self.assertEqual(entrega.estado, EntregaNotificacion.Estado.FALLIDA)

    def test_ca_17_3_el_destinatario_ve_sus_avisos_y_los_marca_como_leidos(self):
        """CA-17.3 El destinatario ve sus avisos con el contador de no leídos y los marca como leídos (MSG-17)."""
        respuesta = self.client.get(reverse("avisos"))
        self.assertContains(respuesta, "MSG-37")
        self.assertContains(respuesta, 'class="contador"')
        respuesta = self.client.post(reverse("marcar_leidas"), follow=True)
        self.assertContains(respuesta, "MSG-17")
        self.assertNotContains(respuesta, 'class="contador"')

    def test_rediseno_fase_e_pago_pendiente_en_el_menu_y_en_inicio(self):
        """Rediseño (fase E) El ganador ve su pago pendiente junto a «Mi historial» y en la tarjeta de inicio."""
        respuesta = self.client.get(reverse("inicio"))
        self.assertEqual(consultas.pendientes_por_rol(self.comprador), {"comprador": 1})
        self.assertContains(respuesta, 'class="contador por-atender">1<', count=2)
        self.assertContains(respuesta, "pago pendiente")

    def test_rediseno_fase_e_pendientes_del_gestor_y_del_moderador(self):
        """Rediseño (fase E) Los contadores del personal coinciden con lo que muestran sus bandejas."""
        self.registrar_articulo()
        self.proponer(self.articulo_listo())
        moderador = self.crear_moderador()
        self.assertEqual(
            consultas.pendientes_por_rol(self.gestor),
            {"gestor_articulos": 1, "gestor_propuestas": 1, "gestor": 2},
        )
        self.assertEqual(
            consultas.pendientes_por_rol(moderador),
            {"moderador": len(moderacion.pendientes_de_revision())},
        )
        self.client.force_login(self.gestor)
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, "artículo por revisar")
        self.assertContains(respuesta, "propuesta por validar")

    def test_rediseno_movil_el_contador_del_moderador_sigue_en_su_bandeja(self):
        """Rediseño (móvil) Dentro de su bandeja el moderador sigue viendo el contador junto a «Moderación»."""
        self.registrar_articulo()
        self.proponer(self.articulo_listo())
        moderador = self.crear_moderador()
        total = len(moderacion.pendientes_de_revision())
        self.assertGreater(total, 0)
        self.client.force_login(moderador)
        respuesta = self.client.get(reverse("moderador_bandeja"))
        self.assertContains(respuesta, f'class="contador por-atender">{total}<span class="solo-lector"> pendientes')

    def test_rediseno_fase_f_los_avisos_no_leidos_dicen_nuevo(self):
        """Rediseño (fase F) Un aviso no leído dice «Nuevo» en texto, no solo con color; al leerlo desaparece."""
        self.assertContains(self.client.get(reverse("avisos")), '<span class="marca-nuevo">Nuevo</span>')
        respuesta = self.client.post(reverse("marcar_leidas"), follow=True)
        self.assertNotContains(respuesta, "marca-nuevo")
