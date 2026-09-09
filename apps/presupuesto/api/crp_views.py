"""Consulta del CRP de BogData. Solo lectura.

DATOS PERSONALES. Estas filas traen cédulas y nombres de contratistas —1.244
personas naturales en el corte 2026-09-07—. El número de documento **no se
expone**: viaja enmascarado salvo para quien tiene el módulo de contratos, que
es el mismo criterio que ya rige el resto del expediente. Un endpoint de
consulta presupuestal no es razón para publicar la cédula de nadie.
"""
import datetime as _dt

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import ModuloRequiredPermission
from apps.presupuesto.services.metrics import VIGENCIA_INICIAL_PDL

_PERMS = [ModuloRequiredPermission("presupuesto_proyectos")]

#: Tope de filas por página. El corte trae 2.630 y devolverlas todas en una
#: respuesta haría una carga de varios MB que la pantalla no puede pintar.
POR_PAGINA = 50
MAX_POR_PAGINA = 200


def _enmascarar(doc: str | None) -> str | None:
    """`'52095086'` → `'520•••86'`. Suficiente para reconocer al tercero en
    pantalla sin publicar el documento completo."""
    if not doc:
        return None
    s = str(doc)
    if len(s) <= 5:
        return "•" * len(s)
    return f"{s[:3]}{'•' * (len(s) - 5)}{s[-2:]}"


@extend_schema(tags=["Presupuesto"], summary="CRP de BogData (lista filtrable)")
class CrpListView(APIView):
    """`GET /presupuesto/api/crp/`

    Filtros: `proyecto`, `contrato`, `rubro`, `tercero`, `tipo_compromiso`,
    `corte`, `q` (busca en objeto y en el número de compromiso), `solo` para
    `obligaciones` | `funcionamiento` | `inversion` | `pdl` |
    `anterior_al_pdl`.

    SIN `solo` la lista trae TODO lo vigente, que es el estado de cuenta tal
    como lo manda BogData. El comprometido que publica `metrics` es solo el
    del PDL en curso, así que los dos totales difieren a propósito: `solo=pdl`
    reproduce el del módulo y `solo=anterior_al_pdl` la diferencia.
    """

    permission_classes = _PERMS

    def get(self, request):
        from django.db import connection

        p = request.query_params
        where, params = ["c.vigente"], []

        def filtro(sql, valor, cast=None):
            if valor in (None, ""):
                return
            where.append(sql)
            params.append(cast(valor) if cast else valor)

        try:
            filtro("c.proyecto_id = %s", p.get("proyecto"), int)
            filtro("c.contrato_id = %s", p.get("contrato"), int)
            filtro("c.tercero_id = %s", p.get("tercero"), int)
            filtro("c.tipo_compromiso_codigo = %s", p.get("tipo_compromiso"), int)
            pagina = max(1, int(p.get("pagina") or 1))
            por = min(MAX_POR_PAGINA, max(1, int(p.get("por") or POR_PAGINA)))
        except (TypeError, ValueError):
            return Response({"detail": "Un filtro numérico no es un número."},
                            status=status.HTTP_400_BAD_REQUEST)

        filtro("c.rubro_codigo = %s", p.get("rubro"))
        if p.get("corte"):
            try:
                _dt.date.fromisoformat(p["corte"])
            except ValueError:
                return Response({"detail": "El corte va como AAAA-MM-DD."},
                                status=status.HTTP_400_BAD_REQUEST)
            where.append("g.fecha_corte = %s")
            params.append(p["corte"])

        solo = (p.get("solo") or "").strip()
        if solo == "obligaciones":
            where.append("c.es_obligacion_por_pagar")
        elif solo == "funcionamiento":
            where.append("c.es_funcionamiento")
        elif solo == "inversion":
            where.append("NOT c.es_obligacion_por_pagar AND NOT c.es_funcionamiento")
        elif solo == "pdl":
            # Lo que el módulo de presupuesto cuenta como comprometido del Plan
            # en curso. Sirve para explicar la diferencia contra el total del
            # reporte sin abrir el código: el corte de 2026 trae compromisos
            # de contratos de hasta 2013 que la Alcaldía sigue pagando, y son
            # ejecución de otra administración.
            where.append("(c.compromiso_anio >= %s OR c.compromiso_anio IS NULL)")
            params.append(VIGENCIA_INICIAL_PDL)
        elif solo == "anterior_al_pdl":
            where.append("c.compromiso_anio < %s")
            params.append(VIGENCIA_INICIAL_PDL)

        q = (p.get("q") or "").strip()
        if q:
            where.append("(c.objeto ILIKE %s OR c.no_compromiso ILIKE %s)")
            params += [f"%{q}%", f"%{q}%"]

        w = " AND ".join(where)
        # El total va en su propia consulta: contar sobre el mismo SELECT
        # paginado obligaría a traer las 2.630 filas para saber cuántas hay.
        with connection.cursor() as cur:
            cur.execute(f"""
                SELECT COUNT(*), COALESCE(SUM(c.valor_neto), 0),
                       COALESCE(SUM(c.autorizacion_giro), 0)
                FROM crp c LEFT JOIN crp_carga g ON g.id = c.carga_id
                WHERE {w}
            """, params)
            total, neto, girado = cur.fetchone()

            cur.execute(f"""
                SELECT c.id, c.n_interno_crp, c.n_posicion_crp, c.numero_de_crp,
                       c.no_compromiso, c.compromiso_numero, c.compromiso_anio,
                       c.contrato_id, c.proyecto_id, pr.nombre,
                       c.rubro_codigo, c.rubro_desc,
                       c.tipo_compromiso_desc, c.modalidad_desc,
                       t.id, t.nombre, t.tipo_doc, t.num_doc, t.es_juridica,
                       c.valor_crp, c.anulaciones, c.valor_neto,
                       c.autorizacion_giro, c.com_sin_aut_giro,
                       c.fecha_registro, c.es_obligacion_por_pagar, c.es_funcionamiento,
                       LEFT(c.objeto, 220)
                FROM crp c
                LEFT JOIN crp_carga g ON g.id = c.carga_id
                LEFT JOIN tercero_sap t ON t.id = c.tercero_id
                LEFT JOIN proyecto pr ON pr.id = c.proyecto_id
                WHERE {w}
                ORDER BY c.valor_neto DESC, c.n_interno_crp
                LIMIT %s OFFSET %s
            """, params + [por, (pagina - 1) * por])
            filas = cur.fetchall()

        # Quién puede ver el documento completo. La lista se pinta igual para
        # todos; lo que cambia es si el número viaja o va enmascarado.
        #
        # El módulo tiene que ser DISTINTO del que exige `permission_classes`:
        # preguntar de nuevo por `presupuesto_proyectos` daba siempre True
        # —quien no lo tiene no llega hasta acá— y la rama del enmascarado era
        # código muerto. El que manda es «CDPs y contratos», que es el criterio
        # del resto del expediente y el que ya decía el encabezado del módulo.
        from apps.login.services.permisos import superusuario_o_modulo
        ve_doc = superusuario_o_modulo(request.user, "presupuesto_cdp")

        items = [{
            "id": f[0], "interno_crp": f[1], "posicion": f[2], "numero_crp": f[3],
            "compromiso": f[4], "compromiso_numero": f[5], "compromiso_anio": f[6],
            "contrato_id": f[7], "proyecto_id": f[8], "proyecto": f[9],
            "rubro": f[10], "rubro_desc": f[11],
            "tipo_compromiso": f[12], "modalidad": f[13],
            "tercero": {
                "id": f[14], "nombre": f[15], "tipo_doc": f[16],
                "num_doc": (f[17] if ve_doc else _enmascarar(f[17])),
                "es_juridica": f[18],
            } if f[14] else None,
            "valor_crp": float(f[19] or 0), "anulaciones": f[20],
            "valor_neto": f[21], "girado": f[22], "sin_girar": f[23],
            "fecha_registro": f[24].isoformat() if f[24] else None,
            "es_obligacion_por_pagar": f[25], "es_funcionamiento": f[26],
            "objeto": f[27],
        } for f in filas]

        return Response({
            "items": items, "total": total, "pagina": pagina, "por": por,
            "paginas": (total + por - 1) // por if por else 1,
            "suma_valor_neto": int(neto or 0),
            "suma_girado": int(girado or 0),
            "documento_visible": ve_doc,
        })


@extend_schema(tags=["Presupuesto"], summary="CRP: resumen por rubro/proyecto")
class CrpResumenView(APIView):
    """`GET /presupuesto/api/crp/resumen-por-proyecto/`

    Reproduce la hoja «RESUMEN POR PROYECTO» del Excel —rubro, descripción y
    suma del valor neto— para poder contrastar la carga contra la fuente sin
    abrir el archivo. Que las dos cifras coincidan es la prueba de que la
    ingesta no perdió ni duplicó nada.

    Y agrega lo que la hoja no trae y sí importa: el girado, y el proyecto de
    la Matriz al que engancha cada rubro.
    """

    permission_classes = _PERMS

    def get(self, request):
        from django.db import connection

        corte = request.query_params.get("corte")
        where, params = ["c.vigente"], []
        if corte:
            where.append("g.fecha_corte = %s")
            params.append(corte)
        w = " AND ".join(where)

        with connection.cursor() as cur:
            cur.execute(f"""
                SELECT c.rubro_codigo,
                       MAX(c.rubro_desc),
                       SUM(c.valor_neto),
                       SUM(c.autorizacion_giro),
                       COUNT(*),
                       MAX(c.proyecto_id),
                       MAX(pr.nombre),
                       BOOL_OR(c.es_obligacion_por_pagar),
                       BOOL_OR(c.es_funcionamiento)
                FROM crp c
                LEFT JOIN crp_carga g ON g.id = c.carga_id
                LEFT JOIN proyecto pr ON pr.id = c.proyecto_id
                WHERE {w}
                GROUP BY c.rubro_codigo
                ORDER BY SUM(c.valor_neto) DESC
            """, params)
            filas = cur.fetchall()

            cur.execute(f"""
                SELECT COALESCE(SUM(c.valor_neto), 0), COALESCE(SUM(c.autorizacion_giro), 0),
                       COUNT(*)
                FROM crp c LEFT JOIN crp_carga g ON g.id = c.carga_id
                WHERE {w}
            """, params)
            neto_t, girado_t, filas_t = cur.fetchone()

        return Response({
            "items": [{
                "rubro": f[0], "descripcion": f[1],
                "valor_neto": int(f[2] or 0), "girado": int(f[3] or 0),
                "n_filas": f[4],
                "proyecto_id": f[5], "proyecto": f[6],
                "es_obligacion_por_pagar": f[7], "es_funcionamiento": f[8],
            } for f in filas],
            "total_valor_neto": int(neto_t or 0),
            "total_girado": int(girado_t or 0),
            "total_filas": filas_t,
            "corte": corte,
        })
