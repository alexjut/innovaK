from django import forms
from apps.kactivo.models.kdocumentos import DocumentoRequisito, ValidacionDocumental
from apps.kactivo.models.kasistencia import Curso, CursoExtendido, Participante, Acudiente
from apps.kactivo.models.karacterizacion import CaracterizacionCultura, CaracterizacionDeporte
from apps.login.models.persona import Persona
from apps.login.models.sisben import Sisben



class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ['nombre', 'institucion', 'clase', 'programas']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'institucion': forms.TextInput(attrs={'class': 'form-control'}),
            'clase': forms.Select(attrs={'class': 'form-control'}),
            'programas': forms.Select(attrs={'class': 'form-control'}),
        }

# =============== FORMULARIO PARTICIPANTE ==================

class ParticipanteForm(forms.ModelForm):
    class Meta:
        model = Participante
        fields = ['persona']



# =================== FORMULARIO CULTURA ===================
class CaracterizacionCulturaForm(forms.ModelForm):
    class Meta:
        model = CaracterizacionCultura
        fields = [
            'persona', 'evento', 'nivel_educativo_codigo',
            'documentacion_soporte', 'motivacion_personal'
        ]
        widgets = {
            'nivel_educativo_codigo': forms.NumberInput(attrs={'class': 'form-control'}),
            'motivacion_personal': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'documentacion_soporte': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
# =============== FORMULARIO DATOS COMPLEMENTARIOS ==================

class DatosComplementariosForm(forms.ModelForm):
    class Meta:
        model = Persona
        fields = [
            'ocupacion_actual', 'sector_economico', 'ingresos_mensuales',
            'tipo_construccion', 'numero_personas_hogar', 'tipo_vivienda',
            'servicio_basico', 'tipo_dispositivo', 'afiliacion_salud', 'eps',
            'acceso_servicios_salud', 'acceso_salud', 'arl', 'acceso_internet'
        ]
        widgets = {
            'arl': forms.Select(attrs={'class': 'form-control'}),
            # Puedes definir otros widgets también si usas Bootstrap
        }


class SisbenForm(forms.ModelForm):
    class Meta:
        model = Sisben
        fields = ['puntaje', 'nivel', 'persona']




# =============== FORMULARIO ACUDIENTE ==================

class AcudienteForm(forms.ModelForm):
    class Meta:
        model = Acudiente
        fields = ['nombre', 'parentesco', 'telefono', 'correo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'parentesco': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control'}),
        }


# =============== FORMULARIO CURSO ==================

class CursoAsignacionForm(forms.Form):
    curso = forms.ModelChoiceField(
        queryset=CursoExtendido.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Curso disponible"
    )

    def __init__(self, *args, **kwargs):
        tipo_area = kwargs.pop('tipo_area', None)
        super().__init__(*args, **kwargs)
        if tipo_area:
            self.fields['curso'].queryset = CursoExtendido.objects.filter(
                tipo_curso=tipo_area
            ).order_by('nombre')


# =============== FORMULARIO DOCUMENTOS ==================

class DocumentoRequisitoForm(forms.ModelForm):
    class Meta:
        model = DocumentoRequisito
        fields = ['nombre', 'descripcion', 'requerido_para']


# =============== FORMULARIO VALIDACIÓN ==================

class ValidacionDocumentalForm(forms.ModelForm):
    class Meta:
        model = ValidacionDocumental
        fields = [
            'documento_identidad',
            'consentimiento_informado',
            'certificado_eps',
            'formulario_inscripcion_firmado',
            'certificacion_residencia',
            'cumplido'
        ]
        widgets = {
            field: forms.CheckboxInput(attrs={'class': 'form-check-input'})
            for field in fields
        }