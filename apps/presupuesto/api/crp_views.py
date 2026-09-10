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


def _resolver_corte(cur, corte):
    """`(carga_id, error)` para el corte pedido. Uno de los dos es `None`.

    POR QUÉ NO SE FILTRA POR `crp_carga.fecha_corte`. `crp` guarda UN solo
    `carga_id` y el upsert lo pisa en cada corte: después de la segunda carga
    ninguna fila apunta ya a la primera. Filtrando por la fecha del join, todo
    corte que no fuera el último devolvía `total=0` y `suma=0` —un cero que
    parece medido— mientras el historial seguía ofreciendo esa carga con sus
    $226.745 M al lado. Acá el corte se resuelve contra `crp_carga` y se
    filtra por la carga, así que un corte que no existe da 400 y uno viejo da
    409 diciendo qué pasó, en vez de una pantalla en ceros.
    """
    try:
        _dt.date.fromisoformat(corte)
    except ValueError:
        return None, Response({"detail": "El corte va como AAAA-MM-DD."},
                              status=status.HTTP_400_BAD_REQUEST)

    cur.execute("SELECT id FROM crp_carga WHERE fecha_corte = %s "
                "ORDER BY id DESC LIMIT 1", [corte])
    fila = cur.fetchone()
    if not fila:
        return None, Response(
            {"detail": f"No hay ninguna carga con corte {corte}."},
            status=status.HTTP_400_BAD_REQUEST)

    cur.execute("SELECT id, fecha_corte FROM crp_carga ORDER BY id DESC LIMIT 1")
    ultima_id, ultima_fecha = cur.fetchone()
    if fila[0] != ultima_id:
        return None, Response(
            {"detail": (
                f"El CRP guarda el estado al último corte cargado "
                f"({ultima_fecha}). Del corte {corte} solo queda el total en "
                f"el historial de cargas, no el detalle por fila.")},
            status=status.HTTP_409_CONFLICT)
    return fila[0], None


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

    `corte` solo acepta el del último cargue: ver `_resolver_corte`. Un corte
    anterior devuelve 409 con el motivo, nunca una pantalla en ceros.
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
            if p.get("corte"):
                carga_id, error = _resolver_corte(cur, p["corte"])
                if error is not None:
                    return error
                where.append("c.carga_id = %s")
                params.append(carga_id)
                w = " AND ".join(where)

            cur.execute(f"""
                SELECT COUNT(*), COALESCE(SUM(c.valor_neto), 0),
                       COALESCE(SUM(c.autorizacion_giro), 0)
                FROM crp c
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
                       c.nombre_bp_beneficiario, c.bp_beneficiario,
                       c.valor_crp, c.anulaciones, c.valor_neto,
                       c.autorizacion_giro, c.com_sin_aut_giro,
                       c.fecha_registro, c.es_obligacion_por_pagar, c.es_funcionamiento,
                       LEFT(c.objeto, 220)
                FROM crp c
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

        # EL NOMBRE SALE DE LA FILA, no de `tercero_sap`. Siete entidades
        # distritales comparten el NIT de Bogotá D.C. y hasta el DDL 028
        # colgaban todas del mismo tercero, así que $34.771 M se mostraban a
        # nombre de quien no los recibió. `crp.nombre_bp_beneficiario` guarda
        # el nombre correcto de CADA fila desde la primera carga. El tercero
        # queda de respaldo, para la fila que venga sin nombre.
        items = [{
            "id": f[0], "interno_crp": f[1], "posicion": f[2], "numero_crp": f[3],
            "compromiso": f[4], "compromiso_numero": f[5], "compromiso_anio": f[6],
            "contrato_id": f[7], "proyecto_id": f[8], "proyecto": f[9],
            "rubro": f[10], "rubro_desc": f[11],
            "tipo_compromiso": f[12], "modalidad": f[13],
            "tercero": {
                "id": f[14], "nombre": f[19] or f[15], "tipo_doc": f[16],
                "num_doc": (f[17] if ve_doc else _enmascarar(f[17])),
                "es_juridica": f[18], "bp_sap": f[20],
            } if f[14] else None,
            "valor_crp": float(f[21] or 0), "anulaciones": f[22],
            "valor_neto": f[23], "girado": f[24], "sin_girar": f[25],
            "fecha_registro": f[26].isoformat() if f[26] else None,
            "es_obligacion_por_pagar": f[27], "es_funcionamiento": f[28],
            "objeto": f[29],
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

        with connection.cursor() as cur:
            if corte:
                carga_id, error = _resolver_corte(cur, corte)
                if error is not None:
                    return error
                where.append("c.carga_id = %s")
                params.append(carga_id)
            w = " AND ".join(where)

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
                LEFT JOIN proyecto pr ON pr.id = c.proyecto_id
                WHERE {w}
                GROUP BY c.rubro_codigo
                ORDER BY SUM(c.valor_neto) DESC
            """, params)
            filas = cur.fetchall()

            cur.execute(f"""
                SELECT COALESCE(SUM(c.valor_neto), 0), COALESCE(SUM(c.autorizacion_giro), 0),
                       COUNT(*)
                FROM crp c
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
