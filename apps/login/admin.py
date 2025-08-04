from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models.usuario import Usuario, UsuarioGrupo
from .models.persona import Persona
from .models.funcionario import Funcionario, Cargo, Dependencia, Subgrupo, TipoFuncionario
from .models.contacto_persona import ContactoPersona
from .models.models_auxiliares import (
    LugarNacimiento, GrupoEtario, Sexo, IdentidadGenero, 
    OrientacionSexual, GrupoEtnico, TipoDiscapacidad, TipoVictima,
    Zona, NivelEducativo, Ocupacion, SectorEconomico,
    TipoConstruccion, AfiliacionSalud, EPS, AccesoSalud,
    CalidadAccesoSalud,ServicioBasico,TipoDispositivo
)
from .models.sisben import Sisben
from apps.login.models.inscripcion import Inscripcion

Funcionario._meta.verbose_name_plural = "Estructura Organizacional – Funcionarios"
Dependencia._meta.verbose_name_plural = "Estructura Organizacional – Dependencias"
Subgrupo._meta.verbose_name_plural = "Estructura Organizacional – Subgrupos"
Cargo._meta.verbose_name_plural = "Estructura Organizacional – Cargos"
TipoFuncionario._meta.verbose_name_plural = "Estructura Organizacional – Tipos de Funcionarios"
Sexo._meta.verbose_name_plural = "Catálogos – Sexos"
NivelEducativo._meta.verbose_name_plural = "Catálogos – Niveles Educativos"
GrupoEtnico._meta.verbose_name_plural = "Catálogos – Grupos Étnicos"
admin.site.index_title = "Panel de Administración"
admin.site.site_header = "Sistema de Gestión Organizacional"
admin.site.site_title = "Administración Alcaldía"


@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = ('participante', 'curso', 'evento', 'fecha_inscripcion', 'estado')
    search_fields = ('participante__persona__nombre1', 'curso__nombre', 'evento__nombre')
    list_filter = ('estado', 'fecha_inscripcion')

@admin.register(Sisben)
class SisbenAdmin(admin.ModelAdmin):
    list_display = ('persona', 'tiene_sisben', 'nivel', 'puntaje')
    search_fields = ('persona__nombre1', 'persona__apellido1')

# Registro de todos los modelos en el admin
class UsuarioGrupoInline(admin.TabularInline):
    model = UsuarioGrupo
    extra = 1  # filas extra vacías

@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    inlines = [UsuarioGrupoInline]
    exclude = ('groups', 'user_permissions')  # no mostrar campos ManyToMany directos
    list_display = ('username', 'email', 'is_staff', 'is_active', 'is_superuser')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Información Personal', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser')
        }),
        ('Fechas importantes', {'fields': ('last_login', 'date_joined')}),
        ('Extra', {'fields': ('es_funcionario',)})
    )

@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre1', 'apellido1', 'sexo_biologico', 'nivel_educativo', 'ocupacion_actual')
    search_fields = ('nombre1', 'apellido1', 'persona_documento__numero_documento')
    list_filter = ('sexo_biologico', 'nivel_educativo', 'grupo_etnico', 'ocupacion_actual')


@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'persona', 'dependencia', 'cargo', 'activo')
    list_filter = ('activo', 'dependencia', 'cargo')
    search_fields = ('persona__primer_nombre', 'persona__primer_apellido')
    raw_id_fields = ('persona',)



@admin.register(Dependencia)
class DependenciaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')

@admin.register(Subgrupo)
class SubgrupoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'dependencia')

@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')

@admin.register(TipoFuncionario)
class TipoFuncionarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')


@admin.register(ContactoPersona)
class ContactoPersonaAdmin(admin.ModelAdmin):
    list_display = ('id', 'telefono_principal', 'direccion', 'localidad', 'barrio', 'upz')
    search_fields = ('telefono_principal', 'direccion')
    list_filter = ('localidad', 'barrio', 'upz')




@admin.register(LugarNacimiento)
class LugarNacimientoAdmin(admin.ModelAdmin):
    exclude = ['id']  # Ocultar campo id
    list_display = ['persona', 'municipio', 'pais', 'departamento']

admin.site.register(GrupoEtario)
admin.site.register(Sexo)
admin.site.register(IdentidadGenero)
admin.site.register(OrientacionSexual)
admin.site.register(GrupoEtnico)
admin.site.register(TipoDiscapacidad)
admin.site.register(TipoVictima)
admin.site.register(Zona)
admin.site.register(NivelEducativo)
admin.site.register(Ocupacion)
admin.site.register(SectorEconomico)
admin.site.register(TipoConstruccion)
admin.site.register(AfiliacionSalud)
admin.site.register(EPS)
admin.site.register(AccesoSalud)
admin.site.register(CalidadAccesoSalud)
admin.site.register(TipoDispositivo)
admin.site.register(ServicioBasico)