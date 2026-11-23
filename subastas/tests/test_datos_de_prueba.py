"""El comando cargar_datos_prueba deja el sistema listo para demostrar sin recorrer el flujo."""
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from subastas import integraciones, reloj
from subastas.models import Adjudicacion, Articulo, Puja, Subasta, Usuario
from subastas.reglas.estados import EstadoArticulo, EstadoSubasta
from subastas.reglas.pagos import EstadoAdjudicacion


class CargarDatosDePrueba(TestCase):
    """Usa los simuladores reales de settings.INTEGRACIONES, como en la demostración."""

    def setUp(self):
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        ajustes = override_settings(
            MEDIA_ROOT=carpeta.name, BANDEJA_SIMULADA=Path(carpeta.name) / "bandeja.jsonl"
        )
        ajustes.enable()
        self.addCleanup(ajustes.disable)
        integraciones.restaurar()
        reloj.establecer_reloj(None)

    def _sin_fotos_reales(self):
        """Las ilustraciones son el respaldo cuando falta la carpeta de fotos."""
        vacia = tempfile.TemporaryDirectory()
        self.addCleanup(vacia.cleanup)
        parche = mock.patch(
            "subastas.management.commands.cargar_datos_prueba.FOTOS_DEMO", Path(vacia.name)
        )
        parche.start()
        self.addCleanup(parche.stop)

    def _cargar(self, *argumentos):
        salida = StringIO()
        call_command("cargar_datos_prueba", *argumentos, stdout=salida)
        return salida.getvalue()

    def test_crea_un_usuario_por_rol_con_residencia_acreditada(self):
        self._cargar("--solo-usuarios")
        self.assertEqual(Usuario.objects.count(), 5)
        self.assertTrue(all(Usuario.objects.values_list("residencia_verificada", flat=True)))
        self.assertFalse(Articulo.objects.exists())

    def test_crea_articulos_en_distintos_estados(self):
        self._cargar()
        estados = set(Articulo.objects.values_list("estado", flat=True))
        self.assertLessEqual(
            {
                EstadoArticulo.REGISTRADO, EstadoArticulo.RECHAZADO, EstadoArticulo.NO_AVALADO,
                EstadoArticulo.VALUADO, EstadoArticulo.DURACION_PROPUESTA,
                EstadoArticulo.EN_SUBASTA, EstadoArticulo.ADJUDICADO,
            },
            estados,
        )

    def test_hay_una_subasta_abierta_de_cada_tipo_con_pujas(self):
        self._cargar()
        abiertas = Subasta.objects.filter(estado=EstadoSubasta.ABIERTA)
        self.assertEqual(
            set(abiertas.values_list("tipo", flat=True)),
            {"INGLESA", "RESERVADA", "HOLANDESA", "COMPRA_INMEDIATA"},
        )
        self.assertEqual(abiertas.count(), 4)
        self.assertEqual(Puja.objects.filter(subasta__in=abiertas, estado=Puja.Estado.ACTIVA).count(), 4)

    def test_deja_una_compra_pendiente_de_pago_para_demostrar_cu_14(self):
        self._cargar()
        adjudicacion = Adjudicacion.objects.get()
        self.assertEqual(adjudicacion.estado, EstadoAdjudicacion.PENDIENTE_PAGO)
        self.assertEqual(adjudicacion.ganador.correo, "comprador@subastas.test")

    def test_ejecutarlo_dos_veces_no_duplica_nada(self):
        self._cargar()
        articulos = Articulo.objects.count()
        self.assertIn("ya existían", self._cargar())
        self.assertEqual((Articulo.objects.count(), Usuario.objects.count()), (articulos, 5))

    def test_sin_fotos_reales_las_fotografias_son_ilustraciones_generadas_localmente(self):
        """Si falta la foto, cada artículo de demostración trae un dibujo, no un bloque de un solo color."""
        from PIL import Image

        from subastas.models import Fotografia

        self._sin_fotos_reales()
        self._cargar()
        for foto in Fotografia.objects.all():
            with foto.archivo.open("rb") as archivo:
                imagen = Image.open(archivo)
                self.assertEqual(imagen.size, (640, 480))
                self.assertGreater(len(imagen.convert("RGB").getcolors(maxcolors=1 << 16) or [0] * 99), 4)

    def test_redibujar_no_crea_ni_borra_registros(self):
        """--redibujar sobrescribe los archivos de las fotos existentes y deja la base igual (RNF-01)."""
        from subastas.models import Fotografia

        self._sin_fotos_reales()
        self._cargar()
        antes = list(Fotografia.objects.values_list("pk", "archivo"))
        salida = self._cargar("--redibujar")
        self.assertIn(f"Fotografías redibujadas: {len(antes)}", salida)
        self.assertEqual(list(Fotografia.objects.values_list("pk", "archivo")), antes)

    def test_sin_debug_y_fuera_de_las_pruebas_se_niega_a_correr(self):
        """Con DEBUG apagado (y sin estar en las pruebas) no crea nada y remite al README."""
        with override_settings(DEBUG=False, EJECUTANDO_PRUEBAS=False):
            with self.assertRaisesMessage(CommandError, "README"):
                self._cargar()
        self.assertFalse(Usuario.objects.exists())
