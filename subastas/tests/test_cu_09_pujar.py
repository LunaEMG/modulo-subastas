"""CU-09 Pujar (Comprador), con el flujo alterno de aceptar el precio en la holandesa."""
from django.urls import reverse

from subastas.models import Puja
from subastas.servicios import pujas

from .base import PruebaSubastas


class CU09Pujar(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(costo_salida=1000)
        self.client.force_login(self.crear_comprador())
        self.detalle = reverse("detalle_subasta", args=[self.subasta.pk])

    def test_ca_09_1_una_puja_mayor_al_precio_actual_se_acepta(self):
        """CA-09.1 Una puja mayor al precio actual se acepta (MSG-12) y el comprador ve que va ganando."""
        self.client.post(reverse("pujar", args=[self.subasta.pk]), {"monto": "1200"})
        detalle = self.client.get(self.detalle)
        self.assertContains(detalle, "MSG-12")
        self.assertContains(detalle, "Vas ganando")
        self.assertEqual(Puja.objects.get().monto, 1200)

    def test_ca_09_2_una_puja_que_no_supera_el_precio_se_rechaza_con_err_06(self):
        """CA-09.2 Una puja que no supera el precio actual se rechaza con ERR-06 (RN-06)."""
        respuesta = self.client.post(reverse("pujar", args=[self.subasta.pk]), {"monto": "900"}, follow=True, **self.desde(self.detalle))
        self.assertContains(respuesta, "ERR-06")
        self.assertFalse(Puja.objects.exists())

    def test_ca_09_3_quien_es_superado_recibe_un_aviso(self):
        """CA-09.3 Al ser superada su puja, el comprador anterior recibe el aviso MSG-36 (S-28)."""
        primero = self.crear_comprador()
        pujas.pujar(comprador=primero, subasta_id=self.subasta.pk, monto=1100)
        self.client.post(reverse("pujar", args=[self.subasta.pk]), {"monto": "1200"})
        self.assertTrue(primero.notificaciones.filter(tipo="MSG-36").exists())

    def test_ca_09_4_en_la_holandesa_se_acepta_el_precio_vigente(self):
        """CA-09.4 En la holandesa el comprador acepta el precio vigente y gana en el acto (MSG-15, S-01)."""
        holandesa = self.subasta_abierta(
            costo_salida=1000, tipo="HOLANDESA",
            holandesa_precio_inicial=2000, holandesa_decremento=100, holandesa_intervalo_min=30,
        )
        url = reverse("detalle_subasta", args=[holandesa.pk])
        detalle = self.client.get(url)
        self.assertContains(detalle, "Aceptar 2,000 fichas")
        self.assertContains(detalle, "Próxima bajada")
        self.client.post(reverse("aceptar_precio_holandesa", args=[holandesa.pk]))
        self.assertContains(self.client.get(url), "Ganaste")

    def test_ca_09_5_el_vendedor_no_puede_pujar_en_su_subasta(self):
        """CA-09.5 El vendedor ve su subasta sin opción de pujar (ERR-41, S-13)."""
        self.client.force_login(self.vendedor)
        self.assertContains(self.client.get(self.detalle), "no puedes pujar")

    def test_aceptar_en_la_holandesa_pasa_por_revisa_y_confirma(self):
        """Rediseño (fase C): «Aceptar» lleva a una confirmación que muestra el precio y no adjudica nada."""
        holandesa = self.subasta_abierta(
            costo_salida=1000, tipo="HOLANDESA",
            holandesa_precio_inicial=2000, holandesa_decremento=100, holandesa_intervalo_min=30,
        )
        confirmar = reverse("confirmar_aceptar_holandesa", args=[holandesa.pk])
        self.assertContains(self.client.get(reverse("detalle_subasta", args=[holandesa.pk])), confirmar)
        pantalla = self.client.get(confirmar)
        self.assertContains(pantalla, "Revisa y confirma")
        self.assertContains(pantalla, "Aceptar 2,000 fichas")
        self.assertContains(pantalla, reverse("aceptar_precio_holandesa", args=[holandesa.pk]))
        holandesa.refresh_from_db()
        self.assertFalse(hasattr(holandesa, "adjudicacion"))

    def test_rediseno_fase_f_errores_en_alert_y_ayuda_ligada_al_monto(self):
        """Rediseño (fase F) El error va en la lista role="alert" y el campo de monto apunta a su ayuda."""
        respuesta = self.client.post(reverse("pujar", args=[self.subasta.pk]), {"monto": "900"}, follow=True, **self.desde(self.detalle))
        html = respuesta.content.decode()
        alerta = html.split('role="alert"')[1].split("</ul>")[0]
        self.assertIn("ERR-06", alerta)
        self.assertIn('aria-describedby="error-monto ayuda-monto"', html)
        self.assertIn('id="ayuda-monto"', html)

    def test_rediseno_movil_la_puja_rechazada_conserva_el_monto_y_avisa_junto_al_campo(self):
        """Rediseño (móvil) Tras ERR-06 la ficha conserva el monto escrito y repite el error junto al campo."""
        respuesta = self.client.post(reverse("pujar", args=[self.subasta.pk]), {"monto": "900"}, **self.desde(self.detalle))
        self.assertEqual(respuesta.status_code, 200)
        html = respuesta.content.decode()
        self.assertIn('value="900"', html)
        self.assertIn('aria-invalid="true"', html)
        self.assertIn("ERR-06", html.split('id="error-monto"')[1].split("</ul>")[0])
        self.assertIn('action="%s#puja"' % reverse("pujar", args=[self.subasta.pk]), html)

    def test_rediseno_movil_un_monto_invalido_conserva_lo_escrito(self):
        """Rediseño (móvil) Un monto que no es entero se rechaza (ERR-13) sin borrar lo que se escribió."""
        respuesta = self.client.post(reverse("pujar", args=[self.subasta.pk]), {"monto": "12.5"}, **self.desde(self.detalle))
        self.assertContains(respuesta, "ERR-13")
        self.assertContains(respuesta, 'value="12.5"')
        self.assertContains(respuesta, 'id="error-monto"')
        self.assertFalse(Puja.objects.exists())

    def test_rediseno_fase_f_confirmacion_en_status(self):
        """Rediseño (fase F) La confirmación va en la lista role="status", no en la de errores."""
        respuesta = self.client.post(reverse("pujar", args=[self.subasta.pk]), {"monto": "1200"}, follow=True)
        html = respuesta.content.decode()
        self.assertIn("MSG-12", html.split('role="status"')[1].split("</ul>")[0])
        self.assertNotIn("MSG-12", html.split('role="alert"')[1].split("</ul>")[0])

    def test_s_32_un_monto_mayor_al_tope_se_rechaza_con_err_66(self):
        """S-32 Un monto que la base de datos no puede guardar se rechaza con ERR-66, no con un error del servidor."""
        respuesta = self.client.post(
            reverse("pujar", args=[self.subasta.pk]), {"monto": "99999999999999999999"}, follow=True
        )
        self.assertContains(respuesta, "ERR-66")
        self.assertContains(respuesta, "El monto no puede pasar de 2,147,483,647 fichas.")
        self.assertFalse(Puja.objects.exists())

    def test_s_32_con_la_oferta_en_el_tope_no_se_ofrece_pujar(self):
        """S-32 Con el precio en el tope la ficha lo dice y no ofrece un formulario que solo puede fallar."""
        tope = self.subasta_abierta(costo_salida=2_147_483_647)
        respuesta = self.client.get(reverse("detalle_subasta", args=[tope.pk]))
        self.assertContains(respuesta, "ya no se puede subir")
        self.assertNotContains(respuesta, 'id="puja"')

    def test_datos_extremos_la_ayuda_de_modificar_dice_el_minimo_con_separadores(self):
        """Datos extremos Al modificar su puja el comprador ve el mínimo con separadores de miles."""
        self.client.post(reverse("pujar", args=[self.subasta.pk]), {"monto": "1200"})
        self.assertContains(self.client.get(self.detalle), "Mínimo 1,201 fichas.")
