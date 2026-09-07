"""El motor de la CARGA de la Matriz PDL (pieza 4).

Convierte `activo` / `carga_origen_id` / `carga_retiro_id` —hoy tres columnas
que nadie escribe— en la regla del plan:

    **La carga nunca borra.** Lo que desaparece de la matriz se marca
    `activo = FALSE` apuntando a la carga que lo retiró.

Dos operaciones, en este orden y nunca fusionadas:

    previsualizar(ruta, corte, usuario)  → una carga en `borrador` con su diff
    aplicar(carga_id, usuario)           → la escribe, en UNA transacción

Están separadas a propósito: el diff tiene que poder mirarse y decidirse. Si
`previsualizar` aplicara, el estado `borrador` no significaría nada y las tres
pantallas de la Fase C no tendrían dónde apoyarse.

QUÉ CUBRE Y QUÉ NO
------------------
Cubre la JERARQUÍA —sectores, objetivos, programas—, que es donde vive la regla
de retiro: son entidades con nombre propio que pueden dejar de existir. NO
toca la plata ni las magnitudes: ésas siguen entrando por
`importar_matriz_pdl_alk`, que ya es idempotente y no pisa lo escrito. Fusionar
las dos cosas en un solo paso mezclaría «cambió el catálogo del Plan» con
«llegaron cifras nuevas», que se revisan distinto y se equivocan distinto.

LAS FILAS SEMBRADAS ANTES DE ESTO
---------------------------------
Los 13 sectores, 5 objetivos y 22 programas que ya están tienen
`carga_origen_id = NULL`: se sembraron con los DDL 023 y 024, antes de que
existiera el registro de cargas. Se dejan así. Ponerles la primera carga que
pase diría que esa carga los trajo, y es falso — un NULL que significa «venía
de antes» es más honesto que una atribución inventada.
"""
import unicodedata
from datetime import datetime, timezone

from django.db import transaction

from apps.presupuesto.models import (MatrizPDLCarga, ObjetivoEstrategico,
                                     ProgramaPDL, Sector)

HOJA_PROG = "Programacion PDL 2025 - 2028"
HOJA_SEG = "Seguimiento"

COL_SECTOR = 2       # Programacion · C
COL_OBJETIVO = 0     # Seguimiento  · A
COL_PROGRAMA = 1     # Seguimiento  · B

ENCABEZADOS = {
    HOJA_PROG: {COL_SECTOR: "Sector"},
    HOJA_SEG: {COL_OBJETIVO: "Objetivo Estrategico", COL_PROGRAMA: "Programa"},
}


class CargaError(Exception):
    """Algo impide seguir. El mensaje va tal cual a la pantalla."""


def norm_texto(v):
    """Mayúsculas, sin tildes, sin espacios dobles. UNA implementación."""
    if v is None:
        return ""
    s = unicodedata.normalize("NFKD", str(v))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.upper().split())


def _partir(texto):
    """«3 - Bogotá confía…» → (3, 'Bogotá confía…')."""
    limpio = " ".join(str(texto).split())
    cabeza, sep, resto = limpio.partition("-")
    if not sep or not cabeza.strip().isdigit():
        raise CargaError(
            f"«{limpio}» no tiene la forma «N - nombre». La matriz cambió de "
            f"convención: revisar docs/operacion/matriz_pdl_mapeo.md.")
    return int(cabeza.strip()), resto.strip()


def leer_jerarquia(ruta):
    """Lee las tres entidades de la matriz. No toca la base.

    Valida los encabezados por nombre antes de leer: si la ALK mueve una
    columna, esto aborta en vez de cargar la columna de al lado en silencio.
    """
    try:
        import openpyxl
    except ImportError:  # pragma: no cover - depende del entorno
        raise CargaError("Falta openpyxl para leer el Excel.")

    try:
        wb = openpyxl.load_workbook(ruta, data_only=True, read_only=True)
    except Exception as exc:  # noqa: BLE001 - el motivo va a pantalla
        raise CargaError(f"No se pudo abrir el archivo: {exc}")

    for hoja in (HOJA_PROG, HOJA_SEG):
        if hoja not in wb.sheetnames:
            raise CargaError(
                f"Falta la hoja «{hoja}». El archivo trae: {wb.sheetnames}")

    def filas(hoja):
        it = wb[hoja].iter_rows(values_only=True)
        cabecera = next(it, ()) or ()
        for idx, esperado in ENCABEZADOS[hoja].items():
            visto = cabecera[idx] if idx < len(cabecera) else None
            if norm_texto(visto) != norm_texto(esperado):
                raise CargaError(
                    f"En «{hoja}» la columna {idx} debería ser «{esperado}» y "
                    f"dice «{visto}».")
        for fila in it:
            if fila and any(c is not None for c in fila):
                yield fila

    sectores, objetivos, programas = {}, {}, {}
    for fila in filas(HOJA_PROG):
        crudo = fila[COL_SECTOR]
        if crudo and str(crudo).strip():
            nombre = " ".join(str(crudo).split())
            sectores[norm_texto(nombre)] = nombre

    for fila in filas(HOJA_SEG):
        if not fila[COL_OBJETIVO] or not fila[COL_PROGRAMA]:
            continue
        cod_o, nom_o = _partir(fila[COL_OBJETIVO])
        cod_p, nom_p = _partir(fila[COL_PROGRAMA])
        objetivos[cod_o] = nom_o
        previo = programas.get(cod_p)
        if previo and previo[1] != cod_o:
            raise CargaError(
                f"El programa {cod_p} aparece bajo los objetivos {previo[1]} y "
                f"{cod_o}. El modelo asume UN padre por programa.")
        programas[cod_p] = (nom_p, cod_o)

    if not sectores or not objetivos or not programas:
        raise CargaError(
            "El archivo no trae jerarquía: "
            f"{len(sectores)} sectores, {len(objetivos)} objetivos, "
            f"{len(programas)} programas. No se registra una carga vacía.")
    return {"sectores": sectores, "objetivos": objetivos, "programas": programas}


def _diff_sectores(leidos):
    vivos = {norm_texto(s.nombre_oficial): s for s in Sector.objects.all()}
    altas = [n for k, n in leidos.items() if k not in vivos]
    reactivar = [vivos[k].nombre_oficial for k in leidos if k in vivos and not vivos[k].activo]
    retiros = [s.nombre_oficial for k, s in vivos.items() if k not in leidos and s.activo]
    return {"altas": sorted(altas), "reactivaciones": sorted(reactivar),
            "cambios": [], "retiros": sorted(retiros)}


def _diff_objetivos(leidos):
    vivos = {o.codigo: o for o in ObjetivoEstrategico.objects.all()}
    altas = [{"codigo": c, "nombre": n} for c, n in leidos.items() if c not in vivos]
    cambios = [{"codigo": c, "de": vivos[c].nombre, "a": n}
               for c, n in leidos.items() if c in vivos and vivos[c].nombre != n]
    reactivar = [c for c in leidos if c in vivos and not vivos[c].activo]
    retiros = [{"codigo": c, "nombre": o.nombre}
               for c, o in vivos.items() if c not in leidos and o.activo]
    return {"altas": sorted(altas, key=lambda d: d["codigo"]),
            "cambios": sorted(cambios, key=lambda d: d["codigo"]),
            "reactivaciones": sorted(reactivar),
            "retiros": sorted(retiros, key=lambda d: d["codigo"])}


def _diff_programas(leidos):
    vivos = {p.codigo: p for p in ProgramaPDL.objects.select_related("objetivo")}
    altas, cambios = [], []
    for cod, (nombre, cod_obj) in leidos.items():
        actual = vivos.get(cod)
        if actual is None:
            altas.append({"codigo": cod, "nombre": nombre, "objetivo": cod_obj})
            continue
        campos = {}
        if actual.nombre != nombre:
            campos["nombre"] = {"de": actual.nombre, "a": nombre}
        if actual.objetivo.codigo != cod_obj:
            # Un programa que cambia de objetivo es reorganización del Plan, no
            # una corrección de texto: se marca aparte para que se vea.
            campos["objetivo"] = {"de": actual.objetivo.codigo, "a": cod_obj}
        if campos:
            cambios.append({"codigo": cod, "campos": campos})
    reactivar = [c for c in leidos if c in vivos and not vivos[c].activo]
    retiros = [{"codigo": c, "nombre": p.nombre}
               for c, p in vivos.items() if c not in leidos and p.activo]
    return {"altas": sorted(altas, key=lambda d: d["codigo"]),
            "cambios": sorted(cambios, key=lambda d: d["codigo"]),
            "reactivaciones": sorted(reactivar),
            "retiros": sorted(retiros, key=lambda d: d["codigo"])}


def calcular_diff(leidos):
    """El diff contra el estado vigente. Solo lee."""
    return {
        "sector": _diff_sectores(leidos["sectores"]),
        "objetivo": _diff_objetivos(leidos["objetivos"]),
        "programa": _diff_programas(leidos["programas"]),
    }


def _contar(diff):
    suma = lambda k: sum(len(bloque.get(k, [])) for bloque in diff.values())  # noqa: E731
    # Las reactivaciones cuentan como CAMBIO, no como alta: la fila ya existía
    # y conserva su `carga_origen`. Contarlas como altas diría que la carga las
    # trajo, y solo las devolvió a la vida.
    return {"n_altas": suma("altas"),
            "n_cambios": suma("cambios") + suma("reactivaciones"),
            "n_retiros": suma("retiros"),
            "n_errores": 0}


def previsualizar(ruta, corte_oficial, usuario_id=None, archivo_nombre=None):
    """Registra la carga en `borrador` con su diff. NO aplica nada."""
    h = MatrizPDLCarga.hash_de(ruta)
    previa = MatrizPDLCarga.objects.filter(hash_sha256=h).first()
    if previa:
        raise CargaError(
            f"Este archivo ya se subió: carga {previa.id} del "
            f"{previa.subido_at:%Y-%m-%d}, estado «{previa.estado}». "
            f"Si es un corte nuevo, el archivo tiene que ser distinto.")

    diff = calcular_diff(leer_jerarquia(ruta))
    import os
    return MatrizPDLCarga.objects.create(
        archivo_nombre=archivo_nombre or os.path.basename(ruta),
        hash_sha256=h,
        archivo_bytes=os.path.getsize(ruta),
        corte_oficial=corte_oficial,
        estado=MatrizPDLCarga.BORRADOR,
        diff=diff,
        subido_por_id=usuario_id,
        **_contar(diff),
    )


def _validar_borrador(carga_id, con_lock=True):
    """La carga, si de verdad se puede aplicar. Si no, `CargaError` con el
    motivo en castellano — termina en pantalla."""
    qs = MatrizPDLCarga.objects.filter(id=carga_id)
    carga = (qs.select_for_update() if con_lock else qs).first()
    if carga is None:
        raise CargaError(f"No existe la carga {carga_id}.")
    if carga.estado != MatrizPDLCarga.BORRADOR:
        raise CargaError(
            f"La carga {carga_id} está «{carga.estado}»: solo se aplica un borrador.")
    if not carga.diff:
        raise CargaError(f"La carga {carga_id} no tiene diff. Volvé a previsualizar.")
    return carga


def _cerrar(carga, usuario_id, extra=None):
    """Marca la carga como aplicada. Dos llamadores: `aplicar` (solo jerarquía)
    y `aplicar_completo` (las cuatro fases)."""
    carga.estado = MatrizPDLCarga.APLICADA
    carga.aplicado_por_id = usuario_id
    carga.aplicado_at = datetime.now(timezone.utc)
    campos = ["estado", "aplicado_por_id", "aplicado_at"]
    if extra is not None:
        carga.diff = {**(carga.diff or {}), "aplicado": extra}
        campos.append("diff")
    carga.save(update_fields=campos)
    return carga


@transaction.atomic
def _aplicar_jerarquia(carga, usuario_id=None):
    """Escribe SOLO la jerarquía del diff guardado. Todo o nada, y sin cerrar
    la carga: quién la cierra depende de si esto fue toda la carga o el primer
    paso de una subida completa.

    Se aplica el diff que se GUARDÓ, no uno recalculado: lo que se aplica tiene
    que ser exactamente lo que alguien miró y aprobó. Si la base cambió entre
    la previsualización y esto, se ve en el resultado y se vuelve a subir.
    """

    # El diff tiene DOS formas según cómo se creó la carga: `previsualizar`
    # (consola) guarda la jerarquía en la raíz, y `previsualizar_completo`
    # (pantalla) la anida bajo «jerarquia» junto a cifras, estructura y
    # alertas. Se aceptan las dos porque las cargas viejas siguen siendo
    # aplicables: migrar su JSON para que esta función no tuviera que
    # preguntar sería reescribir el registro histórico por comodidad de una
    # línea de código.
    d = carga.diff.get("jerarquia", carga.diff)
    hecho = {"altas": 0, "cambios": 0, "reactivaciones": 0, "retiros": 0}

    # ── sectores ──
    for nombre in d["sector"]["altas"]:
        Sector.objects.create(nombre_oficial=nombre, carga_origen_id=carga.id)
        hecho["altas"] += 1
    for nombre in d["sector"].get("reactivaciones", []):
        hecho["reactivaciones"] += Sector.objects.filter(
            nombre_oficial=nombre).update(activo=True, carga_retiro_id=None)
    for nombre in d["sector"]["retiros"]:
        hecho["retiros"] += Sector.objects.filter(nombre_oficial=nombre).update(
            activo=False, carga_retiro_id=carga.id)

    # ── objetivos ──
    for alta in d["objetivo"]["altas"]:
        ObjetivoEstrategico.objects.create(
            codigo=alta["codigo"], nombre=alta["nombre"], carga_origen_id=carga.id)
        hecho["altas"] += 1
    for cam in d["objetivo"]["cambios"]:
        hecho["cambios"] += ObjetivoEstrategico.objects.filter(
            codigo=cam["codigo"]).update(nombre=cam["a"])
    for cod in d["objetivo"].get("reactivaciones", []):
        hecho["reactivaciones"] += ObjetivoEstrategico.objects.filter(
            codigo=cod).update(activo=True, carga_retiro_id=None)
    for ret in d["objetivo"]["retiros"]:
        hecho["retiros"] += ObjetivoEstrategico.objects.filter(
            codigo=ret["codigo"]).update(activo=False, carga_retiro_id=carga.id)

    # ── programas ── (después de los objetivos: un alta puede necesitar uno nuevo)
    ids_obj = {o.codigo: o.id for o in ObjetivoEstrategico.objects.all()}
    for alta in d["programa"]["altas"]:
        objetivo_id = ids_obj.get(alta["objetivo"])
        if objetivo_id is None:
            raise CargaError(
                f"El programa {alta['codigo']} cuelga del objetivo "
                f"{alta['objetivo']}, que no existe ni lo crea esta carga.")
        ProgramaPDL.objects.create(
            codigo=alta["codigo"], nombre=alta["nombre"],
            objetivo_id=objetivo_id, carga_origen_id=carga.id)
        hecho["altas"] += 1
    for cam in d["programa"]["cambios"]:
        campos = {}
        if "nombre" in cam["campos"]:
            campos["nombre"] = cam["campos"]["nombre"]["a"]
        if "objetivo" in cam["campos"]:
            destino = ids_obj.get(cam["campos"]["objetivo"]["a"])
            if destino is None:
                raise CargaError(
                    f"El programa {cam['codigo']} se mueve al objetivo "
                    f"{cam['campos']['objetivo']['a']}, que no existe.")
            campos["objetivo_id"] = destino
        if campos:
            hecho["cambios"] += ProgramaPDL.objects.filter(
                codigo=cam["codigo"]).update(**campos)
    for cod in d["programa"].get("reactivaciones", []):
        hecho["reactivaciones"] += ProgramaPDL.objects.filter(
            codigo=cod).update(activo=True, carga_retiro_id=None)
    for ret in d["programa"]["retiros"]:
        hecho["retiros"] += ProgramaPDL.objects.filter(
            codigo=ret["codigo"]).update(activo=False, carga_retiro_id=carga.id)

    return carga, hecho


def aplicar(carga_id, usuario_id=None):
    """Aplica SOLO la jerarquía y cierra la carga.

    Es lo que usa `manage.py cargar_matriz_pdl`. Para la subida por pantalla
    —que entra jerarquía, cifras, estructura y alertas de una— está
    `aplicar_completo`.
    """
    carga = _validar_borrador(carga_id)
    _, hecho = _aplicar_jerarquia(carga, usuario_id)
    return _cerrar(carga, usuario_id), hecho


def descartar(carga_id, nota=None):
    """Cierra un borrador sin aplicarlo. Queda como registro de que se miró."""
    carga = MatrizPDLCarga.objects.filter(id=carga_id).first()
    if carga is None:
        raise CargaError(f"No existe la carga {carga_id}.")
    if carga.estado != MatrizPDLCarga.BORRADOR:
        raise CargaError(f"La carga {carga_id} está «{carga.estado}».")
    carga.estado = MatrizPDLCarga.DESCARTADA
    carga.nota = nota
    carga.save(update_fields=["estado", "nota"])
    return carga


# ─────────────────────────────────────────────────────────────────────────
# LA SUBIDA COMPLETA: jerarquía + cifras + estructura + alertas
#
# El Excel de la ALK alimenta CUATRO cosas, y hasta acá cada una entraba por
# su propio comando de consola:
#
#   1. jerarquía   sectores, objetivos y programas   → este módulo
#   2. cifras      plata por meta y vigencia          → importar_matriz_pdl_alk
#   3. estructura  proyectos, metas y KPI faltantes   → importar_matriz_pdl_alk
#   4. alertas     cumplimiento por meta              → importar_alerta_metas_pdl
#
# Subir la matriz y que solo entrara la jerarquía habría sido peor que no
# tener pantalla: el diff diría «sin cambios» cuando lo que cambió fueron las
# cifras, que es lo que se mueve todos los meses.
#
# LOS DOS IMPORTADORES NO SE REESCRIBIERON. Son secos por defecto, idempotentes
# y firmados, y llevan meses de correcciones medidas encima (el chequeo de meta
# agrupada que evitó duplicar los indicadores 51/52, el emparejado de columnas
# por nombre y no por posición). Copiar esa lógica acá para «integrarla» habría
# creado una segunda implementación que se desincroniza con la primera. Se
# invocan, y su reporte queda guardado en la carga.
#
# La consecuencia honesta: la jerarquía y las cifras traen diff ESTRUCTURADO
# —se puede preguntar qué cambió, campo por campo—, y la estructura y las
# alertas traen el reporte del importador como texto. No es lo mismo, y por
# eso el payload los separa en vez de mezclarlos en una lista que parecería
# uniforme.
# ─────────────────────────────────────────────────────────────────────────

#: Dónde se guarda el xlsx entre previsualizar y aplicar.
#:
#: NO va en MEDIA_ROOT: nginx sirve `/media/` público y sin autenticación
#: (`nginx.conf`, `location /media/`), y esta matriz trae el presupuesto entero
#: de la localidad. Un archivo que se sube para revisarlo no puede quedar
#: descargable por cualquiera que adivine el nombre.
SUBDIR_CARGAS = ("data", "matriz_cargas")


def _dir_cargas():
    from pathlib import Path

    from django.conf import settings
    d = Path(settings.BASE_DIR).joinpath(*SUBDIR_CARGAS)
    d.mkdir(parents=True, exist_ok=True)
    return d


def ruta_de(carga) -> str | None:
    """El xlsx guardado de una carga, o `None` si ya no está.

    Se nombra por hash y no por el nombre original: dos cortes distintos
    pueden llamarse igual («Matriz de seguimiento PDL 2025-2028.xlsx» es el
    nombre de todos), y el segundo pisaría al primero.
    """
    p = _dir_cargas() / f"{carga.hash_sha256}.xlsx"
    return str(p) if p.exists() else None


def _leer_cifras(ruta):
    """{(codigo_meta, vigencia): {campo: valor}} de la hoja «Seguimiento».

    Reusa `_columnas_plata` del importador —que empareja los encabezados por
    NOMBRE y no por posición, porque el Excel los trae con espacios de más y
    saltos de línea en medio— en vez de volver a resolverlos acá. Dos lecturas
    del mismo Excel que se resuelvan distinto es exactamente lo que hace que la
    previsualización y la escritura terminen discrepando.
    """
    import openpyxl

    from apps.presupuesto.management.commands.importar_matriz_pdl_alk import (
        VIGENCIAS, _columnas_plata, _num,
    )

    wb = openpyxl.load_workbook(ruta, data_only=True, read_only=True)
    ws = wb[HOJA_SEG]
    headers = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    cols = _columnas_plata(headers)
    idx = {h: i for i, h in enumerate(headers) if h is not None}

    salida = {}
    for fila in ws.iter_rows(min_row=2, values_only=True):
        if fila is None or all(v is None for v in fila):
            continue
        concat = fila[idx["Codigo cocatenado"]] if "Codigo cocatenado" in idx else None
        if concat is None:
            continue
        for vig in VIGENCIAS:
            valores = {campo: _num(fila[idx[hdr]])
                       for campo, hdr in cols[vig].items() if hdr in idx}
            if not any(v is not None for v in valores.values()):
                continue
            salida[(str(concat), vig)] = valores
    wb.close()
    return salida


#: Cuánto puede moverse un peso sin que cuente como cambio. Los valores viajan
#: por Excel y vuelven como float: 1328346000.0 y 1328345999.9999998 son la
#: misma plata, y reportarlos como cambio llenaría el diff de ruido que nadie
#: puede revisar.
TOLERANCIA_PESOS = 1.0


def _diff_cifras(leidas):
    """Altas y cambios de plata por meta×vigencia, campo por campo.

    NO HAY RETIROS, y es a propósito: una meta que desaparece de la matriz
    conserva su plata histórica. Borrarla dejaría al cockpit sin poder explicar
    en qué se ejecutó una vigencia cerrada. Lo que el archivo no trae, se
    queda tal cual — que es la regla que pidió Alex: «actualiza datos, no suma
    ni borra, y lo que no viene ya está».
    """
    from django.db import connection

    campos = ("proyectado_pdl", "apropiacion_poai", "comprometido", "girado")
    with connection.cursor() as cur:
        cur.execute(f"""
            SELECT codigo_meta, vigencia, {', '.join(campos)}
            FROM presu_presupuesto_meta_vigencia
            WHERE fuente = 'matriz_pdl_alk'
        """)
        actual = {(str(r[0]), r[1]): dict(zip(campos, [
            float(v) if v is not None else None for v in r[2:]]))
            for r in cur.fetchall()}

    altas, cambios = [], []
    for clave, nuevos in sorted(leidas.items()):
        cod, vig = clave
        viejos = actual.get(clave)
        if viejos is None:
            altas.append({"codigo_meta": cod, "vigencia": vig, "valores": nuevos})
            continue
        movidos = {}
        for campo in campos:
            a, b = viejos.get(campo), nuevos.get(campo)
            # `None → valor` es un alta de campo y cuenta; `valor → None` NO
            # se reporta como cambio porque el importador no escribe nulos
            # sobre datos: una columna vacía en el Excel de este mes no borra
            # lo que se cargó el mes pasado.
            if b is None:
                continue
            if a is None or abs(a - b) > TOLERANCIA_PESOS:
                movidos[campo] = {"de": a, "a": b}
        if movidos:
            cambios.append({"codigo_meta": cod, "vigencia": vig, "campos": movidos})

    return {
        "altas": altas,
        "cambios": cambios,
        "sin_cambio": len(leidas) - len(altas) - len(cambios),
        "filas_leidas": len(leidas),
    }


def _correr_importador(comando, ruta, escribir=False, usuario=None):
    """Invoca un importador y devuelve su reporte como texto.

    Se captura la salida en vez de refactorizar los comandos: llevan meses de
    correcciones medidas encima y son la única implementación de esa lógica.
    Si algo falla, el error viaja como parte del reporte en vez de tumbar la
    carga entera — al previsualizar es información («este importador no va a
    poder»), no una excepción que deja a la persona sin ver el resto del diff.
    """
    import io

    from django.core.management import call_command

    buf = io.StringIO()
    kwargs = {"stdout": buf, "stderr": buf}
    if escribir:
        kwargs["write"] = True
        kwargs["usuario"] = usuario
    try:
        call_command(comando, ruta, **kwargs)
        return {"ok": True, "reporte": buf.getvalue()}
    except Exception as e:                      # noqa: BLE001 — va a pantalla
        return {"ok": False, "reporte": buf.getvalue(), "error": str(e)}


def previsualizar_completo(ruta, corte_oficial, usuario_id=None,
                           archivo_nombre=None):
    """Registra la carga en `borrador` con el diff de las CUATRO fases.

    No escribe nada del plan: deja la carga lista para que alguien mire el
    diff y decida. El archivo se guarda porque `aplicar_completo` lo necesita
    —los dos importadores leen el xlsx, no el diff— y porque exigir que se
    vuelva a subir para aplicar abriría la puerta a aplicar un archivo
    distinto del que se revisó.
    """
    import os
    import shutil

    h = MatrizPDLCarga.hash_de(ruta)
    previa = MatrizPDLCarga.objects.filter(hash_sha256=h).first()
    if previa:
        raise CargaError(
            f"Este archivo ya se subió: carga {previa.id} del "
            f"{previa.subido_at:%Y-%m-%d}, estado «{previa.estado}». "
            f"Si es un corte nuevo, el archivo tiene que ser distinto.")

    diff_jerarquia = calcular_diff(leer_jerarquia(ruta))
    diff_cifras = _diff_cifras(_leer_cifras(ruta))
    estructura = _correr_importador("importar_matriz_pdl_alk", ruta)
    alertas = _correr_importador("importar_alerta_metas_pdl", ruta)

    conteos = _contar(diff_jerarquia)
    # Las cifras entran al conteo de la carga: son el grueso de lo que cambia
    # mes a mes, y dejarlas fuera haría que una carga con 300 cifras movidas y
    # ningún programa nuevo se anunciara como «sin cambios».
    conteos["n_altas"] += len(diff_cifras["altas"])
    conteos["n_cambios"] += len(diff_cifras["cambios"])

    destino = _dir_cargas() / f"{h}.xlsx"
    shutil.copyfile(ruta, destino)

    return MatrizPDLCarga.objects.create(
        archivo_nombre=archivo_nombre or os.path.basename(ruta),
        hash_sha256=h,
        archivo_bytes=os.path.getsize(ruta),
        corte_oficial=corte_oficial,
        estado=MatrizPDLCarga.BORRADOR,
        diff={
            "jerarquia": diff_jerarquia,
            "cifras": diff_cifras,
            "estructura": estructura,
            "alertas": alertas,
        },
        subido_por_id=usuario_id,
        **conteos,
    )


def aplicar_completo(carga_id, usuario_id=None):
    """Escribe las cuatro fases. Devuelve `(carga, hecho)`.

    LA JERARQUÍA VA EN TRANSACCIÓN Y LOS IMPORTADORES NO, y no es un descuido:
    cada importador abre la suya y es idempotente, así que reintentarlo es
    seguro. Meterlos dentro de una transacción externa haría que un fallo en
    las alertas revirtiera las cifras ya escritas, y volver a aplicar una carga
    está bloqueado por el estado — quedaría un corte a medio entrar sin forma
    de terminarlo desde la pantalla.

    Por eso el orden es de más estructural a más accesorio: si algo se cae, lo
    que quedó escrito es lo que sostiene a lo demás, nunca al revés.
    """
    carga = _validar_borrador(carga_id, con_lock=False)
    ruta = ruta_de(carga)
    if ruta is None:
        raise CargaError(
            f"El archivo de la carga {carga_id} ya no está en disco. "
            "Hay que volver a subirlo para poder aplicarlo.")

    from django.contrib.auth import get_user_model
    usuario = (get_user_model().objects.filter(id=usuario_id).first()
               if usuario_id else None)
    if usuario is None:
        raise CargaError(
            "Aplicar una matriz sin autor no queda defendible: hace falta "
            "un usuario identificado.")

    # ── 1. Jerarquía, con el diff GUARDADO ──
    _, hecho_jerarquia = _aplicar_jerarquia(carga, usuario_id)

    # ── 2 y 3. Cifras y estructura (mismo importador) ── 4. Alertas ──
    estructura = _correr_importador("importar_matriz_pdl_alk", ruta,
                                    escribir=True, usuario=usuario.username)
    alertas = _correr_importador("importar_alerta_metas_pdl", ruta,
                                 escribir=True, usuario=usuario.username)

    _cerrar(carga, usuario_id, extra={"jerarquia": hecho_jerarquia,
                                     "estructura": estructura,
                                     "alertas": alertas})
    return carga, {**hecho_jerarquia,
                   "estructura_ok": estructura["ok"],
                   "alertas_ok": alertas["ok"]}
