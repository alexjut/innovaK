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
        "grupo_sanguineo_id": "login_persona",

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

    ALLOWED_FIELDS["login_persona"] = list(
            set(ALLOWED_FIELDS.get("login_persona", [])) | {
                "id", "nombre1", "nombre2", "apellido1", "apellido2",
                "apellido", "estrato_social", "sexo_biologico_id",
                "identidad_genero_id", "grupo_etnico_id",
                "orientacion_sexual_id", "eps_id",
                # NO pongas grupo_sanguineo_id si el campo no existe
            }
        )

    # Sinónimos comunes para Persona. N17 mínima: expandido con
    # términos coloquiales que la gente realmente teclea.
    FIELD_MAPPING = {
        # Identificación / nombre
        "nombre": "nombre1",
        "primer nombre": "nombre1",
        "segundo nombre": "nombre2",
        "apellido": "apellido",
        "apellidos": "apellido",
        "primer apellido": "apellido1",
        "segundo apellido": "apellido2",
        "humanos": "id",
        "usuarios": "id",
        "registradas": "id",
        "registrados": "id",
        # Demográfico
        "estrato": "estrato_social",
        "estratos": "estrato_social",
        "nivel socioeconomico": "estrato_social",
        "nivel socioeconómico": "estrato_social",
        "nivel socio economico": "estrato_social",
        "socioeconomico": "estrato_social",
        "nacimiento": "fecha_nacimiento",
        "edad": "fecha_nacimiento",
        "edades": "fecha_nacimiento",
        "años": "fecha_nacimiento",
        "nacieron": "fecha_nacimiento",
        "grupo sanguineo": "grupo_sanguineo_id",
        "grupo sanguíneo": "grupo_sanguineo_id",
        "sexo": "sexo_biologico_id",
        "genero": "identidad_genero_id",
        "género": "identidad_genero_id",
        "identidad de género": "identidad_genero_id",
        "identidad de genero": "identidad_genero_id",
        "orientación sexual": "orientacion_sexual_id",
        "orientacion sexual": "orientacion_sexual_id",
        "grupo étnico": "grupo_etnico_id",
        "grupo etnico": "grupo_etnico_id",
        "etnia": "grupo_etnico_id",
        "lgbt": "pertenencia_lgbti",
        "lgbti": "pertenencia_lgbti",
        "lgbtiq": "pertenencia_lgbti",
        # Poblacional / vulnerabilidad
        "discapacidad": "discapacidad",
        "discapacitado": "discapacidad",
        "discapacitados": "discapacidad",
        "tipo discapacidad": "tipo_discapacidad_id",
        "cuidador": "rol_cuidador",
        "cuidadora": "rol_cuidador",
        "víctima": "victima_conflicto",
        "victima": "victima_conflicto",
        "víctimas": "victima_conflicto",
        "victimas": "victima_conflicto",
        "conflicto": "victima_conflicto",
        "tipo víctima": "tipo_victima_id",
        "tipo victima": "tipo_victima_id",
        "migrante": "migrante",
        "migrantes": "migrante",
        "rural": "poblacion_rural",
        "campo": "poblacion_rural",
        # Hogar
        "personas en hogar": "numero_personas_hogar",
        "habitantes hogar": "numero_personas_hogar",
        # Salud
        "eps": "eps_id",
        "arl": "arl_id",
        "afiliación salud": "afiliacion_salud_id",
        "afiliacion salud": "afiliacion_salud_id",
        "acceso salud": "acceso_servicios_salud_id",
        # Educación / laboral
        "ocupación": "ocupacion_actual_id",
        "ocupacion": "ocupacion_actual_id",
        "oficio": "ocupacion_actual_id",
        "sector económico": "sector_economico_id",
        "sector economico": "sector_economico_id",
        "nivel educativo": "nivel_educativo_id",
        "estudios": "nivel_educativo_id",
        "estudia": "actualmente_estudia",
        "estudiando": "actualmente_estudia",
        "institución": "institucion",
        "institucion": "institucion",
        "colegio": "institucion",
        "universidad": "institucion",
        "ingresos": "ingresos_mensuales",
        "salario": "ingresos_mensuales",
        # Conectividad / dispositivos
        "internet": "acceso_internet",
        "dispositivo": "tipo_dispositivo_id",
        # Vivienda / servicios
        "vivienda": "tipo_vivienda_codigo",
        "construcción": "tipo_construccion_codigo",
        "construccion": "tipo_construccion_codigo",
        "servicios básicos": "servicio_basico_codigo",
        "servicios basicos": "servicio_basico_codigo",
        # Ubicación
        "zona": "zona_codigo",
        "upz": "zona_codigo",
        "upl": "zona_codigo",
        "sector": "zona_codigo",
        "sectores": "zona_codigo",
        "barrio": "zona_codigo",
        "barrios": "zona_codigo",
        "lugar nacimiento": "lugar_nacimiento_codigo",
        "lugar de nacimiento": "lugar_nacimiento_codigo",
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