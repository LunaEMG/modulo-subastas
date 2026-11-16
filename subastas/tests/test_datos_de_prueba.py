"""El comando cargar_datos_prueba deja el sistema listo para demostrar sin recorrer el flujo."""
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
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
