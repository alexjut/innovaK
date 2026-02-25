#SSH beto@0.tcp.ngrok.io -p 12929
# password: beto2025.
#mongosh -u innovacion_kennedy -p '' --authenticationDatabase gestion_contratos
#use gestion_contratos

# contratacion/utils/mongo_conexion.py
# -- coding: utf-8 --
from pymongo import MongoClient, errors
import gridfs, logging, os
from datetime import datetime
import unicodedata, re
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================
#  Catálogos por grupo
# =============================
TIPOS_DOCUMENTOS_SIPSE = [
    "Hoja de vida en formato personal", "Memorando SIPSE", "SIPSE - CDP",
    "Estudio Previo SIPSE", "No Hay SIPSE", "ARL",
]

TIPOS_DOCUMENTOS_CONTRATISTA = [
    "Hoja de vida en formato personal", "Cédula de ciudadanía", "Tarjeta Militar",
    "Registro Único Tributario – RUT", "Resolución de facturación",
    "Registro de Información Tributaria - RIT",
    "Formato de Autorización consulta inhabilidades por delitos sexuales",
    "Consulta inhabilidades por delitos sexuales expedido por la Policía Nacional",
    "Certificado de Antecedentes Judiciales expedido por la Policía Nacional",
    "Registro Nacional de Medidas Correctivas – RNMC, expedido por la Policía Nacional",
    "Certificado de Antecedentes Disciplinarios, expedido por la Personería",
    "Certificado de Antecedentes Disciplinarios, expedido por la Procuraduría",
    "Certificado de Antecedentes Fiscales, expedido por la Contraloría",
    "Consulta en el Registro de Deudores Alimentarios Morosos (REDAM)",
    "Título de Bachiller y título Técnico o Profesional", "Título de Posgrado",
    "Certificaciones de experiencia laboral y/o profesional", "Tarjeta Profesional (cuando aplique)",
    "Certificado de vigencia y antecedentes disciplinarios de la profesión (cuando apllique)",
    "Certificación de afiliación al Sistema General de Seguridad Social en Salud",
    "Certificación de afiliación al Sistema General de Seguridad Social en Pensiones",
    "Certificación bancaria", "Hoja de Vida SIDEAP",
    "Declaración de Bienes y Rentas (versión SIDEAP)",
    "Declaración de Conflictos de Interés (versión SIDEAP)",
    "Ley 2013 – Declaraciones de bienes, conflictos e impuesto sobre la renta",
    "Certificado Médico Ocupacional", "Solicitud Afiliación ARL",
    "Relación de Contratos de Prestación de Servicios vigentes con otras Entidades Estatales",
    "Pantallazo perfil de usuario SECOP II", "Acuerdo de Confidencialidad",
    "Póliza",
]

# Documentos para inscripción cursos
TIPOS_DOCUMENTOS_CURSOS = [
    "Documento de Identidad",
    "Certificado Afiliacion EPS",
    "Certificado de Residencia o recibo publico",
    "Formato de Consentimiento informado",
    "Encuesta estado de salud firmado",
    "Documento Habeas Data",
]

# Documentos para seguimiento de operadores
TIPOS_DOCUMENTOS_OPERADORES = [
    "Acta de inicio",
    "Cédula representante legal",
    "Cámara de comercio",
    "Contrato",
    "Estudios técnicos: financiero, mercado y tecnico",
    "Estudios previos",
    "Actas de comité de contratación",
    "Actas de Ingresos de almacén",
    "Cronograma",
    "Otros (debates de control político ante la JAL, quejas escritas, derechos de petición, etc)",
    "Informes de ejecución",
    "Informe entrega final",
]

# =============================
#  Lista MAESTRA unificada (unificacion de todos los tipos)
# =============================
def _uniq(seq):
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

TIPOS_DOCUMENTOS = _uniq(
    TIPOS_DOCUMENTOS_SIPSE
    + TIPOS_DOCUMENTOS_CONTRATISTA
    + TIPOS_DOCUMENTOS_CURSOS
    + TIPOS_DOCUMENTOS_OPERADORES
    
)

# Choices para Django (forms/models)
DOC_TIPO_CHOICES = [(t, t) for t in TIPOS_DOCUMENTOS]

# =============================
#  Aliases para normalizar entradas comunes
# =============================
ALIASES_TIPOS = {
    # Contratista
    "rut": "Registro Único Tributario – RUT",
    "r.u.t": "Registro Único Tributario – RUT",
    "rit": "Registro de Información Tributaria - RIT",
    "r.i.t": "Registro de Información Tributaria - RIT",
    "poliza": "Póliza",
    "hoja de vida": "Hoja de vida en formato personal",
    "sipse cdp": "SIPSE - CDP",
    "estudio previo": "Estudio Previo SIPSE",

    # Cursos
    "documento identidad": "Documento de Identidad",
    "certificado eps": "Certificado Afiliacion EPS",
    "recibo publico": "Certificado de Residencia o recibo publico",
    "consentimiento informado": "Formato de Consentimiento informado",
    "encuesta salud": "Encuesta estado de salud firmado",
    "habeas data": "Documento Habeas Data",

    # Operadores
    "cedula representante legal": "Cédula representante legal",
    "camara comercio": "Cámara de comercio",
    "acta inicio": "Acta de inicio",
    "estudios tecnicos": "Estudios técnicos: financiero, mercado y tecnico",
    "actas comite contratacion": "Actas de comité de contratación",
    "ingresos almacen": "Actas de Ingresos de almacén",
}

# =============================
#  Normalización / Validación
# =============================
def _strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")

def normalizar_tipo(tipo: str) -> str:
    """
    Devuelve una etiqueta del catálogo:
    - quita tildes → minúsculas → colapsa espacios
    - aplica ALIASES si coincide (retorna la etiqueta canónica)
    - si no hay alias, devuelve la cadena original (para conservar mayúsculas/acentos)
    """
    if not tipo:
        return ""
    base = _strip_accents(tipo).lower().strip()
    base = re.sub(r"\s+", " ", base)
    if base in ALIASES_TIPOS:
        return ALIASES_TIPOS[base]
    return tipo

def tipo_valido(tipo: str) -> bool:
    """Valida contra la lista maestra (acepta original o alias normalizado)."""
    t_norm = normalizar_tipo(tipo)
    return t_norm in TIPOS_DOCUMENTOS or tipo in TIPOS_DOCUMENTOS

def limpiar_nombre_archivo(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"[^A-Za-z0-9.-]+", "", s).strip("_").lower()
    return s

# =============================
#  Conexión Mongo
# =============================
MONGO_USER = os.getenv("MONGO_USER", "innovacion_kennedy")
MONGO_PASS = os.getenv("MONGO_PASS", "innovacion2025")
AUTH_DB    = os.getenv("MONGO_AUTH_DB", "admin")
DB_NAME    = os.getenv("MONGO_DB_NAME", "gestion_contratos")

HOSTS = [
    os.getenv("MONGO_HOST", "host.docker.internal:27017"),
    "192.168.0.101:27017",
    "127.0.0.1:27017",
    "172.17.0.1:27018",
]

def _build_uri(hostport: str) -> str:
    return f"mongodb://{MONGO_USER}:{MONGO_PASS}@{hostport}/?authSource={AUTH_DB}"

MONGO_CONFIGS = [
    {"name": f"Mongo @ {hp}", "uri": _build_uri(hp), "db": DB_NAME, "timeout_ms": 10000}
    for hp in HOSTS
]

def conectar_mongo():
    for cfg in MONGO_CONFIGS:
        try:
            logger.info(f"Intentando conexión: {cfg['name']}")
            cliente = MongoClient(
                cfg['uri'],
                serverSelectionTimeoutMS=cfg['timeout_ms'],
                socketTimeoutMS=cfg['timeout_ms'],
                connectTimeoutMS=cfg['timeout_ms'],
            )
            cliente.admin.command("ping")
            logger.info(f"✅ Conexión exitosa usando: {cfg['name']} (db={cfg['db']})")
            return cliente, cfg['db']
        except errors.ServerSelectionTimeoutError as e:
            logger.warning(f"❌ Timeout en {cfg['name']}: {e}")
        except errors.OperationFailure as e:
            logger.warning(f"❌ Error de autenticación en {cfg['name']}: {e}")
        except Exception as e:
            logger.warning(f"❌ Error en {cfg['name']}: {e}")
    logger.error("❌ No se pudo establecer conexión MongoDB con ninguna configuración")
    return None, None

def obtener_db_y_fs(collection: str = "docs"):
    try:
        cliente, db_name = conectar_mongo()
        if not cliente:
            return None
        db = cliente.get_database(db_name or DB_NAME)
        fs = gridfs.GridFS(db, collection=collection)
        return db, fs, cliente
    except Exception as e:
        logger.exception(f"❌ Error al inicializar GridFS: {e}")
        return None

def obtener_fs_simple(collection: str = "docs"):
    res = obtener_db_y_fs(collection=collection)
    if res:
        _, fs, _ = res
        return fs
    return None

# =============================
#  Helper de subida
# =============================
def subir_a_gridfs(ruta_archivo: str, tipo_documento: str, persona_id, habeas: bool = True, collection: str = "docs"):
    """
    Sube un archivo a GridFS validando el tipo (lista maestra) y agregando metadatos.
    Retorna el ObjectId del archivo.
    """
    if not tipo_valido(tipo_documento):
        raise ValueError(f"Tipo de documento no válido: {tipo_documento}")

    res = obtener_db_y_fs(collection=collection)
    if not res:
        raise RuntimeError("No fue posible conectar a Mongo/GridFS")

    db, fs, cliente = res
    p = Path(ruta_archivo)
    now = datetime.utcnow()

    tipo_label = tipo_documento               
    tipo_canon = normalizar_tipo(tipo_label)  

    meta = {
        "tipo_documento": tipo_canon,
        "tipo_documento_label": tipo_label,
        "persona_id": int(persona_id) if str(persona_id).isdigit() else persona_id,
        "habeas_data": bool(habeas),
        "createdAt": now,
        "updatedAt": now,
        "nombre_limpio": limpiar_nombre_archivo(p.name),
    }

    with p.open("rb") as f:
        file_id = fs.put(f, filename=p.name, chunkSize=1024*1024, metadata=meta)

    try:
        cliente.close()
    except Exception:
        pass

    return file_id