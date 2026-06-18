"""APIViews DRF — apps.login (Etapa B Plan Frontend).

Endpoints públicos y autenticados que exponen contratos JSON estables
para clientes Angular. La view HTML legacy
`apps.login.views.eventos.inscripcion.inscribir_participante` sigue
viva para QR escaneado en móviles sin JS — ambos invocan el mismo
service `apps.login.services.inscripcion_evento.inscribir_persona`.

Endpoints actuales:
    POST /api/eventos/<id>/inscripciones/   AllowAny — inscripción pública vía QR
    GET  /api/eventos/<id>/sesiones/        cursos — listar sesiones planeadas
    POST /api/eventos/<id>/sesiones/        cursos — crear N sesiones (bulk)
    GET  /api/sesiones/<id>/asistencia/     eventos_asistencia — listar marcas + inscritos
    POST /api/sesiones/<id>/asistencia/     eventos_asistencia — bulk upsert (docente pasa lista)
"""
import logging

from django.db.models import Q
from django.shortcuts import get_object_or_404  # noqa
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.permissions import AllowAny
from apps.login.api.qr_token import QrTokenPermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import ModuloRequiredPermission
from apps.login.api.rate_limit import RateLimitedMixin
from apps.login.models.curso_sesiones import (
    AsistenciaClase, Clase, EvaluacionParticipante,
)
from apps.login.models.evento import Evento
from apps.login.services.curso_notas import (
    borrar_nota, notas_de_curso, promedios_por_curso, registrar_nota,
)
from apps.login.services.curso_sesiones import (
    crear_sesiones, inscritos_de_curso, tomar_lista,
)
from apps.login.services.inscripcion_evento import inscribir_persona

from .serializers import (
    AsistenciaMarcaSerializer,
    ClaseSerializer,
    InscripcionPublicaSerializer,
    InscripcionResultadoSerializer,
    NotasBulkSerializer,
    SesionesCrearSerializer,
    TomarListaSerializer,
)


logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Eventos"],
    summary="Inscripción pública a evento (QR)",
    request=InscripcionPublicaSerializer,
    responses={
        201: InscripcionResultadoSerializer,
        400: OpenApiResponse(OpenApiTypes.OBJECT, "Validación de campos."),
        404: OpenApiResponse(OpenApiTypes.OBJECT, "Evento no existe o inactivo."),
    },
)
class InscripcionEventoCreateView(RateLimitedMixin, APIView):
    """POST /api/eventos/<evento_id>/inscripciones/ — público.

    Inscribe un participante a un evento. Pensado para el cliente
    Angular que se renderiza cuando un asistente escanea el QR del
    evento. No requiere autenticación (decisión #6 Opción A del PR-1
    arquitecto: AllowAny + rate-limit a futuro).

    Validaciones:
      - El evento debe existir y estar activo. Si no, 404.
      - `nombre1` y `apellido1` son obligatorios. Resto opcional.
      - Campos opcionales solo se persisten si la columna existe en
        la tabla `persona` (BD evoluciona).
    """
    # Etapa C #2: público sin auth obligatoria, pero acepta JWT/Session
    # si el cliente los manda (Angular logueado, app móvil, etc.) para
    # registrar `usuario_editor` con el username real en vez de 'publico'.
    permission_classes = [QrTokenPermission]
    # Etapa C #3: rate limit 10/min/IP (formularios públicos QR).
    rate_limit = "10/min"

    def post(self, request, evento_id):
        evento = get_object_or_404(Evento, pk=evento_id, activo=True)

        serializer = InscripcionPublicaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Si llega JWT/Session válido, usar el username; si no, 'publico'.
        editor = request.user.username if request.user.is_authenticated else 'publico'

        try:
            resultado = inscribir_persona(
                evento_id=evento.id,
                datos=serializer.to_service_kwargs(),
                usuario_editor=editor,
            )
        except Exception:
            logger.exception("Error inscribiendo participante a evento %s", evento_id)
            return Response(
                {"detail": "No se pudo registrar la inscripción. Intenta de nuevo."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        salida = InscripcionResultadoSerializer({
            "persona_id": resultado.persona_id,
            "participante_id": resultado.participante_id,
            "participante_evento_id": resultado.participante_evento_id,
        })
        return Response(salida.data, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────────────
# PR-B Curso Docente — sesiones + asistencia
# ─────────────────────────────────────────────────────────────────────────


@extend_schema_view(
    get=extend_schema(
        tags=["Eventos"],
        summary="Sesiones planeadas del curso",
        responses={200: ClaseSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["Eventos"],
        summary="Crear N sesiones (bulk)",
        request=SesionesCrearSerializer,
        responses={201: OpenApiResponse(OpenApiTypes.OBJECT, "{creadas, sesion_ids}")},
    ),
)
class SesionesEventoView(APIView):
    """GET /api/eventos/<id>/sesiones/ y POST para crear sesiones bulk.

    GET: lista sesiones planeadas del curso ordenadas por fecha.
    POST body: {"sesiones": [{"fecha":"2026-06-01", "hora_inicio":"07:00",
        "hora_fin":"08:00", "lugar":"Aula 3", "nombre":"Sesión 1"}, ...]}

    Para POST, requiere módulo `cursos` (Coordinador/Admin).
    """
    permission_classes = [ModuloRequiredPermission("cursos")]

    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, pk=evento_id)
        sesiones = (Clase.objects.filter(evento_id=evento.id)
                    .select_related('dictada_por__persona')
                    .order_by('fecha', 'hora_inicio'))
        return Response({
            "evento_id": evento.id,
            "count": sesiones.count(),
            "results": ClaseSerializer(sesiones, many=True).data,
        })

    def post(self, request, evento_id):
        evento = get_object_or_404(Evento, pk=evento_id)
        ser = SesionesCrearSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            resultado = crear_sesiones(
                evento_id=evento.id,
                sesiones=ser.validated_data['sesiones'],
            )
        except Exception:
            logger.exception("Error creando sesiones para evento %s", evento_id)
            return Response(
                {"detail": "No se pudieron crear las sesiones."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(
            {"creadas": resultado.creadas, "sesion_ids": resultado.sesion_ids},
            status=status.HTTP_201_CREATED,
        )


class SesionDetalleView(APIView):
    """PATCH /api/sesiones/<id>/ — asigna quién dictó la sesión.

    Body: {"dictada_por_id": <funcionario_id|null>}. NULL = la dictó el
    docente titular del curso. Sirve para registrar suplencias (el
    supervisor asigna a otro funcionario). Requiere módulo `cursos`.
    """
    permission_classes = [ModuloRequiredPermission("cursos")]

    def patch(self, request, clase_id):
        clase = get_object_or_404(Clase, pk=clase_id)
        if "dictada_por_id" in request.data:
            raw = request.data.get("dictada_por_id")
            if raw in (None, "", "null"):
                clase.dictada_por_id = None
            else:
                from apps.login.models.funcionario import Funcionario
                try:
                    fid = int(raw)
                except (TypeError, ValueError):
                    return Response({"detail": "dictada_por_id inválido."}, status=400)
                if not Funcionario.objects.filter(pk=fid, activo=True).exists():
                    return Response(
                        {"detail": "Funcionario no existe o está inactivo."}, status=400)
                clase.dictada_por_id = fid
            clase.save(update_fields=["dictada_por_id"])
        clase = (Clase.objects.select_related('dictada_por__persona')
                 .get(pk=clase.pk))
        return Response(ClaseSerializer(clase).data)


@extend_schema_view(
    get=extend_schema(
        tags=["Eventos"],
        summary="Lista inscritos + asistencia de la sesión",
        responses={200: OpenApiResponse(OpenApiTypes.OBJECT, "{clase_id, fecha, lista:[...]}")},
    ),
    post=extend_schema(
        tags=["Eventos"],
        summary="Tomar lista (bulk upsert)",
        request=TomarListaSerializer,
        responses={200: OpenApiResponse(OpenApiTypes.OBJECT, "{presentes, ausentes, total}")},
    ),
)
class AsistenciaSesionView(APIView):
    """GET y POST asistencia para una sesión (Clase) específica.

    GET: devuelve la lista de inscritos al curso + las marcas
    existentes para esta sesión. Útil para que el front renderice
    la tabla de "tomar lista" con el estado actual.

    POST body: {"fecha":"opcional", "marcas":[{"participante_id":12,
        "presente":true, "observacion":"llegó tarde"}, ...]}
    Bulk upsert. Idempotente.

    Requiere módulo `eventos_asistencia` (Docente, Coordinador, Admin).
    """
    permission_classes = [ModuloRequiredPermission("eventos_asistencia")]

    def get(self, request, clase_id):
        clase = get_object_or_404(Clase, pk=clase_id)
        inscritos = list(inscritos_de_curso(clase.evento_id))
        marcas_existentes = AsistenciaClase.objects.filter(
            clase_id=clase.id, fecha=clase.fecha
        )
        marcas_por_part = {m.participante_id: m for m in marcas_existentes}

        lista = []
        for pe in inscritos:
            p = pe.participante
            persona = p.persona
            m = marcas_por_part.get(p.id)
            lista.append({
                "participante_id": p.id,
                "nombre": f'{persona.nombre1 or ""} {persona.apellido1 or ""}'.strip(),
                "asistencia_id": m.id if m else None,
                "presente": m.asistencia if m else None,
                "observacion": (m.observaciones if m else None),
            })

        return Response({
            "clase_id": clase.id,
            "evento_id": clase.evento_id,
            "fecha": clase.fecha,
            "nombre": clase.nombre,
            "total_inscritos": len(lista),
            "lista": lista,
        })

    def post(self, request, clase_id):
        clase = get_object_or_404(Clase, pk=clase_id)
        ser = TomarListaSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            resultado = tomar_lista(
                clase_id=clase.id,
                marcas=ser.validated_data['marcas'],
                fecha_override=ser.validated_data.get('fecha'),
            )
        except Exception:
            logger.exception("Error tomando lista de sesión %s", clase_id)
            return Response(
                {"detail": "No se pudo guardar la asistencia."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({
            "presentes": resultado.presentes,
            "ausentes": resultado.ausentes,
            "total": resultado.total,
        })


# ─────────────────────────────────────────────────────────────────────────
# PR-C Curso Docente — Notas / Evaluaciones (escala 0-5 SED Bogotá)
# ─────────────────────────────────────────────────────────────────────────


def _serializar_evaluacion(ev):
    return {
        "id": ev.id,
        "evento_id": ev.evento_id,
        "participante_id": ev.participante_id,
        "nota": ev.resultado,
        "etiqueta": ev.observaciones,
        "fecha": ev.fecha_evaluacion,
    }


@extend_schema_view(
    get=extend_schema(
        tags=["Eventos"],
        summary="Lista notas del curso + promedios",
        responses={200: OpenApiResponse(OpenApiTypes.OBJECT, "{evento_id, count, results:[...], promedios:{}}")},
    ),
    post=extend_schema(
        tags=["Eventos"],
        summary="Registrar/actualizar notas (bulk)",
        request=NotasBulkSerializer,
        responses={
            201: OpenApiResponse(OpenApiTypes.OBJECT, "{creadas, actualizadas, errores:[]}"),
            200: OpenApiResponse(OpenApiTypes.OBJECT, "Idem con errores parciales."),
        },
    ),
)
class NotasEventoView(APIView):
    """GET y POST notas para un curso.

    GET: lista evaluaciones del curso (todas las filas) + promedio por
    participante. Pensado para que el front renderice tabla docente o
    boletín por estudiante.

    POST body: {"notas":[{"participante_id":12,"nota":4.5,
        "etiqueta":"Parcial 1","fecha":"2026-05-20"}, ...]}
    Bulk: por cada item crea una fila nueva (o actualiza si trae
    `evaluacion_id`). Requiere módulo `cursos`.
    """
    permission_classes = [ModuloRequiredPermission("cursos")]

    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, pk=evento_id)
        evals = notas_de_curso(evento.id)
        return Response({
            "evento_id": evento.id,
            "count": evals.count(),
            "results": [_serializar_evaluacion(e) for e in evals],
            "promedios": {
                str(k): str(v) for k, v in promedios_por_curso(evento.id).items()
            },
        })

    def post(self, request, evento_id):
        evento = get_object_or_404(Evento, pk=evento_id)
        ser = NotasBulkSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        creadas = 0
        actualizadas = 0
        errores = []
        for item in ser.validated_data["notas"]:
            try:
                r = registrar_nota(
                    evento_id=evento.id,
                    participante_id=item["participante_id"],
                    nota=item["nota"],
                    etiqueta=item.get("etiqueta"),
                    fecha=item.get("fecha"),
                    evaluacion_id=item.get("evaluacion_id"),
                )
                if r.creada:
                    creadas += 1
                else:
                    actualizadas += 1
            except (ValueError, EvaluacionParticipante.DoesNotExist) as e:
                errores.append({
                    "participante_id": item["participante_id"],
                    "error": str(e),
                })

        return Response({
            "creadas": creadas,
            "actualizadas": actualizadas,
            "errores": errores,
        }, status=status.HTTP_200_OK if errores else status.HTTP_201_CREATED)


@extend_schema(
    tags=["Eventos"],
    summary="Borrar una evaluación",
    responses={204: OpenApiResponse(description="Borrada."),
               404: OpenApiResponse(description="No existe.")},
)
class NotaDetalleView(APIView):
    """DELETE /api/notas/<id>/ — borra una evaluación.

    Requiere módulo `cursos`.
    """
    permission_classes = [ModuloRequiredPermission("cursos")]

    def delete(self, request, evaluacion_id):
        get_object_or_404(EvaluacionParticipante, pk=evaluacion_id)
        borrar_nota(evaluacion_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────────────────────────────────
# PR-D Curso Docente — Reporte consolidado
# ─────────────────────────────────────────────────────────────────────────


@extend_schema(
    tags=["Eventos"],
    summary="Reporte consolidado del curso (asistencia + notas + promedio)",
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT, "{evento_id, evento_nombre, count, results:[FilaReporte]}")},
)
class ReporteCursoView(APIView):
    """GET /api/eventos/<id>/reporte/ — reporte consolidado del curso.

    Devuelve JSON con asistencia + notas + promedio por participante.
    Mismo dataset que renderiza la view HTML; consume el mismo service.
    Requiere módulo `cursos`.
    """
    permission_classes = [ModuloRequiredPermission("cursos")]

    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, pk=evento_id)
        from apps.login.services.curso_reporte import reporte_a_dict
        data = reporte_a_dict(evento.id)
        return Response({
            "evento_id": evento.id,
            "evento_nombre": evento.nombre,
            "count": len(data),
            "results": data,
        })


# ─────────────────────────────────────────────────────────────────────────
# Etapa D PR-5 — /api/me/ : datos del usuario autenticado para Angular
# ─────────────────────────────────────────────────────────────────────────


from drf_spectacular.utils import inline_serializer
from rest_framework import serializers as drf_serializers
from rest_framework.permissions import IsAuthenticated


@extend_schema(
    tags=["Autenticación"],
    summary="Datos del usuario autenticado",
    responses={
        200: inline_serializer(
            name="MeResponse",
            fields={
                "id": drf_serializers.IntegerField(),
                "username": drf_serializers.CharField(),
                "first_name": drf_serializers.CharField(),
                "last_name": drf_serializers.CharField(),
                "email": drf_serializers.CharField(),
                "is_superuser": drf_serializers.BooleanField(),
                "is_staff": drf_serializers.BooleanField(),
                "groups": drf_serializers.ListField(child=drf_serializers.CharField()),
                "modules": drf_serializers.ListField(child=drf_serializers.CharField()),
            },
        ),
        401: OpenApiResponse(description="Sin auth"),
    },
)
class MeView(APIView):
    """GET /api/me/ — devuelve perfil del usuario logueado + módulos.

    Pensado para que Angular (Etapa D) sepa:
    - Quién es el usuario (nombre para mostrar en topbar).
    - Si es superuser (bypass de gating).
    - Qué módulos N15 tiene asignados (filtrar sidebar / hub cards).

    Si es superuser, devuelve TODOS los módulos activos del catálogo
    (mismo comportamiento que el helper `_modulos_de` del dashboard).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        from apps.login.services.permisos import get_modulos_usuario

        # Etapa D PR-13.5: si llegó autenticado por JWT pero NO tiene
        # sesión Django, crearla. Esto permite que los iframes/links a
        # páginas Django (mapa Leaflet, cursos legacy, admin /org/*)
        # funcionen sin un segundo login. JWT + sesión Django coexisten.
        if not request.session.session_key:
            try:
                from django.contrib.auth import login as django_login
                django_login(request, u)
            except Exception:
                pass  # nunca rompemos /api/me/ por esto.

        if u.is_superuser:
            from apps.login.models.permisos import Modulo
            modules = list(
                Modulo.objects.filter(activo=True)
                              .values_list("codigo", flat=True)
            )
        else:
            modules = sorted(get_modulos_usuario(u))

        return Response({
            "id": u.id,
            "username": u.username,
            "first_name": u.first_name or "",
            "last_name": u.last_name or "",
            "email": u.email or "",
            "is_superuser": u.is_superuser,
            "is_staff": u.is_staff,
            "groups": list(u.groups.values_list("name", flat=True).distinct()),
            "modules": sorted(modules),
        })


# ─────────────────────────────────────────────────────────────────────────
# Etapa D — Administración Angular nativo (Roles, Org, Personas)
# ─────────────────────────────────────────────────────────────────────────


class AdminRolesView(APIView):
    """GET /api/admin/roles/ — lista grupos con módulos asignados."""
    permission_classes = [ModuloRequiredPermission("roles")]

    def get(self, request):
        from django.contrib.auth.models import Group
        from django.db.models import Count
        from apps.login.models.permisos import Modulo, RolMeta, RolModulo

        rolmetas = {rm.group_id: rm for rm in RolMeta.objects.all()}
        items = []
        for g in Group.objects.annotate(num_users=Count("usuarios", distinct=True)).order_by("name"):
            rm = rolmetas.get(g.id)
            mods = list(RolModulo.objects.filter(group_id=g.id)
                        .values_list("modulo__codigo", flat=True))
            items.append({
                "id": g.id,
                "name": g.name,
                "num_users": g.num_users,
                "num_modulos": len(mods),
                "es_protegido": (rm.es_protegido if rm else False),
                "activo": (rm.activo if rm else True),
            })
        return Response({"count": len(items), "results": items})


class AdminRolDetalleView(APIView):
    """GET /api/admin/roles/<id>/ — detalle con módulos + usuarios.
    POST /api/admin/roles/<id>/modulos/ — actualiza set de módulos.
    POST /api/admin/roles/<id>/toggle/  — switch activo.
    """
    permission_classes = [ModuloRequiredPermission("roles")]

    def get(self, request, rol_id):
        from django.contrib.auth.models import Group, User
        from apps.login.models.permisos import Modulo, RolMeta, RolModulo

        g = get_object_or_404(Group, pk=rol_id)
        rm = RolMeta.objects.filter(group_id=g.id).first()
        asignados = set(RolModulo.objects.filter(group_id=g.id)
                        .values_list("modulo_id", flat=True))
        modulos = [{
            "codigo": m.codigo, "nombre": m.nombre,
            "asignado": m.codigo in asignados,
        } for m in Modulo.objects.filter(activo=True).order_by("codigo")]
        usuarios = [{
            "id": u.id, "username": u.username,
            "nombre": (f"{u.first_name} {u.last_name}").strip() or u.username,
        } for u in g.usuarios.all().order_by("username")[:200]]

        return Response({
            "id": g.id, "name": g.name,
            "es_protegido": (rm.es_protegido if rm else False),
            "activo": (rm.activo if rm else True),
            "modulos": modulos,
            "usuarios": usuarios,
        })


class AdminRolModulosView(APIView):
    """POST /api/admin/roles/<id>/modulos/ con {codigos:[...]} actualiza
    el set de módulos asignados al rol (reemplazo completo)."""
    permission_classes = [ModuloRequiredPermission("roles")]

    def post(self, request, rol_id):
        from django.contrib.auth.models import Group
        from django.db import transaction
        from apps.login.models.permisos import Modulo, RolMeta, RolModulo
        from apps.login.services.permisos import invalidar_cache_global

        g = get_object_or_404(Group, pk=rol_id)
        # Admin (protegido): NO se puede quitar módulo `roles`.
        rm = RolMeta.objects.filter(group_id=g.id).first()
        codigos = request.data.get("codigos") or []
        if not isinstance(codigos, list):
            return Response({"detail": "codigos debe ser una lista."},
                            status=status.HTTP_400_BAD_REQUEST)

        if rm and rm.es_protegido and "roles" not in codigos:
            return Response(
                {"detail": "El rol protegido no puede perder el módulo 'roles'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        modulos_validos = list(
            Modulo.objects.filter(codigo__in=codigos, activo=True),
        )
        with transaction.atomic():
            RolModulo.objects.filter(group_id=g.id).delete()
            for m in modulos_validos:
                RolModulo.objects.create(group_id=g.id, modulo=m)
        invalidar_cache_global()
        return Response({"id": g.id, "count": len(modulos_validos),
                         "detail": "Módulos actualizados."})


class AdminRolToggleView(APIView):
    """POST /api/admin/roles/<id>/toggle/ — switch activo."""
    permission_classes = [ModuloRequiredPermission("roles")]

    def post(self, request, rol_id):
        from django.contrib.auth.models import Group
        from apps.login.models.permisos import RolMeta
        from apps.login.services.permisos import invalidar_cache_global

        g = get_object_or_404(Group, pk=rol_id)
        rm, _ = RolMeta.objects.get_or_create(
            group_id=g.id,
            defaults={"activo": True, "es_protegido": False},
        )
        if rm.es_protegido:
            return Response({"detail": "El rol protegido no se puede desactivar."},
                            status=status.HTTP_400_BAD_REQUEST)
        rm.activo = not rm.activo
        rm.save(update_fields=["activo"])
        invalidar_cache_global()
        return Response({"id": g.id, "activo": rm.activo})


class AdminRolCrearView(APIView):
    """POST /api/admin/roles/ con {name} — crea grupo + RolMeta activo."""
    permission_classes = [ModuloRequiredPermission("roles")]

    def post(self, request):
        from django.contrib.auth.models import Group
        from apps.login.models.permisos import RolMeta

        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"detail": "name es obligatorio."},
                            status=status.HTTP_400_BAD_REQUEST)
        if Group.objects.filter(name=name).exists():
            return Response({"detail": "Ya existe un rol con ese nombre."},
                            status=status.HTTP_400_BAD_REQUEST)
        g = Group.objects.create(name=name)
        RolMeta.objects.create(group_id=g.id, activo=True, es_protegido=False)
        return Response({"id": g.id, "name": g.name, "detail": "Rol creado."},
                        status=status.HTTP_201_CREATED)


class AdminRolUsuariosView(APIView):
    """Gestión de usuarios asignados a un rol.

    POST   /api/admin/roles/<id>/usuarios/            {usuario_id} → agrega.
    DELETE /api/admin/roles/<id>/usuarios/<user_id>/  → quita.

    Replica `apps.login.views.roles.rol_usuario_{agregar,quitar}` para
    Angular. Cada cambio invalida la caché global de permisos. El rol
    protegido (Admin) no puede quedarse sin su último usuario.
    """
    permission_classes = [ModuloRequiredPermission("roles")]

    def post(self, request, rol_id):
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group
        from apps.login.services.permisos import invalidar_cache_global
        User = get_user_model()

        g = get_object_or_404(Group, pk=rol_id)
        usuario_id = request.data.get("usuario_id")
        if not usuario_id:
            return Response({"detail": "usuario_id es obligatorio."},
                            status=status.HTTP_400_BAD_REQUEST)
        user = get_object_or_404(User, pk=usuario_id)
        user.groups.add(g)
        invalidar_cache_global()
        return Response({
            "detail": f"{user.username} agregado al rol '{g.name}'.",
            "usuario": {
                "id": user.id, "username": user.username,
                "nombre": (f"{user.first_name} {user.last_name}").strip() or user.username,
            },
        }, status=status.HTTP_201_CREATED)

    def delete(self, request, rol_id, user_id):
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group
        from apps.login.models.permisos import RolMeta
        from apps.login.services.permisos import invalidar_cache_global
        User = get_user_model()

        g = get_object_or_404(Group, pk=rol_id)
        user = get_object_or_404(User, pk=user_id)
        meta = RolMeta.objects.filter(group_id=g.id).first()

        # El rol protegido (Admin) no puede quedarse sin último usuario.
        if meta and meta.es_protegido:
            quedan = User.objects.filter(groups=g).exclude(pk=user.pk).exists()
            if not quedan:
                return Response(
                    {"detail": f"No puedes quitar al último usuario del rol protegido '{g.name}'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        user.groups.remove(g)
        invalidar_cache_global()
        return Response({"detail": f"{user.username} retirado del rol '{g.name}'."})


class AdminUsuariosSearchView(APIView):
    """GET /api/admin/usuarios/?q= — búsqueda de usuarios (User) para asignar a roles.

    Acepta `exclude_rol` (id de grupo) para no listar usuarios que ya tienen
    ese rol. Paginado simple.
    """
    permission_classes = [ModuloRequiredPermission("roles")]

    def get(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        q = (request.query_params.get("q") or "").strip()
        exclude_rol = request.query_params.get("exclude_rol")
        page = max(int(request.query_params.get("page", "1") or "1"), 1)
        page_size = min(int(request.query_params.get("page_size", "30") or "30"), 100)

        qs = User.objects.all().order_by("username")
        if q:
            qs = qs.filter(
                Q(username__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
            )
        if exclude_rol:
            try:
                qs = qs.exclude(groups__id=int(exclude_rol))
            except ValueError:
                pass

        total = qs.count()
        start = (page - 1) * page_size
        items = [{
            "id": u.id, "username": u.username,
            "nombre": (f"{u.first_name} {u.last_name}").strip() or u.username,
        } for u in qs[start:start + page_size]]
        return Response({
            "count": total, "page": page, "page_size": page_size, "results": items,
        })


class AdminOrgListaView(APIView):
    """GET /api/admin/org/<entidad>/ — lista paginada.
    POST /api/admin/org/<entidad>/ — crea registro.

    entidad ∈ {dependencias, subgrupos, funcionarios, organizaciones,
                proveedores, beneficiarios}.
    """
    permission_classes = [ModuloRequiredPermission("org_admin")]

    def post(self, request, entidad):
        from apps.login.models.funcionario import (
            Dependencia, Subgrupo, Funcionario, TipoFuncionario,
        )
        try:
            from apps.login.models.contratos import (
                Organizacion, Proveedor, Beneficiario,
            )
        except Exception:
            Organizacion = Proveedor = Beneficiario = None  # noqa

        d = request.data or {}

        try:
            if entidad == "dependencias":
                if not d.get("nombre"):
                    return Response({"detail": "nombre obligatorio."},
                                    status=status.HTTP_400_BAD_REQUEST)
                obj = Dependencia.objects.create(nombre=d["nombre"].strip())
                return Response({"id": obj.id, "detail": "Dependencia creada."},
                                status=status.HTTP_201_CREATED)

            if entidad == "subgrupos":
                if not d.get("nombre") or not d.get("dependencia_id"):
                    return Response({"detail": "nombre y dependencia_id obligatorios."},
                                    status=status.HTTP_400_BAD_REQUEST)
                obj = Subgrupo.objects.create(
                    nombre=d["nombre"].strip(),
                    dependencia_id=int(d["dependencia_id"]),
                )
                return Response({"id": obj.id, "detail": "Subgrupo creado."},
                                status=status.HTTP_201_CREATED)

            if entidad == "funcionarios":
                if not d.get("persona_id"):
                    return Response({"detail": "persona_id obligatorio."},
                                    status=status.HTTP_400_BAD_REQUEST)
                obj = Funcionario.objects.create(
                    persona_id=int(d["persona_id"]),
                    tipo_funcionario_id=d.get("tipo_funcionario_id") or None,
                    activo=True,
                )
                # subgrupo / dependencia se setean si existen como FKs
                if d.get("subgrupo_id"):
                    obj.subgrupo_id = int(d["subgrupo_id"])
                if d.get("dependencia_id"):
                    obj.dependencia_id = int(d["dependencia_id"])
                obj.save()
                return Response({"id": obj.id, "detail": "Funcionario creado."},
                                status=status.HTTP_201_CREATED)

            if entidad == "organizaciones" and Organizacion:
                if not d.get("nombre"):
                    return Response({"detail": "nombre obligatorio."},
                                    status=status.HTTP_400_BAD_REQUEST)
                obj = Organizacion.objects.create(
                    nombre=d["nombre"].strip(),
                    nit=d.get("nit") or "",
                    correo=d.get("correo") or "",
                    telefono=d.get("telefono") or "",
                )
                return Response({"id": obj.id, "detail": "Organización creada."},
                                status=status.HTTP_201_CREATED)

            if entidad == "proveedores" and Proveedor:
                if not d.get("nombre") or not d.get("nit"):
                    return Response({"detail": "nombre y nit obligatorios."},
                                    status=status.HTTP_400_BAD_REQUEST)
                obj = Proveedor.objects.create(
                    nombre=d["nombre"].strip(),
                    nit=d["nit"].strip(),
                    tipo_persona=d.get("tipo_persona") or "NATURAL",
                    direccion=d.get("direccion") or "",
                )
                return Response({"id": obj.id, "detail": "Proveedor creado."},
                                status=status.HTTP_201_CREATED)

            if entidad == "beneficiarios" and Beneficiario:
                tipo = (d.get("tipo") or "").strip().upper()
                if tipo not in ("PERSONA", "ORGANIZACION", "PROVEEDOR"):
                    return Response(
                        {"detail": "tipo debe ser PERSONA, ORGANIZACION o PROVEEDOR."},
                        status=status.HTTP_400_BAD_REQUEST)
                req = ("tipo_documento_codigo", "numero_documento", "nombre_legal")
                falta = [k for k in req if not d.get(k)]
                if falta:
                    return Response(
                        {"detail": f"Campos obligatorios: {', '.join(falta)}"},
                        status=status.HTTP_400_BAD_REQUEST)
                # FK polimórfico según tipo: el constraint de BD
                # (ck_beneficiario_fk_por_tipo) exige que el FK del tipo
                # esté lleno (solo ese, los otros 2 NULL).
                fk_key, fk_val = {
                    "PERSONA": ("persona_id", d.get("persona_id")),
                    "ORGANIZACION": ("organizacion_id", d.get("organizacion_id")),
                    "PROVEEDOR": ("proveedor_id", d.get("proveedor_id")),
                }[tipo]
                if not fk_val:
                    return Response(
                        {"detail": f"{fk_key} es obligatorio cuando tipo={tipo}."},
                        status=status.HTTP_400_BAD_REQUEST)
                extra = {fk_key: fk_val}
                obj = Beneficiario.objects.create(
                    tipo=tipo,
                    tipo_documento_id=d["tipo_documento_codigo"],
                    numero_documento=str(d["numero_documento"]).strip(),
                    nombre_legal=d["nombre_legal"].strip(),
                    correo=d.get("correo") or None,
                    telefono=d.get("telefono") or None,
                    **extra,
                )
                return Response({"id": obj.id, "detail": "Beneficiario creado."},
                                status=status.HTTP_201_CREATED)

            return Response({"detail": "Entidad no soportada para POST."},
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, entidad, obj_id):
        """Edita los campos permitidos de un registro existente."""
        from apps.login.models.funcionario import Dependencia, Subgrupo, Funcionario
        try:
            from apps.login.models.contratos import Organizacion, Proveedor, Beneficiario
        except Exception:
            Organizacion = Proveedor = Beneficiario = None  # noqa
        d = request.data or {}
        modelos = {
            "dependencias": (Dependencia, ("nombre",)),
            "subgrupos": (Subgrupo, ("nombre", "dependencia_id")),
            "funcionarios": (Funcionario, ("tipo_funcionario_id", "subgrupo_id", "dependencia_id", "activo")),
            "organizaciones": (Organizacion, ("nombre", "nit", "correo", "telefono")),
            "proveedores": (Proveedor, ("nombre", "nit", "tipo_persona", "direccion")),
            "beneficiarios": (Beneficiario, ("nombre_legal", "correo", "telefono")),
        }
        if entidad not in modelos or modelos[entidad][0] is None:
            return Response({"detail": "Entidad no soportada para editar."}, status=400)
        Model, campos = modelos[entidad]
        obj = get_object_or_404(Model, pk=obj_id)
        try:
            for c in campos:
                if c in d:
                    v = d[c]
                    if c.endswith("_id"):
                        v = int(v) if v else None
                    elif c == "activo":
                        v = bool(v)
                    elif isinstance(v, str):
                        v = v.strip()
                    setattr(obj, c, v)
            obj.save()
        except Exception as e:
            return Response({"detail": str(e)}, status=400)
        return Response({"id": obj.id, "detail": "Actualizado correctamente."})

    def get(self, request, entidad):
        from apps.login.models.funcionario import (
            Dependencia, Subgrupo, Funcionario,
        )
        try:
            from apps.login.models.contratos import (
                Organizacion, Proveedor, Beneficiario,
            )
        except Exception:
            Organizacion = Proveedor = Beneficiario = None  # noqa

        q = (request.query_params.get("q") or "").strip()
        page = max(int(request.query_params.get("page", "1") or "1"), 1)
        page_size = min(int(request.query_params.get("page_size", "50") or "50"), 200)

        def paginar(qs, mapper):
            total = qs.count()
            start = (page - 1) * page_size
            items = [mapper(o) for o in qs[start:start + page_size]]
            return Response({
                "entidad": entidad, "count": total,
                "page": page, "page_size": page_size, "results": items,
            })

        if entidad == "dependencias":
            qs = Dependencia.objects.all().order_by("nombre")
            if q: qs = qs.filter(nombre__icontains=q)
            return paginar(qs, lambda d: {"id": d.id, "nombre": d.nombre})

        if entidad == "subgrupos":
            qs = Subgrupo.objects.select_related("dependencia").order_by("nombre")
            if q: qs = qs.filter(nombre__icontains=q)
            return paginar(qs, lambda s: {
                "id": s.id, "nombre": s.nombre,
                "dependencia": (s.dependencia.nombre if s.dependencia_id else None),
            })

        if entidad == "funcionarios":
            qs = (Funcionario.objects
                  .select_related("persona", "subgrupo")
                  .filter(activo=True)
                  .order_by("persona__apellido1", "persona__nombre1"))
            if q:
                qs = qs.filter(
                    Q(persona__nombre1__icontains=q)
                    | Q(persona__apellido1__icontains=q)
                )
            def mf(f):
                p = f.persona
                nombre = (f"{p.nombre1 or ''} {p.apellido1 or ''}").strip() if p else "—"
                return {
                    "id": f.id, "nombre": nombre,
                    "subgrupo": (f.subgrupo.nombre if f.subgrupo_id else None),
                }
            return paginar(qs, mf)

        if entidad == "organizaciones" and Organizacion:
            qs = Organizacion.objects.all().order_by("nombre")
            if q: qs = qs.filter(nombre__icontains=q)
            return paginar(qs, lambda o: {
                "id": o.id, "nombre": o.nombre,
                "nit": getattr(o, "nit", None),
            })

        if entidad == "proveedores" and Proveedor:
            qs = Proveedor.objects.all().order_by("nombre")
            if q: qs = qs.filter(nombre__icontains=q)
            return paginar(qs, lambda o: {
                "id": o.id, "nombre": o.nombre,
                "nit": getattr(o, "nit", None),
            })

        if entidad == "beneficiarios" and Beneficiario:
            qs = Beneficiario.objects.all().order_by("-id")[:1000]  # pesado
            return paginar(qs, lambda b: {
                "id": b.id, "tipo": getattr(b, "tipo", None),
            })

        return Response({"detail": "Entidad no soportada."},
                        status=status.HTTP_400_BAD_REQUEST)


class AdminPersonasSearchView(APIView):
    """GET /api/admin/personas/?q= — búsqueda paginada de personas."""
    permission_classes = [ModuloRequiredPermission("personas_registro")]

    def get(self, request):
        from apps.login.models import Persona
        q = (request.query_params.get("q") or "").strip()
        page = max(int(request.query_params.get("page", "1") or "1"), 1)
        page_size = min(int(request.query_params.get("page_size", "50") or "50"), 200)
        qs = (Persona.objects
              .select_related("persona_documento", "persona_documento__tipo_documento"))
        if q:
            qs = qs.filter(
                Q(nombre1__icontains=q) | Q(apellido1__icontains=q)
                | Q(persona_documento__numero_documento__icontains=q)
            )
        qs = qs.order_by("apellido1", "nombre1")
        total = qs.count()
        start = (page - 1) * page_size
        items = []
        for p in qs[start:start + page_size]:
            doc_num = (p.persona_documento.numero_documento
                       if p.persona_documento else None)
            items.append({
                "id": p.id,
                "nombre": (f"{p.nombre1 or ''} {p.nombre2 or ''} "
                           f"{p.apellido1 or ''} {p.apellido2 or ''}").strip(),
                "documento": doc_num,
            })
        return Response({
            "count": total, "page": page, "page_size": page_size,
            "results": items,
        })


# ─────────────────────────────────────────────────────────────────────────
# Etapa D — Eventos CRUD + listado + tipos (Angular nativo)
# ─────────────────────────────────────────────────────────────────────────


def _serializar_evento_lite(ev):
    funcionario_nombre = ""
    if ev.funcionario_id and ev.funcionario.persona:
        p = ev.funcionario.persona
        funcionario_nombre = f"{p.nombre1 or ''} {p.apellido1 or ''}".strip()
    return {
        "id": ev.id,
        "nombre": ev.nombre,
        "tipo_codigo": ev.tipo_evento_id,
        "tipo_nombre": (ev.tipo_evento.nombre if ev.tipo_evento_id else None),
        "subgrupo_id": ev.subgrupo_id,
        "subgrupo_nombre": (ev.subgrupo.nombre if ev.subgrupo_id else None),
        "dependencia_id": ev.dependencia_id,
        "dependencia_nombre": (ev.dependencia.nombre if ev.dependencia_id else None),
        "linea_id": ev.linea_id,
        "linea_nombre": (ev.linea.nombre if ev.linea_id else None),
        "funcionario_id": ev.funcionario_id,
        "funcionario_nombre": funcionario_nombre,
        "fecha_inicio": ev.fecha_inicio.isoformat() if ev.fecha_inicio else None,
        "fecha_fin": ev.fecha_fin.isoformat() if ev.fecha_fin else None,
        "actividad_plan_id": ev.actividad_plan_id,
        "activo": ev.activo,
    }


class EventoListaView(APIView):
    permission_classes = [ModuloRequiredPermission("eventos")]

    def get(self, request):
        qs = (Evento.objects
              .select_related("tipo_evento", "subgrupo", "dependencia",
                              "funcionario__persona", "linea", "actividad_plan")
              .order_by("-fecha_inicio", "-id"))

        q = (request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(nombre__icontains=q)
                | Q(tipo_evento__nombre__icontains=q)
                | Q(subgrupo__nombre__icontains=q)
            )

        tipo = request.query_params.get("tipo")
        if tipo:
            qs = qs.filter(tipo_evento_id=tipo)

        dep = request.query_params.get("dependencia_id")
        if dep:
            try: qs = qs.filter(dependencia_id=int(dep))
            except ValueError: pass

        sub = request.query_params.get("subgrupo_id")
        if sub:
            try: qs = qs.filter(subgrupo_id=int(sub))
            except ValueError: pass

        activo = request.query_params.get("activo")
        if activo in ("1", "true"):
            qs = qs.filter(activo=True)
        elif activo in ("0", "false"):
            qs = qs.filter(activo=False)

        page = max(int(request.query_params.get("page", "1") or "1"), 1)
        page_size = min(int(request.query_params.get("page_size", "50") or "50"), 200)
        total = qs.count()
        start = (page - 1) * page_size
        items = [_serializar_evento_lite(e) for e in qs[start:start + page_size]]

        return Response({
            "count": total,
            "page": page,
            "page_size": page_size,
            "results": items,
        })


class EventoCRUDView(APIView):
    permission_classes = [ModuloRequiredPermission("eventos")]

    _CAMPOS_EDITABLES = (
        "nombre", "descripcion", "tipo_evento_id", "dependencia_id",
        "subgrupo_id", "linea_id", "funcionario_id", "lugar_incidencia_id",
        "actividad_plan_id", "indicador_id", "fecha_inicio", "fecha_fin",
        "magnitud_aportada", "sector_caracterizacion", "activo",
        # Campos extra data-driven por tipo (evento_creacion_schema):
        "cupo_maximo", "festival_id", "escuela_id",
    )

    def get(self, request, evento_id):
        ev = get_object_or_404(
            Evento.objects.select_related(
                "tipo_evento", "subgrupo", "dependencia",
                "funcionario__persona", "linea", "actividad_plan", "indicador",
                "lugar_incidencia__geo_referenciacion",
            ),
            pk=evento_id,
        )
        data = _serializar_evento_lite(ev)
        data.update({
            "descripcion": ev.descripcion or "",
            "lugar_incidencia_id": ev.lugar_incidencia_id,
            "indicador_id": ev.indicador_id,
            "indicador_nombre": (ev.indicador.nombre if ev.indicador_id else None),
            "magnitud_aportada": (str(ev.magnitud_aportada)
                                  if ev.magnitud_aportada is not None else None),
            "sector_caracterizacion": ev.sector_caracterizacion,
            # Campos extra data-driven (para precargar al editar).
            "cupo_maximo": ev.cupo_maximo,
            "festival_id": ev.festival_id,
            "escuela_id": ev.escuela_id,
            # Proyecto derivado de la actividad_plan (para precargar la cascada
            # presupuestal al editar).
            "proyecto_id": (ev.actividad_plan.proyecto_id
                            if ev.actividad_plan_id else None),
        })
        # Ubicación: precarga el mapa al editar.
        if ev.lugar_incidencia_id and ev.lugar_incidencia.geo_referenciacion_id:
            geo = ev.lugar_incidencia.geo_referenciacion
            data["latitud"] = float(geo.latitud) if geo.latitud is not None else None
            data["longitud"] = float(geo.longitud) if geo.longitud is not None else None
            data["direccion"] = geo.direccion_texto or ""
        return Response(data)

    def _crear_lugar_incidencia(self, lat, lng, direccion):
        """Crea la cadena geo Lugar→GeoReferenciacion→LugarIncidencia
        y devuelve el id. None si lat/lng faltan."""
        if lat is None or lng is None:
            return None
        from decimal import Decimal
        from apps.georeferenciacion.models.models_localizacion import (
            GeoReferenciacion, LugarIncidencia,
        )
        from apps.georeferenciacion.utils import (
            crear_con_fallback_id, get_lugar_generico,
        )
        lugar = get_lugar_generico()
        geo = crear_con_fallback_id(
            GeoReferenciacion,
            latitud=Decimal(str(lat)),
            longitud=Decimal(str(lng)),
            direccion_texto=direccion or "",
            fuente="manual", precision="manual_click",
            lugar=lugar,
        )
        li = crear_con_fallback_id(LugarIncidencia, geo_referenciacion=geo)
        return li.id

    def _vincular_contrato(self, evento, contrato_id):
        if not contrato_id or not evento.actividad_plan_id:
            return
        from apps.presupuesto.models.sql import ContratoActividadPlan
        try:
            ContratoActividadPlan.objects.get_or_create(
                contrato_id=int(contrato_id),
                actividad_plan_id=evento.actividad_plan_id,
                defaults={"monto": 0, "activo": True},
            )
        except Exception:
            pass  # no rompe el create del evento si la vinculación falla

    def post(self, request):
        from django.db import transaction
        data = {k: v for k, v in (request.data or {}).items()
                if k in self._CAMPOS_EDITABLES}
        if not data.get("nombre"):
            return Response({"detail": "El campo nombre es obligatorio."},
                            status=status.HTTP_400_BAD_REQUEST)
        # Si llega lat/lng y no hay lugar_incidencia_id, crear cadena geo.
        extra = request.data or {}
        try:
            with transaction.atomic():
                if not data.get("lugar_incidencia_id"):
                    li_id = self._crear_lugar_incidencia(
                        extra.get("latitud"), extra.get("longitud"),
                        extra.get("direccion"),
                    )
                    if li_id:
                        data["lugar_incidencia_id"] = li_id
                if not data.get("lugar_incidencia_id"):
                    # Sin coordenadas: ubicar en la Alcaldía para que el
                    # evento siempre aparezca en el mapa.
                    from apps.georeferenciacion.utils import (
                        get_lugar_incidencia_default,
                    )
                    li_def = get_lugar_incidencia_default()
                    if li_def:
                        data["lugar_incidencia_id"] = li_def.id
                ev = Evento.objects.create(**data)
                # Alimenta el KPI: cada evento con indicador suma su avance
                # (paridad con el flujo Django legacy — sin esto la cadena de
                # reporte Proyecto→Meta→KPI←Evento queda incompleta).
                if data.get("indicador_id") and data.get("magnitud_aportada"):
                    from apps.presupuesto.models import AvanceIndicador
                    from datetime import date
                    hoy = date.today()
                    AvanceIndicador.objects.create(
                        indicador_id=data["indicador_id"],
                        evento_id=ev.id,
                        magnitud_aportada=data["magnitud_aportada"],
                        fecha_aporte=hoy,
                        periodo=hoy.strftime("%Y-%m"),
                        origen="EVENTO",
                    )
                self._vincular_contrato(ev, extra.get("contrato_financia"))
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": ev.id, "detail": "Evento creado."},
                        status=status.HTTP_201_CREATED)

    def _sync_avance(self, ev, old_magnitud):
        """Si cambió la magnitud de un evento con KPI, ajusta su AvanceIndicador
        (origen='AJUSTE') — paridad con el flujo Django para no romper las matrices."""
        if not ev.indicador_id or ev.magnitud_aportada is None:
            return
        if str(old_magnitud) == str(ev.magnitud_aportada):
            return
        from apps.presupuesto.models import AvanceIndicador
        from datetime import date
        av = (AvanceIndicador.objects
              .filter(evento_id=ev.id, indicador_id=ev.indicador_id)
              .order_by("-id").first())
        if av:
            av.magnitud_aportada = ev.magnitud_aportada
            av.origen = "AJUSTE"
            av.observaciones = f"Ajuste por edición del evento {ev.id}"
            av.save(update_fields=["magnitud_aportada", "origen", "observaciones"])
        else:
            hoy = date.today()
            AvanceIndicador.objects.create(
                indicador_id=ev.indicador_id, evento_id=ev.id,
                magnitud_aportada=ev.magnitud_aportada,
                fecha_aporte=hoy, periodo=hoy.strftime("%Y-%m"),
                origen="AJUSTE",
                observaciones=f"Ajuste por edición del evento {ev.id}",
            )

    def patch(self, request, evento_id):
        from django.db import transaction
        ev = get_object_or_404(Evento, pk=evento_id)
        old_magnitud = ev.magnitud_aportada
        data = {k: v for k, v in (request.data or {}).items()
                if k in self._CAMPOS_EDITABLES}
        extra = request.data or {}
        # Si llega lat/lng nuevos y no hay lugar_incidencia_id,
        # se crea uno nuevo y se reemplaza.
        if (not data.get("lugar_incidencia_id")
            and extra.get("latitud") is not None
            and extra.get("longitud") is not None):
            li_id = self._crear_lugar_incidencia(
                extra.get("latitud"), extra.get("longitud"),
                extra.get("direccion"),
            )
            if li_id:
                data["lugar_incidencia_id"] = li_id
        for k, v in data.items():
            setattr(ev, k, v)
        try:
            with transaction.atomic():
                ev.save()
                self._vincular_contrato(ev, extra.get("contrato_financia"))
                self._sync_avance(ev, old_magnitud)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": ev.id, "detail": "Evento actualizado."})


class EventoToggleActivoView(APIView):
    permission_classes = [ModuloRequiredPermission("eventos")]

    def post(self, request, evento_id):
        ev = get_object_or_404(Evento, pk=evento_id)
        ev.activo = not bool(ev.activo)
        ev.save(update_fields=["activo"])
        return Response({"id": ev.id, "activo": ev.activo})


class EventoQRView(APIView):
    """QR del evento como JSON: URL pública + PNG base64.

    Reemplaza la página Django `qr_evento` (template `eventos/qr_evento.html`).
    La URL pública la resuelve `_url_publica_por_tipo`, así que para un evento
    de Banco apunta al form Angular `/app/p/banco/<id>`.
    """
    permission_classes = [ModuloRequiredPermission("eventos")]

    def get(self, request, evento_id):
        import base64
        import io

        import qrcode

        from apps.login.views.eventos._helpers import _url_publica_por_tipo

        ev = get_object_or_404(
            Evento.objects.select_related("tipo_evento", "funcionario__persona"),
            pk=evento_id,
        )
        path = _url_publica_por_tipo(ev.tipo_evento, ev.id)
        url_publica = request.build_absolute_uri(path)

        img = qrcode.make(url_publica)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_base64 = base64.b64encode(buf.getvalue()).decode()

        func = getattr(ev, "funcionario", None)
        persona = getattr(func, "persona", None) if func else None
        funcionario_nombre = None
        if persona:
            funcionario_nombre = " ".join(
                filter(None, [getattr(persona, "nombre1", ""), getattr(persona, "apellido1", "")])
            ).strip() or None

        return Response({
            "evento": {
                "id": ev.id,
                "nombre": ev.nombre,
                "fecha_inicio": ev.fecha_inicio,
                "fecha_fin": getattr(ev, "fecha_fin", None),
                "tipo": ev.tipo_evento.nombre if ev.tipo_evento else None,
                "tipo_codigo": ev.tipo_evento.codigo if ev.tipo_evento else None,
                "funcionario": funcionario_nombre,
                "activo": ev.activo,
            },
            "url_publica": url_publica,
            "url_publica_path": path,
            "qr_base64": qr_base64,
        })


class TiposEventoCRUDView(APIView):
    permission_classes = [ModuloRequiredPermission("tipos_evento")]

    _EDITABLES = (
        "nombre", "descripcion", "icono", "activo", "orden",
        "permite_caracterizacion", "permite_inscripcion", "permite_qr",
        "requiere_actividad_plan",
    )

    def get(self, request):
        from django.db.models import Count
        from apps.login.models.evento import TipoEvento
        qs = (TipoEvento.objects
              .annotate(eventos_count=Count("eventos"))
              .order_by("-activo", "nombre"))
        items = [{
            "codigo": t.codigo, "nombre": t.nombre,
            "descripcion": t.descripcion or "", "icono": t.icono,
            "color_hex": t.color_hex, "activo": t.activo, "orden": t.orden,
            "permite_caracterizacion": t.permite_caracterizacion,
            "permite_inscripcion": t.permite_inscripcion,
            "permite_qr": t.permite_qr,
            "requiere_actividad_plan": t.requiere_actividad_plan,
            "eventos_count": t.eventos_count,
        } for t in qs]
        return Response({"count": len(items), "results": items})

    def post(self, request):
        from apps.login.models.evento import TipoEvento
        data = request.data or {}
        codigo = (data.get("codigo") or "").strip().upper()
        if not codigo or not data.get("nombre"):
            return Response({"detail": "codigo y nombre son obligatorios."},
                            status=status.HTTP_400_BAD_REQUEST)
        attrs = {k: data[k] for k in self._EDITABLES if k in data}
        # `color_hex` es property read-only; la columna real es `color`.
        if data.get("color_hex") or data.get("color"):
            attrs["color"] = data.get("color_hex") or data.get("color")
        if TipoEvento.objects.filter(codigo=codigo).exists():
            return Response({"detail": "Ya existe un tipo con ese código."},
                            status=status.HTTP_400_BAD_REQUEST)
        t = TipoEvento.objects.create(codigo=codigo, **attrs)
        return Response({"codigo": t.codigo, "detail": "Tipo creado."},
                        status=status.HTTP_201_CREATED)


class TipoEventoDetalleView(APIView):
    permission_classes = [ModuloRequiredPermission("tipos_evento")]

    def patch(self, request, codigo):
        from apps.login.models.evento import TipoEvento
        t = get_object_or_404(TipoEvento, codigo=codigo)
        data = request.data or {}
        for k in TiposEventoCRUDView._EDITABLES:
            if k in data:
                setattr(t, k, data[k])
        if "color_hex" in data or "color" in data:
            t.color = data.get("color_hex") or data.get("color")
        t.save()
        return Response({"codigo": t.codigo, "detail": "Tipo actualizado."})


# ─────────────────────────────────────────────────────────────────────────
# Etapa D — Caracterizaciones por evento Angular nativo
# ─────────────────────────────────────────────────────────────────────────


@extend_schema(
    tags=["Caracterizaciones"],
    summary="Caracterizaciones capturadas para un evento",
    responses={200: OpenApiTypes.OBJECT},
)
class CaracterizacionesPorEventoView(APIView):
    """`GET /api/eventos/<id>/caracterizaciones/`

    Replica la vista HTML `caracterizaciones_por_evento` para Angular.
    El evento debe ser tipo con `permite_caracterizacion` y tener
    `sector_caracterizacion` definido.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, evento_id):
        from apps.caracterizacion.models import (
            CaracterizacionCultura, CaracterizacionDeporte,
            CaracterizacionMujer, CaracterizacionSalud,
            CaracterizacionPoblacional,
            CaracterizacionParticipacionCiudadana,
        )
        from apps.caracterizacion.sectores import SECTORES_LABEL
        from apps.login.models import Persona

        evento = get_object_or_404(
            Evento.objects.select_related("tipo_evento", "subgrupo"),
            pk=evento_id,
        )

        if not evento.tipo_evento or not evento.tipo_evento.permite_caracterizacion:
            return Response(
                {"detail": "Este evento no es de tipo Caracterización."},
                status=status.HTTP_404_NOT_FOUND,
            )

        SECTOR_MODELS = {
            "cultura": CaracterizacionCultura,
            "deporte": CaracterizacionDeporte,
            "mujer": CaracterizacionMujer,
            "salud": CaracterizacionSalud,
            "poblacional": CaracterizacionPoblacional,
            "participacion_ciudadana": CaracterizacionParticipacionCiudadana,
        }
        sector = (evento.sector_caracterizacion or "").strip().lower() or None
        Modelo = SECTOR_MODELS.get(sector) if sector else None

        items = []
        if Modelo is not None:
            rows = list(Modelo.objects.filter(evento_id=evento_id).order_by("-id"))
            persona_ids = [r.persona_id for r in rows if r.persona_id]
            personas = {
                p.id: p for p in Persona.objects
                    .filter(id__in=persona_ids)
                    .select_related("persona_documento",
                                    "persona_documento__tipo_documento")
            }
            for r in rows:
                p = personas.get(r.persona_id)
                doc_numero = (p.persona_documento.numero_documento
                              if p and p.persona_documento else "—")
                doc_tipo = (p.persona_documento.tipo_documento.codigo
                            if p and p.persona_documento and p.persona_documento.tipo_documento
                            else "—")
                nombre = (
                    f"{p.nombre1 or ''} {p.nombre2 or ''} "
                    f"{p.apellido1 or ''} {p.apellido2 or ''}".strip()
                    if p else "—"
                )
                items.append({
                    "id": r.id,
                    "persona_id": r.persona_id,
                    "doc_numero": doc_numero,
                    "doc_tipo": doc_tipo,
                    "nombre_completo": nombre,
                    "created_at": getattr(r, "created_at", None)
                        and r.created_at.isoformat(),
                })

        return Response({
            "evento": {
                "id": evento.id,
                "nombre": evento.nombre,
                "tipo_codigo": evento.tipo_evento_id,
                "tipo_nombre": evento.tipo_evento.nombre,
                "subgrupo": (evento.subgrupo.nombre if evento.subgrupo_id else None),
            },
            "sector": sector,
            "sector_label": SECTORES_LABEL.get(sector) if sector else None,
            "total": len(items),
            "items": items,
        })


# ─────────────────────────────────────────────────────────────────────────
# Etapa D — Cursos del docente Angular nativo
# ─────────────────────────────────────────────────────────────────────────


@extend_schema(
    tags=["Cursos"],
    summary="Cursos del docente actual (CURSO/CAPACITACION asignados)",
    responses={200: OpenApiTypes.OBJECT},
)
class MisCursosView(APIView):
    """`GET /api/cursos/mios/` — cursos del docente actual.

    Replica la lógica de la view HTML `mis_cursos`: filtra por
    funcionario.persona_id = request.user.persona_id, devuelve por cada
    curso su resumen (inscritos, sesiones totales, sesiones pasadas).
    Si el usuario es superuser o no tiene persona vinculada, ve todos
    los cursos vivos.

    Requiere módulo `cursos`.
    """
    permission_classes = [ModuloRequiredPermission("cursos")]

    def get(self, request):
        from apps.login.services.curso_sesiones import (
            mis_cursos_de_docente, resumen_curso,
        )

        cursos = mis_cursos_de_docente(request.user)
        out = []
        for c in cursos[:200]:
            r = resumen_curso(c.id)
            funcionario_nombre = ""
            if c.funcionario_id and c.funcionario.persona:
                p = c.funcionario.persona
                funcionario_nombre = f"{p.nombre1 or ''} {p.apellido1 or ''}".strip()
            out.append({
                "id": c.id,
                "nombre": c.nombre,
                "tipo_codigo": c.tipo_evento_id,
                "tipo_nombre": (c.tipo_evento.nombre if c.tipo_evento_id else None),
                "subgrupo": (c.subgrupo.nombre if c.subgrupo_id else None),
                "fecha_inicio": c.fecha_inicio.isoformat() if c.fecha_inicio else None,
                "fecha_fin": c.fecha_fin.isoformat() if c.fecha_fin else None,
                "funcionario_nombre": funcionario_nombre,
                "inscritos": r["inscritos_count"],
                "en_espera": r["en_espera_count"],
                "cupo_maximo": r["cupo_maximo"],
                "sesiones": r["sesiones_count"],
                "pasadas": r["sesiones_pasadas"],
                "activo": c.activo,
            })

        return Response({"count": len(out), "results": out})


@extend_schema(
    tags=["Cursos"],
    summary="Detalle del curso (header + resumen agregado)",
    responses={200: OpenApiTypes.OBJECT},
)
class CursoDetalleView(APIView):
    """`GET /api/cursos/<id>/` — header + resumen agregado del curso."""
    permission_classes = [ModuloRequiredPermission("cursos")]

    def get(self, request, evento_id):
        from apps.login.services.curso_sesiones import resumen_curso

        evento = get_object_or_404(
            Evento.objects.select_related(
                "tipo_evento", "subgrupo", "funcionario__persona",
            ),
            pk=evento_id,
        )
        funcionario_nombre = ""
        if evento.funcionario_id and evento.funcionario.persona:
            p = evento.funcionario.persona
            funcionario_nombre = f"{p.nombre1 or ''} {p.apellido1 or ''}".strip()

        # URL pública del formulario de inscripción/caracterización del curso
        # (para Explorarte va a la caracterización cultura; para una
        # capacitación, al form de inscripción genérico). Sirve el botón
        # "Inscripción" del panel del curso.
        from apps.login.views.eventos._helpers import _url_publica_por_tipo
        url_path = _url_publica_por_tipo(evento.tipo_evento, evento.id)

        return Response({
            "id": evento.id,
            "nombre": evento.nombre,
            "descripcion": evento.descripcion or "",
            "tipo_codigo": evento.tipo_evento_id,
            "tipo_nombre": (evento.tipo_evento.nombre if evento.tipo_evento_id else None),
            "subgrupo": (evento.subgrupo.nombre if evento.subgrupo_id else None),
            "fecha_inicio": evento.fecha_inicio.isoformat() if evento.fecha_inicio else None,
            "fecha_fin": evento.fecha_fin.isoformat() if evento.fecha_fin else None,
            "funcionario_nombre": funcionario_nombre,
            "activo": evento.activo,
            "url_inscripcion": request.build_absolute_uri(url_path),
            "resumen": resumen_curso(evento.id),
        })

    def patch(self, request, evento_id):
        """Edita el cupo máximo y/o el docente asignado al curso.

        - `cupo_maximo`: cupo del curso (lista de espera cuando se llena).
        - `funcionario_id`: docente titular del curso (Evento.funcionario).
          Acepta null/"" para desasignar.
        """
        evento = get_object_or_404(Evento, pk=evento_id)
        update_fields = []
        if "cupo_maximo" in request.data:
            raw = request.data.get("cupo_maximo")
            if raw in (None, "", "null"):
                evento.cupo_maximo = None
            else:
                try:
                    cupo = int(raw)
                except (TypeError, ValueError):
                    return Response({"detail": "cupo_maximo inválido."}, status=400)
                if cupo < 0:
                    return Response({"detail": "El cupo no puede ser negativo."}, status=400)
                evento.cupo_maximo = cupo
            update_fields.append("cupo_maximo")
        if "funcionario_id" in request.data:
            raw = request.data.get("funcionario_id")
            if raw in (None, "", "null"):
                evento.funcionario_id = None
            else:
                from apps.login.models.funcionario import Funcionario
                try:
                    fid = int(raw)
                except (TypeError, ValueError):
                    return Response({"detail": "funcionario_id inválido."}, status=400)
                if not Funcionario.objects.filter(pk=fid, activo=True).exists():
                    return Response(
                        {"detail": "Funcionario no existe o está inactivo."}, status=400)
                evento.funcionario_id = fid
            update_fields.append("funcionario_id")
        if update_fields:
            evento.save(update_fields=update_fields)
        from apps.login.services.curso_sesiones import resumen_curso
        return Response({"id": evento.id, "resumen": resumen_curso(evento.id)})


# ─────────────────────────────────────────────────────────────────────────
# Etapa D — Hub de Actividades Angular nativo
# ─────────────────────────────────────────────────────────────────────────


@extend_schema(
    tags=["Actividades"],
    summary="Lista tipos de actividad disponibles para el usuario",
    responses={200: OpenApiTypes.OBJECT},
)
class ActividadesTiposView(APIView):
    """Devuelve catálogo `TipoEvento` con conteo de eventos vivos.

    Filtrado por módulos del usuario para no listar tipos a los que no
    tiene acceso. Replica la lógica del hub Django `hub_actividades`.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count, Q
        from apps.login.models.evento import Evento, TipoEvento
        from apps.login.services.permisos import get_modulos_usuario

        u = request.user
        if u.is_superuser:
            from apps.login.models.permisos import Modulo
            mods = set(Modulo.objects.filter(activo=True).values_list("codigo", flat=True))
        else:
            mods = get_modulos_usuario(u)

        # Rutas Angular nativas (servidas bajo /app/).
        admin_cards = [
            {"codigo": "_LISTAR_", "nombre": "Lista de actividades",
             "subtitulo": "Ver todas las actividades", "icono": "fa-list",
             "color": "info", "visible": "eventos" in mods,
             "ruta": "/eventos"},
            {"codigo": "_CREAR_", "nombre": "Crear actividad",
             "subtitulo": "Registrar nueva actividad", "icono": "fa-plus-circle",
             "color": "success", "visible": "eventos" in mods,
             "ruta": "/eventos/nueva"},
            {"codigo": "_TIPOS_", "nombre": "Tipos de actividad",
             "subtitulo": "Catálogo de tipos", "icono": "fa-tags",
             "color": "warning", "visible": "tipos_evento" in mods,
             "ruta": "/eventos/tipos"},
        ]

        puede_abrir = bool(mods & {
            "eventos", "banco_iniciativas", "caracterizacion",
            "cursos", "eventos_asistencia",
        })
        tipos = []
        if puede_abrir:
            qs = (TipoEvento.objects.filter(activo=True)
                  .annotate(num_eventos=Count("eventos",
                            filter=Q(eventos__activo=True)))
                  .order_by("orden", "nombre"))
            for t in qs:
                # CURSO/CAPACITACION son cursos (aunque permitan caracterización
                # como Explorarte): se ven con el módulo cursos/eventos, no solo
                # con caracterizacion. El front redirige a /app/cursos.
                es_curso = t.codigo in ("CURSO", "CAPACITACION")
                if es_curso:
                    if not (mods & {"cursos", "eventos", "caracterizacion"}):
                        continue
                elif t.permite_caracterizacion and "caracterizacion" not in mods:
                    continue
                if t.codigo == "BANCO_INICIATIVAS" and not (
                    mods & {"banco_iniciativas", "eventos"}
                ):
                    continue
                if (not t.permite_caracterizacion
                        and t.codigo != "BANCO_INICIATIVAS"
                        and not es_curso
                        and "eventos" not in mods):
                    continue
                tipos.append({
                    "codigo": t.codigo,
                    "nombre": t.nombre,
                    "descripcion": (t.descripcion or "").strip(),
                    "icono": t.icono or "fa-folder",
                    "color_hex": t.color_hex,
                    "permite_caracterizacion": t.permite_caracterizacion,
                    "permite_inscripcion": t.permite_inscripcion,
                    "num_eventos": t.num_eventos,
                })

            # Unifica CURSO + CAPACITACION en UNA sola card: ambos van al mismo
            # panel (/app/cursos) y mis_cursos_de_docente ya los trata juntos.
            # No se tocan los códigos en BD; es solo la presentación del hub.
            merged = None
            unificado = []
            for t in tipos:
                if t["codigo"] in ("CURSO", "CAPACITACION"):
                    if merged is None:
                        merged = t
                        merged["codigo"] = "CURSO"  # la card lleva a /app/cursos
                        merged["nombre"] = "Cursos y capacitaciones"
                        merged["icono"] = "fa-chalkboard-teacher"
                        unificado.append(merged)
                    else:
                        merged["num_eventos"] += t["num_eventos"]
                else:
                    unificado.append(t)
            tipos = unificado

        payload = {
            "cards_admin": [c for c in admin_cards if c["visible"]],
            "tipos": tipos,
        }

        es_admin = u.is_superuser or u.groups.filter(name="Admin").exists()
        if es_admin:
            self._anexar_capa_sector(request, payload, tipos)

        return Response(payload)

    def _anexar_capa_sector(self, request, payload, tipos):
        from collections import defaultdict
        from django.db.models import Count
        from apps.login.models.evento import Evento
        from apps.login.models.funcionario import Subgrupo
        from apps.presupuesto.models.core import Proyecto
        from apps.dashboard.services.sector_colores import (
            SECTOR_COLORS, color_de_sector,
        )

        sector_param = request.GET.get("sector")
        try:
            sector_filtro = int(sector_param) if sector_param else None
        except (TypeError, ValueError):
            sector_filtro = None

        nombres = dict(Subgrupo.objects.values_list("id", "nombre"))

        proy_por_sub = {
            r["subgrupo_id"]: r["n"]
            for r in (Proyecto.objects.values("subgrupo_id")
                      .annotate(n=Count("id")))
        }
        ev_por_sub = {
            r["subgrupo_id"]: r["n"]
            for r in (Evento.objects.filter(activo=True).values("subgrupo_id")
                      .annotate(n=Count("id")))
        }

        sub_ids = set(proy_por_sub) | set(ev_por_sub)
        resumen = []
        for sid in sub_ids:
            nombre = nombres.get(sid) if sid is not None else None
            resumen.append({
                "subgrupo_id": sid,
                "nombre": nombre or "Sin sector",
                "color": color_de_sector(nombre),
                "num_proyectos": proy_por_sub.get(sid, 0),
                "num_eventos": ev_por_sub.get(sid, 0),
            })
        resumen.sort(key=lambda x: x["num_eventos"], reverse=True)
        payload["resumen_sector"] = resumen

        ev_qs = Evento.objects.filter(activo=True)
        if sector_filtro is not None:
            ev_qs = ev_qs.filter(subgrupo_id=sector_filtro)
        tipo_sub = defaultdict(lambda: defaultdict(int))
        for r in (ev_qs.values("tipo_evento_id", "subgrupo_id")
                  .annotate(n=Count("id"))):
            tipo_sub[r["tipo_evento_id"]][r["subgrupo_id"]] = r["n"]

        for t in tipos:
            por_sub = tipo_sub.get(t["codigo"], {})
            desglose = []
            total = 0
            for sid, cnt in por_sub.items():
                nombre = nombres.get(sid) if sid is not None else None
                desglose.append({
                    "subgrupo_id": sid,
                    "nombre": nombre or "Sin sector",
                    "color": color_de_sector(nombre),
                    "count": cnt,
                })
                total += cnt
            desglose.sort(key=lambda x: x["count"], reverse=True)
            t["por_sector"] = desglose
            if sector_filtro is not None:
                t["num_eventos"] = total

        payload["sector_colors"] = dict(SECTOR_COLORS)


@extend_schema(
    tags=["Actividades"],
    summary="Subgrupos con eventos del tipo dado, o sectores si CARACTERIZACION",
    responses={200: OpenApiTypes.OBJECT},
)
class SubgruposPorTipoView(APIView):
    """Para un `tipo` de actividad devuelve:

    - Si `permite_caracterizacion`: lista de sectores (cultura, deporte,
      mujer, salud, poblacional, participación) con su URL Angular.
    - Si no: lista de subgrupos con eventos vivos del tipo + conteo.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, codigo):
        from django.db.models import Count
        from apps.login.models.evento import Evento, TipoEvento
        from apps.login.models.funcionario import Subgrupo

        tipo = get_object_or_404(TipoEvento, codigo=codigo, activo=True)

        if tipo.permite_caracterizacion:
            from apps.caracterizacion.sectores import (
                SECTORES_IMPLEMENTADOS, SECTORES_LABEL,
                SECTORES_ICONO, SECTORES_DESC,
            )
            sectores = [
                {"codigo": s,
                 "nombre": SECTORES_LABEL.get(s, s),
                 "descripcion": SECTORES_DESC.get(s, ""),
                 "icono": SECTORES_ICONO.get(s, "fa-clipboard-list")}
                for s in SECTORES_IMPLEMENTADOS
            ]
            return Response({
                "tipo": {"codigo": tipo.codigo, "nombre": tipo.nombre,
                         "descripcion": (tipo.descripcion or "").strip(),
                         "permite_caracterizacion": True},
                "subgrupos": [],
                "sectores": sectores,
            })

        subs = (Subgrupo.objects
                .filter(eventos__tipo_evento_id=codigo, eventos__activo=True)
                .annotate(num_eventos=Count("eventos", filter=Q(
                    eventos__tipo_evento_id=codigo, eventos__activo=True)))
                .select_related("dependencia")
                .distinct()
                .order_by("nombre"))

        subgrupos = [{
            "id": s.id,
            "nombre": s.nombre,
            "dependencia_id": s.dependencia_id,
            "dependencia_nombre": (s.dependencia.nombre.title() if s.dependencia_id else None),
            "num_eventos": s.num_eventos,
        } for s in subs]

        return Response({
            "tipo": {"codigo": tipo.codigo, "nombre": tipo.nombre,
                     "descripcion": (tipo.descripcion or "").strip(),
                     "icono": tipo.icono, "color_hex": tipo.color_hex,
                     "permite_caracterizacion": False,
                     "permite_inscripcion": tipo.permite_inscripcion},
            "subgrupos": subgrupos,
            "sectores": [],
        })


@extend_schema(
    tags=["Actividades"],
    summary="Eventos del par (tipo, subgrupo) con líneas finas",
    responses={200: OpenApiTypes.OBJECT},
)
class EventosPorTipoSubgrupoView(APIView):
    """Lista eventos del par (tipo, subgrupo). Filtro opcional por línea
    fina (`?linea=<id>`). Devuelve estructura plana lista para tabla.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, codigo, subgrupo_id):
        from apps.login.models.evento import Evento, TipoEvento
        from apps.login.models.funcionario import Subgrupo, SubgrupoLinea

        tipo = get_object_or_404(TipoEvento, codigo=codigo, activo=True)
        subgrupo = get_object_or_404(Subgrupo, pk=subgrupo_id)

        linea_id = request.query_params.get("linea")
        try:
            linea_id_int = int(linea_id) if linea_id else None
        except (TypeError, ValueError):
            linea_id_int = None

        qs = (Evento.objects
              .filter(tipo_evento_id=codigo, subgrupo_id=subgrupo_id)
              .select_related("tipo_evento", "subgrupo", "dependencia",
                              "funcionario__persona", "actividad_plan", "linea")
              .order_by("-fecha_inicio", "-id"))
        if linea_id_int:
            qs = qs.filter(linea_id=linea_id_int)

        lineas = list(SubgrupoLinea.objects.filter(
            subgrupo_id=subgrupo_id, activo=True
        ).order_by("orden", "nombre").values("id", "nombre"))

        from apps.login.views.eventos._helpers import _url_publica_por_tipo
        eventos = []
        for ev in qs:
            funcionario_nombre = ""
            if ev.funcionario_id and ev.funcionario.persona:
                p = ev.funcionario.persona
                funcionario_nombre = f"{p.nombre1 or ''} {p.apellido1 or ''}".strip()
            eventos.append({
                "id": ev.id,
                "nombre": ev.nombre,
                "linea": (ev.linea.nombre if ev.linea_id else None),
                "linea_id": ev.linea_id,
                "fecha_inicio": ev.fecha_inicio.isoformat() if ev.fecha_inicio else None,
                "fecha_fin": ev.fecha_fin.isoformat() if ev.fecha_fin else None,
                "activo": ev.activo,
                "funcionario_nombre": funcionario_nombre,
                "actividad_plan_id": ev.actividad_plan_id,
                # Formulario público (QR) según el tipo: Banco→inscribir,
                # Caracterización→wizard del sector, Jóvenes→beca, etc.
                "url_publica": _url_publica_por_tipo(tipo, ev.id),
                "sector_caracterizacion": ev.sector_caracterizacion,
            })

        return Response({
            "tipo": {"codigo": tipo.codigo, "nombre": tipo.nombre,
                     "permite_caracterizacion": tipo.permite_caracterizacion,
                     "permite_inscripcion": tipo.permite_inscripcion},
            "subgrupo": {"id": subgrupo.id, "nombre": subgrupo.nombre,
                         "dependencia_nombre": (subgrupo.dependencia.nombre
                            if subgrupo.dependencia_id else None)},
            "lineas_disponibles": lineas,
            "linea_id_actual": linea_id_int,
            "eventos": eventos,
            "total": len(eventos),
        })




# ─────────────────────────────────────────────────────────────────────
# Etapa D — Quick wins: perfil/password, crear persona (organizador).
# ─────────────────────────────────────────────────────────────────────
class CambiarPasswordView(APIView):
    """POST /api/perfil/cambiar-password/ {actual, nueva}."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        actual = request.data.get("actual") or ""
        nueva = request.data.get("nueva") or ""
        if not request.user.check_password(actual):
            return Response({"detail": "La contraseña actual es incorrecta."}, status=400)
        if len(nueva) < 6:
            return Response({"detail": "La nueva contraseña debe tener al menos 6 caracteres."}, status=400)
        request.user.set_password(nueva)
        request.user.save(update_fields=["password"])
        return Response({"detail": "Contraseña actualizada correctamente."})


class PersonaCrearView(APIView):
    """POST /api/personas/crear/ — alta de persona (organizador).
    Reusa el flujo del padrón: busca por documento o crea Persona+Participante."""
    permission_classes = [ModuloRequiredPermission("personas_registro")]

    def get(self, request):
        # Catálogo de tipos de documento para el form.
        from apps.login.models.persona_documento import TipoDocumento
        return Response({"tipos_documento": [
            {"codigo": t.codigo, "nombre": t.nombre}
            for t in TipoDocumento.objects.all().order_by("nombre")]})

    def post(self, request):
        from django.db import transaction
        from apps.login.models.persona import Persona, Participante
        from apps.login.models.persona_documento import PersonaDocumento, TipoDocumento
        d = request.data or {}
        numero = str(d.get("numero_documento") or "").strip()
        nombre1 = str(d.get("nombre1") or "").strip()
        apellido1 = str(d.get("apellido1") or "").strip()
        if not numero or not nombre1 or not apellido1:
            return Response({"detail": "numero_documento, nombre1 y apellido1 son obligatorios."}, status=400)
        existente = Persona.objects.filter(persona_documento__numero_documento=numero).first()
        if existente:
            return Response({"id": existente.id, "detail": "La persona ya existía.", "ya_existia": True})
        try:
            with transaction.atomic():
                doc = PersonaDocumento.objects.filter(numero_documento=numero).first()
                if not doc:
                    tipo = (TipoDocumento.objects.filter(codigo=d.get("tipo_documento_codigo") or 1).first()
                            or TipoDocumento.objects.first())
                    doc = PersonaDocumento.objects.create(tipo_documento=tipo, numero_documento=numero)
                p = Persona.objects.create(
                    usuario=request.user, persona_documento=doc,
                    nombre1=nombre1, nombre2=(str(d.get("nombre2") or "").strip() or None),
                    apellido1=apellido1, apellido2=(str(d.get("apellido2") or "").strip() or None),
                    fecha_nacimiento=(d.get("fecha_nacimiento") or None),
                )
                Participante.objects.create(persona=p)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)
        return Response({"id": p.id, "detail": "Persona creada.", "ya_existia": False}, status=201)


class EventosInsightsView(APIView):
    """GET /api/eventos/insights/ — dashboard analítico de eventos (JSON)."""
    permission_classes = [ModuloRequiredPermission("eventos")]

    def get(self, request):
        from apps.login.views.eventos.insights import compute_eventos_insights
        return Response(compute_eventos_insights())


class EventoCreacionSchemaView(APIView):
    """`GET /api/eventos/creacion-schema/?tipo=<codigo>` — campos extra del
    tipo para el formulario de creación data-driven (evento_creacion_schema)."""
    permission_classes = [ModuloRequiredPermission("eventos")]

    def get(self, request):
        from apps.login.services.evento_creacion_schema import schema_creacion
        codigo = (request.query_params.get("tipo") or "").strip()
        return Response(schema_creacion(codigo))


class CursosInsightsView(APIView):
    """`GET /api/cursos/insights/` — dashboard analítico de Cursos y
    capacitaciones (JSON, nivel Power BI). Requiere módulo `cursos`."""
    permission_classes = [ModuloRequiredPermission("cursos")]

    def get(self, request):
        from apps.login.services.curso_sesiones import insights_cursos
        return Response(insights_cursos())


class CursoInscritosView(APIView):
    """Inscritos del curso + gestión de cupo/lista de espera.

    GET   /api/cursos/<id>/inscritos/         lista con estado.
    PATCH /api/cursos/<id>/inscritos/         {participante_evento_id, estado}
          → aceptar (espera→inscrito, respeta cupo) / rechazar (→rechazado).
    """
    permission_classes = [ModuloRequiredPermission("cursos")]

    def get(self, request, evento_id):
        from apps.login.services.curso_sesiones import inscritos_de_curso
        out = []
        for pe in inscritos_de_curso(evento_id):
            p = pe.participante.persona if pe.participante_id else None
            nombre = (f"{p.nombre1 or ''} {p.apellido1 or ''}".strip() if p else "")
            out.append({
                "id": pe.id,
                "persona_nombre": nombre or f"Participante #{pe.participante_id}",
                "estado": pe.estado,
                "fecha_registro": (pe.fecha_registro.isoformat()
                                   if pe.fecha_registro else None),
            })
        return Response({"results": out})

    def patch(self, request, evento_id):
        from apps.login.models.inscripcion_evento import ParticipanteEvento
        pe_id = request.data.get("participante_evento_id")
        nuevo = request.data.get("estado")
        if nuevo not in (ParticipanteEvento.INSCRITO, ParticipanteEvento.ESPERA,
                         ParticipanteEvento.RECHAZADO):
            return Response({"detail": "estado inválido."}, status=400)
        pe = get_object_or_404(ParticipanteEvento, pk=pe_id, evento_id=evento_id)
        # Al aceptar, respetar el cupo del curso.
        if nuevo == ParticipanteEvento.INSCRITO:
            ev = Evento.objects.filter(pk=evento_id).first()
            cupo = ev.cupo_maximo if ev else None
            if cupo is not None:
                ocup = (ParticipanteEvento.objects
                        .filter(evento_id=evento_id, estado=ParticipanteEvento.INSCRITO)
                        .exclude(pk=pe.pk).count())
                if ocup >= cupo:
                    return Response(
                        {"detail": "El cupo está lleno; cierra un inscrito antes de aceptar."},
                        status=400)
        pe.estado = nuevo
        pe.save(update_fields=["estado"])
        return Response({"id": pe.id, "estado": pe.estado})


class DocentesDisponiblesView(APIView):
    """`GET /api/cursos/docentes/` — funcionarios asignables como docente
    (para el selector 'asignar docente' del curso)."""
    permission_classes = [ModuloRequiredPermission("cursos")]

    def get(self, request):
        from apps.login.models.funcionario import Funcionario
        out = []
        for f in (Funcionario.objects.filter(activo=True)
                  .select_related("persona", "cargo").order_by("persona__apellido1")[:500]):
            p = f.persona
            nombre = (f"{p.nombre1 or ''} {p.apellido1 or ''}".strip() if p else "")
            out.append({
                "funcionario_id": f.id,
                "nombre": nombre or f"Funcionario #{f.id}",
                "cargo": (f.cargo.nombre if f.cargo_id else None),
            })
        return Response({"results": out})
