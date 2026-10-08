"""Comprueba que Kenny esté encendido, y con qué.

    python manage.py verificar_kenny            # estado + modelos + una prueba
    python manage.py verificar_kenny --sin-prueba
    python manage.py verificar_kenny --modelo openai/gpt-oss-20b

Existe porque encender a Kenny depende de una credencial de un tercero, y
hasta ahora la única forma de saber si quedó bien era abrir la pantalla y
escribirle. Peor: estuvo APAGADO desde julio hasta el 2026-10-08 sin que nadie
lo notara, porque la falta de credencial no dejaba rastro.

Esto responde tres cosas que antes había que adivinar:

  1. ¿Está la credencial? (sin imprimirla nunca)
  2. ¿Qué modelos da ESE proveedor? — se le pregunta a él, en vez de confiar
     en un nombre escrito en un manual que envejece.
  3. ¿Responde de verdad, en cuánto tiempo y con cuántos tokens?

NUNCA imprime la clave. Solo su longitud y sus últimos tres caracteres, que
basta para distinguir «puse la que no era» de «no puse ninguna».
"""
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.dashboard.services.kenny_llm import estado, kb_para


class Command(BaseCommand):
    help = "Verifica la credencial de Kenny, los modelos del proveedor y una respuesta real."

    def add_arguments(self, p):
        p.add_argument("--sin-prueba", action="store_true",
                       help="No gasta una llamada al modelo.")
        p.add_argument("--modelo", default=None,
                       help="Prueba con este modelo en vez del configurado.")
        p.add_argument("--pregunta", default="¿Qué es una meta del Plan de Desarrollo?")

    def handle(self, *a, **o):
        e = estado()
        ok, warn, err = self.style.SUCCESS, self.style.WARNING, self.style.ERROR

        self.stdout.write("\n── 1. La credencial ──")
        clave = getattr(settings, "MISTRAL_API_KEY", "") or ""
        if not clave:
            self.stdout.write(err("  NO HAY credencial. Kenny responde «no-config» a todo."))
            self.stdout.write("  " + (e.get("que_falta") or ""))
            self.stdout.write(warn(
                "\n  Qué hacer, y no es código:\n"
                "    1. Cuenta gratis en console.groq.com (o aistudio.google.com).\n"
                "       No piden tarjeta.\n"
                "    2. Generar una API key.\n"
                "    3. Ponerla en .env y reiniciar el contenedor:\n\n"
                "       MISTRAL_API_KEY=la_clave_que_le_dieron\n"
                "       MISTRAL_API_URL=https://api.groq.com/openai/v1\n"
                "       MISTRAL_MODEL=openai/gpt-oss-20b\n\n"
                "    El nombre de las variables quedó histórico: el cliente es\n"
                "    compatible con OpenAI, así que sirve cualquier proveedor que\n"
                "    lo sea. No hace falta cambiar una línea de código."))
            return
        self.stdout.write(ok(f"  Hay credencial: {len(clave)} caracteres, "
                             f"termina en …{clave[-3:]}"))
        self.stdout.write(f"  Proveedor: {e['url']}")
        self.stdout.write(f"  Modelo configurado: {e['modelo']}")
        self.stdout.write(f"  Conocimiento disponible: {e['conocimiento_caracteres']:,} caracteres")

        self.stdout.write("\n── 2. Los modelos que da ESTE proveedor ──")
        try:
            from openai import OpenAI
            cli = OpenAI(api_key=clave, base_url=e["url"])
            ids = sorted(m.id for m in cli.models.list().data)
            self.stdout.write(ok(f"  {len(ids)} modelos disponibles:"))
            for i in ids[:25]:
                marca = "  <- el configurado" if i == e["modelo"] else ""
                self.stdout.write(f"      {i}{marca}")
            if len(ids) > 25:
                self.stdout.write(f"      … y {len(ids)-25} más")
            if e["modelo"] not in ids:
                self.stdout.write(err(
                    f"\n  OJO: «{e['modelo']}» NO está en la lista. Ponga en "
                    "MISTRAL_MODEL uno de los de arriba y reinicie."))
        except Exception as exc:
            self.stdout.write(err(f"  No se pudo consultar la lista: {type(exc).__name__}"))
            self.stdout.write("  Suele ser la clave equivocada, el proveedor caído, o que "
                              "este contenedor no sale a internet.")
            return

        if o["sin_prueba"]:
            return

        self.stdout.write("\n── 3. Una pregunta de verdad ──")
        pregunta = o["pregunta"]
        kb, elegidos = kb_para(pregunta)
        self.stdout.write(f"  Pregunta: {pregunta}")
        self.stdout.write(f"  Conocimiento que se le manda: {len(kb):,} car. "
                          f"de {', '.join(elegidos) or 'nada'}")
        try:
            from apps.dashboard.services.kenny_llm import SYSTEM_PROMPT
            from openai import OpenAI
            cli = OpenAI(api_key=clave, base_url=e["url"])
            t = time.time()
            r = cli.chat.completions.create(
                model=o["modelo"] or e["modelo"],
                messages=[{"role": "system", "content": SYSTEM_PROMPT + "\n\n" + kb},
                          {"role": "user", "content": pregunta}],
                temperature=0.3, max_tokens=500)
            seg = time.time() - t
            texto = (r.choices[0].message.content or "").strip()
            u = getattr(r, "usage", None)
            self.stdout.write(ok(f"\n  RESPONDIÓ en {seg:.2f} s"))
            if u:
                self.stdout.write(f"  Tokens: {u.prompt_tokens} de entrada + "
                                  f"{u.completion_tokens} de salida = {u.total_tokens}")
                # Con cuota gratuita, esto es lo que de verdad importa saber.
                self.stdout.write(f"  A ese ritmo, 200.000 tokens al día dan "
                                  f"~{200000 // max(u.total_tokens, 1)} preguntas.")
            self.stdout.write("\n  " + (texto[:600] or "(respuesta vacía)"))
            self.stdout.write(ok("\n  Kenny está ENCENDIDO."))
        except Exception as exc:
            self.stdout.write(err(f"  Falló la llamada: {type(exc).__name__}: {exc}"[:300]))
