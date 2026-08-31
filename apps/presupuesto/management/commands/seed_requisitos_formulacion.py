"""Siembra el catálogo de requisitos de formulación (spec 004 §11).

    docker exec innova_k python manage.py seed_requisitos_formulacion            # seco
    docker exec innova_k python manage.py seed_requisitos_formulacion --write

SECO POR DEFECTO, como el resto de comandos del repo tras C3: sin `--write`
imprime qué haría. E IDEMPOTENTE (`update_or_create`): correrlo dos veces no
duplica ni pisa lo que un área haya marcado — sólo toca el catálogo, nunca los
cumplimientos.

LA LISTA NO SE COPIÓ LITERAL, y la razón importa. El §11 del prompt maestro
enumera 24 puntos, pero no todos son requisitos:

  · CUATRO YA SON COLUMNAS de `formulacion` y pedirlos otra vez en un checklist
    sería preguntar dos veces lo mismo: Meta relacionada (se deriva de la
    actividad), Actividad relacionada, Vigencia y Objeto.
  · UNO ya es columna con nombre propio: Presupuesto estimado → `valor_estimado`.
  · TRES SON ESTADOS, no requisitos, y viven en `formulacion_estado`:
    «Observaciones resueltas», «Aprobación» y «Lista para contratación».

Quedan los 16 que sí son requisitos verificables con evidencia.

⚠️ QUÉ FALTA CONFIRMAR CON ALEX: cuáles BLOQUEAN. Acá se marcan tres —estudios
previos, CDP y revisión jurídica— porque son los que ningún proceso puede
saltarse, pero eso es un criterio razonable, NO el proceso institucional
verificado. El plan (§5) dice explícitamente que el catálogo definitivo se fija
después de mirar la normativa de la Alcaldía, no antes.

Y dos requisitos nacen sabiendo que hoy no se pueden llenar solos: PAA y
Apropiación no existen como dato en ninguna parte del sistema (medido en el
diagnóstico). Se dejan en el catálogo porque son parte del proceso real; se
marcarán a mano hasta que haya fuente.
"""
from django.core.management.base import BaseCommand

#: (codigo, nombre, bloque, obligatorio, bloquea, exige_evidencia)
REQUISITOS = [
    # ── Necesidad: por qué se contrata ──
    ("necesidad",       "Necesidad identificada",              "necesidad",  True,  False, False),
    ("alcance",         "Alcance",                             "necesidad",  True,  False, False),
    # ── Técnico: qué se contrata ──
    ("estudios_previos", "Estudios previos",                   "tecnico",    True,  True,  True),
    ("estudio_mercado",  "Estudio de mercado",                 "tecnico",    True,  False, True),
    ("analisis_sector",  "Análisis del sector",                "tecnico",    False, False, True),
    ("especificaciones", "Especificaciones técnicas",          "tecnico",    True,  False, True),
    ("riesgos",          "Riesgos",                            "tecnico",    True,  False, False),
    # ── Financiero: con qué plata ──
    ("fuente_financiacion", "Fuente de financiación",          "financiero", True,  False, False),
    ("paa",              "PAA (Plan Anual de Adquisiciones)",  "financiero", True,  False, True),
    ("apropiacion",      "Apropiación",                        "financiero", True,  False, True),
    ("cdp",              "CDP",                                "financiero", True,  True,  True),
    # ── Contractual: cómo se contrata ──
    ("modalidad",        "Modalidad de selección",             "contractual", True, False, False),
    ("documentos",       "Documentos soporte",                 "contractual", True, False, True),
    # ── Revisiones ──
    ("revision_tecnica",   "Revisión técnica",                 "revision",   True,  False, False),
    ("revision_financiera", "Revisión financiera",             "revision",   True,  False, False),
    ("revision_juridica",  "Revisión jurídica",                "revision",   True,  True,  False),
]


class Command(BaseCommand):
    help = "Siembra el catálogo de requisitos de formulación (seco por defecto)."

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true",
                            help="Escribe de verdad. Sin esto sólo reporta.")

    def handle(self, *args, **opciones):
        from apps.presupuesto.models import RequisitoFormulacion

        escribir = opciones["write"]
        creados = actualizados = iguales = 0

        for orden, (codigo, nombre, bloque, obligatorio, bloquea, evidencia) in enumerate(REQUISITOS, 1):
            campos = {"nombre": nombre, "bloque": bloque, "orden": orden,
                      "obligatorio": obligatorio, "bloquea": bloquea,
                      "exige_evidencia": evidencia, "activo": True}
            actual = RequisitoFormulacion.objects.filter(codigo=codigo).first()
            if actual is None:
                creados += 1
                estado = "CREARÍA" if not escribir else "creado"
            elif any(getattr(actual, k) != v for k, v in campos.items()):
                actualizados += 1
                estado = "ACTUALIZARÍA" if not escribir else "actualizado"
            else:
                iguales += 1
                continue
            marcas = []
            if bloquea:
                marcas.append("BLOQUEA")
            if not obligatorio:
                marcas.append("opcional")
            if evidencia:
                marcas.append("con evidencia")
            self.stdout.write(f"  {estado:14s} {codigo:22s} {nombre:38s} "
                              f"{'· ' + ', '.join(marcas) if marcas else ''}")
            if escribir:
                RequisitoFormulacion.objects.update_or_create(codigo=codigo, defaults=campos)

        self.stdout.write("")
        self.stdout.write(f"  {len(REQUISITOS)} requisitos · nuevos {creados} · "
                          f"cambiados {actualizados} · ya iguales {iguales}")
        if not escribir:
            self.stdout.write(self.style.WARNING(
                "  SECO: no se escribió nada. Corré con --write para aplicarlo."))
