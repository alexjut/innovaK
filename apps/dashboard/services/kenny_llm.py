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

from django.conf import settings

logger = logging.getLogger(__name__)

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

        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": (mensaje or "")[:2000]},
            ],
            temperature=0.3,
            max_tokens=400,
        )
        texto = (resp.choices[0].message.content or "").strip()
        if not texto:
            return {"ok": False, "error": "vacio"}
        return {"ok": True, "respuesta": texto}
    except Exception:
        logger.exception("KENNY LLM error (%s)", model)
        return {"ok": False, "error": "llm-error"}
