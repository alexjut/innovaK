"""Cargue masivo de beneficiarios — endpoints DRF.

**Solo la prevalidación por ahora.** Es deliberado: prevalidar no escribe nada,
así que funciona sin el DDL 004 aplicado y sirve desde ya para lo que el área
necesita hoy — poder ver qué trae su archivo antes de que exista nada más.

El flujo completo será de tres tiempos, con la compuerta humana en el medio:

    1. prevalidar   → no persiste. Devuelve el reporte fila a fila.   ← ESTE
    2. crear lote   → guarda archivo + hash y deja el lote 'validado'
    3. procesar     → escribe personas, beneficiarios y entregas

Los pasos 2 y 3 necesitan la tabla `cargue_beneficiarios`, que crea el DDL 004.

## Habeas data

El reporte devuelve documentos y nombres: son las 174 personas del archivo. El
endpoint está gateado por el módulo `jovenes_a_la_e`, y cuando exista el módulo
transversal `datos_personales` este es uno de los sitios que hay que apretar —
`Visor` y `Lider_contrato` deberían ver el resumen y el desglose, no la lista
con cédulas. Queda dicho acá para que no se pase por alto al implementarlo.
"""
from __future__ import annotations

import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.jovenes_a_la_e.models import CargueBeneficiarios
from apps.jovenes_a_la_e.services import cargue_excel
from apps.jovenes_a_la_e.services import cargue_beneficiarios as servicio
from apps.login.api.permissions import ModuloRequiredPermission

logger = logging.getLogger(__name__)

_PERMS = [ModuloRequiredPermission("jovenes_a_la_e")]

#: Tope de bytes del archivo. 175 filas pesan ~30 KB; 10 MB es holgura de
#: sobra y evita que una subida equivocada (un PDF escaneado, un ZIP) se lea
#: entera en memoria antes de fallar.
MAX_BYTES = 10 * 1024 * 1024


class CarguePrevalidarView(APIView):
    """POST — lee el Excel y devuelve el reporte. **No persiste nada.**

    multipart/form-data:
        archivo   (obligatorio) el .xlsx del área
        vigencia  (opcional)    año del beneficio; si no viene, no se juzga

    La vigencia se pide acá y no por fila a propósito: es del LOTE. El archivo
    de 2025 y el de 2026 son dos archivos distintos, y mezclarlos en el mismo
    conteo es el error que la columna evita.
    """
    permission_classes = _PERMS

    def post(self, request):
        archivo = request.FILES.get("archivo")
        if archivo is None:
            return Response(
                {"detail": "Falta el archivo. Envíelo como 'archivo' en multipart/form-data."},
                status=status.HTTP_400_BAD_REQUEST)

        if archivo.size > MAX_BYTES:
            return Response(
                {"detail": f"El archivo pesa {archivo.size // 1024} KB y el tope es "
                           f"{MAX_BYTES // 1024 // 1024} MB."},
                status=status.HTTP_400_BAD_REQUEST)

        vigencia = (request.data.get("vigencia") or "").strip()
        if vigencia and not (vigencia.isdigit() and int(vigencia) >= 2024):
            return Response({"detail": "La vigencia debe ser un año igual o posterior a 2024."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            lectura = cargue_excel.leer(archivo)
        except cargue_excel.ArchivoInvalido as exc:
            # El archivo no se puede leer como planilla: no es error del
            # servidor ni hay reporte que dar, así que va como 400 con el
            # motivo tal cual, que ya está redactado para un humano.
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:  # noqa: BLE001
            logger.exception("Fallo leyendo el Excel de beneficiarios")
            return Response({"detail": "No se pudo leer el archivo."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        resumen = lectura.resumen()
        resumen["archivo"] = archivo.name
        resumen["vigencia"] = int(vigencia) if vigencia else None
        filas = [f.como_dict() for f in lectura.filas]

        # Los documentos repetidos se devuelven aparte, agrupados, porque son
        # los que EXIGEN una decisión antes de procesar: una persona entra una
        # sola vez y cuál de sus matrículas lo elige quien carga.
        repetidos = [
            {
                "documento": doc,
                "nombre": _nombre(grupo[0]),
                "opciones": [
                    {"fila": f["fila"],
                     "programa": f["datos"].get("programa"),
                     "snies_programa": f["datos"].get("snies_programa"),
                     "institucion": f["datos"].get("ies_nombre"),
                     "snies_ies": f["datos"].get("snies_ies"),
                     "nivel": f["datos"].get("nivel_formacion")}
                    for f in grupo
                ],
            }
            for doc, grupo in sorted(servicio.documentos_repetidos(filas).items())
        ]

        return Response({
            "resumen": resumen,
            # Las filas van completas: el usuario tiene que poder ver CUÁL
            # fila está mal, no cuántas. Con el tope de 2.000 del lector, el
            # peor caso son unos pocos MB de JSON.
            "filas": filas,
            "repetidos": repetidos,
            "puede_procesar": lectura.con_error == 0,
            "siguiente_paso": (
                "Elija una matrícula por cada documento repetido y procese el cargue."
                if repetidos else
                ("Todo listo para cargar." if lectura.con_error == 0
                 else "Corrija las filas con error antes de cargar.")
            ),
        })


def _nombre(fila: dict) -> str:
    d = fila.get("datos") or {}
    return " ".join(filter(None, [d.get("nombre1"), d.get("nombre2"),
                                  d.get("apellido1"), d.get("apellido2")]))


class CargueEventosView(APIView):
    """GET — eventos de captura de becas a los que se puede cargar.

    Solo los de tipo `JOVENES_BECA`. Se marca cuáles NO tienen actividad del
    plan: se pueden ver, pero no se les puede cargar, y la UI lo explica en vez
    de dejar al usuario adivinando por qué falla.
    """
    permission_classes = _PERMS

    def get(self, request):
        from apps.login.models import Evento

        eventos = (Evento.objects
                   .filter(tipo_evento_codigo="JOVENES_BECA")
                   .order_by("-fecha_inicio", "-id"))
        return Response({"eventos": [
            {"id": e.id, "nombre": e.nombre,
             "fecha_inicio": e.fecha_inicio.isoformat() if e.fecha_inicio else None,
             "actividad_plan_id": e.actividad_plan_id,
             "cargable": bool(e.actividad_plan_id)}
            for e in eventos
        ]})


class CargueListCreateView(APIView):
    """GET lista los lotes · POST crea uno (lee, valida y guarda; NO escribe entregas)."""
    permission_classes = _PERMS

    def get(self, request):
        lotes = CargueBeneficiarios.objects.select_related("evento")[:50]
        return Response({"lotes": [_lote_json(l) for l in lotes]})

    def post(self, request):
        from apps.login.models import Evento

        archivo = request.FILES.get("archivo")
        if archivo is None:
            return Response({"detail": "Falta el archivo."},
                            status=status.HTTP_400_BAD_REQUEST)
        if archivo.size > MAX_BYTES:
            return Response({"detail": f"El archivo supera los {MAX_BYTES // 1024 // 1024} MB."},
                            status=status.HTTP_400_BAD_REQUEST)

        evento = Evento.objects.filter(id=request.data.get("evento_id") or 0).first()
        if evento is None:
            return Response({"detail": "Elija el evento de captura al que pertenece el cargue."},
                            status=status.HTTP_400_BAD_REQUEST)

        vigencia = (request.data.get("vigencia") or "").strip()
        if not vigencia.isdigit():
            return Response({"detail": "La vigencia es obligatoria (año del beneficio)."},
                            status=status.HTTP_400_BAD_REQUEST)

        elecciones = request.data.get("elecciones")
        if isinstance(elecciones, str):
            import json
            try:
                elecciones = json.loads(elecciones or "{}")
            except ValueError:
                return Response({"detail": "El campo 'elecciones' no es JSON válido."},
                                status=status.HTTP_400_BAD_REQUEST)

        try:
            lote = servicio.crear_lote(
                archivo=archivo, evento=evento, vigencia=int(vigencia),
                usuario=request.user, elecciones=elecciones or {},
            )
        except (servicio.CargueInvalido, cargue_excel.ArchivoInvalido) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(_lote_json(lote, detalle=True), status=status.HTTP_201_CREATED)


class CargueDetailView(APIView):
    """GET — el lote con su reporte completo."""
    permission_classes = _PERMS

    def get(self, request, pk):
        lote = get_object_or_404(CargueBeneficiarios.objects.select_related("evento"), pk=pk)
        return Response(_lote_json(lote, detalle=True))


class CargueProcesarView(APIView):
    """POST — escribe las entregas del lote. Es el paso que sí persiste."""
    permission_classes = _PERMS

    def post(self, request, pk):
        lote = get_object_or_404(CargueBeneficiarios, pk=pk)
        try:
            resultado = servicio.procesar(lote, usuario=request.user)
        except servicio.CargueInvalido as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:  # noqa: BLE001
            logger.exception("Fallo procesando el cargue %s", pk)
            return Response({"detail": "No se pudo procesar el cargue. No se guardó nada."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        lote.refresh_from_db()
        return Response({**resultado, "lote": _lote_json(lote)})


class CargueAnularView(APIView):
    """POST — deshace el lote y libera su archivo para volver a cargarlo."""
    permission_classes = _PERMS

    def post(self, request, pk):
        lote = get_object_or_404(CargueBeneficiarios, pk=pk)
        try:
            resultado = servicio.anular(lote)
        except servicio.CargueInvalido as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        lote.refresh_from_db()
        return Response({**resultado, "lote": _lote_json(lote)})


def _lote_json(lote, detalle: bool = False) -> dict:
    data = {
        "id": lote.id,
        "evento_id": lote.evento_id,
        "evento_nombre": lote.evento.nombre if lote.evento_id else None,
        "vigencia": lote.vigencia,
        "archivo_nombre": lote.archivo_nombre,
        "archivo_sha256": lote.archivo_sha256,
        "estado": lote.estado,
        "filas_total": lote.filas_total,
        "filas_ok": lote.filas_ok,
        "filas_error": lote.filas_error,
        "created_at": lote.created_at.isoformat() if lote.created_at else None,
    }
    if detalle:
        data["resumen"] = lote.resumen
        data["filas"] = lote.filas_reporte
    return data
