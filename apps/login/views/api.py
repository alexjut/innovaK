from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from apps.kactivo.models.kasistencia import Curso
from django.db import connection


@login_required
def api_personas_search(request):
    """Endpoint Select2 para personas. Busca por nombres/apellidos/documento.
    Formato Select2: {results:[{id, text}], pagination:{more}}.
    Filtros opcionales: ?excluir_funcionarios=1 / ?excluir_beneficiarios=1.
    """
    q = (request.GET.get('q') or '').strip()
    page = max(1, int(request.GET.get('page') or 1))
    page_size = 20
    offset = (page - 1) * page_size

    excluir_func = request.GET.get('excluir_funcionarios') == '1'
    excluir_benef = request.GET.get('excluir_beneficiarios') == '1'

    where = ['1=1']
    params = []
    if q:
        where.append("""(
            COALESCE(p.nombre1,'') ILIKE %s OR
            COALESCE(p.nombre2,'') ILIKE %s OR
            COALESCE(p.apellido1,'') ILIKE %s OR
            COALESCE(p.apellido2,'') ILIKE %s OR
            COALESCE(pd.numero_documento,'') ILIKE %s
        )""")
        like = f"%{q}%"
        params.extend([like] * 5)
    if excluir_func:
        where.append("NOT EXISTS (SELECT 1 FROM funcionario f WHERE f.persona_id = p.id AND f.activo)")
    if excluir_benef:
        where.append("NOT EXISTS (SELECT 1 FROM beneficiario b WHERE b.persona_id = p.id AND b.activo)")

    sql = f"""
        SELECT p.id,
               COALESCE(p.nombre1,'') || ' ' ||
               COALESCE(p.nombre2,'') || ' ' ||
               COALESCE(p.apellido1,'') || ' ' ||
               COALESCE(p.apellido2,'') AS nombre,
               COALESCE(pd.numero_documento,'') AS doc
        FROM persona p
        LEFT JOIN persona_documento pd ON pd.id = p.persona_documento
        WHERE {' AND '.join(where)}
        ORDER BY p.apellido1, p.nombre1
        LIMIT %s OFFSET %s
    """
    params.extend([page_size + 1, offset])
    with connection.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    return JsonResponse({
        'results': [
            {'id': r[0], 'text': f"{' '.join(r[1].split())}" + (f" ({r[2]})" if r[2] else "")}
            for r in rows
        ],
        'pagination': {'more': has_more},
    })

@login_required
def api_organizaciones_search(request):
    """Endpoint Select2 para organizaciones. Busca por nombre/NIT.
    Formato Select2: {results:[{id, text}], pagination:{more}}.
    """
    q = (request.GET.get('q') or '').strip()
    page = max(1, int(request.GET.get('page') or 1))
    page_size = 20
    offset = (page - 1) * page_size

    where = ['1=1']
    params = []
    if q:
        where.append("(COALESCE(nombre,'') ILIKE %s OR COALESCE(nit,'') ILIKE %s)")
        like = f"%{q}%"
        params.extend([like, like])

    sql = f"""
        SELECT id, nombre, COALESCE(nit,'') AS nit
        FROM organizacion
        WHERE {' AND '.join(where)}
        ORDER BY nombre
        LIMIT %s OFFSET %s
    """
    params.extend([page_size + 1, offset])
    with connection.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    return JsonResponse({
        'results': [
            {'id': r[0], 'text': f"{r[1]}" + (f" ({r[2]})" if r[2] else "")}
            for r in rows
        ],
        'pagination': {'more': has_more},
    })


@login_required
def cursos_por_area(request):
    area = request.GET.get('area')
    cursos = Curso.objects.filter(clase__disciplina__categoria__icontains=area).values('id', 'nombre')
    return JsonResponse(list(cursos), safe=False)


# ✅ Subgrupos por Dependencia
@login_required
def subgrupos_por_area(request):
    dependencia_id = request.GET.get('area_id')  # viene del JS
    if not dependencia_id:
        return JsonResponse([], safe=False)

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, nombre
            FROM subgrupo
            WHERE dependencia_id = %s
            ORDER BY nombre
        """, [dependencia_id])
        subgrupos = [{"id": row[0], "nombre": row[1]} for row in cursor.fetchall()]

    return JsonResponse(subgrupos, safe=False)


# ✅ Obtener Funcionarios según Subgrupo
@login_required
def funcionarios_por_subgrupo(request):
    subgrupo_id = request.GET.get('subgrupo_id')
    if not subgrupo_id:
        return JsonResponse([], safe=False)

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT f.id, CONCAT(p.nombre1, ' ', p.apellido1) AS nombre
            FROM funcionario f
            JOIN persona p ON f.persona_id = p.id
            WHERE f.subgrupo_id = %s
            ORDER BY nombre
        """, [subgrupo_id])
        funcionarios = [{"id": row[0], "nombre": row[1]} for row in cursor.fetchall()]

    return JsonResponse(funcionarios, safe=False)



# ✅ PR-3 actividades: líneas internas (granularidad fina) por subgrupo
@login_required
def lineas_por_subgrupo(request):
    raw = request.GET.get('subgrupo_id') or ''
    # QA-1 (auditoría 2026-05-06): validar entero antes de pasar a SQL.
    # Antes: input no-numérico (ej. ?subgrupo_id=abc) reventaba con 500
    # (psycopg2.errors.InvalidTextRepresentation). Ahora 200 con lista vacía.
    try:
        subgrupo_id = int(raw)
    except (TypeError, ValueError):
        return JsonResponse({'lineas': []})
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, codigo, nombre
            FROM subgrupo_linea
            WHERE subgrupo_id = %s AND activo = TRUE
            ORDER BY orden NULLS LAST, nombre
        """, [subgrupo_id])
        lineas = [{"id": r[0], "codigo": r[1], "nombre": r[2]} for r in cursor.fetchall()]
    return JsonResponse({'lineas': lineas})


@login_required
def obtener_barrios(request):
    upz_codigo = request.GET.get('upz')
    if not upz_codigo:
        return JsonResponse({'barrios': []})

    with connection.cursor() as cursor:
        cursor.execute("SELECT codigo, nombre FROM barrio WHERE upz_codigo = %s ORDER BY nombre", [upz_codigo])
        barrios = cursor.fetchall()

    return JsonResponse({'barrios': barrios})
