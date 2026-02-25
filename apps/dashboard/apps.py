# apps/dashboard/apps.py
from django.apps import AppConfig
import importlib
import logging
import sys

logger = logging.getLogger(__name__)

class DashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # ⬇️ Ajusta al path real de tu proyecto. Por tu árbol: Innovak/apps/dashboard
    name = "apps.dashboard"
    verbose_name = "Dashboard (IA)"

    def ready(self):
        """
        Registra dashboards y servicios de IA evitando ejecutar
        cargas pesadas en comandos de mantenimiento.
        """
        # Evita cargar Dash/IA en comandos que no necesitan el runtime
        skip_cmds = {"makemigrations", "migrate", "collectstatic", "shell", "test"}
        if any(cmd in sys.argv for cmd in skip_cmds):
            return

        modules_to_load = (
            "apps.dashboard.dash_apps",                # Dash apps (si las tienes)
            "apps.dashboard.services.intent_analyzer", # Servicio IA
            "apps.dashboard.services.query_builder",   # Builder de queries
        )

        for mod in modules_to_load:
            try:
                importlib.import_module(mod)
                logger.info("Cargado módulo de dashboard: %s", mod)
            except Exception as e:
                logger.exception("Error cargando %s: %s", mod, e)
