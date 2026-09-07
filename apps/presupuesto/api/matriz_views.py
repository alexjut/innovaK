"""La CARGA de la Matriz PDL por pantalla.

Hasta acá la matriz entraba por consola, con tres comandos distintos sobre el
mismo Excel. Funcionaba, pero dejaba la actualización del Plan dependiendo de
que alguien con acceso al contenedor los corriera en el orden correcto — y sin
registro de quién subió qué, ni forma de ver el cambio ANTES de aplicarlo.

TRES CANDADOS, NO UNO. Esto reescribe el Plan de Desarrollo entero:

1. **Módulo** `presupuesto_proyectos`, como el resto de presupuesto.
2. **Rol** — `ModuloRequiredPermission` ya rebota a los de solo lectura en
   cualquier método que no sea GET.
3. **Autor obligatorio al aplicar** — una matriz aplicada sin nombre no queda
   defendible ante un área que pregunte por qué le cambió la meta.

EL FLUJO ESTÁ PARTIDO EN DOS PASOS A PROPÓSITO: subir previsualiza y NO
escribe. Si subir aplicara, el estado `borrador` no significaría nada y nadie
podría mirar el diff antes de decidir — que es justamente lo que la pantalla
viene a resolver.
"""
import datetime as _dt
import os
import tempfile

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import ModuloRequiredPermission
from apps.presupuesto.models import MatrizPDLCarga
from apps.presupuesto.services import matriz_carga as svc

_PERMS = [ModuloRequiredPermission("presupuesto_proyectos")]

#: 20 MB. La matriz real pesa ~2 MB; el tope está para que un archivo
#: equivocado no se copie entero a disco antes de que nadie lo mire.
MAX_BYTES = 20 * 1024 * 1024


def _serializar(carga, con_diff=False):
    d = {
        "id": carga.id,
        "archivo_nombre": carga.archivo_nombre,
        "archivo_bytes": carga.archivo_bytes,
        "corte_oficial": carga.corte_oficial.isoformat() if carga.corte_oficial else None,
        "estado": carga.estado,
        "n_altas": carga.n_altas,
        "n_cambios": carga.n_cambios,
        "n_retiros": carga.n_retiros,
        "sin_cambios": carga.sin_cambios,
        "subido_at": carga.subido_at.isoformat() if carga.subido_at else None,
        "aplicado_at": carga.aplicado_at.isoformat() if carga.aplicado_at else None,
        "nota": carga.nota,
        # Si el xlsx ya no está en disco la carga no se puede aplicar, y la
        # pantalla tiene que poder decirlo ANTES de ofrecer el botón.
        "archivo_disponible": svc.ruta_de(carga) is not None,
    }
    if con_diff:
        d["diff"] = carga.diff
    return d


@extend_schema(tags=["Presupuesto"], summary="Cargas de la Matriz PDL")
class MatrizCargaListView(APIView):
    """`GET` lista las cargas · `POST` sube un Excel y lo PREVISUALIZA."""

    permission_classes = _PERMS
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        cargas = MatrizPDLCarga.objects.all()[:50]
        return Response({"items": [_serializar(c) for c in cargas]})

    def post(self, request):
        archivo = request.FILES.get("archivo")
        if archivo is None:
            return Response({"detail": "Falta el archivo de la matriz (.xlsx)."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not archivo.name.lower().endswith((".xlsx", ".xlsm")):
            return Response({"detail": "El archivo tiene que ser un Excel (.xlsx)."},
                            status=status.HTTP_400_BAD_REQUEST)
        if archivo.size > MAX_BYTES:
            return Response(
                {"detail": f"El archivo pesa {archivo.size // 1024 // 1024} MB y el "
                           f"tope son {MAX_BYTES // 1024 // 1024} MB."},
                status=status.HTTP_400_BAD_REQUEST)

        crudo = (request.data.get("corte_oficial") or "").strip()
        if not crudo:
            return Response(
                {"detail": "Falta la fecha de corte que declara la matriz. No se "
                           "deduce de la fecha de subida: dos personas pueden "
                           "subir el mismo corte en días distintos."},
                status=status.HTTP_400_BAD_REQUEST)
        try:
            corte = _dt.date.fromisoformat(crudo)
        except ValueError:
            return Response({"detail": "La fecha de corte va como AAAA-MM-DD."},
                            status=status.HTTP_400_BAD_REQUEST)
        if corte > _dt.date.today():
            return Response({"detail": "La fecha de corte no puede estar en el futuro."},
                            status=status.HTTP_400_BAD_REQUEST)

        # A un temporal y no directo al directorio de cargas: si el Excel está
        # roto o ya se subió, no queda un archivo huérfano con nombre de hash
        # que después nadie sabe si corresponde a una carga real.
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        try:
            for trozo in archivo.chunks():
                tmp.write(trozo)
            tmp.close()
            carga = svc.previsualizar_completo(
                tmp.name, corte, usuario_id=request.user.id,
                archivo_nombre=archivo.name)
        except svc.CargaError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except KeyError as e:
            # Falta una hoja: el mensaje de `KeyError` es solo el nombre, y a
            # secas no se entiende. Se traduce, porque es el error más probable
            # cuando alguien sube el archivo equivocado.
            return Response(
                {"detail": f"El Excel no tiene la hoja {e}. ¿Es la Matriz de "
                           "Seguimiento PDL y no otro archivo?"},
                status=status.HTTP_400_BAD_REQUEST)
        finally:
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)

        return Response(_serializar(carga, con_diff=True),
                        status=status.HTTP_201_CREATED)


@extend_schema(tags=["Presupuesto"], summary="Una carga de la Matriz PDL")
class MatrizCargaDetailView(APIView):
    """`GET` el diff completo · `POST` aplica o descarta."""

    permission_classes = _PERMS

    def get(self, request, pk):
        carga = MatrizPDLCarga.objects.filter(id=pk).first()
        if carga is None:
            return Response({"detail": "Esa carga no existe."},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(_serializar(carga, con_diff=True))

    def post(self, request, pk):
        accion = (request.data.get("accion") or "").strip()
        if accion not in ("aplicar", "descartar"):
            return Response(
                {"detail": "`accion` tiene que ser «aplicar» o «descartar»."},
                status=status.HTTP_400_BAD_REQUEST)
        try:
            if accion == "aplicar":
                carga, hecho = svc.aplicar_completo(pk, usuario_id=request.user.id)
                return Response({**_serializar(carga, con_diff=True), "hecho": hecho})
            carga = svc.descartar(pk, nota=(request.data.get("nota") or "").strip() or None)
            return Response(_serializar(carga))
        except svc.CargaError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
