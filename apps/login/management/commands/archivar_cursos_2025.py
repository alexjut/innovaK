"""Archiva (soft-delete) los cursos placeholder de 2025 (CC-05 del QA).

Son 5 eventos tipo CURSO con `fecha_inicio=2025-01-01`, `fecha_fin=NULL` y
sin sesiones, que contaminan el listado de cursos y los Insights ("activos"
falsos). Archivar = `activo=False` (mismo mecanismo del botón "Archivar
individual"). Acción REVERSIBLE (solo flip de flag), idempotente y logueada.

Por seguridad NO archiva nada si el conjunto detectado no coincide con los
5 ids esperados — exige confirmación con --apply (dry-run por defecto).

    python manage.py archivar_cursos_2025            # dry-run (no escribe)
    python manage.py archivar_cursos_2025 --apply    # aplica el archivado
"""
from django.core.management.base import BaseCommand

from apps.login.models.evento import Evento

# Cursos 2025 placeholder identificados por el QA (CC-05) para revisión humana.
IDS_ESPERADOS = [74, 76, 77, 79, 81]


class Command(BaseCommand):
    help = "Archiva (activo=False) los 5 cursos placeholder de 2025 (CC-05)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply", action="store_true",
            help="Aplica el archivado. Sin esta bandera solo muestra el plan.",
        )

    def handle(self, *args, **options):
        aplicar = options["apply"]
        cursos = list(Evento.objects.filter(id__in=IDS_ESPERADOS)
                      .order_by("id"))
        encontrados = {c.id for c in cursos}
        faltantes = set(IDS_ESPERADOS) - encontrados

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Cursos 2025 a archivar (esperados: {IDS_ESPERADOS})"))
        for c in cursos:
            tipo = c.tipo_evento_id
            estado = "ya archivado" if c.activo is False else "activo"
            marca = "—" if c.activo is False else "→ activo=False"
            self.stdout.write(
                f"  id={c.id} [{tipo}] {estado:>13}  {marca}  {c.nombre[:50]!r}")
        if faltantes:
            self.stdout.write(self.style.WARNING(
                f"  Aviso: ids no encontrados en BD: {sorted(faltantes)}"))

        # Verificación de seguridad: todos deben ser CURSO.
        no_curso = [c.id for c in cursos if c.tipo_evento_id != "CURSO"]
        if no_curso:
            self.stdout.write(self.style.ERROR(
                f"ABORTADO: ids que NO son tipo CURSO: {no_curso}. "
                "No se archiva nada."))
            return

        a_archivar = [c for c in cursos if c.activo is not False]
        if not a_archivar:
            self.stdout.write(self.style.SUCCESS(
                "Nada que hacer: los cursos ya están archivados (idempotente)."))
            return

        if not aplicar:
            self.stdout.write(self.style.WARNING(
                f"DRY-RUN: {len(a_archivar)} curso(s) se archivarían. "
                "Re-ejecuta con --apply para aplicar."))
            return

        n = (Evento.objects
             .filter(id__in=[c.id for c in a_archivar])
             .update(activo=False))
        self.stdout.write(self.style.SUCCESS(
            f"Archivados {n} curso(s) (activo=False). Reversible con "
            f"Evento.objects.filter(id__in={[c.id for c in a_archivar]})"
            ".update(activo=True)."))
