# apps/dashboard/services/query_builder.py
from django.db.models import Q, Count
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
        return (Q(nombre1__icontains=value) |
                Q(nombre2__icontains=value) |
                Q(apellido1__icontains=value) |
                Q(apellido2__icontains=value))
    # apellido: busca en ambos apellidos
    if field in ("apellido", "apellidos", "persona__apellido"):
        return (Q(apellido1__icontains=value) |
                Q(apellido2__icontains=value))
    return None


class SafeQueryBuilder:
    RELATED_LABELS = {
        "eps_id": "eps__nombre",
        "sexo_biologico_id": "sexo_biologico__nombre",
        "identidad_genero_id": "identidad_genero__nombre",
        "grupo_etnico_id": "grupo_etnico__nombre",
        "orientacion_sexual_id": "orientacion_sexual__nombre",
        "grupo_sanguineo_id": "grupo_sanguineo__nombre",  # si lo tienes
    }

    @staticmethod
    def build(intent: dict, user=None):
        """
        intent esperado:
        {
          "type": "count" | "filter" | "group" | "top",
          "target_model": "login_persona",
          "conditions": [{"field": "nombre1", "value": "ana"}, ...]
            * En "group":  value="__group_by__"
            * En "top":    value="__top__"
        }

        `user` fija el ALCANCE RBAC: un no-superuser solo consulta las personas
        que participaron en eventos de su subgrupo/contrato/curso. Fail-closed:
        sin `user` válido el universo queda vacío (`.none()`), nunca la BD entera.
        """
        query_type = intent.get("type")
        model_key = intent.get("target_model") or MODEL_KEY
        conditions = intent.get("conditions", [])

        # 1) Modelo fijo: Persona
        if model_key != MODEL_KEY:
            model_key = MODEL_KEY
        model_class = Persona

        # 1b) Universo base scopeado. El superuser conserva el universo completo
        #     de Persona (histórico); el resto queda acotado a sus beneficiarios.
        from apps.login.services import scope
        if scope.ve_todo(user):
            base_qs = model_class.objects.all()
        else:
            base_qs = scope.personas_beneficiarias_visibles(user)

        # 2) Construir filtros seguros usando Q
        q_objects = Q()

        # Marcadores especiales para GROUP/TOP
        group_marker = None
        top_marker = None

        for cond in conditions:
            raw_field = cond.get("field")
            value = cond.get("value")

            if not raw_field or value is None:
                continue

            # Mapear sinónimos -> campo canónico
            field = AIConfig.translate_synonym(raw_field)

            # Captura de marcadores especiales
            if value == "__group_by__":
                group_marker = field
                continue
            if value == "__top__":
                top_marker = field
                continue

            # Validar si el campo es permitido para Persona
            if not AIConfig.is_field_allowed(model_key, field):
                # Permite el virtual 'nombre_completo'
                 if field in ("nombre", "nombre_completo", "persona__nombre",
                            "apellido", "apellidos", "persona__apellido"):
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
                if isinstance(value, (int, float, bool)):
                    q_objects &= Q(**{f"{field}__exact": value})
                else:
                    q_objects &= Q(**{f"{field}__icontains": value})

        # 3) Ejecutar según el tipo
        if query_type == QueryType.COUNT.value:
            return {
                "description": f"Contar Persona con: {conditions}",
                "query": f"{model_class.__name__}.objects.filter({q_objects})",
                "executable": lambda: base_qs.filter(q_objects).count(),
            }

        if query_type == QueryType.FILTER.value:
            # Devuelve un subconjunto útil de columnas por defecto
            default_values = ["id", "nombre1", "nombre2", "apellido1", "apellido2", "fecha_nacimiento"]
            return {
                "description": f"Filtrar Persona con: {conditions}",
                "query": f"{model_class.__name__}.objects.filter({q_objects})",
                "executable": lambda: list(base_qs.filter(q_objects).values(*default_values)),
            }

        # GROUP
        if query_type == QueryType.GROUP.value:
            if not group_marker or not AIConfig.is_field_allowed(model_key, group_marker):
                raise ValueError("Campo de agrupación no permitido o no especificado")

            label_field = SafeQueryBuilder.RELATED_LABELS.get(group_marker, group_marker)

            def _label_safe(v):
                if v in (None, "", "None", "null"):
                    return "Sin dato"
                return str(v)

            def exec_group():
                data = (
                    base_qs.filter(q_objects)
                    .values(label_field)
                    .annotate(total=Count("id"))
                    .order_by("-total")
                )[:100]
                return [{"categoria": _label_safe(r.get(label_field)), "total": r.get("total", 0)} for r in data]

            return {
                "description": f"Distribución por {group_marker}",
                "query": f"{model_class.__name__}.objects.filter(...).values('{label_field}').annotate(total=Count('id'))",
                "executable": exec_group,
            }

        # TOP
        if query_type == QueryType.TOP.value:
            if not top_marker or not AIConfig.is_field_allowed(model_key, top_marker):
                raise ValueError("Campo TOP no permitido o no especificado")

            label_field = SafeQueryBuilder.RELATED_LABELS.get(top_marker, top_marker)

            def _label_safe(v):
                if v in (None, "", "None", "null"):
                    return "Sin dato"
                return str(v)

            def exec_top():
                row = (
                    base_qs.filter(q_objects)
                    .values(label_field)
                    .annotate(total=Count("id"))
                    .order_by("-total")
                    .first()
                )
                if not row:
                    return [{"categoria": None, "total": 0}]
                return [{"categoria": _label_safe(row.get(label_field)), "total": row.get("total", 0)}]

            return {
                "description": f"Más común por {top_marker}",
                "query": f"{model_class.__name__}.objects.filter(...).values('{label_field}').annotate(total=Count('id')).order_by('-total')[:1]",
                "executable": exec_top,
            }
        # Tipo no reconocido
        return {
            "description": "Consulta no reconocida",
            "query": "N/A",
            "executable": lambda: [],
        }
