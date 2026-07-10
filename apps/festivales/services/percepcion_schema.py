"""Cuestionario de percepción del festival — motor data-driven.

UN solo cuestionario, general para todos los festivales. El front (Angular)
lo renderiza con `@switch(field.type)` (igual que la captura genérica y la
caracterización). Cambiar las preguntas = editar este dict; sin DDL.

Tipos de campo: text, textarea, select, checkbox.
`map_to` marca el campo que además se guarda en columna fija de
`festival_percepcion` (numero_documento / nombre) para búsqueda y dedup.
"""

CALIFICACION = ["Excelente", "Bueno", "Regular", "Malo"]

# Autorización Habeas Data (Ley 1581 de 2012). Va como label del checkbox
# obligatorio: sin marcarlo, el POST llega vacío → 400 (gate legal).
HABEAS_DATA = (
    "Autorizo de manera voluntaria y expresa el tratamiento de mis datos "
    "personales con fines estrictamente estadísticos y de análisis del impacto "
    "de los eventos culturales en la localidad de Kennedy. La información será "
    "tratada de manera confidencial conforme a la Ley 1581 de 2012."
)

PERCEPCION_SCHEMA = {
    "titulo": "Percepción del impacto del festival",
    "objetivo": (
        "Conocer la percepción de los ciudadanos sobre el impacto cultural, "
        "social y de identidad que generan los festivales de Kennedy."
    ),
    "campos": [
        {"name": "acepta_datos", "label": HABEAS_DATA, "type": "checkbox", "required": True},
        # II. Identificación y caracterización
        {"name": "nombre_completo", "label": "Nombre completo", "type": "text", "required": True, "map_to": "nombre"},
        {"name": "numero_documento", "label": "Número de cédula", "type": "text", "required": True, "map_to": "numero_documento"},
        {"name": "telefono", "label": "Número de teléfono", "type": "text"},
        {"name": "genero", "label": "Género", "type": "select", "required": True,
         "options": ["Femenino", "Masculino", "No binario / Otro", "Prefiero no decir"]},
        {"name": "rango_edad", "label": "Rango de edad", "type": "select", "required": True,
         "options": ["18 - 25 años", "26 - 40 años", "41 - 60 años", "Más de 60 años"]},
        {"name": "lugar_residencia", "label": "¿En qué UPZ o barrio de Kennedy reside usted?", "type": "text", "required": True},
        # III. Impacto del festival en la comunidad
        {"name": "impacto_identidad", "label": "Impacto en el fortalecimiento de la identidad cultural de Kennedy", "type": "select", "required": True, "options": CALIFICACION},
        {"name": "impacto_integracion", "label": "Capacidad del festival para fomentar la integración y unión entre habitantes", "type": "select", "required": True, "options": CALIFICACION},
        {"name": "calidad_programacion", "label": "Calidad de la programación artística y cultural ofrecida", "type": "select", "required": True, "options": CALIFICACION},
        {"name": "imagen_positiva", "label": "Impacto para proyectar una imagen positiva de Kennedy hacia la ciudad", "type": "select", "required": True, "options": CALIFICACION},
        # IV. Sugerencias y mejoras
        {"name": "aspecto_mejorar", "label": "¿Qué aspecto del festival cree que debería mejorar para futuras versiones?", "type": "text"},
        {"name": "sugerencia_adicional", "label": "¿Alguna sugerencia adicional para que los eventos tengan mayor impacto positivo en la comunidad?", "type": "textarea"},
    ],
}

# Preguntas de calificación (select con la escala) — para el insight.
PREGUNTAS_CALIFICACION = [
    c["name"] for c in PERCEPCION_SCHEMA["campos"]
    if c["type"] == "select" and c.get("options") == CALIFICACION
]
