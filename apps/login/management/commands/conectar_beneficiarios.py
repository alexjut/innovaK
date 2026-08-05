"""Conecta los dos universos de personas que nunca se cruzaron.

## El problema que resuelve

Al auditar la cadena el 2026-08-05 apareció esto:

    participante            2.693 personas inscritas a eventos
    beneficiario            3.605 "atendidos"
    intersección                0     ← ni una sola fila en común

Son dos cargas independientes. `Beneficiario` es el universo único de
atendidos y lo alimentan los flujos de becas, entregas, caracterización y
banco… pero **el único flujo que captura gente de verdad —la inscripción a
eventos— nunca lo llamaba**. Y en `contrato_beneficiario` (2.950 filas, la
tabla que dice qué contrato atendió a quién) la columna `beneficiario_id`
estaba **100 % NULL**: el vínculo real era texto libre por número de documento.

El resultado visible era un tablero que mostraba **0 beneficiarios** y que se
leyó durante meses como "no hay datos capturados", cuando lo que había era
2.545 inscripciones sin conectar.

## Los dos backfills

`--paso contratos` — `contrato_beneficiario.beneficiario_id` desde
`numero_documento`. Verificado antes de escribir una sola fila: los 2.892
documentos distintos cruzan uno a uno con `beneficiario`, y **ningún documento
tiene dos beneficiarios**, así que no hay ambigüedad que resolver.

`--paso participantes` — crea el `Beneficiario` que falta para cada persona
inscrita a un evento, con el mismo helper idempotente que usan los otros
flujos (`asegurar_beneficiario_persona`). No inventa datos: si la persona no
tiene documento registrado, el helper devuelve `None` y acá se cuenta aparte
en vez de fabricar un beneficiario a medias.

## Uso

    python manage.py conectar_beneficiarios              # seco, ambos pasos
    python manage.py conectar_beneficiarios --write      # persiste
    python manage.py conectar_beneficiarios --paso contratos --write

Seco por defecto (`--write` para escribir), que es el patrón de `sync_capa` y
`asignar_estrato_sedes`. Idempotente: re-correrlo no duplica nada.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import connection, transaction


class Command(BaseCommand):
    help = "Conecta participantes y contratos con el universo `beneficiario`."

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true",
                            help="Persiste los cambios (default: seco).")
        parser.add_argument("--paso", default="ambos",
                            choices=["ambos", "contratos", "participantes"])
        parser.add_argument("--limite", type=int, default=0,
                            help="Máximo de personas a procesar (0 = todas).")

    def handle(self, *args, **opts):
        self.write_mode = opts["write"]
        if opts["paso"] in ("ambos", "contratos"):
            self._paso_contratos()
        if opts["paso"] in ("ambos", "participantes"):
            self._paso_participantes(opts["limite"])

        self.stdout.write("")
        if self.write_mode:
            self.stdout.write(self.style.SUCCESS("ESCRITO."))
        else:
            self.stdout.write(self.style.WARNING(
                "SECO: no se escribió nada. Usa --write para persistir."))

    # ── Paso 1 · contrato_beneficiario.beneficiario_id ───────────────────
    def _paso_contratos(self):
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n1. contrato_beneficiario.beneficiario_id"))

        with connection.cursor() as cur:
            cur.execute("""
                SELECT count(*),
                       count(beneficiario_id),
                       count(*) FILTER (WHERE beneficiario_id IS NULL
                                          AND numero_documento IS NOT NULL)
                FROM contrato_beneficiario
            """)
            total, con_id, candidatas = cur.fetchone()

            # Cuántas de las candidatas cruzan de verdad, y si alguna es ambigua.
            cur.execute("""
                SELECT count(*) FROM contrato_beneficiario cb
                WHERE cb.beneficiario_id IS NULL
                  AND EXISTS (SELECT 1 FROM beneficiario b
                              WHERE b.numero_documento = cb.numero_documento)
            """)
            cruzan = cur.fetchone()[0]

            cur.execute("""
                SELECT count(*) FROM (
                  SELECT numero_documento FROM beneficiario
                  WHERE numero_documento IS NOT NULL
                  GROUP BY 1 HAVING count(*) > 1) x
            """)
            ambiguos = cur.fetchone()[0]

        self.stdout.write(f"   filas totales           {total}")
        self.stdout.write(f"   ya tienen beneficiario  {con_id}")
        self.stdout.write(f"   candidatas (NULL+doc)   {candidatas}")
        self.stdout.write(f"   de esas, cruzan         {cruzan}")
        self.stdout.write(f"   sin cruce               {candidatas - cruzan}")

        if ambiguos:
            # No se adivina: si un documento tiene dos beneficiarios, elegir uno
            # es inventar un vínculo entre plata pública y una persona.
            self.stdout.write(self.style.ERROR(
                f"   ⚠ {ambiguos} documentos con MÁS DE UN beneficiario. "
                f"No se escribe nada en este paso: hay que resolver la "
                f"ambigüedad primero."))
            return

        if not self.write_mode or not cruzan:
            return

        with transaction.atomic(), connection.cursor() as cur:
            cur.execute("""
                UPDATE contrato_beneficiario cb
                   SET beneficiario_id = b.id
                  FROM beneficiario b
                 WHERE b.numero_documento = cb.numero_documento
                   AND cb.beneficiario_id IS NULL
            """)
            self.stdout.write(self.style.SUCCESS(
                f"   → {cur.rowcount} filas enlazadas"))

    # ── Paso 2 · Beneficiario para cada participante ─────────────────────
    def _paso_participantes(self, limite: int):
        from apps.login.models.persona import Persona
        from apps.login.services.beneficiario_helpers import (
            asegurar_beneficiario_persona,
        )

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n2. Beneficiario para las personas inscritas a eventos"))

        with connection.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT pa.persona_id
                  FROM participante pa
                 WHERE pa.persona_id IS NOT NULL
                   AND NOT EXISTS (SELECT 1 FROM beneficiario b
                                   WHERE b.persona_id = pa.persona_id)
                 ORDER BY pa.persona_id
            """)
            ids = [r[0] for r in cur.fetchall()]

        if limite:
            ids = ids[:limite]
        self.stdout.write(f"   personas sin beneficiario  {len(ids)}")

        if not self.write_mode:
            # En seco se cuenta cuántas PODRÍAN crearse, sin tocar nada: el
            # helper solo funciona si la persona tiene documento registrado.
            with connection.cursor() as cur:
                # Ojo con el sentido de la relación: NO es
                # `persona_documento.persona_id`. Es `persona.persona_documento`
                # apuntando a la tabla de documentos (una persona tiene un
                # documento, no al revés).
                cur.execute("""
                    SELECT count(*) FROM persona p
                     JOIN persona_documento pd ON pd.id = p.persona_documento
                     WHERE p.id = ANY(%s)
                       AND pd.tipo_documento_codigo IS NOT NULL
                """, [ids])
                con_doc = cur.fetchone()[0]
            self.stdout.write(f"   con documento (se crearían) {con_doc}")
            self.stdout.write(f"   sin documento (se omiten)   {len(ids) - con_doc}")
            return

        creados = omitidos = fallidos = 0
        for pid in ids:
            persona = Persona.objects.filter(id=pid).first()
            if persona is None:
                fallidos += 1
                continue
            try:
                if asegurar_beneficiario_persona(persona) is None:
                    omitidos += 1     # sin documento: no se inventa
                else:
                    creados += 1
            except Exception as exc:
                fallidos += 1
                self.stdout.write(self.style.ERROR(
                    f"   persona {pid}: {exc}"))

        self.stdout.write(self.style.SUCCESS(f"   → {creados} beneficiarios creados"))
        if omitidos:
            self.stdout.write(self.style.WARNING(
                f"   → {omitidos} omitidos por no tener documento registrado"))
        if fallidos:
            self.stdout.write(self.style.ERROR(f"   → {fallidos} con error"))
