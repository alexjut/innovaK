"""
apps/votaciones/views/registro.py
View y APIs para el registro de votantes desde el frontend HTML.
"""
import json
from django.contrib.auth.decorators import login_required
from apps.login.decorators import modulo_required
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from django.db.models import Count
from django.db.models import Q, ProtectedError
from django.contrib import messages
from apps.login.models.persona import Persona, Participante
from apps.login.models.persona_documento import PersonaDocumento, TipoDocumento


# ── Página principal de registro ──────────────────────────────────────────────

@login_required
@modulo_required("votaciones_votantes")
def registro_votante_view(request):
    return render(request, 'votaciones/registro_votante.html')


# ── Página listado de votantes ────────────────────────────────────────────────

@login_required
@modulo_required("votaciones_votantes")
def listado_votantes_view(request):
    return render(request, 'votaciones/listado_votantes.html')


# ── API: listar tipos de documento ───────────────────────────────────────────

@login_required
@modulo_required("votaciones_votantes")
def api_tipos_documento(request):
    tipos = TipoDocumento.objects.all().order_by('nombre')
    return JsonResponse({
        'tipos': [{'codigo': t.codigo, 'nombre': t.nombre} for t in tipos]
    })


# ── API: buscar persona por cédula ────────────────────────────────────────────

@login_required
@modulo_required("votaciones_votantes")
@require_http_methods(['POST'])
def api_buscar_persona(request):
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)

    numero = str(data.get('document_number', '')).strip()
    if not numero:
        return JsonResponse({'ok': False, 'error': 'Cédula obligatoria'}, status=400)

    doc = PersonaDocumento.objects.filter(numero_documento=numero).first()
    if doc:
        persona = Persona.objects.filter(persona_documento=doc).first()
        if persona:
            partes = [
                persona.nombre1 or '',
                persona.nombre2 or '',
                persona.apellido1 or '',
                persona.apellido2 or '',
            ]
            full_name = ' '.join(p.strip() for p in partes if p.strip())
            return JsonResponse({
                'ok': True,
                'exists': True,
                'persona_id': persona.id,
                'full_name': full_name,
                'document_number': numero,
            })

    return JsonResponse({
        'ok': True,
        'exists': False,
        'document_number': numero,
    })


# ── API: registrar nueva persona ──────────────────────────────────────────────

@login_required
@modulo_required("votaciones_votantes")
@require_http_methods(['POST'])
def api_registrar_votante(request):
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)

    numero = str(data.get('numero_documento', '')).strip()
    nombre1 = str(data.get('nombre1', '')).strip()
    apellido1 = str(data.get('apellido1', '')).strip()

    if not numero:
        return JsonResponse({'ok': False, 'error': 'Número de documento obligatorio'})
    if not nombre1:
        return JsonResponse({'ok': False, 'error': 'Primer nombre obligatorio'})
    if not apellido1:
        return JsonResponse({'ok': False, 'error': 'Primer apellido obligatorio'})

    # Verificar si ya tiene Persona asociada — si sí, devolver directamente
    persona_existente = Persona.objects.filter(
        persona_documento__numero_documento=numero
    ).first()
    if persona_existente:
        partes = [
            persona_existente.nombre1 or '',
            persona_existente.nombre2 or '',
            persona_existente.apellido1 or '',
            persona_existente.apellido2 or '',
        ]
        full_name = ' '.join(p.strip() for p in partes if p.strip())
        return JsonResponse({
            'ok': True,
            'persona_id': persona_existente.id,
            'full_name': full_name,
            'ya_existia': True,
        })

    tipo_codigo = data.get('tipo_documento_codigo') or 1
    nombre2 = str(data.get('nombre2', '')).strip() or None
    apellido2 = str(data.get('apellido2', '')).strip() or None
    fecha_nacimiento = data.get('fecha_nacimiento') or None

    try:
        with transaction.atomic():
            # 1. Reutilizar PersonaDocumento si ya existe, si no crear uno nuevo
            persona_doc = PersonaDocumento.objects.filter(
                numero_documento=numero
            ).first()

            if not persona_doc:
                tipo_doc = TipoDocumento.objects.filter(codigo=tipo_codigo).first()
                if not tipo_doc:
                    tipo_doc = TipoDocumento.objects.first()
                persona_doc = PersonaDocumento.objects.create(
                    tipo_documento=tipo_doc,
                    numero_documento=numero,
                )

            # 2. Crear Persona mínima
            persona = Persona.objects.create(
                usuario=request.user,
                persona_documento=persona_doc,
                nombre1=nombre1,
                nombre2=nombre2,
                apellido1=apellido1,
                apellido2=apellido2,
                fecha_nacimiento=fecha_nacimiento or None,
            )

            # 3. Crear Participante
            Participante.objects.create(persona=persona)

            return JsonResponse({
                'ok': True,
                'persona_id': persona.id,
                'full_name': f"{nombre1} {apellido1}".strip(),
                'ya_existia': False,
            })

    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


# ── API: listado de votantes ──────────────────────────────────────────────────

@login_required
@modulo_required("votaciones_votantes")
@require_http_methods(['GET'])
def api_listado_votantes(request):
    from ..models import Vote, Event

    event_id = request.GET.get('event_id')

    qs = Vote.objects.all()
    if event_id:
        qs = qs.filter(event_id=event_id)

    votos = (
        qs
        .values('document_number', 'voter_full_name', 'event_id', 'created_at')
        .annotate(total_votos=Count('id'))
        .order_by('-created_at')
    )

    eventos = {e.id: e.name for e in Event.objects.all()}

    hoy = timezone.localdate()
    total_hoy = 0
    resultado = []

    for v in votos:
        fecha = v['created_at']
        try:
            fecha_local = timezone.localtime(fecha)
            if fecha_local.date() == hoy:
                total_hoy += 1
        except Exception:
            pass

        resultado.append({
            'document_number': v['document_number'],
            'voter_full_name': v['voter_full_name'] or f"Cédula {v['document_number']}",
            'event_name': eventos.get(v['event_id'], '—'),
            'created_at': v['created_at'].isoformat() if v['created_at'] else None,
            'total_votos': v['total_votos'],
        })

    total_general = Vote.objects.values('document_number').distinct().count()

    return JsonResponse({
        'ok': True,
        'votantes': resultado,
        'total_evento': len(resultado),
        'total_general': total_general,
        'total_hoy': total_hoy,
    })