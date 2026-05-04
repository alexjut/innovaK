from django import forms
from django.contrib.auth.models import Group
from apps.login.models.usuario import Usuario
from .models.sisben import Sisben
from apps.login.models.persona import Persona
from apps.login.models import Sexo, IdentidadGenero, OrientacionSexual, GrupoEtnico 
from apps.login.models.inscripcion import Inscripcion
from apps.login.models.evento import Evento  # M1: ya no duplicado en kactivo
from apps.georeferenciacion.models import UPZ, Barrio




class InscripcionForm(forms.ModelForm):
    class Meta:
        model = Inscripcion
        fields = ['curso', 'evento', 'fecha_inscripcion', 'observaciones', 'estado']
        widgets = {
            'fecha_inscripcion': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'curso': forms.Select(attrs={'class': 'form-control'}),
            'evento': forms.Select(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        curso = cleaned_data.get("curso")
        evento = cleaned_data.get("evento")

        if not curso and not evento:
            raise forms.ValidationError("Debe seleccionar un curso o un evento.")
        if curso and evento:
            raise forms.ValidationError("Seleccione solo uno: curso o evento.")
        return cleaned_data

class SisbenForm(forms.ModelForm):
    class Meta:
        model = Sisben
        fields = ['tiene_sisben', 'nivel', 'puntaje']
        widgets = {
            'nivel': forms.TextInput(attrs={'class': 'form-control'}),
            'puntaje': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class UsuarioRegistroForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirmar contraseña")
    grupo = forms.ModelChoiceField(queryset=Group.objects.all(), required=True, label="Grupo o Rol")

    class Meta:
        model = Usuario
        fields = ['username', 'password', 'grupo']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")

        if password and confirm and password != confirm:
            raise forms.ValidationError("Las contraseñas no coinciden.")


class PersonaForm(forms.ModelForm):
    class Meta:
        model = Persona
        fields = [
            'nombre1', 'nombre2', 'apellido1', 'apellido2',
            'usuario', 'persona_documento',
            'lugar_nacimiento', 'grupo_etario', 'sexo_biologico', 'identidad_genero',
            'orientacion_sexual', 'grupo_etnico', 'pertenencia_lgbti', 'discapacidad',
            'tipo_discapacidad', 'rol_cuidador', 'victima_conflicto', 'tipo_victima',
            'migrante', 'poblacion_rural', 'contacto', 'zona', 'estrato_social',
            'nivel_educativo', 'actualmente_estudia', 'institucion',
            'ocupacion_actual', 'sector_economico', 'ingresos_mensuales',
            'tipo_construccion', 'numero_personas_hogar', 'tipo_vivienda',
            'servicio_basico', 'tipo_dispositivo',
            'afiliacion_salud', 'eps', 'acceso_servicios_salud', 'acceso_salud',
            'arl', 'acceso_internet'
        ]

    # ✅ Agrupación de campos para organizar en template
    secciones = {
        "Datos personales": ['nombre1', 'nombre2', 'apellido1', 'apellido2', 'usuario'],
        "Documento": ['persona_documento'],
        "Datos sociodemográficos": ['grupo_etario', 'sexo_biologico', 'identidad_genero', 'orientacion_sexual', 'grupo_etnico'],
        "Condición": ['pertenencia_lgbti', 'discapacidad', 'tipo_discapacidad', 'rol_cuidador', 'victima_conflicto', 'tipo_victima', 'migrante', 'poblacion_rural'],
        "Ubicación": ['lugar_nacimiento', 'zona', 'estrato_social', 'tipo_construccion', 'tipo_vivienda', 'numero_personas_hogar'],
        "Educación y ocupación": ['nivel_educativo', 'actualmente_estudia', 'institucion', 'ocupacion_actual', 'sector_economico', 'ingresos_mensuales'],
        "Salud": ['afiliacion_salud', 'eps', 'acceso_servicios_salud', 'acceso_salud', 'arl', 'acceso_internet'],
        "Tecnología y servicios": ['servicio_basico', 'tipo_dispositivo']
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # ✅ Hacer todos los campos opcionales
        for field_name, field in self.fields.items():
            field.required = False
            # ✅ Ajustar selects para que muestren "---------"
            if hasattr(field.widget, 'choices') and field.widget.choices:
                field.empty_label = "---------"




class EventoPersonaForm(forms.Form):
    # --- Sección Evento ---
    nombre_evento = forms.CharField(
        label="Nombre del evento",
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    fecha_realizacion = forms.DateField(
        label="Fecha de realización",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    hora_inicio = forms.TimeField(
        label="Hora de inicio",
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'})
    )
    responsable_evento = forms.CharField(
        label="Responsable del evento",
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    # --- Sección Participante ---
    nombre1 = forms.CharField(label="Primer Nombre", max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    nombre2 = forms.CharField(label="Segundo Nombre", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    apellido1 = forms.CharField(label="Primer Apellido", max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    apellido2 = forms.CharField(label="Segundo Apellido", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    fecha_nacimiento = forms.DateField(label="Fecha de nacimiento", widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))

    # ✅ Campos relacionados con tablas externas
    sexo_biologico = forms.ModelChoiceField(
        queryset=Sexo.objects.all(),
        required=False,
        label="Sexo biológico",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    identidad_genero = forms.ModelChoiceField(
        queryset=IdentidadGenero.objects.all(),
        required=False,
        label="Identidad de género",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    orientacion_sexual = forms.ModelChoiceField(
        queryset=OrientacionSexual.objects.all(),
        required=False,
        label="Orientación sexual",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    grupo_etnico = forms.ModelChoiceField(
        queryset=GrupoEtnico.objects.all(),
        required=False,
        label="Grupo étnico",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    discapacidad = forms.BooleanField(label="¿Tiene discapacidad?", required=False)

    telefono = forms.CharField(label="Número de teléfono", max_length=20, widget=forms.TextInput(attrs={'class': 'form-control'}))
    correo = forms.EmailField(label="Correo electrónico", required=False, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    # --- Ubicación ---
    upz = forms.ModelChoiceField(
        queryset=UPZ.objects.all(),
        required=False,
        label="UPZ",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    barrio = forms.ModelChoiceField(
        queryset=Barrio.objects.all(),
        required=False,
        label="Barrio",
        widget=forms.Select(attrs={'class': 'form-select'})
    )