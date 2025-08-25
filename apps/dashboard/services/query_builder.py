# apps/dashboard/services/query_builder.py
from django.db.models import Q
from apps.dashboard.ai_config import AIConfig, get_model
from .intent_analyzer import QueryType

# ──────────────────────────────────────────────────────────────
# Registro mínimo (solo Persona)
# ──────────────────────────────────────────────────────────────
MODEL_KEY = "login_persona"
Persona = get_model(MODEL_KEY)  # apps.login.models.persona.Persona

# ──────────────────────────────────────────────────────────────
# Filtros virtuales
# ──────────────────────────────────────────────────────────────
def build_virtual_filter(field: str, value):
    """
    Campos 'virtuales' que no existen como columna directa pero
    queremos soportar en consultas de texto.
    """
    # nombre_completo: busca en nombre1, nombre2, apellido1, apellido2
    if field in ("nombre", "nombre_completo", "persona__nombre"):
        return (
            Q(nombre1__icontains=value) |
            Q(nombre2__icontains=value) |
            Q(apellido1__icontains=value) |
            Q(apellido2__icontains=value)
        )
    return None


class SafeQueryBuilder:
    @staticmethod
    def build(intent: dict):
        """
        intent esperado (desde tu IntentAnalyzer):
        {
          "type": "count" | "filter",
          "target_model": "login_persona",  # opcional, default persona
          "conditions": [{"field": "nombre1", "value": "ana"}, ...]
        }
        """
        query_type = intent.get("type")
        model_key = intent.get("target_model") or MODEL_KEY
        conditions = intent.get("conditions", [])

        # 1) Modelo fijo: Persona
        if model_key != MODEL_KEY:
            model_key = MODEL_KEY
        model_class = Persona

        # 2) Construir filtros seguros usando Q
        q_objects = Q()
        for cond in conditions:
            raw_field = cond.get("field")
            value = cond.get("value")

            if not raw_field or value is None:
                # si no hay field o value, ignora la condición
                continue

            # Mapear sinónimos -> campo canónico
            field = AIConfig.translate_synonym(raw_field)

            # Validar si el campo es permitido para Persona
            if not AIConfig.is_field_allowed(model_key, field):
                # Permite el virtual 'nombre_completo'
                if field in ("nombre", "nombre_completo", "persona__nombre"):
                    vq = build_virtual_filter(field, value)
                    if vq is not None:
                        q_objects &= vq
                        continue
                raise ValueError(f"El campo '{field}' no está permitido para '{model_key}'")

            # Campo virtual soportado explícitamente
            vq = build_virtual_filter(field, value)
            if vq is not None:
                q_objects &= vq
            else:
                # Por defecto usamos icontains (texto); si llega un bool/int funciona con exact
                # Heurística simple: exact para tipos no-str
                if isinstance(value, (int, float, bool)):
                    q_objects &= Q(**{f"{field}__exact": value})
                else:
                    q_objects &= Q(**{f"{field}__icontains": value})

        # 3) Ejecutar según el tipo
        if query_type == QueryType.COUNT.value:
            return {
                "description": f"Contar Persona con: {conditions}",
                "query": f"{model_class.__name__}.objects.filter({q_objects})",
                "executable": lambda: model_class.objects.filter(q_objects).count(),
            }

        if query_type == QueryType.FILTER.value:
            # Devuelve un subconjunto útil de columnas por defecto
            default_values = ["id", "nombre1", "nombre2", "apellido1", "apellido2", "fecha_nacimiento"]
            return {
                "description": f"Filtrar Persona con: {conditions}",
                "query": f"{model_class.__name__}.objects.filter({q_objects})",
                "executable": lambda: list(model_class.objects.filter(q_objects).values(*default_values)),
            }

        # Tipo no reconocido
        return {
            "description": "Consulta no reconocida",
            "query": "N/A",
            "executable": lambda: [],
        }
