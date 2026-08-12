"""Guardado progresivo del formulario público del Banco.

El Documento Guía promete un formulario de 45 a 60 minutos con «motor de
guardado progresivo síncrono en el servidor». Hoy el flujo es todo-o-nada: una
caída de conexión a los 50 minutos borra el trabajo completo. Para una
convocatoria que reparte plata pública eso no es una molestia de usabilidad —
es una barrera de acceso que golpea más fuerte justo a quien se postula desde
un celular con datos móviles.

DÓNDE VIVE EL BORRADOR, Y POR QUÉ NO EN POSTGRES
------------------------------------------------
`inscripcion_banco_iniciativa` tiene **7 columnas NOT NULL** (evento,
organización, nombre y documento del representante, trayectoria, población
atendida…). Un borrador es, por definición, incompleto: no las puede llenar. Y
crear una tabla nueva exigiría DDL sobre una base compartida.

Va a **Mongo cifrado**, que además es el lugar correcto por otra razón: un
borrador lleva cédulas, nombres y direcciones. En Mongo queda cifrado en
reposo; en una columna JSONB quedaría en claro y saldría en cada backup.

EL TOKEN, Y POR QUÉ NO BASTA EL ID DE MONGO
-------------------------------------------
El endpoint es público (sin login): lo único que identifica al borrador es lo
que el navegador guardó. Usar el `ObjectId` pelado sería un agujero: los
ObjectId son semi-secuenciales (timestamp + contador), así que se pueden
enumerar, y cada acierto entregaría la cédula y la dirección de otra persona.

El token es `<mongo_id>.<hmac>` — mismo patrón que `qr_token.py`. Adivinar el
id no alcanza: hay que traer la firma, y esa sale de una clave del servidor.
La comparación es en tiempo constante.
"""
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone

from django.conf import settings

from apps.documentos.services import mongo_storage

log = logging.getLogger(__name__)

MIME_BORRADOR = "application/json"

#: Cuánto vive un borrador sin tocarse. La convocatoria dura semanas y el
#: formulario una hora: 30 días cubre de sobra a quien lo deja a medias y
#: vuelve, sin acumular cédulas indefinidamente en Mongo.
VIGENCIA_DIAS = 30

#: Techo del payload. Un borrador son campos de formulario, no archivos: los
#: anexos van por su propio camino. Sin tope, el endpoint público sería un
#: subidero de basura gratis.
MAX_BYTES = 512 * 1024


class BorradorInvalido(Exception):
    """El token no es válido, no corresponde al evento, o el borrador venció."""


def _clave() -> str:
    """Misma clave que los QR públicos: es el mismo dominio de confianza."""
    return getattr(settings, "QR_TOKEN_SECRET", None) or settings.SECRET_KEY


def _firma(mongo_id: str) -> str:
    mensaje = f"banco-borrador:{mongo_id}".encode()
    return hmac.new(_clave().encode(), mensaje, hashlib.sha256).hexdigest()[:20]


def _componer_token(mongo_id: str) -> str:
    return f"{mongo_id}.{_firma(mongo_id)}"


def _abrir_token(token: str) -> str:
    """Valida la firma y devuelve el `mongo_id`. Lanza `BorradorInvalido`."""
    if not token or "." not in token:
        raise BorradorInvalido("Token de borrador mal formado.")
    mongo_id, _, firma = token.partition(".")
    # compare_digest: sin esto, el tiempo de respuesta filtra cuántos
    # caracteres de la firma acertó quien esté probando.
    if not mongo_id or not hmac.compare_digest(firma, _firma(mongo_id)):
        raise BorradorInvalido("Token de borrador inválido.")
    return mongo_id


def _ahora():
    return datetime.now(timezone.utc)


def guardar(evento_id, datos: dict, token: str | None = None) -> dict:
    """Crea o actualiza el borrador. Devuelve `{token, guardado_en, expira_en}`.

    Con `token` actualiza EN SITIO y el token no cambia: el cliente lo guarda
    una vez y no tiene que aprenderse uno nuevo en cada autoguardado. Si el
    token trae firma válida pero el documento ya no existe (venció y lo purgó
    el comando de limpieza), se crea uno nuevo en vez de fallar — el ciudadano
    no tiene por qué perder lo que acaba de escribir.
    """
    if not isinstance(datos, dict):
        raise BorradorInvalido("El borrador debe ser un objeto de campos.")

    sobre = {
        "evento_id": int(evento_id),
        "guardado_en": _ahora().isoformat(),
        "expira_en": (_ahora() + timedelta(days=VIGENCIA_DIAS)).isoformat(),
        "datos": datos,
    }
    crudo = json.dumps(sobre, ensure_ascii=False).encode("utf-8")
    if len(crudo) > MAX_BYTES:
        raise BorradorInvalido(
            f"El borrador supera el máximo de {MAX_BYTES // 1024} KB. "
            f"Los archivos no van en el borrador: se adjuntan al radicar.")

    # `owner` va SIN cifrar en Mongo, así que solo lleva lo que no identifica a
    # nadie. La fecha se duplica acá para que la purga pueda filtrar en Mongo
    # sin descifrar cada borrador. La que MANDA para validar sigue siendo la de
    # adentro: alterar esta solo cambiaría cuándo se borra, nunca permitiría
    # leer un borrador vencido.
    owner = {
        "tipo": "banco_borrador",
        "evento_id": int(evento_id),
        "expira_en": sobre["expira_en"],
    }

    if token:
        mongo_id = _abrir_token(token)
        if mongo_storage.actualizar(mongo_id, crudo, MIME_BORRADOR, owner):
            return {"token": token, "guardado_en": sobre["guardado_en"],
                    "expira_en": sobre["expira_en"]}
        log.info("Borrador %s ya no existe (vencido o purgado); se crea otro.",
                 mongo_id)

    mongo_id = mongo_storage.guardar(crudo, MIME_BORRADOR, owner)
    return {"token": _componer_token(mongo_id),
            "guardado_en": sobre["guardado_en"],
            "expira_en": sobre["expira_en"]}


def leer(evento_id, token: str) -> dict:
    """Devuelve `{datos, guardado_en, expira_en}`. Lanza `BorradorInvalido`."""
    mongo_id = _abrir_token(token)
    try:
        crudo, _mime = mongo_storage.leer(mongo_id)
    except ValueError as exc:
        raise BorradorInvalido("El borrador ya no existe o venció.") from exc

    try:
        sobre = json.loads(crudo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BorradorInvalido("El borrador está corrupto.") from exc

    # Un token válido de OTRO evento no puede abrir este formulario: los
    # catálogos y las validaciones son por evento.
    if int(sobre.get("evento_id", -1)) != int(evento_id):
        raise BorradorInvalido("El borrador es de otra convocatoria.")

    if _vencido(sobre):
        raise BorradorInvalido("El borrador venció.")

    return {"datos": sobre.get("datos") or {},
            "guardado_en": sobre.get("guardado_en"),
            "expira_en": sobre.get("expira_en")}


def _vencido(sobre: dict) -> bool:
    """Vence por la fecha guardada DENTRO del sobre cifrado.

    Va adentro a propósito: si estuviera en los metadatos en claro, alargar la
    vigencia de un borrador ajeno sería editar un campo de Mongo.
    """
    marca = sobre.get("expira_en")
    if not marca:
        return False
    try:
        return datetime.fromisoformat(marca) < _ahora()
    except ValueError:
        # Fecha ilegible → se trata como VENCIDO. Un error de formato no puede
        # convertirse en un borrador inmortal con cédulas adentro.
        return True


def descartar(token: str) -> bool:
    """Borra el borrador. Se llama al radicar: ya no hay nada que retomar."""
    try:
        mongo_id = _abrir_token(token)
    except BorradorInvalido:
        return False
    return mongo_storage.borrar(mongo_id)


def purgar_vencidos(ahora=None) -> int:
    """Borra de Mongo los borradores ya vencidos. Devuelve cuántos.

    Filtra por la fecha de `owner` (en claro) para no descifrar uno por uno.
    Esa fecha es manipulable en teoría, pero el peor caso es que un borrador
    se quede almacenado de más: para LEERLO sigue mandando la de adentro.
    """
    marca = (ahora or _ahora()).isoformat()
    return mongo_storage.borrar_por_owner({
        "tipo": "banco_borrador",
        "expira_en": {"$lt": marca},
    })
