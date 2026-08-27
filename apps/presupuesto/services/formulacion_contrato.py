"""El salto de FORMULACIÓN a CONTRATO, sin perder la traza.

LA REGLA, y es la que impide el duplicado que la precarga vino a eliminar:

  1. **Nada se empareja solo, y la máquina ni siquiera propone.** Se intentó
     un buscador de candidatos por parecido de objeto y se midió que no puede
     funcionar: sobre un caso de respuesta conocida devolvió 747 candidatos y
     el correcto no estaba entre los doce primeros (ver `buscar_en_secop`). El
     área busca por NÚMERO, que es lo único exacto y lo que conoce porque
     firmó; el sistema le muestra lo que SECOP publica para que confirme.

  2. **Enlazar NO crea un contrato paralelo.** Si el contrato ya está en la
     tabla interna, se enlaza a ése. Si sólo está en el espejo de SECOP, se
     trae con los datos de la fuente —ni uno inventado— y se enlaza. El
     `uq_contrato_tripleta` es la red: si alguien lo intenta dos veces, la base
     lo impide.

  3. **La relación es N:M en los dos sentidos, y no es teoría.** El contrato 98
     toca siete actividades del plan; las actividades 124 y 125 tienen dos
     contratos cada una. Un contrato puede nacer de varias formulaciones y una
     formulación puede terminar en varios contratos.

  4. **Deshacer no borra el contrato.** Quita el vínculo y deja la traza. Un
     emparejamiento equivocado se corrige; un contrato borrado no se recupera.

Desde un contrato se puede responder «¿de qué formulación nací?» y desde una
formulación «¿en qué contrato terminé?». Ése es el §15 del plan.
"""
from __future__ import annotations

import re
import unicodedata

#: La MISMA conciliación de siempre. No se reimplementa: se importa. Hubo un
#: emparejamiento propio que empataba 0 de 25 durante meses.
from apps.dashboard.services.kpis_presupuesto import _REF_SECOP_RX

_RX = re.compile(_REF_SECOP_RX)

#: Palabras que aparecen en casi todo objeto contractual y no distinguen nada.
_VACIAS = {
    "de", "la", "el", "los", "las", "del", "y", "en", "para", "con", "por", "a",
    "al", "un", "una", "que", "se", "su", "sus", "prestar", "servicios",
    "servicio", "apoyo", "realizar", "realizacion", "contrato", "contratar",
    "localidad", "kennedy", "alcaldia", "local", "fondo", "desarrollo",
}


class EnlaceInvalido(ValueError):
    """No se puede enlazar. El motivo va en castellano: termina en pantalla."""


def _norma(texto: str) -> set[str]:
    """Palabras significativas de un texto, sin tildes ni relleno."""
    base = unicodedata.normalize("NFKD", texto or "")
    base = "".join(c for c in base if not unicodedata.combining(c)).lower()
    return {p for p in re.findall(r"[a-z0-9]+", base)
            if len(p) > 3 and p not in _VACIAS}


def _partes(referencia: str):
    """(tipo, número, vigencia) de una referencia de SECOP, o None."""
    m = _RX.match((referencia or "").upper().strip())
    if not m:
        return None
    tipo = re.match(r"^([A-Z]+)", (referencia or "").upper().strip())
    return (tipo.group(1) if tipo else None, int(m.group(1)), int(m.group(2)))


def buscar_en_secop(termino: str, vigencia: int | None = None, limite: int = 20) -> dict:
    """Busca en el espejo de SECOP el contrato que el área ya firmó.

    **POR NÚMERO O REFERENCIA, no por parecido de texto.** Y esto no es pereza:
    se intentó lo otro y se midió que no puede funcionar.

    LO QUE SE PROBÓ Y SE DESCARTÓ (2026-08-27). Un buscador de «candidatos» que
    proponía filas de SECOP con palabras en común con el objeto de la
    formulación. Contra un caso de respuesta conocida —la actividad 114, cuyo
    contrato real es el CPS-983-2025— devolvió **747 candidatos** y el correcto
    **no estaba entre los doce primeros**: arriba quedaban contratos que
    empataban por «comunitarias», «mediante» y «procesos», que es plantilla.

    La causa no es el tokenizador. Son TRES IDIOMAS para la misma cosa:

        la formulación dice   «Fortalecer 100 organizaciones comunitarias»
        innovaK guarda        «KENNEDY CAMINA SEGURA — convenio 983-2025»
        SECOP publica         «PRESTAR SERVICIOS PARA LA IMPLEMENTACIÓN DE
                               ACCIONES PEDAGÓGICAS Y LOGÍSTICAS…»

    Cero palabras significativas en común. El repo ya lo había escrito para la
    precarga (`precargar_contratos_secop.py::_difieren`): el objeto interno es
    un nombre curado y el de SECOP es el objeto legal. Proponer sobre eso sería
    ofrecer un candidato equivocado con cara de acierto, y alguien lo pulsaría.

    Y no hay otra señal fiable: SECOP **no publica** el área, ni el proyecto, ni
    la meta. Lo único exacto es el número — que el área conoce, porque firmó.
    """
    from apps.presupuesto.models import FormulacionContrato, SecopContrato

    termino = (termino or "").strip()
    if len(termino) < 3:
        return {"resultados": [], "total": 0,
                "motivo_vacio": "Escribe al menos tres caracteres del número o "
                                "la referencia del contrato (por ejemplo «983»)."}

    qs = SecopContrato.objects.all()
    if vigencia:
        qs = qs.filter(anio=vigencia)

    solo_digitos = re.sub(r"\D", "", termino)
    if solo_digitos:
        # Por número: es la vía exacta. `referencia_contrato` trae sufijos
        # —«CPS-1113-2024 (2)»— así que se busca por contención, no por igualdad.
        qs = qs.filter(referencia_contrato__icontains=solo_digitos)
    else:
        qs = qs.filter(referencia_contrato__icontains=termino)

    ya_ligados = set(FormulacionContrato.objects.values_list("contrato_id", flat=True))
    filas = []
    for s in qs.order_by("-anio", "referencia_contrato")[:limite]:
        p = _partes(s.referencia_contrato)
        interno = _contrato_interno(p) if p else None
        filas.append({
            "id_contrato": s.id_contrato,
            "referencia": s.referencia_contrato,
            "anio": s.anio,
            "objeto": (s.objeto_contrato or "")[:220],
            "valor": float(s.valor_contrato) if s.valor_contrato is not None else None,
            "proveedor": s.proveedor,
            "estado_secop": s.estado_contrato,
            "modalidad": s.modalidad,
            "url_proceso": s.url_proceso,
            "proceso_de_compra": s.proceso_de_compra,
            # Si la referencia no parsea, el número no se puede deducir y el
            # enlace lo va a rechazar. Se avisa ANTES de que pulse.
            "parseable": p is not None,
            "ya_en_innovak": interno.id if interno else None,
            "ya_ligado_a_otra": bool(interno and interno.id in ya_ligados),
        })

    return {
        "resultados": filas,
        "total": qs.count(),
        "mostrados": len(filas),
        "criterio": ("Búsqueda por número o referencia del contrato en el espejo "
                     "de SECOP. No se busca por parecido del objeto: el texto "
                     "del plan y el objeto legal no comparten vocabulario."),
        "motivo_vacio": (None if filas else
                         f"Ninguna referencia de SECOP contiene «{termino}». Si el "
                         f"contrato acaba de firmarse, puede que todavía no esté "
                         f"publicado: el espejo se actualiza a diario."),
    }


def _contrato_interno(partes):
    """El contrato interno de esa tripleta, si ya existe."""
    if not partes:
        return None
    from apps.presupuesto.models import Contrato
    tipo, numero, vigencia = partes
    return Contrato.objects.filter(contrato_tipo=tipo, contrato_numero=numero,
                                   contrato_vigencia=vigencia).first()


def enlazar_desde_secop(formulacion, id_contrato_secop: str, usuario) -> dict:
    """Ata la formulación al contrato publicado en SECOP. Lo trae si hace falta.

    Lanza `EnlaceInvalido` con el motivo en castellano. No inventa ni un dato:
    todo lo que se escribe en `contrato` viene de la fila del espejo.
    """
    from django.db import transaction
    from django.utils import timezone

    from apps.presupuesto.models import (
        Contrato, FormulacionContrato, SecopContrato,
    )
    from apps.presupuesto.models.auditoria import AuditoriaDato
    from apps.presupuesto.services.auditoria import registrar_cambio

    s = SecopContrato.objects.filter(id_contrato=id_contrato_secop).first()
    if s is None:
        raise EnlaceInvalido("Esa fila no está en el espejo de SECOP.")

    partes = _partes(s.referencia_contrato)
    if partes is None:
        raise EnlaceInvalido(
            f"La referencia «{s.referencia_contrato}» no tiene el formato "
            f"TIPO-NÚMERO-AÑO, así que no se puede deducir el número del "
            f"contrato. Hay que registrarlo a mano.")

    tipo, numero, vigencia = partes
    ahora = timezone.now()

    with transaction.atomic():
        contrato = _contrato_interno(partes)
        creado = False
        if contrato is None:
            # Se trae con los datos de la FUENTE. Ninguno se inventa; lo que
            # SECOP no publica queda NULL.
            contrato = Contrato.objects.create(
                id=_siguiente_id_contrato(),
                contrato_tipo=tipo, contrato_numero=numero,
                contrato_vigencia=vigencia,
                objeto=(s.objeto_contrato or None),
                valor=s.valor_contrato,
                fecha_inicio=s.fecha_inicio, fecha_fin=s.fecha_fin,
            )
            creado = True
            registrar_cambio(
                usuario=usuario, entidad="contrato", entidad_id=contrato.id,
                campo="creacion", valor_anterior=None,
                valor_nuevo=f"{tipo} {numero}/{vigencia}",
                contrato_id=contrato.id, subgrupo_id=formulacion.subgrupo_id,
                fuente=AuditoriaDato.SECOP,
                observacion=(f"Traído del espejo de SECOP ({s.id_contrato}) al "
                             f"enlazarlo con la formulación {formulacion.id}."))

        if FormulacionContrato.objects.filter(formulacion=formulacion,
                                              contrato=contrato).exists():
            raise EnlaceInvalido("Esa formulación ya está enlazada a ese contrato.")

        FormulacionContrato.objects.create(
            formulacion=formulacion, contrato=contrato,
            ligado_en=ahora, ligado_por_id=getattr(usuario, "id", None))
        registrar_cambio(
            usuario=usuario, entidad="formulacion", entidad_id=formulacion.id,
            campo="contrato", valor_anterior=None,
            valor_nuevo=f"{tipo} {numero}/{vigencia}",
            contrato_id=contrato.id, subgrupo_id=formulacion.subgrupo_id,
            fuente=AuditoriaDato.MANUAL,
            observacion=f"Enlazada desde SECOP ({s.id_contrato}).")

    return {"contrato_id": contrato.id, "numero": f"{tipo} {numero}/{vigencia}",
            "contrato_creado": creado, "id_contrato_secop": s.id_contrato}


def _siguiente_id_contrato() -> int:
    """El id del contrato nuevo.

    `contrato.id` ES identity (la «deuda S5» es falsa), pero el modelo Django lo
    declara `IntegerField`, así que el ORM manda `id=NULL` y el INSERT falla. Se
    toma de la secuencia REAL en vez de un MAX+1: el MAX+1 no la avanza y deja
    los dos contadores separados —hoy la secuencia va en 386 y los ids en 105—,
    que es como se llega a una colisión meses después.
    """
    from django.db import connection
    with connection.cursor() as cur:
        cur.execute("SELECT nextval(pg_get_serial_sequence('contrato', 'id'))")
        return cur.fetchone()[0]


def desenlazar(formulacion, contrato_id: int, usuario, motivo: str | None = None) -> dict:
    """Quita el vínculo. NO borra el contrato.

    Un emparejamiento equivocado se corrige; un contrato borrado no se
    recupera. Y el deshacer queda auditado con su motivo, porque «por qué se
    desató» es justo lo que alguien va a preguntar dentro de un año.
    """
    from apps.presupuesto.models import FormulacionContrato
    from apps.presupuesto.models.auditoria import AuditoriaDato
    from apps.presupuesto.services.auditoria import registrar_cambio

    vinculo = FormulacionContrato.objects.filter(
        formulacion=formulacion, contrato_id=contrato_id).first()
    if vinculo is None:
        raise EnlaceInvalido("Esa formulación no está enlazada a ese contrato.")

    numero = str(vinculo.contrato)
    vinculo.delete()
    registrar_cambio(
        usuario=usuario, entidad="formulacion", entidad_id=formulacion.id,
        campo="contrato", valor_anterior=numero, valor_nuevo=None,
        contrato_id=contrato_id, subgrupo_id=formulacion.subgrupo_id,
        fuente=AuditoriaDato.MANUAL,
        observacion=motivo or "Sin motivo declarado.")
    return {"ok": True, "contrato_id": contrato_id, "numero": numero}


def contratos_de(formulacion) -> list[dict]:
    """En qué contratos terminó una formulación. La mitad del §15."""
    from apps.presupuesto.models import FormulacionContrato
    return [{
        "contrato_id": v.contrato_id,
        "numero": str(v.contrato),
        "valor": float(v.contrato.valor) if v.contrato.valor is not None else None,
        "objeto": v.contrato.objeto,
        "etapa": v.contrato.etapa.nombre if v.contrato.etapa_id else None,
        "ligado_en": v.ligado_en.isoformat() if v.ligado_en else None,
    } for v in (FormulacionContrato.objects.filter(formulacion=formulacion)
                .select_related("contrato", "contrato__etapa"))]


def formulaciones_de(contrato_id: int) -> list[dict]:
    """De qué formulación nació un contrato. La otra mitad del §15."""
    from apps.presupuesto.models import FormulacionContrato
    return [{
        "formulacion_id": v.formulacion_id,
        "codigo": f"F-{v.formulacion_id:03d}",
        "objeto": v.formulacion.objeto,
        "vigencia": v.formulacion.vigencia_id,
        "actividad_plan_id": v.formulacion.actividad_plan_id,
        "estado": v.formulacion.estado.nombre,
    } for v in (FormulacionContrato.objects.filter(contrato_id=contrato_id)
                .select_related("formulacion", "formulacion__estado"))]
