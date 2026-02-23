# apps/presupuesto/admin.py
from django.contrib import admin
from .models.core_catalogos import Area

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    search_fields = ("nombre",)
    list_display = ("id", "nombre")
