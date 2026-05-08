"""CRUD de eventos: crear, listar, editar.

Endpoints:
- crear_evento()             → form + cascada Proyecto→Actividad→Indicador
- listar_eventos()           → tabla paginada con filtros
- editar_evento(evento_id)   → edita campos básicos + sincroniza avance
"""
import io
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, connection, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.caracterizacion.sectores import SECTORES, SECTORES_VALIDOS
from apps.georeferenciacion.models.models_localizacion import LugarIncidencia
from apps.georeferenciacion.utils import crear_con_fallback_id, get_lugar_generico
from apps.login.decorators import modulo_required
from apps.login.models.evento import Evento, TipoEvento
from apps.login.models.funcionario import Dependencia, Funcionario
from apps.presupuesto.models import ActividadPlan, AvanceIndicador, Indicador, Proyecto

from ._helpers import _url_publica_por_tipo

logger = logging.getLogger(__name__)


@login_required
@modulo_required('eventos')
def crear_evento(request):
    """
    Crear evento con cascada Proyecto→Actividad→Indicador y alimentación
    automática de avance en presu_avance_ind_periodo.
    """
    dependencias = Dependencia.objects.all().order_by('nombre')
    proyectos = Proyecto.objects.all().order_by('nombre')
    tipos_evento = TipoEvento.objects.filter(activo=True).order_by('nombre')

    qr_base64 = None
    inscripcion_url = None
    evento_info = None

    if request.method == 'POST':
        # 1. Lectura del POST
        nombre = (request.POST.get('nombre_evento') or '').strip() or None
        descripcion = (request.POST.get('descripcion') or '').strip() or None
        fecha_str = request.POST.get('fecha_realizacion')
        fecha_fin_str = request.POST.get('fecha_fin') or None  # opcional
        # hora_inicio se recibe del form pero no se persiste (modelo Evento
        # no tiene columna hora). Deuda documentada.

        # Contrato que financia (opcional). Si se selecciona, se guarda en
        # ContratoActividadPlan al crear el evento (PR-financiero).
        contrato_financia_id = request.POST.get('contrato_financia') or None

        # Cascada A (quién organiza)
        dependencia_id = request.POST.get('dependencia') or None
        subgrupo_id = request.POST.get('subgrupo') or None
        funcionario_id = request.POST.get('funcionario') or None
        # PR-3: línea fina dentro del subgrupo (opcional, depende del subgrupo).
        linea_id = request.POST.get('linea') or None

        # Cascada B (qué aporta al plan) - ESTRICTO
        # 'proyecto' del POST solo se usa para filtro JS en front,
        # backend solo persiste actividad_plan_id e indicador_id
        actividad_plan_id = request.POST.get('actividad_plan') or None
        indicador_id = request.POST.get('indicador') or None
        magnitud_str = request.POST.get('magnitud_aportada')

        tipo_evento_codigo = request.POST.get('tipo_evento') or None
        sector_caracterizacion = (request.POST.get('sector_caracterizacion') or '').strip().lower() or None

        # Ubicación híbrida (dirección libre + click en mapa)
        direccion = (request.POST.get('direccion') or '').strip() or None
        latitud_str = request.POST.get('latitud')
        longitud_str = request.POST.get('longitud')

        # 2. Validación cascada A (obligatorios)
        if not (fecha_str and dependencia_id and subgrupo_id and funcionario_id):
            messages.error(
                request,
                "⚠ Fecha, dependencia, subgrupo y funcionario son obligatorios."
            )
            return render(request, 'eventos/crear_evento.html', {
                'dependencias': dependencias,
                'proyectos': proyectos,
                'tipos_evento': tipos_evento,
                'sectores_caracterizacion': SECTORES,
            })

        # 3. Validación tipo de evento (obligatorio)
        if not tipo_evento_codigo:
            messages.error(request, "⚠ Debe seleccionar el tipo de evento.")
            return render(request, 'eventos/crear_evento.html', {
                'dependencias': dependencias,
                'proyectos': proyectos,
                'tipos_evento': tipos_evento,
                'sectores_caracterizacion': SECTORES,
            })

        tipo_evento_obj = TipoEvento.objects.filter(codigo=tipo_evento_codigo).first()
        if tipo_evento_obj is None:
            messages.error(request, "⚠ El tipo de evento seleccionado no existe.")
            return render(request, 'eventos/crear_evento.html', {
                'dependencias': dependencias,
                'proyectos': proyectos,
                'tipos_evento': tipos_evento,
                'sectores_caracterizacion': SECTORES,
            })

        if tipo_evento_obj.permite_caracterizacion:
            if not sector_caracterizacion:
                messages.error(request, "⚠ Debes elegir el sector de la caracterización.")
                return render(request, 'eventos/crear_evento.html', {
                    'dependencias': dependencias,
                    'proyectos': proyectos,
                    'tipos_evento': tipos_evento,
                    'sectores_caracterizacion': SECTORES,
                })
            if sector_caracterizacion not in SECTORES_VALIDOS:
                messages.error(request, "⚠ Sector de caracterización inválido.")
                return render(request, 'eventos/crear_evento.html', {
                    'dependencias': dependencias,
                    'proyectos': proyectos,
                    'tipos_evento': tipos_evento,
                    'sectores_caracterizacion': SECTORES,
                })
        else:
            sector_caracterizacion = None

        # 3b. Validación ubicación (dirección + mapa obligatorios)
        if not (direccion and latitud_str and longitud_str):
            messages.error(request, "⚠ Debe indicar dirección y marcar ubicación en el mapa.")
            return render(request, 'eventos/crear_evento.html', {
                'dependencias': dependencias,
                'proyectos': proyectos,
                'tipos_evento': tipos_evento,
                'sectores_caracterizacion': SECTORES,
            })

        try:
            latitud = Decimal(latitud_str)
            longitud = Decimal(longitud_str)
            # Sanidad: rango geográfico Colombia
            if not (-5 < latitud < 15 and -82 < longitud < -66):
                raise InvalidOperation()
        except (InvalidOperation, ValueError):
            messages.error(request, "⚠ Coordenadas inválidas. Haga click en el mapa.")
            return render(request, 'eventos/crear_evento.html', {
                'dependencias': dependencias,
                'proyectos': proyectos,
                'tipos_evento': tipos_evento,
                'sectores_caracterizacion': SECTORES,
            })

        # 4. Validación cascada B (ESTRICTO)
        if not (actividad_plan_id and indicador_id and magnitud_str):
            messages.error(
                request,
                "⚠ Debe seleccionar actividad, indicador y magnitud aportada al plan."
            )
            return render(request, 'eventos/crear_evento.html', {
                'dependencias': dependencias,
                'proyectos': proyectos,
                'tipos_evento': tipos_evento,
                'sectores_caracterizacion': SECTORES,
            })

        # 4. Validar magnitud numérica >= 0
        try:
            magnitud = Decimal(magnitud_str)
            if magnitud < 0:
                raise InvalidOperation()
        except (InvalidOperation, ValueError):
            messages.error(request, "⚠ Magnitud aportada debe ser un número válido ≥ 0.")
            return render(request, 'eventos/crear_evento.html', {
                'dependencias': dependencias,
                'proyectos': proyectos,
                'tipos_evento': tipos_evento,
                'sectores_caracterizacion': SECTORES,
            })

        # 5. Validar existencia de FKs cascada B (evita IntegrityError genérico)
        if not ActividadPlan.objects.filter(id=actividad_plan_id).exists():
            messages.error(request, "⚠ La actividad seleccionada no existe.")
            return render(request, 'eventos/crear_evento.html', {
                'dependencias': dependencias,
                'proyectos': proyectos,
                'tipos_evento': tipos_evento,
                'sectores_caracterizacion': SECTORES,
            })

        if not Indicador.objects.filter(id=indicador_id, activo=True).exists():
            messages.error(request, "⚠ El indicador seleccionado no existe o está inactivo.")
            return render(request, 'eventos/crear_evento.html', {
                'dependencias': dependencias,
                'proyectos': proyectos,
                'tipos_evento': tipos_evento,
                'sectores_caracterizacion': SECTORES,
            })

        # 6. Crear cadena geo + evento + avance en transacción atómica
        try:
            with transaction.atomic():
                # 6a. Cadena geográfica: Lugar (genérico shared) → GeoReferenciacion → LugarIncidencia
                lugar_generico = get_lugar_generico()
                geo = crear_con_fallback_id(
                    GeoReferenciacion,
                    latitud=latitud,
                    longitud=longitud,
                    direccion_texto=direccion,
                    fuente='manual',
                    precision='manual_click',
                    lugar=lugar_generico,
                )
                lugar_incid = crear_con_fallback_id(
                    LugarIncidencia,
                    geo_referenciacion=geo,
                )

                # 6b. Evento
                evento = Evento.objects.create(
                    nombre=nombre,
                    descripcion=descripcion,
                    fecha_inicio=fecha_str,
                    fecha_fin=(fecha_fin_str or fecha_str),
                    activo=True,
                    dependencia_id=dependencia_id,
                    subgrupo_id=subgrupo_id,
                    linea_id=linea_id,  # PR-3: granularidad fina (opcional)
                    funcionario_id=funcionario_id,
                    actividad_plan_id=actividad_plan_id,
                    indicador_id=indicador_id,
                    magnitud_aportada=magnitud,
                    tipo_evento_id=tipo_evento_codigo,
                    lugar_incidencia_id=lugar_incid.id,
                    sector_caracterizacion=sector_caracterizacion,
                )

                fecha_aporte = date.today()
                AvanceIndicador.objects.create(
                    indicador_id=indicador_id,
                    evento_id=evento.id,
                    magnitud_aportada=magnitud,
                    fecha_aporte=fecha_aporte,
                    periodo=fecha_aporte.strftime("%Y-%m"),
                    origen='EVENTO',
                )

                # Vinculación opcional contrato↔actividad_plan. Si el
                # funcionario eligió un contrato, lo asociamos a la
                # actividad de este evento (idempotente: get_or_create).
                if contrato_financia_id:
                    from apps.presupuesto.models.sql import ContratoActividadPlan
                    ContratoActividadPlan.objects.get_or_create(
                        contrato_id=contrato_financia_id,
                        actividad_plan_id=actividad_plan_id,
                        defaults={
                            'monto': 0,
                            'activo': True,
                        },
                    )

                # 6c. Datos específicos por tipo de evento.
                # INFO_TERRENO sigue siendo lógica específica por código:
                # crea fila auxiliar `EventoInfoTerreno` con datos del recorrido.
                if tipo_evento_codigo == 'INFO_TERRENO':
                    EventoInfoTerreno.objects.create(
                        evento=evento,
                        hallazgos=(request.POST.get('hallazgos') or '').strip() or None,
                        recorrido=(request.POST.get('recorrido') or '').strip() or None,
                        observaciones=(request.POST.get('observaciones') or '').strip() or None,
                    )

                funcionario = Funcionario.objects.select_related('persona').get(
                    id=funcionario_id
                )

                # Generar QR — la URL cambia según el comportamiento del tipo
                # (data-driven via flags). Mantener sincronizado con
                # `_url_inscripcion_evento` más abajo.
                inscripcion_url = request.build_absolute_uri(
                    _url_publica_por_tipo(tipo_evento_obj, evento.id)
                )
                qr_img = qrcode.make(inscripcion_url)
                buffer = io.BytesIO()
                qr_img.save(buffer, format='PNG')
                qr_base64 = base64.b64encode(buffer.getvalue()).decode()

                # nombre1 + apellido1 (campos reales del modelo Persona)
                persona = funcionario.persona
                responsable_nombre = f"{persona.nombre1 or ''} {persona.apellido1 or ''}".strip()

                evento_info = {
                    'id': evento.id,
                    'nombre': nombre,
                    'fecha': fecha_str,
                    'responsable': responsable_nombre,
                }

            messages.success(
                request,
                f"✅ Evento creado correctamente. Avance registrado: +{magnitud} en el KPI."
            )

        except IntegrityError as exc:
            logger.exception("IntegrityError al crear evento")
            if 'null value in column "id"' in str(exc):
                messages.error(
                    request,
                    "⚠ Error de configuración de BD (secuencia evento_id_seq faltante). "
                    "Coordinar con soporte técnico."
                )
            else:
                messages.error(
                    request,
                    "⚠ Conflicto guardando el evento. Verifica los datos e intenta de nuevo."
                )
        except Funcionario.DoesNotExist:
            logger.exception("Funcionario no encontrado")
            messages.error(request, "⚠ El funcionario responsable no se encontró.")
        except Exception:
            logger.exception("Error inesperado al crear evento")
            messages.error(
                request,
                "⚠ Ocurrió un error inesperado. Revisa los logs o contacta soporte."
            )

    # GET o POST con error → render
    return render(request, 'eventos/crear_evento.html', {
        'dependencias': dependencias,
        'proyectos': proyectos,
        'tipos_evento': tipos_evento,
        'sectores_caracterizacion': SECTORES,
        'qr_code': qr_base64,
        'inscripcion_url': inscripcion_url,
        'evento_info': evento_info,
    })
#=======================
#listado de eventos 
#======================
def _current_qs(request):
    """Conserva filtros en redirects/paginación."""
    keep = {}
    for k in ("q", "desde", "hasta", "dep", "sub", "page"):
        v = (request.GET.get(k) or "").strip()
        if v:
            keep[k] = v
    return urlencode(keep)


@login_required
def listar_eventos(request):
    # =========================================================
    # 1) Toggle de activo (POST)
    # =========================================================
    if request.method == "POST" and request.POST.get("toggle_id"):
        evento_id = request.POST.get("toggle_id")
        try:
            with transaction.atomic():
                with connection.cursor() as c:
                    c.execute("""
                        UPDATE evento
                        SET activo = NOT COALESCE(activo, FALSE)
                        WHERE id = %s
                    """, [evento_id])
            messages.success(request, "Estado actualizado.")
        except Exception as e:
            messages.error(request, f"No se pudo actualizar: {e}")
        # Redirige preservando filtros
        return redirect(f"{request.path}?{_current_qs(request)}")

    # =========================================================
    # 2) Filtros (GET)
    # =========================================================
    q       = (request.GET.get('q') or '').strip()
    f_desde = (request.GET.get('desde') or '').strip()
    f_hasta = (request.GET.get('hasta') or '').strip()
    dep     = (request.GET.get('dep') or '').strip()  # id numérica de dependencia
    sub     = (request.GET.get('sub') or '').strip()  # nombre subgrupo (texto)

    where = ["1=1"]
    params = []

    if q:
        where.append("COALESCE(e.nombre, '') ILIKE %s")
        params.append(f"%{q}%")

    if f_desde:
        where.append("e.fecha_inicio >= %s")
        params.append(f_desde)

    if f_hasta:
        where.append("e.fecha_fin <= %s")
        params.append(f_hasta)

    if dep:
        # si viene numérico, filtra por id; si no, por nombre
        try:
            dep_id = int(dep)
            where.append("e.dependencia_id = %s")
            params.append(dep_id)
        except ValueError:
            where.append("COALESCE(d.nombre,'') ILIKE %s")
            params.append(f"%{dep}%")

    if sub:
        where.append("COALESCE(sg.nombre,'') ILIKE %s")
        params.append(f"%{sub}%")

    sql = f"""
        SELECT
          e.id,                          -- 0
          e.nombre,                      -- 1
          e.fecha_inicio,                -- 2
          e.fecha_fin,                   -- 3
          e.activo,                      -- 4
          e.dependencia_id,              -- 5
          COALESCE(d.nombre,''),         -- 6 dependencia_nombre
          e.subgrupo_id,                 -- 7
          COALESCE(sg.nombre,''),        -- 8 subgrupo_nombre
          e.funcionario_id,              -- 9
          COALESCE(p.nombre1,'') || ' ' || COALESCE(p.apellido1,''),  -- 10 responsable_nombre
          COALESCE(te.codigo, ''),                   -- 11 tipo_evento_codigo
          COALESCE(te.permite_inscripcion, FALSE),   -- 12 flag inscripción (Banco)
          COALESCE(te.permite_caracterizacion, FALSE),-- 13 flag caracterización
          COALESCE(e.sector_caracterizacion, '')     -- 14 sector (mujer/salud/etc.)
        FROM evento e
        LEFT JOIN dependencia d ON d.id = e.dependencia_id
        LEFT JOIN subgrupo    sg ON sg.id = e.subgrupo_id
        LEFT JOIN funcionario f  ON f.id = e.funcionario_id
        LEFT JOIN persona     p  ON p.id = f.persona_id
        LEFT JOIN tipo_evento te ON te.codigo = e.tipo_evento_codigo
        WHERE {" AND ".join(where)}
        ORDER BY e.id DESC
    """

    with connection.cursor() as c:
        c.execute(sql, params)
        rows = c.fetchall()

    paginator = Paginator(rows, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'eventos/lista_eventos.html', {
        'page_obj': page_obj,
        'q': q, 'desde': f_desde, 'hasta': f_hasta, 'dep': dep, 'sub': sub,
    })
#=======================
# editar de eventos (PR-F)
#======================
@login_required
@modulo_required('eventos')
def editar_evento(request, evento_id):
    """
    Edita campos del evento y sincroniza el AvanceIndicador asociado
    si cambia la magnitud_aportada.

    NO permite cambiar indicador_id ni actividad_plan_id (eso es destructivo:
    si te equivocaste de KPI, desactiva el evento y crea otro).
    """
    evento = get_object_or_404(Evento, pk=evento_id)

    if request.method == 'POST':
        # Campos editables
        nombre = (request.POST.get('nombre') or '').strip() or None
        descripcion = (request.POST.get('descripcion') or '').strip() or None
        fecha_inicio = request.POST.get('fecha_inicio') or None
        fecha_fin = request.POST.get('fecha_fin') or None
        magnitud_str = request.POST.get('magnitud_aportada') or ''

        # Validar magnitud (solo si el evento tiene indicador asociado)
        magnitud_nueva = None
        if evento.indicador_id and magnitud_str:
            try:
                magnitud_nueva = Decimal(magnitud_str)
                if magnitud_nueva < 0:
                    messages.error(request, "⚠ La magnitud no puede ser negativa.")
                    return redirect('login:editar_evento', evento_id=evento_id)
            except (InvalidOperation, TypeError):
                messages.error(request, "⚠ Magnitud inválida.")
                return redirect('login:editar_evento', evento_id=evento_id)

        # Validar fechas
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            messages.error(request, "⚠ La fecha de fin no puede ser anterior a la de inicio.")
            return redirect('login:editar_evento', evento_id=evento_id)

        try:
            with transaction.atomic():
                # Detectar cambio de magnitud
                magnitud_antigua = evento.magnitud_aportada
                magnitud_cambio = (
                    magnitud_nueva is not None
                    and magnitud_antigua != magnitud_nueva
                )

                # Actualizar evento
                evento.nombre = nombre
                evento.descripcion = descripcion
                if fecha_inicio:
                    evento.fecha_inicio = fecha_inicio
                if fecha_fin:
                    evento.fecha_fin = fecha_fin
                if magnitud_nueva is not None:
                    evento.magnitud_aportada = magnitud_nueva
                evento.save()

                # Sincronizar AvanceIndicador asociado
                if magnitud_cambio:
                    avance = (
                        AvanceIndicador.objects
                        .filter(evento_id=evento.id, activo=True)
                        .order_by('-id')
                        .first()
                    )
                    if avance:
                        avance.magnitud_aportada = magnitud_nueva
                        avance.origen = 'AJUSTE'
                        obs = avance.observaciones or ''
                        nota = f"[Ajuste {date.today().isoformat()}] Magnitud cambió de {magnitud_antigua} a {magnitud_nueva}."
                        avance.observaciones = (obs + "\n" + nota).strip()
                        avance.save()
                        messages.info(request,
                            f"Avance asociado actualizado: {magnitud_antigua} → {magnitud_nueva}.")

            messages.success(request, "✅ Evento actualizado.")
            return redirect('login:listar_eventos')
        except Exception as e:
            messages.error(request, f"⚠ Error al actualizar: {e}")

    # GET: render form con datos actuales
    return render(request, 'eventos/editar_evento.html', {
        'evento': evento,
    })

