"""Crea la línea del plan que le falta a un KPI que sí tiene meta.

    docker exec innova_k python manage.py crear_lineas_plan_faltantes            # seco
    docker exec innova_k python manage.py crear_lineas_plan_faltantes --write --usuario <username>

SECO POR DEFECTO, firmado e IDEMPOTENTE.

EL PROBLEMA QUE RESUELVE. Una formulación cuelga de una actividad del plan. Hay
áreas con KPI vivo, meta declarada y trabajo real en territorio que **no tienen
ni una fila en `actividad_plan`**, así que no pueden formular: el endpoint las
rebota con 403 porque ninguna actividad es suya. Medido el 2026-08-27:

    Subsidio tipo C · proyecto 2610 · KPI 32 «Apoyo económico tipo C a
                      personas mayores», meta 5.826 personas mayores
    Infraestructura · proyecto 2574 · KPI 28 «Tramos viales intervenidos»,
                      meta 30 tramos — y 30 filas reales en tramo_vial_contrato
    Infraestructura · proyecto 2790 · KPI 29 «Parques intervenidos»,
                      meta 13 parques — y 14 filas en intervencion_parque

No es que esas áreas no ejecuten: Infraestructura tiene la obra medida tramo a
tramo. Es que su trabajo nunca se escribió como línea del plan.

DE DÓNDE SALE EL TEXTO, PORQUE NO SE INVENTA. La descripción es **el nombre del
propio KPI**, que es dato institucional ya cargado, no una redacción mía. Queda
dicho en la auditoría y el área puede renombrarla: el texto es suyo.

SOBRE `descripcion_ci`, porque es fácil diagnosticarla mal (yo lo hice). Es una
**columna GENERADA**: `GENERATED ALWAYS AS (lower(trim(descripcion)))`. No hay
que poblarla, y de hecho **no se puede** —PostgreSQL rechaza el INSERT con
«cannot insert a non-DEFAULT value into a generated column»—. Por eso ningún
código del repo la escribe y por eso las 54 filas la tienen: la calcula la base.

La consecuencia buena es que el UNIQUE `(proyecto_id, descripcion_ci)` protege
SIEMPRE, sin depender de que nadie se acuerde: dos actividades que sólo difieran
en mayúsculas o espacios chocan. Que es justo lo que hace falta acá.

Lo que sí conviene saber: **el modelo Django declara el UNIQUE equivocado** —
`unique_together = (("proyecto", "descripcion"))`, sensible a mayúsculas—
mientras la base lo tiene sobre la columna normalizada. El ORM cree que
distingue y la base no. No se corrige acá, es otro cambio.

Además se engancha la línea a su KPI (`actividad_indicador`), porque una
actividad sin indicador no le suma a ninguna meta y volvería a quedar invisible.
"""
from django.core.management.base import BaseCommand

SQL_FALTANTES = """
    SELECT p.subgrupo_id, sg.nombre, p.id, p.codigo,
           i.id, i.nombre, i.meta_magnitud, i.unidad_medida
    FROM presu_indicador_meta_proyecto i
    JOIN meta_proyecto mp ON mp.id = i.meta_proyecto_id
    JOIN proyecto p       ON p.id  = mp.proyecto_id
    JOIN subgrupo sg      ON sg.id = p.subgrupo_id
    WHERE i.activo
      AND NOT EXISTS (SELECT 1 FROM actividad_plan ap WHERE ap.proyecto_id = p.id)
    ORDER BY p.subgrupo_id, i.id
"""


class Command(BaseCommand):
    help = ("Crea la actividad del plan que falta para los KPIs cuyo proyecto no "
            "tiene ninguna (seco por defecto).")

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true",
                            help="Escribe de verdad. Sin esto sólo reporta.")
        parser.add_argument("--usuario", default=None,
                            help="Username de quien corre el comando. Obligatorio "
                                 "con --write: la auditoría no puede quedar sin autor.")

    def handle(self, *args, **opciones):
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
                    "  Falta --usuario. Escribir en el plan de un área sin dejar "
                    "autor no se puede defender."))
                return
            autor = get_user_model().objects.filter(username=username).first()
            if autor is None:
                self.stderr.write(self.style.ERROR(f"  El usuario «{username}» no existe."))
                return
            self.stdout.write(f"  Firma: {autor.username} (id {autor.id})\n")

        with connection.cursor() as cur:
            cur.execute(SQL_FALTANTES)
            faltantes = cur.fetchall()

        if not faltantes:
            self.stdout.write("  No falta ninguna: todos los KPI activos con meta "
                              "tienen su proyecto con al menos una actividad del plan.")
            return

        creadas = 0
        for sub_id, sub_nombre, proy_id, proy_cod, kpi_id, kpi_nombre, meta, unidad in faltantes:
            descripcion = (kpi_nombre or "").strip()
            self.stdout.write(
                f"  {'CREARÍA' if not escribir else 'creada '}  {sub_nombre:<18} "
                f"proy {proy_cod:<8} KPI {kpi_id:<4} → actividad «{descripcion[:46]}» "
                f"(meta {meta} {unidad})")
            if not escribir:
                creadas += 1
                continue

            with transaction.atomic(), connection.cursor() as cur:
                # SQL y no ORM por el ON CONFLICT: apoyarse en el UNIQUE real
                # de la base —sobre la columna generada— es lo que hace la
                # corrida idempotente de verdad, en vez de un `exists()` previo
                # que deja una ventana entre la consulta y el INSERT.
                # `descripcion_ci` NO se manda: es generada y Postgres la rechaza.
                cur.execute("""
                    INSERT INTO actividad_plan (proyecto_id, descripcion)
                    VALUES (%s, %s)
                    ON CONFLICT (proyecto_id, descripcion_ci) DO NOTHING
                    RETURNING id
                """, [proy_id, descripcion])
                fila = cur.fetchone()
                if fila is None:      # ya existía con ese texto
                    continue
                ap_id = fila[0]
                # Sin indicador, la actividad no le suma a ninguna meta y volvería
                # a quedar invisible para el panel y para la formulación.
                cur.execute("""
                    INSERT INTO actividad_indicador (actividad_plan_id, indicador_id, activo)
                    VALUES (%s, %s, TRUE)
                    ON CONFLICT (actividad_plan_id, indicador_id) DO NOTHING
                """, [ap_id, kpi_id])

            creadas += 1
            registrar_cambio(
                usuario=autor, entidad="actividad_plan", entidad_id=ap_id,
                campo="creacion", valor_anterior=None, valor_nuevo=descripcion[:120],
                proyecto_id=proy_id, subgrupo_id=sub_id,
                fuente=AuditoriaDato.SISTEMA,
                observacion=(f"Creada porque el proyecto no tenía ninguna actividad "
                             f"del plan y su KPI {kpi_id} sí tiene meta ({meta} "
                             f"{unidad}), así que el área no podía formular. El "
                             f"texto es el nombre del propio KPI: el área puede "
                             f"renombrarlo."))

        self.stdout.write("")
        self.stdout.write(f"  faltantes {len(faltantes)} · "
                          f"{'crearía' if not escribir else 'creadas'} {creadas}")
        if not escribir:
            self.stdout.write(self.style.WARNING(
                "  SECO: no se escribió nada. Corré con --write --usuario <username>."))
