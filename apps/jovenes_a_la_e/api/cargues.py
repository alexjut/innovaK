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

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.jovenes_a_la_e.services import cargue_excel
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
        return Response({
            "resumen": resumen,
            # Las filas van completas: el usuario tiene que poder ver CUÁL
            # fila está mal, no cuántas. Con el tope de 2.000 del lector, el
            # peor caso son unos pocos MB de JSON.
            "filas": [f.como_dict() for f in lectura.filas],
            "puede_procesar": lectura.con_error == 0,
            "siguiente_paso": (
                "El cargue definitivo todavía no está habilitado: falta aplicar el "
                "DDL 004. Por ahora esta pantalla valida el archivo y muestra qué "
                "trae."
            ),
        })
