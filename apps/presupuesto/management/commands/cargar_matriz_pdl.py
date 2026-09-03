"""Sube, previsualiza y aplica una carga de la Matriz PDL (pieza 4).

    # ver qué cambiaría, sin escribir nada
    manage.py cargar_matriz_pdl --archivo "Matriz…xlsx" --corte 2026-07-23 --seco

    # registrar el borrador con su diff (no aplica)
    manage.py cargar_matriz_pdl --archivo "Matriz…xlsx" --corte 2026-07-23

    manage.py cargar_matriz_pdl --listar
    manage.py cargar_matriz_pdl --aplicar 3
    manage.py cargar_matriz_pdl --descartar 3 --nota "corte equivocado"

Es la versión de consola del flujo de tres pantallas de la Fase C: subir →
previsualizar → aplicar. Las pantallas van a llamar al mismo servicio
(`apps.presupuesto.services.matriz_carga`), no a reimplementarlo.

CUBRE LA JERARQUÍA, NO LA PLATA. Sectores, objetivos y programas — que es donde
vive la regla «la carga nunca borra». Las cifras siguen entrando por
`importar_matriz_pdl_alk`. Están separados a propósito: «cambió el catálogo del
Plan» y «llegaron cifras nuevas» se revisan distinto y se equivocan distinto.
"""
import json
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.presupuesto.models import MatrizPDLCarga
from apps.presupuesto.services import matriz_carga as svc


class _Seco(Exception):
    """Señal interna para revertir la transacción de `--seco`."""


class Command(BaseCommand):
    help = "Sube, previsualiza y aplica una carga de la Matriz PDL."

    def add_arguments(self, parser):
        parser.add_argument("--archivo", help="Ruta del .xlsx")
        parser.add_argument("--corte", help="Fecha de corte oficial (YYYY-MM-DD)")
        parser.add_argument("--usuario-id", type=int, default=None)
        parser.add_argument("--seco", action="store_true",
                            help="calcula y muestra el diff sin registrar nada")
        parser.add_argument("--listar", action="store_true")
        parser.add_argument("--aplicar", type=int, metavar="ID")
        parser.add_argument("--descartar", type=int, metavar="ID")
        parser.add_argument("--nota", default=None)

    # ── salida ────────────────────────────────────────────────────────────
    def _pintar_diff(self, diff):
        vacio = True
        for entidad in ("sector", "objetivo", "programa"):
            bloque = diff.get(entidad, {})
            for clase in ("altas", "cambios", "reactivaciones", "retiros"):
                filas = bloque.get(clase) or []
                if not filas:
                    continue
                vacio = False
                self.stdout.write(f"  {entidad} · {clase} ({len(filas)}):")
                for f in filas:
                    self.stdout.write(f"      {json.dumps(f, ensure_ascii=False)}")
        if vacio:
            # Un diff vacío NO es un error: es la respuesta correcta cuando la
            # ALK reguarda el Excel sin tocar el catálogo. Decirlo así evita
            # que alguien lo lea como «falló».
            self.stdout.write("  sin cambios en la jerarquía "
                              "(el catálogo del Plan quedó igual)")

    # ── acciones ──────────────────────────────────────────────────────────
    def _listar(self):
        cargas = MatrizPDLCarga.objects.all()[:30]
        if not cargas:
            self.stdout.write("No hay cargas registradas.")
            return
        for c in cargas:
            self.stdout.write(
                f"  {c.id:>3}  {c.corte_oficial}  {c.estado:<11} "
                f"+{c.n_altas}/~{c.n_cambios}/-{c.n_retiros}  {c.archivo_nombre}")

    def _previsualizar(self, opts):
        if not opts["archivo"] or not opts["corte"]:
            raise CommandError("Hacen falta --archivo y --corte.")
        try:
            corte = date.fromisoformat(opts["corte"])
        except ValueError:
            raise CommandError("--corte va en formato YYYY-MM-DD.")

        if opts["seco"]:
            # En seco NO se registra la carga: se calcula el diff y se muestra.
            # Registrar un borrador en un ensayo dejaría el hash tomado y la
            # subida de verdad se rechazaría como duplicada.
            diff = svc.calcular_diff(svc.leer_jerarquia(opts["archivo"]))
            self.stdout.write(self.style.WARNING("SECO — no se registra nada"))
            self._pintar_diff(diff)
            return

        carga = svc.previsualizar(opts["archivo"], corte, opts["usuario_id"])
        self.stdout.write(self.style.SUCCESS(
            f"Carga {carga.id} registrada en BORRADOR "
            f"(+{carga.n_altas} / ~{carga.n_cambios} / -{carga.n_retiros})"))
        self._pintar_diff(carga.diff)
        self.stdout.write(f"\nPara aplicarla:  --aplicar {carga.id}")

    def _aplicar(self, carga_id, usuario_id, seco):
        try:
            with transaction.atomic():
                carga, hecho = svc.aplicar(carga_id, usuario_id)
                self.stdout.write(self.style.SUCCESS(
                    f"Carga {carga.id} APLICADA: {hecho['altas']} altas, "
                    f"{hecho['cambios']} cambios, "
                    f"{hecho['reactivaciones']} reactivaciones, "
                    f"{hecho['retiros']} retiros (marcados inactivos, no borrados)"))
                if seco:
                    raise _Seco()
        except _Seco:
            self.stdout.write(self.style.WARNING(
                "SECO — se hizo ROLLBACK, nada quedó escrito."))

    def handle(self, *args, **opts):
        try:
            if opts["listar"]:
                return self._listar()
            if opts["aplicar"] is not None:
                return self._aplicar(opts["aplicar"], opts["usuario_id"], opts["seco"])
            if opts["descartar"] is not None:
                carga = svc.descartar(opts["descartar"], opts["nota"])
                return self.stdout.write(f"Carga {carga.id} DESCARTADA.")
            return self._previsualizar(opts)
        except svc.CargaError as exc:
            # El motivo va tal cual: son mensajes escritos para que los lea una
            # persona («este archivo ya se subió: carga 3 del …»), no trazas.
            raise CommandError(str(exc))
