"""Engancha la meta «subsidio tipo c» a su proyecto oficial.

La meta 7 quedó en el catálogo como un stub suelto: sin fila en
`meta_proyecto`, y por eso sin proyecto, sin sector y fuera de la cadena
Proyecto → Meta → KPI. Era la única de las 24 así.

Todo lo que escribe sale de `sdp_meta_oficial` (ingesta de SDP datos
abiertos), no de un supuesto: proyecto **2610 KENNEDY INGRESO CON
PROPÓSITO**, meta **26103 «Beneficiar 5.826 personas mayores con apoyo
económico tipo C»**, `tipo_anualizacion='Constante'`.

Esa anualización es la razón de que la magnitud del KPI sea 5.826 y no
5.826/4: la meta sostiene la misma población cada vigencia, así que el
aporte del año y el del cuatrienio son la misma cifra. Sumar las cuatro
vigencias daría 23.304 personas mayores que no existen.

Idempotente y **dry-run por defecto**:

    python manage.py enganchar_meta_subsidio_c            # muestra el plan
    python manage.py enganchar_meta_subsidio_c --apply    # escribe
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.presupuesto.models import (
    Indicador, MetaBD, MetaProyectoBD, Proyecto, SdpMetaOficial,
)

SUBGRUPO_SUBSIDIO_C = 6      # 'Subsidio tipo C' (dependencia INVERSIÓN LOCAL)
COD_META = 7                 # la meta huérfana del catálogo
COD_PROYECTO = "2610"
ID_META_SDP = "26103"


class Command(BaseCommand):
    help = ("Engancha la meta 7 «subsidio tipo c» al proyecto 2610 con su KPI, "
            "usando la meta 26103 de SDP. Dry-run por defecto.")

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                            help="Ejecuta la escritura (sin esta bandera: dry-run).")

    def handle(self, *args, **opts):
        self.apply = opts["apply"]
        modo = "APPLY" if self.apply else "DRY-RUN"
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n=== Enganchar meta «subsidio tipo c» [{modo}] ===\n"))

        oficial = (SdpMetaOficial.objects
                   .filter(plan_meta_producto_id=ID_META_SDP)
                   .order_by("vigencia").first())
        if not oficial:
            self.stderr.write(self.style.ERROR(
                f"⚠ No está la fila oficial de la meta {ID_META_SDP} en sdp_meta_oficial. "
                f"Corre primero `ingest_sdp_datos_abiertos`. Aborta sin escribir."))
            return

        self.oficial = oficial
        self.vigencias = sorted(set(SdpMetaOficial.objects
                                    .filter(plan_meta_producto_id=ID_META_SDP)
                                    .values_list("vigencia", flat=True)))
        self._log_fuente()

        if self.apply:
            with transaction.atomic():
                self._run()
            self.stdout.write(self.style.SUCCESS("\nOK · escrito."))
        else:
            self._run()
            self.stdout.write(self.style.WARNING(
                "\nDRY-RUN: no se escribió nada. Re-ejecuta con --apply."))

    # ── pasos ────────────────────────────────────────────────────────
    def _run(self):
        proy = self._proyecto()
        meta = self._meta()
        mp = self._meta_proyecto(meta, proy)
        self._kpi(mp)

    def _proyecto(self):
        proy = Proyecto.objects.filter(codigo=COD_PROYECTO).first()
        if proy:
            self._log(f"[1] Proyecto {COD_PROYECTO} ya existe (id={proy.id}) → se reusa.")
            return proy
        self._log(f"[1] CREAR Proyecto {COD_PROYECTO} «{self.oficial.nombre_proyecto}» · "
                  f"subgrupo={SUBGRUPO_SUBSIDIO_C} (Subsidio tipo C) · programa=None")
        if self.apply:
            proy = Proyecto.objects.create(
                codigo=COD_PROYECTO,
                nombre=self.oficial.nombre_proyecto,
                subgrupo_id=SUBGRUPO_SUBSIDIO_C,
                programa=None,
            )
            self._log(f"    → Proyecto id={proy.id}")
        return proy

    def _meta(self):
        meta = MetaBD.objects.get(codigo=COD_META)
        nuevo = f"{self._nombre_meta()} (cuatrienio {self.vigencias[0]}-{self.vigencias[-1]})"
        self._log(f"[2] Meta {COD_META}: {meta.nombre!r}\n           → {nuevo!r}")
        if self.apply:
            meta.nombre = nuevo
            meta.descripcion = f"Meta {ID_META_SDP} del PDL. Fuente: SDP datos abiertos."
            meta.save(update_fields=["nombre", "descripcion"])
        return meta

    def _meta_proyecto(self, meta, proy):
        mp = MetaProyectoBD.objects.filter(meta=meta).first()
        if mp:
            self._log(f"[3] Ya tenía meta_proyecto (id={mp.id}) → se reusa.")
            return mp
        self._log(f"[3] CREAR meta_proyecto: meta {COD_META} → proyecto {COD_PROYECTO} "
                  f"(este era el enganche que faltaba)")
        if self.apply:
            mp = MetaProyectoBD.objects.create(meta=meta, proyecto=proy)
            self._log(f"    → meta_proyecto id={mp.id}")
        return mp

    def _kpi(self, mp):
        kpi = Indicador.objects.filter(meta_proyecto=mp).first() if mp else None
        if kpi:
            self._log(f"[4] Ya tenía KPI (id={kpi.id}) → se reusa.")
            return kpi
        magnitud = self.oficial.magnitud_programada
        self._log(f"[4] CREAR KPI · magnitud={magnitud:.0f} · unidad='personas mayores' · SUMA")
        if self.apply:
            kpi = Indicador.objects.create(
                meta_proyecto=mp,
                nombre=f"Apoyo económico tipo C a personas mayores (meta {ID_META_SDP})",
                descripcion=self._descripcion_kpi(magnitud),
                unidad_medida="personas mayores",
                meta_magnitud=magnitud,
                tipo_agregacion="SUMA",
                activo=True,
            )
            self._log(f"    → KPI id={kpi.id}")
        return kpi

    # ── helpers ──────────────────────────────────────────────────────
    def _nombre_meta(self):
        return (self.oficial.plan_meta_producto_nombre or "").strip().rstrip(".")

    def _descripcion_kpi(self, magnitud):
        return (
            f"Personas mayores de Kennedy con apoyo económico tipo C "
            f"(transferencias monetarias). Anualización CONSTANTE: el aporte de "
            f"cada vigencia es {magnitud:.0f} personas y el cuatrienio "
            f"{self.vigencias[0]}-{self.vigencias[-1]} es esa misma cifra — las "
            f"vigencias NO se suman. Fuente: SDP datos abiertos, meta "
            f"{ID_META_SDP} del proyecto {COD_PROYECTO}."
        )

    def _log_fuente(self):
        o = self.oficial
        self._log(f"[0] Oficial SDP · proyecto {o.codigo_proyecto} «{o.nombre_proyecto}»")
        self._log(f"    meta {ID_META_SDP}: {self._nombre_meta()}")
        self._log(f"    anualización={o.tipo_anualizacion} · magnitud={o.magnitud_programada} "
                  f"· vigencias={self.vigencias}")
        self._log(f"    sector={o.sector}")

    def _log(self, msg):
        tag = "[APPLY] " if self.apply else "[plan]  "
        self.stdout.write(f"  {tag}{msg}")
