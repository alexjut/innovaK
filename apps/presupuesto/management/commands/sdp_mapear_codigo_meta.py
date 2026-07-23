"""Puebla `metas.codigo_meta` con el código SEGPLAN oficial (de sdp_meta_oficial).

Aparea cada meta interna SIN codigo_meta con la meta oficial del MISMO proyecto
(cruce por `proyecto.codigo` normalizado) usando similitud de nombre. Muestra la
propuesta en --dry-run (default) y solo escribe con --apply.

Uso:
    docker exec innova_k python manage.py sdp_mapear_codigo_meta            # preview
    docker exec innova_k python manage.py sdp_mapear_codigo_meta --apply    # escribe
    docker exec innova_k python manage.py sdp_mapear_codigo_meta --umbral 0.55

Solo toca `metas.codigo_meta` (columna hoy vacía); no altera nada más. Idempotente:
re-correr no repropone las que ya quedaron con codigo_meta.
"""
import difflib
import re
import unicodedata

from django.core.management.base import BaseCommand
from django.db import connection


def _norm(s):
    """Normaliza para comparar: sin acentos, sin puntuación/espacios, minúsculas.
    '4.000' → '4000'; 'artísticos,' → 'artisticos'."""
    s = (s or "").lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    return "".join(c for c in s if c.isalnum())


def _cantidad(s):
    """Primera cantidad del texto (maneja miles con . o ,): 'Beneficiar 20.000' → 20000.
    None si no hay número."""
    m = re.search(r"\d[\d.,]*", (s or ""))
    if not m:
        return None
    try:
        return int(re.sub(r"[.,]", "", m.group()))
    except ValueError:
        return None


def _sim(a, b):
    """Similitud 0-1: texto (difflib) con bonus/penalización por la CANTIDAD.
    La cantidad es señal fuerte: '280 colectivos' ≠ '20.000 personas' aunque el
    resto del texto se parezca (evita el falso positivo 27842 vs 27841)."""
    base = difflib.SequenceMatcher(None, _norm(a), _norm(b)).ratio()
    ca, cb = _cantidad(a), _cantidad(b)
    if ca is not None and cb is not None:
        if ca == cb:
            return min(1.0, base + 0.15)   # misma cantidad → refuerza
        return base * 0.6                  # cantidad distinta → penaliza fuerte
    return base


class Command(BaseCommand):
    help = "Puebla metas.codigo_meta con el código SEGPLAN oficial (por similitud de nombre)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Escribe (default: solo preview).")
        parser.add_argument("--umbral", type=float, default=0.5,
                            help="Similitud mínima para aceptar el match (0-1, default 0.5).")

    def handle(self, *args, **opts):
        umbral = opts["umbral"]
        with connection.cursor() as c:
            # Metas internas sin codigo_meta + su proyecto normalizado
            c.execute("""
                SELECT m.codigo, m.nombre, regexp_replace(p.codigo, '^0+', '') AS proy
                FROM metas m
                JOIN meta_proyecto mp ON mp.meta_id = m.codigo
                JOIN proyecto p ON p.id = mp.proyecto_id
                WHERE m.codigo_meta IS NULL
                ORDER BY proy, m.codigo
            """)
            internas = c.fetchall()

            # Oficiales por proyecto: {proy: [(cod, nombre)]}
            c.execute("""
                SELECT DISTINCT regexp_replace(codigo_proyecto, '^0+', '') AS proy,
                       plan_meta_producto_id, plan_meta_producto_nombre
                FROM sdp_meta_oficial
            """)
            oficiales = {}
            for proy, cod, nom in c.fetchall():
                oficiales.setdefault(proy, []).append((cod, nom))

            propuestas = []   # (meta_codigo, meta_nombre, proy, cod_oficial, nom_oficial, score)
            sin_match = []
            for meta_cod, meta_nom, proy in internas:
                cands = oficiales.get(proy, [])
                if not cands:
                    sin_match.append((meta_cod, meta_nom, proy, "sin proyecto oficial"))
                    continue
                mejor = max(cands, key=lambda x: _sim(meta_nom, x[1]))
                score = _sim(meta_nom, mejor[1])
                if score >= umbral:
                    propuestas.append((meta_cod, meta_nom, proy, mejor[0], mejor[1], score))
                else:
                    sin_match.append((meta_cod, meta_nom, proy, f"mejor score {score:.2f} < {umbral}"))

            self.stdout.write(self.style.MIGRATE_HEADING(
                f"=== PROPUESTA DE MAPEO ({len(propuestas)} matches, {len(sin_match)} sin match) ==="))
            for mc, mn, proy, oc, on, sc in propuestas:
                self.stdout.write(f"  proy {proy}: meta[{mc}] '{(mn or '')[:40]}'  →  "
                                  f"SEGPLAN [{oc}]  (sim {sc:.2f})")
            if sin_match:
                self.stdout.write(self.style.WARNING("  -- SIN MATCH --"))
                for mc, mn, proy, motivo in sin_match:
                    self.stdout.write(f"    proy {proy}: meta[{mc}] '{(mn or '')[:40]}' → {motivo}")

            if not opts["apply"]:
                self.stdout.write(self.style.WARNING(
                    "\n--dry-run: nada se escribió. Reejecuta con --apply para poblar metas.codigo_meta."))
                return

            # Escribir
            n = 0
            for mc, mn, proy, oc, on, sc in propuestas:
                c.execute("UPDATE metas SET codigo_meta=%s WHERE codigo=%s AND codigo_meta IS NULL",
                          [oc, mc])
                n += c.rowcount
            self.stdout.write(self.style.SUCCESS(f"\nOK: {n} metas actualizadas con su codigo_meta oficial."))
