"""API del dominio FORMULACIÓN.

LOS TRES GATES son los mismos de `CapturarDatoContratoView`, y no se reinventan:

  1. **Scope de lectura** — el área tiene que estar en `subgrupos_visibles`.
  2. **Rol** — `puede_crear_en_area`: familia Coordinador Y el área en su scope.
  3. **Pertenencia** — la actividad del plan tiene que ser del área. Sin esto,
     cambiar un número en la petición deja formular sobre el plan de otra área;
     el hueco existió antes en `VincularContratoActividadPlanView`.

El permiso VIAJA EN EL PAYLOAD (`puede_formular`), por la misma razón que
`puede_registrar_etapa`: si la pantalla reimplementa la regla hay dos fuentes
de verdad sobre quién puede escribir, y la del navegador se puede editar.

Innovación no necesita nada especial: como superusuario, `subgrupos_visibles`
devuelve `None` y ve todo. La delegación a un área es una fila en
`usuario_pertenencia`, que ya existe (decisión del 2026-08-27).
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


def _area_y_gates(request, area, exigir_rol=True):
    """Resuelve el área y aplica los gates 1 y 2. Devuelve `(sub, error)`."""
    from apps.login.services.permisos import puede_crear_en_area
    from apps.login.services.scope import subgrupos_visibles
    from apps.presupuesto.services.modulos_area import resolver_area

    sub = resolver_area(area)
    if sub is None:
        return None, Response({"detail": "Esa área no existe."},
                              status=status.HTTP_404_NOT_FOUND)
    subs = subgrupos_visibles(request.user)
    if subs is not None and sub.id not in subs:
        return None, Response({"detail": "No tienes acceso a esta área."},
                              status=status.HTTP_403_FORBIDDEN)
    if exigir_rol and not puede_crear_en_area(request.user, sub.id):
        return None, Response(
            {"detail": "Para formular hace falta el rol de Coordinador de esta área."},
            status=status.HTTP_403_FORBIDDEN)
    return sub, None


def _actividades_del_area(subgrupo_id):
    """Las actividades del plan que pertenecen al área. Gate 3."""
    from apps.presupuesto.models.core import ActividadPlan, Proyecto
    pids = Proyecto.objects.filter(subgrupo_id=subgrupo_id).values_list("id", flat=True)
    return set(ActividadPlan.objects.filter(proyecto_id__in=pids)
               .values_list("id", flat=True))


def _fila(f, con_detalle=False):
    from apps.presupuesto.services.formulacion import completitud, destinos_validos, semaforo
    c = completitud(f)
    s = semaforo(f, c)
    fila = {
        "id": f.id,
        "codigo": f"F-{f.id:03d}",
        "actividad_plan_id": f.actividad_plan_id,
        "actividad": f.actividad_plan.descripcion,
        "vigencia": f.vigencia_id,
        "objeto": f.objeto,
        "valor_estimado": float(f.valor_estimado) if f.valor_estimado is not None else None,
        "estado": {"codigo": f.estado.codigo, "nombre": f.estado.nombre,
                   "orden": f.estado.orden,
                   "bloquea_contratacion": f.estado.bloquea_contratacion},
        "estado_fecha": f.estado_fecha.isoformat() if f.estado_fecha else None,
        "completitud": c["pct"],
        "completitud_detalle": {k: c[k] for k in
                                ("ok", "aplicables", "no_aplica", "revisados", "de")},
        "bloqueada": c["bloqueada"],
        "faltan_criticos": c["faltan_criticos"],
        "semaforo": s,
        "cancelada": f.cancelado_en is not None,
    }
    if con_detalle:
        fila["requisitos"] = c["requisitos"]
        fila["destinos"] = destinos_validos(f.estado_id)
        fila["responsable_funcionario_id"] = f.responsable_funcionario_id
    return fila


class FormulacionesAreaView(APIView):
    """`GET|POST /presupuesto/api/areas/<area>/formulaciones/`"""
    permission_classes = [IsAuthenticated]

    def get(self, request, area):
        from apps.login.services.permisos import puede_crear_en_area
        from apps.presupuesto.models import Formulacion
        from apps.presupuesto.services.formulacion import catalogo_estados

        # Leer NO exige el rol: un área puede ver lo suyo aunque no lo formule.
        sub, error = _area_y_gates(request, area, exigir_rol=False)
        if error:
            return error

        qs = (Formulacion.objects.filter(subgrupo_id=sub.id)
              .select_related("estado", "actividad_plan"))
        vigencia = request.query_params.get("vigencia")
        if vigencia:
            qs = qs.filter(vigencia_id=vigencia)

        filas = [_fila(f) for f in qs]
        return Response({
            "area": {"id": sub.id, "nombre": sub.nombre},
            "formulaciones": filas,
            "resumen": _resumen(filas),
            "estados_catalogo": catalogo_estados(),
            # El permiso lo decide el servidor, no la pantalla.
            "puede_formular": puede_crear_en_area(request.user, sub.id),
        })

    def post(self, request, area):
        from django.db import IntegrityError, transaction
        from django.utils import timezone

        from apps.presupuesto.models import Formulacion
        from apps.presupuesto.models.auditoria import AuditoriaDato
        from apps.presupuesto.services.auditoria import registrar_cambio

        sub, error = _area_y_gates(request, area)
        if error:
            return error

        d = request.data or {}
        try:
            actividad_id = int(d.get("actividad_plan_id"))
            vigencia = int(d.get("vigencia"))
        except (TypeError, ValueError):
            return Response(
                {"detail": "Hacen falta la actividad del plan y la vigencia."},
                status=status.HTTP_400_BAD_REQUEST)

        # ── gate 3: la actividad tiene que ser del área ──
        if actividad_id not in _actividades_del_area(sub.id):
            # 403 y no 404: existe, pero es de otra área. El mensaje no dice de
            # quién — sería filtrar información ajena.
            return Response({"detail": "Esa actividad no pertenece a esta área."},
                            status=status.HTTP_403_FORBIDDEN)

        objeto = (d.get("objeto") or "").strip()
        if not objeto:
            return Response({"detail": "El objeto es obligatorio: es lo que se "
                                       "va a contratar."},
                            status=status.HTTP_400_BAD_REQUEST)

        ahora = timezone.now()
        try:
            with transaction.atomic():
                f = Formulacion.objects.create(
                    actividad_plan_id=actividad_id, vigencia_id=vigencia,
                    subgrupo_id=sub.id, objeto=objeto,
                    descripcion=d.get("descripcion") or None,
                    valor_estimado=d.get("valor_estimado") or None,
                    responsable_funcionario_id=d.get("responsable_funcionario_id") or None,
                    estado_id=1, estado_fecha=ahora,
                    estado_usuario_id=request.user.id,
                    creado_en=ahora, creado_usuario_id=request.user.id)
                registrar_cambio(
                    usuario=request.user, entidad="formulacion", entidad_id=f.id,
                    campo="creacion", valor_anterior=None,
                    valor_nuevo=f"{objeto[:60]} · vigencia {vigencia}",
                    subgrupo_id=sub.id, fuente=AuditoriaDato.MANUAL,
                    observacion=d.get("observacion") or None)
        except IntegrityError:
            # El UNIQUE (actividad, vigencia). Se traduce en vez de dejar salir
            # el error de Postgres, que nombra la restricción y no ayuda.
            return Response(
                {"detail": "Esa actividad ya tiene una formulación en esa "
                           "vigencia. Abrila en vez de crear otra."},
                status=status.HTTP_409_CONFLICT)

        return Response(_fila(f, con_detalle=True), status=status.HTTP_201_CREATED)


def _resumen(filas):
    """Los contadores del §16: formulado, contratado y lo que falta convertir."""
    return {
        "n": len(filas),
        "listas": sum(1 for f in filas if not f["estado"]["bloquea_contratacion"]),
        "bloqueadas": sum(1 for f in filas if f["bloqueada"]),
        "canceladas": sum(1 for f in filas if f["cancelada"]),
        "valor_formulado": sum(f["valor_estimado"] or 0 for f in filas
                               if not f["cancelada"]),
    }


class FormulacionDetalleView(APIView):
    """`GET /presupuesto/api/formulaciones/<id>/`"""
    permission_classes = [IsAuthenticated]

    def get(self, request, formulacion_id):
        from apps.login.services.permisos import puede_crear_en_area
        from apps.login.services.scope import subgrupos_visibles
        from apps.presupuesto.models import Formulacion

        f = (Formulacion.objects.select_related("estado", "actividad_plan")
             .filter(id=formulacion_id).first())
        if f is None:
            return Response({"detail": "Esa formulación no existe."},
                            status=status.HTTP_404_NOT_FOUND)
        subs = subgrupos_visibles(request.user)
        if subs is not None and f.subgrupo_id not in subs:
            return Response({"detail": "Esa formulación es de otra área."},
                            status=status.HTTP_403_FORBIDDEN)

        datos = _fila(f, con_detalle=True)
        datos["puede_formular"] = puede_crear_en_area(request.user, f.subgrupo_id)
        return Response(datos)


class FormulacionEstadoView(APIView):
    """`PATCH /presupuesto/api/formulaciones/<id>/estado/`"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, formulacion_id):
        from apps.login.services.permisos import puede_crear_en_area
        from apps.presupuesto.models import Formulacion
        from apps.presupuesto.services.formulacion import (
            TransicionInvalida, cambiar_estado,
        )

        f = (Formulacion.objects.select_related("estado", "actividad_plan")
             .filter(id=formulacion_id).first())
        if f is None:
            return Response({"detail": "Esa formulación no existe."},
                            status=status.HTTP_404_NOT_FOUND)
        if not puede_crear_en_area(request.user, f.subgrupo_id):
            return Response(
                {"detail": "Para mover una formulación hace falta el rol de "
                           "Coordinador de esta área."},
                status=status.HTTP_403_FORBIDDEN)
        if "estado_codigo" not in request.data:
            return Response({"detail": "Falta `estado_codigo`."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            salida = cambiar_estado(f, request.data["estado_codigo"], request.user,
                                    observacion=request.data.get("observacion"))
        except TransicionInvalida as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        f.refresh_from_db()
        return Response({**salida, "formulacion": _fila(f, con_detalle=True)})


class FormulacionRequisitoView(APIView):
    """`POST /presupuesto/api/formulaciones/<id>/requisitos/<codigo>/`"""
    permission_classes = [IsAuthenticated]

    ESTADOS = {"ok", "pendiente", "sin_dato", "no_aplica"}

    def post(self, request, formulacion_id, codigo):
        from django.utils import timezone

        from apps.login.services.permisos import puede_crear_en_area
        from apps.presupuesto.models import (
            Formulacion, RequisitoCumplido, RequisitoFormulacion,
        )
        from apps.presupuesto.models.auditoria import AuditoriaDato
        from apps.presupuesto.services.auditoria import registrar_cambio
        from apps.presupuesto.services.formulacion import completitud, semaforo

        f = (Formulacion.objects.select_related("estado", "actividad_plan")
             .filter(id=formulacion_id).first())
        if f is None:
            return Response({"detail": "Esa formulación no existe."},
                            status=status.HTTP_404_NOT_FOUND)
        if not puede_crear_en_area(request.user, f.subgrupo_id):
            return Response({"detail": "Para diligenciar hace falta el rol de "
                                       "Coordinador de esta área."},
                            status=status.HTTP_403_FORBIDDEN)

        req = RequisitoFormulacion.objects.filter(codigo=codigo, activo=True).first()
        if req is None:
            return Response({"detail": "Ese requisito no está en el catálogo."},
                            status=status.HTTP_404_NOT_FOUND)
        estado = (request.data or {}).get("estado")
        if estado not in self.ESTADOS:
            return Response(
                {"detail": f"Estado no válido. Sólo: {', '.join(sorted(self.ESTADOS))}."},
                status=status.HTTP_400_BAD_REQUEST)

        anterior = RequisitoCumplido.objects.filter(formulacion=f, requisito=req).first()
        RequisitoCumplido.objects.update_or_create(
            formulacion=f, requisito=req,
            defaults={"estado": estado, "fecha": timezone.now(),
                      "usuario_id": request.user.id,
                      "observacion": (request.data.get("observacion") or None)})
        registrar_cambio(
            usuario=request.user, entidad="formulacion_requisito",
            entidad_id=f.id, campo=req.codigo,
            valor_anterior=anterior.estado if anterior else None,
            valor_nuevo=estado, subgrupo_id=f.subgrupo_id,
            fuente=AuditoriaDato.MANUAL,
            observacion=request.data.get("observacion") or None)

        c = completitud(f)
        return Response({"ok": True, "requisito": req.codigo, "estado": estado,
                         "completitud": c["pct"], "bloqueada": c["bloqueada"],
                         "faltan_criticos": c["faltan_criticos"],
                         "semaforo": semaforo(f, c)})
