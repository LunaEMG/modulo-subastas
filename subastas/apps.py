from django.apps import AppConfig


class SubastasConfig(AppConfig):
    name = "subastas"
    verbose_name = "Módulo de Subastas"

    def ready(self):
        from .servicios import notificaciones

        notificaciones.registrar_suscriptores()
