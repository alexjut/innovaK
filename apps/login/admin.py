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
    CalidadAccesoSalud
)
from .models.sisben import Sisben

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


admin.site.register(TipoFuncionario)
admin.site.register(Dependencia)
admin.site.register(Cargo)
admin.site.register(Subgrupo)


@admin.register(ContactoPersona)
class ContactoPersonaAdmin(admin.ModelAdmin):
    list_display = ('id', 'telefono_principal', 'direccion', 'localidad', 'barrio', 'upz')
    search_fields = ('telefono_principal', 'direccion')
    list_filter = ('localidad', 'barrio', 'upz')




admin.site.register(LugarNacimiento)
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
