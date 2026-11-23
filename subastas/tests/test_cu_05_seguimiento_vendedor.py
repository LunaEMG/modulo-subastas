"""CU-05 Dar seguimiento a sus artículos y subastas (Vendedor), con el resultado de la venta."""
from django.urls import reverse

from subastas import reloj

from subastas.servicios import cierre, consultas, pujas, revision

from .base import PruebaSubastas


class CU05Seguimiento(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(costo_salida=1000, duracion_horas=24)
        self.client.force_login(self.vendedor)
        self.url = reverse("detalle_articulo", args=[self.subasta.articulo_id])

    def test_ca_05_1_el_vendedor_ve_sus_articulos_y_el_estado_de_cada_uno(self):
        """CA-05.1 «Mis artículos» lista los artículos del vendedor y el detalle muestra la subasta «Abierta»."""
        self.assertContains(self.client.get(reverse("mis_articulos")), "Reloj de prueba")
        self.assertContains(self.client.get(self.url), "Abierta")

    def test_ca_05_2_al_venderse_ve_precio_final_comision_y_monto_neto(self):
        """CA-05.2 Al adjudicarse, el detalle muestra precio final, comisión del 25 % y lo que recibirá (RN-14, S-04)."""
        pujas.pujar(comprador=self.crear_comprador(), subasta_id=self.subasta.pk, monto=2000)
        self.reloj.avanzar(hours=24)
        cierre.procesar_pendientes()
        detalle = self.client.get(self.url)
        self.assertContains(detalle, "Comisión (25 %)")
        self.assertContains(detalle, "500 fichas")
        self.assertContains(detalle, "Recibirás")
        self.assertContains(detalle, "1,500 fichas")

    def test_ca_05_3_otro_vendedor_no_ve_el_articulo_err_43(self):
        """CA-05.3 Un vendedor no puede consultar el artículo de otro (ERR-43)."""
        self.client.force_login(self.crear_vendedor())
        self.assertContains(self.client.get(self.url, follow=True), "ERR-43")

    def test_ca_05_4_el_menu_cuenta_los_articulos_que_requieren_accion(self):
        """CA-05.4 El menú cuenta los artículos que requieren acción del vendedor (por corregir o por proponer) y «Mis artículos» los lista arriba, en «Requieren tu acción»; sin pendientes no hay contador ni sección (S-34).

        Con un artículo por proponer y otro rechazado, el contador dice 2 y la sección enlaza a ambos."""
        por_proponer = self.articulo_listo()
        rechazado = self.registrar_articulo()
        revision.rechazar_articulo(gestor=self.gestor, articulo_id=rechazado.pk, motivo="Faltan fotos.")
        self.assertEqual(consultas.pendientes_por_rol(self.vendedor), {"vendedor": 2})
        respuesta = self.client.get(reverse("mis_articulos"))
        self.assertContains(respuesta, 'class="contador por-atender">2<')
        self.assertContains(respuesta, "Requieren tu acción")
        self.assertContains(respuesta, reverse("proponer_subasta", args=[por_proponer.pk]))
        self.assertContains(respuesta, reverse("corregir_articulo", args=[rechazado.pk]))

    def test_ca_05_4_sin_pendientes_no_hay_contador_ni_seccion(self):
        """CA-05.4 El menú cuenta los artículos que requieren acción del vendedor (por corregir o por proponer) y «Mis artículos» los lista arriba, en «Requieren tu acción»; sin pendientes no hay contador ni sección (S-34).

        Un artículo ya en subasta no requiere acción: no hay contador ni sección."""
        respuesta = self.client.get(reverse("mis_articulos"))
        self.assertNotContains(respuesta, "Requieren tu acción")
        self.assertNotContains(respuesta, "contador por-atender")

    def test_una_subasta_desierta_rotula_el_cierre_programado(self):
        """Una subasta cerrada sin adjudicación rotula su fecha como «Cierre programado» y regresa al artículo, no a «Subastas abiertas»."""
        self.reloj.avanzar(hours=24)
        cierre.procesar_pendientes()
        html = self.client.get(reverse("detalle_subasta", args=[self.subasta.pk])).content.decode()
        self.assertIn(f"<dt>Cierre programado</dt><dd>{reloj.formato(self.subasta.fecha_cierre)}</dd>", html)
        self.assertIn("← Volver al artículo", html)
        self.assertNotIn("Pujas activas", html)
        self.assertIn("Precio al cierre", html)
        self.assertNotIn("Precio actual", html)

    def test_rnf_02_los_montos_holandeses_llevan_fichas(self):
        """RNF-02 En la ficha del artículo, «desde» y «baja» de la holandesa llevan su unidad en fichas."""
        holandesa = self.subasta_abierta(tipo="HOLANDESA", holandesa_precio_inicial=5000, holandesa_decremento=100, holandesa_intervalo_min=60)
        html = self.client.get(reverse("detalle_articulo", args=[holandesa.articulo_id])).content.decode()
        self.assertIn("desde 5,000 fichas, baja 100 fichas cada 60 min", html)

    def test_la_propuesta_enviada_explica_el_orden_de_revision(self):
        """Con la propuesta enviada, la ficha del artículo explica que primero la revisa el moderador y después el gestor."""
        articulo = self.articulo_listo()
        self.proponer(articulo)
        respuesta = self.client.get(reverse("detalle_articulo", args=[articulo.pk]))
        self.assertContains(respuesta, "Tu propuesta la revisa primero el moderador y después el gestor.")
