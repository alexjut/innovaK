"""Carga de la Matriz PDL desde pantalla — endpoints DRF (Fase C).

El mismo flujo que ya existe por consola (`manage.py cargar_matriz_pdl`), pero
para que el área lo haga sin entrar al contenedor. Cuatro tiempos, y la
compuerta humana está entre el segundo y el tercero:

    0. prevalidar  → lee el .xlsx y devuelve el diff. **No persiste NADA.**
    1. subir       → registra el borrador con su diff (POST a la lista)
    2. previsualizar → el borrador con su diff GUARDADO (GET al detalle)
    3. aplicar / descartar → el paso que escribe, o el que cierra sin escribir

El paso 0 no es un lujo: `hash_sha256` es UNIQUE y **nada lo libera** —ni
descartar—, así que subir «solo para mirar» quema el archivo para siempre. Es
el mismo modo seco que el `--seco` del comando, y se apoya en dos funciones
públicas del motor (`leer_jerarquia` + `calcular_diff`); no reimplementa nada.

QUÉ CUBRE Y QUÉ NO
------------------
Solo la JERARQUÍA: sectores, objetivos estratégicos y programas. **No sube
plata, ni metas, ni magnitudes** — eso sigue entrando por
`importar_matriz_pdl_alk`. El archivo se llama «Matriz de seguimiento PDL» y
trae dinero adentro, así que el malentendido es el default: por eso el alcance
va escrito en el payload (`ALCANCE`) y no solo en la plantilla.

QUIÉN PUEDE QUÉ
---------------
Gate único: el módulo `presupuesto_proyectos`, el mismo de las ~45 vistas de
presupuesto y el que ya gobierna la sección `/presupuesto` del sidebar. Con eso
la pantalla no queda visible-pero-403 y no hace falta sembrar un módulo nuevo
(uno sin sembrar deja afuera a TODOS menos a los superusuarios, y falla en
silencio en despliegue).

`ModuloRequiredPermission` ya trae el gate RBAC B0: **Visor queda fuera de todo
POST** con «Tu rol es de solo lectura.». Eso incluye `prevalidar`, que es un
POST aunque no escriba. Queda dicho acá para que no se descubra en producción:
la pantalla debe ESCONDER la barra de subida a quien no puede escribir, y para
eso el payload trae `puede_subir` / `puede_aplicar` con su motivo.

NO se crea el rol `Planeacion` en esta entrega — es decisión de organigrama de
Alex y hoy no existe el grupo. El enganche sí está hecho: `puede_aplicar` y
`puede_aplicar_motivo` viajan EN EL PAYLOAD (el patrón que `ContratoEtapaView`
documenta a lo largo), así que el día que el rol exista el cambio es
`permission_classes = _PERMS + [PlaneacionPermission]` —lista NUEVA, jamás
`_PERMS.append(...)`, que le pondría el candado a todo presupuesto— más una
rama en `_puede_aplicar`. **Cero cambios en Angular.** Cuando llegue ese día:
el grupo nace del seed (`ROLES_GESTIONADOS` + `ASIGNACION_INICIAL` en
`seed_modulos.py`) y NUNCA de `/admin/roles`, que acepta texto libre; sin
tilde, en ASCII, y sin empezar por «Coordinador» (cualquier grupo con ese
prefijo gana poder de creación de actividades/eventos/contratos por RBAC).

Y una advertencia que no se busca donde no está: **la consola se salta todos
los permisos**. `manage.py cargar_matriz_pdl --aplicar N` recibe `--usuario-id`
como DATO, no como identidad. Está bien —consola = acceso al contenedor— pero
significa que cualquier regla de quién aplica vive EXCLUSIVAMENTE en esta capa
web, no dentro del servicio.

CÓMO ESTÁ ORDENADO EL ARCHIVO
-----------------------------
Arriba las guardas de entrada (tope, tipo, zip, cuota, corte, temporal), en el
medio las vistas, y al final los helpers de presentación (`_a_renglones`,
`_avisos`, `_carga_json`) — igual que `_lote_json` en el cargue de jóvenes.
"""
from __future__ import annotations

import logging
import os
import tempfile
import zipfile
from contextlib import contextmanager
from datetime import date

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import IntegrityError, connection, transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import ModuloRequiredPermission
from apps.presupuesto.models import (MatrizPDLCarga, ObjetivoEstrategico,
                                     ProgramaPDL, Sector)
from apps.presupuesto.services import matriz_carga as svc

logger = logging.getLogger(__name__)

#: El módulo que gatea la pantalla. Se reusa el de presupuesto a propósito
#: (ver el docstring del módulo): inventar uno nuevo sin sembrarlo deja a
#: todos afuera y el 403 no explica por qué.
MODULO = "presupuesto_proyectos"
_PERMS = [ModuloRequiredPermission(MODULO)]

#: Tope de bytes del archivo. El .xlsx real de la Matriz pesa ~102 KB, así que
#: 2 MB son 20× de holgura. No es 10 MB como en el cargue de jóvenes por una
#: razón concreta: `core/settings.py` NO sobreescribe
#: `FILE_UPLOAD_MAX_MEMORY_SIZE` (2,5 MB por defecto), así que con este tope
#: **todo archivo aceptado llegó en memoria** y el único archivo que tocamos en
#: disco es el temporal nuestro. Además mantiene el parseo lejos del
#: `--timeout 120` de gunicorn (docker-compose.yml:54, `--workers 3`), que mata
#: al worker con una señal en cuyo camino el `finally` que borra el temporal NO
#: se ejecuta. nginx corta antes, en 20M (nginx.conf:85), y ése es otro tope:
#: el suyo evita la TRANSFERENCIA, el nuestro evita el PARSEO.
MAX_BYTES = 2 * 1024 * 1024

#: Un .xlsx es un ZIP por dentro. Se lee solo el directorio central (unos
#: microsegundos) y se suman los tamaños descomprimidos: es lo que impide que
#: un archivo de 2 MB con una tabla de cadenas compartidas monstruosa tenga a
#: openpyxl 120 s comiendo RAM y se lleve un tercio del servidor. Es una
#: GUARDA, no lógica de negocio: no reimplementa nada del motor.
MAX_DESCOMPRIMIDO = 120 * 1024 * 1024

#: El único tipo que se acepta, y la extensión que le corresponde.
MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

#: `content_type` que se aceptan además del oficial. Acá se afloja a propósito
#: respecto de `formulacion_views.MIMES`, y por un motivo que no aplica allá:
#: ahí la lista blanca tiene 7 tipos y el MIME es lo que los discrimina; acá el
#: tipo aceptado es UNO solo, la extensión ya lo discrimina, y el filtro de
#: verdad es que el archivo abra como zip y traiga las dos hojas de la matriz.
#: Un navegador sin `shared-mime-info` manda `application/octet-stream` para un
#: .xlsx perfectamente válido, y rechazarlo dejaría al área trabada con un
#: mensaje que no explica nada.
MIMES_GENERICOS = {"", "application/octet-stream", "application/zip",
                   "application/x-zip-compressed"}

#: El PDL 2025-2028 arranca en 2025: una fecha de corte anterior es un dedazo.
CORTE_MINIMO = date(2025, 1, 1)

#: Cuota de intentos por usuario y ventana (10 min). Se cuenta en CACHÉ y NO
#: en `presu_matriz_carga`: un archivo que no parsea no deja fila, así que
#: contar filas dejaría fuera del tope justo al abuso más barato —mandar
#: basura—, que es el que de verdad ocupa los 3 workers. Si la caché no
#: responde, no se bloquea a nadie: esto frena el martilleo, no es un control
#: de acceso.
MAX_INTENTOS = 10
VENTANA_INTENTOS = 10 * 60

#: Llave del advisory lock que serializa las subidas. Ver `_turno_de_subida`.
_LOCK_SUBIDA = 0x4D505F43  # 'MP_C' — Matriz PDL · Carga

#: Umbral del aviso de retiro masivo. La mitad del catálogo activo es señal de
#: un Excel truncado o de otro corte; el mínimo de 3 evita que un catálogo
#: chico dispare la alarma por una sola baja legítima.
UMBRAL_RETIRO_MASIVO = 0.5
MINIMO_RETIRO_MASIVO = 3

#: La frase de alcance, servida desde acá para que la pantalla no tenga su
#: propia versión que envejezca aparte.
ALCANCE = ("Esto actualiza el catálogo del Plan: sectores, objetivos "
           "estratégicos y programas. No mueve presupuesto ni magnitudes. "
           "Lo que se retira queda marcado como inactivo, no se borra.")

ETIQUETA_ENTIDAD = {"sector": "Sector",
                    "objetivo": "Objetivo estratégico",
                    "programa": "Programa"}
ETIQUETA_CAMPO = {"nombre": "Nombre", "objetivo": "Objetivo estratégico"}

#: Orden en que se entregan los renglones del diff, y no es indiferente: los
#: RETIROS van primero porque son la única clase que quita algo y el síntoma de
#: un archivo equivocado (un Excel truncado se manifiesta como una lista enorme
#: de retiros). Puestos donde se leen sin scroll, un error caro se vuelve
#: visible.
ORDEN_CLASES = ("retiros", "altas", "cambios", "reactivaciones")


# ─────────────────────────────────────────────────────────────────────
# Guardas de entrada
# ─────────────────────────────────────────────────────────────────────

def _archivo_de(request):
    """`(archivo, None)` o `(None, Response de error)`."""
    archivo = request.FILES.get("archivo")
    if archivo is None:
        return None, Response(
            {"detail": "Falta el archivo. Envíelo como 'archivo' en multipart/form-data."},
            status=status.HTTP_400_BAD_REQUEST)
    if archivo.size == 0:
        return None, Response({"detail": "El archivo está vacío."},
                              status=status.HTTP_400_BAD_REQUEST)
    if archivo.size > MAX_BYTES:
        return None, Response(
            {"detail": f"El archivo pesa {archivo.size // 1024} KB y el tope es "
                       f"{MAX_BYTES // 1024} KB. La Matriz PDL pesa unos 100 KB: "
                       f"revise que sea el archivo correcto."},
            status=status.HTTP_400_BAD_REQUEST)

    mime = (archivo.content_type or "").split(";")[0].strip().lower()
    extension = os.path.splitext(archivo.name or "")[1].lower()
    if extension != ".xlsx" or (mime != MIME_XLSX and mime not in MIMES_GENERICOS):
        return None, Response(
            {"detail": "El archivo tiene que ser un Excel .xlsx. Si lo abrió en "
                       "Excel, use «Guardar como → Libro de Excel (.xlsx)»."},
            status=status.HTTP_400_BAD_REQUEST)
    return archivo, None


def _corte_de(request):
    """`(date, None)` o `(None, Response de error)`.

    Se valida contra el calendario y no solo contra el formato: es la fecha que
    DECLARA quien sube (no la de subida), no hay pantalla para corregirla, y
    ordena todo el historial (`ordering = ['-corte_oficial', …]`). Un dedazo en
    el año deja esa carga clavada arriba de todos los listados para siempre.
    """
    crudo = (request.data.get("corte_oficial") or "").strip()
    if not crudo:
        return None, Response(
            {"detail": "Falta la fecha de corte del archivo (la que trae la "
                       "matriz de la ALK, no la de hoy)."},
            status=status.HTTP_400_BAD_REQUEST)
    try:
        corte = date.fromisoformat(crudo)
    except ValueError:
        return None, Response({"detail": "La fecha de corte va en formato AAAA-MM-DD."},
                              status=status.HTTP_400_BAD_REQUEST)
    if corte > date.today():
        return None, Response(
            {"detail": "La fecha de corte es posterior a hoy. Revise el año."},
            status=status.HTTP_400_BAD_REQUEST)
    if corte < CORTE_MINIMO:
        return None, Response(
            {"detail": f"La fecha de corte es anterior a {CORTE_MINIMO.isoformat()} "
                       f"y el PDL 2025-2028 arranca en 2025. Revise el año."},
            status=status.HTTP_400_BAD_REQUEST)
    return corte, None


def _cuota_excedida(request):
    """Response 429 si el usuario se pasó de intentos en la ventana, o None."""
    uid = getattr(request.user, "id", None)
    if not uid:
        return None
    clave = f"matriz_pdl:intentos:{uid}"
    try:
        # `add` solo escribe si la clave no existe, así que el TTL se cuenta
        # desde el PRIMER intento: ventana fija, no una que se renueva sola con
        # cada golpe (que sería un bloqueo permanente para quien insiste).
        cache.add(clave, 0, VENTANA_INTENTOS)
        intentos = cache.incr(clave)
    except Exception:  # noqa: BLE001 - caché caída no puede frenar el trabajo
        logger.warning("No se pudo contar los intentos de subida de la Matriz PDL.")
        return None
    if intentos > MAX_INTENTOS:
        return Response(
            {"detail": f"Ya intentó subir {MAX_INTENTOS} archivos en pocos minutos. "
                       f"Espere unos minutos antes de volver a intentarlo."},
            status=status.HTTP_429_TOO_MANY_REQUESTS)
    return None


def _revisar_zip(ruta):
    """Motivo por el que NO se debe abrir con openpyxl, o `None` si está bien."""
    try:
        with zipfile.ZipFile(ruta) as z:
            descomprimido = sum(e.file_size for e in z.infolist())
    except zipfile.BadZipFile:
        return ("El archivo no es un .xlsx válido: por dentro un .xlsx es un ZIP "
                "y éste no lo es. Vuelva a guardarlo desde Excel como «Libro de "
                "Excel (.xlsx)».")
    except OSError:
        return "No se pudo leer el archivo subido."
    if descomprimido > MAX_DESCOMPRIMIDO:
        return (f"El archivo se expande a {descomprimido // (1024 * 1024)} MB al "
                f"abrirlo y el tope es {MAX_DESCOMPRIMIDO // (1024 * 1024)} MB. "
                f"No parece la Matriz PDL.")
    return None


@contextmanager
def _ruta_temporal(subido):
    """Vuelca el `UploadedFile` a un archivo real y entrega su RUTA.

    Existe porque el motor recibe una ruta y la toca TRES veces, y solo una de
    las tres toleraría un objeto: `MatrizPDLCarga.hash_de(ruta)` hace
    `open(ruta, 'rb')`, y el `create` de `previsualizar` hace
    `os.path.getsize(ruta)` y `os.path.basename(ruta)`. Un `UploadedFile`
    revienta ahí con TypeError.

    POR QUÉ ACÁ Y NO EN EL SERVICIO: el contrato del motor es «una ruta», está
    commiteado y probado; que la entrada llegue como un objeto en memoria es un
    hecho del transporte HTTP. Adaptar el transporte al contrato del servicio
    es el trabajo de la vista — no se recalcula ni un hash ni un diff.

    POR QUÉ NO `subido.temporary_file_path()`: `core/settings.py` no toca
    `FILE_UPLOAD_MAX_MEMORY_SIZE`, así que rige el default de 2,5 MB y —con
    nuestro tope de 2 MB— la matriz llega SIEMPRE como `InMemoryUploadedFile`,
    clase que no tiene ese método.

    POR QUÉ `delete=False` + `os.unlink` y no `with NamedTemporaryFile(...)`:
    `leer_jerarquia` abre openpyxl con `read_only=True` y **nunca llama a
    `wb.close()`**, así que el zip sigue abierto cuando el `with` intentaría
    borrar. En Linux el unlink diferido funciona, pero cada petición filtraría
    un descriptor. El borrado va cuando nosotros decidimos.

    POR QUÉ AL TEMP DEL SISTEMA (`dir=None`) y no al árbol del proyecto: en
    esta máquina el contenedor monta el árbol de trabajo y trabajan dos
    personas; un temporal en `BASE_DIR` lo ve el otro, aparece en `git status`
    y algún día se commitea. El prefijo `matriz_pdl_` es para reconocer de un
    vistazo a un huérfano (que puede quedar si el worker muere entre el write y
    el `finally`: ~100 KB por incidente, sin acumulación realista).
    """
    tmp = tempfile.NamedTemporaryFile(prefix="matriz_pdl_", suffix=".xlsx",
                                      delete=False)
    ruta = tmp.name
    try:
        try:
            for trozo in subido.chunks():
                tmp.write(trozo)
            tmp.flush()
        finally:
            tmp.close()
        yield ruta
    finally:
        try:
            os.unlink(ruta)
        except OSError:
            logger.warning("Quedó sin borrar el temporal %s", ruta)


def _turno_de_subida():
    """Toma el advisory lock que hace de turno único para subir.

    La invariante que sostiene es «un solo borrador abierto a la vez», y hace
    falta porque el motor no la impone: `previsualizar` solo mira el hash, así
    que hoy pueden convivir dos borradores calculados contra la MISMA base.
    Aplicar el primero y después el segundo hace que el segundo intente crear
    lo que el primero ya creó → `IntegrityError` contra el UNIQUE de
    `presu_sector.nombre_oficial` o `presu_objetivo_estrategico.codigo`, que no
    es `CargaError` y saldría como 500 con un texto que no le sirve a nadie.

    POR QUÉ UN LOCK Y NO UN `.exists()` PELADO: dos subidas simultáneas de
    archivos DISTINTOS pasarían las dos el chequeo y crearían dos borradores.
    El advisory lock se suelta solo al terminar la transacción, así que el
    chequeo y el INSERT quedan dentro del mismo turno. Se serializan las
    subidas (~1 s cada una, unas pocas al año): es un precio que no se siente.
    """
    with connection.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(%s)", [_LOCK_SUBIDA])


def _puede_escribir(request):
    """`(True, None)` o `(False, motivo)`. El motivo es texto de pantalla."""
    from apps.login.services.permisos import bloquea_escritura

    if bloquea_escritura(request.user, "POST", MODULO):
        return False, ("Su rol es de solo lectura: puede consultar el historial, "
                       "pero no subir ni aplicar la matriz.")
    return True, None


# ─────────────────────────────────────────────────────────────────────
# Vistas
# ─────────────────────────────────────────────────────────────────────

class MatrizCargaPrevalidarView(APIView):
    """POST — lee el .xlsx y devuelve el diff. **No persiste NADA.**

    multipart/form-data:
        archivo  (obligatorio) el .xlsx de la ALK

    Es el paso que permite mirar sin comprometerse, y no es un adorno: el
    UNIQUE de `hash_sha256` no se libera nunca —tampoco al descartar—, así que
    una subida «solo para ver» quema el archivo para siempre. Acá se llama a
    `leer_jerarquia` + `calcular_diff`, exactamente lo que hace el `--seco` del
    comando de consola.

    Aunque el archivo ya se haya subido antes, el diff se calcula igual y se
    devuelve: poder ver qué dice ese archivo es justo el valor del ensayo. Lo
    que cambia es `puede_subir`, que sale en `false` con el motivo.

    OJO: es un POST, así que `ModuloRequiredPermission` lo cierra a los roles
    de solo lectura aunque no escriba nada. Es correcto y es intencional, pero
    la pantalla tiene que esconder la barra de subida (ver `puede_subir`) o el
    botón «Revisar» contradice su propia etiqueta.
    """
    permission_classes = _PERMS

    def post(self, request):
        archivo, error = _archivo_de(request)
        if error is not None:
            return error
        error = _cuota_excedida(request)
        if error is not None:
            return error

        try:
            with _ruta_temporal(archivo) as ruta:
                motivo = _revisar_zip(ruta)
                if motivo:
                    return Response({"detail": motivo},
                                    status=status.HTTP_400_BAD_REQUEST)
                # El hash se calcula con `MatrizPDLCarga.hash_de` (que recibe
                # una RUTA) y NUNCA con el `sha256_de` de jóvenes (que recibe
                # un file-object): el UNIQUE de la base se llena con la
                # primera, así que con la otra se compararía contra un valor
                # que nadie escribió.
                huella = MatrizPDLCarga.hash_de(ruta)
                previa = MatrizPDLCarga.objects.filter(hash_sha256=huella).first()
                diff = svc.calcular_diff(svc.leer_jerarquia(ruta))
        except svc.CargaError as exc:
            # El motivo va tal cual: los mensajes de `CargaError` ya están
            # redactados para que los lea una persona («En «Seguimiento» la
            # columna 0 debería ser…»). No es culpa del servidor: 400.
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:  # noqa: BLE001
            logger.exception("Fallo revisando el Excel de la Matriz PDL")
            return Response({"detail": "No se pudo leer el archivo. No se guardó nada."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        vigente = _vigente()
        abierto = _borrador_abierto()
        escribe, motivo_escritura = _puede_escribir(request)

        duplicado = None
        if previa is not None:
            duplicado = {
                "carga_id": previa.id,
                "estado": previa.estado,
                "corte_oficial": (previa.corte_oficial.isoformat()
                                  if previa.corte_oficial else None),
                "subido_at": previa.subido_at.isoformat() if previa.subido_at else None,
                "texto": (f"Este archivo ya se subió: carga {previa.id} del "
                          f"{previa.subido_at:%Y-%m-%d}, estado «{previa.estado}». "
                          f"Descartar una carga NO libera el archivo: si es un "
                          f"corte nuevo, tiene que ser un archivo distinto."),
            }

        puede_subir = escribe and duplicado is None and abierto is None
        return Response({
            "archivo": {"nombre": archivo.name, "bytes": archivo.size,
                        "hash_sha256": huella},
            "estado_revision": _estado_revision(diff),
            "resumen": _resumen(diff),
            "cambios": _a_renglones(diff),
            "avisos": _avisos(diff, vigente),
            "vigente": vigente,
            "alcance": ALCANCE,
            # El diff crudo viaja como evidencia y para depurar. La pantalla
            # renderiza `cambios`, que es su traducción; si pintara una versión
            # propia del diff, «lo que alguien miró y aprobó» dejaría de ser
            # verificable contra lo que se guarda.
            "diff": diff,
            "duplicado": duplicado,
            "borrador_abierto": abierto,
            "puede_subir": puede_subir,
            "siguiente_paso": _siguiente_paso(
                escribe, motivo_escritura, duplicado, abierto, _estado_revision(diff)),
        })


class MatrizCargaListCreateView(APIView):
    """GET el historial y el estado vigente · POST sube y crea el borrador."""
    permission_classes = _PERMS

    def get(self, request):
        """GET — una sola llamada pinta la pantalla de entrada.

        Devuelve el historial, lo que el Plan tiene HOY y el borrador sin
        resolver si lo hay. El estado vigente va acá y no en un endpoint aparte
        porque hace falta ANTES de subir: «salen 9 sectores» no significa nada
        si no se sabe cuántos hay.
        """
        cargas = list(MatrizPDLCarga.objects.all()[:30])
        nombres = _nombres_de_usuario(
            [c.subido_por_id for c in cargas] + [c.aplicado_por_id for c in cargas])
        ultima = _ultima_aplicada()
        escribe, motivo = _puede_escribir(request)
        return Response({
            "cargas": [_carga_json(c, request=request, nombres=nombres,
                                   ultima_aplicada=ultima,
                                   escritura=(escribe, motivo)) for c in cargas],
            "vigente": _vigente(ultima=ultima, nombres=nombres),
            "borrador_abierto": _borrador_abierto(),
            "alcance": ALCANCE,
            "puede_subir": escribe,
            "puede_subir_motivo": motivo,
        })

    def post(self, request):
        """POST — registra el borrador con su diff. Todavía NO escribe el Plan.

        multipart/form-data:
            archivo        (obligatorio) el .xlsx de la ALK
            corte_oficial  (obligatorio) AAAA-MM-DD, la fecha que trae la matriz
        """
        archivo, error = _archivo_de(request)
        if error is not None:
            return error
        corte, error = _corte_de(request)
        if error is not None:
            return error
        error = _cuota_excedida(request)
        if error is not None:
            return error

        # La validación de extensión garantiza que `archivo.name` no viene
        # vacío. Se pasa EXPLÍCITO porque si no, `previsualizar` cae en
        # `os.path.basename(ruta)` y guardaría el nombre aleatorio del temporal
        # («tmp8f3k2x.xlsx») — que es justo lo que la pantalla del historial le
        # muestra a la persona para reconocer qué subió.
        nombre = os.path.basename(archivo.name)[:255]

        try:
            with _ruta_temporal(archivo) as ruta:
                motivo = _revisar_zip(ruta)
                if motivo:
                    return Response({"detail": motivo},
                                    status=status.HTTP_400_BAD_REQUEST)
                with transaction.atomic():
                    _turno_de_subida()
                    abierto = _borrador_abierto()
                    if abierto is not None:
                        return Response(
                            {"detail": f"Hay una revisión sin terminar: la carga "
                                       f"{abierto['id']} (corte "
                                       f"{abierto['corte_oficial']}). Termínela "
                                       f"—aplicar o descartar— antes de subir otra "
                                       f"matriz.",
                             "borrador_abierto": abierto},
                            status=status.HTTP_409_CONFLICT)
                    carga = svc.previsualizar(
                        ruta, corte, usuario_id=request.user.id,
                        archivo_nombre=nombre)
        except svc.CargaError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError:
            # El UNIQUE del hash. No es `CargaError`, así que sin esta rama
            # saldría como 500 después de que el usuario hizo algo razonable.
            logger.exception("IntegrityError registrando la carga de la Matriz PDL")
            return Response(
                {"detail": "Ese archivo se registró desde otra pestaña o por otra "
                           "persona mientras se subía. Recargue el historial."},
                status=status.HTTP_409_CONFLICT)
        except Exception:  # noqa: BLE001
            logger.exception("Fallo registrando la carga de la Matriz PDL")
            return Response({"detail": "No se pudo leer el archivo. No se guardó nada."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(_carga_json(carga, detalle=True, request=request),
                        status=status.HTTP_201_CREATED)


class MatrizCargaDetalleView(APIView):
    """GET — la carga con su diff GUARDADO. Es la pantalla de previsualizar.

    **No se recalcula nada**: `aplicar` escribe el diff que se guardó, porque
    lo que se aplica tiene que ser exactamente lo que alguien miró y aprobó.
    Volver a llamar a `calcular_diff` acá rompería esa garantía en silencio.
    """
    permission_classes = _PERMS

    def get(self, request, pk):
        carga = get_object_or_404(MatrizPDLCarga, pk=pk)
        return Response(_carga_json(carga, detalle=True, request=request))


class MatrizCargaAplicarView(APIView):
    """POST — escribe el catálogo del Plan. Es el paso que sí persiste.

    Cuerpo: `{}`. Solo viaja el id de la URL — **nunca el diff**: reenviarlo
    desde el cliente sería dejar que el navegador decida qué se escribe.

    NO se envuelve en `transaction.atomic`: el servicio ya lo está y toma
    `select_for_update()` sobre su propia fila. Un atomic externo solo alargaría
    el bloqueo, y —esto importa— movería el chequeo de estado fuera de la
    transacción que toma el lock, que es justo lo que hace que dos personas
    aplicando la MISMA carga esté cubierto: la segunda queda bloqueada en el
    SELECT, y al soltarse el lock re-lee la fila ya en «aplicada» y sale por
    `CargaError`. No hay doble escritura. Si alguien mueve ese chequeo o
    envuelve `aplicar` en un atomic que empiece antes, esa garantía se cae.
    """
    permission_classes = _PERMS

    def post(self, request, pk):
        carga = get_object_or_404(MatrizPDLCarga, pk=pk)

        # EL PORTÓN DE ESCRITURA, ANTES QUE EL ESTADO.
        #
        # Faltaba: esta vista publicaba `puede_aplicar` en el payload y NO lo
        # exigía. Hoy la diferencia no se nota —`ModuloRequiredPermission` ya
        # corta a los roles de solo lectura en POST—, y por eso el hueco es
        # fácil de no ver: el día que `_puede_escribir` distinga a Planeación
        # del resto, la pantalla escondería el botón y el endpoint lo seguiría
        # aceptando. Un permiso que se anuncia y no se exige es peor que no
        # anunciarlo.
        #
        # 403 y no 409: no es un conflicto de estado, es que este usuario no
        # puede escribir el catálogo del Plan.
        escribe, motivo = _puede_escribir(request)
        if not escribe:
            return Response({"detail": motivo}, status=status.HTTP_403_FORBIDDEN)

        # Pre-vuelo ADVISORY: se lee sin bloqueo, solo para poder devolver un
        # 409 con un mensaje útil. La verificación que de verdad protege es la
        # que hace el servicio dentro de su transacción. No se duplica lógica:
        # se duplica una LECTURA para mejorar el código de estado.
        if carga.estado != MatrizPDLCarga.BORRADOR:
            return Response({"detail": _motivo_no_borrador(carga)},
                            status=status.HTTP_409_CONFLICT)
        otra = _aplicada_despues(carga, _ultima_aplicada())
        if otra is not None:
            # Segunda capa sobre la regla de un solo borrador: ésta también
            # cubre que la base se haya movido por otra vía (una corrida de
            # `manage.py cargar_matriz_pdl --aplicar N` o de
            # `importar_matriz_pdl_alk`), donde no hubo borrador que estorbara.
            return Response({"detail": _motivo_obsoleta(otra)},
                            status=status.HTTP_409_CONFLICT)

        try:
            # OJO: devuelve una TUPLA `(carga, hecho)`, no un dict como el
            # `procesar` del cargue de jóvenes. Copiar aquella línea revienta.
            carga, hecho = svc.aplicar(pk, usuario_id=request.user.id)
        except svc.CargaError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError:
            logger.exception("IntegrityError aplicando la carga %s de la Matriz PDL", pk)
            return Response(
                {"detail": "Otra carga ya escribió parte de estos cambios. NO se "
                           "escribió nada; vuelva a subir el archivo para ver qué "
                           "falta."},
                status=status.HTTP_409_CONFLICT)
        except Exception:  # noqa: BLE001
            logger.exception("Fallo aplicando la carga %s de la Matriz PDL", pk)
            return Response({"detail": "No se pudo aplicar la carga. No se guardó nada."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        carga.refresh_from_db()

        # Se compara lo HECHO contra lo esperado. `n_cambios` trae las
        # reactivaciones sumadas adentro (así lo decidió `_contar` en el
        # servicio), por eso la suma del lado izquierdo.
        coincide = (hecho["altas"] == carga.n_altas
                    and hecho["cambios"] + hecho["reactivaciones"] == carga.n_cambios
                    and hecho["retiros"] == carga.n_retiros)
        return Response({
            # Se devuelve `hecho` —lo que de verdad pasó—, no `n_altas/
            # n_cambios/n_retiros`, que es lo que se esperaba. Son dos juegos
            # de claves distintos y divergen justo cuando importa: si la base
            # cambió en el medio, los `update()` devuelven 0 y nadie se entera.
            "hecho": hecho,
            "coincide": coincide,
            "resultado_texto": _frase_hecho(hecho),
            "aviso": None if coincide else (
                "Se aplicó menos de lo que se revisó: la base cambió entre la "
                "revisión y ahora. Vuelva a subir el archivo para ver qué falta."),
            "alcance": ALCANCE,
            "carga": _carga_json(carga, detalle=True, request=request),
        })


class MatrizCargaDescartarView(APIView):
    """POST — cierra un borrador sin aplicarlo.

    Cuerpo JSON: `{"nota": "por qué se descarta"}` — **obligatoria**. El motor
    la acepta opcional; acá se exige porque descartar es lo ÚNICO irreversible
    de estas pantallas (el UNIQUE del hash no se libera nunca) y la nota es el
    único rastro que queda de una carga que jamás se aplicó.

    Es el único sitio donde la vista agrega una transacción a propósito:
    `descartar` no es atómica ni toma `select_for_update` (a diferencia de
    `aplicar`), así que un aplicar y un descartar simultáneos se cruzan —
    `aplicar` commitea con todo escrito y el `save` de `descartar` deja la fila
    en «descartada». El Plan quedaría cambiado y el registro diría lo
    contrario, que es justo lo que un plan de desarrollo tiene que poder
    contestar. El CHECK de la base no lo atrapa.
    """
    permission_classes = _PERMS

    def post(self, request, pk):
        # Mismo portón que `aplicar`, y por el mismo motivo: descartar es lo
        # único IRREVERSIBLE del módulo —el UNIQUE del hash no se libera— y
        # publicaba `puede_descartar` sin exigirlo.
        escribe, motivo = _puede_escribir(request)
        if not escribe:
            return Response({"detail": motivo}, status=status.HTTP_403_FORBIDDEN)

        nota = (request.data.get("nota") or "").strip()
        if len(nota) < 5:
            return Response(
                {"detail": "Escriba por qué se descarta. Es lo único que queda de "
                           "esta carga, y el archivo no se va a poder volver a subir."},
                status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                fila = MatrizPDLCarga.objects.select_for_update().filter(pk=pk).first()
                if fila is None:
                    return Response({"detail": f"No existe la carga {pk}."},
                                    status=status.HTTP_404_NOT_FOUND)
                if fila.estado != MatrizPDLCarga.BORRADOR:
                    return Response({"detail": _motivo_no_borrador(fila)},
                                    status=status.HTTP_409_CONFLICT)
                # `descartar` hace `carga.nota = nota` SIN condicional: un None
                # pisaría lo que hubiera escrito antes. Hoy la nota es
                # obligatoria y el respaldo no se dispara nunca; queda para que
                # aflojar esa regla mañana no borre una nota en silencio.
                carga = svc.descartar(pk, nota=nota or fila.nota)
        except svc.CargaError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:  # noqa: BLE001
            logger.exception("Fallo descartando la carga %s de la Matriz PDL", pk)
            return Response({"detail": "No se pudo descartar la carga."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"carga": _carga_json(carga, detalle=True, request=request)})


# ─────────────────────────────────────────────────────────────────────
# Estado vigente y consultas de apoyo
# ─────────────────────────────────────────────────────────────────────

def _ultima_aplicada():
    return (MatrizPDLCarga.objects
            .filter(estado=MatrizPDLCarga.APLICADA, aplicado_at__isnull=False)
            .order_by("-aplicado_at").first())


def _borrador_abierto():
    """El borrador sin resolver, o None.

    Sale en el payload para que la pantalla pueda ofrecer «Continuar la
    revisión»: si se cierra la pestaña entre subir y aplicar, el borrador queda
    vivo en la base y sin esta fila la persona creería que se perdió y subiría
    el archivo otra vez — que ahora se rechaza por repetido.
    """
    b = (MatrizPDLCarga.objects
         .filter(estado=MatrizPDLCarga.BORRADOR).order_by("-subido_at").first())
    if b is None:
        return None
    return {"id": b.id,
            "corte_oficial": b.corte_oficial.isoformat() if b.corte_oficial else None,
            "archivo_nombre": b.archivo_nombre,
            "subido_at": b.subido_at.isoformat() if b.subido_at else None}


def _conteos_vigentes():
    """Cuántas filas ACTIVAS hay hoy de cada entidad.

    Solo activas: es contra las activas que el motor calcula los retiros, así
    que es el denominador honesto para el aviso de retiro masivo.
    """
    return {"sectores": Sector.objects.filter(activo=True).count(),
            "objetivos": ObjetivoEstrategico.objects.filter(activo=True).count(),
            "programas": ProgramaPDL.objects.filter(activo=True).count()}


def _vigente(ultima=None, nombres=None):
    """Lo que el Plan tiene HOY, más la última carga aplicada."""
    datos = _conteos_vigentes()
    ultima = ultima if ultima is not None else _ultima_aplicada()
    if ultima is None:
        datos["ultima_aplicada"] = None
        return datos
    nombres = nombres if nombres is not None else _nombres_de_usuario(
        [ultima.aplicado_por_id])
    datos["ultima_aplicada"] = {
        "id": ultima.id,
        "corte_oficial": (ultima.corte_oficial.isoformat()
                          if ultima.corte_oficial else None),
        "aplicado_at": ultima.aplicado_at.isoformat() if ultima.aplicado_at else None,
        "aplicado_por": nombres.get(ultima.aplicado_por_id),
    }
    return datos


def _nombres_de_usuario(ids):
    """`{id: nombre}` para mostrar quién subió y quién aplicó.

    `subido_por_id` y `aplicado_por_id` son `IntegerField` sueltos, NO claves
    foráneas: no hay `select_related` que traiga el nombre, hay que resolverlo
    aparte. Una sola consulta para todo el lote.
    """
    ids = {i for i in ids if i}
    if not ids:
        return {}
    usuarios = get_user_model().objects.filter(id__in=ids)
    return {u.id: (f"{u.first_name} {u.last_name}".strip() or u.get_username())
            for u in usuarios}


def _aplicada_despues(carga, ultima):
    """La carga que se aplicó DESPUÉS de que ésta se previsualizó, o None.

    Su diff se calculó contra el estado que había en `subido_at`; si desde
    entonces se aplicó otra carga, describe un mundo que ya no existe. Sin este
    chequeo, aplicarla choca contra un UNIQUE y sale un 500 sin explicación en
    vez de una frase que se entiende. Y no se puede «recalcular» en su lugar:
    el archivo no se persiste (`archivo_bytes` es el TAMAÑO, no el contenido),
    y aunque se pudiera, se estaría aplicando algo que nadie miró.
    """
    if ultima is None or ultima.id == carga.id:
        return None
    if not (carga.subido_at and ultima.aplicado_at):
        return None
    return ultima if ultima.aplicado_at > carga.subido_at else None


def _motivo_no_borrador(carga):
    if carga.estado == MatrizPDLCarga.APLICADA:
        cuando = (f" el {carga.aplicado_at:%Y-%m-%d}" if carga.aplicado_at else "")
        return f"La carga {carga.id} ya se aplicó{cuando}: solo se opera sobre un borrador."
    return f"La carga {carga.id} se descartó: solo se opera sobre un borrador."


def _motivo_obsoleta(otra):
    return (f"Se aplicó la carga {otra.id} después de que ésta se previsualizó: "
            f"lo que muestra ya no describe el estado actual del Plan. Vuelva a "
            f"subir el archivo para comparar contra lo que hay hoy.")


def _puede_aplicar(carga, request, ultima_aplicada=None, escritura=None):
    """`(bool, motivo)`. Mezcla permiso Y estado a propósito.

    Si la pantalla tuviera que componer `estado === 'borrador' && !cargando() &&
    tienePermiso()`, esa expresión sería una máquina de estados escrita dos
    veces —Python y TypeScript— que envejece de a una mitad. Con un booleano y
    una frase, el componente hace `[disabled]="!c.puede_aplicar"` y muestra el
    motivo al lado en vez de dejar un botón gris y mudo.
    """
    if carga.estado != MatrizPDLCarga.BORRADOR:
        return False, _motivo_no_borrador(carga)
    if carga.diff is None:
        return False, ("Esta carga no tiene los cambios calculados. Descártela y "
                       "vuelva a subir el archivo.")
    escribe, motivo = escritura if escritura is not None else _puede_escribir(request)
    if not escribe:
        return False, motivo
    otra = _aplicada_despues(carga, ultima_aplicada if ultima_aplicada is not None
                             else _ultima_aplicada())
    if otra is not None:
        return False, _motivo_obsoleta(otra)
    return True, None


def _puede_descartar(carga, request, escritura=None):
    if carga.estado != MatrizPDLCarga.BORRADOR:
        return False, _motivo_no_borrador(carga)
    return escritura if escritura is not None else _puede_escribir(request)


# ─────────────────────────────────────────────────────────────────────
# Presentación del diff
# ─────────────────────────────────────────────────────────────────────

def _estado_revision(diff):
    """`'con_cambios' | 'sin_cambios' | 'sin_calcular'`.

    `MatrizPDLCarga.sin_cambios` devuelve None cuando todavía no hay diff, True
    cuando el catálogo quedó igual y False cuando hay cambios — tres estados
    escritos así a propósito. Pero en Angular `!carga.sin_cambios` trata el
    None como «sí hay cambios», que es exactamente el bug que esa propiedad
    quiso evitar. Un string de tres valores no tiene forma de colapsar a dos
    por accidente; un booleano nullable sí.

    Y que no haya cambios NO es un error: es la respuesta correcta cuando la
    ALK reguarda el Excel sin tocar el catálogo.
    """
    if not diff:
        return "sin_calcular"
    return "sin_cambios" if not any(_resumen(diff).values()) else "con_cambios"


def _resumen(diff):
    """Los CUATRO conteos por clase, cada uno por separado.

    No es `_contar` del servicio y no tiene por qué serlo: aquella función
    guarda las columnas del modelo y suma las reactivaciones DENTRO de
    `n_cambios` (decisión suya, con su comentario). Acá la pantalla tiene
    cuatro tiles —Salen, Entran, Se corrigen, Vuelven— y mostrar las
    reactivaciones sumadas en «cambios» y otra vez en su propio tile las
    contaría dos veces en la misma fila. Los dos juegos de números viajan en el
    payload y van rotulados distinto: `resumen` acá, `n_altas/n_cambios/
    n_retiros` en la carga.
    """
    def suma(clase):
        return sum(len((diff.get(e) or {}).get(clase) or [])
                   for e in ("sector", "objetivo", "programa"))
    # `reactivaciones` se lee con `.get(clase, [])` —igual que hace `aplicar`—
    # porque un diff registrado antes podría no traerla; `altas`, `cambios` y
    # `retiros` sí están garantizadas en las tres entidades.
    return {"altas": suma("altas"), "cambios": suma("cambios"),
            "reactivaciones": suma("reactivaciones"), "retiros": suma("retiros")}


def _mapas_de_nombres(diff):
    """`{entidad: {codigo: nombre}}` para traducir los códigos del diff.

    Hace falta porque el diff trae códigos pelados donde la persona lee
    nombres: `reactivaciones` de objetivo y programa son enteros sueltos, y en
    un cambio de programa el campo `objetivo` tiene `de`/`a` como CÓDIGOS. Sin
    esto la pantalla mostraría «de 2 a 5», que no le dice nada a nadie.

    Se resuelve en el servidor y no en Angular porque los nombres están en la
    base, no en el payload, y una segunda llamada desde el cliente para adornar
    una lista sería peor. Salvedad honesta: el nombre que se muestra es el de
    HOY, no el que tenía cuando se calculó el diff — que para una reactivación
    es justamente lo correcto.
    """
    objetivos = {o.codigo: o.nombre for o in ObjetivoEstrategico.objects.all()}
    programas = {p.codigo: p.nombre for p in ProgramaPDL.objects.all()}
    # Un programa puede colgar de un objetivo que crea ESTA MISMA carga, y
    # entonces todavía no está en la base: si no se suman las altas del diff,
    # el destino saldría como un número pelado justo en el caso en que más hace
    # falta leer el nombre.
    for alta in ((diff.get("objetivo") or {}).get("altas") or []):
        objetivos.setdefault(alta["codigo"], alta["nombre"])
    for alta in ((diff.get("programa") or {}).get("altas") or []):
        programas.setdefault(alta["codigo"], alta["nombre"])
    return {"objetivo": objetivos, "programa": programas}


def _rotulo(codigo, nombre):
    return f"{codigo} · {nombre}" if nombre else str(codigo)


def _renglon(entidad, clase, codigo, titulo, campos=None, contexto=None):
    return {"entidad": entidad, "entidad_label": ETIQUETA_ENTIDAD[entidad],
            "clase": clase, "codigo": codigo, "titulo": titulo,
            "campos": campos or [], "contexto": contexto}


def _a_renglones(diff):
    """El diff como UNA lista plana que la plantilla recorre con un solo `@for`.

    Existe porque el diff tiene tres formas distintas para la misma idea, y
    dejarlas para que las resuelva la plantilla serían cuatro ramas con
    `$any()` que se rompen la primera vez que alguien las toque:

      · **sector** no tiene código —es un string suelto— y su lista `cambios`
        está SIEMPRE vacía, porque la llave del sector es su nombre
        normalizado. Un sector renombrado sale como un alta MÁS un retiro, no
        como un cambio (por eso el aviso `sector_renombre`).
      · **objetivo** trae el cambio PLANO: `{codigo, de, a}`, solo el nombre.
      · **programa** lo trae ANIDADO bajo `campos`, con uno o dos campos, y en
        `objetivo` los `de`/`a` son códigos enteros.
      · las **reactivaciones** de objetivo y programa son enteros pelados, sin
        nombre; los **retiros** de sector son strings y los de objetivo y
        programa son objetos.

    No recalcula nada —el diff crudo sigue viajando aparte—: reordena y
    resuelve nombres. El orden es por CLASE y después por entidad, que es como
    se lee la pantalla («Salen del Plan: un sector y dos programas»).
    """
    mapas = _mapas_de_nombres(diff)
    renglones = []
    for clase in ORDEN_CLASES:
        for entidad in ("sector", "objetivo", "programa"):
            for fila in ((diff.get(entidad) or {}).get(clase) or []):
                renglones.append(_renglon_de(entidad, clase, fila, mapas))
    return renglones


def _renglon_de(entidad, clase, fila, mapas):
    if entidad == "sector":
        # altas, reactivaciones y retiros son el nombre oficial, a secas.
        return _renglon(entidad, clase, None, str(fila))

    if clase == "reactivaciones":
        # Entero pelado: el nombre sale del catálogo (la fila existe, está
        # inactiva). No se inventa nada si no aparece.
        nombre = mapas[entidad].get(fila)
        return _renglon(entidad, clase, fila, _rotulo(fila, nombre),
                        contexto="Vuelve a estar activo en el Plan.")

    if clase == "altas":
        titulo = _rotulo(fila["codigo"], fila["nombre"])
        contexto = None
        if entidad == "programa":
            padre = fila.get("objetivo")
            contexto = ("Cuelga del objetivo estratégico "
                        f"{_rotulo(padre, mapas['objetivo'].get(padre))}.")
        return _renglon(entidad, clase, fila["codigo"], titulo, contexto=contexto)

    if clase == "retiros":
        return _renglon(entidad, clase, fila["codigo"],
                        _rotulo(fila["codigo"], fila["nombre"]),
                        contexto="Deja de aparecer en la matriz. No se borra: "
                                 "queda marcado como inactivo y se puede seguir "
                                 "consultando, junto con la carga que lo retiró.")

    # clase == "cambios"
    if entidad == "objetivo":
        # Forma PLANA. El título lleva el nombre que tiene HOY —el que la
        # persona conoce—; el renglón de campo muestra el antes y el después.
        return _renglon(entidad, clase, fila["codigo"],
                        _rotulo(fila["codigo"], fila["de"]),
                        campos=[{"campo": "nombre",
                                 "campo_label": ETIQUETA_CAMPO["nombre"],
                                 "de": fila["de"], "a": fila["a"]}])

    # programa: forma ANIDADA bajo `campos`.
    campos = []
    for campo, valor in (fila.get("campos") or {}).items():
        if campo == "objetivo":
            # Los `de`/`a` crudos son códigos int; acá salen resueltos a
            # «N · nombre». El diff original conserva los enteros.
            campos.append({"campo": campo,
                           "campo_label": ETIQUETA_CAMPO["objetivo"],
                           "de": _rotulo(valor["de"], mapas["objetivo"].get(valor["de"])),
                           "a": _rotulo(valor["a"], mapas["objetivo"].get(valor["a"]))})
        else:
            campos.append({"campo": campo,
                           "campo_label": ETIQUETA_CAMPO.get(campo, campo.capitalize()),
                           "de": valor["de"], "a": valor["a"]})
    # El título lleva el nombre que el programa tiene HOY. Si el cambio incluye
    # el nombre, ese dato ya viene en el propio diff (`de`) y se prefiere: es lo
    # que se le mostró a quien revisó, y no depende de una consulta que podría
    # traer otra cosa si la base se movió en el medio.
    nombre_hoy = ((fila.get("campos") or {}).get("nombre") or {}).get("de")
    return _renglon(entidad, clase, fila["codigo"],
                    _rotulo(fila["codigo"],
                            nombre_hoy or mapas["programa"].get(fila["codigo"])),
                    campos=campos)


def _plural(n, singular, plural):
    return f"{n} {singular if n == 1 else plural}"


def _avisos(diff, vigente):
    """Lo que el diff no dice solo, en frases ya redactadas.

    Van como texto y no como códigos para que Angular no tenga que traducir
    nada: son advertencias, y una advertencia que hay que interpretar dos veces
    llega tarde.
    """
    avisos = []
    for entidad, clave, plural in (("sector", "sectores", "sectores"),
                                   ("objetivo", "objetivos", "objetivos estratégicos"),
                                   ("programa", "programas", "programas")):
        retiros = len((diff.get(entidad) or {}).get("retiros") or [])
        activos = vigente.get(clave) or 0
        if (retiros >= MINIMO_RETIRO_MASIVO and activos
                and retiros / activos >= UMBRAL_RETIRO_MASIVO):
            avisos.append({
                "tipo": "retiro_masivo", "nivel": "danger",
                "texto": (f"Este archivo retira {retiros} de los {activos} "
                          f"{plural} activos. Suele ser señal de un archivo "
                          f"incompleto o de otro corte. Revise antes de aplicar.")})

    sector = diff.get("sector") or {}
    if (sector.get("altas") or []) and (sector.get("retiros") or []):
        avisos.append({
            "tipo": "sector_renombre", "nivel": "warning",
            "texto": ("Los sectores se comparan por su nombre. Si la ALK corrigió "
                      "una tilde o una palabra, aparece como uno que sale y otro "
                      "que entra — no es un duplicado.")})

    mueven = [c for c in ((diff.get("programa") or {}).get("cambios") or [])
              if "objetivo" in (c.get("campos") or {})]
    if mueven:
        avisos.append({
            "tipo": "programa_cambia_objetivo", "nivel": "info",
            "texto": (f"{_plural(len(mueven), 'programa pasa', 'programas pasan')} "
                      f"a otro objetivo estratégico. Eso es una reorganización del "
                      f"Plan, no una corrección de texto.")})
    return avisos


def _siguiente_paso(escribe, motivo_escritura, duplicado, abierto, estado_revision):
    """La frase que la pantalla obedece sin pensar, tras revisar el archivo."""
    if not escribe:
        return motivo_escritura
    if duplicado is not None:
        return duplicado["texto"]
    if abierto is not None:
        return (f"Hay una revisión sin terminar (carga {abierto['id']}, corte "
                f"{abierto['corte_oficial']}). Termínela antes de subir otra matriz.")
    if estado_revision == "sin_cambios":
        return ("El archivo no cambia el catálogo del Plan. Puede subirlo igual: "
                "queda el registro de que este corte se recibió y se revisó.")
    return "Todo listo. Al subir queda un borrador con este mismo diff."


def _frase_hecho(hecho):
    if not any(hecho.values()):
        # Un diff vacío aplicado NO es un fracaso: es lo que pasa cuando la ALK
        # reguarda el Excel sin tocar el catálogo. «Se aplicaron 0 altas, 0
        # cambios…» se lee como que algo falló, y no falló nada.
        return ("El catálogo del Plan quedó igual: no había nada que escribir. "
                "Queda el registro de que este corte se recibió y se revisó.")
    partes = [_plural(hecho["altas"], "alta", "altas"),
              _plural(hecho["cambios"], "cambio", "cambios"),
              _plural(hecho["reactivaciones"], "reactivación", "reactivaciones"),
              _plural(hecho["retiros"], "retiro", "retiros")]
    return "Se aplicaron " + ", ".join(partes[:-1]) + " y " + partes[-1] + "."


def _carga_json(carga, detalle=False, request=None, nombres=None,
                ultima_aplicada=None, escritura=None):
    """La carga como dict. `detalle=True` agrega lo pesado (el diff y su lectura).

    Mismo reparto que `_lote_json` en el cargue de jóvenes: la lista omite los
    campos grandes, el detalle y el 201 los incluyen.

    `nombres`, `ultima_aplicada` y `escritura` se pueden pasar ya resueltos: la
    lista los calcula UNA vez para las 30 filas. Si no vienen, se resuelven acá
    — que es lo correcto para el detalle, donde hay una sola carga. Importa
    sobre todo con `escritura`: el chequeo de rol lee `user.groups` y **no está
    cacheado** (a diferencia del de módulo, que va por Redis), así que dejarlo
    por fila serían 30 consultas para responder siempre lo mismo.
    """
    if nombres is None:
        nombres = _nombres_de_usuario([carga.subido_por_id, carga.aplicado_por_id])
    data = {
        "id": carga.id,
        "archivo_nombre": carga.archivo_nombre,
        "archivo_bytes": carga.archivo_bytes,
        # El hash completo, para que alguien pueda correr `sha256sum` sobre su
        # copia y cerrar la pregunta «¿subí el que era?». No es un secreto.
        "hash_sha256": carga.hash_sha256,
        "corte_oficial": (carga.corte_oficial.isoformat()
                          if carga.corte_oficial else None),
        "estado": carga.estado,
        "estado_revision": _estado_revision(carga.diff),
        "n_altas": carga.n_altas,
        "n_cambios": carga.n_cambios,
        "n_retiros": carga.n_retiros,
        "n_errores": carga.n_errores,
        "subido_por_id": carga.subido_por_id,
        "subido_por": nombres.get(carga.subido_por_id),
        "subido_at": carga.subido_at.isoformat() if carga.subido_at else None,
        "aplicado_por_id": carga.aplicado_por_id,
        "aplicado_por": nombres.get(carga.aplicado_por_id),
        "aplicado_at": carga.aplicado_at.isoformat() if carga.aplicado_at else None,
        "nota": carga.nota,
    }
    if request is not None:
        # El permiso VIAJA EN EL PAYLOAD, y no es un adorno: `GET /api/me/` ya
        # devuelve `groups`, así que Angular PODRÍA decidirlo solo — y por eso
        # justamente no se hace. Sería una segunda fuente de verdad, y el día
        # que la regla cambie la pantalla miente en una de las dos direcciones.
        escritura = escritura if escritura is not None else _puede_escribir(request)
        data["puede_aplicar"], data["puede_aplicar_motivo"] = _puede_aplicar(
            carga, request, ultima_aplicada, escritura)
        data["puede_descartar"], data["puede_descartar_motivo"] = _puede_descartar(
            carga, request, escritura)
    if detalle:
        diff = carga.diff or {}
        data["resumen"] = _resumen(diff)
        data["cambios"] = _a_renglones(diff)
        data["avisos"] = _avisos(diff, _conteos_vigentes())
        data["vigente"] = _vigente()
        data["alcance"] = ALCANCE
        data["diff"] = carga.diff
    return data
