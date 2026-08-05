"""Licencias y atribución de las fuentes oficiales que sincroniza innovaK.

IDECA, Catastro (UAECD), SED, SCJ, IDU y datos.gov.co publican bajo **CC BY 4.0**:
la atribución es **obligatoria**. Hasta 2026-08-05 solo 1 de 12 fuentes la
declaraba (RUMBO §1.1). Este módulo la declara en un solo sitio, como constante,
para que los comandos de sync —y cualquier vista que reutilice el dato— la citen
igual y sin inventarla.
"""

# clave → (nombre legible, licencia, atribución textual completa)
LICENCIAS = {
    "IDECA": (
        "IDECA — Infraestructura de Datos del Distrito",
        "CC BY 4.0",
        "Datos: Unidad Administrativa Especial de Catastro Distrital (UAECD) / "
        "IDECA — Alcaldía Mayor de Bogotá. Licencia CC BY 4.0.",
    ),
    "CATASTRO": (
        "Catastro Bogotá (UAECD)",
        "CC BY 4.0",
        "Datos: Unidad Administrativa Especial de Catastro Distrital (UAECD) — "
        "Alcaldía Mayor de Bogotá. Licencia CC BY 4.0.",
    ),
    "SED": (
        "Secretaría de Educación del Distrito",
        "CC BY 4.0",
        "Datos: Secretaría de Educación del Distrito (SED) — Alcaldía Mayor de "
        "Bogotá. Licencia CC BY 4.0.",
    ),
    "SCJ": (
        "Secretaría de Seguridad, Convivencia y Justicia",
        "CC BY 4.0",
        "Datos: Secretaría Distrital de Seguridad, Convivencia y Justicia (SCJ) — "
        "Alcaldía Mayor de Bogotá. Licencia CC BY 4.0.",
    ),
    "SECOP": (
        "SECOP II — Colombia Compra Eficiente",
        "Datos Abiertos (datos.gov.co)",
        "Datos: SECOP II / Colombia Compra Eficiente, vía datos.gov.co. CC BY 4.0.",
    ),
    "SDP": (
        "Secretaría Distrital de Planeación",
        "Datos Abiertos (datos.gov.co)",
        "Datos: Secretaría Distrital de Planeación (SDP), vía datos.gov.co. CC BY 4.0.",
    ),
    "IDU": (
        "Instituto de Desarrollo Urbano",
        "CC BY 4.0",
        "Datos: Instituto de Desarrollo Urbano (IDU) — Alcaldía Mayor de Bogotá. "
        "Licencia CC BY 4.0.",
    ),
}


def atribucion(clave: str) -> str:
    """La atribución textual de una fuente, o cadena vacía si no está declarada."""
    entrada = LICENCIAS.get(clave)
    return entrada[2] if entrada else ""


def bloque_atribucion() -> str:
    """Texto multilínea con la atribución de todas las fuentes (para logs/pies)."""
    return "\n".join(f"  · {atrib}" for _n, _lic, atrib in LICENCIAS.values())
