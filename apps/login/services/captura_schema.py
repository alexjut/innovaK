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

# Escala de percepción usada en las preguntas de impacto (secciones III).
CALIFICACION_PERCEPCION = ["Excelente", "Bueno", "Regular", "Malo"]

# Texto de autorización Habeas Data (Ley 1581 de 2012). Va como label del
# checkbox obligatorio: sin marcarlo, el POST llega vacío → 400 (gate legal).
HABEAS_DATA_FESTIVAL = (
    "Autorizo de manera voluntaria y expresa el tratamiento de mis datos "
    "personales con fines estrictamente estadísticos y de análisis del impacto "
    "de los eventos culturales en la localidad de Kennedy. La información será "
    "tratada de manera confidencial conforme a la Ley 1581 de 2012."
)


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
    # ── Percepción del impacto de un festival (encuesta ciudadana) ────
    # UN solo formulario, general para TODOS los festivales presentes y
    # futuros: cada festival es un `evento` de este tipo → su QR sale solo.
    # NO es captura de beneficiarios: es un instrumento de percepción con
    # muchas respuestas por festival, por eso el evento NO cuelga de una
    # actividad-plan (validar una respuesta no suma a ningún KPI). El
    # festival se identifica por el evento (evento.nombre), no por texto
    # libre, para no fragmentar las matrices.
    "PERCEPCION_FESTIVAL": {
        "titulo": "Percepción del impacto del festival",
        "icono": "fa-masks-theater",
        "campos": [
            {"name": "acepta_datos", "label": HABEAS_DATA_FESTIVAL, "type": "checkbox", "required": True},
            # II. Identificación y caracterización
            {"name": "nombre_completo", "label": "Nombre completo", "type": "text", "required": True, "map_to": "nombre_legal"},
            {"name": "numero_documento", "label": "Número de cédula", "type": "text", "required": True, "map_to": "numero_documento"},
            {"name": "telefono", "label": "Número de teléfono", "type": "text"},
            {"name": "genero", "label": "Género", "type": "select", "required": True,
             "options": ["Femenino", "Masculino", "No binario / Otro", "Prefiero no decir"]},
            {"name": "rango_edad", "label": "Rango de edad", "type": "select", "required": True,
             "options": ["18 - 25 años", "26 - 40 años", "41 - 60 años", "Más de 60 años"]},
            {"name": "lugar_residencia", "label": "¿En qué UPZ o barrio de Kennedy reside usted?", "type": "text", "required": True},
            # III. Impacto del festival en la comunidad
            {"name": "impacto_identidad", "label": "Impacto en el fortalecimiento de la identidad cultural de Kennedy", "type": "select", "required": True, "options": CALIFICACION_PERCEPCION},
            {"name": "impacto_integracion", "label": "Capacidad del festival para fomentar la integración y unión entre habitantes", "type": "select", "required": True, "options": CALIFICACION_PERCEPCION},
            {"name": "calidad_programacion", "label": "Calidad de la programación artística y cultural ofrecida", "type": "select", "required": True, "options": CALIFICACION_PERCEPCION},
            {"name": "imagen_positiva", "label": "Impacto para proyectar una imagen positiva de Kennedy hacia la ciudad", "type": "select", "required": True, "options": CALIFICACION_PERCEPCION},
            # IV. Sugerencias y mejoras
            {"name": "aspecto_mejorar", "label": "¿Qué aspecto del festival cree que debería mejorar para futuras versiones?", "type": "text"},
            {"name": "sugerencia_adicional", "label": "¿Alguna sugerencia adicional para que los eventos tengan mayor impacto positivo en la comunidad?", "type": "textarea"},
        ],
    },
}


def schema_de(codigo: str) -> dict | None:
    """Devuelve el esquema del tipo, o None si no es un tipo de captura genérica."""
    return CAPTURA_SCHEMAS.get(codigo)
