from django.contrib import admin
from .models.models_localizacion import Localidad, UPZ, Barrio, Lugar, Pais, Departamento, Municipio, LugarIncidencia

# ✅ Configuración básica para cada modelo
@admin.register(Localidad)
class LocalidadAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre')
    search_fields = ('nombre',)


@admin.register(UPZ)
class UPZAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'localidad_codigo')
    search_fields = ('nombre',)
    list_filter = ('localidad_codigo',)


@admin.register(Barrio)
class BarrioAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'upz_codigo')
    search_fields = ('nombre',)
    list_filter = ('upz_codigo',)


@admin.register(Lugar)
class LugarAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'direccion', 'localidad', 'upz', 'barrio')
    search_fields = ('nombre', 'direccion')
    list_filter = ('localidad', 'upz', 'barrio')


@admin.register(Pais)
class PaisAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre')
    search_fields = ('nombre',)


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'pais')
    search_fields = ('nombre',)
    list_filter = ('pais',)


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre')
    search_fields = ('nombre',)


@admin.register(LugarIncidencia)
class LugarIncidenciaAdmin(admin.ModelAdmin):
    list_display = ('id', 'geo_referenciacion')
    search_fields = ('geo_referenciacion',)
