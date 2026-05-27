from datetime import date
from django import forms
from apps.login.forms import PersonaForm
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
    CalidadAccesoSalud, ServicioBasico, TipoDispositivo
)
from .models.sisben import Sisben
from apps.login.models.persona_documento import PersonaDocumento, TipoDocumento
from apps.login.models.persona import Participante
from apps.login.models.evento import Evento, TipoEvento
from apps.login.models.documentos_evento import TipoArchivo, DocumentoEvento
from apps.georeferenciacion.models.models_localizacion import Lugar


# ──────────────────────────────────────────────
# Widget fecha DD / MM / AAAA para PersonaDocumento
# ──────────────────────────────────────────────

class FechaExpedicionWidget(forms.MultiWidget):
    def __init__(self):
        widgets = [
            forms.NumberInput(attrs={'placeholder': 'DD', 'min': 1, 'max': 31, 'style': 'width:60px'}),
            forms.NumberInput(attrs={'placeholder': 'MM', 'min': 1, 'max': 12, 'style': 'width:60px'}),
            forms.NumberInput(attrs={'placeholder': 'AAAA', 'min': 1900, 'max': 2100, 'style': 'width:90px'}),
        ]
        super().__init__(widgets)

    def decompress(self, value):
        if value:
            return [value.day, value.month, value.year]
        return [None, None, None]


class FechaExpedicionField(forms.MultiValueField):
    widget = FechaExpedicionWidget

    def __init__(self, *args, **kwargs):
        fields = (
            forms.IntegerField(min_value=1, max_value=31),
            forms.IntegerField(min_value=1, max_value=12),
            forms.IntegerField(min_value=1900, max_value=2100),
        )
        super().__init__(fields=fields, require_all_fields=False, *args, **kwargs)

    def compress(self, data_list):
        if data_list and all(data_list):
            return date(int(data_list[2]), int(data_list[1]), int(data_list[0]))
        return None


class PersonaDocumentoForm(forms.ModelForm):
    fecha_expedicion = FechaExpedicionField(required=False, label="Fecha expedición")

    class Meta:
        model = PersonaDocumento
        fields = '__all__'


# ──────────────────────────────────────────────
# Registros Admin
# ──────────────────────────────────────────────

@admin.register(TipoDocumento)
class TipoDocumentoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre']
    search_fields = ['nombre']


@admin.register(PersonaDocumento)
class PersonaDocumentoAdmin(admin.ModelAdmin):
    form = PersonaDocumentoForm
    list_display = ['id', 'tipo_documento', 'numero_documento', 'fecha_expedicion']
    search_fields = ['numero_documento']
    list_filter = ['tipo_documento']


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


@admin.register(Sisben)
class SisbenAdmin(admin.ModelAdmin):
    list_display = ('persona', 'tiene_sisben', 'nivel', 'puntaje')
    search_fields = ('persona__nombre1', 'persona__apellido1')


class UsuarioGrupoInline(admin.TabularInline):
    model = UsuarioGrupo
    extra = 1


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    inlines = [UsuarioGrupoInline]
    exclude = ('groups', 'user_permissions')
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
    form = PersonaForm  # ← esta línea
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


@admin.register(Participante)
class ParticipanteAdmin(admin.ModelAdmin):
    list_display = ('id', 'persona')
    search_fields = ('persona__nombre1', 'persona__apellido1')


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'tipo_evento', 'fecha_inicio', 'activo')
    list_filter = ('tipo_evento', 'activo')
    search_fields = ('nombre',)
    raw_id_fields = ('lugar_incidencia',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'lugar_incidencia':
            kwargs['queryset'] = Lugar.objects.only('id', 'nombre')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(TipoEvento)
class TipoEventoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre')
    search_fields = ('nombre',)


@admin.register(TipoArchivo)
class TipoArchivoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)


@admin.register(DocumentoEvento)
class DocumentoEventoAdmin(admin.ModelAdmin):
    list_display = ('evento', 'tipo_archivo', 'nombre_archivo', 'fecha_subida')
    list_filter = ('tipo_archivo',)
    search_fields = ('nombre_archivo',)


@admin.register(LugarNacimiento)
class LugarNacimientoAdmin(admin.ModelAdmin):
    exclude = ['id']
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