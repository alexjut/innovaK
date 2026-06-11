"""Esquemas de captura por tipo_evento — motor data-driven (Opción A).

Cada entrada define los campos del formulario público de un `tipo_evento`.
El front (Angular) los renderiza con un `@switch(field.type)` (igual que el
wizard de caracterización). Agregar un tipo nuevo de captura = añadir una
entrada aquí; NO requiere DDL ni componente nuevo.

Tipos de campo soportados: text, textarea, number, money, select, checkbox.
`map_to` marca el campo que además se guarda en una columna fija de
`captura_generica` (para búsqueda/matrices/dedup): nombre_legal,
numero_documento, persona_id, organizacion_id.
`options` estáticas inline; `catalogo` para opciones dinámicas (upl, barrio).
"""

SECTOR_CULTURAL = [
    "Música", "Danza", "Teatro", "Artes plásticas y visuales",
    "Audiovisual", "Literatura", "Patrimonio", "Circo", "Otro",
]

ENFOQUE_DIFERENCIAL = [
    "Ninguno", "NARP (afro)", "Indígena", "LGBTIQ+", "Persona con discapacidad",
    "Víctima del conflicto", "Mujer", "Joven", "Adulto mayor",
]


CAPTURA_SCHEMAS = {
    # ── Beneficio a organización (genérico; el área/sector va dentro) ──
    "CULTURA_ORG": {
        "titulo": "Organización beneficiada",
        "icono": "fa-people-group",
        "campos": [
            {"name": "nombre_organizacion", "label": "Nombre de la organización", "type": "text", "required": True, "map_to": "nombre_legal"},
            {"name": "nit", "label": "NIT", "type": "text"},
            {"name": "tipo_organizacion", "label": "Tipo de organización", "type": "select",
             "options": ["Fundación", "Corporación", "Colectivo", "Asociación", "Agrupación", "Otra"]},
            {"name": "sector_cultural", "label": "Sector / área (cultura)", "type": "select", "options": SECTOR_CULTURAL},
            {"name": "representante_nombre", "label": "Representante legal", "type": "text", "required": True},
            {"name": "representante_doc", "label": "Documento del representante", "type": "text", "required": True, "map_to": "numero_documento"},
            {"name": "telefono", "label": "Teléfono", "type": "text"},
            {"name": "correo", "label": "Correo", "type": "text"},
            {"name": "upl", "label": "UPL", "type": "select", "catalogo": "upls"},
            {"name": "barrio", "label": "Barrio", "type": "select", "catalogo": "barrios"},
            {"name": "direccion", "label": "Dirección", "type": "text"},
            {"name": "descripcion_apoyo", "label": "Descripción del apoyo/beneficio", "type": "textarea"},
        ],
    },
    # ── Estímulo otorgado (genérico; disciplina/sector va dentro) ─────
    "ESTIMULO_CULTURAL": {
        "titulo": "Estímulo otorgado",
        "icono": "fa-award",
        "campos": [
            {"name": "tipo_beneficiario", "label": "Tipo de beneficiario", "type": "select", "options": ["Persona", "Organización"], "required": True},
            {"name": "nombre", "label": "Nombre del beneficiario", "type": "text", "required": True, "map_to": "nombre_legal"},
            {"name": "numero_documento", "label": "Documento / NIT", "type": "text", "required": True, "map_to": "numero_documento"},
            {"name": "tipo_estimulo", "label": "Tipo de estímulo", "type": "select", "required": True,
             "options": ["Beca", "Premio", "Pasantía", "Apoyo concertado", "Residencia"]},
            {"name": "disciplina", "label": "Disciplina/modalidad", "type": "select", "options": SECTOR_CULTURAL},
            {"name": "valor_estimulo", "label": "Valor del estímulo", "type": "money"},
            {"name": "enfoque_diferencial", "label": "Enfoque diferencial", "type": "select", "options": ENFOQUE_DIFERENCIAL},
            {"name": "telefono", "label": "Teléfono", "type": "text"},
            {"name": "correo", "label": "Correo", "type": "text"},
            {"name": "upl", "label": "UPL", "type": "select", "catalogo": "upls"},
            {"name": "barrio", "label": "Barrio", "type": "select", "catalogo": "barrios"},
            {"name": "descripcion", "label": "Descripción del estímulo", "type": "textarea"},
        ],
    },
    # ── Proyecto financiado (genérico; línea/sector va dentro) ────────
    "PROYECTO_CULTURAL": {
        "titulo": "Proyecto financiado",
        "icono": "fa-lightbulb",
        "campos": [
            {"name": "nombre_proyecto", "label": "Nombre del proyecto", "type": "text", "required": True, "map_to": "nombre_legal"},
            {"name": "organizacion_proponente", "label": "Organización proponente", "type": "text"},
            {"name": "representante_nombre", "label": "Representante / responsable", "type": "text", "required": True},
            {"name": "representante_doc", "label": "Documento del responsable", "type": "text", "required": True, "map_to": "numero_documento"},
            {"name": "linea", "label": "Línea / sector cultural", "type": "select", "options": SECTOR_CULTURAL},
            {"name": "valor_financiado", "label": "Valor financiado", "type": "money"},
            {"name": "telefono", "label": "Teléfono", "type": "text"},
            {"name": "correo", "label": "Correo", "type": "text"},
            {"name": "upl", "label": "UPL", "type": "select", "catalogo": "upls"},
            {"name": "barrio", "label": "Barrio", "type": "select", "catalogo": "barrios"},
            {"name": "descripcion", "label": "Descripción del proyecto", "type": "textarea", "required": True},
        ],
    },
}


def schema_de(codigo: str) -> dict | None:
    """Devuelve el esquema del tipo, o None si no es un tipo de captura genérica."""
    return CAPTURA_SCHEMAS.get(codigo)
