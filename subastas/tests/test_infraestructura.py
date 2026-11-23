"""Reloj, servicios externos simulados y catálogos iniciales."""
import json
import tempfile
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils.module_loading import import_string

from subastas import integraciones, reloj
from subastas.integraciones import puertos, simulados
from subastas.models import Categoria, Rol
from subastas.reglas.articulos import CATEGORIAS_PERMITIDAS

from .base import INICIO


class Reloj(SimpleTestCase):
    def tearDown(self):
        reloj.establecer_reloj(None)

    def test_el_reloj_fijo_solo_avanza_cuando_se_le_pide(self):
        fijo = reloj.RelojFijo(INICIO)
        reloj.establecer_reloj(fijo)
        self.assertEqual(reloj.ahora(), INICIO)
        fijo.avanzar(days=3)
        self.assertEqual(reloj.ahora(), INICIO + timedelta(days=3))

    def test_el_reloj_de_demostracion_suma_el_desplazamiento_guardado(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with override_settings(RELOJ_DEMO_ARCHIVO=Path(carpeta) / "reloj.json"):
                self.assertEqual(reloj.leer_desplazamiento(), 0)
                reloj.guardar_desplazamiento(3 * 86400)
                diferencia = reloj.RelojDemo().ahora() - reloj.RelojSistema().ahora()
                self.assertAlmostEqual(diferencia.total_seconds(), 3 * 86400, delta=5)


class ServiciosExternos(SimpleTestCase):
    def tearDown(self):
        integraciones.restaurar()

    def test_cada_puerto_tiene_un_simulador_configurado_que_lo_implementa(self):
        contratos = {
            "pagos": puertos.ServicioPagos,
            "valuador": puertos.ValuadorBienes,
            "logistica": puertos.ProveedorLogistico,
            "identidad": puertos.ValidadorIdentidad,
            "codigo_movil": puertos.EnviadorCodigoMovil,
            "correo": puertos.EnviadorCorreo,
        }
        self.assertEqual(set(settings.INTEGRACIONES), set(contratos))
        for nombre, contrato in contratos.items():
            with self.subTest(servicio=nombre):
                self.assertIsInstance(integraciones.obtener(nombre), contrato)

    def test_sustituir_un_servicio_es_cambiar_una_linea_de_configuracion(self):
        nueva = dict(settings.INTEGRACIONES, pagos="subastas.tests.base.PagosDoble")
        with override_settings(INTEGRACIONES=nueva):
            integraciones.restaurar()
            self.assertIsInstance(
                integraciones.obtener("pagos"), import_string("subastas.tests.base.PagosDoble")
            )

    def test_simulador_de_identidad(self):
        identidad = simulados.IdentidadSimulada()
        self.assertTrue(identidad.acredita_residencia_en_mexico(nombre="Ana", codigo_postal="07738"))
        for codigo_postal in ("00000", "1234", "ABCDE", ""):
            self.assertFalse(
                identidad.acredita_residencia_en_mexico(nombre="Ana", codigo_postal=codigo_postal)
            )

    def test_s31_el_simulador_de_identidad_ignora_los_documentos(self):
        documentos = puertos.DocumentosIdentidad(curp="AAAA000101HDFRRR09")
        self.assertFalse(documentos.vacio)
        self.assertTrue(puertos.DocumentosIdentidad().vacio)
        identidad = simulados.IdentidadSimulada()
        self.assertTrue(identidad.acredita_residencia_en_mexico(
            nombre="Ana", codigo_postal="07738", documentos=documentos
        ))
        self.assertFalse(identidad.acredita_residencia_en_mexico(
            nombre="Ana", codigo_postal="00000", documentos=documentos
        ))

    def test_simulador_de_valuador(self):
        valuador = simulados.ValuadorSimulado()
        datos = {"articulo_id": 1, "categoria": "Relojes", "anio": 2020, "precio_propuesto": 5000}
        avalado = valuador.valuar(descripcion="Reloj suizo original", **datos)
        self.assertTrue(avalado.es_autentico)
        self.assertEqual(avalado.precio_avalado, 5000)
        rechazado = valuador.valuar(descripcion="Es una réplica muy buena", **datos)
        self.assertFalse(rechazado.es_autentico)
        self.assertIsNone(rechazado.precio_avalado)

    def test_simuladores_de_pagos_y_logistica(self):
        pago = simulados.PagosSimulado().cobrar(comprador_id=1, monto_fichas=100, concepto="x")
        self.assertTrue(pago.aprobado)
        self.assertTrue(pago.referencia.startswith("PAG-"))
        envio = simulados.LogisticaSimulada().solicitar_recoleccion(
            adjudicacion_id=1, vendedor_id=1, comprador_id=2
        )
        self.assertTrue(envio.startswith("LOG-"))

    def test_los_simuladores_de_correo_y_codigo_dejan_el_envio_en_la_bandeja(self):
        reloj.establecer_reloj(reloj.RelojFijo(INICIO))
        self.addCleanup(reloj.establecer_reloj, None)
        with tempfile.TemporaryDirectory() as carpeta:
            with override_settings(BANDEJA_SIMULADA=Path(carpeta) / "bandeja.jsonl"):
                self.assertEqual(simulados.leer_bandeja(), [])
                simulados.CodigoMovilSimulado().enviar(telefono="5511112222", codigo="123456")
                self.assertTrue(
                    simulados.CorreoSimulado().enviar(
                        destinatario="ana@prueba.test", asunto="Hola", cuerpo="Texto"
                    )
                )
                correo, sms = simulados.leer_bandeja()
        self.assertEqual((correo["canal"], correo["destino"]), ("CORREO", "ana@prueba.test"))
        self.assertEqual(sms["canal"], "SMS")
        self.assertIn("123456", sms["cuerpo"])


class CatalogosIniciales(TestCase):
    def test_existen_los_cuatro_roles(self):
        self.assertEqual(
            set(Rol.objects.values_list("nombre", flat=True)),
            {Rol.VENDEDOR, Rol.COMPRADOR, Rol.GESTOR, Rol.MODERADOR},
        )

    def test_existen_las_cuatro_categorias_con_su_bandera_de_valuacion(self):
        self.assertEqual(
            dict(Categoria.objects.values_list("nombre", "requiere_valuacion")),
            CATEGORIAS_PERMITIDAS,
        )


class BandejaSimulada(TestCase):
    def test_muestra_las_fechas_en_hora_local_y_regresa_al_inicio(self):
        """La bandeja simulada muestra cada fecha en hora local (dd/mm/AAAA HH:MM) y un enlace de regreso al inicio."""
        with tempfile.TemporaryDirectory() as carpeta:
            archivo = Path(carpeta) / "bandeja.jsonl"
            archivo.write_text(json.dumps({
                "fecha": "2026-12-01T16:00:00+00:00", "canal": "CORREO", "destino": "ana@prueba.test",
                "asunto": "Hola", "cuerpo": "Texto",
            }) + "\n", encoding="utf-8")
            with override_settings(DEBUG=True, BANDEJA_SIMULADA=archivo):
                respuesta = self.client.get(reverse("bandeja_simulada"))
        self.assertContains(respuesta, "· 01/12/2026 10:00</span>")
        self.assertContains(respuesta, f'<a href="{reverse("inicio")}">← Inicio</a>')
