# dashboard/__init__.py
default_app_config = 'dashboard.apps.DashboardConfig'

# dashboard/apps.py
from django.apps import AppConfig

class DashboardConfig(AppConfig):
    name = 'dashboard'

    def ready(self):
        import dashboard.dash_apps  # Esto activa los dashboards