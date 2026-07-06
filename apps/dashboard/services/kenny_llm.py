"""Cerebro conversacional de KENNY (LLM).

Usa un endpoint OpenAI-compatible (por defecto la API de Mistral) para responder
en lenguaje natural como asistente de la Alcaldía Local de Kennedy. El LLM se
llama SOLO desde el backend; la API key nunca llega al navegador.

Config por entorno (.env):
  MISTRAL_API_KEY   — clave del proveedor (obligatoria para activar el LLM).
  MISTRAL_API_URL   — base_url OpenAI-compatible. Default: https://api.mistral.ai/v1
                      (si es self-hosted vLLM/Ollama, apunta a su /v1).
  MISTRAL_MODEL     — id del modelo. Default: mistral-small-latest
                      (para el peso exacto usa 'Mistral-Small-3.2-24B-Instruct-2506').
"""
import logging
import os
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

# ── Knowledge base: KENNY interioriza los docs del proyecto ─────────────
# Se carga una vez (cache de módulo). Restart para refrescar tras editar docs.
_KB_CACHE = None
_KB_LIMITE = 16000        # ~ tope de caracteres de contexto de proyecto
_KB_POR_DOC = 4000        # ~ tope por documento (para que quepan varios)


def _cargar_kb() -> str:
    global _KB_CACHE
    if _KB_CACHE is not None:
        return _KB_CACHE
    try:
        docs = Path(settings.BASE_DIR) / "docs"
        fuentes = [
            docs / "GLOSARIO.md",
            *sorted((docs / "manuales_uso").glob("*.md")),
            *sorted((docs / "manuales_modulos").glob("*.md")),
        ]
        partes, total = [], 0
        for f in fuentes:
            if not f.is_file():
                continue
            try:
                txt = f.read_text(encoding="utf-8")[:_KB_POR_DOC]
            except Exception:
                continue
            if total + len(txt) > _KB_LIMITE:
                txt = txt[: max(0, _KB_LIMITE - total)]
            if not txt:
                break
            partes.append(f"### {f.stem}\n{txt}")
            total += len(txt)
            if total >= _KB_LIMITE:
                break
        _KB_CACHE = "\n\n".join(partes)
    except Exception:
        logger.exception("KENNY: no se pudo cargar el knowledge base")
        _KB_CACHE = ""
    return _KB_CACHE

SYSTEM_PROMPT = (
    "Eres KENNY, el asistente virtual de la Alcaldía Local de Kennedy (Bogotá), "
    "dentro de innovaK, el sistema interno de gestión. Ayudas a los funcionarios "
    "con dos cosas: (1) INTERNO: cómo usar la plataforma y sus módulos "
    "(Presupuesto, Actividades, Mapa de Kennedy, Festivales, Votaciones, "
    "Consulta IA, Administración); (2) EXTERNO: los proyectos de inversión local "
    "que ejecuta la localidad en Cultura, Deporte, Educación y Participación "
    "(cursos, festivales, becas 'Jóvenes a la E', el Banco de Iniciativas "
    "Recreodeportivas, entregas y caracterizaciones). "
    "Responde en español colombiano, breve (2 a 4 frases), amable y claro. "
    "Si te piden CIFRAS de la población atendida (beneficiarios), sugiere usar la "
    "opción 'Consultar datos con IA'. Nunca inventes datos numéricos exactos."
)


def _cfg(name: str, default: str = "") -> str:
    return getattr(settings, name, os.getenv(name, default))


def responder(mensaje: str, usuario=None) -> dict:
    """Devuelve {ok, respuesta} o {ok:False, error}. Nunca lanza."""
    api_key = _cfg("MISTRAL_API_KEY")
    if not api_key:
        return {"ok": False, "error": "no-config"}

    base_url = _cfg("MISTRAL_API_URL", "https://api.mistral.ai/v1")
    model = _cfg("MISTRAL_MODEL", "mistral-small-latest")
    try:
        from openai import OpenAI

        kb = _cargar_kb()
        system = SYSTEM_PROMPT
        if kb:
            system += (
                "\n\nUsa este CONOCIMIENTO DEL PROYECTO (glosario y manuales de "
                "innovaK) para responder con precisión. Si algo no está aquí, dilo "
                "con naturalidad y no lo inventes:\n\n" + kb
            )

        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": (mensaje or "")[:2000]},
            ],
            temperature=0.3,
            max_tokens=500,
        )
        texto = (resp.choices[0].message.content or "").strip()
        if not texto:
            return {"ok": False, "error": "vacio"}
        return {"ok": True, "respuesta": texto}
    except Exception:
        logger.exception("KENNY LLM error (%s)", model)
        return {"ok": False, "error": "llm-error"}
