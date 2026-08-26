from django.apps import AppConfig


class LoginConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.login' 
    verbose_name = 'Login y Usuarios'

    def ready(self):
        # Invalidación del catálogo de organización (dependencias, subgrupos,
        # tipos de evento). Ver el porqué en `apps/login/signals.py`.
        from apps.login import signals
        signals.conectar()
