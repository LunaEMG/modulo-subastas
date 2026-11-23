"""RNF-02 Presentación: el tiempo restante se calcula en la plantilla desde la fecha de cierre que ya existe."""
import os
import re
from html import unescape
from datetime import timedelta
from unittest import mock
from urllib.parse import parse_qs, quote

from django.contrib.staticfiles import finders
from django.template import Context, Template
from django.test import Client, RequestFactory, override_settings
from django.urls import reverse
from django.utils.text import slugify
from django.views.defaults import server_error

from subastas import reloj, subastas_tipos as tipos
from subastas.models import Categoria
from subastas.reglas.dinero import FICHAS_POR_PESO
from subastas.reglas.pagos import DIAS_PARA_PAGAR

from .base import CONTRASENA, INICIO, PruebaSubastas

PLANTILLA = Template(
    "{% load presentacion %}{{ f|tiempo_restante }}|{{ f|es_urgente|yesno:'urgente,normal' }}|{{ f|fecha_completa }}"
)


def pintar(fecha):
    return PLANTILLA.render(Context({"f": fecha})).split("|")


class RNF02TiempoRestante(PruebaSubastas):
    def test_rnf_02_con_mas_de_un_dia_dice_dias_y_horas(self):
        """RNF-02 Con 2 días y 4 horas por delante se lee «quedan 2 d 4 h» y no es urgente."""
        texto, urgencia, _ = pintar(INICIO + timedelta(days=2, hours=4, minutes=30))
        self.assertEqual(texto, "quedan 2 d 4 h")
        self.assertEqual(urgencia, "normal")

    def test_rnf_02_con_menos_de_un_dia_dice_horas_y_minutos_y_es_urgente(self):
        """RNF-02 Con menos de un día se lee «quedan 5 h 10 min» y se marca como urgente."""
        texto, urgencia, _ = pintar(INICIO + timedelta(hours=5, minutes=10))
        self.assertEqual(texto, "quedan 5 h 10 min")
        self.assertEqual(urgencia, "urgente")

    def test_rnf_02_con_menos_de_una_hora_dice_minutos(self):
        """RNF-02 Con 12 minutos por delante se lee «quedan 12 min»."""
        self.assertEqual(pintar(INICIO + timedelta(minutes=12, seconds=40))[0], "quedan 12 min")

    def test_rnf_02_sin_fecha_de_cierre_no_muestra_nada(self):
        """RNF-02 Sin fecha de cierre (por ejemplo, en la holandesa) no se muestra tiempo ni urgencia."""
        self.assertEqual(pintar(None), ["", "normal", ""])

    def test_rnf_02_una_fecha_vencida_no_muestra_tiempo(self):
        """RNF-02 Si la fecha de cierre ya pasó no se muestra tiempo restante."""
        texto, urgencia, _ = pintar(INICIO - timedelta(minutes=1))
        self.assertEqual((texto, urgencia), ("", "normal"))

    def test_rnf_02_sigue_al_reloj_del_sistema(self):
        """RNF-02 El cálculo usa reloj.ahora(): al adelantar el reloj, el tiempo restante baja."""
        cierre = INICIO + timedelta(days=1, hours=2)
        self.assertEqual(pintar(cierre)[0], "quedan 1 d 2 h")
        self.reloj.avanzar(hours=3)
        self.assertEqual(pintar(cierre)[:2], ["quedan 23 h 0 min", "urgente"])

    def test_rnf_02_la_fecha_completa_usa_el_formato_del_modulo(self):
        """RNF-02 La fecha completa se escribe dd/mm/AAAA HH:MM en hora local."""
        self.assertRegex(pintar(INICIO + timedelta(days=1))[2], r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}$")


# Enlace y nombre de cada tarjeta de categoría de la portada.
TARJETA_CATEGORIA = r'<a class="tarjeta-categoria[^"]*" href="([^"]+)">.*?<span class="nombre-categoria">([^<]+)</span>'


def clases_de_botones(html):
    """Las listas de clases de cada elemento que es un botón (class="boton …")."""
    return [clases.split() for clases in re.findall(r'class="(boton(?: [^"]*)?)"', html)]


def botones_principales(html):
    """Los botones en oro: los que no son secundarios, de peligro, discretos ni de texto."""
    variantes = {"secundario", "peligro", "discreto", "boton-texto"}
    return [c for c in clases_de_botones(html) if not variantes & set(c)]


class RNF02FichaDeSubasta(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.subasta = self.subasta_abierta(costo_salida=1000, tipo="COMPRA_INMEDIATA", precio_compra_inmediata=5000)
        self.comprador = self.crear_comprador()
        self.client.force_login(self.comprador)
        self.detalle = reverse("detalle_subasta", args=[self.subasta.pk])

    def ficha(self):
        return self.client.get(self.detalle).content.decode()

    def test_rnf_02_la_ficha_muestra_el_tiempo_restante_y_la_fecha_de_cierre(self):
        """RNF-02 La ficha muestra «quedan…» junto al precio y, además, la fecha completa de cierre."""
        html = self.ficha()
        self.assertIn(">quedan 1 d 0 h</time>", html)
        self.assertIn(f"<dt>Cierre</dt><dd>{reloj.formato(self.subasta.fecha_cierre)}</dd>", html)

    def test_rnf_02_hay_una_sola_accion_principal(self):
        """RNF-02 La ficha tiene una sola acción principal en oro; «Comprar ya» va como secundaria."""
        html = self.ficha()
        self.assertEqual(botones_principales(html), [["boton"]])
        self.assertIn('class="boton secundario boton-ancho-sec"', html)

    def test_rnf_02_si_va_ganando_la_franja_es_de_oro(self):
        """RNF-02 Con una puja que va ganando, «Tu puja» aparece en la franja oro de situación."""
        self.client.post(reverse("pujar", args=[self.subasta.pk]), {"monto": "1200"})
        html = self.ficha()
        self.assertIn('class="mi-situacion situacion-ganando"', html)
        self.assertNotIn("situacion-superado", html)
        self.assertEqual(len(botones_principales(html)), 1)

    def test_rnf_02_si_lo_superaron_la_franja_es_la_mas_fuerte(self):
        """RNF-02 Si otro comprador lo supera, «Tu puja» aparece en la franja tinta de situación."""
        self.client.post(reverse("pujar", args=[self.subasta.pk]), {"monto": "1200"})
        self.client.force_login(self.crear_comprador())
        self.client.post(reverse("pujar", args=[self.subasta.pk]), {"monto": "1500"})
        self.client.force_login(self.comprador)
        html = self.ficha()
        self.assertIn('class="mi-situacion situacion-superado"', html)
        self.assertIn("Te superaron", html)

    def test_rnf_02_retirar_mi_puja_es_un_boton_de_texto(self):
        """RNF-02 «Retirar mi puja» es una acción de bajo peso: botón de texto (con 44 px de área táctil por CSS)."""
        self.client.post(reverse("pujar", args=[self.subasta.pk]), {"monto": "1200"})
        self.assertIn('<button class="boton boton-texto" type="submit">Retirar mi puja</button>', self.ficha())

    def test_rnf_02_al_ganar_el_precio_final_va_en_franja_oro(self):
        """RNF-02 Cuando el comprador gana, «Precio final» y «Ganaste» aparecen en la franja oro sólida."""
        self.client.post(reverse("comprar_de_inmediato", args=[self.subasta.pk]))
        html = self.ficha()
        self.assertIn('class="mi-situacion situacion-ganaste"', html)
        self.assertIn("Ganaste", html)
        self.assertNotIn("</time>", html)


class RNF02Portada(PruebaSubastas):
    def test_rnf_02_sin_sesion_el_oro_es_crear_cuenta_y_explorar_subastas(self):
        """RNF-02 Sin sesión, el oro es «Crear cuenta» en el encabezado y «Explorar subastas» en el hero, que pasa por Entrar y vuelve al listado; «Cómo funciona» es secundaria y baja a su sección."""
        html = self.client.get(reverse("inicio")).content.decode()
        self.assertEqual(botones_principales(html), [["boton", "boton-registro"], ["boton"]])
        self.assertIn('<a class="boton boton-registro" href="{}">Crear cuenta</a>'.format(reverse("registro")), html)
        explorar = re.search(r'<a class="boton" href="([^"]+)">Explorar subastas</a>', html)
        ruta, consulta = explorar.group(1).split("?", 1)
        self.assertEqual(ruta, reverse("entrar"))
        self.assertEqual(parse_qs(consulta)["next"], [reverse("buscar_subastas")])
        self.assertIn('<a class="boton secundario" href="#como-funciona">Cómo funciona</a>', html)
        self.assertIn('id="como-funciona"', html)

    def test_rnf_02_con_sesion_cada_rol_es_una_tarjeta(self):
        """RNF-02 Con sesión, la portada muestra una tarjeta por cada lugar al que puede ir el usuario; el único botón en oro es «Buscar»."""
        self.client.force_login(self.crear_comprador())
        html = self.client.get(reverse("inicio")).content.decode()
        self.assertEqual(html.count('class="tarjeta tarjeta-enlace tarjeta-rol"'), 2)
        self.assertEqual(botones_principales(html), [["boton", "boton-buscar"]])

    def test_rnf_02_sin_sesion_no_aparece_ninguna_subasta(self):
        """RNF-02 Sin sesión, la portada no muestra subastas aunque haya alguna abierta: ni su título, ni su precio, ni un enlace a su ficha."""
        subasta = self.subasta_abierta()
        html = self.client.get(reverse("inicio")).content.decode()
        self.assertNotIn(subasta.articulo.titulo, html)
        self.assertNotIn(reverse("detalle_subasta", args=[subasta.pk]), html)
        self.assertNotIn("tarjeta-subasta", html)
        self.assertNotIn('class="precio"', html)

    def test_rnf_02_sin_sesion_cada_categoria_lleva_a_entrar_y_vuelve_al_listado_filtrado(self):
        """RNF-02 Sin sesión, cada categoría es una tarjeta que lleva a Entrar y, tras el código, al listado con su filtro."""
        html = self.client.get(reverse("inicio")).content.decode()
        destinos = re.findall(TARJETA_CATEGORIA, html)
        self.assertEqual(len(destinos), Categoria.objects.count())
        for href, nombre in destinos:
            ruta, consulta = href.split("?", 1)
            self.assertEqual(ruta, reverse("entrar"))
            self.assertEqual(parse_qs(consulta)["next"], [reverse("buscar_subastas") + "?categoria=" + quote(nombre)])

    def test_rnf_02_con_sesion_los_accesos_por_categoria_apuntan_al_buscador_con_su_filtro(self):
        """RNF-02 Con sesión, hay un acceso por categoría que abre el buscador con esa categoría ya filtrada (CU-08)."""
        self.client.force_login(self.crear_comprador())
        html = self.client.get(reverse("inicio")).content.decode()
        enlaces = [href for href, _ in re.findall(TARJETA_CATEGORIA, html)]
        self.assertEqual(len(enlaces), Categoria.objects.count())
        filtradas = set()
        for href in enlaces:
            self.assertTrue(href.startswith(reverse("buscar_subastas") + "?categoria="))
            formulario = self.client.get(href).context["formulario"]
            self.assertTrue(formulario.is_valid())
            filtradas.add(formulario.cleaned_data["categoria"].nombre)
        self.assertEqual(filtradas, set(Categoria.objects.values_list("nombre", flat=True)))

    def test_rnf_02_con_sesion_la_pildora_envia_el_texto_al_buscador(self):
        """RNF-02 Con sesión, la píldora de búsqueda envía «texto» por GET al buscador existente."""
        self.client.force_login(self.crear_comprador())
        html = self.client.get(reverse("inicio")).content.decode()
        formulario = html.split('<form class="buscador-inicio"')[1].split("</form>")[0]
        self.assertIn('method="get" action="{}"'.format(reverse("buscar_subastas")), formulario)
        self.assertIn('name="texto"', formulario)

    def test_rnf_02_los_tipos_de_la_portada_son_los_del_sistema(self):
        """RNF-02 Sin sesión, cada tipo de subasta aparece en una línea con el nombre y la descripción que usa el sistema."""
        html = self.client.get(reverse("inicio")).content.decode()
        self.assertEqual(html.count("<div><dt>"), len(tipos.todos()))
        for tipo in tipos.todos():
            self.assertIn("<dt>{}</dt><dd>{}</dd>".format(tipo.nombre, tipo.descripcion), html)

    def test_rnf_02_como_funciona_coincide_con_las_reglas(self):
        """RNF-02 «Cómo funciona» usa los valores de las reglas: residencia en México (RN-15), fichas (RN-13) y días para pagar (RN-11)."""
        html = self.client.get(reverse("inicio")).content.decode()
        self.assertIn("con tu código postal en México", html)
        self.assertIn("1 ficha equivale a {} peso".format(FICHAS_POR_PESO), html)
        self.assertIn("tienes {} días para pagar".format(DIAS_PARA_PAGAR), html)

    def test_rnf_02_la_hoja_de_estilos_lleva_su_version(self):
        """RNF-02 La hoja de estilos se enlaza con su fecha de modificación, para que el navegador no use una versión vieja tras un cambio."""
        html = self.client.get(reverse("inicio")).content.decode()
        version = int(os.path.getmtime(finders.find("subastas/estilos.css")))
        self.assertIn('href="/static/subastas/estilos.css?v={}"'.format(version), html)

    def test_rnf_02_la_portada_usa_tarjetas_con_foto_y_no_chips(self):
        """RNF-02 Con y sin sesión, la portada muestra una tarjeta con la foto real (.jpg) de cada categoría; los chips solo van en el listado."""
        anonimo = self.client.get(reverse("inicio")).content.decode()
        self.client.force_login(self.crear_comprador())
        con_sesion = self.client.get(reverse("inicio")).content.decode()
        for html in (anonimo, con_sesion):
            self.assertNotIn("acceso-categoria", html)
            self.assertNotIn(".webp", html)
            for nombre in Categoria.objects.values_list("nombre", flat=True):
                foto = "/static/subastas/categorias/{}.jpg".format(slugify(nombre))
                self.assertRegex(html, r'<a class="tarjeta-categoria cat-{}" href="[^"]+"><img src="{}" alt=""'.format(slugify(nombre), re.escape(foto)))

class RNF02PantallasDeTrabajo(PruebaSubastas):
    def setUp(self):
        super().setUp()
        self.articulo = self.registrar_articulo()

    def test_rnf_02_la_bandeja_del_gestor_es_una_tabla_que_se_apila_en_el_telefono(self):
        """RNF-02 La bandeja del gestor muestra cada lista en una tabla sobre su superficie, con cifras a la derecha y etiquetas para apilarse en el teléfono."""
        self.client.force_login(self.gestor)
        html = self.client.get(reverse("gestor_bandeja")).content.decode()
        self.assertIn('<div class="tarjeta tabla-caja">', html)
        self.assertIn('<table class="apilada">', html)
        self.assertIn('<td class="numero" data-etiqueta="Costo de salida">', html)

    def test_rnf_02_en_la_moderacion_el_estado_va_en_sello_tambien_en_el_telefono(self):
        """RNF-02 En la moderación, el estado del artículo va en un sello en su columna y, en el teléfono, junto al título."""
        self.client.force_login(self.crear_moderador())
        html = self.client.get(reverse("moderador_bandeja")).content.decode()
        fila = html.split('<td class="celda-principal">')[1].split("</tr>")[0]
        self.assertIn('<div class="solo-movil"><span class="sello', fila)
        self.assertIn('<td class="col-estado"><span class="sello', fila)

    def test_rnf_02_el_regreso_a_la_bandeja_es_un_enlace_de_migas(self):
        """RNF-02 El enlace para volver a la bandeja lleva la clase de migas (área táctil de 44 px por CSS)."""
        self.client.force_login(self.gestor)
        html = self.client.get(reverse("gestor_articulo", args=[self.articulo.pk])).content.decode()
        self.assertIn('<p class="migas"><a href="{}">← Pendientes</a></p>'.format(reverse("gestor_bandeja")), html)


def hoja_de_estilos():
    with open(finders.find("subastas/estilos.css"), encoding="utf-8") as archivo:
        return archivo.read()


class RNF02Iconos(PruebaSubastas):
    """Íconos Lucide (ISC): archivos del proyecto, un tamaño único y siempre junto a una palabra."""

    def test_rnf_02_cada_icono_de_la_hoja_es_un_archivo_del_proyecto_con_su_licencia(self):
        """RNF-02 Cada ícono que usa la hoja de estilos existe en iconos/ y la licencia de Lucide va con ellos."""
        from subastas.templatetags.presentacion import ICONO_GENERICO, ICONOS_CATEGORIA

        nombres = set(re.findall(r'url\("iconos/([a-z0-9-]+)\.svg"\)', hoja_de_estilos()))
        nombres |= {*ICONOS_CATEGORIA.values(), ICONO_GENERICO}  # Los de categoría van en la plantilla.
        self.assertGreaterEqual(len(nombres), 30)
        for nombre in nombres:
            self.assertIsNotNone(finders.find(f"subastas/iconos/{nombre}.svg"), nombre)
        self.assertIsNotNone(finders.find("subastas/iconos/LICENCIA-Lucide.txt"))

    def test_rnf_02_los_iconos_tienen_un_solo_trazo_y_nada_ejecutable(self):
        """RNF-02 Todos los SVG tienen la misma rejilla (24) y el mismo trazo (2), sin scripts ni enlaces."""
        carpeta = os.path.dirname(finders.find("subastas/iconos/LICENCIA-Lucide.txt"))
        for archivo in (a for a in os.listdir(carpeta) if a.endswith(".svg")):
            with open(os.path.join(carpeta, archivo), encoding="utf-8") as f:
                svg = f.read()
            self.assertIn('viewBox="0 0 24 24"', svg, archivo)
            self.assertIn('stroke-width="2"', svg, archivo)
            self.assertNotRegex(svg, r"<script|href|\son[a-z]+=", archivo)

    def test_rnf_02_el_tamano_es_una_sola_variable_y_no_quedan_iconos_dibujados(self):
        """RNF-02 El tamaño de los íconos se define una vez (--icono-tamano) y ya no hay íconos dibujados en la hoja."""
        css = hoja_de_estilos()
        self.assertEqual(len(re.findall(r"--icono-tamano:", css)), 1)
        self.assertNotIn("data:image/svg", css)

    def test_rnf_02_el_menu_lleva_el_icono_de_cada_destino(self):
        """RNF-02 Cada enlace del menú lleva la clase de su ícono: sin sesión Entrar y Crear cuenta (en la portada, Entrar y el botón «Crear cuenta»); con sesión los de su rol."""
        html = self.client.get(reverse("entrar")).content.decode()
        self.assertIn('class="ir-entrar" href="{}"'.format(reverse("entrar")), html)
        self.assertIn('class="ir-registro" href="{}"'.format(reverse("registro")), html)
        html = self.client.get(reverse("inicio")).content.decode()
        self.assertIn('class="ir-entrar" href="{}"'.format(reverse("entrar")), html)
        self.client.force_login(self.crear_comprador())
        html = self.client.get(reverse("inicio")).content.decode()
        for clase, destino in [("ir-subastas", "buscar_subastas"), ("ir-historial", "historial"), ("ir-avisos", "avisos")]:
            self.assertIn('class="{}" href="{}"'.format(clase, reverse(destino)), html)

    def test_rnf_02_la_tarjeta_aparta_el_numero_de_pujas_para_su_icono(self):
        """RNF-02 En la tarjeta del listado, «N pujas» va en su propio elemento para llevar el ícono de puja."""
        self.subasta_abierta()
        self.client.force_login(self.crear_comprador())
        html = self.client.get(reverse("buscar_subastas")).content.decode()
        self.assertIn('<span class="pujas">0 pujas</span>', html)

    def test_rnf_02_los_estados_vacios_llevan_su_icono(self):
        """RNF-02 Búsqueda sin resultados y avisos vacíos llevan su propio ícono; las demás listas, el de lista vacía."""
        self.client.force_login(self.crear_comprador())
        html = self.client.get(reverse("buscar_subastas")).content.decode()
        self.assertIn('<p class="vacio vacio-busqueda">', html)
        html = self.client.get(reverse("avisos")).content.decode()
        self.assertIn('<p class="vacio vacio-avisos">No tienes avisos.</p>', html)
        css = hoja_de_estilos()
        self.assertRegex(css, r"\.vacio-busqueda \{ --icono: var\(--i-search-x\); \}")
        self.assertRegex(css, r"\.vacio-avisos \{ --icono: var\(--i-bell-off\); \}")


class RNF02FotosDeDemostracion(PruebaSubastas):
    """Los artículos [Demo] usan fotos reales reducidas; la ilustración queda de respaldo."""

    def setUp(self):
        super().setUp()
        import tempfile
        from pathlib import Path

        from django.test import override_settings

        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        ajustes = override_settings(
            MEDIA_ROOT=carpeta.name, BANDEJA_SIMULADA=Path(carpeta.name) / "bandeja.jsonl"
        )
        ajustes.enable()
        self.addCleanup(ajustes.disable)

    def _cargar(self, *argumentos):
        from io import StringIO

        from django.core.management import call_command

        from subastas import integraciones

        integraciones.restaurar()
        reloj.establecer_reloj(None)
        salida = StringIO()
        call_command("cargar_datos_prueba", *argumentos, stdout=salida)
        return salida.getvalue()

    def test_rnf_02_cada_foto_existe_mide_800_px_y_respeta_los_limites(self):
        """RNF-02 Cada foto listada es un JPEG de 800 px de ancho, sin EXIF, y cabe en los límites del formulario."""
        from PIL import Image

        from subastas.forms.articulos import MAXIMO_FOTOGRAFIAS, TAMANO_MAXIMO_MB
        from subastas.management.commands.cargar_datos_prueba import FOTOS_DEMO, FOTOS_POR_ARTICULO

        for titulo, nombres in FOTOS_POR_ARTICULO.items():
            self.assertLessEqual(len(nombres), MAXIMO_FOTOGRAFIAS, titulo)
            for nombre in nombres:
                ruta = FOTOS_DEMO / nombre
                self.assertTrue(ruta.is_file(), nombre)
                self.assertLess(ruta.stat().st_size, TAMANO_MAXIMO_MB * 1024 * 1024, nombre)
                with Image.open(ruta) as imagen:
                    self.assertEqual((imagen.format, imagen.width), ("JPEG", 800), nombre)
                    self.assertFalse(imagen.getexif(), nombre)
        en_carpeta = {ruta.name for ruta in FOTOS_DEMO.glob("*.jpg")}
        listadas = {nombre for nombres in FOTOS_POR_ARTICULO.values() for nombre in nombres}
        self.assertEqual(en_carpeta, listadas)

    def test_rnf_02_creditos_lista_autor_enlace_y_licencia_de_cada_foto(self):
        """RNF-02 CREDITOS.md tiene una fila por foto con su enlace a Pexels o Unsplash y la licencia."""
        from subastas.management.commands.cargar_datos_prueba import FOTOS_DEMO, FOTOS_POR_ARTICULO

        filas = {
            fila.split("|")[1].strip(" `"): fila
            for fila in (FOTOS_DEMO / "CREDITOS.md").read_text(encoding="utf-8").splitlines()
            if fila.startswith("| `")
        }
        for nombres in FOTOS_POR_ARTICULO.values():
            for nombre in nombres:
                celdas = [celda.strip() for celda in filas[nombre].strip("|").split("|")]
                self.assertEqual(len(celdas), 5, nombre)
                self.assertTrue(celdas[2], nombre)  # Autor
                self.assertRegex(celdas[3], r"^https://(www\.pexels\.com|unsplash\.com)/", nombre)
                self.assertRegex(celdas[4], r"(Pexels|Unsplash) License", nombre)

    def test_rnf_02_cada_articulo_de_demo_tiene_sus_fotos_y_las_galerias_varias(self):
        """RNF-02 Los diez artículos [Demo] usan sus fotos reales, en orden; moto y cronógrafo traen tres."""
        from pathlib import Path

        from subastas.management.commands.cargar_datos_prueba import FOTOS_POR_ARTICULO, PREFIJO
        from subastas.models import Articulo

        self._cargar()
        articulos = Articulo.objects.filter(titulo__startswith=PREFIJO)
        self.assertEqual(articulos.count(), len(FOTOS_POR_ARTICULO))
        for articulo in articulos:
            esperadas = FOTOS_POR_ARTICULO[articulo.titulo.removeprefix(PREFIJO).strip()]
            guardadas = [Path(foto.archivo.name).name for foto in articulo.fotografias_visibles]
            self.assertEqual(len(guardadas), len(esperadas), articulo.titulo)
            for guardada, esperada in zip(guardadas, esperadas):
                self.assertTrue(guardada.startswith(Path(esperada).stem), (guardada, esperada))
        self.assertEqual(
            sorted(len(n) for n in FOTOS_POR_ARTICULO.values() if len(n) > 1), [3, 3]
        )

    def test_rnf_02_si_falta_una_foto_se_usa_la_ilustracion(self):
        """RNF-02 Sin la carpeta de fotos, cada artículo recibe su ilustración de 640 × 480."""
        import tempfile
        from pathlib import Path
        from unittest import mock

        from PIL import Image

        from subastas.models import Fotografia

        with tempfile.TemporaryDirectory() as vacia, mock.patch(
            "subastas.management.commands.cargar_datos_prueba.FOTOS_DEMO", Path(vacia)
        ):
            self._cargar()
        self.assertEqual(Fotografia.objects.count(), 10)
        for foto in Fotografia.objects.all():
            with foto.archivo.open("rb") as archivo, Image.open(archivo) as imagen:
                self.assertEqual((imagen.format, imagen.size), ("PNG", (640, 480)))

    def test_rnf_02_redibujar_no_toca_las_fotos_reales(self):
        """RNF-02 --redibujar solo sobrescribe ilustraciones: con fotos reales no cambia ningún archivo."""
        from subastas.models import Fotografia

        self._cargar()
        antes = {foto.pk: foto.archivo.read() for foto in Fotografia.objects.all()}
        self.assertIn("Fotografías redibujadas: 0", self._cargar("--redibujar"))
        despues = {foto.pk: foto.archivo.read() for foto in Fotografia.objects.all()}
        self.assertEqual(antes, despues)

    def test_rnf_02_la_portada_de_la_tarjeta_recorta_las_fotos_verticales(self):
        """RNF-02 Una foto vertical no estira la tarjeta: la portada fija su proporción y recorta."""
        self.assertRegex(
            hoja_de_estilos(), r"\.tarjeta-subasta \.portada \{[^}]*aspect-ratio: 1; overflow: hidden;"
        )

    def test_rnf_02_compra_inmediata_recuerda_los_dias_para_pagar(self):
        """RNF-02 La descripción de compra inmediata dice que quien la acepta tiene los días de RN-11 para pagar."""
        self.assertIn(
            "tiene {} días para pagarla".format(DIAS_PARA_PAGAR),
            tipos.obtener("COMPRA_INMEDIATA").descripcion,
        )

    def test_rnf_02_el_sello_de_las_cifras_se_parte_antes_de_salirse(self):
        """RNF-02 «Aún no se alcanza» puede partirse dentro de su columna de cifras en vez de tocar el borde."""
        self.assertRegex(
            hoja_de_estilos(), r"\.cifras dd \.sello \{ white-space: normal; max-width: 100%;"
        )


class RNF02ChipsDeCategoria(PruebaSubastas):
    """Un solo mapeo categoría → ícono (presentacion.ICONOS_CATEGORIA) con ícono genérico de respaldo."""

    def test_rnf_02_cada_icono_del_mapeo_existe(self):
        """RNF-02 Los íconos del mapeo y el genérico (tag) son archivos de iconos/."""
        from subastas.templatetags.presentacion import ICONO_GENERICO, ICONOS_CATEGORIA

        for nombre in [*ICONOS_CATEGORIA.values(), ICONO_GENERICO]:
            self.assertIsNotNone(finders.find(f"subastas/iconos/{nombre}.svg"), nombre)

    def test_rnf_02_cada_foto_del_mapeo_existe_junto_a_los_iconos(self):
        """RNF-02 Las fotos de portada se asignan en el mismo módulo que los íconos, a las mismas categorías, y cada archivo existe."""
        from subastas.templatetags.presentacion import FOTOS_CATEGORIA, ICONOS_CATEGORIA

        self.assertEqual(set(FOTOS_CATEGORIA), set(ICONOS_CATEGORIA))
        for archivo in FOTOS_CATEGORIA.values():
            self.assertTrue(archivo.endswith(".jpg"), archivo)
            self.assertIsNotNone(finders.find(f"subastas/categorias/{archivo}"), archivo)

    def test_rnf_02_una_categoria_nueva_sin_foto_usa_su_tinte_y_su_icono_en_la_portada(self):
        """RNF-02 En la portada, una categoría que no está en el mapeo de fotos muestra su tinte y el ícono «tag» grande, sin imagen."""
        Categoria.objects.create(nombre="Instrumentos musicales")
        html = self.client.get(reverse("inicio")).content.decode()
        tarjeta = re.search(r'<a class="tarjeta-categoria cat-instrumentos-musicales" href="[^"]+">(.*?)</a>', html)
        self.assertIsNotNone(tarjeta)
        self.assertNotIn("<img", tarjeta.group(1))
        self.assertIn('<span class="icono-respaldo" style="--icono: url(\'/static/subastas/iconos/tag.svg\')"></span>', tarjeta.group(1))
        self.assertIn('<span class="nombre-categoria">Instrumentos musicales</span>', tarjeta.group(1))

    def test_rnf_02_los_filtros_activos_son_pildoras_que_quitan_solo_ese_filtro(self):
        """RNF-02 Junto al total, cada filtro activo (texto, categoría, tipo) es una píldora con su nombre y
        un enlace a la misma búsqueda sin ese filtro; sin filtros no hay píldoras."""
        self.subasta_abierta()
        self.client.force_login(self.crear_comprador())
        buscar = reverse("buscar_subastas")
        for consulta in ({}, {"texto": "  ", "categoria": "", "tipo": ""}):
            self.assertNotContains(self.client.get(buscar, consulta), "filtros-activos")
        html = self.client.get(buscar, {"texto": "reloj", "categoria": "Relojes", "tipo": "INGLESA"}).content.decode()
        barra = html.split('<div class="barra-resultados">')[1].split("</div>")[0]
        pildoras = re.findall(r'<a class="filtro-activo" href="([^"]+)" aria-label="Quitar filtro ([^"]+)">([^<]+)</a>', barra)
        self.assertEqual([(etiqueta, texto) for _, etiqueta, texto in pildoras],
                         [("«reloj»", "«reloj»"), ("Relojes", "Relojes"), ("Inglesa", "Inglesa")])
        consultas = [parse_qs(unescape(href).split("?", 1)[1]) for href, _, _ in pildoras]
        self.assertTrue(all(unescape(href).startswith(buscar + "?") for href, _, _ in pildoras))
        self.assertEqual(consultas, [
            {"categoria": ["Relojes"], "tipo": ["INGLESA"]},
            {"texto": ["reloj"], "tipo": ["INGLESA"]},
            {"texto": ["reloj"], "categoria": ["Relojes"]},
        ])
        solo_tipo = self.client.get(buscar, {"tipo": "INGLESA"}).content.decode()
        self.assertIn('<a class="filtro-activo" href="{}" aria-label="Quitar filtro Inglesa">Inglesa</a>'.format(buscar), solo_tipo)

    def test_rnf_02_una_categoria_nueva_usa_el_icono_generico_sin_tocar_plantillas(self):
        """RNF-02 Una categoría que no está en el mapeo lleva el ícono «tag» en la insignia de la tarjeta."""
        nueva = Categoria.objects.create(nombre="Instrumentos musicales")
        subasta = self.subasta_abierta()
        subasta.articulo.categoria = nueva
        subasta.articulo.save()
        self.client.force_login(self.crear_comprador())
        html = self.client.get(reverse("buscar_subastas")).content.decode()
        self.assertIn(
            '<span class="chip-categoria" style="--icono: url(\'/static/subastas/iconos/tag.svg\')">Instrumentos musicales</span>',
            html,
        )

    def test_rnf_02_el_mapeo_vive_en_un_solo_lugar_y_el_tinte_solo_en_la_insignia(self):
        """RNF-02 La hoja no asigna íconos por categoría, y el tono de categoría solo lo usan la insignia y la tarjeta de portada."""
        css = hoja_de_estilos()
        self.assertNotIn("--icono-cat", css)
        self.assertNotIn("--tinte-cat", css)
        for regla in re.findall(r"\.cat-[a-z-]+ \{[^}]*\}", css):
            self.assertNotIn("--icono", regla)
        sin_comentarios = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        usos = re.findall(r"([^{}]+)\{[^}]*var\(--prof-cat\)", sin_comentarios)
        self.assertEqual([u.strip() for u in usos], [".chip-categoria", ".tarjeta-categoria"])

    def test_rnf_02_la_tarjeta_de_categoria_no_crece_al_pasar_el_cursor(self):
        """RNF-02 Al pasar el cursor por una tarjeta de categoría solo aparece un borde; la foto no se escala."""
        css = hoja_de_estilos()
        self.assertNotIn("scale(", css)
        self.assertIn(".tarjeta-categoria:hover { box-shadow: 0 0 0 2px var(--borde-campo); }", css)



def banda(html):
    """El bloque <header class="banda…">…</header> de la pantalla, o "" si no lo tiene."""
    encontrada = re.search(r'<header class="banda[^"]*">(.*?)</header>', html, re.S)
    return encontrada.group(1) if encontrada else ""


class RNF02BandaDeEncabezado(PruebaSubastas):
    def test_rnf_02_las_pantallas_de_cuenta_llevan_su_h1_en_la_banda(self):
        """RNF-02 Entrar, código de verificación y registro muestran su h1 y su línea de contexto en la banda oscura,
        y debajo solo el formulario, sin foto."""
        entrar = self.client.get(reverse("entrar")).content.decode()
        self.assertIn("<h1>Entrar</h1>", banda(entrar))
        self.assertIn("Paso 1 de 2", banda(entrar))
        self.assertNotIn("cuenta-foto", entrar)
        self.assertNotIn("cronografo.jpg", entrar)
        self.assertIn("<h1>Crear cuenta</h1>", banda(self.client.get(reverse("registro")).content.decode()))
        usuario = self.crear_comprador()
        codigo = self.client.post(reverse("entrar"), {"correo": usuario.correo, "contrasena": CONTRASENA}, follow=True)
        self.assertIn("<h1>Código de verificación</h1>", banda(codigo.content.decode()))

    def test_rnf_02_las_pantallas_del_comprador_llevan_su_h1_en_la_banda(self):
        """RNF-02 Panel, buscador, ficha, historial, avisos y la confirmación del comprador llevan su h1 en la banda;
        el panel lleva ahí el saludo (su barra de búsqueda va debajo, en claro) y la ficha la categoría y el estado."""
        subasta = self.subasta_abierta(tipo="COMPRA_INMEDIATA", precio_compra_inmediata=5000)
        self.client.force_login(self.crear_comprador())
        panel = self.client.get(reverse("inicio")).content.decode()
        inicio = banda(panel)
        self.assertIn("<h1>Casa de Subastas</h1>", inicio)
        self.assertIn("Hola, Comprador de prueba.", inicio)
        self.assertNotIn("buscador-inicio", inicio)
        self.assertIn('<form class="buscador-inicio"', panel)
        self.assertIn("<h1>Subastas abiertas</h1>", banda(self.client.get(reverse("buscar_subastas")).content.decode()))
        ficha = banda(self.client.get(reverse("detalle_subasta", args=[subasta.pk])).content.decode())
        self.assertIn("<h1>Reloj de prueba</h1>", ficha)
        self.assertIn("<span>Relojes</span>", ficha)
        self.assertIn('<span class="sello sello-en-curso">Abierta</span>', ficha)
        self.assertIn("<h1>Mi historial</h1>", banda(self.client.get(reverse("historial")).content.decode()))
        self.assertIn("<h1>Avisos</h1>", banda(self.client.get(reverse("avisos")).content.decode()))
        confirmar = banda(self.client.get(reverse("confirmar_compra_inmediata", args=[subasta.pk])).content.decode())
        self.assertIn("<h1>Revisa y confirma</h1>", confirmar)
        self.assertIn("<strong>Reloj de prueba</strong>", confirmar)

    def test_rnf_02_el_buscador_sigue_fijo_fuera_de_la_banda(self):
        """RNF-02 El buscador es una franja clara aparte justo después de la banda (si fuera hijo de la banda, dejaría de quedar fijo)."""
        self.client.force_login(self.crear_comprador())
        html = self.client.get(reverse("buscar_subastas")).content.decode()
        self.assertNotIn('class="busqueda"', banda(html))
        self.assertRegex(html, r'</header>\s*<div class="busqueda">')

    def test_rnf_02_el_personal_y_sus_confirmaciones_llevan_banda(self):
        """RNF-02 Las pantallas del vendedor, del gestor y del moderador, y la confirmación del moderador (plantilla
        compartida, sin monto), llevan su h1 en la banda; las migas de regreso van dentro de la banda."""
        articulo = self.registrar_articulo()
        vendedor, gestor, moderador = self.vendedor, self.gestor, self.crear_moderador()
        self.client.force_login(vendedor)
        mis_articulos = banda(self.client.get(reverse("mis_articulos")).content.decode())
        self.assertIn("<h1>Mis artículos</h1>", mis_articulos)
        self.assertIn('<a class="boton" href="{}">Registrar artículo</a>'.format(reverse("registrar_articulo")), mis_articulos)
        self.assertIn("<h1>Registrar artículo</h1>", banda(self.client.get(reverse("registrar_articulo")).content.decode()))
        detalle = banda(self.client.get(reverse("detalle_articulo", args=[articulo.pk])).content.decode())
        self.assertIn("<h1>Reloj de prueba</h1>", detalle)
        self.assertIn('<p class="migas"><a href="{}">← Mis artículos</a></p>'.format(reverse("mis_articulos")), detalle)
        self.client.force_login(gestor)
        self.assertIn("<h1>Pendientes del gestor</h1>", banda(self.client.get(reverse("gestor_bandeja")).content.decode()))
        revisar = banda(self.client.get(reverse("gestor_articulo", args=[articulo.pk])).content.decode())
        self.assertIn("<h1>Reloj de prueba</h1>", revisar)
        self.assertIn('<p class="migas"><a href="{}">← Pendientes</a></p>'.format(reverse("gestor_bandeja")), revisar)
        infractor = self.crear_comprador()
        self.client.force_login(moderador)
        self.assertIn("<h1>Moderación</h1>", banda(self.client.get(reverse("moderador_bandeja")).content.decode()))
        self.assertIn("<h1>Reloj de prueba</h1>", banda(self.client.get(reverse("moderador_articulo", args=[articulo.pk])).content.decode()))
        self.assertIn("<h1>Comprador de prueba</h1>", banda(self.client.get(reverse("moderador_usuario", args=[infractor.pk])).content.decode()))
        confirmacion = self.client.post(reverse("confirmar_sancion", args=[infractor.pk]), {"motivo": "Spam", "nivel": "1"})
        html = banda(confirmacion.content.decode())
        self.assertIn("<h1>Revisa y confirma</h1>", html)
        self.assertIn("<strong>Comprador de prueba</strong>", html)


class RNF02PaginasDeError(PruebaSubastas):
    @override_settings(DEBUG=False)
    def test_rnf_02_la_404_es_propia_con_banda_y_enlace_a_inicio(self):
        """RNF-02 Una dirección que no existe muestra la 404 propia, en español, con banda y enlace al inicio."""
        respuesta = self.client.get("/no-existe/")
        self.assertEqual(respuesta.status_code, 404)
        self.assertTemplateUsed(respuesta, "404.html")
        self.assertIn("<h1>Página no encontrada</h1>", banda(respuesta.content.decode()))
        self.assertContains(respuesta, f'<a href="{reverse("inicio")}">Ir al inicio</a>', status_code=404)

    @override_settings(DEBUG=False)
    def test_rnf_02_la_500_es_autonoma(self):
        """RNF-02 Un error del servidor muestra la 500 propia, que se pinta sin procesadores de contexto ni base de datos, con los mismos estilos."""
        cliente = Client(raise_request_exception=False)
        with mock.patch("subastas.views.general.render", side_effect=RuntimeError("falla simulada")):
            respuesta = cliente.get(reverse("inicio"))
        html = respuesta.content.decode()
        self.assertEqual(respuesta.status_code, 500)
        self.assertIn("<h1>Algo salió mal</h1>", html)
        self.assertIn("subastas/estilos.css", html)
        self.assertIn('<a href="/">Ir al inicio</a>', html)
        with self.assertNumQueries(0):
            server_error(RequestFactory().get("/"))
