"""Colores por sector (subgrupo) — fuente única reusable.

El "sector" sale del `subgrupo` (Cultura, Deporte, Mujer, etc.). Este
módulo centraliza la paleta para que el hub de actividades, el mapa geo
y los listados pinten cada sector con el mismo color.

Las claves de `SECTOR_COLORS` son nombres de subgrupo normalizados
(minúsculas, sin tildes). Subgrupos no listados reciben un color
determinístico (hash estable del nombre); subgrupo NULL → gris.
"""
import unicodedata

GRIS_SIN_SECTOR = "#6B7280"

SECTOR_COLORS = {
    "cultura": "#8B5CF6",
    "deporte": "#10B981",
    "mujer": "#EC4899",
    "salud": "#14B8A6",
    "participacion": "#3B82F6",
    "seguridad": "#DC2626",
    "juventud": "#F59E0B",
    "educacion": "#0EA5E9",
}

# Paleta de respaldo determinística para subgrupos fuera del catálogo.
_PALETA_FALLBACK = [
    "#7C3AED", "#059669", "#DB2777", "#0D9488", "#2563EB",
    "#B91C1C", "#D97706", "#0284C7", "#9333EA", "#16A34A",
    "#E11D48", "#0891B2",
]


def _normalizar(nombre):
    base = unicodedata.normalize("NFKD", nombre or "")
    base = "".join(c for c in base if not unicodedata.combining(c))
    return base.strip().lower()


def color_de_sector(nombre):
    """Color hex para un nombre de subgrupo. None → gris 'Sin sector'."""
    if not nombre:
        return GRIS_SIN_SECTOR
    clave = _normalizar(nombre)
    if not clave:
        return GRIS_SIN_SECTOR
    for catalogo, color in SECTOR_COLORS.items():
        if catalogo in clave:
            return color
    idx = sum(ord(c) for c in clave) % len(_PALETA_FALLBACK)
    return _PALETA_FALLBACK[idx]


def color_de_subgrupo_id(subgrupo_id, nombres=None):
    """Color hex desde un id de subgrupo.

    `nombres`: dict {id: nombre} opcional para evitar un query extra.
    Si no se pasa y el id no es None, resuelve el nombre desde BD.
    """
    if subgrupo_id is None:
        return GRIS_SIN_SECTOR
    if nombres is not None:
        return color_de_sector(nombres.get(subgrupo_id))
    from apps.login.models.funcionario import Subgrupo
    nombre = (Subgrupo.objects.filter(pk=subgrupo_id)
              .values_list("nombre", flat=True).first())
    return color_de_sector(nombre)
