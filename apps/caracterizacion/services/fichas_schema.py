"""Esquemas data-driven de las fichas INTERNAS de caracterización.

A diferencia del motor público (`apps.login.services.captura_schema`,
manejado por `tipo_evento`), estas fichas las llena el equipo del área
desde el panel autenticado y se indexan por (sector, target).

Agregar una ficha nueva = una entrada en `FICHAS[sector][target]`. Los
campos `select` con `catalogo` resuelven sus opciones contra `CATALOGOS`
(ver `cargar_catalogos`). Sin DDL: todo lo capturado vive en `datos` JSONB
de `captura_generica`.

Tipos de campo: text, textarea, number, date, select, checkbox, file.
"""

# Registro de catálogos: nombre lógico → (tabla, columna valor, columna label).
# Las columnas NO son uniformes en la BD (eps/grupo_sanguineo difieren).
CATALOGOS = {
    "tipos_documento":   ("tipo_documento", "codigo", "nombre"),
    "sexos":             ("sexo", "codigo", "nombre"),
    "grupos_etarios":    ("grupo_etario", "codigo", "nombre"),
    "identidades_genero": ("identidad_genero", "codigo", "nombre"),
    "orientaciones":     ("orientacion_sexual", "codigo", "nombre"),
    "etnias":            ("grupo_etnico", "codigo", "nombre"),
    "tipos_discapacidad": ("tipo_discapacidad", "codigo", "nombre"),
    "tipos_victima":     ("tipo_victima", "codigo", "nombre"),
    "niveles_educativos": ("nivel_educativo", "codigo", "nombre"),
    "eps":               ("eps", "id", "nombre"),
    "grupos_sanguineos": ("grupo_sanguineo", "id", "tipo"),
    "upzs":              ("upz", "codigo", "nombre"),
    "tipos_organizacion": ("tipo_organizacion", "codigo", "nombre"),
}


# Campos generales de las 3 fichas — compartidos por TODOS los sectores.
# Cada sector reusa estas definiciones y solo cambia titulo + tipo_codigo
# (ver `_construir_fichas`).
_CAMPOS_INDIVIDUO = [
        # ── Identificación ──────────────────────────────────────────
        {"name": "tipo_documento", "label": "Tipo de documento", "type": "select",
         "catalogo": "tipos_documento", "required": True, "grupo": "Identificación"},
        {"name": "numero_documento", "label": "Número de documento", "type": "text",
         "required": True, "map_to": "numero_documento", "grupo": "Identificación"},
        {"name": "nombre1", "label": "Primer nombre", "type": "text",
         "required": True, "grupo": "Identificación"},
        {"name": "nombre2", "label": "Segundo nombre", "type": "text",
         "grupo": "Identificación"},
        {"name": "apellido1", "label": "Primer apellido", "type": "text",
         "required": True, "grupo": "Identificación"},
        {"name": "apellido2", "label": "Segundo apellido", "type": "text",
         "grupo": "Identificación"},
        {"name": "fecha_nacimiento", "label": "Fecha de nacimiento", "type": "date",
         "required": True, "grupo": "Identificación"},

        # ── Demográfico ─────────────────────────────────────────────
        {"name": "sexo", "label": "Sexo", "type": "select",
         "catalogo": "sexos", "grupo": "Demográfico"},
        {"name": "grupo_etario", "label": "Grupo etario", "type": "select",
         "catalogo": "grupos_etarios", "grupo": "Demográfico"},
        {"name": "identidad_genero", "label": "Identidad de género", "type": "select",
         "catalogo": "identidades_genero", "grupo": "Demográfico"},
        {"name": "orientacion_sexual", "label": "Orientación sexual", "type": "select",
         "catalogo": "orientaciones", "grupo": "Demográfico"},
        {"name": "grupo_etnico", "label": "Grupo étnico", "type": "select",
         "catalogo": "etnias", "grupo": "Demográfico"},
        {"name": "discapacidad", "label": "¿Presenta discapacidad?", "type": "checkbox",
         "grupo": "Demográfico"},
        {"name": "tipo_discapacidad", "label": "Tipo de discapacidad", "type": "select",
         "catalogo": "tipos_discapacidad", "grupo": "Demográfico"},
        {"name": "rol_cuidador", "label": "¿Rol de cuidador?", "type": "checkbox",
         "grupo": "Demográfico"},
        {"name": "victima_conflicto", "label": "¿Víctima del conflicto?", "type": "checkbox",
         "grupo": "Demográfico"},
        {"name": "tipo_victima", "label": "Tipo de víctima", "type": "select",
         "catalogo": "tipos_victima", "grupo": "Demográfico"},
        {"name": "madre_cabeza", "label": "¿Madre cabeza de hogar?", "type": "checkbox",
         "grupo": "Demográfico"},
        {"name": "habitante_calle", "label": "¿Habitante de calle?", "type": "checkbox",
         "grupo": "Demográfico"},
        {"name": "nivel_educativo", "label": "Nivel educativo", "type": "select",
         "catalogo": "niveles_educativos", "grupo": "Demográfico"},
        {"name": "eps", "label": "EPS", "type": "select",
         "catalogo": "eps", "grupo": "Demográfico"},
        {"name": "grupo_sanguineo", "label": "Grupo sanguíneo", "type": "select",
         "catalogo": "grupos_sanguineos", "grupo": "Demográfico"},

        # ── Contacto y territorio ───────────────────────────────────
        {"name": "correo", "label": "Correo electrónico", "type": "text",
         "grupo": "Contacto y territorio"},
        {"name": "telefono", "label": "Teléfono", "type": "text",
         "grupo": "Contacto y territorio"},
        {"name": "direccion", "label": "Dirección", "type": "text",
         "grupo": "Contacto y territorio"},
        {"name": "complemento", "label": "Complemento de dirección", "type": "text",
         "grupo": "Contacto y territorio"},
        {"name": "upz", "label": "UPZ", "type": "select",
         "catalogo": "upzs", "grupo": "Contacto y territorio"},
        {"name": "sector_catastral", "label": "Sector catastral", "type": "text",
         "grupo": "Contacto y territorio"},

        # ── Pertenencia ─────────────────────────────────────────────
        {"name": "nombre_organizacion", "label": "Nombre de la organización", "type": "text",
         "grupo": "Pertenencia"},

        # ── Documentos ──────────────────────────────────────────────
        {"name": "documento_identidad", "label": "Documento de identidad", "type": "file",
         "grupo": "Documentos"},
        {"name": "certificado_eps", "label": "Certificado de EPS", "type": "file",
         "grupo": "Documentos"},
        {"name": "recibo_publico", "label": "Recibo de servicio público", "type": "file",
         "grupo": "Documentos"},
        {"name": "documento_acudiente", "label": "Documento del acudiente", "type": "file",
         "grupo": "Documentos"},
        {"name": "consentimiento", "label": "Consentimiento informado", "type": "file",
         "grupo": "Documentos"},

        # ── Cierre ──────────────────────────────────────────────────
        {"name": "observaciones", "label": "Observaciones", "type": "textarea",
         "grupo": "Cierre"},
]


_CAMPOS_ORGANIZACION = [
        {"name": "nombre", "label": "Nombre de la organización", "type": "text",
         "required": True, "map_to": "nombre_legal", "grupo": "Identificación"},
        {"name": "nit", "label": "NIT", "type": "text",
         "map_to": "numero_documento", "grupo": "Identificación"},
        {"name": "tipo_organizacion", "label": "Tipo de organización", "type": "select",
         "catalogo": "tipos_organizacion", "grupo": "Identificación"},
        {"name": "direccion", "label": "Dirección", "type": "text", "grupo": "Contacto"},
        {"name": "upz", "label": "UPZ", "type": "select", "catalogo": "upzs", "grupo": "Contacto"},
        {"name": "contacto", "label": "Persona de contacto", "type": "text", "grupo": "Contacto"},
        {"name": "telefono", "label": "Teléfono", "type": "text", "grupo": "Contacto"},
        {"name": "correo", "label": "Correo electrónico", "type": "text", "grupo": "Contacto"},
        {"name": "observaciones", "label": "Observaciones", "type": "textarea", "grupo": "Cierre"},
]

_CAMPOS_LUGAR = [
        {"name": "contratista", "label": "Contratista", "type": "text", "grupo": "Contratista"},
        {"name": "nit_contratista", "label": "NIT del contratista", "type": "text", "grupo": "Contratista"},
        {"name": "tipo_intervencion", "label": "Tipo de intervención", "type": "text", "grupo": "Intervención"},
        {"name": "fecha_realizacion", "label": "Fecha de realización", "type": "date", "grupo": "Intervención"},
        {"name": "realizada_por_colectivo", "label": "Realizada por (colectivo)", "type": "text", "grupo": "Intervención"},
        {"name": "n_personas_capacitadas", "label": "N° de personas capacitadas", "type": "number", "grupo": "Intervención"},
        {"name": "valor_por_espacio", "label": "Valor por espacio", "type": "number", "grupo": "Intervención"},
        {"name": "direccion", "label": "Dirección", "type": "text",
         "required": True, "map_to": "nombre_legal", "grupo": "Ubicación"},
        {"name": "codigo_identificacion", "label": "Código de identificación", "type": "text", "grupo": "Ubicación"},
        {"name": "upz", "label": "UPZ", "type": "select", "catalogo": "upzs", "grupo": "Ubicación"},
        {"name": "detalle_elementos", "label": "Detalle de elementos entregados", "type": "textarea", "grupo": "Elementos"},
        {"name": "observaciones", "label": "Observaciones", "type": "textarea", "grupo": "Cierre"},
]


# Definición por target: (target lógico, target de captura, campos compartidos).
_TARGETS = {
    "individuo":    ("persona",      _CAMPOS_INDIVIDUO),
    "organizacion": ("organizacion", _CAMPOS_ORGANIZACION),
    "lugar":        ("lugar",        _CAMPOS_LUGAR),
}

# Sectores con fichas internas → etiqueta humana usada en el título.
# tipo_codigo resultante: CARACT_<SECTOR>_<TARGET> (en mayúsculas).
# IMPORTANTE: cultura conserva sus tipo_codigo históricos exactos
# (CARACT_CULTURA_*) porque ya hay datos capturados con esas claves.
_SECTORES_FICHAS = {
    "cultura":   "Cultura",
    "seguridad": "Seguridad",
}


def _construir_fichas() -> dict:
    """Genera FICHAS[sector][target] reusando los campos generales.

    Cada (sector, target) comparte exactamente los mismos campos; solo
    difieren el `titulo` y el `tipo_codigo` (CARACT_<SECTOR>_<TARGET>).
    """
    fichas = {}
    for sector, label in _SECTORES_FICHAS.items():
        fichas[sector] = {}
        for target, (target_captura, campos) in _TARGETS.items():
            fichas[sector][target] = {
                "titulo": f"Ficha de caracterización — {target.capitalize()} ({label})",
                "target": target_captura,
                "tipo_codigo": f"CARACT_{sector.upper()}_{target.upper()}",
                "campos": campos,
            }
    return fichas


FICHAS = _construir_fichas()

# Targets reconocidos por el contrato del endpoint, aunque no tengan ficha.
TARGETS_VALIDOS = ("individuo", "organizacion", "lugar")


def ficha_de(sector: str, target: str):
    """Devuelve el esquema de la ficha (sector, target), o None."""
    return (FICHAS.get(sector) or {}).get(target)


def campos_file(esquema) -> list:
    """Nombres de los campos `file` del esquema."""
    return [c["name"] for c in esquema["campos"] if c["type"] == "file"]


def campos_checkbox(esquema) -> set:
    """Nombres de los campos `checkbox` del esquema."""
    return {c["name"] for c in esquema["campos"] if c["type"] == "checkbox"}
