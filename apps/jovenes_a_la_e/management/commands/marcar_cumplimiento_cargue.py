"""Marca el cumplimiento (acceso / permanencia) de las entregas de un lote.

## Por qué existe

El archivo del área **no trae** la columna que discrimina acceso de
permanencia, así que el cargue deja las entregas con las dos en `False` y el
avance no se le puede imputar a ninguna meta. Cuando el área define a cuál
corresponden —o cuando corresponden todas a la misma, que es el caso de la
vigencia 2025— hay que poder marcarlas sin volver a cargar el archivo ni tocar
la base a mano.

## Qué significa cada una

- **ACCESO (meta 23771)**: la persona INICIA estudios posmedia en esa vigencia.
- **PERMANENCIA (meta 23772)**: recibe apoyo de sostenimiento para CONTINUAR
  estudios ya iniciados.

Son metas distintas, no dos formas de decir lo mismo: la misma persona puede
contar en acceso un año y en permanencia el siguiente, y ahí no hay doble
conteo. Marcar la equivocada infla la ejecución de una meta ajena, y por eso
este comando es **seco por defecto**: hay que pedir `--aplicar`.

## Cómo se deshace

Volver a correrlo con las banderas contrarias. Lo que escribe son dos booleanos
y el `metas_codigos` derivado de ellos; no crea ni borra filas.

Ejemplos:

    # Ver qué haría (no escribe)
    python manage.py marcar_cumplimiento_cargue --lote 3 --acceso

    # Aplicar
    python manage.py marcar_cumplimiento_cargue --lote 3 --acceso --aplicar

    # Los dos cumplimientos
    python manage.py marcar_cumplimiento_cargue --lote 3 --acceso --permanencia --aplicar
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.jovenes_a_la_e.models import CargueBeneficiarios, EntregaBeca

META_ACCESO = "23771"
META_PERMANENCIA = "23772"


class Command(BaseCommand):
    help = ("Marca acceso/permanencia en las entregas de un lote de cargue. "
            "Seco por defecto: exige --aplicar para escribir.")

    def add_arguments(self, parser):
        parser.add_argument("--lote", type=int, required=True,
                            help="Id del cargue (cargue_beneficiarios.id).")
        parser.add_argument("--acceso", action="store_true",
                            help="Marca cumplimiento de ACCESO (meta 23771).")
        parser.add_argument("--permanencia", action="store_true",
                            help="Marca cumplimiento de PERMANENCIA (meta 23772).")
        parser.add_argument("--aplicar", action="store_true",
                            help="Escribe de verdad. Sin esto solo informa.")

    def handle(self, *args, **opts):
        lote = CargueBeneficiarios.objects.filter(id=opts["lote"]).first()
        if lote is None:
            raise CommandError(f"No existe el cargue #{opts['lote']}.")
        if lote.estado != "procesado":
            raise CommandError(
                f"El cargue #{lote.id} está '{lote.estado}': solo se marcan los procesados.")

        acceso, permanencia = opts["acceso"], opts["permanencia"]
        if not (acceso or permanencia):
            raise CommandError(
                "Indique al menos --acceso o --permanencia. Correrlo sin ninguna "
                "de las dos pondría en cero el cumplimiento de todo el lote, y "
                "eso, si es lo que se busca, se pide explícito.")

        metas = ([META_ACCESO] if acceso else []) + ([META_PERMANENCIA] if permanencia else [])
        entregas = EntregaBeca.objects.filter(cargue_id=lote.id)
        n = entregas.count()

        self.stdout.write(
            f"Cargue #{lote.id} · {lote.archivo_nombre} · vigencia {lote.vigencia}\n"
            f"  entregas: {n}\n"
            f"  acceso (23771):      {'SÍ' if acceso else 'no'}\n"
            f"  permanencia (23772): {'SÍ' if permanencia else 'no'}\n"
            f"  metas_codigos → {','.join(metas)}"
        )

        if not opts["aplicar"]:
            self.stdout.write(self.style.WARNING(
                "\nSECO: no se escribió nada. Repita con --aplicar."))
            return

        with transaction.atomic():
            actualizadas = entregas.update(
                cumplimiento_acceso=acceso,
                cumplimiento_permanencia=permanencia,
                metas_codigos=",".join(metas) or None,
            )
            # Queda anotado en el lote quién dijo qué, para que dentro de un
            # año se pueda saber de dónde salió la cifra que se reportó.
            reporte = lote.reporte or {}
            reporte["cumplimiento_marcado"] = {
                "acceso": acceso, "permanencia": permanencia,
                "metas": metas, "entregas": actualizadas,
            }
            lote.reporte = reporte
            lote.save(update_fields=["reporte", "updated_at"])

        self.stdout.write(self.style.SUCCESS(
            f"\n{actualizadas} entregas marcadas."))

        # Marcar el cumplimiento sin recalcular dejaría el KPI en cero teniendo
        # los beneficiarios marcados, que es exactamente la clase de desfase
        # que nadie revisa hasta que hay que reportar.
        from apps.jovenes_a_la_e.services import avance as avance_becas
        r = avance_becas.recalcular(
            lote.vigencia, actividad_plan_id=lote.evento.actividad_plan_id)
        self.stdout.write(f"\nAvance recalculado ({r['periodo']}):")
        for i in r["indicadores"]:
            self.stdout.write(f"  KPI {i['indicador_id']} · {i['nombre']}: "
                              f"{i['personas']} personas ({i['accion']})")
        if r["motivo"]:
            self.stdout.write(self.style.WARNING(f"  {r['motivo']}"))
