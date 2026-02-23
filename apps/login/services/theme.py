# apps/login/services/theme.py
from dataclasses import dataclass

@dataclass(frozen=True)
class Theme:
    dep_id: int
    dep_slug: str
    dep_name: str
    color: str        # primario
    color_dark: str   # hover / encabezados
    color_soft: str   # chips / fondos suaves
    text_on: str      # texto sobre primario

# Paleta por Dependencia (IDs según tu tabla)
THEMES: dict[int, Theme] = {
    1: Theme(1, "inspecciones", "Inspecciones de Policía", "#0EA5E9", "#0284C7", "#E0F2FE", "#FFFFFF"),
    2: Theme(2, "despacho", "Despacho",                    "#8B5CF6", "#6D28D9", "#EEF2FF", "#FFFFFF"),
    3: Theme(3, "inversion-local", "Inversión Local",      "#22C55E", "#16A34A", "#ECFDF5", "#0F172A"),
    4: Theme(4, "administrativa", "Administrativa y Fin.", "#F59E0B", "#D97706", "#FFFBEB", "#0F172A"),
    5: Theme(5, "juridica", "Gestión Policiva y Jurídica", "#EF4444", "#DC2626", "#FEF2F2", "#FFFFFF"),
}

# Logos por Subgrupo (solo Inversión Local, “los de calle”)
# Coloca los logos en static/img/subgrupos/...
SUBGRUPO_LOGOS: dict[str, str] = {
    # slug -> ruta estática
    "reactivacion-economica":  "img/subgrupos/reactivacion_economica.png",
    "coordinacion-inversion-local": "img/subgrupos/coordinacion_inversion_local.png",
    "infraestructura":         "img/subgrupos/infraestructura.png",
    "seguridad":               "img/subgrupos/seguridad.png",
    "acuerdos-ciudadanos":     "img/subgrupos/acuerdos_ciudadanos.png",
    "mujer":                   "img/subgrupos/mujer.png",
    "paz-memoria-reconciliacion": "img/subgrupos/paz_memoria_reconciliacion.png",
}

import re
def slugify(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u").replace("ñ","n")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")

def get_theme(dep_id: int | None):
    return THEMES.get(dep_id or -1, THEMES[4])  # por defecto admin/fin

def get_subgrupo_logo(dep_id: int | None, subgrupo_nombre: str | None):
    if dep_id != 3:  # solo Inversión Local
        return None
    key = slugify(subgrupo_nombre or "")
    return SUBGRUPO_LOGOS.get(key)
