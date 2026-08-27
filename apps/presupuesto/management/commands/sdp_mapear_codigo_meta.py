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

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


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


def _sin_numeros(s):
    """Normaliza QUITANDO las cantidades.

    Porque la cantidad no compara: la meta interna suele ser la tajada de UNA
    vigencia y la oficial es la del cuatrienio. «Fortalecer 50 actores» y
    «Fortalecer 200 actores» son la MISMA meta vista a dos escalas. Medido en
    el proyecto 2745: las siete metas internas son 1 de 4, 3 de 10, 1 de 4,
    50 de 200, 150 de 600 y 2 de 8.
    """
    return _norm(re.sub(r"\d[\d.,]*", " ", s or ""))


def _contencion(interno, oficial):
    """Cuánto del nombre INTERNO aparece dentro del oficial (0-1).

    No es similitud simétrica, y la diferencia decide. El nombre interno es una
    ABREVIACIÓN del oficial —«Implementar 2 proyectos de justicia local» contra
    «Implementar 8 proyectos de justicia local para la resolución…»—, así que
    `difflib.ratio()` los castiga por la diferencia de largo justo cuando más
    se parecen. Medido: con ratio simétrico el proyecto 2745 acertaba 6 de 7 y
    fallaba una por 0.01; con contención, 7 de 7, y la matriz completa tiene un
    solo 1.00 por fila —el correcto— con el resto entre 0.24 y 0.89.
    """
    sm = difflib.SequenceMatcher(None, interno, oficial)
    casan = sum(bl.size for bl in sm.get_matching_blocks())
    return casan / max(1, min(len(interno), len(oficial)))


def _asignar(internas, oficiales):
    """Empareja 1:1 las metas de UN proyecto, no fila por fila.

    Es un problema de asignación, y tratarlo como búsquedas independientes fue
    la causa del único error del ensayo: dos metas internas peleaban por la
    misma oficial y la que la perdía se quedaba con la segunda mejor de todas
    en vez de con la suya. Se recorren los pares de mayor a menor y cada lado
    se usa una sola vez.

    Devuelve [(meta, oficial, contención, segunda_mejor_contención)].
    """
    pares = sorted(
        ((_contencion(_sin_numeros(mn), _sin_numeros(on)), mc, oc, mn, on)
         for mc, mn in internas for oc, on in oficiales),
        key=lambda x: (-x[0], str(x[1]), str(x[2])))
    usadas_i, usadas_o, salida = set(), set(), []
    for score, mc, oc, mn, on in pares:
        if mc in usadas_i or oc in usadas_o:
            continue
        usadas_i.add(mc)
        usadas_o.add(oc)
        segunda = max([x[0] for x in pares if x[1] == mc and x[2] != oc] or [0.0])
        salida.append((mc, mn, oc, on, score, segunda))
    return salida


class Command(BaseCommand):
    help = "Puebla metas.codigo_meta con el código SEGPLAN oficial (por similitud de nombre)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Escribe (default: solo preview).")
        parser.add_argument("--usuario", default=None,
                            help="Username que firma el enganche. OBLIGATORIO con --apply.")
        parser.add_argument("--manual", action="append", default=[], metavar="META:OFICIAL",
                            help="Enganche confirmado por una persona, p. ej. --manual 9:27112. "
                                 "Repetible. Se valida que el código oficial sea del MISMO "
                                 "proyecto que la meta; no se acepta a ciegas.")
        parser.add_argument("--umbral", type=float, default=0.5,
                            help="(en desuso) Similitud simétrica mínima. Ver --umbral-contencion.")
        parser.add_argument("--umbral-contencion", type=float, default=1.0,
                            help="Contención mínima para escribir sin preguntar "
                                 "(0-1, default 1.0: el nombre interno tiene que "
                                 "estar ENTERO dentro del oficial).")
        parser.add_argument("--margen", type=float, default=0.05,
                            help="Distancia mínima con la 2ª candidata (default 0.05). "
                                 "Un empate no se resuelve solo.")

    def handle(self, *args, **opts):
        umbral = opts["umbral"]                     # noqa: F841 (compat)
        umbral_cont = opts["umbral_contencion"]
        margen = opts["margen"]
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

            # ── enganches confirmados por una persona ──
            #
            # Van aparte del emparejador y NO a ciegas: se exige que el código
            # oficial pertenezca al MISMO proyecto que la meta. Un dedazo acá
            # engancha el avance de otra área y no se nota, porque la cifra
            # aparece y parece razonable. Las que llegan por acá son las que el
            # algoritmo mandó a preguntar: «IVC» son tres letras que empatan
            # con tres metas oficiales distintas, y sólo una persona sabe cuál.
            manuales = []
            for par in opts["manual"]:
                try:
                    meta_txt, oficial_txt = par.split(":", 1)
                    meta_cod = int(meta_txt.strip())
                except ValueError:
                    raise CommandError(f"--manual mal escrito: «{par}». Se espera META:OFICIAL.")
                oficial = oficial_txt.strip()
                c.execute("""SELECT m.nombre, regexp_replace(p.codigo,'^0+','') , m.codigo_meta
                             FROM metas m
                             JOIN meta_proyecto mp ON mp.meta_id = m.codigo
                             JOIN proyecto p ON p.id = mp.proyecto_id
                             WHERE m.codigo = %s""", [meta_cod])
                fila = c.fetchone()
                if fila is None:
                    raise CommandError(f"La meta {meta_cod} no existe o no cuelga de un proyecto.")
                nombre_meta, proy_meta, ya = fila
                if ya:
                    self.stdout.write(self.style.WARNING(
                        f"  meta {meta_cod} ya estaba enganchada a {ya}: se deja como está."))
                    continue
                c.execute("""SELECT regexp_replace(codigo_proyecto,'^0+',''),
                                    max(plan_meta_producto_nombre)
                             FROM sdp_meta_oficial WHERE plan_meta_producto_id = %s
                             GROUP BY 1""", [oficial])
                ofi = c.fetchone()
                if ofi is None:
                    raise CommandError(
                        f"El código oficial {oficial} no está en el espejo de SEGPLAN.")
                proy_ofi, nombre_ofi = ofi
                if proy_ofi != proy_meta:
                    raise CommandError(
                        f"La meta {meta_cod} es del proyecto {proy_meta} y la meta oficial "
                        f"{oficial} es del {proy_ofi}. No se engancha entre proyectos "
                        f"distintos: sería cruzar el avance de otra área.")
                manuales.append((meta_cod, nombre_meta, proy_meta, oficial, nombre_ofi))

            # Agrupadas por proyecto: la asignación es 1:1 dentro de cada uno.
            por_proyecto = {}
            for meta_cod, meta_nom, proy in internas:
                por_proyecto.setdefault(proy, []).append((meta_cod, meta_nom))

            propuestas = []   # (meta_codigo, meta_nombre, proy, cod_oficial, nom_oficial, score)
            sin_match = []
            for proy, metas_del_proy in sorted(por_proyecto.items()):
                cands = oficiales.get(proy, [])
                if not cands:
                    for meta_cod, meta_nom in metas_del_proy:
                        sin_match.append((meta_cod, meta_nom, proy, "sin proyecto oficial",
                                          None))
                    continue
                asignadas = set()
                for mc, mn, oc, on, score, segunda in _asignar(metas_del_proy, cands):
                    asignadas.add(mc)
                    # SOLO se escribe lo que no admite duda: el nombre interno
                    # contenido ENTERO en el oficial y ninguna otra candidata
                    # cerca. Lo demás va a una lista con nombre y pregunta, que
                    # es más útil que una fila mal enganchada: un codigo_meta
                    # equivocado cruza el avance oficial de OTRA meta y nadie
                    # lo nota, porque la cifra aparece y parece razonable.
                    if score >= umbral_cont and (score - segunda) >= margen:
                        propuestas.append((mc, mn, proy, oc, on, score))
                    else:
                        propuestas_dudosas = (
                            f"contención {score:.2f}, 2ª candidata {segunda:.2f}"
                            f" → mejor candidata [{oc}] {(on or '')[:44]}")
                        sin_match.append((mc, mn, proy, propuestas_dudosas, oc))
                for mc, mn in metas_del_proy:
                    if mc not in asignadas:
                        sin_match.append((mc, mn, proy,
                                          "no quedó ninguna meta oficial libre", None))

            if manuales:
                self.stdout.write(self.style.MIGRATE_HEADING(
                    f"=== CONFIRMADOS POR UNA PERSONA ({len(manuales)}) ==="))
                for mc, mn, proy, oc, on in manuales:
                    self.stdout.write(f"  proy {proy}: meta[{mc}] '{(mn or '')[:40]}'  →  "
                                      f"SEGPLAN [{oc}] {(on or '')[:44]}")
            self.stdout.write(self.style.MIGRATE_HEADING(
                f"=== PROPUESTA DE MAPEO ({len(propuestas)} matches, {len(sin_match)} sin match) ==="))
            for mc, mn, proy, oc, on, sc in propuestas:
                self.stdout.write(f"  proy {proy}: meta[{mc}] '{(mn or '')[:40]}'  →  "
                                  f"SEGPLAN [{oc}]  (sim {sc:.2f})")
            if sin_match:
                self.stdout.write(self.style.WARNING(
                    "  -- PIDEN UNA PERSONA (no se escriben) --"))
                for mc, mn, proy, motivo, _cand in sin_match:
                    self.stdout.write(f"    proy {proy}: meta[{mc}] '{(mn or '')[:40]}'")
                    self.stdout.write(f"        {motivo}")

            if not opts["apply"]:
                self.stdout.write(self.style.WARNING(
                    "\n--dry-run: nada se escribió. Reejecuta con --apply para poblar metas.codigo_meta."))
                return

            # ── escribir ──
            #
            # `--usuario` es obligatorio y NO es burocracia: el 2026-08-27 este
            # comando escribió 8 filas en la base compartida sin que nadie lo
            # hubiera aprobado, porque no había ninguna guarda que frenara un
            # `--apply` suelto. Ahora la hay, y además cada fila queda auditada:
            # un `codigo_meta` equivocado cruza el avance oficial de OTRA meta
            # y no se nota, porque la cifra aparece y parece razonable.
            from django.contrib.auth import get_user_model

            from apps.presupuesto.models.auditoria import AuditoriaDato
            from apps.presupuesto.services.auditoria import registrar_cambio

            username = opts.get("usuario")
            if not username:
                raise CommandError(
                    "--apply exige --usuario: el enganche con la fuente oficial "
                    "queda auditado, y una auditoría sin autor no sirve de nada.")
            usuario = get_user_model().objects.filter(username=username).first()
            if usuario is None:
                raise CommandError(f"No existe el usuario «{username}».")

            n = 0
            # `registrar_cambio` NUNCA lanza —para no perder el dato si la
            # auditoría falla—, así que un error ahí se traga en silencio y el
            # comando reportaría éxito sin dejar rastro. Ya pasó, con una
            # constante de `fuente` que no existía. Se cuenta y se avisa.
            sin_auditoria = []
            with transaction.atomic():
                for mc, mn, proy, oc, on in manuales:
                    c.execute(
                        "UPDATE metas SET codigo_meta=%s WHERE codigo=%s AND codigo_meta IS NULL",
                        [oc, mc])
                    if not c.rowcount:
                        continue
                    n += c.rowcount
                    fila = registrar_cambio(
                        usuario=usuario, entidad="meta", entidad_id=mc,
                        campo="codigo_meta", valor_anterior=None, valor_nuevo=str(oc),
                        fuente=AuditoriaDato.MANUAL,
                        observacion=(f"Enganche CONFIRMADO A MANO (el algoritmo no lo "
                                     f"resolvía) dentro del proyecto {proy}: "
                                     f"«{(on or '')[:70]}»"))
                    if fila is None:
                        sin_auditoria.append(mc)
                for mc, mn, proy, oc, on, sc in propuestas:
                    c.execute(
                        "UPDATE metas SET codigo_meta=%s WHERE codigo=%s AND codigo_meta IS NULL",
                        [oc, mc])
                    if not c.rowcount:
                        continue
                    n += c.rowcount
                    fila = registrar_cambio(
                        usuario=usuario, entidad="meta", entidad_id=mc,
                        campo="codigo_meta", valor_anterior=None, valor_nuevo=str(oc),
                        fuente=AuditoriaDato.SEGPLAN,
                        observacion=(f"Enganche con SEGPLAN por contención {sc:.2f} "
                                     f"dentro del proyecto {proy}: «{(on or '')[:70]}»"))
                    if fila is None:
                        sin_auditoria.append(mc)
            self.stdout.write(self.style.SUCCESS(
                f"\nOK: {n} metas enganchadas, firmadas por {username}."))
            if sin_auditoria:
                self.stdout.write(self.style.ERROR(
                    f"⚠ SIN AUDITORÍA: {sin_auditoria}. El enganche se escribió "
                    f"pero no quedó rastro de su origen. Revisar el log."))
            if n:
                self.stdout.write(
                    "Para deshacer: UPDATE metas SET codigo_meta=NULL WHERE codigo IN ("
                    + ", ".join(str(x[0]) for x in list(manuales) + list(propuestas)) + ");")
