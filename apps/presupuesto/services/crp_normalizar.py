"""Normalizar el CRP de BogData: compromiso, proyecto y tipo de rubro.

Tres funciones puras, sin BD, porque son las que deciden a qué se engancha
cada fila del reporte — y equivocarse acá no da error: da un CRP colgado del
contrato de otro.
"""
from __future__ import annotations

import re

#: `351-2026`, `002-2026`, `1047-2025`. Con ceros a la izquierda. 1.914 filas.
_RE_GUION = re.compile(r"^(\d{1,5})\s*-\s*(\d{4})$")

#: `2024404`, `20241158`. Año pegado al consecutivo, sin separador. 571 filas.
#:
#: El año va PRIMERO y son cuatro dígitos: `2024404` es el 404 de 2024, no el
#: 2024 de 404. Se ancla el año a 20xx para no partir un número largo que no
#: lleve año — un `1234567` sin más no es «el 567 del año 1234».
_RE_PEGADO = re.compile(r"^(20\d{2})(\d{1,6})$")

#: `934 2025`, `939 2025`: el mismo formato del guion con un espacio. Son 4
#: filas y podrían ignorarse, pero dejarlas fuera significaría no enganchar
#: cuatro contratos reales por un carácter.
_RE_ESPACIO = re.compile(r"^(\d{1,5})\s+(\d{4})$")

#: `CPS-858-2025`. Trae el tipo por delante, como las referencias de SECOP.
_RE_CON_TIPO = re.compile(r"^[A-Z]+\s*-\s*(\d{1,5})\s*-\s*(\d{4})$", re.I)


def normalizar_numero_compromiso(raw) -> tuple[int | None, int | None]:
    """`'351-2026'` → `(351, 2026)`. Lo que no es un contrato → `(None, None)`.

    DEVUELVE NULOS EN VEZ DE ADIVINAR. En el archivo hay 45 filas `EDIL n
    FDLK` —honorarios de ediles, que no son contratos— y otras 95 en 23
    escrituras distintas: `EPS017`, `RES 541`, `149957-2025`, documentos SAP
    de 10 y 14 dígitos. Forzar un número para ellas colgaría el CRP del
    contrato equivocado, que es peor que dejarlo suelto: un vacío se ve y se
    corrige, un enganche falso se propaga.

    Los formatos que sí se aceptan salieron de medir el archivo completo, no
    de suponer (corte 2026-09-07, 2.630 filas):

        1.914  NNN-AAAA        351-2026, 002-2026
          571  AAAAnnn         2024404  (año pegado al consecutivo)
            4  NNN AAAA        934 2025 (espacio en vez de guion)
            1  CPS-NNN-AAAA    CPS-858-2025
        ─────
           45  EDIL n FDLK     → (None, None), a propósito
           95  otros           EPS017, RES 541, 149957-2025, SAP → (None, None)

    Los 140 que no parsean se cuentan aparte en `cargar_crp`: si la fuente
    cambia de formato, ese contador sube y `compromisos_sin_contrato` baja.
    """
    if raw is None:
        return (None, None)
    s = " ".join(str(raw).strip().split())
    if not s:
        return (None, None)

    for patron in (_RE_GUION, _RE_ESPACIO, _RE_CON_TIPO):
        m = patron.match(s)
        if m:
            return (int(m.group(1)), int(m.group(2)))

    m = _RE_PEGADO.match(s)
    if m:
        return (int(m.group(2)), int(m.group(1)))

    return (None, None)


#: Los rubros de inversión 2026 llevan el proyecto en `[15:19]` (0-based):
#: `O23011745992024271101000` → `2711`.
#:
#: LA ESPECIFICACIÓN DECÍA `[16:20]`, Y DA `7110`. Lo cazó el test que compara
#: el rubro contra el Elemento PEP —`PM/0008/0101/4599000**2711**`, que
#: termina en el mismo código— sobre las 876 filas de inversión del
#: archivo. Un offset corrido por uno no falla: engancha el CRP a un proyecto
#: que no existe, o peor, a otro que sí.
_LARGO_RUBRO_INVERSION = 24
_POS_PROYECTO = slice(15, 19)

#: `PM/0008/0101/4599000XXXX` → los últimos 4 dígitos son el proyecto.
_RE_PEP = re.compile(r"(\d{4})$")


def proyecto_de_rubro(rubro) -> str | None:
    """El código de proyecto del PDL que lleva el rubro, o `None`.

    Solo los rubros de INVERSIÓN lo llevan. Los de obligaciones por pagar
    (`O230689`, `O230690`, `O21900x` — 1.688 filas, el 64 % del archivo) y los
    de funcionamiento (`O21…`) no identifican proyecto: devuelven `None`, y
    cuando su contrato está registrado en innovaK el proyecto se recupera en
    `cargar_crp` cruzando `contrato_id` (23 filas en el corte 2026-09-07).
    """
    if not rubro:
        return None
    s = str(rubro).strip()
    if len(s) != _LARGO_RUBRO_INVERSION or not s.upper().startswith("O23011"):
        return None
    cod = s[_POS_PROYECTO]
    return cod if cod.isdigit() else None


def proyecto_de_pep(pep) -> str | None:
    """El proyecto según el Elemento PEP. Se usa para CONTRASTAR el rubro.

    Los dos tienen que coincidir. Cuando no, se reporta en vez de elegir uno:
    una discrepancia entre las dos vías significa que el rubro o el PEP están
    mal escritos en la fuente, y taparla con una preferencia arbitraria
    dejaría el CRP colgado del proyecto equivocado sin que nadie se entere.
    """
    if not pep:
        return None
    m = _RE_PEP.search(str(pep).strip())
    return m.group(1) if m else None


def tipo_de_rubro(rubro) -> str:
    """`inversion` | `obligacion_por_pagar` | `funcionamiento` | `desconocido`.

    Decide si la fila puede enganchar proyecto. Medido en el archivo del
    corte 2026-09-07: 876 de inversión, 1.688 de obligaciones por pagar
    (64 % de las filas, 59,6 % de la plata) y 66 de funcionamiento.

    Los `O219001`/`O219002` cuentan como obligación por pagar y NO como
    funcionamiento, aunque empiecen por `O21`: son reservas de gasto de
    funcionamiento de vigencias anteriores, y lo que decide el balde es si la
    fila puede identificar proyecto, no de qué bolsillo salió. Son 86 filas, y
    contarlas del otro lado es lo que daba los 152 de funcionamiento que decía
    esta línea.
    """
    if not rubro:
        return "desconocido"
    s = str(rubro).strip().upper()
    if s.startswith(("O230689", "O230690", "O219001", "O219002")):
        return "obligacion_por_pagar"
    if s.startswith("O23011"):
        return "inversion"
    if s.startswith("O21"):
        return "funcionamiento"
    return "desconocido"


#: Qué tipos de documento son persona jurídica. `NITC` es NIT de consorcio:
#: en el archivo lo lleva UN solo tercero que concentra $34.771 M (15,3 % del
#: neto), así que clasificarlo mal desplazaría una sexta parte de la plata.
_TIPOS_JURIDICA = {"NIT", "NITC"}


def es_persona_juridica(tipo_doc) -> bool | None:
    """`True` jurídica, `False` natural, `None` si el tipo no se reconoce.

    `None` y no `False`: el archivo trae un `HCM033` que no es ninguno de los
    dos conocidos, y contarlo como natural inventaría una clasificación.
    """
    if not tipo_doc:
        return None
    t = str(tipo_doc).strip().upper()
    if t in _TIPOS_JURIDICA:
        return True
    if t in {"CC", "TI", "CE", "PAS", "PA"}:
        return False
    return None
