# apps/login/context_processors.py
from dataclasses import dataclass
import re

@dataclass(frozen=True)
class Theme:
    dep_id: int
    dep_name: str
    color: str        # primario
    color_dark: str   # encabezados/hover
    color_soft: str   # fondos suaves
    on_color: str     # texto sobre primario

THEMES = {
    1: Theme(1, "Inspecciones de Policía",     "#0EA5E9", "#0284C7", "#E0F2FE", "#FFFFFF"),
    2: Theme(2, "Despacho",                    "#8B5CF6", "#6D28D9", "#EEF2FF", "#FFFFFF"),
    3: Theme(3, "Inversión Local",             "#22C55E", "#16A34A", "#ECFDF5", "#0F172A"),
    4: Theme(4, "Administrativa y Financiera", "#F59E0B", "#D97706", "#FFFBEB", "#0F172A"),
    5: Theme(5, "Gestión Policiva y Jurídica", "#EF4444", "#DC2626", "#FEF2F2", "#FFFFFF"),
}

def _slug(s: str) -> str:
    s = (s or "").strip().lower()
    s = (s.replace("á","a").replace("é","e").replace("í","i")
           .replace("ó","o").replace("ú","u").replace("ñ","n"))
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")

def theme_context(request):
    # Tema por GET -> ?dep=<id>&sub=<nombre>
    try:
        dep_id = int(request.GET.get("dep", "") or 0)
    except ValueError:
        dep_id = 0
    sub = request.GET.get("sub") or ""

    theme = THEMES.get(dep_id, THEMES[4])  # default: Administrativa y Fin.
    # Solo Inversión Local usa logos por subgrupo (los de calle)
    subgrupo_logo = None
    if dep_id == 3 and sub:
        # coloca tus PNG en static/images/subgrupos/<slug>.png
        subgrupo_logo = f"images/subgrupos/{_slug(sub)}.png"

    return {
        "THEME": theme,
        "DEP_ID": theme.dep_id,
        "DEP_NAME": theme.dep_name,
        "SUBGRUPO_NAME": sub,
        "SUBGRUPO_LOGO": subgrupo_logo,
    }
