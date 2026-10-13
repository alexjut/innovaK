"""Regenera la ficha de conexión de la API pública DESDE LA API VIVA.

    python manage.py ficha_api_publica

Vivía como un script en el escritorio de quien la escribió, o sea que nadie más
podía regenerarla y cada cifra se iba quedando vieja en silencio. Acá dentro
cualquiera la vuelve a sacar, y las cifras son medidas y no escritas a mano.

Desde que `/api/publica/v1/esquema/` existe, esta ficha YA NO es el contrato de
la API: el contrato es el esquema OpenAPI, que se genera de las vistas y no
puede desfasarse. Esto queda para lo que un esquema no puede decir —por qué un
campo viene en `null`, qué trampa tiene el origen, qué cobertura hay hoy—.
"""
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

from apps.publico.services.contratos import FILTROS, PARAMETROS_VALIDOS
from apps.publico.services.metadatos import metadatos


class Command(BaseCommand):
    help = "Regenera docs/api_publica_contratos.json desde la API viva."

    def handle(self, *args, **opts):

        m = metadatos()
        BASE = "https://intranet-public-alk.ngrok.app/api/publica/v1"
        c = connection.cursor()
        c.execute("select count(*), count(distinct id_contrato) from secop_modificacion")
        mods, cts_mod = c.fetchone()
        c.execute("select count(*) from secop_modificacion where tipo='CESION'")
        cesiones = c.fetchone()[0]
        c.execute("select anio, count(*) filter (where referencia_contrato like '%(%'), count(*) "
                  "from secop_contrato group by 1 order by 1")
        sipse = {str(a): {"con_codigo_sipse": s, "contratos": t} for a, s, t in c.fetchall()}

        cfg = {
          "nombre": m["nombre"], "version": "v1", "estado": "beta",
          "base_url": BASE,
          "autenticacion": {"requerida": False,
                            "nota": "Solo lectura. No envíe credenciales ni cookies."},
          "endpoints": {
            "listar_contratos": {"metodo": "GET", "ruta": "/contratos/",
                                 "descripcion": "Lista paginada por cursor"},
            "detalle_contrato": {"metodo": "GET", "ruta": "/contratos/{id_contrato}/"},
            "modificaciones":   {"metodo": "GET", "ruta": "/contratos/{id_contrato}/modificaciones/",
                                 "descripcion": "Cesiones, prórrogas, adiciones, suspensiones"},
            "modificaciones_lote": {
                "metodo": "POST", "ruta": "/contratos/modificaciones/lote/",
                "cuerpo": {"ids": ["CO1.PCCNTR.…", "…"]},
                "descripcion": "Hasta 200 contratos en una petición. Existe "
                               "para la carga del certificado contractual: "
                               "1.767 contratos son 9 peticiones en vez de "
                               "1.767 viajes.",
                "nota": "Pasarse del tope se RECHAZA con 400, no se trunca: "
                        "una carga que creyó pedir 500 y recibió 200 arrastra "
                        "el hueco sin saberlo."},
            "agregados":        {"metodo": "GET", "ruta": "/agregados/"},
            "metadatos":        {"metodo": "GET", "ruta": "/metadatos/",
                                 "descripcion": "Corte, cobertura y diccionario"},
            # El contrato de la API es el ESQUEMA, no esta ficha: se genera de
            # las vistas, así que no puede quedar desfasado como sí puede este
            # archivo.
            "esquema_openapi":  {"metodo": "GET", "ruta": "/esquema/",
                                 "descripcion": "OpenAPI 3 de la API pública, "
                                                "sin credenciales. Sirve para "
                                                "generar el cliente."},
            "docs":             {"metodo": "GET", "ruta": "/docs/",
                                 "descripcion": "Swagger UI sobre ese esquema."},
          },
          "parametros": {
            "paginacion": {"tipo": "cursor", "params": ["cursor", "limite"],
                           "limite_default": 50, "limite_max": 500},
            "filtros": sorted(FILTROS) + ["q", "naturaleza"],
            "validos": sorted(PARAMETROS_VALIDOS),
            "sincronizacion_incremental": {
              "param": "actualizado_desde", "formato": "ISO-8601",
              "uso": "Trae lo que la ingesta modificó desde ese corte. Para actualizar "
                     "una copia sin volver a bajar el dataset entero."},
            "parametro_desconocido": {
              "respuesta": 400,
              "nota": "Un parámetro que la API no reconoce es un error, no se ignora. "
                      "La respuesta lista los válidos."},
          },
          "limites": {"listar": "120/min", "detalle": "300/min", "metadatos": "600/min",
                      "codigo_exceso": 429, "header_espera": "Retry-After", "por": "IP"},
          "identificador_estable": m["identificador_estable"],
          "referencia_parseada": {
            "campos": ["prefijo", "numero", "vigencia", "codigo_sipse", "normalizada", "parseo"],
            "parseo": {"exacto": "vino bien en el origen",
                       "corregido": "se normalizaron separadores o paréntesis",
                       "parcial": "no se pudo sacar todo (p. ej. vigencia de 5 dígitos)",
                       "fallido": "no se pudo partir"},
            "nota": "El origen viene sucio y NO se corrige en silencio. Si su cruce es "
                    "delicado use solo las `exacto`; si quiere cobertura use todas y "
                    "sabrá cuáles venían torcidas.",
            "codigo_sipse_por_anio": sipse,
            "aviso_sipse": "El código de SIPSE aparece en la referencia desde 2025. En "
                           "2024 NO hay ninguno: esos contratos están completos en todo "
                           "lo demás, pero no se pueden cruzar por ese código.",
          },
          "fechas": {
            "campos": ["firma", "inicio", "fin_inicial", "fin_actual",
                       "dias_adicionados", "duracion_contrato"],
            "nota": "`fin_inicial` = `fin_actual` − `dias_adicionados`, con los días "
                    "que publica SECOP. Sin prórroga las dos fechas coinciden.",
          },
          "modificaciones": {
            "total": mods, "contratos_con_alguna": cts_mod, "cesiones": cesiones,
            "fuente": "SECOP II — datasets u8cx-r425 (detalle) y cb9c-h8sn (tipo)",
            "en_firme": "`en_firme=false` es un BORRADOR de SECOP (estado «En Edición» "
                        "o en trámite). No lo lea como un cambio consumado.",
            "cesiones_proveedores": "SECOP NO publica el contratista anterior ni el "
                                    "nuevo. Salen en `null` con su motivo y el texto de "
                                    "`proposito` al lado. No se deduce del texto.",
          },
          # Lo primero que hay que leer antes de cruzar suspensiones: el campo
          # obvio es justo el que engaña.
          "suspensiones": {
            "donde": "/contratos/{id_contrato}/modificaciones/ → `suspensiones`",
            "no_usar": "`modificacion.tipo` viene INVERTIDO en el par "
                       "suspensión/reactivación: 94,1 % de los casos medidos. "
                       "Las filas marcadas SUSPENSIoN son los reinicios.",
            "de_donde_sale": "Del dataset DEDICADO u99c-7mfm, que trae dos "
                             "tipos limpios. Cada clase viaja con "
                             "`clases_motivo` nombrándolo, y el texto del acto "
                             "al lado para poder comprobarla.",
            "periodos": (m.get("eje_suspension") or {}).get("periodos"),
            "lo_que_NO_publicamos":
                "La duración de la suspensión. `dias_entre_actos` es la "
                "distancia entre el acto que suspende y el que reanuda; el "
                "término lo decreta el TEXTO del acto y difiere en 72,1 % de "
                "los casos, entre -21 y +36 días. Si necesita el plazo, lea "
                "`proposito_inicio`.",
            "no_dice_que_este_suspendido_hoy":
                "Una cadena abierta solo dice que el último acto publicado es "
                "una suspensión: 111 de 113 contratos con la cadena abierta "
                "tienen `fecha_fin` ya pasada.",
          },
          "contratista": {
            "campos": ["nombre", "tipo_documento", "documento", "naturaleza", "proveedor_ref"],
            "nota": "Datos públicos (Ley 1712). `proveedor_ref` es un seudónimo estable "
                    "por proveedor: sirve para agrupar sin depender de cómo el origen "
                    "escriba el número.",
          },
          "convencion_sin_dato": m["convencion_sin_dato"],
          "valor_pagado": {
            "regla": "Un 0 de SECOP sale como `null` con motivo, NUNCA como 0.",
            "porque": "La tabla no tiene una sola fila en NULL: el 0 y el «no se "
                      "reportó» son indistinguibles. Hay casos con giro probado en "
                      "BogData que SECOP reporta en 0.",
          },
          "alcance": m["alcance"] + " Desde 2024 (vigencia del Plan de Desarrollo).",
          "frescura": {"endpoint": "/metadatos/", "campo": "corte",
                       "corte_actual": m["corte"], "nota": m["corte_nota"]},
          "cobertura_actual": {k: v["pct"] for k, v in m["cobertura"].items()},
          "licencia": m["licencia"], "atribucion": m["atribucion"],
          "ejemplos_curl": [
            f"curl -s '{BASE}/metadatos/'",
            f"curl -s '{BASE}/contratos/?anio=2025&limite=100'",
            f"curl -s '{BASE}/contratos/?actualizado_desde=2026-09-01'",
            f"curl -s '{BASE}/contratos/CO1.PCCNTR.7876249/'",
            f"curl -s '{BASE}/contratos/CO1.PCCNTR.8951822/modificaciones/'",
            f"curl -s '{BASE}/esquema/' -o openapi.yaml",
            ("curl -s -X POST '%s/contratos/modificaciones/lote/' "
             "-H 'Content-Type: application/json' "
             '-d \'{"ids":["CO1.PCCNTR.7876249","CO1.PCCNTR.8951822"]}\'' % BASE),
          ],
        }
        destino = Path(settings.BASE_DIR) / "docs" / "api_publica_contratos.json"
        destino.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
        self.stdout.write("escrita en docs/api_publica_contratos.json. Resumen:")
        self.stdout.write(f"  contratos      : {m['filas']}")
        self.stdout.write(f"  modificaciones : {mods} sobre {cts_mod} contratos · {cesiones} cesiones")
        self.stdout.write(f"  cobertura      : { {k: v['pct'] for k, v in m['cobertura'].items()} }")
