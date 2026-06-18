"""Esquema de creación por tipo de evento (data-driven).

El formulario de creación de actividad muestra campos BASE comunes (nombre,
fechas, lugar, subgrupo, descripción, actividad_plan según flag) + los campos
EXTRA propios del tipo, declarados aquí. Agregar un campo a un tipo = una
entrada en este dict, sin tocar Angular (mismo principio que captura_schema,
hub_card, caracterización).

Cada campo: name (= columna de `evento`), label, type (number|text|select|
checkbox|date), required?, catalogo? (opciones dinámicas vía CATALOGOS).
Las columnas referenciadas deben estar en EventoCRUDView._CAMPOS_EDITABLES.
"""

# tipo_evento.codigo -> lista de campos extra
CREACION_SCHEMAS = {
    "CURSO": [
        {"name": "cupo_maximo", "type": "number",
         "label": "Cupo máximo (vacío = sin límite)"},
        {"name": "escuela_id", "type": "select", "catalogo": "escuelas",
         "label": "Escuela / sede donde se dicta"},
    ],
    "FESTIVAL": [
        {"name": "festival_id", "type": "select", "catalogo": "festivales",
         "required": True, "label": "Festival al que pertenece este acto"},
    ],
}


def campos_de(codigo: str) -> list:
    return CREACION_SCHEMAS.get((codigo or "").upper(), [])


def _catalogo(nombre: str) -> list:
    """Opciones dinámicas para los select del esquema."""
    if nombre == "festivales":
        from apps.festivales.models import Festival
        return [{"value": f.id, "label": f"{f.nombre} ({f.vigencia})"}
                for f in Festival.objects.all().order_by("-vigencia", "nombre")]
    if nombre == "escuelas":
        from apps.georeferenciacion.models.models_catalogos import Escuela
        return [{"value": e.id, "label": f"{e.nombre}" + (f" · {e.tipo}" if e.tipo else "")}
                for e in Escuela.objects.filter(activo=True).order_by("nombre")]
    return []


def schema_creacion(codigo: str) -> dict:
    """{fields:[...], catalogos:{nombre:[{value,label}]}} para un tipo."""
    campos = campos_de(codigo)
    catalogos = {}
    for c in campos:
        cat = c.get("catalogo")
        if cat and cat not in catalogos:
            catalogos[cat] = _catalogo(cat)
    return {"fields": campos, "catalogos": catalogos}
