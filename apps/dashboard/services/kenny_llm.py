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
import re
import unicodedata
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

# ── Knowledge base: KENNY interioriza los docs del proyecto ─────────────
#
# ## Por qué se eligen los documentos por pregunta y no se mandan todos
#
# Hasta el 2026-10-08 esto concatenaba GLOSARIO + manuales_uso + manuales_modulos
# en ORDEN ALFABÉTICO hasta llenar 16.000 caracteres, y los mandaba enteros en
# cada pregunta. Dos problemas, y el segundo es peor que el primero:
#
# 1. **Coste y cuota.** Los 16.000 caracteres son ~4.300 tokens, el 85 % de la
#    entrada de cada pregunta. Con un proveedor de pago da igual —medido: USD
#    0,0011 por pregunta—, pero con una cuota gratuita es lo que decide cuántas
#    preguntas se pueden responder al día: 35 con la base completa contra ~110
#    recortada.
#
# 2. **Había documentos que NUNCA llegaban.** Medido: de los 9 disponibles solo
#    6 entraban, y los 3 que se caían eran `festivales`, `infraestructura` y
#    `mapa` — por la F, la I y la M del alfabeto, no por ser menos útiles. A
#    quien preguntara por el mapa, Kenny le respondía sin tener una línea sobre
#    el mapa. Eso no se notaba porque Kenny contestaba igual.
#
# Ahora se eligen los documentos que la pregunta necesita. El glosario entra
# siempre, porque define el vocabulario con el que está escrito todo lo demás.
_DOCS_CACHE = None

#: Tope por documento al cargarlo. Los manuales son largos y su parte útil está
#: al principio.
_KB_POR_DOC = 4000
#: Lo que se le manda al modelo por pregunta. Más chico que el tope viejo de
#: 16.000 a propósito: ver el punto 1 de arriba.
_KB_LIMITE = 5000
#: El glosario siempre entra, pero no se come el presupuesto entero.
_KB_GLOSARIO = 1800

_PALABRA = re.compile(r"[a-z0-9ñ]{4,}")
#: Palabras que aparecen en toda pregunta y no distinguen un documento de otro.
_VACIAS = frozenset("""
como cual cuales cuando donde quien quienes para pero porque este esta esto
estos estas sobre entre desde hasta tiene tienen hacer puedo puede pueden
quiero necesito ayuda favor gracias usted ustedes nosotros tambien solo
mismo misma mucho mucha algun alguna todos todas cosa cosas parte partes
""".split())


def _sin_tildes(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", t.lower())
                   if not unicodedata.combining(c))


def _documentos() -> list[tuple[str, str]]:
    """[(nombre, texto)] de todos los documentos, cargados una vez.

    Cache de módulo: hay que reiniciar para refrescar tras editar los docs.
    """
    global _DOCS_CACHE
    if _DOCS_CACHE is not None:
        return _DOCS_CACHE
    salida: list[tuple[str, str]] = []
    try:
        docs = Path(settings.BASE_DIR) / "docs"
        fuentes = [
            docs / "GLOSARIO.md",
            *sorted((docs / "manuales_uso").glob("*.md")),
            *sorted((docs / "manuales_modulos").glob("*.md")),
        ]
        for f in fuentes:
            if not f.is_file():
                continue
            try:
                txt = f.read_text(encoding="utf-8")[:_KB_POR_DOC]
            except Exception:
                continue
            if txt:
                # El nombre de la carpeta desambigua: hay dos README.
                salida.append((f"{f.parent.name}/{f.stem}", txt))
    except Exception:
        logger.exception("KENNY: no se pudieron cargar los documentos")
    _DOCS_CACHE = salida
    return salida


def _puntuar(nombre: str, texto: str, palabras: set[str]) -> int:
    """Cuánto tiene que ver un documento con la pregunta.

    Conteo de palabras, no vectores: no hay dependencia que instalar, corre en
    microsegundos y —lo que importa en este proyecto— se puede explicar. Si
    alguien pregunta por qué Kenny no sabía algo, la respuesta es una cuenta
    que se puede repetir a mano, no un espacio de embeddings.
    """
    n = _sin_tildes(nombre)
    t = _sin_tildes(texto)
    puntos = 0
    for w in palabras:
        # El nombre del documento pesa más que una mención en el cuerpo: que la
        # pregunta diga «festivales» y exista el manual de festivales es la
        # señal más fuerte que hay.
        if w in n:
            puntos += 20
        puntos += min(t.count(w), 8)
    return puntos


def kb_para(pregunta: str) -> tuple[str, list[str]]:
    """El conocimiento que ESTA pregunta necesita, y de qué documentos salió.

    Devuelve el texto y la lista de documentos elegidos. La lista se registra:
    sin ella, «Kenny no supo responder» no se puede diagnosticar.
    """
    docs = _documentos()
    if not docs:
        return "", []

    palabras = {w for w in _PALABRA.findall(_sin_tildes(pregunta or ""))
                if w not in _VACIAS}

    glosario = next((d for d in docs if d[0].endswith("GLOSARIO")), None)
    resto = [d for d in docs if d is not glosario]

    partes, elegidos, total = [], [], 0
    # El glosario siempre: define el vocabulario de todo lo demás.
    if glosario:
        trozo = glosario[1][:_KB_GLOSARIO]
        partes.append(f"### {glosario[0]}\n{trozo}")
        elegidos.append(glosario[0])
        total += len(trozo)

    # Sin palabras útiles en la pregunta no hay de qué elegir: se cae al orden
    # de siempre, que al menos es estable y reproducible.
    puntuados = (sorted(resto, key=lambda d: -_puntuar(d[0], d[1], palabras))
                 if palabras else resto)

    for nombre, texto in puntuados:
        if total >= _KB_LIMITE:
            break
        trozo = texto[: _KB_LIMITE - total]
        if not trozo:
            break
        partes.append(f"### {nombre}\n{trozo}")
        elegidos.append(nombre)
        total += len(trozo)

    return "\n\n".join(partes), elegidos


def _cargar_kb() -> str:
    """TODO el conocimiento, sin elegir. Se conserva para `estado()`.

    `estado()` lo usa para decir cuántos caracteres hay disponibles, que es lo
    que distingue «falta la credencial» de «faltan los documentos». Para
    responder una pregunta se usa `kb_para()`, que elige.
    """
    return "\n\n".join(f"### {n}\n{t}" for n, t in _documentos())


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


#: Para que el aviso de «apagado» salga UNA vez por proceso y no en cada
#: pulsación: un log por mensaje del usuario sería ruido y se perdería igual.
_AVISO_APAGADO_DADO = False


def estado() -> dict:
    """¿Está Kenny encendido? Se puede preguntar SIN gastar una llamada al LLM.

    Existe porque el asistente estuvo APAGADO desde julio y nadie se enteró
    hasta el 2026-10-08. El defecto no era la falta de credencial —eso es un
    trámite— sino que la falta de credencial **no se veía**: `responder()`
    devolvía `{"ok": False, "error": "no-config"}` sin escribir una sola línea
    de registro, el endpoint contestaba 200, y la interfaz caía al menú de
    siempre. Un asistente mudo y un asistente apagado se ven igual.

    Ahora el estado es consultable, y la pantalla puede decir «Kenny está
    apagado: falta la credencial» en vez de disimularlo.
    """
    api_key = _cfg("MISTRAL_API_KEY")
    url = _cfg("MISTRAL_API_URL", "https://api.mistral.ai/v1")
    model = _cfg("MISTRAL_MODEL", "mistral-small-latest")
    if not api_key:
        return {
            "activo": False,
            "motivo": "falta_credencial",
            # Lo que hay que hacer, escrito acá para que no haya que buscarlo.
            "que_falta": (
                "No hay `MISTRAL_API_KEY`. Es una credencial del proveedor del "
                "modelo, no un cambio de código: se pone en `.env` y se "
                "reinicia el contenedor. `MISTRAL_API_URL` y `MISTRAL_MODEL` "
                "son opcionales y ya tienen valor por defecto."),
            "url": url, "modelo": model,
            # El tamaño de la base de conocimiento SÍ se puede medir sin clave:
            # dice si el problema es solo la credencial o también los docs.
            "conocimiento_caracteres": len(_cargar_kb()),
        }
    return {
        "activo": True, "motivo": None, "que_falta": None,
        "url": url, "modelo": model,
        "conocimiento_caracteres": len(_cargar_kb()),
    }


def responder(mensaje: str, usuario=None) -> dict:
    """Devuelve {ok, respuesta} o {ok:False, error}. Nunca lanza."""
    global _AVISO_APAGADO_DADO
    api_key = _cfg("MISTRAL_API_KEY")
    if not api_key:
        # SE REGISTRA, y antes no. Esta rama devolvía el dict y se iba en
        # silencio: por eso el asistente pudo estar apagado tres meses sin que
        # nadie lo notara. Un WARNING una vez por proceso no es ruido, es la
        # diferencia entre un sistema callado y un sistema roto.
        if not _AVISO_APAGADO_DADO:
            logger.warning(
                "KENNY APAGADO: falta MISTRAL_API_KEY. El asistente responde "
                "`no-config` a todo y la interfaz cae al menú. Es una "
                "credencial en .env + reinicio, no un cambio de código.")
            _AVISO_APAGADO_DADO = True
        return {"ok": False, "error": "no-config",
                "motivo": "falta_credencial",
                "detalle": estado()["que_falta"]}

    base_url = _cfg("MISTRAL_API_URL", "https://api.mistral.ai/v1")
    model = _cfg("MISTRAL_MODEL", "mistral-small-latest")
    try:
        from openai import OpenAI

        kb, elegidos = kb_para(mensaje)
        # Se registra QUÉ documentos se le dieron. Sin esto, «Kenny no supo
        # responder» no se puede diagnosticar: no se sabría si le faltó el
        # documento o si lo tenía y no lo usó.
        logger.info("KENNY kb: %d car. de %s", len(kb), ", ".join(elegidos) or "nada")
        from apps.dashboard.services.uso_ia import registrar
        registrar("kenny", mensaje, "respondido",
                  extra=f"docs={len(elegidos)} kb={len(kb)}")
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
