from django import forms
from apps.kactivo.models.kdocumentos import DocumentoRequisito, ValidacionDocumental
from apps.kactivo.models.kasistencia import Curso, CursoExtendido, Participante, Acudiente, Evento, Actividad
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

class ParticipanteInscripcionForm(forms.Form):
    # Datos de Persona
    nombre = forms.CharField(label='Nombre Completo')
    tipo_documento = forms.CharField(label='Tipo de Documento')
    identificacion = forms.CharField(label='Documento de Identidad')
    fecha_expedicion = forms.DateField(label='Fecha de Expedición', widget=forms.DateInput(attrs={'type': 'date'}))
    lugar_expedicion = forms.CharField(label='Lugar de Expedición')
    pais_origen = forms.CharField(label='País de Origen')
    ciudad = forms.CharField(label='Ciudad')
    area = forms.CharField(label='Área')
    localidad = forms.CharField(label='Localidad')
    upz_participante = forms.CharField(label='UPZ del Participante')
    barrio = forms.CharField(label='Barrio')
    correo = forms.EmailField(label='Correo Electrónico')
    telefono = forms.CharField(label='Teléfono de Contacto')
    direccion = forms.CharField(label='Dirección')
    fecha_nacimiento = forms.DateField(label='Fecha de Nacimiento', widget=forms.DateInput(attrs={'type': 'date'}))
    edad = forms.IntegerField(label='Edad', required=False)

    # Vinculación a inscripción
    curso = forms.ModelChoiceField(
        queryset=Curso.objects.all(), required=False, label="Curso al que desea inscribirse"
    )
    evento = forms.ModelChoiceField(
        queryset=Evento.objects.all(), required=False, label="Evento al que desea inscribirse"
    )
    actividad = forms.ModelChoiceField(
        queryset=Actividad.objects.all(), required=False, label="Actividad al que desea inscribirse"
    )

    def clean(self):
        cleaned_data = super().clean()
        curso = cleaned_data.get("curso")
        evento = cleaned_data.get("evento")
        actividad = cleaned_data.get("actividad")

        seleccionados = sum(bool(x) for x in [curso, evento, actividad])
        if seleccionados != 1:
            raise forms.ValidationError("Debe seleccionar exactamente uno entre curso, evento o actividad.")

        return cleaned_data



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