from django.http import JsonResponse
from apps.kactivo.models.kasistencia import Curso
from django.db import connection

def cursos_por_area(request):
    area = request.GET.get('area')
    cursos = Curso.objects.filter(clase__disciplina__categoria__icontains=area).values('id', 'nombre')
    return JsonResponse(list(cursos), safe=False)


# ✅ Subgrupos por Dependencia
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



def obtener_barrios(request):
    upz_codigo = request.GET.get('upz')
    if not upz_codigo:
        return JsonResponse({'barrios': []})

    with connection.cursor() as cursor:
        cursor.execute("SELECT codigo, nombre FROM barrio WHERE upz_codigo = %s ORDER BY nombre", [upz_codigo])
        barrios = cursor.fetchall()

    return JsonResponse({'barrios': barrios})
