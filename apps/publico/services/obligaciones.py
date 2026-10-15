"""Las obligaciones específicas de un contrato, para la certificación laboral.

Responde la pregunta que bloqueaba a quien consume esta API: la lista numerada
de obligaciones, como lista y no como párrafo, porque ese documento las imprime
una por una y tiene efectos para la persona.

## De dónde salen, y de dónde NO

Del **estudio previo** del proceso, que SECOP publica en PDF. No del objeto
contractual —que es un párrafo—, no de contratos parecidos, y no completadas
con nada: lo pidieron así por escrito y es la única forma defendible en un
documento con efectos jurídicos.

Cada obligación viaja con el archivo del que salió, su fecha de carga y su URL,
para que cualquiera pueda abrir el PDF y comprobarla.

## Cuándo la lista va vacía, y por qué

Siempre con su motivo. Los cuatro casos medidos:

    sin_seccion         el estudio previo no tiene una sección de obligaciones
                        específicas del contratista (pasa en los convenios)
    lista_incompleta    la hay, pero el PDF perdió la numeración a mitad y
                        leeríamos 5 de 8. Publicar una lista a medias en una
                        certificación es peor que no publicarla: quien la lee
                        no tiene forma de notar que faltan tres
    calidad_baja        el texto del PDF viene con palabras partidas y se
                        imprimirían así
    sin_estudio_previo  no hay estudio previo publicado para ese proceso

## El recorte que hay que decir primero

**De 2020 a 2023 no hay ninguna.** De esas vigencias solo se publicó el
expediente post-contractual —actas de cierre, liquidaciones, certificados—, así
que no es que no hayamos podido leerlo: no está publicado. Medido el 2026-10-15:

    2024   1.031 de 1.135 contratos con estudio previo publicado  (90,8 %)
    2025   1.012 de 1.184                                         (85,5 %)
    2026     720 de   872                                         (82,6 %)
    2020-2023   0 de 2.347                                        ( 0,0 %)

Y de los que sí tienen estudio previo, la lista se lee en el 88,7 % (medido
sobre los primeros 150 documentos procesados, 8,3 obligaciones por documento).
"""
from django.db import connection

MOTIVOS = {
    "sin_estudio_previo": (
        "No hay un estudio previo publicado para el proceso de este contrato. "
        "De 2020 a 2023 no hay ninguno: de esas vigencias SECOP solo publicó el "
        "expediente posterior al contrato."),
    "pendiente": (
        "El estudio previo está publicado pero todavía no se ha leído. La "
        "lectura corre de noche; no se descarga durante la consulta."),
    "sin_seccion": (
        "El estudio previo no trae una sección de obligaciones específicas del "
        "contratista. Pasa en los convenios interadministrativos, que reparten "
        "compromisos entre las partes en vez de listar obligaciones."),
    "lista_incompleta": (
        "La sección existe pero el PDF perdió la numeración a mitad de la "
        "lista, así que solo se podría entregar una parte. No se entrega: una "
        "lista con 5 de 8 obligaciones en una certificación laboral es peor que "
        "ninguna, porque quien la lee no puede notar que faltan tres. El texto "
        "de la sección queda en `seccion_texto` para transcribirla a mano."),
    "calidad_baja": (
        "El texto extraído del PDF trae palabras partidas —el generador coloca "
        "cada letra aparte— y se imprimirían así en el certificado."),
    "sin_texto": (
        "El PDF no tiene capa de texto: es una imagen escaneada."),
    "descarga_fallo": (
        "El archivo está en el índice de SECOP pero no se pudo descargar."),
    "no_es_pdf": (
        "Lo que respondió la URL de descarga no es un PDF."),
    "error": (
        "La lectura del PDF falló por un motivo no previsto; quedó anotado."),
}

_SQL = """
    SELECT d.id, d.proceso, d.extraccion_estado, d.extraccion_motivo,
           d.nombre_archivo, d.fecha_carga, d.url_descarga, d.paginas,
           d.calidad_pct, d.seccion_encabezado, d.extraccion_fecha,
           d.seccion_texto
    FROM secop_documento d
    JOIN (
        SELECT proceso, MAX(COALESCE(fecha_carga, '1900-01-01'::timestamptz)) f
        FROM secop_documento
        WHERE clase = 'estudio_previo' AND extension = 'pdf'
        GROUP BY proceso
    ) u ON u.proceso = d.proceso
       AND COALESCE(d.fecha_carga, '1900-01-01'::timestamptz) = u.f
    WHERE d.clase = 'estudio_previo' AND d.extension = 'pdf'
      AND d.proceso = ANY(%s)
"""


def _vacio(motivo_clave, proceso=None, extra=None):
    salida = {
        "obligaciones": [],
        "obligaciones_motivo": MOTIVOS.get(motivo_clave, motivo_clave),
        "motivo_codigo": motivo_clave,
        "documento": None,
        "proceso": proceso,
    }
    if extra:
        salida.update(extra)
    return salida


def por_contrato(ids: list[str]) -> dict[str, dict]:
    """Devuelve SIEMPRE una entrada por cada contrato pedido, aunque esté vacía.

    Un contrato ausente del resultado se lee como «no hay dato» cuando lo que
    pasa es que no se preguntó. Esa confusión ya arruinó dos diagnósticos en
    este proyecto.
    """
    if not ids:
        return {}
    ids = list(dict.fromkeys(ids))
    with connection.cursor() as cur:
        cur.execute("""SELECT id_contrato, proceso_de_compra
                       FROM secop_contrato WHERE id_contrato = ANY(%s)""", [ids])
        proceso_de = {r[0]: r[1] for r in cur.fetchall()}
        procesos = sorted({p for p in proceso_de.values() if p})

        docs: dict[str, dict] = {}
        obligaciones: dict[int, list] = {}
        if procesos:
            cur.execute(_SQL, [procesos])
            for (did, proc, estado, motivo, nombre, fcarga, url, paginas,
                 calidad, enc, fextrac, cruda) in cur.fetchall():
                docs[proc] = {
                    "documento_id": did, "estado": estado, "motivo": motivo,
                    "nombre": nombre, "fecha_carga": fcarga, "url": url,
                    "paginas": paginas, "calidad_pct": calidad,
                    "encabezado": enc, "leido": fextrac, "seccion": cruda,
                }
            if docs:
                cur.execute("""
                    SELECT documento_id, numero, descripcion, metodo
                    FROM secop_obligacion
                    WHERE documento_id = ANY(%s)
                    ORDER BY documento_id, numero
                """, [[d["documento_id"] for d in docs.values()]])
                for did, numero, desc, metodo in cur.fetchall():
                    obligaciones.setdefault(did, []).append(
                        {"numero": numero, "descripcion": desc,
                         "metodo": metodo})

    salida: dict[str, dict] = {}
    for id_ct in ids:
        proc = proceso_de.get(id_ct)
        if not proc or proc not in docs:
            salida[id_ct] = _vacio("sin_estudio_previo", proc)
            continue
        d = docs[proc]
        ficha = {
            "nombre": d["nombre"],
            "fecha_carga": d["fecha_carga"].isoformat() if d["fecha_carga"] else None,
            "url_descarga": d["url"],
            "paginas": d["paginas"],
            "encabezado_seccion": d["encabezado"],
            "leido": d["leido"].isoformat() if d["leido"] else None,
            # La métrica con la que se decidió publicar o no. Viaja para que la
            # decisión sea auditable y no una caja negra.
            "calidad_texto_pct": (float(d["calidad_pct"])
                                  if d["calidad_pct"] is not None else None),
        }
        items = obligaciones.get(d["documento_id"], [])
        if d["estado"] == "ok" and items:
            salida[id_ct] = {
                "obligaciones": items,
                "obligaciones_motivo": None,
                "motivo_codigo": None,
                "documento": ficha,
                "proceso": proc,
            }
        else:
            clave = d["estado"] if d["estado"] != "ok" else "error"
            # Cuando la lista no se publica, el texto de la sección SÍ: es lo
            # que permite transcribirla a mano sin volver a buscar el PDF.
            salida[id_ct] = _vacio(clave, proc, {
                "documento": ficha,
                "detalle": d["motivo"],
                "seccion_texto": d["seccion"],
            })
    return salida


def cobertura() -> dict:
    """Cuántos contratos tienen sus obligaciones, por año y medido en vivo."""
    with connection.cursor() as cur:
        cur.execute("""
            WITH ultimo AS (
                SELECT d.proceso, d.id, d.extraccion_estado
                FROM secop_documento d
                JOIN (SELECT proceso,
                             MAX(COALESCE(fecha_carga,'1900-01-01'::timestamptz)) f
                      FROM secop_documento
                      WHERE clase='estudio_previo' AND extension='pdf'
                      GROUP BY proceso) u
                  ON u.proceso = d.proceso
                 AND COALESCE(d.fecha_carga,'1900-01-01'::timestamptz) = u.f
                WHERE d.clase='estudio_previo' AND d.extension='pdf'
            )
            SELECT s.anio,
                   COUNT(*)                                        AS contratos,
                   COUNT(ultimo.id)                                AS con_doc,
                   COUNT(*) FILTER (WHERE ultimo.extraccion_estado='ok') AS con_lista
            FROM secop_contrato s
            LEFT JOIN ultimo ON ultimo.proceso = s.proceso_de_compra
            GROUP BY s.anio ORDER BY s.anio
        """)
        por_anio = [{"anio": a, "contratos": n, "con_estudio_previo": d,
                     "con_obligaciones": o,
                     "pct_con_obligaciones": (round(100.0 * o / n, 1) if n else None)}
                    for a, n, d, o in cur.fetchall()]
        cur.execute("""
            SELECT extraccion_estado, COUNT(*) FROM secop_documento
            WHERE clase='estudio_previo' GROUP BY 1 ORDER BY 2 DESC
        """)
        estados = dict(cur.fetchall())
        cur.execute("SELECT COUNT(*) FROM secop_obligacion")
        total = cur.fetchone()[0]
    return {
        "por_anio": por_anio,
        "estado_de_la_lectura": estados,
        "obligaciones_publicadas": total,
        "recorte_2020_2023": (
            "De 2020 a 2023 no hay ninguna obligación publicable: de esas "
            "vigencias SECOP solo publicó el expediente posterior al contrato "
            "—actas de cierre, liquidaciones, certificados—, 2,6 archivos por "
            "proceso contra 51 en 2025-2026. No es que no hayamos podido "
            "leerlo: el estudio previo de esos años no está publicado."),
        "metodo": (
            "Lista numerada de la sección «obligaciones específicas» del "
            "estudio previo más reciente del proceso. Los números tienen que ir "
            "de 1 en 1; donde se rompe la secuencia termina la lista. Si sobra "
            "prosa después del último ítem, la lista se considera incompleta y "
            "NO se publica."),
        "fuente": "SECOP II — nbae-kzan y dmgg-8hin (archivos del proceso)",
    }
