from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from subastas import reloj


class Command(BaseCommand):
    help = "Adelanta el reloj de demostración (solo con DEBUG)."

    def add_arguments(self, parser):
        parser.add_argument("--minutos", type=float, default=0)
        parser.add_argument("--horas", type=float, default=0)
        parser.add_argument("--dias", type=float, default=0)
        parser.add_argument("--reiniciar", action="store_true", help="Regresa al reloj real.")

    def handle(self, *args, minutos, horas, dias, reiniciar, **opciones):
        if not settings.RELOJ.endswith("RelojDemo"):
            raise CommandError("El reloj de demostración solo está activo con DEBUG.")
        if reiniciar:
            reloj.guardar_desplazamiento(0)
        else:
            avance = timedelta(minutes=minutos, hours=horas, days=dias)
            if avance <= timedelta(0):
                raise CommandError("Indica cuánto adelantar: --minutos, --horas o --dias.")
            reloj.guardar_desplazamiento(reloj.leer_desplazamiento() + avance.total_seconds())
        self.stdout.write(f"Hora del sistema: {reloj.formato(reloj.ahora())}")
