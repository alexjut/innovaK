"""Carga el reporte de CRP de BogData.

    docker exec -it innova_k python manage.py cargar_crp "CRP 07092026.xlsx"
    docker exec -it innova_k python manage.py cargar_crp archivo.xlsx --write --usuario alexjut

SECO POR DEFECTO, como el resto de los importadores del repo
(`importar_matriz_pdl_alk`, `cargar_matriz_pdl`): sin `--write` lee, valida y
reporta lo que HARÍA, sin tocar la base. Un cargue de $226.745 M no debería
poder dispararse por un enter de más.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

#: Los seis totales del corte 2026-09-07. Se pasan por bandera y no se
#: cablean: son de ESE archivo, y dejarlos escritos haría que el próximo corte
#: aborte siempre o —peor— que alguien borre la validación entera para poder
#: cargar.
AYUDA_TOTALES = (
    "Totales de control, separados por coma y en el orden: valor_crp, "
    "anulaciones, reintegros, valor_neto, autorizacion_giro, sin_aut_giro. "
    "Si se pasan y no cuadran, la carga aborta."
)


class Command(BaseCommand):
    help = "Carga el reporte de CRP de BogData/SAP. Seco por defecto."

    def add_arguments(self, parser):
        parser.add_argument("xlsx_path")
        parser.add_argument("--write", action="store_true",
                            help="Escribe de verdad. Sin esto, solo reporta.")
        parser.add_argument("--usuario", default=None,
                            help="Username de quien carga. Obligatorio con --write.")
        parser.add_argument("--totales", default=None, help=AYUDA_TOTALES)

    def handle(self, *args, **opts):
        from apps.presupuesto.services.crp_carga import (
            CAMPOS_PLATA, CargaError, cargar_crp, leer, validar,
        )

        esperados = None
        if opts["totales"]:
            partes = [p.strip() for p in opts["totales"].split(",")]
            if len(partes) != len(CAMPOS_PLATA):
                raise CommandError(
                    f"--totales espera {len(CAMPOS_PLATA)} números en el orden: "
                    f"{', '.join(CAMPOS_PLATA)}.")
            try:
                esperados = dict(zip(CAMPOS_PLATA, (int(p.replace(".", "").replace(",", ""))
                                                    for p in partes)))
            except ValueError as e:
                raise CommandError(f"--totales tiene un valor que no es número: {e}")

        autor = None
        if opts["write"]:
            from django.contrib.auth import get_user_model
            if not opts["usuario"]:
                raise CommandError(
                    "--write exige --usuario: un cargue del presupuesto de la "
                    "localidad sin autor no queda defendible.")
            autor = get_user_model().objects.filter(username=opts["usuario"]).first()
            if autor is None:
                raise CommandError(f"No existe el usuario «{opts['usuario']}».")

        try:
            if not opts["write"]:
                # SECO: se lee y se valida, y se deshace lo que se haya escrito.
                # Correr el cargador entero y revertir es lo único que prueba
                # que la carga REAL va a funcionar — validar por separado
                # dejaría fuera las FK, que es donde falló tres veces.
                filas = leer(opts["xlsx_path"])
                totales = validar(filas, esperados)
                self.stdout.write(self.style.MIGRATE_HEADING(
                    f"\n[seco] {len(filas)} filas leídas y validadas"))
                for c in CAMPOS_PLATA:
                    self.stdout.write(f"    {c:24s} {totales[c]:>18,}")
                try:
                    with transaction.atomic():
                        r = cargar_crp(opts["xlsx_path"], usuario=None,
                                       totales_esperados=esperados)
                        self._reportar(r)
                        raise _Revertir()
                except _Revertir:
                    self.stdout.write(self.style.WARNING(
                        "\n[seco] nada se escribió. Repetí con --write --usuario <u>."))
                return

            r = cargar_crp(opts["xlsx_path"], usuario=autor,
                           totales_esperados=esperados)
            self._reportar(r)
            self.stdout.write(self.style.SUCCESS(
                f"\nOK: carga {r['carga_id']}, corte {r['fecha_corte']}, "
                f"firmada por {opts['usuario']}."))
        except CargaError as e:
            raise CommandError(str(e))

    def _reportar(self, r):
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n[carga] corte {r['fecha_corte']}"))
        self.stdout.write(
            f"    leídas {r['leidas']} · insertadas {r['insertadas']} · "
            f"actualizadas {r['actualizadas']} · marcadas no vigentes {r['no_vigentes']}")
        # Lo que no cruzó se dice SIEMPRE, aunque la carga haya ido bien: es
        # trabajo pendiente, y una carga que solo informa lo que sí entró deja
        # el hueco invisible.
        if r["compromisos_sin_contrato"]:
            self.stdout.write(self.style.WARNING(
                f"    {len(r['compromisos_sin_contrato'])} compromisos sin "
                f"contrato en innovaK (no se crean solos): "
                f"{', '.join(r['compromisos_sin_contrato'][:8])}…"))
        if r["rubros_sin_proyecto"]:
            self.stdout.write(self.style.WARNING(
                f"    {len(r['rubros_sin_proyecto'])} rubros de inversión sin "
                f"proyecto en la Matriz: {', '.join(r['rubros_sin_proyecto'][:5])}"))
        if r["choques_rubro_pep"]:
            self.stdout.write(self.style.ERROR(
                f"    {len(r['choques_rubro_pep'])} filas con el rubro y el PEP "
                f"apuntando a proyectos distintos — revisar la fuente: "
                f"{r['choques_rubro_pep'][:3]}"))


class _Revertir(Exception):
    """Corta la transacción del modo seco. No es un error."""
