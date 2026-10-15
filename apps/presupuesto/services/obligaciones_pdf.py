"""Leer las obligaciones específicas del estudio previo, o declarar que no.

Lo delicado de este módulo no es extraer texto: es **negarse a entregar una
lista a medias**. Lo que sale de acá se imprime numerado en la certificación
laboral de una persona, así que una lista con 5 de 8 obligaciones es peor que
ninguna — quien la lee no tiene forma de notar que faltan tres.

## Cómo se encuentra la sección

Anclada al principio de una línea, con su número de sección opcional
(`10.5 OBLIGACIONES ESPECÍFICAS`) y tolerando espacios de más. Las tres cosas
costaron un diagnóstico falso cada una, medido sobre seis documentos reales:

1. **Buscada como subcadena**, el encabezado se encontraba en la frase en prosa
   «…garantizar el objeto del contrato y las obligaciones específicas
   descritas…», que aparece páginas antes de la sección, y desde ahí no había
   ninguna lista que leer.
2. **Exigiendo un espacio entre palabras**, un documento que trae
   `10.5 OBLIGACIONES  ESPECÍFICAS` con dos quedaba como «sin sección» teniendo
   la lista completa adentro.
3. **Con el número de lista como prefijo válido**, la obligación
   «3 . Garantizar técnicamente el proceso…» se leía como el encabezado de
   garantías y la lista se cortaba en el 2.

## Cómo se sabe dónde termina

Por dos reglas, y las dos son auto-validantes:

- **Los números van de 1 en 1.** Donde se rompe la secuencia, termina la lista.
  Así no se trague la lista siguiente, que vuelve a empezar en 1.
- **Los cierres se exigen como encabezado de línea y son específicos.** Con
  «SUPERVISI» en la lista, la obligación 1 se cortaba a sí misma, porque su
  propio texto dice «apoyo a la supervisión».

## La compuerta de calidad

El texto extraído de algunos PDF trae palabras partidas —«verac idad»,
«docume ntos»— porque el generador coloca cada glifo aparte. Eso se imprimiría
así en el certificado. Se mide con el porcentaje de tokens de UNA letra que no
son «y a o e u» (que sí son palabras del español): los estudios previos de CPS
dan 1,7-2,2 % y un convenio de 40 páginas dio 4,6 %.

La primera versión de esa métrica contaba todas las letras sueltas y daba 10 %,
lo que me hizo concluir que el texto era inservible y casi descartar el frente
entero. Era falso: 528 de 668 eran esas cinco palabras.
"""
import re

#: Cómo se llama la sección. Se prueban en orden y gana la que aparezca primero.
ENCABEZADOS = (
    "OBLIGACIONES ESPECÍFICAS DEL CONTRATISTA",
    "OBLIGACIONES ESPECIFICAS DEL CONTRATISTA",
    "OBLIGACIONES ESPECÍFICAS",
    "OBLIGACIONES ESPECIFICAS",
    "OBLIGACIONES DEL CONTRATISTA",
)

#: Lo que cierra la sección: encabezados de la plantilla, nunca palabras
#: sueltas. Cada entrada tiene que ser específica, porque muchas obligaciones
#: EMPIEZAN con esas palabras.
CIERRES = (
    "OBLIGACIONES DE LA SECRETAR", "OBLIGACIONES DEL FONDO",
    "OBLIGACIONES GENERALES", "COMPROMISOS DE LA SECRETAR",
    "OBLIGACIONES DE LA ENTIDAD",
    "SUPERVISIÓN DEL CONTRATO", "SUPERVISION DEL CONTRATO",
    "VALOR DEL CONTRATO", "FORMA DE PAGO", "PLAZO DE EJECUCI",
    "GARANTÍAS", "GARANTIAS", "GARANTÍA ÚNICA", "GARANTIA UNICA",
    "LIQUIDACIÓN DEL CONTRATO", "LIQUIDACION DEL CONTRATO",
    "PERFIL REQUERIDO", "IDONEIDAD Y EXPERIENCIA",
    "ANÁLISIS DEL SECTOR", "ANALISIS DEL SECTOR",
    "ANÁLISIS DE RIESGOS", "ANALISIS DE RIESGOS", "MATRIZ DE RIESGOS",
)

#: Un ítem de la lista: número, separador y texto. El origen escribe «1 .» con
#: el punto separado, así que el espacio antes del punto es opcional.
ITEM = re.compile(r"(?m)^[^\S\n]*(\d{1,2})[^\S\n]*[.)\-][^\S\n]+(?=\S)")

#: Un número de sección —«10.6», «2.1»— que indica que empezó otro apartado.
SECCION_NUM = re.compile(r"(?m)^[^\S\n]*\d{1,2}\.\d{1,2}[.)]?\s")

#: Prefijo opcional de encabezado: SOLO un número de sección con punto adentro.
#: Un número de lista suelto no cuenta; ver el punto 3 del encabezado.
_PREFIJO = r"(?m)^[^\S\n]*(?:\d{1,2}(?:\.\d{1,2})+[.)]?[^\S\n]+)?"
_PREFIJO_CIERRE = r"(?m)^[^\S\n]*(?:\d{1,2}\.\d{1,2}[.)]?[^\S\n]+)?"

#: Las cinco palabras de una letra del español. Sin excluirlas, la métrica de
#: calidad da 10 % en un texto limpio.
_UNA_LETRA_LEGITIMA = {"a", "y", "e", "o", "u"}

_PALABRA = re.compile(r"[A-Za-zÁÉÍÓÚÑÜáéíóúñü]+")

#: Umbral de la compuerta. Por encima de esto no se publica lista.
CALIDAD_MAXIMA_PCT = 3.0

#: Si después del último ítem sobra más texto que esto, la lista está incompleta.
COLA_MAXIMA = 160

#: Largo a partir del cual una última obligación mucho mayor que las demás se
#: considera una que absorbió texto sin numerar.
#:
#: Calibrado contra las listas ya aceptadas, no a ojo: sobre 278 documentos
#: leídos, la última obligación NUNCA pasa de 1,8 veces la mediana de las demás
#: y su máximo absoluto es 488 caracteres. Las obligaciones tienen mediana 226,
#: p95 457 y máximo 913. Con 3 veces la mediana y piso de 600 no se rechaza
#: ninguna de las 278 que hoy están bien.
LARGO_SOSPECHOSO = 600

#: Menos obligaciones que esto es un parseo truncado, no una lista corta.
#:
#: Medido sobre 326 documentos leídos: el mínimo real son 5 obligaciones, y
#: NINGUNO tiene 3 o menos. La distribución se concentra en 8 y 9. Se deja el
#: piso en 4 para tener un margen por debajo de lo observado.
#:
#: Hace falta porque las otras dos reglas no ven este caso: con solo dos ítems
#: no hay mediana con la que comparar, y si la continuación sin número se
#: absorbe dentro del segundo, no sobra cola que medir.
MINIMO_OBLIGACIONES = 4


def _flex(frase: str) -> str:
    """El patrón de una frase tolerando espacios de más entre palabras."""
    return r"\s+".join(re.escape(p) for p in frase.split())


def _limpiar(t: str) -> str:
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{2,}", "\n", t)
    return t.strip()


def calidad_pct(texto: str) -> float:
    """Porcentaje de tokens de una letra que NO son palabras del español.

    Es la medida de lo roto que viene el texto. Cuanto más alto, más palabras
    partidas por la extracción.
    """
    toks = _PALABRA.findall(texto or "")
    if not toks:
        return 100.0
    sueltas = sum(1 for t in toks
                  if len(t) == 1 and t.lower() not in _UNA_LETRA_LEGITIMA)
    return round(100.0 * sueltas / len(toks), 2)


def extraer(texto: str) -> tuple[str | None, list[dict], str | None]:
    """`(encabezado, obligaciones, motivo)`. La lista va vacía si no se puede.

    Nunca lanza y nunca completa: cuando algo no cuadra devuelve lista vacía y
    el motivo, que es lo que el consumidor pidió por escrito —«si el dato no
    existe, preferimos el campo vacío»—.
    """
    if not texto:
        return None, [], "sin_texto"
    U = texto.upper()

    pos, enc, fin_enc = -1, None, None
    for e in ENCABEZADOS:
        m = re.search(_PREFIJO + _flex(e), U)
        if m and (pos < 0 or m.start() < pos):
            pos, enc, fin_enc = m.start(), e, m.end()
    if pos < 0:
        return None, [], "sin_seccion"

    cuerpo = texto[fin_enc:]
    CU = cuerpo.upper()
    fin = len(cuerpo)
    for c in CIERRES:
        m = re.search(_PREFIJO_CIERRE + _flex(c), CU)
        if m and m.start() < fin:
            fin = m.start()
    cuerpo = cuerpo[:fin]

    marcas = list(ITEM.finditer(cuerpo))
    items: list[dict] = []
    esperado = 1
    descartado = ""          # lo que se cortó del último ítem, en crudo
    for k, m in enumerate(marcas):
        if int(m.group(1)) != esperado:
            break
        sig = marcas[k + 1].start() if k + 1 < len(marcas) else len(cuerpo)
        crudo = cuerpo[m.end():sig]
        # El corte se busca sobre el CRUDO, no sobre el limpiado: mezclar un
        # largo ya limpiado con posiciones del crudo daba una cola equivocada
        # —el limpiado es más corto— y la lista a medias pasaba por completa.
        corte = SECCION_NUM.search(crudo)
        if corte:
            descartado = crudo[corte.start():]
            crudo = crudo[:corte.start()]
        else:
            descartado = ""
        trozo = _limpiar(crudo)
        if not trozo:
            break
        items.append({"numero": esperado, "descripcion": trozo})
        esperado += 1

    if not items:
        return enc, [], "seccion_sin_lista_numerada"

    # ¿Sobró prosa después del último ítem? Entonces la lista tiene más de los
    # que leímos: en un documento medido, tras la obligación 5 sigue «Gestionar
    # técnicamente la elaboración de respuestas…» sin número, porque el PDF lo
    # perdió. Son 8 y leeríamos 5.
    # Lo que se cortó del último ítem porque empezaba otra sección: si es
    # mucho, eran obligaciones que perdieron su número.
    cola = re.sub(r"[\s.·•\-]+", "", _limpiar(descartado))
    if len(cola) > COLA_MAXIMA:
        return enc, [], "lista_incompleta"

    # Y la otra forma del mismo problema: cuando la continuación sin número va
    # al FINAL del cuerpo, no sobra cola porque se absorbe dentro de la última
    # obligación, que queda desproporcionada. La regla de la cola solo la caza
    # si después viene un número de sección que la corte.
    #
    # Se exige que haya al menos tres para tener con qué comparar, y las dos
    # condiciones a la vez: mucho más larga que la mediana Y larga en términos
    # absolutos. Una obligación legítimamente larga entre obligaciones cortas no
    # basta para descartar la lista.
    if len(items) < MINIMO_OBLIGACIONES:
        return enc, [], "lista_incompleta"

    if len(items) >= 3:
        largos = sorted(len(i["descripcion"]) for i in items[:-1])
        mediana = largos[len(largos) // 2]
        ultimo_largo = len(items[-1]["descripcion"])
        if ultimo_largo > max(3 * mediana, LARGO_SOSPECHOSO):
            return enc, [], "lista_incompleta"
    return enc, items, None


def seccion_cruda(texto: str) -> str | None:
    """El texto de la sección, sin parsear. Es el respaldo auditable.

    Se guarda incluso cuando la lista no se publica: es lo que permite que
    alguien transcriba a mano en vez de volver a buscar el PDF.
    """
    if not texto:
        return None
    U = texto.upper()
    for e in ENCABEZADOS:
        m = re.search(_PREFIJO + _flex(e), U)
        if m:
            return _limpiar(texto[m.start():m.start() + 12000]) or None
    return None
