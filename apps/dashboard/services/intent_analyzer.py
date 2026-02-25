# apps/dashboard/services/intent_analyzer.py
import json, os, re
from enum import Enum
from openai import OpenAI
from django.conf import settings
from apps.dashboard.ai_config import AIConfig

class QueryType(Enum):
    COUNT   = "count"
    FILTER  = "filter"
    GROUP   = "group"    # NUEVO
    TOP     = "top"      # NUEVO
    UNKNOWN = "unknown"

# ─────────────────────────────
# Fallback con reglas simples
# ─────────────────────────────
_name_word = r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+"
_num_word  = r"\d+"

def _fallback_rules(query: str) -> dict:
    q = (query or "").strip()
    ql = q.lower()

    # --- GROUP por campos conocidos (incluye estrato) ---
    if re.search(r"\b(segun|según|por)\b", ql) or \
       re.search(r"\bpersonas?\b.*\b(sexo|identidad|género|genero|etnia|étnic|orientaci[oó]n|eps|estrato)\b", ql):
        mapping = {
            "sexo": "sexo_biologico_id",
            "identidad": "identidad_genero_id",
            "identidad de genero": "identidad_genero_id",
            "identidad de género": "identidad_genero_id",
            "genero": "identidad_genero_id",
            "género": "identidad_genero_id",
            "etnia": "grupo_etnico_id",
            "étnic": "grupo_etnico_id",
            "orientacion": "orientacion_sexual_id",
            "orientación": "orientacion_sexual_id",
            "eps": "eps_id",
            "estrato": "estrato_social",
        }
        target_field = None
        for k, v in mapping.items():
            if k in ql:
                target_field = v; break
        # Solo activamos si el campo está permitido (y por tanto existe)
        if target_field and target_field in AIConfig.ALLOWED_FIELDS.get("login_persona", []):
            return {
                "type": QueryType.GROUP.value,
                "target_model": "login_persona",
                "conditions": [{"field": target_field, "value": "__group_by__"}],
                "suggested_queries": []
            }

    # --- TOP 1 (“más usada / más común”) ---
    if re.search(r"\b(mas usada|más usada|mas comun|más comun|mas común|más común)\b", ql):
        field = "eps_id"
        if "sexo" in ql: field = "sexo_biologico_id"
        if field in AIConfig.ALLOWED_FIELDS.get("login_persona", []):
            return {
                "type": QueryType.TOP.value,
                "target_model": "login_persona",
                "conditions": [{"field": field, "value": "__top__"}],
                "suggested_queries": []
            }

    # --- Totales genéricos ---
    if re.search(r"\b(cuant[ao]s?|cuánt[ao]s?|cantidad|total)\b.*\b(personas|humanos|usuarios)\b", ql):
        return {"type": QueryType.COUNT.value, "target_model": "login_persona", "conditions": [], "suggested_queries": []}

    # --- Primer/segundo nombre ---
    m = re.search(r"(?:personas?\s+con\s+)?(?:primer\s+nombre|nombre1)\s+("+_name_word+")", ql)
    if m:
        return {"type": QueryType.FILTER.value, "target_model": "login_persona",
                "conditions": [{"field": "nombre1", "value": m.group(1)}], "suggested_queries": []}

    m = re.search(r"(?:personas?\s+con\s+)?(?:segundo\s+nombre|nombre2)\s+("+_name_word+")", ql)
    if m:
        return {"type": QueryType.FILTER.value, "target_model": "login_persona",
                "conditions": [{"field": "nombre2", "value": m.group(1)}], "suggested_queries": []}

    # --- Apellido (virtual o específico) ---
    m = re.search(r"(?:personas?\s+con\s+)?(?:apellidos?|apellido1|apellido2)\s+("+_name_word+")", ql)
    if m:
        kw = "apellido"
        if "apellido1" in ql or "primer apellido" in ql: kw = "apellido1"
        if "apellido2" in ql or "segundo apellido" in ql: kw = "apellido2"
        return {"type": QueryType.FILTER.value, "target_model": "login_persona",
                "conditions": [{"field": kw, "value": m.group(1)}], "suggested_queries": []}

    # --- ¿Cuántas personas ...? (extras simples) ---
    if re.search(r"\b(cuantas|cuántas|cuantos|cuántos)\b.*\bpersonas\b", ql):
        conds = []
        m = re.search(r"estrato\s+("+_num_word+")", ql)
        if m: conds.append({"field": "estrato_social", "value": m.group(1)})
        m = re.search(r"(nombre|llam[ao]s?)\s+("+_name_word+")", ql)
        if m: conds.append({"field": "nombre_completo", "value": m.group(2)})
        if "internet" in ql: conds.append({"field": "acceso_internet", "value": True})
        return {"type": QueryType.COUNT.value, "target_model": "login_persona", "conditions": conds, "suggested_queries": []}

    # --- Búsqueda por “nombre …” ---
    m = re.search(r"personas?.{0,10}\b(nombre|llam[ao]s?)\s+("+_name_word+")", ql)
    if m:
        return {"type": QueryType.FILTER.value, "target_model": "login_persona",
                "conditions": [{"field": "nombre_completo", "value": m.group(2)}], "suggested_queries": []}

    m = re.search(r"\bnombre\s+("+_name_word+")\b", ql)
    if m:
        return {"type": QueryType.FILTER.value, "target_model": "login_persona",
                "conditions": [{"field": "nombre_completo", "value": m.group(1)}], "suggested_queries": []}

    if re.fullmatch(_name_word, ql):
        return {"type": QueryType.FILTER.value, "target_model": "login_persona",
                "conditions": [{"field": "nombre_completo", "value": q}], "suggested_queries": []}

    return {"type": QueryType.UNKNOWN.value, "target_model": "login_persona", "conditions": [], "suggested_queries": []}

# ─────────────────────────────
# Helpers para coerción/whitelist
# ─────────────────────────────
def _generate_model_info() -> str:
    fields = AIConfig.ALLOWED_FIELDS.get("login_persona", [])
    return f"login_persona: {fields}"

def _generate_synonyms() -> str:
    return "\n".join([f'- "{k}" → "{v}"' for k, v in AIConfig.FIELD_MAPPING.items()])

def _coerce_and_whitelist(payload: dict) -> dict:
    """
    Traduce sinónimos y filtra campos no permitidos.
    Mantiene COUNT/FILTER/GROUP/TOP si las condiciones son válidas.
    """
    out = {
        "type": payload.get("type", QueryType.UNKNOWN.value),
        "target_model": "login_persona",
        "conditions": [],
        "suggested_queries": payload.get("suggested_queries", []),
    }

    for c in payload.get("conditions", []):
        raw = (c or {}).get("field")
        if not raw:
            continue
        field = AIConfig.translate_synonym(raw)
        value = (c or {}).get("value")

        # Permite marcadores especiales para GROUP/TOP
        if value in ("__group_by__", "__top__"):
            if field in AIConfig.ALLOWED_FIELDS.get("login_persona", []):
                out["conditions"].append({"field": field, "value": value})
            continue

        # virtual nombre
        if field in ("nombre", "nombre_completo", "persona__nombre"):
            out["conditions"].append({"field": "nombre_completo", "value": value})
            continue

        # ⬇️ NUEVO: virtual apellido (apellido1 OR apellido2)
        if field in ("apellido", "apellidos", "persona__apellido"):
            out["conditions"].append({"field": "apellido", "value": value})
            continue

        

        # Solo campos whitelisted
        if field in AIConfig.ALLOWED_FIELDS.get("login_persona", []):
            out["conditions"].append({"field": field, "value": value})

    # Si no es uno de los tipos soportados, márcalo como UNKNOWN
    if out["type"] not in (
        QueryType.COUNT.value,
        QueryType.FILTER.value,
        QueryType.GROUP.value,
        QueryType.TOP.value,
    ):
        out["type"] = QueryType.UNKNOWN.value

    return out

# ─────────────────────────────
# Analizador principal
# ─────────────────────────────
class IntentAnalyzer:
    @staticmethod
    def analyze(query: str) -> dict:
        # 0) Intento con LLM si está disponible (opcional)
        try:
            models_info = _generate_model_info()
            synonyms = _generate_synonyms()
            prompt = f"""
Devuelve SOLO JSON con:
- "type": "count" | "filter" | "group" | "top"
- "target_model": SIEMPRE "login_persona"
- "conditions": lista de {{"field","value"}}
  * Para "group" usa value="__group_by__"
  * Para "top"   usa value="__top__"
- "suggested_queries": lista de strings

Usa ÚNICAMENTE estos campos:
{models_info}

Sinónimos:
{synonyms}

Ejemplos:
{{"type":"filter","target_model":"login_persona","conditions":[{{"field":"nombre1","value":"ana"}}]}}
{{"type":"count","target_model":"login_persona","conditions":[{{"field":"estrato_social","value":"2"}}]}}
{{"type":"group","target_model":"login_persona","conditions":[{{"field":"sexo_biologico_id","value":"__group_by__"}}]}}
{{"type":"top","target_model":"login_persona","conditions":[{{"field":"eps_id","value":"__top__"}}]}}

Pregunta:
"{query}"
"""
            api_key = getattr(settings, "OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
            model_name = getattr(settings, "OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
            if api_key:
                client = OpenAI(api_key=api_key)
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                )
                content = (resp.choices[0].message.content or "").strip()
                if content.startswith("```"):
                    content = content.strip("`")
                    content = content.replace("json", "", 1).strip()
                raw = json.loads(content)
                coerced = _coerce_and_whitelist(raw)
                if coerced["type"] in (
                    QueryType.COUNT.value,
                    QueryType.FILTER.value,
                    QueryType.GROUP.value,
                    QueryType.TOP.value,
                ):
                    return coerced
        except Exception:
            # Silenciamos; pasamos al fallback
            pass

        # 1) Reglas determinísticas
        fb = _fallback_rules(query)
        return _coerce_and_whitelist(fb)
