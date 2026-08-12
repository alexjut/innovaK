"""Espejo legible de los soportes del Banco de Iniciativas en OneDrive.

## Qué es y qué NO es

**Mongo sigue siendo el sistema de registro.** `mongo_storage.guardar()`
cifra en reposo (AES-256-GCM) y es lo que protege los datos personales;
ahí viven los originales y de ahí salen las descargas autenticadas del
aplicativo. Este módulo **no lo reemplaza**: sube una copia legible a
OneDrive para que el área de Deportes pueda ver y descargar los soportes
sin entrar al aplicativo, que es el requisito operativo del Documento
Maestro (repositorio seguro + consolidado «tipo Tu Pago»).

Si OneDrive está caído, mal configurado o sin credenciales, **la
radicación no se rompe**: se registra en el log y el flujo sigue. Es el
mismo criterio que ya aplica el resto del proyecto con las evidencias en
Mongo (ver `apps/presupuesto/services/infraestructura.py::_guardar_evidencia`).
Por eso ninguna función pública de este módulo lanza excepción: devuelven
`None`/`False`/un dict con `errores`.

## Estructura de carpetas

La raíz admite **anidado con barras** (`Banco/aspirantes`), que es como el área
pidió organizarlo el 2026-08-10:

    Banco/aspirantes/<vigencia>/<NIT o documento>-<NOMBRE ORGANIZACIÓN>/
        1_soporte_legal.pdf
        2_cedula_representante.pdf
        3_rut.pdf
        4_reconocimiento_deportivo.pdf
        9_firma.pdf
        CONSOLIDADO_<nombre organización>.pdf

La carpeta se crea sola al radicar. Todo es idempotente: volver a llamar
con la misma organización reusa la carpeta y reemplaza los archivos.

## Autenticación

Client credentials (app-only) contra Microsoft Graph: la app registrada
en Entra ID pide un token con `scope=https://graph.microsoft.com/.default`
y escribe sobre un drive fijo. No hay usuario interactivo, así que **no
aplica `/me/drive`**: aunque el destino sea el OneDrive de una persona, la app
entra sola y hay que direccionarlo por id.

Credenciales **solo por variables de entorno** (este repo es público):

    ONEDRIVE_TENANT_ID       obligatoria
    ONEDRIVE_CLIENT_ID       obligatoria
    ONEDRIVE_CLIENT_SECRET   obligatoria (caduca: anotar la fecha)
    ONEDRIVE_DRIVE_ID        \ una de las dos basta. Con el correo, el id del
    ONEDRIVE_USUARIO         / drive se resuelve solo (ver `drive_id()`).
    ONEDRIVE_CARPETA_RAIZ    opcional (default `Banco/aspirantes`)

Sin ellas el servicio queda **inactivo** y lo dice en el log una sola vez.

**Sobre el permiso que hay que pedirle a TI.** Si el destino es el OneDrive
personal de una cuenta, el permiso de aplicación es `Files.ReadWrite.All`, que
alcanza **todos** los OneDrive del tenant — una administración suele negarlo, y
con razón. Una biblioteca de SharePoint permite `Sites.Selected`, acotado a ese
único sitio, y este módulo funciona igual: solo cambia el id del drive.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from typing import Optional, Sequence

import requests
from django.conf import settings

from .pdf_consolidado import Anexo, consolidar

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
LOGIN_BASE = "https://login.microsoftonline.com"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"

TIMEOUT_S = 30
# Subida simple (PUT .../content). Los soportes del Banco están topados en
# settings.DOCUMENTOS_MAX_UPLOAD_BYTES (2 MB); por encima de 4 MB Graph
# exige sesión de carga por partes, que no se implementa aquí a propósito.
MAX_BYTES_SUBIDA = 4 * 1024 * 1024

# Nombres canónicos de los anexos dentro de la carpeta de la organización.
# La clave es la que usa el formulario/modelo; el valor es el archivo en
# OneDrive. El prefijo numérico fija el orden de lectura del área.
NOMBRES_ANEXOS = {
    "soporte_legal": "1_soporte_legal.pdf",
    "cedula_representante": "2_cedula_representante.pdf",
    "rut": "3_rut.pdf",
    "reconocimiento_deportivo": "4_reconocimiento_deportivo.pdf",
    "residencia_representante": "5_residencia_representante.pdf",
    # Soportes del Bloque 1 (Documento Guía). El prefijo `B1_` los agrupa
    # después de los de identidad y antes de la firma, que cierra.
    "staff_listado": "B1_31_listado_staff.pdf",
    "trayectoria": "B1_32_trayectoria.pdf",
    "composicion_genero": "B1_33_composicion_genero.pdf",
    "beneficiarios_listado": "B1_34_beneficiarios.pdf",
    "arraigo_uso_espacio": "B1_42_uso_espacio_y_estrato.pdf",
    "caracterizacion_demografica": "B1_51_caracterizacion_demografica.pdf",
    "instancias_actas": "B1_61_instancias.pdf",
    "declaracion_antecedentes": "B1_62_declaracion_antecedentes.pdf",
    "firma": "9_firma.pdf",
}

# Orden de aparición en el PDF consolidado y títulos legibles para su portada.
ORDEN_ANEXOS = (
    ("soporte_legal", "Soporte legal de la organización"),
    ("cedula_representante", "Documento de identidad del representante legal"),
    ("rut", "Registro Único Tributario (RUT)"),
    ("reconocimiento_deportivo", "Reconocimiento deportivo / aval sectorial"),
    ("residencia_representante", "Certificado de residencia del representante"),
    ("staff_listado", "§3.1 Listado del staff con firmas"),
    ("trayectoria", "§3.2 Certificaciones de trayectoria comunitaria"),
    ("composicion_genero", "§3.3 Conformación de género de la organización"),
    ("beneficiarios_listado", "§3.4 Listado de beneficiarios atendidos"),
    ("arraigo_uso_espacio", "§4.2 Autorización de uso del escenario y estrato"),
    ("caracterizacion_demografica", "§5.1 Caracterización demográfica"),
    ("instancias_actas", "§6.1 Participación en instancias locales"),
    ("declaracion_antecedentes", "§6.2 Declaración de antecedentes con la ALK"),
    ("firma", "Firma del representante legal"),
)

# Caracteres que OneDrive/SharePoint no admiten en nombres de ítem.
_PROHIBIDOS = re.compile(r'[\\/:*?"<>|#%{}~&]')

#: Estructura pedida por el área (2026-08-10): `Banco / aspirantes / <año> /
#: <NIT>-<ORGANIZACIÓN>/`. La barra anida carpetas; ver `segmentos_raiz()`.
CARPETA_RAIZ_DEFAULT = "Banco/aspirantes"

_drive_cache: dict = {"id": None}
_token_cache: dict = {"valor": None, "expira": 0.0}
_token_lock = threading.Lock()
_aviso_inactivo_emitido = False


# ─────────────────────────── configuración ───────────────────────────

def _cfg(nombre: str, default: str = "") -> str:
    return (getattr(settings, nombre, default) or "").strip()


def carpeta_raiz() -> str:
    return _cfg("ONEDRIVE_CARPETA_RAIZ", CARPETA_RAIZ_DEFAULT) or CARPETA_RAIZ_DEFAULT


def segmentos_raiz() -> list[str]:
    """La raíz partida en carpetas: `"Banco/aspirantes"` → `["Banco", "aspirantes"]`.

    Antes la raíz era UN solo nombre de carpeta, así que una barra se
    convertía en guion bajo (`_PROHIBIDOS`) y `Banco/aspirantes` terminaba
    creando una única carpeta llamada «Banco_aspirantes». Se admite el anidado
    porque es como el área pidió organizarlo: `Banco / aspirantes / …`.
    """
    return [sanear_nombre(p) for p in carpeta_raiz().split("/") if p.strip()]


def activo() -> bool:
    """True si hay credenciales completas. No hace red.

    El destino se puede dar de dos formas y basta con UNA: `ONEDRIVE_DRIVE_ID`
    (el GUID del drive) o `ONEDRIVE_USUARIO` (el correo cuyo OneDrive recibe
    los soportes). La segunda existe porque conseguir el GUID obliga a entrar a
    Graph Explorer, mientras que el correo ya se conoce; con él, el id se
    resuelve solo la primera vez y se cachea.
    """
    global _aviso_inactivo_emitido
    faltantes = [
        k for k in ("ONEDRIVE_TENANT_ID", "ONEDRIVE_CLIENT_ID",
                    "ONEDRIVE_CLIENT_SECRET")
        if not _cfg(k)
    ]
    if not _cfg("ONEDRIVE_DRIVE_ID") and not _cfg("ONEDRIVE_USUARIO"):
        faltantes.append("ONEDRIVE_DRIVE_ID (o ONEDRIVE_USUARIO)")
    if faltantes:
        if not _aviso_inactivo_emitido:
            logger.info(
                "onedrive_inactivo faltan=%s "
                "detalle=\"espejo deshabilitado; Mongo sigue guardando los originales\"",
                ",".join(faltantes),
            )
            _aviso_inactivo_emitido = True
        return False
    return True


def reiniciar_token() -> None:
    """Olvida el token y el drive cacheados (tests y rotación de secreto)."""
    with _token_lock:
        _token_cache["valor"] = None
        _token_cache["expira"] = 0.0
        _drive_cache["id"] = None


def drive_id() -> Optional[str]:
    """El drive destino: el configurado, o el del usuario de `ONEDRIVE_USUARIO`.

    Resolver por correo cuesta una llamada a Graph (`/users/<correo>/drive`) y
    se cachea en memoria. Devuelve None si no se pudo — nunca lanza, como todo
    en este módulo.
    """
    fijo = _cfg("ONEDRIVE_DRIVE_ID")
    if fijo:
        return fijo
    if _drive_cache["id"]:
        return _drive_cache["id"]

    usuario = _cfg("ONEDRIVE_USUARIO")
    if not usuario:
        return None
    token = _token()
    if not token:
        return None
    from urllib.parse import quote
    try:
        r = requests.get(
            f"{GRAPH_BASE}/users/{quote(usuario)}/drive",
            headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT_S)
        if r.status_code != 200:
            logger.warning("onedrive_drive_no_resuelto status=%s usuario=%s",
                           r.status_code, usuario)
            return None
        encontrado = (r.json() or {}).get("id")
    except Exception as exc:  # noqa: BLE001
        logger.warning("onedrive_drive_error error=%s", type(exc).__name__)
        return None
    if encontrado:
        _drive_cache["id"] = encontrado
    return encontrado


# ───────────────────────────── nombres ───────────────────────────────

def sanear_nombre(nombre: str, max_len: int = 120) -> str:
    """Deja un nombre válido para OneDrive (sin caracteres prohibidos)."""
    limpio = _PROHIBIDOS.sub(" ", str(nombre or ""))
    limpio = re.sub(r"\s+", " ", limpio).strip(" .")
    return limpio[:max_len].strip(" .")


def nombre_carpeta_organizacion(identificacion: str, nombre_organizacion: str) -> str:
    """`<NIT o documento>-<NOMBRE DE LA ORGANIZACIÓN>`.

    Si no hay identificación (colectivo informal sin NIT), la carpeta queda
    solo con el nombre — nunca con un guion suelto que confunda al área.
    """
    ident = sanear_nombre(identificacion, 40)
    nombre = sanear_nombre(nombre_organizacion, 100).upper()
    if ident and nombre:
        return f"{ident}-{nombre}"
    return ident or nombre or "SIN IDENTIFICAR"


def nombre_consolidado(nombre_organizacion: str) -> str:
    return f"CONSOLIDADO_{sanear_nombre(nombre_organizacion, 100)}.pdf"


def ruta_organizacion(vigencia, identificacion: str, nombre_organizacion: str) -> list[str]:
    """Segmentos de la carpeta destino, desde la raíz configurada."""
    return [
        *segmentos_raiz(),
        sanear_nombre(str(vigencia), 20),
        nombre_carpeta_organizacion(identificacion, nombre_organizacion),
    ]


def _ruta_texto(partes: Sequence[str]) -> str:
    return "/".join(p for p in partes if p)


def _url_por_ruta(partes: Sequence[str], sufijo: str = "") -> str:
    """URL de Graph direccionada por ruta.

    Sin sufijo:  `/drives/{id}/root:/a/b`            (metadatos del ítem)
    Con sufijo:  `/drives/{id}/root:/a/b:/children`  (sufijo = '/children')
    """
    from urllib.parse import quote

    drive = drive_id() or ""
    ruta = "/".join(quote(p, safe="") for p in partes if p)
    if not ruta:
        return f"{GRAPH_BASE}/drives/{drive}/root"
    return f"{GRAPH_BASE}/drives/{drive}/root:/{ruta}:{sufijo}" if sufijo \
        else f"{GRAPH_BASE}/drives/{drive}/root:/{ruta}"


# ────────────────────────────── token ────────────────────────────────

def _token() -> Optional[str]:
    """Token app-only, cacheado en memoria hasta 60 s antes de expirar."""
    if not activo():
        return None
    ahora = time.time()
    with _token_lock:
        if _token_cache["valor"] and _token_cache["expira"] > ahora:
            return _token_cache["valor"]
        url = f"{LOGIN_BASE}/{_cfg('ONEDRIVE_TENANT_ID')}/oauth2/v2.0/token"
        datos = {
            "grant_type": "client_credentials",
            "client_id": _cfg("ONEDRIVE_CLIENT_ID"),
            "client_secret": _cfg("ONEDRIVE_CLIENT_SECRET"),
            "scope": GRAPH_SCOPE,
        }
        try:
            r = requests.post(url, data=datos, timeout=TIMEOUT_S)
            if r.status_code != 200:
                # NUNCA se loguea el cuerpo: puede repetir el client_secret.
                logger.warning("onedrive_token_falla status=%s", r.status_code)
                return None
            payload = r.json()
        except Exception as exc:
            logger.warning("onedrive_token_error error=%s", type(exc).__name__)
            return None

        token = payload.get("access_token")
        if not token:
            logger.warning("onedrive_token_sin_access_token")
            return None
        _token_cache["valor"] = token
        _token_cache["expira"] = ahora + max(int(payload.get("expires_in", 3600)) - 60, 60)
        return token


def _headers(extra: Optional[dict] = None) -> Optional[dict]:
    token = _token()
    if not token:
        return None
    cabeceras = {"Authorization": f"Bearer {token}"}
    if extra:
        cabeceras.update(extra)
    return cabeceras


# ──────────────────────────── operaciones ────────────────────────────

def _obtener_item(partes: Sequence[str]) -> Optional[dict]:
    """Metadatos del ítem en esa ruta, o None si no existe / falla."""
    cabeceras = _headers()
    if cabeceras is None:
        return None
    try:
        r = requests.get(_url_por_ruta(partes), headers=cabeceras, timeout=TIMEOUT_S)
    except Exception as exc:
        logger.warning("onedrive_get_error ruta=%r error=%s", _ruta_texto(partes), type(exc).__name__)
        return None
    if r.status_code == 200:
        return r.json()
    if r.status_code != 404:
        logger.warning("onedrive_get_status ruta=%r status=%s",
                       _ruta_texto(partes), r.status_code)
    return None


def _crear_subcarpeta(padre: Sequence[str], nombre: str) -> Optional[dict]:
    """Crea `nombre` dentro de `padre`. Si ya existe, devuelve la existente."""
    cabeceras = _headers({"Content-Type": "application/json"})
    if cabeceras is None:
        return None
    url = _url_por_ruta(padre, "/children") if padre else \
        f"{GRAPH_BASE}/drives/{drive_id() or ''}/root/children"
    cuerpo = {
        "name": nombre,
        "folder": {},
        # 'fail' + relectura: 'replace' borraría el contenido ya subido.
        "@microsoft.graph.conflictBehavior": "fail",
    }
    try:
        r = requests.post(url, json=cuerpo, headers=cabeceras, timeout=TIMEOUT_S)
    except Exception as exc:
        logger.warning("onedrive_mkdir_error nombre=%r error=%s", nombre, type(exc).__name__)
        return None
    if r.status_code in (200, 201):
        return r.json()
    if r.status_code == 409:  # carrera con otra radicación simultánea
        return _obtener_item(list(padre) + [nombre])
    logger.warning("onedrive_mkdir_status nombre=%r status=%s", nombre, r.status_code)
    return None


def asegurar_carpeta(partes: Sequence[str]) -> Optional[str]:
    """Crea la ruta completa si hace falta y devuelve el `id` de la hoja.

    Idempotente: si ya existe no toca nada. Devuelve None si el servicio
    está inactivo o Graph falló (nunca lanza).
    """
    partes = [p for p in (partes or []) if p]
    if not partes:
        return None
    if not activo():
        return None

    existente = _obtener_item(partes)
    if existente and "folder" in existente:
        return existente.get("id")

    item = None
    for i, nombre in enumerate(partes):
        actual = partes[: i + 1]
        item = _obtener_item(actual)
        if item is None:
            item = _crear_subcarpeta(partes[:i], nombre)
        if item is None:
            logger.warning("onedrive_carpeta_no_creada ruta=%r", _ruta_texto(actual))
            return None
    logger.info("onedrive_carpeta_ok ruta=%r", _ruta_texto(partes))
    return (item or {}).get("id")


def subir_archivo(
    partes: Sequence[str],
    nombre_archivo: str,
    contenido: bytes,
    mime: str = "application/octet-stream",
) -> Optional[dict]:
    """Sube (o reemplaza) un archivo dentro de `partes`.

    Devuelve el ítem de Graph (`id`, `name`, `webUrl`, ...) o None si no se
    pudo. Idempotente: reemplaza el archivo del mismo nombre, de modo que
    re-radicar no deja duplicados.
    """
    if not activo():
        return None
    if not contenido:
        logger.info("onedrive_subida_vacia archivo=%r", nombre_archivo)
        return None
    if len(contenido) > MAX_BYTES_SUBIDA:
        logger.warning("onedrive_archivo_muy_grande archivo=%r bytes=%d",
                       nombre_archivo, len(contenido))
        return None

    nombre_archivo = sanear_nombre(nombre_archivo, 128)
    if asegurar_carpeta(partes) is None:
        return None

    cabeceras = _headers({"Content-Type": mime or "application/octet-stream"})
    if cabeceras is None:
        return None

    url = _url_por_ruta(list(partes) + [nombre_archivo],
                        "/content?@microsoft.graph.conflictBehavior=replace")
    try:
        r = requests.put(url, data=contenido, headers=cabeceras, timeout=TIMEOUT_S)
    except Exception as exc:
        logger.warning("onedrive_subida_error archivo=%r error=%s",
                       nombre_archivo, type(exc).__name__)
        return None
    if r.status_code not in (200, 201):
        logger.warning("onedrive_subida_status archivo=%r status=%s",
                       nombre_archivo, r.status_code)
        return None

    try:
        item = r.json()
    except Exception:
        item = {"name": nombre_archivo}
    logger.info("onedrive_subida_ok ruta=%r archivo=%r bytes=%d",
                _ruta_texto(partes), nombre_archivo, len(contenido))
    return item


def ping() -> bool:
    """Verifica credenciales + alcance del drive. Para healthcheck."""
    if not activo():
        return False
    cabeceras = _headers()
    if cabeceras is None:
        return False
    try:
        r = requests.get(f"{GRAPH_BASE}/drives/{drive_id() or ''}",
                         headers=cabeceras, timeout=TIMEOUT_S)
        return r.status_code == 200
    except Exception:
        return False


# ───────────────────────── orquestación ──────────────────────────────

def construir_consolidado(anexos: dict, *, nombre_organizacion: str,
                          subtitulos: Sequence[str] = ()) -> Optional[bytes]:
    """PDF único con todos los anexos, en el orden oficial del documento.

    `anexos` es `{clave: (contenido_bytes, mime)}` con las claves de
    `NOMBRES_ANEXOS`. Las claves desconocidas se anexan al final para no
    perder soportes complementarios.
    """
    lista: list[Anexo] = []
    usadas = set()
    for clave, titulo in ORDEN_ANEXOS:
        dato = (anexos or {}).get(clave)
        if not dato:
            continue
        contenido, mime = _desempacar(dato)
        if contenido:
            lista.append(Anexo(titulo, contenido, mime))
            usadas.add(clave)
    for clave, dato in (anexos or {}).items():
        if clave in usadas or not dato:
            continue
        contenido, mime = _desempacar(dato)
        if contenido:
            lista.append(Anexo(str(clave).replace("_", " ").capitalize(), contenido, mime))

    return consolidar(
        lista,
        titulo=f"Banco de Iniciativas · {nombre_organizacion}",
        subtitulos=subtitulos,
    )


def _desempacar(dato) -> tuple[Optional[bytes], str]:
    """Acepta `bytes` o `(bytes, mime)`."""
    if isinstance(dato, (bytes, bytearray)):
        return bytes(dato), "application/pdf"
    try:
        contenido, mime = dato
    except Exception:
        return None, "application/pdf"
    if not isinstance(contenido, (bytes, bytearray)):
        return None, "application/pdf"
    return bytes(contenido), (mime or "application/pdf")


def espejar_soportes(
    *,
    vigencia,
    identificacion: str,
    nombre_organizacion: str,
    anexos: dict,
    subtitulos: Sequence[str] = (),
    incluir_consolidado: bool = True,
) -> dict:
    """Sube los soportes + el consolidado a la carpeta de la organización.

    **Best-effort por diseño**: nunca lanza. El llamador (la radicación)
    puede ignorar el resultado; sirve para log/auditoría.

    Devuelve:
        {"activo": bool, "carpeta": "...", "subidos": [...],
         "errores": [...], "consolidado": "CONSOLIDADO_x.pdf" | None}
    """
    reporte = {"activo": False, "carpeta": None, "subidos": [],
               "errores": [], "consolidado": None}
    try:
        partes = ruta_organizacion(vigencia, identificacion, nombre_organizacion)
        reporte["carpeta"] = _ruta_texto(partes)

        if not activo():
            reporte["errores"].append("servicio_inactivo")
            return reporte
        reporte["activo"] = True

        if asegurar_carpeta(partes) is None:
            reporte["errores"].append("carpeta_no_creada")
            return reporte

        for clave, (contenido, mime) in (
            (k, _desempacar(v)) for k, v in (anexos or {}).items()
        ):
            if not contenido:
                continue
            nombre = NOMBRES_ANEXOS.get(clave) or f"{sanear_nombre(clave, 60)}.pdf"
            if subir_archivo(partes, nombre, contenido, mime):
                reporte["subidos"].append(nombre)
            else:
                reporte["errores"].append(nombre)

        if incluir_consolidado:
            pdf = construir_consolidado(
                anexos, nombre_organizacion=nombre_organizacion, subtitulos=subtitulos)
            if pdf:
                nombre = nombre_consolidado(nombre_organizacion)
                if subir_archivo(partes, nombre, pdf, "application/pdf"):
                    reporte["consolidado"] = nombre
                    reporte["subidos"].append(nombre)
                else:
                    reporte["errores"].append(nombre)
    except Exception as exc:
        # Blindaje final: la radicación NO se cae por el espejo.
        logger.warning("onedrive_espejo_error error=%s detalle=%s",
                       type(exc).__name__, exc)
        reporte["errores"].append("excepcion_inesperada")
    return reporte
