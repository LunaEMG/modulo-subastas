"""CU-08 Buscar subastas, filtrar y consultar el detalle (Comprador)."""
from django.urls import reverse

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

    def test_datos_extremos_una_sola_ficha_y_titulo_completo(self):
        """Datos extremos Un precio de 1 se lee «1 ficha»; la tarjeta guarda el título completo aunque lo corte a dos líneas."""
        self.subasta_abierta(costo_salida=1)
        respuesta = self.client.get(reverse("buscar_subastas"))
        self.assertContains(respuesta, '1 <span class="unidad">ficha</span>')
        self.assertContains(respuesta, 'title="Reloj de prueba"')

    def test_datos_extremos_galeria_con_foto_principal_y_miniaturas(self):
        """Datos extremos La ficha muestra la primera foto grande y las demás como miniaturas que abren la imagen completa."""
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

    def test_rediseno_fase_f_tarjetas_con_h2_imagenes_diferidas_y_pagina_actual(self):
        """Rediseño (fase F) Títulos de tarjeta en h2, portadas con tamaño y carga diferida, y menú con la página actual."""
        respuesta = self.client.get(reverse("buscar_subastas"))
        self.assertContains(respuesta, '<h2 class="titulo-tarjeta">Reloj de prueba</h2>', html=False)
        self.assertContains(respuesta, 'fetchpriority="high"', count=1)
        self.assertContains(respuesta, 'width="400" height="300"')
        self.assertContains(respuesta, 'aria-current="page"', count=1)
        self.assertContains(respuesta, 'href="#contenido"')
        self.assertContains(respuesta, 'id="contenido"')
        detalle = self.client.get(reverse("detalle_subasta", args=[self.subasta.pk]))
        self.assertContains(detalle, 'aria-current="true"', count=1)

    def test_rediseno_movil_solo_la_primera_portada_carga_de_inmediato(self):
        """Rediseño (móvil) La primera portada se pide con prioridad; las siguientes esperan a acercarse."""
        self.subasta_abierta()
        respuesta = self.client.get(reverse("buscar_subastas"))
        self.assertContains(respuesta, 'fetchpriority="high"', count=1)
        self.assertContains(respuesta, 'loading="lazy"', count=1)

    def test_rediseno_movil_la_busqueda_usa_el_teclado_de_buscar(self):
        """Rediseño (móvil) El campo de búsqueda es type="search" y la tecla Intro dice «Buscar»."""
        respuesta = self.client.get(reverse("buscar_subastas"))
        self.assertContains(respuesta, 'type="search"')
        self.assertContains(respuesta, 'enterkeyhint="search"')
