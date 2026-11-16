"""TransactionTestCase para que cada hilo abra su propia transacción IMMEDIATE de SQLite."""
import threading

from django.db import connection
from django.test import TransactionTestCase

from subastas.mensajes import ErrorDeNegocio
from subastas.models import Puja
from subastas.servicios import pujas

from .base import EntornoDePrueba


class PujasSimultaneas(EntornoDePrueba, TransactionTestCase):
    # Conserva los roles y categorías que cargan las migraciones.
    serialized_rollback = True

    def setUp(self):
        self.preparar_entorno()
        self.addCleanup(self.restaurar_entorno)

    def test_dos_pujas_iguales_simultaneas_solo_aceptan_una(self):
        subasta = self.subasta_abierta(costo_salida=1000)
        compradores = [self.crear_comprador(), self.crear_comprador()]
        salida = threading.Barrier(len(compradores))
        resultados = []

        def pujar(comprador):
            try:
                salida.wait()
                pujas.pujar(comprador=comprador, subasta_id=subasta.pk, monto=1001)
                resultados.append("aceptada")
            except ErrorDeNegocio as error:
                resultados.append(error.codigo)
            finally:
                connection.close()

        hilos = [threading.Thread(target=pujar, args=(c,)) for c in compradores]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join(timeout=30)

        self.assertEqual(sorted(resultados), ["ERR-06", "aceptada"])
        self.assertEqual(Puja.objects.filter(subasta=subasta).count(), 1)
