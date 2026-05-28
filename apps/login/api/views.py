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
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import ModuloRequiredPermission
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


class InscripcionEventoCreateView(APIView):
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
    permission_classes = [AllowAny]
    authentication_classes = []  # el endpoint es público; ignora JWT/session

    def post(self, request, evento_id):
        evento = get_object_or_404(Evento, pk=evento_id, activo=True)

        serializer = InscripcionPublicaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            resultado = inscribir_persona(
                evento_id=evento.id,
                datos=serializer.to_service_kwargs(),
                usuario_editor='publico',
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
        sesiones = Clase.objects.filter(evento_id=evento.id).order_by('fecha', 'hora_inicio')
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


class NotaDetalleView(APIView):
    """DELETE /api/notas/<id>/ — borra una evaluación.

    Requiere módulo `cursos`.
    """
    permission_classes = [ModuloRequiredPermission("cursos")]

    def delete(self, request, evaluacion_id):
        get_object_or_404(EvaluacionParticipante, pk=evaluacion_id)
        borrar_nota(evaluacion_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
