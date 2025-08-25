# apps/dashboard/ai_config.py
from django.utils.module_loading import import_string

MODEL_PATHS = {
    "login_persona": "apps.login.models.persona.Persona",
    "login_participante": "apps.login.models.persona.Participante",  # por si consultas derivadas
}

def get_model(model_key: str):
    return import_string(MODEL_PATHS[model_key])

class AIConfig:
    # Campos REALES de Persona (los que mostraste)
    FIELD_MODEL_MAP = {
        # Identificación / nombre
        "id": "login_persona",
        "nombre1": "login_persona",
        "nombre2": "login_persona",
        "apellido1": "login_persona",
        "apellido2": "login_persona",
        "fecha_nacimiento": "login_persona",

        # Relaciones útiles (FK) — usaremos lookups a pk/str cuando haga sentido
        "usuario_id": "login_persona",
        "persona_documento_id": "login_persona",
        "lugar_nacimiento_codigo": "login_persona",
        "grupo_etario": "login_persona",
        "sexo_biologico_id": "login_persona",
        "identidad_genero_id": "login_persona",
        "orientacion_sexual_id": "login_persona",
        "grupo_etnico_id": "login_persona",

        # Socio-demo
        "pertenencia_lgbti": "login_persona",
        "discapacidad": "login_persona",
        "tipo_discapacidad_id": "login_persona",
        "rol_cuidador": "login_persona",
        "victima_conflicto": "login_persona",
        "tipo_victima_id": "login_persona",
        "migrante": "login_persona",
        "poblacion_rural": "login_persona",

        # Contacto / zona
        "contacto_id": "login_persona",
        "zona_codigo": "login_persona",
        "estrato_social": "login_persona",

        # Educación
        "nivel_educativo_id": "login_persona",
        "actualmente_estudia": "login_persona",
        "institucion": "login_persona",

        # Laboral / ingresos
        "ocupacion_actual_id": "login_persona",
        "sector_economico_id": "login_persona",
        "ingresos_mensuales": "login_persona",

        # Vivienda / servicios
        "tipo_construccion_codigo": "login_persona",
        "numero_personas_hogar": "login_persona",
        "tipo_vivienda_codigo": "login_persona",
        "servicio_basico_codigo": "login_persona",
        "tipo_dispositivo_id": "login_persona",

        # Salud
        "afiliacion_salud_id": "login_persona",
        "eps_id": "login_persona",
        "acceso_servicios_salud_id": "login_persona",
        "acceso_salud_codigo": "login_persona",
        "arl_id": "login_persona",
        "acceso_internet": "login_persona",

        # Auditoría
        "created_at": "login_persona",
        "updated_at": "login_persona",
        "usuario_editor": "login_persona",
    }

    # Whitelist por modelo
    ALLOWED_FIELDS = {}
    for f, m in FIELD_MODEL_MAP.items():
        ALLOWED_FIELDS.setdefault(m, []).append(f)

    # Sinónimos comunes para Persona
    FIELD_MAPPING = {
        "nombre": "nombre1",
        "segundo nombre": "nombre2",
        "primer apellido": "apellido1",
        "segundo apellido": "apellido2",
        "nacimiento": "fecha_nacimiento",
        "estrato": "estrato_social",
        "personas en hogar": "numero_personas_hogar",
        "eps": "eps_id",
        "arl": "arl_id",
        "ocupacion": "ocupacion_actual_id",
        "nivel educativo": "nivel_educativo_id",
        "institución": "institucion",
        "ingresos": "ingresos_mensuales",
        "internet": "acceso_internet",
        "zona": "zona_codigo",
        "sexo": "sexo_biologico_id",
        "identidad de género": "identidad_genero_id",
        "orientación sexual": "orientacion_sexual_id",
        "grupo étnico": "grupo_etnico_id",
    }

    @staticmethod
    def is_field_allowed(model_key: str, field: str) -> bool:
        return field in AIConfig.ALLOWED_FIELDS.get(model_key, [])

    @staticmethod
    def get_model_for_field(field: str):
        key = AIConfig.FIELD_MODEL_MAP.get(field)
        return get_model(key) if key else None

    @staticmethod
    def translate_synonym(user_field: str) -> str:
        return AIConfig.FIELD_MAPPING.get(user_field, user_field)