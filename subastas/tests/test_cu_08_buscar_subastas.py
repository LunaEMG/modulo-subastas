"""CU-08 Buscar subastas, filtrar y consultar el detalle (Comprador)."""
from django.urls import reverse

from subastas import reloj
from subastas.servicios import pujas

from .base import PruebaSubastas, fotografia


class CU08BuscarSubastas(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(costo_salida=1000, tipo="COMPRA_INMEDIATA", precio_compra_inmediata=5000)
        self.client.force_login(self.crear_comprador())

    def test_ca_08_1_se_listan_y_filtran_las_subastas_abiertas(self):
        """CA-08.1 La búsqueda lista las subastas abiertas y filtra por texto, categoría y tipo."""
        buscar = reverse("buscar_subastas")
        self.assertContains(self.client.get(buscar), "Reloj de prueba")
        self.assertContains(self.client.get(buscar, {"texto": "reloj"}), "Reloj de prueba")
        self.assertNotContains(self.client.get(buscar, {"categoria": "Videojuegos"}), "Reloj de prueba")
        self.assertNotContains(self.client.get(buscar, {"tipo": "HOLANDESA"}), "Reloj de prueba")

    def test_rnf_02_una_sola_ficha_y_titulo_completo(self):
        """RNF-02 Un precio de 1 se lee «1 ficha»; la tarjeta guarda el título completo aunque lo corte a dos líneas."""
        self.subasta_abierta(costo_salida=1)
        respuesta = self.client.get(reverse("buscar_subastas"))
        self.assertContains(respuesta, '1 <span class="unidad">ficha</span>')
        self.assertContains(respuesta, 'title="Reloj de prueba"')

    def test_rnf_02_galeria_con_foto_principal_y_miniaturas(self):
        """RNF-02 La ficha muestra la primera foto grande y las demás como miniaturas que abren la imagen completa."""
        articulo = self.articulo_listo(fotografias=[fotografia(), fotografia(), fotografia()])
        subasta = self.publicar(articulo, self.proponer(articulo))
        html = self.client.get(reverse("detalle_subasta", args=[subasta.pk])).content.decode()
        self.assertEqual(html.count('class="galeria-principal"'), 1)
        miniaturas = html.split('class="galeria-miniaturas"')[1].split("</div>")[0]
        self.assertEqual(miniaturas.count('target="_blank"'), 2)
        self.assertIn('alt="Fotografía 3 de Reloj de prueba"', miniaturas)

    def test_ca_08_2_las_subastas_vencidas_no_aparecen(self):
        """CA-08.2 Una subasta cuya fecha de cierre ya pasó no aparece en la búsqueda."""
        self.reloj.avanzar(hours=25)
        self.assertNotContains(self.client.get(reverse("buscar_subastas")), "Reloj de prueba")

    def test_ca_08_3_el_detalle_muestra_precio_actual_y_puja_minima(self):
        """CA-08.3 El detalle muestra la puja mínima aceptada y la opción de comprar ya."""
        detalle = self.client.get(reverse("detalle_subasta", args=[self.subasta.pk]))
        self.assertContains(detalle, "Mínimo 1,001 fichas")
        self.assertContains(detalle, "Comprar ya por 5,000")

    def test_rnf_02_tarjetas_con_h2_imagenes_diferidas_y_pagina_actual(self):
        """RNF-02 Títulos de tarjeta en h2, portadas con tamaño y carga diferida, y menú con la página actual."""
        respuesta = self.client.get(reverse("buscar_subastas"))
        self.assertContains(respuesta, '<h2 class="titulo-tarjeta">Reloj de prueba</h2>', html=False)
        self.assertContains(respuesta, 'fetchpriority="high"', count=1)
        self.assertContains(respuesta, 'width="400" height="300"')
        self.assertContains(respuesta, 'aria-current="page"', count=1)
        self.assertContains(respuesta, 'href="#contenido"')
        self.assertContains(respuesta, 'id="contenido"')
        detalle = self.client.get(reverse("detalle_subasta", args=[self.subasta.pk]))
        self.assertContains(detalle, 'aria-current="true"', count=1)

    def test_rnf_02_solo_la_primera_portada_carga_de_inmediato(self):
        """RNF-02 La primera portada se pide con prioridad; las siguientes esperan a acercarse."""
        self.subasta_abierta()
        respuesta = self.client.get(reverse("buscar_subastas"))
        self.assertContains(respuesta, 'fetchpriority="high"', count=1)
        self.assertContains(respuesta, 'loading="lazy"', count=1)

    def test_rnf_02_la_busqueda_usa_el_teclado_de_buscar(self):
        """RNF-02 El campo de búsqueda es type="search" y la tecla Intro dice «Buscar»."""
        respuesta = self.client.get(reverse("buscar_subastas"))
        self.assertContains(respuesta, 'type="search"')
        self.assertContains(respuesta, 'enterkeyhint="search"')

    def test_rnf_02_la_tarjeta_lleva_el_color_y_la_placa_de_su_categoria(self):
        """RNF-02 Cada tarjeta lleva la clase de su categoría (cat-<nombre>) y la categoría en una placa sobre la foto."""
        respuesta = self.client.get(reverse("buscar_subastas"))
        self.assertContains(respuesta, "cat-relojes")
        self.assertContains(
            respuesta,
            '<span class="chip-categoria" style="--icono: url(\'/static/subastas/iconos/watch.svg\')">Relojes</span>',
            html=False,
        )

    def test_rnf_02_la_barra_dice_cuantos_resultados_hay(self):
        """RNF-02 La barra de resultados dice cuántas subastas encontró la búsqueda, en singular o plural."""
        buscar = reverse("buscar_subastas")
        self.assertContains(self.client.get(buscar), '<p class="total">1 resultado</p>', html=False)
        self.subasta_abierta()
        self.assertContains(self.client.get(buscar), '<p class="total">2 resultados</p>', html=False)
        self.assertContains(self.client.get(buscar, {"tipo": "HOLANDESA"}), '<p class="total">0 resultados</p>', html=False)

    def test_rnf_02_la_tarjeta_dice_el_tiempo_restante_y_guarda_la_fecha_completa(self):
        """RNF-02 La tarjeta muestra «quedan…» y conserva la fecha completa de cierre en su title."""
        respuesta = self.client.get(reverse("buscar_subastas")).content.decode()
        self.assertIn(">quedan 1 d 0 h</time>", respuesta)
        cierre = self.subasta.fecha_cierre
        self.assertIn(f'title="cierra {reloj.formato(cierre)}"', respuesta)
        self.assertNotIn('class="tiempo urgente"', respuesta)

    def test_rnf_02_con_menos_de_un_dia_el_tiempo_se_marca_urgente(self):
        """RNF-02 Cuando falta menos de un día para el cierre, el tiempo restante se marca como urgente."""
        self.reloj.avanzar(hours=2)
        respuesta = self.client.get(reverse("buscar_subastas"))
        self.assertContains(respuesta, 'class="tiempo urgente"', count=1)
        self.assertContains(respuesta, ">quedan 22 h 0 min</time>", html=False)

    def test_s_36_el_detalle_solo_muestra_subastas_abiertas_o_propias(self):
        """S-36 Una subasta sin publicar o un id inexistente responden 404. Cerrada, la siguen viendo
        quien pujó, el ganador y el vendedor, pero no otro comprador."""
        articulo = self.articulo_listo()
        propuesta = self.proponer(articulo)
        self.assertEqual(self.client.get(reverse("detalle_subasta", args=[propuesta.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("detalle_subasta", args=[999999])).status_code, 404)

        comprador = self.crear_comprador()
        pujas.pujar(comprador=comprador, subasta_id=self.subasta.pk, monto=1500)
        self.reloj.avanzar(hours=25)
        self.client.get(reverse("inicio"))  # El actor Tiempo cierra la subasta.
        detalle = reverse("detalle_subasta", args=[self.subasta.pk])
        self.assertEqual(self.client.get(detalle).status_code, 404)
        self.client.force_login(comprador)
        self.assertContains(self.client.get(reverse("historial")), detalle)
        self.assertEqual(self.client.get(detalle).status_code, 200)
        self.client.force_login(self.vendedor)
        self.assertEqual(self.client.get(detalle).status_code, 200)
