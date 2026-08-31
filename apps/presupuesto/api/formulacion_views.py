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


def _fila(f, con_detalle=False, n_contratos=None):
    """`n_contratos` llega de afuera a propósito: la lista lo resuelve en una
    sola consulta para las N filas. Si llega `None` se consulta acá — cómodo
    para el detalle, inaceptable dentro de un bucle."""
    from apps.presupuesto.services.formulacion import (
        coherencia, completitud, destinos_validos, semaforo)
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
    if n_contratos is None:
        from apps.presupuesto.models import FormulacionContrato
        n_contratos = FormulacionContrato.objects.filter(formulacion=f).count()
    fila["contratos_n"] = n_contratos
    # `null` cuando la traza cuadra: el silencio acá es una respuesta.
    fila["coherencia"] = coherencia(f, n_contratos)
    fila["responsable"] = _responsable(f)
    if con_detalle:
        fila["requisitos"] = c["requisitos"]
        fila["destinos"] = destinos_validos(f.estado_id)
    return fila


def _responsable(f) -> dict:
    """Quién responde por la formulación.

    `null` con su motivo, nunca un nombre vacío: «sin encargado» es una tarea
    pendiente con dueño —el área— y tiene que verse como tal para que se llene.
    """
    if not f.responsable_funcionario_id:
        return {"id": None, "nombre": None,
                "motivo": "Sin encargado asignado todavía."}
    try:
        nombre = _nombre_de(f.responsable_funcionario)
    except Exception:
        nombre = None
    return {"id": f.responsable_funcionario_id,
            "nombre": (nombre or "").strip() or f"Funcionario {f.responsable_funcionario_id}",
            "motivo": None}


def _funcionarios_de(subgrupo_id: int) -> list[dict]:
    """Los funcionarios del área, para elegir encargado.

    Si el área no tiene ninguno, la lista viene vacía Y con su motivo: un
    desplegable vacío sobre la nada culpa al usuario de algo que no es suyo.
    Es la misma lección del selector de responsables de evento.
    """
    from apps.login.models.funcionario import Funcionario
    salida = [{"id": fn.id, "nombre": _nombre_de(fn) or f"Funcionario {fn.id}"}
              for fn in (Funcionario.objects.filter(subgrupo_id=subgrupo_id)
                         .select_related("persona"))]
    return sorted(salida, key=lambda x: x["nombre"])


def _nombre_de(funcionario) -> str:
    """Nombre y apellido de un funcionario.

    Los campos de `Persona` son `nombre1/nombre2/apellido1/apellido2`, no
    `nombres/apellidos`. Se usan el primero de cada uno, que es como el resto
    del sistema nombra a la gente.
    """
    try:
        p = funcionario.persona
    except Exception:
        return ""
    partes = [getattr(p, "nombre1", None), getattr(p, "apellido1", None)]
    return " ".join(x.strip() for x in partes if x and x.strip())


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

        from apps.presupuesto.services.formulacion_contrato import (
            contratos_por_formulacion)
        formulaciones = list(qs)
        n_por_f = contratos_por_formulacion([f.id for f in formulaciones])
        filas = [_fila(f, n_contratos=n_por_f.get(f.id, 0)) for f in formulaciones]
        return Response({
            "area": {"id": sub.id, "nombre": sub.nombre},
            "formulaciones": filas,
            "resumen": _resumen(filas),
            # Por qué está vacío, cuando lo está. Un 0 anónimo acá se lee como
            # «esta área no formula nada», y medido son otras dos cosas muy
            # distintas: o sus líneas del plan ya están contratadas, o el área
            # no tiene ni una línea del plan donde colgar una formulación —le
            # pasa a Infraestructura y a Subsidio tipo C, que tienen KPI con
            # meta y cero filas en `actividad_plan`.
            "contexto": _contexto_vacio(sub.id) if not filas else None,
            "estados_catalogo": catalogo_estados(),
            # Lo que hace falta para ABRIR una formulación desde la pantalla.
            # Va en la misma respuesta y no en tres llamadas: el formulario los
            # necesita a los tres antes de poder dibujarse.
            "actividades": _actividades_para_formular(sub.id),
            "funcionarios": _funcionarios_de(sub.id),
            "funcionarios_motivo": (
                None if _funcionarios_de(sub.id) else
                "Esta área no tiene funcionarios registrados, así que todavía no "
                "hay a quién asignar como encargado. Se crean en Organización."),
            "vigencias": _vigencias(),
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

        return Response(_fila(f, con_detalle=True, n_contratos=0),
                        status=status.HTTP_201_CREATED)


def _vigencias() -> list[int]:
    """Los años del catálogo, del más reciente al más viejo."""
    from apps.presupuesto.models.core_catalogos import Vigencia
    return sorted((v.codigo for v in Vigencia.objects.all()), reverse=True)


def _actividades_para_formular(subgrupo_id: int) -> list[dict]:
    """Las actividades del área y en qué vigencias ya están formuladas.

    Se devuelven TODAS, no sólo las libres: el formulario necesita mostrar la
    que ya tiene formulación como deshabilitada y decir por qué, en vez de
    omitirla y dejar al área buscando una actividad que no aparece.
    """
    from apps.presupuesto.models import Formulacion
    from apps.presupuesto.models.core import ActividadPlan, Proyecto

    pids = list(Proyecto.objects.filter(subgrupo_id=subgrupo_id)
                .values_list("id", flat=True))
    if not pids:
        return []
    ya = {}
    for aid, vig in Formulacion.objects.filter(subgrupo_id=subgrupo_id).values_list(
            "actividad_plan_id", "vigencia_id"):
        ya.setdefault(aid, []).append(vig)
    return [{"id": a.id, "descripcion": a.descripcion,
             "formulada_en": sorted(ya.get(a.id, []))}
            for a in ActividadPlan.objects.filter(proyecto_id__in=pids)
            .order_by("descripcion")]


def _contexto_vacio(subgrupo_id: int) -> dict:
    """Explica un «0 formulaciones». Nunca se devuelve un cero pelado."""
    from apps.presupuesto.models.core import ActividadPlan, Proyecto
    from apps.presupuesto.models.sql import ContratoActividadPlan

    pids = list(Proyecto.objects.filter(subgrupo_id=subgrupo_id)
                .values_list("id", flat=True))
    lineas = list(ActividadPlan.objects.filter(proyecto_id__in=pids)
                  .values_list("id", flat=True)) if pids else []
    con_contrato = set(ContratoActividadPlan.objects
                       .filter(actividad_plan_id__in=lineas, activo=True)
                       .values_list("actividad_plan_id", flat=True))

    if not pids:
        causa, detalle = "sin_proyectos", (
            "El área no tiene proyectos cargados, así que no hay plan del que "
            "colgar una formulación.")
    elif not lineas:
        causa, detalle = "sin_lineas_de_plan", (
            "El área tiene proyectos pero ninguna actividad del plan. Una "
            "formulación cuelga de una actividad: hasta que existan, no hay "
            "dónde formular.")
    elif len(con_contrato) == len(lineas):
        n = len(lineas)
        causa, detalle = "todo_contratado", (
            (f"La única actividad del plan de esta área ya tiene contrato."
             if n == 1 else
             f"Las {n} actividades del plan de esta área ya tienen contrato.")
            + " No es que no se formule: es que ya se contrató.")
    else:
        faltan = len(lineas) - len(con_contrato)
        causa, detalle = "sin_formular_todavia", (
            f"El área tiene {faltan} actividad{'' if faltan == 1 else 'es'} del "
            f"plan sin contrato y todavía no ha abierto su formulación.")

    return {
        "causa": causa,
        "detalle": detalle,
        "lineas_de_plan": len(lineas),
        "lineas_con_contrato": len(con_contrato),
        "proyectos": len(pids),
    }


def _resumen(filas):
    """Los contadores del §16.

    SE CUENTAN POR EL SEMÁFORO, no por una regla paralela. La primera versión
    contaba `bloqueada` por su cuenta y decía «5 bloqueadas» mientras la
    pantalla pintaba «⚪ Borrador · Sin iniciar» en las cinco: el contador y el
    icono salían de caminos distintos y se contradecían. Ahora el contador ES
    el icono, así que no pueden separarse.

    Y `valor_formulado` es `null` cuando ninguna tiene valor, NUNCA 0. Un 0 ahí
    dice «vale cero pesos»; lo que pasa es que no hay dato. Se publica al lado
    cuántas de cuántas lo tienen, para que el vacío se pueda juzgar.
    """
    from apps.presupuesto.services.formulacion_contrato import resumen_contratado

    vivas = [f for f in filas if not f["cancelada"]]
    con_valor = [f for f in vivas if f["valor_estimado"] is not None]
    por_semaforo = {}
    for f in filas:
        clave = f["semaforo"]["clave"]
        por_semaforo[clave] = por_semaforo.get(clave, 0) + 1
    return {
        "n": len(filas),
        "listas": por_semaforo.get("lista", 0),
        "bloqueadas": por_semaforo.get("bloqueada", 0),
        "en_proceso": por_semaforo.get("en_proceso", 0),
        "observadas": por_semaforo.get("observada", 0),
        "sin_iniciar": por_semaforo.get("sin_iniciar", 0),
        "canceladas": sum(1 for f in filas if f["cancelada"]),
        "valor_formulado": (sum(f["valor_estimado"] for f in con_valor)
                            if con_valor else None),
        "valor_cobertura": {"con": len(con_valor), "de": len(vivas)},
        "valor_motivo": (None if con_valor else
                         "Ninguna formulación tiene valor estimado todavía. "
                         "Lo registra el área."),
        # La otra mitad del par: de lo que se está formulando, cuánto YA es
        # contrato. Se calcula sobre las vivas — una formulación cancelada que
        # alcanzó a tener contrato no cuenta como avance de lo que sigue en pie.
        "contratado": resumen_contratado([f["id"] for f in vivas]),
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


class FormulacionContratosView(APIView):
    """`GET|POST /presupuesto/api/formulaciones/<id>/contratos/`

    El salto de formulación a contrato, que es donde no se puede perder la
    traza. El GET devuelve en qué contratos terminó y, si se pasa `q`, busca en
    el espejo de SECOP por número. El POST enlaza.
    """
    permission_classes = [IsAuthenticated]

    def _formulacion(self, request, formulacion_id, exigir_rol):
        from apps.login.services.permisos import puede_crear_en_area
        from apps.login.services.scope import subgrupos_visibles
        from apps.presupuesto.models import Formulacion

        f = (Formulacion.objects.select_related("estado", "actividad_plan")
             .filter(id=formulacion_id).first())
        if f is None:
            return None, Response({"detail": "Esa formulación no existe."},
                                  status=status.HTTP_404_NOT_FOUND)
        subs = subgrupos_visibles(request.user)
        if subs is not None and f.subgrupo_id not in subs:
            return None, Response({"detail": "Esa formulación es de otra área."},
                                  status=status.HTTP_403_FORBIDDEN)
        if exigir_rol and not puede_crear_en_area(request.user, f.subgrupo_id):
            return None, Response(
                {"detail": "Para enlazar un contrato hace falta el rol de "
                           "Coordinador de esta área."},
                status=status.HTTP_403_FORBIDDEN)
        return f, None

    def get(self, request, formulacion_id):
        from apps.presupuesto.services.formulacion_contrato import (
            buscar_en_secop, contratos_de,
        )
        f, error = self._formulacion(request, formulacion_id, exigir_rol=False)
        if error:
            return error

        salida = {"formulacion_id": f.id, "contratos": contratos_de(f)}
        q = (request.query_params.get("q") or "").strip()
        if q:
            vig = request.query_params.get("vigencia")
            salida["busqueda"] = buscar_en_secop(
                q, vigencia=int(vig) if vig and vig.isdigit() else None)
        return Response(salida)

    def post(self, request, formulacion_id):
        from apps.presupuesto.services.formulacion_contrato import (
            EnlaceInvalido, contratos_de, enlazar_desde_secop,
        )
        f, error = self._formulacion(request, formulacion_id, exigir_rol=True)
        if error:
            return error

        id_secop = (request.data or {}).get("id_contrato_secop")
        if not id_secop:
            return Response(
                {"detail": "Falta `id_contrato_secop`: el identificador de la "
                           "fila de SECOP que se va a enlazar."},
                status=status.HTTP_400_BAD_REQUEST)
        try:
            salida = enlazar_desde_secop(f, id_secop, request.user)
        except EnlaceInvalido as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({**salida, "contratos": contratos_de(f)},
                        status=status.HTTP_201_CREATED)

    def delete(self, request, formulacion_id):
        from apps.presupuesto.services.formulacion_contrato import (
            EnlaceInvalido, contratos_de, desenlazar,
        )
        f, error = self._formulacion(request, formulacion_id, exigir_rol=True)
        if error:
            return error
        contrato_id = (request.data or {}).get("contrato_id")
        if not contrato_id:
            return Response({"detail": "Falta `contrato_id`."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            salida = desenlazar(f, int(contrato_id), request.user,
                                motivo=(request.data or {}).get("motivo"))
        except EnlaceInvalido as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({**salida, "contratos": contratos_de(f)})


class ContratoFormulacionesView(APIView):
    """`GET /presupuesto/api/contratos/<id>/formulaciones/`

    La otra mitad de la traza: desde un contrato, de qué formulación nació.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, contrato_id):
        from apps.presupuesto.services.formulacion_contrato import formulaciones_de
        return Response({"contrato_id": contrato_id,
                         "formulaciones": formulaciones_de(contrato_id)})


class FormulacionResponsableView(APIView):
    """`PATCH /presupuesto/api/formulaciones/<id>/responsable/`

    Asigna o quita el encargado. Es DATO, no permiso: quién puede tocar la
    formulación lo siguen decidiendo el scope y el rol. Esto dice quién
    RESPONDE por ella, que es otra pregunta — y la que hace falta para poder
    reclamarle a alguien.

    Se empieza con todas en «sin encargado» a propósito: es un pendiente con
    dueño visible, que se llena con el tiempo. Esconderlo detrás de un valor
    por defecto haría que nunca se llenara.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, formulacion_id):
        from apps.login.models.funcionario import Funcionario
        from apps.login.services.permisos import puede_crear_en_area
        from apps.presupuesto.models import Formulacion
        from apps.presupuesto.models.auditoria import AuditoriaDato
        from apps.presupuesto.services.auditoria import registrar_cambio

        f = (Formulacion.objects.select_related("estado", "actividad_plan")
             .filter(id=formulacion_id).first())
        if f is None:
            return Response({"detail": "Esa formulación no existe."},
                            status=status.HTTP_404_NOT_FOUND)
        if not puede_crear_en_area(request.user, f.subgrupo_id):
            return Response(
                {"detail": "Para asignar el encargado hace falta el rol de "
                           "Coordinador de esta área."},
                status=status.HTTP_403_FORBIDDEN)

        if "funcionario_id" not in request.data:
            return Response({"detail": "Falta `funcionario_id`. Envía null para "
                                       "dejarla sin encargado."},
                            status=status.HTTP_400_BAD_REQUEST)

        antes = _responsable(f)["nombre"]
        fid = request.data["funcionario_id"]
        if fid in (None, "", 0):
            f.responsable_funcionario_id = None
        else:
            fn = Funcionario.objects.filter(id=fid).first()
            if fn is None:
                return Response({"detail": "Ese funcionario no existe."},
                                status=status.HTTP_404_NOT_FOUND)
            # El encargado tiene que ser del área. Sin esto, cambiar un número
            # en la petición le asigna una formulación a alguien de otra.
            if fn.subgrupo_id != f.subgrupo_id:
                return Response(
                    {"detail": "Ese funcionario no pertenece a esta área."},
                    status=status.HTTP_403_FORBIDDEN)
            f.responsable_funcionario_id = fn.id

        from django.utils import timezone
        f.actualizado_en = timezone.now()
        f.save(update_fields=["responsable_funcionario", "actualizado_en"])
        registrar_cambio(
            usuario=request.user, entidad="formulacion", entidad_id=f.id,
            campo="responsable", valor_anterior=antes,
            valor_nuevo=_responsable(f)["nombre"],
            proyecto_id=f.actividad_plan.proyecto_id, subgrupo_id=f.subgrupo_id,
            fuente=AuditoriaDato.MANUAL,
            observacion=(request.data.get("observacion") or None))
        return Response({"ok": True, "responsable": _responsable(f)})


#: Tope de subida. No es un número redondo por gusto: los estudios previos y
#: los análisis del sector llegan escaneados y pesan, pero 25 MB por archivo es
#: suficiente para un PDF de 300 páginas y evita que un vídeo pegado por error
#: llene la base. Si un soporte no cabe, es mejor que lo diga acá que descubrir
#: a los seis meses que Mongo se llenó.
MAX_BYTES = 25 * 1024 * 1024

#: Lo que un expediente de formulación puede contener de verdad. Se valida el
#: tipo declarado Y la extensión: el navegador miente sobre el `content_type`
#: con facilidad, y una lista blanca es lo único que impide que entre un .exe.
MIMES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg", "image/png": ".png",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}


class FormulacionDocumentosView(APIView):
    """`GET|POST /presupuesto/api/formulaciones/<id>/documentos/`

    Los soportes del expediente. El archivo va a **Mongo cifrado**, que ya está
    activo; en Postgres queda sólo el puntero. OneDrive está cableado en
    `apps/documentos` pero apagado por credenciales: cuando lleguen, el espejo
    se enciende sin tocar esto.

    ORDEN DE ESCRITURA, y no es indiferente: primero Mongo, después Postgres, y
    si Postgres falla se borra el blob. Al revés dejaría filas apuntando a un
    documento que no existe — que es peor que no tener el documento, porque la
    pantalla diría que sí está.

    Si el soporte se sube contra un requisito, además lo marca como cumplido y
    lo enlaza: `exige_evidencia` está en 8 de los 16, así que sin esto esa marca
    no se podía cumplir.
    """
    permission_classes = [IsAuthenticated]

    def _formulacion(self, request, formulacion_id, exigir_rol):
        from apps.login.services.permisos import puede_crear_en_area
        from apps.login.services.scope import subgrupos_visibles
        from apps.presupuesto.models import Formulacion

        f = (Formulacion.objects.select_related("actividad_plan")
             .filter(id=formulacion_id).first())
        if f is None:
            return None, Response({"detail": "Esa formulación no existe."},
                                  status=status.HTTP_404_NOT_FOUND)
        subs = subgrupos_visibles(request.user)
        if subs is not None and f.subgrupo_id not in subs:
            return None, Response({"detail": "Esa formulación es de otra área."},
                                  status=status.HTTP_403_FORBIDDEN)
        if exigir_rol and not puede_crear_en_area(request.user, f.subgrupo_id):
            return None, Response(
                {"detail": "Para cargar soportes hace falta el rol de "
                           "Coordinador de esta área."},
                status=status.HTTP_403_FORBIDDEN)
        return f, None

    def get(self, request, formulacion_id):
        f, error = self._formulacion(request, formulacion_id, exigir_rol=False)
        if error:
            return error
        return Response({"formulacion_id": f.id, "documentos": _documentos_de(f)})

    def post(self, request, formulacion_id):
        import os

        from django.db import transaction
        from django.utils import timezone

        from apps.documentos.services import mongo_storage
        from apps.presupuesto.models import (
            DocumentoFormulacion, RequisitoCumplido, RequisitoFormulacion,
        )
        from apps.presupuesto.models.auditoria import AuditoriaDato
        from apps.presupuesto.services.auditoria import registrar_cambio

        f, error = self._formulacion(request, formulacion_id, exigir_rol=True)
        if error:
            return error

        archivo = request.FILES.get("archivo")
        if archivo is None:
            return Response({"detail": "Falta el archivo (campo `archivo`)."},
                            status=status.HTTP_400_BAD_REQUEST)
        if archivo.size > MAX_BYTES:
            return Response(
                {"detail": f"El archivo pesa {archivo.size // (1024*1024)} MB y el "
                           f"tope es {MAX_BYTES // (1024*1024)} MB."},
                status=status.HTTP_400_BAD_REQUEST)
        if archivo.size == 0:
            return Response({"detail": "El archivo está vacío."},
                            status=status.HTTP_400_BAD_REQUEST)

        mime = (archivo.content_type or "").split(";")[0].strip().lower()
        extension = os.path.splitext(archivo.name or "")[1].lower()
        if mime not in MIMES or extension != MIMES[mime]:
            return Response(
                {"detail": "Sólo se aceptan PDF, imágenes (JPG/PNG) y documentos "
                           "de Office, y la extensión tiene que corresponder al "
                           "tipo del archivo."},
                status=status.HTTP_400_BAD_REQUEST)

        codigo = (request.data.get("requisito_codigo") or "").strip() or None
        requisito = None
        if codigo:
            requisito = RequisitoFormulacion.objects.filter(
                codigo=codigo, activo=True).first()
            if requisito is None:
                return Response({"detail": "Ese requisito no está en el catálogo."},
                                status=status.HTTP_404_NOT_FOUND)

        contenido = archivo.read()
        try:
            mongo_id = mongo_storage.guardar(
                contenido, mime,
                {"tipo": "formulacion", "id": f.id, "campo": codigo or "soporte"})
        except Exception as exc:                      # noqa: BLE001
            # Se dice que el problema es del almacenamiento y no del archivo:
            # «no se pudo guardar» a secas manda a la gente a reintentar en vano.
            return Response(
                {"detail": f"No se pudo guardar el archivo en el almacenamiento "
                           f"cifrado: {exc}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE)

        try:
            with transaction.atomic():
                doc = DocumentoFormulacion.objects.create(
                    formulacion=f, tipo=codigo, mongo_id=mongo_id,
                    nombre_archivo=(archivo.name or "soporte")[:255],
                    mime=mime, tamano_bytes=archivo.size,
                    subido_por_id=request.user.id, created_at=timezone.now())
                if requisito is not None:
                    # El soporte ES la evidencia: se marca cumplido y se enlaza.
                    RequisitoCumplido.objects.update_or_create(
                        formulacion=f, requisito=requisito,
                        defaults={"estado": "ok", "documento": doc,
                                  "fecha": timezone.now(),
                                  "usuario_id": request.user.id})
        except Exception:
            # El blob quedaría huérfano en Mongo: se borra. Una fila de Postgres
            # apuntando a nada es peor que no tener el documento.
            mongo_storage.borrar(mongo_id)
            raise

        registrar_cambio(
            usuario=request.user, entidad="formulacion", entidad_id=f.id,
            campo=f"documento:{codigo or 'soporte'}", valor_anterior=None,
            valor_nuevo=(archivo.name or "soporte")[:120],
            proyecto_id=f.actividad_plan.proyecto_id, subgrupo_id=f.subgrupo_id,
            fuente=AuditoriaDato.MANUAL)

        from apps.presupuesto.services.formulacion import completitud
        c = completitud(f)
        return Response({"documento": _fila_documento(doc),
                         "documentos": _documentos_de(f),
                         "completitud": c["pct"], "bloqueada": c["bloqueada"]},
                        status=status.HTTP_201_CREATED)


def _fila_documento(d) -> dict:
    return {
        "id": d.id,
        "nombre": d.nombre_archivo,
        "tipo": d.tipo,
        "mime": d.mime,
        "tamano_bytes": d.tamano_bytes,
        "subido_en": d.created_at.isoformat() if d.created_at else None,
        # `onedrive_item_id` viaja aunque hoy sea siempre null: la pantalla
        # puede decir «espejo pendiente» sin que haya que cambiarla el día que
        # lleguen las credenciales.
        "en_onedrive": bool(d.onedrive_item_id),
    }


def _documentos_de(f) -> list[dict]:
    from apps.presupuesto.models import DocumentoFormulacion
    return [_fila_documento(d) for d in
            DocumentoFormulacion.objects.filter(formulacion=f)]


class FormulacionDocumentoDetalleView(APIView):
    """`GET|DELETE /presupuesto/api/formulaciones/<id>/documentos/<doc_id>/`

    El GET descarga el archivo descifrado. El DELETE lo borra de Mongo y de
    Postgres, y si era la evidencia de un requisito lo devuelve a «pendiente»:
    dejar el requisito en «cumplido» sin soporte sería afirmar algo que ya no
    se puede probar.
    """
    permission_classes = [IsAuthenticated]

    def _doc(self, request, formulacion_id, doc_id, exigir_rol):
        from apps.login.services.permisos import puede_crear_en_area
        from apps.login.services.scope import subgrupos_visibles
        from apps.presupuesto.models import DocumentoFormulacion

        d = (DocumentoFormulacion.objects.select_related("formulacion")
             .filter(id=doc_id, formulacion_id=formulacion_id).first())
        if d is None:
            return None, Response({"detail": "Ese soporte no existe."},
                                  status=status.HTTP_404_NOT_FOUND)
        subs = subgrupos_visibles(request.user)
        if subs is not None and d.formulacion.subgrupo_id not in subs:
            return None, Response({"detail": "Ese soporte es de otra área."},
                                  status=status.HTTP_403_FORBIDDEN)
        if exigir_rol and not puede_crear_en_area(request.user, d.formulacion.subgrupo_id):
            return None, Response(
                {"detail": "Para borrar un soporte hace falta el rol de "
                           "Coordinador de esta área."},
                status=status.HTTP_403_FORBIDDEN)
        return d, None

    def get(self, request, formulacion_id, doc_id):
        from django.http import HttpResponse

        from apps.documentos.services import mongo_storage

        d, error = self._doc(request, formulacion_id, doc_id, exigir_rol=False)
        if error:
            return error
        try:
            contenido, mime = mongo_storage.leer(d.mongo_id)
        except Exception as exc:                      # noqa: BLE001
            return Response({"detail": f"No se pudo leer el archivo: {exc}"},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        resp = HttpResponse(contenido, content_type=mime or "application/octet-stream")
        resp["Content-Disposition"] = f'attachment; filename="{d.nombre_archivo}"'
        return resp

    def delete(self, request, formulacion_id, doc_id):
        from django.db import transaction
        from django.utils import timezone

        from apps.documentos.services import mongo_storage
        from apps.presupuesto.models import RequisitoCumplido
        from apps.presupuesto.models.auditoria import AuditoriaDato
        from apps.presupuesto.services.auditoria import registrar_cambio

        d, error = self._doc(request, formulacion_id, doc_id, exigir_rol=True)
        if error:
            return error

        f = d.formulacion
        nombre, mongo_id = d.nombre_archivo, d.mongo_id
        with transaction.atomic():
            # El requisito que se apoyaba en este soporte vuelve a «pendiente».
            RequisitoCumplido.objects.filter(documento=d).update(
                estado="pendiente", documento=None, fecha=timezone.now(),
                usuario_id=request.user.id)
            d.delete()
        mongo_storage.borrar(mongo_id)

        registrar_cambio(
            usuario=request.user, entidad="formulacion", entidad_id=f.id,
            campo="documento:baja", valor_anterior=nombre[:120], valor_nuevo=None,
            proyecto_id=f.actividad_plan.proyecto_id, subgrupo_id=f.subgrupo_id,
            fuente=AuditoriaDato.MANUAL,
            observacion=(request.data or {}).get("motivo") or None)

        from apps.presupuesto.services.formulacion import completitud
        c = completitud(f)
        return Response({"ok": True, "documentos": _documentos_de(f),
                         "completitud": c["pct"], "bloqueada": c["bloqueada"]})
