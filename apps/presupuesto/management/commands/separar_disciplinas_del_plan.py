"""Saca del plan las disciplinas que nunca fueron líneas del plan.

    docker exec innova_k python manage.py separar_disciplinas_del_plan            # seco
    docker exec innova_k python manage.py separar_disciplinas_del_plan --write --usuario <username>

SECO POR DEFECTO y firmado. **Exporta antes de borrar**: sin vuelta atrás, un
DELETE sobre la base compartida no se puede defender.

EL PROBLEMA. `actividad_plan` mezcla dos poblaciones que no son lo mismo:

  · **líneas del plan de inversión** — «Fortalecer 100 organizaciones
    comunitarias», «Otorgamiento de estímulos al sector artístico» — que se
    formulan y se contratan;
  · **disciplinas** — «Boxeo», «Polimotor», «ARTES ESCÉNICAS», «CLASES DE
    DANZA» — que son lo que se ejecuta en territorio, no una línea del plan.

Las segundas inflan todo lo que cuenta actividades: el panel de Deporte muestra
24 «actividades» que son disciplinas, y los contadores de «actividades sin
contrato» y «sin KPI» las cuentan como incumplimiento.

EL DISCRIMINADOR ES «NO TIENE INDICADOR NI CONTRATO», no `actividad_id`. Eso ya
se midió y se equivocó una vez: el Banco de Iniciativas (#108) tiene
`actividad_id` y SÍ es línea del plan. Las 34 que salen no tienen indicador
activo ni contrato vivo.

QUÉ SE PIERDE Y QUÉ NO, medido antes de escribir:

  · **El nombre no se pierde.** Las 34 apuntan a una entrada de `actividad`
    (el catálogo, 74 filas) y su texto es IDÉNTICO al del catálogo — se
    comprobó una por una: 0 sin catálogo, 0 con texto distinto.
  · **Lo único que se pierde es el par (proyecto ↔ disciplina)**, y no lo usa
    nadie: 0 eventos, 0 indicadores, 0 contratos, 0 filas de
    `presupuesto_tiempo` apuntan a las 34.
  · **Y aun así se exporta todo** a un `.sql` de restauración antes de tocar
    nada. La ruta se imprime.

LAS GUARDAS, y por qué cada una. `actividad_plan` recibe cinco FKs y dos son
peligrosas al borrar:

    presu_impacto_actividad_indicador  ON DELETE CASCADE   ← se lo lleva en silencio
    evento                             ON DELETE SET NULL  ← deja el evento huérfano

Por eso NINGUNA fila se borra si tiene algo colgando: se reporta y se deja.
Medido hoy, eso excluye a una —#106 «fortalecimiento»—, que tiene una fila en
la tabla legacy de impactos con cantidad 500 registrada el 2025-09-12. Un
CASCADE no puede llevarse dato institucional sin que lo decida una persona.
"""
from pathlib import Path

from django.core.management.base import BaseCommand

SQL_DISCIPLINAS = """
    SELECT ap.id, ap.proyecto_id, p.codigo, p.subgrupo_id, ap.descripcion, ap.actividad_id
    FROM actividad_plan ap
    JOIN proyecto p ON p.id = ap.proyecto_id
    WHERE ap.actividad_id IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM actividad_indicador ai
                      WHERE ai.actividad_plan_id = ap.id AND ai.activo)
      AND NOT EXISTS (SELECT 1 FROM contrato_actividad_plan cap
                      WHERE cap.actividad_plan_id = ap.id AND cap.activo)
    ORDER BY p.subgrupo_id, ap.id
"""

#: Todo lo que puede colgar de una actividad del plan. Si algo de esto existe,
#: la fila NO se borra: se reporta y la decide una persona.
DEPENDENCIAS = [
    ("evento",                            "actividad_plan_id", "eventos"),
    ("actividad_indicador",               "actividad_plan_id", "indicadores"),
    ("contrato_actividad_plan",           "actividad_plan_id", "contratos"),
    ("presupuesto_tiempo",                "actividad_plan_id", "cronograma"),
    ("presu_impacto_actividad_indicador", "actividad_plan_id", "impactos (legacy)"),
    ("formulacion",                       "actividad_plan_id", "formulaciones"),
]


class Command(BaseCommand):
    help = ("Saca de actividad_plan las disciplinas sin indicador ni contrato "
            "(seco por defecto; exporta antes de borrar).")

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true",
                            help="Borra de verdad. Sin esto sólo reporta.")
        parser.add_argument("--usuario", default=None,
                            help="Username de quien corre el comando. Obligatorio con --write.")

    def _dependencias(self, cur, ap_id):
        """Qué cuelga de esta fila. Vacío = se puede borrar."""
        colgando = []
        for tabla, col, etiqueta in DEPENDENCIAS:
            cur.execute(f"SELECT count(*) FROM {tabla} WHERE {col} = %s", [ap_id])
            n = cur.fetchone()[0]
            if n:
                colgando.append(f"{n} {etiqueta}")
        return colgando

    def handle(self, *args, **opciones):
        from datetime import datetime

        from django.conf import settings
        from django.db import connection, transaction

        from apps.presupuesto.models.auditoria import AuditoriaDato
        from apps.presupuesto.services.auditoria import registrar_cambio

        escribir = opciones["write"]
        autor = None
        if escribir:
            from django.contrib.auth import get_user_model
            username = opciones["usuario"]
            if not username:
                self.stderr.write(self.style.ERROR(
                    "  Falta --usuario. Un borrado sobre la base compartida no "
                    "puede quedar sin autor."))
                return
            autor = get_user_model().objects.filter(username=username).first()
            if autor is None:
                self.stderr.write(self.style.ERROR(f"  El usuario «{username}» no existe."))
                return
            self.stdout.write(f"  Firma: {autor.username} (id {autor.id})\n")

        with connection.cursor() as cur:
            cur.execute(SQL_DISCIPLINAS)
            filas = cur.fetchall()
            candidatas, retenidas = [], []
            for ap_id, proy_id, proy_cod, sub_id, desc, act_id in filas:
                colgando = self._dependencias(cur, ap_id)
                (retenidas if colgando else candidatas).append(
                    (ap_id, proy_id, proy_cod, sub_id, desc, act_id, colgando))

        for ap_id, _pid, proy, sub, desc, act, colgando in retenidas:
            self.stdout.write(self.style.WARNING(
                f"  SE RETIENE   #{ap_id} «{(desc or '')[:44]}» (proy {proy}) — "
                f"tiene {', '.join(colgando)}. No se toca: lo decide una persona."))

        for ap_id, _pid, proy, sub, desc, act, _ in candidatas:
            self.stdout.write(
                f"  {'BORRARÍA' if not escribir else 'borrada '}     #{ap_id} "
                f"«{(desc or '')[:44]}» (proy {proy}, sub {sub}) → sigue en el "
                f"catálogo como actividad {act}")

        self.stdout.write("")
        self.stdout.write(f"  disciplinas {len(filas)} · "
                          f"{'borraría' if not escribir else 'borradas'} "
                          f"{len(candidatas)} · retenidas {len(retenidas)}")

        if not escribir:
            self.stdout.write(self.style.WARNING(
                "  SECO: no se borró nada. Corré con --write --usuario <username>."))
            return
        if not candidatas:
            return

        # ── el respaldo, ANTES de tocar nada ──
        sello = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = Path(settings.BASE_DIR) / "logs" / f"restaurar_disciplinas_{sello}.sql"
        destino.parent.mkdir(parents=True, exist_ok=True)
        lineas = [
            "-- Restauración de las disciplinas retiradas de `actividad_plan`.",
            f"-- Generado el {datetime.now():%Y-%m-%d %H:%M:%S} por "
            f"separar_disciplinas_del_plan.",
            "--",
            "-- Devuelve las filas con su id original. `descripcion_ci` NO se",
            "-- incluye: es una columna generada y Postgres rechaza el INSERT.",
            "BEGIN;",
        ]
        for ap_id, pid, _proy, _sub, desc, act, _ in candidatas:
            texto = (desc or "").replace("'", "''")
            lineas.append(
                f"INSERT INTO actividad_plan (id, proyecto_id, descripcion, actividad_id) "
                f"VALUES ({ap_id}, {pid}, '{texto}', {act});")
        lineas += [
            "SELECT setval(pg_get_serial_sequence('actividad_plan','id'), "
            "(SELECT max(id) FROM actividad_plan));",
            "COMMIT;",
        ]
        destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"\n  Respaldo escrito: {destino}"))

        with transaction.atomic(), connection.cursor() as cur:
            for ap_id, pid, _proy, sub, desc, _act, _ in candidatas:
                # Se vuelve a comprobar DENTRO de la transacción: entre el
                # informe y el borrado pudo entrar una fila nueva.
                colgando = self._dependencias(cur, ap_id)
                if colgando:
                    self.stdout.write(self.style.WARNING(
                        f"  SE SALTA     #{ap_id}: le apareció {', '.join(colgando)}"))
                    continue
                cur.execute("DELETE FROM actividad_plan WHERE id = %s", [ap_id])
                registrar_cambio(
                    usuario=autor, entidad="actividad_plan", entidad_id=ap_id,
                    campo="baja", valor_anterior=(desc or "")[:120], valor_nuevo=None,
                    proyecto_id=pid, subgrupo_id=sub,
                    fuente=AuditoriaDato.SISTEMA,
                    observacion=("Retirada de `actividad_plan`: es una disciplina, "
                                 "no una línea del plan. Sin indicador ni contrato, "
                                 "y su nombre sigue en el catálogo `actividad`. "
                                 f"Restauración en {destino.name}."))
        self.stdout.write(self.style.SUCCESS(
            f"  {len(candidatas)} disciplinas fuera del plan."))
