"""Para cron en producción; en la demostración ya lo hace ProcesoDelTiempoMiddleware."""
from django.core.management.base import BaseCommand

from subastas.servicios import cierre


class Command(BaseCommand):
    help = "Ejecuta CU-15 (cierre de subastas) y CU-16 (vencimiento de pagos y resubasta)."

    def handle(self, *args, **opciones):
        resultado = cierre.procesar_pendientes()
        self.stdout.write(
            f"Subastas cerradas: {resultado['cerradas']}. "
            f"Adjudicaciones vencidas y resubastadas: {resultado['resubastadas']}."
        )
