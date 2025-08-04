from django.apps import AppConfig

class GeoreferenciacionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.georeferenciacion'

    def ready(self):
        import apps.georeferenciacion.models
