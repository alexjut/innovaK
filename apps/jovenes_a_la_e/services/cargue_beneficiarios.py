"""Cargue masivo de beneficiarios — el servicio que sí escribe.

Tres tiempos, con la compuerta humana en el medio:

    1. prevalidar  →  `cargue_excel.leer()`. No persiste. Ya existe.
    2. crear_lote  →  guarda el reporte y el hash. Todavía no escribe entregas.
    3. procesar    →  escribe personas, beneficiarios y entregas.

Y `anular`, que deshace un lote entero.

## Por qué el lote guarda el reporte y no el archivo

Lo que hay que escribir ya está normalizado dentro del reporte, con el número
de fila real de cada registro. Guardar además el .xlsx obligaría a montar
almacenamiento para un binario que ya no aporta nada, y el SHA-256 sigue
alcanzando para reconocerlo si lo vuelven a subir.

## Una matrícula por persona, y la elige quien carga

Decisión de Alex (2026-08-12). Cuando una persona aparece con dos matrículas en
el mismo archivo —caso real: el documento 1000494673, Técnico Laboral en una
institución y Administración de Empresas en otra— **se carga UNA sola**, y cuál
lo decide la persona que carga, no el sistema. El servicio se niega a procesar
mientras algún documento repetido no tenga elección: elegir por omisión «la
primera» sería decidir por el usuario justo donde él dijo que no.

Las descartadas quedan en el reporte con `descartada=True` y su motivo, así que
después se puede saber qué no entró y por qué.

## Enriquecer en vez de duplicar

Si la persona ya tiene una entrega de esa vigencia capturada por QR —sin
códigos SNIES—, el cargue **completa esa fila** en vez de crear otra: conserva
la firma que el ciudadano dejó y evita dos filas para un mismo beneficio. Si el
programa que dice el QR no coincide con el del archivo, se avisa con los dos
valores; el ciudadano bien pudo escribirlo distinto, y el que manda es el
archivo oficial.
"""
from __future__ import annotations

import hashlib
import logging

from django.db import transaction

from apps.jovenes_a_la_e.models import CargueBeneficiarios, EntregaBeca
from apps.jovenes_a_la_e.services import cargue_excel
from apps.login.services.beneficiario_helpers import asegurar_beneficiario_persona

logger = logging.getLogger(__name__)


class CargueInvalido(Exception):
    """El lote no se puede crear o procesar. El mensaje va al usuario tal cual."""


def sha256_de(archivo) -> str:
    """Hash del contenido, leyéndolo por bloques y dejando el puntero al inicio."""
    h = hashlib.sha256()
    archivo.seek(0)
    for bloque in iter(lambda: archivo.read(64 * 1024), b""):
        h.update(bloque)
    archivo.seek(0)
    return h.hexdigest()


def documentos_repetidos(filas: list[dict]) -> dict[str, list[dict]]:
    """Documentos con más de una matrícula cargable, con sus filas.

    Solo mira las filas que se podrían cargar: dos filas con error no son un
    caso de elección, son dos filas que hay que corregir.
    """
    por_documento: dict[str, list[dict]] = {}
    for fila in filas:
        if fila.get("estado") == "error":
            continue
        doc = (fila.get("datos") or {}).get("documento")
        if doc:
            por_documento.setdefault(doc, []).append(fila)
    return {doc: grupo for doc, grupo in por_documento.items() if len(grupo) > 1}


def aplicar_elecciones(filas: list[dict], elecciones: dict) -> list[dict]:
    """Marca como descartadas las matrículas que el usuario no eligió.

    `elecciones` es `{documento: fila_excel_elegida}`. Devuelve las filas con
    `descartada` y `motivo_descarte` puestos donde corresponde.

    Lanza `CargueInvalido` si falta una elección o si apunta a una fila que no
    es de ese documento: procesar con una elección incompleta cargaría las dos
    matrículas, que es justo lo que se quiso evitar.
    """
    repetidos = documentos_repetidos(filas)
    elecciones = {str(k): int(v) for k, v in (elecciones or {}).items()}

    faltantes = [doc for doc in repetidos if doc not in elecciones]
    if faltantes:
        raise CargueInvalido(
            "Falta elegir cuál matrícula se carga para "
            f"{len(faltantes)} documento(s): {', '.join(sorted(faltantes)[:5])}"
            + ("…" if len(faltantes) > 5 else "")
        )

    for doc, grupo in repetidos.items():
        elegida = elecciones[doc]
        validas = {f["fila"] for f in grupo}
        if elegida not in validas:
            raise CargueInvalido(
                f"Para el documento {doc} se eligió la fila {elegida}, que no es "
                f"una de sus matrículas ({', '.join(str(f) for f in sorted(validas))})."
            )
        for fila in grupo:
            if fila["fila"] != elegida:
                fila["descartada"] = True
                fila["motivo_descarte"] = (
                    f"Se cargó la matrícula de la fila {elegida} para este documento; "
                    "por decisión de quien carga, una persona entra una sola vez."
                )
    return filas


def _cargables(filas: list[dict]) -> list[dict]:
    return [f for f in filas
            if f.get("estado") != "error" and not f.get("descartada")]


@transaction.atomic
def crear_lote(*, archivo, evento, vigencia: int, usuario=None,
               elecciones: dict | None = None) -> CargueBeneficiarios:
    """Lee el archivo, valida y deja el lote listo para procesar. NO escribe entregas."""
    from apps.login.models import Evento

    if not isinstance(evento, Evento):
        raise CargueInvalido("Falta el evento de captura al que pertenece el cargue.")
    # `tipo_evento_id` guarda el CÓDIGO, no un entero: el modelo mapea la
    # columna `tipo_evento_codigo` como FK con `to_field='codigo'`.
    if evento.tipo_evento_id != "JOVENES_BECA":
        raise CargueInvalido(
            f"El evento «{evento.nombre}» no es de entrega de becas."
        )
    if not evento.actividad_plan_id:
        # Sin actividad del plan no hay KPI al final de la cadena, así que los
        # beneficiarios no le sumarían a ninguna meta. Es la regla que el DDL
        # 004 dejó exigida en `tipo_evento`.
        raise CargueInvalido(
            f"El evento «{evento.nombre}» no está atado a una actividad del plan: "
            "sus beneficiarios no le sumarían a ninguna meta. Asígnasela antes de cargar."
        )
    if vigencia is None or int(vigencia) < 2024:
        raise CargueInvalido("La vigencia debe ser un año igual o posterior a 2024.")
    vigencia = int(vigencia)

    hash_archivo = sha256_de(archivo)
    ya = (CargueBeneficiarios.objects
          .filter(vigencia=vigencia, archivo_sha256=hash_archivo)
          .exclude(estado="anulado").first())
    if ya:
        raise CargueInvalido(
            f"Este archivo ya se cargó en la vigencia {vigencia} (lote #{ya.id}, "
            f"{ya.get_estado_display().lower()}). Anúlalo si quieres volver a cargarlo."
        )

    lectura = cargue_excel.leer(archivo)
    filas = [f.como_dict() for f in lectura.filas]
    aplicar_elecciones(filas, elecciones or {})

    resumen = lectura.resumen()
    resumen["vigencia"] = vigencia
    resumen["archivo"] = getattr(archivo, "name", "")
    resumen["descartadas"] = sum(1 for f in filas if f.get("descartada"))

    return CargueBeneficiarios.objects.create(
        evento=evento,
        usuario=usuario if getattr(usuario, "pk", None) else None,
        vigencia=vigencia,
        archivo_nombre=getattr(archivo, "name", "sin-nombre.xlsx"),
        archivo_sha256=hash_archivo,
        estado="validado",
        filas_total=lectura.total,
        filas_ok=len(_cargables(filas)),
        filas_error=lectura.con_error,
        reporte={"resumen": resumen, "filas": filas},
    )


def _entrega_qr_existente(vigencia: int, documento: str):
    """La entrega de esa persona y vigencia capturada por QR, si la hay.

    Se reconoce por no tener códigos SNIES: es lo que distingue una captura del
    ciudadano de una fila del archivo oficial. La base garantiza que hay como
    mucho UNA (el índice único con NULLS NOT DISTINCT colapsa a
    (vigencia, documento) cuando los SNIES son nulos), así que no hay
    ambigüedad sobre cuál enriquecer.
    """
    return (EntregaBeca.objects
            .filter(vigencia=vigencia, numero_documento=documento,
                    snies_ies__isnull=True, snies_programa__isnull=True)
            .first())


@transaction.atomic
def procesar(lote: CargueBeneficiarios, *, usuario=None) -> dict:
    """Escribe personas, beneficiarios y entregas. Devuelve el conteo de lo hecho."""
    from apps.caracterizacion.services.persona_lookup import obtener_o_crear_persona

    if lote.estado == "procesado":
        raise CargueInvalido(f"El lote #{lote.id} ya fue procesado.")
    if lote.estado == "anulado":
        raise CargueInvalido(f"El lote #{lote.id} está anulado.")

    filas = lote.filas_reporte
    if any(f.get("estado") == "error" for f in filas):
        raise CargueInvalido(
            "El archivo tiene filas con error. Corrígelas y vuelve a cargarlo: "
            "no se procesa a medias."
        )

    creadas = enriquecidas = 0
    avisos: list[str] = []

    for fila in _cargables(filas):
        d = fila["datos"]
        persona, _ = obtener_o_crear_persona(
            tipo_documento_codigo=d.get("tipo_documento_codigo") or 6,
            numero_documento=d["documento"],
            nombre1=d["nombre1"],
            apellido1=d["apellido1"],
            nombre2=d.get("nombre2"),
            apellido2=d.get("apellido2"),
        )
        asegurar_beneficiario_persona(
            persona, correo=d.get("correo"), telefono=d.get("telefono"))

        campos = {
            "persona": persona,
            "tipo_doc_codigo": d.get("tipo_documento_codigo"),
            "nombre1": d["nombre1"],
            "nombre2": d.get("nombre2"),
            "apellido1": d["apellido1"],
            "apellido2": d.get("apellido2"),
            "telefono": d.get("telefono"),
            "correo": d.get("correo"),
            "vigencia": lote.vigencia,
            "snies_programa": d.get("snies_programa"),
            "snies_ies": d.get("snies_ies"),
            "programa_academico": d.get("programa"),
            "institucion": d.get("ies_nombre"),
            "nivel_formacion": d.get("nivel_formacion"),
            # El archivo del área no discrimina acceso/permanencia, así que
            # quedan en False y `metas_codigos` en NULL: la entrega existe,
            # pero no se le puede imputar avance a ninguna meta todavía.
            "cumplimiento_acceso": bool(d.get("acceso")),
            "cumplimiento_permanencia": bool(d.get("permanencia")),
            "cargue": lote,
            "origen": "CARGA",
        }
        metas = []
        if campos["cumplimiento_acceso"]:
            metas.append("23771")
        if campos["cumplimiento_permanencia"]:
            metas.append("23772")
        campos["metas_codigos"] = ",".join(metas) or None

        previa = _entrega_qr_existente(lote.vigencia, d["documento"])
        if previa is not None:
            # Enriquecer, no duplicar: se conserva la firma del ciudadano y el
            # evento donde se capturó. Solo se completan los datos académicos.
            if previa.programa_academico and d.get("programa") and \
                    previa.programa_academico.strip().upper() != d["programa"].strip().upper():
                avisos.append(
                    f"Fila {fila['fila']}: el formulario del ciudadano decía "
                    f"«{previa.programa_academico}» y el archivo dice "
                    f"«{d['programa']}». Se dejó el del archivo."
                )
            for campo, valor in campos.items():
                if campo in ("cargue", "origen"):
                    continue          # la fila sigue siendo del QR: tenía firma
                setattr(previa, campo, valor)
            previa.cargue = lote
            previa.save()
            enriquecidas += 1
        else:
            EntregaBeca.objects.create(evento=lote.evento, estado="validada", **campos)
            creadas += 1

    lote.estado = "procesado"
    if usuario is not None and getattr(usuario, "pk", None) and lote.usuario_id is None:
        lote.usuario = usuario
    reporte = lote.reporte or {}
    reporte.setdefault("resumen", {})["avisos_proceso"] = avisos
    lote.reporte = reporte
    lote.save(update_fields=["estado", "usuario", "reporte", "updated_at"])

    return {"creadas": creadas, "enriquecidas": enriquecidas,
            "descartadas": sum(1 for f in filas if f.get("descartada")),
            "avisos": avisos}


@transaction.atomic
def anular(lote: CargueBeneficiarios) -> dict:
    """Deshace el lote: borra lo que escribió y libera su hash.

    Las entregas que el cargue **enriqueció** no se borran: existían antes,
    las capturó un ciudadano y tienen su firma. Se les quita el vínculo con el
    lote y se dejan como estaban en lo demás — borrarlas sería destruir una
    captura que el cargue no creó.
    """
    if lote.estado == "anulado":
        raise CargueInvalido(f"El lote #{lote.id} ya está anulado.")

    del_lote = EntregaBeca.objects.filter(cargue_id=lote.id)
    creadas_por_el = del_lote.filter(origen="CARGA")
    borradas = creadas_por_el.count()
    creadas_por_el.delete()
    desvinculadas = del_lote.update(cargue=None)

    lote.estado = "anulado"
    lote.save(update_fields=["estado", "updated_at"])
    return {"borradas": borradas, "desvinculadas": desvinculadas}
