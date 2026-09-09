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


#: Leer la Matriz o el CRP es cosa de cualquiera con `presupuesto_proyectos`.
#: Escribirlos no: las dos cargas no editan una fila, sustituyen el libro
#: entero —el CRP marca `vigente=FALSE` todo lo que el archivo nuevo no
#: traiga—, así que un rol provisionado para UN contrato podía dejar el
#: comprometido de la localidad en el valor de su propia fila. Y no se deshace
#: desde la pantalla: el hash impide resubir el corte legítimo y el FK es
#: RESTRICT, así que recuperar exige entrar por SQL.
#:
#: El gate es «CDPs y contratos» y NO el alcance de `ve_todo`, aunque el
#: alcance sería lo conceptualmente exacto: hoy `ve_todo` solo es cierto para
#: superusuarios —los Admin que no lo son quedan acotados a su subgrupo
#: porque su pertenencia global todavía no está creada—, así que exigirlo
#: dejaría el cargue en manos de cuatro cuentas y rompería el flujo real.
#: `presupuesto_cdp` distingue exactamente lo que hay que distinguir: lo
#: tienen los Admin y no lo tiene el rol de contrato.
_PERMS_ESCRITURA = [ModuloRequiredPermission("presupuesto_cdp")]

_MSG_SOLO_LECTURA = ("Reemplazar el libro presupuestal de la localidad exige el "
                     "módulo de CDPs y contratos; tu rol está limitado a su "
                     "contrato.")


def _puede_reemplazar_el_libro(user) -> bool:
    from apps.login.services.permisos import superusuario_o_modulo
    return bool(user and user.is_authenticated
                and superusuario_o_modulo(user, "presupuesto_cdp"))


def _perms_con_escritura_acotada(vista):
    """`_PERMS` para leer; además el módulo de contratos para escribir."""
    perms = [p() for p in _PERMS]
    if vista.request.method not in ("GET", "HEAD", "OPTIONS"):
        perms += [p() for p in _PERMS_ESCRITURA]
    return perms

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
        # Aplicar reescribe el Plan de toda la localidad; previsualizar y
        # descartar no tocan nada publicado. Por eso el alcance se exige acá
        # y no en `get_permissions`: el permiso depende de la acción.
        if accion == "aplicar" and not _puede_reemplazar_el_libro(request.user):
            return Response({"detail": _MSG_SOLO_LECTURA},
                            status=status.HTTP_403_FORBIDDEN)
        try:
            if accion == "aplicar":
                carga, hecho = svc.aplicar_completo(pk, usuario_id=request.user.id)
                return Response({**_serializar(carga, con_diff=True), "hecho": hecho})
            carga = svc.descartar(pk, nota=(request.data.get("nota") or "").strip() or None)
            return Response(_serializar(carga))
        except svc.CargaError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────────────────────────────────────
# El CRP de BogData, en la MISMA pantalla que la Matriz.
#
# Son dos archivos distintos que alimentan el mismo tablero y los sube la
# misma persona: separarlos en dos pantallas obligaría a recordar cuál va
# dónde. Comparten el patrón —subir, ver qué haría, decidir— y no el motor:
# la Matriz previsualiza contra un diff guardado y el CRP contra sus seis
# cifras de control, que son formas distintas de contestar «¿esto está bien?».
# ─────────────────────────────────────────────────────────────────────────

def _serializar_crp_carga(c):
    return {
        "id": c.id,
        "archivo_nombre": c.archivo_nombre,
        "fecha_corte": c.fecha_corte.isoformat() if c.fecha_corte else None,
        "vigencia": c.vigencia,
        "filas_leidas": c.filas_leidas,
        "filas_insertadas": c.filas_insertadas,
        "filas_actualizadas": c.filas_actualizadas,
        "filas_no_vigentes": c.filas_no_vigentes,
        "compromisos_sin_contrato": c.compromisos_sin_contrato,
        "rubros_sin_proyecto": c.rubros_sin_proyecto,
        "total_valor_neto": float(c.total_valor_neto) if c.total_valor_neto else None,
        "total_aut_giro": float(c.total_aut_giro) if c.total_aut_giro else None,
        "subido_at": c.created_at.isoformat() if c.created_at else None,
        "nota": c.nota,
    }


@extend_schema(tags=["Presupuesto"], summary="Cargas del CRP de BogData")
class CrpCargaListView(APIView):
    """`GET` el historial · `POST` sube un reporte y lo carga.

    A DIFERENCIA DE LA MATRIZ, acá subir SÍ escribe, y no es una inconsistencia:
    la Matriz cambia el catálogo del Plan —qué programas existen, qué se
    retira— y eso hay que mirarlo antes de aplicarlo. El CRP es un estado de
    cuenta: sus 2.630 filas reemplazan el saldo anterior por la PK natural, no
    proponen nada que decidir. Lo que sí protege es el gate: si los seis
    totales no cuadran con el archivo, no se escribe ni una fila.
    """

    permission_classes = _PERMS
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        return _perms_con_escritura_acotada(self)

    def get(self, request):
        from apps.presupuesto.models import CrpCarga
        return Response({"items": [_serializar_crp_carga(c)
                                   for c in CrpCarga.objects.all()[:50]]})

    def post(self, request):
        from apps.presupuesto.services.crp_carga import CAMPOS_PLATA, CargaError, cargar_crp

        archivo = request.FILES.get("archivo")
        if archivo is None:
            return Response({"detail": "Falta el reporte de CRP (.xlsx)."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not archivo.name.lower().endswith((".xlsx", ".xlsm")):
            return Response({"detail": "El archivo tiene que ser un Excel (.xlsx)."},
                            status=status.HTTP_400_BAD_REQUEST)
        if archivo.size > MAX_BYTES:
            return Response(
                {"detail": f"El archivo pesa {archivo.size // 1024 // 1024} MB y el "
                           f"tope son {MAX_BYTES // 1024 // 1024} MB."},
                status=status.HTTP_400_BAD_REQUEST)

        # Los totales son OPCIONALES pero se piden en la pantalla: son la
        # única defensa contra un reporte truncado, que fila por fila se ve
        # perfecto. Si no se pasan, se carga igual y se avisa.
        esperados = None
        crudo = (request.data.get("totales") or "").strip()
        if crudo:
            partes = [p.strip() for p in crudo.split(",")]
            if len(partes) != len(CAMPOS_PLATA):
                return Response(
                    {"detail": f"Los totales van en el orden {', '.join(CAMPOS_PLATA)} "
                               f"— se esperaban {len(CAMPOS_PLATA)} y llegaron {len(partes)}."},
                    status=status.HTTP_400_BAD_REQUEST)
            try:
                esperados = dict(zip(CAMPOS_PLATA,
                                     (int(p.replace(".", "").replace(",", "").replace("$", ""))
                                      for p in partes)))
            except ValueError:
                return Response({"detail": "Alguno de los totales no es un número."},
                                status=status.HTTP_400_BAD_REQUEST)

        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        try:
            for trozo in archivo.chunks():
                tmp.write(trozo)
            tmp.close()
            salida = cargar_crp(tmp.name, usuario=request.user,
                                totales_esperados=esperados,
                                nota=(request.data.get("nota") or "").strip() or None)
        except CargaError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except KeyError as e:
            return Response(
                {"detail": f"El Excel no tiene la hoja {e}. ¿Es el reporte de CRP "
                           "de BogData y no otro archivo?"},
                status=status.HTTP_400_BAD_REQUEST)
        finally:
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)

        # El nombre real, no el del temporal.
        from apps.presupuesto.models import CrpCarga
        carga = CrpCarga.objects.filter(id=salida["carga_id"]).first()
        if carga:
            carga.archivo_nombre = archivo.name
            carga.save(update_fields=["archivo_nombre"])

        return Response({
            **_serializar_crp_carga(carga),
            "sin_totales": esperados is None,
            # Lo que no cruzó viaja recortado: 2.209 compromisos sin contrato
            # no caben en un aviso, y la lista entera la da el endpoint de
            # detalle o el comando.
            "compromisos_sin_contrato_muestra": salida["compromisos_sin_contrato"][:20],
            "rubros_sin_proyecto_muestra": salida["rubros_sin_proyecto"][:10],
            "choques_rubro_pep": len(salida["choques_rubro_pep"]),
            # Lo que ni siquiera se evaluó, aparte de lo que se evaluó y no
            # cruzó: si mañana BogData cambia el formato del número de
            # compromiso, este contador sube y el otro BAJA.
            "compromiso_no_parsea_filas": sum(
                v[0] for v in salida["compromiso_no_parsea"].values()),
            "compromiso_no_parsea_muestra": list(salida["compromiso_no_parsea"])[:20],
            "compromisos_ambiguos": salida["compromisos_ambiguos"],
            "proyecto_por_contrato": salida["proyecto_por_contrato"],
        }, status=status.HTTP_201_CREATED)
