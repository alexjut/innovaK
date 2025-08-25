# apps/dashboard/services/intent_analyzer.py
import json, os, re
from enum import Enum
from openai import OpenAI
from django.conf import settings
from apps.dashboard.ai_config import AIConfig

class QueryType(Enum):
    COUNT = "count"
    FILTER = "filter"
    UNKNOWN = "unknown"

# ─────────────────────────────
# Fallback con reglas simples
# ─────────────────────────────
_name_word = r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+"
_num_word  = r"\d+"

def _fallback_rules(query: str) -> dict:
    q = (query or "").strip()
    ql = q.lower()

    # 1) ¿Cuántas personas ...?
    if re.search(r"\b(cuantas|cuántas|cuantos|cuántos)\b.*\bpersonas\b", ql):
        conds = []

        # ... estrato 2 / de estrato 2
        m = re.search(r"estrato\s+("+_num_word+")", ql)
        if m:
            conds.append({"field": "estrato_social", "value": m.group(1)})

        # ... con nombre X
        m = re.search(r"(nombre|llam[ao]s?)\s+("+_name_word+")", ql)
        if m:
            conds.append({"field": "nombre_completo", "value": m.group(2)})

        # ... que estudian / con internet / etc. (amplía aquí si quieres)
        if "internet" in ql:
            conds.append({"field": "acceso_internet", "value": True})

        return {
            "type": QueryType.COUNT.value,
            "target_model": "login_persona",
            "conditions": conds,
            "suggested_queries": []
        }

    # 2) personas con nombre X / buscar nombre X
    m = re.search(r"personas?.{0,10}\b(nombre|llam[ao]s?)\s+("+_name_word+")", ql)
    if m:
        return {
            "type": QueryType.FILTER.value,
            "target_model": "login_persona",
            "conditions": [{"field": "nombre_completo", "value": m.group(2)}],
            "suggested_queries": []
        }

    # 3) personas estrato N
    m = re.search(r"personas?.{0,10}\bestrato\s+("+_num_word+")", ql)
    if m:
        return {
            "type": QueryType.FILTER.value,
            "target_model": "login_persona",
            "conditions": [{"field": "estrato_social", "value": m.group(1)}],
            "suggested_queries": []
        }

    # 4) “nombre alexander” suelto o palabra sola: lo tratamos como búsqueda por nombre
    m = re.search(r"\bnombre\s+("+_name_word+")\b", ql)
    if m:
        return {
            "type": QueryType.FILTER.value,
            "target_model": "login_persona",
            "conditions": [{"field": "nombre_completo", "value": m.group(1)}],
            "suggested_queries": []
        }

    if re.fullmatch(_name_word, ql):
        return {
            "type": QueryType.FILTER.value,
            "target_model": "login_persona",
            "conditions": [{"field": "nombre_completo", "value": q}],
            "suggested_queries": []
        }

    return {"type": QueryType.UNKNOWN.value, "target_model": "login_persona", "conditions": [], "suggested_queries": []}

def _generate_model_info() -> str:
    fields = AIConfig.ALLOWED_FIELDS.get("login_persona", [])
    return f"login_persona: {fields}"

def _generate_synonyms() -> str:
    return "\n".join([f'- "{k}" → "{v}"' for k, v in AIConfig.FIELD_MAPPING.items()])

def _coerce_and_whitelist(payload: dict) -> dict:
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
        if field in AIConfig.ALLOWED_FIELDS.get("login_persona", []):
            out["conditions"].append({"field": field, "value": (c or {}).get("value")})
        elif field in ("nombre", "nombre_completo", "persona__nombre"):
            out["conditions"].append({"field": "nombre_completo", "value": (c or {}).get("value")})
    if out["type"] not in (QueryType.COUNT.value, QueryType.FILTER.value):
        out["type"] = QueryType.UNKNOWN.value
    return out

class IntentAnalyzer:
    @staticmethod
    def analyze(query: str) -> dict:
        # 0) Intento con LLM si está disponible
        try:
            models_info = _generate_model_info()
            synonyms = _generate_synonyms()
            prompt = f"""
Devuelve SOLO JSON (sin explicaciones) con:
- "type": "count" | "filter"
- "target_model": SIEMPRE "login_persona"
- "conditions": lista de {{"field","value"}}
- "suggested_queries": lista de strings

Usa ÚNICAMENTE estos campos: 
{models_info}

Sinónimos:
{synonyms}

Ejemplos:
{{"type":"filter","target_model":"login_persona","conditions":[{{"field":"nombre1","value":"ana"}}]}}
{{"type":"count","target_model":"login_persona","conditions":[{{"field":"estrato_social","value":"2"}}]}}

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
                if coerced["type"] in (QueryType.COUNT.value, QueryType.FILTER.value):
                    return coerced
        except Exception:
            # silenciamos; pasamos al fallback
            pass

        # 1) Reglas determinísticas
        fb = _fallback_rules(query)
        return _coerce_and_whitelist(fb)
