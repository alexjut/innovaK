"""Forms de `login` que siguen vivos.

Este módulo tenía cuatro `ModelForm`/`Form`; tres murieron con el corte a
Angular del 2026-06-11, cuando el registro de usuario y la inscripción a
eventos pasaron a DRF. Se retiraron el 2026-08-06: `SisbenForm`,
`UsuarioRegistroForm` y `EventoPersonaForm`.

Queda `PersonaForm`, que **no es residuo**: lo usa `PersonaAdmin` en
`apps/login/admin.py`, o sea el `/admin` de Django, que sí sigue en pie. Es
justo lo que el inventario del bloque D daba por muerto.
"""
from django import forms

from apps.login.models.persona import Persona


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
