"""Precarga desde SECOP lo que ya sabe la Administración.

EL PRINCIPIO QUE IMPLEMENTA: el funcionario no vuelve a escribir información que
el Distrito ya publicó. Antes de pedirle un dato a un área, se agota la fuente
oficial (Constitución II · plan §2).

Medido el 2026-08-24, de nuestros 25 contratos:

    contratista   0/25   ← el hueco más grande, y está entero en SECOP
    valor        22/25
    fechas       20/25
    objeto       24/25

Los 25 tienen espejo en `secop_contrato`. Esta precarga cierra esos huecos SIN
un solo formulario — es el mayor golpe de completitud disponible.

SECO POR DEFECTO. Sin `--write` no escribe nada: imprime qué haría. Es el mismo
default del resto de ingestas del repo, y existe porque una corrida de
exploración no puede terminar tocando una BD compartida de producción.

    # ver qué traería (no escribe)
    docker exec innova_k python manage.py precargar_contratos_secop
    # escribir de verdad
    docker exec innova_k python manage.py precargar_contratos_secop --write
    # sólo un área
    docker exec innova_k python manage.py precargar_contratos_secop --subgrupo 8

PRECEDENCIA (Constitución II). Un dato que YA existe no se pisa: si SECOP dice
algo distinto, se REPORTA y se deja como está. Sobrescribir en silencio una
captura humana con la fuente —o al revés— es justo lo que la precedencia
prohíbe. Sólo se llenan huecos.

CONCILIACIÓN. Se reutiliza `_REF_SECOP_RX` de `apps.dashboard.services.
kpis_presupuesto`, el regex que ya empata 24 de 25 por (número, año). No se
inventa otro emparejamiento: hubo uno que empataba 0 de 25 durante meses.
"""
from django.core.management.base import BaseCommand
from django.db import connection, transaction


class Command(BaseCommand):
    help = "Precarga contratista, valor, fechas y objeto desde SECOP (seco por defecto)."

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true",
                            help="Escribe de verdad. Sin esto sólo reporta.")
        parser.add_argument("--subgrupo", type=int, default=None,
                            help="Limita a un subgrupo (id). Por omisión, todos.")

    # ── emparejamiento ────────────────────────────────────────────────────
    def _espejos(self, contratos):
        """{contrato_id: fila de SECOP} usando la conciliación oficial.

        Una consulta para todos, no una por contrato: son 3.073 filas de SECOP
        y 25 contratos, y el N+1 se nota.
        """
        from apps.dashboard.services.kpis_presupuesto import _REF_SECOP_RX
        llaves = {(str(c.contrato_numero), str(c.contrato_vigencia)): c.id
                  for c in contratos if c.contrato_numero and c.contrato_vigencia}
        if not llaves:
            return {}
        sql = """
            SELECT (regexp_match(upper(trim(s.referencia_contrato)), %s))[1] AS num,
                   (regexp_match(upper(trim(s.referencia_contrato)), %s))[2] AS vig,
                   s.proveedor, s.documento_proveedor, s.valor_contrato,
                   s.fecha_inicio, s.fecha_fin, s.objeto_contrato,
                   s.referencia_contrato
            FROM secop_contrato s
            WHERE s.referencia_contrato IS NOT NULL
        """
        salida = {}
        with connection.cursor() as cur:
            cur.execute(sql, [_REF_SECOP_RX, _REF_SECOP_RX])
            for num, vig, prov, doc, valor, ini, fin, objeto, ref in cur.fetchall():
                cid = llaves.get((str(num), str(vig))) if num and vig else None
                if cid is None or cid in salida:
                    continue   # el primero gana; los sufijos «(2)» son la misma fila
                salida[cid] = {
                    "proveedor": (prov or "").strip() or None,
                    "documento": (str(doc).strip() if doc else None) or None,
                    "valor": valor, "fecha_inicio": ini, "fecha_fin": fin,
                    "objeto": (objeto or "").strip() or None,
                    "referencia": (ref or "").strip() or None,
                }
        return salida

    def _proveedor_id(self, nombre, documento, escribir, cache):
        """Devuelve el id del proveedor, creándolo si hace falta.

        La tabla `proveedor` está vacía (0 filas, medido 2026-08-24) y
        `Contrato.proveedor_id` apunta ahí sin FK formal. Se identifica por NIT
        cuando lo hay —es lo único estable— y por nombre exacto cuando no.
        """
        from apps.login.models.contratos import Proveedor
        llave = (documento or "").strip() or f"nombre:{nombre}"
        if llave in cache:
            return cache[llave]
        qs = (Proveedor.objects.filter(nit=documento) if documento
              else Proveedor.objects.filter(nombre=nombre))
        p = qs.first()
        if p is None:
            if not escribir:
                cache[llave] = "(nuevo)"
                return "(nuevo)"
            p = Proveedor.objects.create(nombre=nombre, nit=documento or "")
        cache[llave] = p.id
        return p.id

    @staticmethod
    def _difieren(campo, actual, secop) -> bool:
        """¿El dato de innovaK y el de SECOP dicen cosas distintas DE VERDAD?

        Comparar con `str()` reporta ruido y el ruido se termina ignorando. En
        la primera corrida salieron 27 «discrepancias» y casi ninguna lo era:

        - **Dinero**: `23168769452.0000` (4 decimales del modelo) contra
          `23168769452.00` (2 de SECOP). Mismo número. Se comparan como Decimal.
        - **Objeto**: innovaK guarda un nombre corto y legible —«KENNEDY CAMINA
          SEGURA — convenio 983-2025»— y SECOP el objeto legal de 300 caracteres.
          Eso NO es una discrepancia: es dato interno curado, y es mejor para la
          pantalla. Y cuando sí es el mismo texto, SECOP cambia las comas por
          punto y coma. Se compara normalizado, y sólo se reporta si el texto
          normalizado de innovaK no está contenido en el de SECOP ni al revés.
        """
        if campo == "valor":
            from decimal import Decimal, InvalidOperation
            try:
                return Decimal(str(actual)) != Decimal(str(secop))
            except (InvalidOperation, TypeError):
                return str(actual) != str(secop)
        if campo == "objeto":
            import re, unicodedata

            def norm(t):
                t = unicodedata.normalize("NFKD", str(t))
                t = "".join(ch for ch in t if not unicodedata.combining(ch))
                return re.sub(r"[^a-z0-9 ]+", " ", t.lower()).strip()

            a, b = norm(actual), norm(secop)
            a = re.sub(r"\s+", " ", a)
            b = re.sub(r"\s+", " ", b)
            return not (a in b or b in a)
        return str(actual) != str(secop)

    @staticmethod
    def _empate_dudoso(c, s) -> str | None:
        """¿Este espejo es de VERDAD el mismo contrato? Devuelve el motivo si no.

        La conciliación empata por (número, año) **sin el tipo**, y eso es
        deliberado: agregarlo pierde empates reales porque nuestros
        `contrato_tipo` incluyen `CON` y `SUBASTA`, que no son prefijos de
        SECOP. El comentario que lo documenta ya avisaba: «si algún día entra un
        contrato que colisione, esto hay que volver a mirarlo».

        Entró. Medido el 2026-08-24, dos contratos empatan con tipo distinto:

          contrato 99 — SUBASTA-998-2025 ↔ CCV-998-2025
              valor IDÉNTICO ($2.058.504.840). Es el mismo: la subasta es el
              proceso, el CCV el contrato que sale de él. Empate bueno.

          contrato 100 — CPS-1078-2025 ↔ CCV-1078-2025
              valor DISTINTO ($59.457.606 contra $38.052.868). Dudoso.

        La regla: tipo distinto **y** valor distinto → no se precarga. Se
        reporta para que el área lo confirme desde Mi Área. Precargar un
        contratista con un empate dudoso escribiría un dato inventado sobre
        información contractual — justo lo que prohíbe la Constitución I.
        """
        from decimal import Decimal, InvalidOperation
        ref = (s.get("referencia") or "").upper()
        tipo_secop = ref.split("-")[0].strip() if "-" in ref else ""
        tipo_nuestro = (c.contrato_tipo or "").strip().upper()
        if not tipo_secop or tipo_secop == tipo_nuestro:
            return None
        # Tipo distinto: el valor decide.
        if c.valor is None or s.get("valor") is None:
            return f"tipo distinto ({tipo_nuestro} vs {tipo_secop}) y sin valor con qué contrastar"
        try:
            if Decimal(str(c.valor)) == Decimal(str(s["valor"])):
                return None          # mismo dinero: es el mismo contrato
        except (InvalidOperation, TypeError):
            pass
        return (f"tipo distinto ({tipo_nuestro} vs {tipo_secop}) Y valor distinto "
                f"({c.valor} vs {s['valor']})")

    # ── ejecución ─────────────────────────────────────────────────────────
    def handle(self, *args, **op):
        from apps.presupuesto.models.core import Contrato, ContratoProyecto, Proyecto

        escribir = op["write"]
        qs = Contrato.objects.all()
        if op["subgrupo"] is not None:
            pids = list(Proyecto.objects.filter(subgrupo_id=op["subgrupo"])
                        .values_list("id", flat=True))
            cids = list(ContratoProyecto.objects.filter(proyecto_id__in=pids)
                        .values_list("contrato_id", flat=True))
            qs = qs.filter(id__in=cids)

        contratos = list(qs)
        espejos = self._espejos(contratos)

        self.stdout.write(f"Contratos a revisar: {len(contratos)}")
        self.stdout.write(f"Con espejo en SECOP: {len(espejos)}")
        if not escribir:
            self.stdout.write(self.style.WARNING("\nMODO SECO — no se escribe nada. Usa --write.\n"))

        llenados, discrepancias, sin_espejo, dudosos, cache = {}, [], [], [], {}

        for c in contratos:
            s = espejos.get(c.id)
            if s is None:
                sin_espejo.append(c)
                continue

            motivo = self._empate_dudoso(c, s)
            if motivo:
                dudosos.append((c, motivo))
                continue

            cambios = {}

            # ── contratista: el hueco grande ──
            if c.proveedor_id is None and s["proveedor"]:
                pid = self._proveedor_id(s["proveedor"], s["documento"], escribir, cache)
                cambios["proveedor_id"] = pid
            elif c.proveedor_id is not None and s["proveedor"]:
                pass   # ya tiene: no se toca

            # ── el resto: sólo huecos, nunca pisar ──
            for campo, valor in (("valor", s["valor"]),
                                 ("fecha_inicio", s["fecha_inicio"]),
                                 ("fecha_fin", s["fecha_fin"]),
                                 ("objeto", s["objeto"])):
                actual = getattr(c, campo)
                if actual in (None, "") and valor not in (None, ""):
                    cambios[campo] = valor
                elif (actual not in (None, "") and valor not in (None, "")
                        and self._difieren(campo, actual, valor)):
                    discrepancias.append((c, campo, actual, valor))

            if cambios:
                llenados[c.id] = cambios

        # ── reporte ───────────────────────────────────────────────────────
        self.stdout.write(f"\nContratos con huecos que SECOP puede llenar: {len(llenados)}")
        por_campo = {}
        for cambios in llenados.values():
            for k in cambios:
                por_campo[k] = por_campo.get(k, 0) + 1
        for campo, n in sorted(por_campo.items(), key=lambda x: -x[1]):
            self.stdout.write(f"  {campo:16} {n}")

        if discrepancias:
            self.stdout.write(self.style.WARNING(
                f"\nDISCREPANCIAS ({len(discrepancias)}) — NO se tocan, se reportan:"))
            for c, campo, actual, secop in discrepancias[:15]:
                self.stdout.write(f"  contrato {c.id} · {campo}: innovaK={actual} · SECOP={secop}")
            if len(discrepancias) > 15:
                self.stdout.write(f"  … y {len(discrepancias) - 15} más")

        if dudosos:
            self.stdout.write(self.style.WARNING(
                f"\nEMPATE DUDOSO ({len(dudosos)}) — NO se precargan:"))
            for c, motivo in dudosos:
                self.stdout.write(f"  contrato {c.id} · {c.contrato_tipo} "
                                  f"{c.contrato_numero}/{c.contrato_vigencia}: {motivo}")
            self.stdout.write("  → los confirma el área desde Mi Área, con auditoría.")

        if sin_espejo:
            self.stdout.write(self.style.WARNING(
                f"\nSin espejo en SECOP ({len(sin_espejo)}):"))
            for c in sin_espejo:
                self.stdout.write(f"  contrato {c.id} · {c.contrato_tipo} "
                                  f"{c.contrato_numero}/{c.contrato_vigencia}")

        # ── escritura ─────────────────────────────────────────────────────
        if not escribir:
            self.stdout.write(self.style.WARNING(
                "\nNada escrito (modo seco). Repite con --write para aplicar."))
            return

        from apps.presupuesto.models.core import Contrato as C
        n = 0
        with transaction.atomic():
            for cid, cambios in llenados.items():
                C.objects.filter(id=cid).update(**cambios)
                n += 1
        self.stdout.write(self.style.SUCCESS(f"\n✓ {n} contrato(s) actualizados."))
