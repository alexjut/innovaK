from django import forms
from django.contrib.auth.models import Group
from apps.login.models.usuario import Usuario
from .models.sisben import Sisben
from apps.login.models.persona import Persona

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
       # Diccionario de agrupaciones para el template
    secciones = {
        "Datos personales": ['nombres', 'apellidos', 'tipo_documento', 'numero_documento'],
        "Datos sociodemográficos": ['genero', 'grupo_etnico', 'nivel_educativo'],
        "Ubicación": ['direccion', 'localidad', 'zona', 'estrato_social'],
        "Contacto": ['telefono', 'email'],
        "Condición": ['tipo_victima', 'migrante', 'poblacion_rural', 'contacto'],
    }