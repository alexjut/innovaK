import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','core.settings')
django.setup()
from apps.presupuesto.models.core import Proyecto
print('OK Proyecto:', Proyecto)