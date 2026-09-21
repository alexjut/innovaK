"""Partir la referencia del contrato en sus pedazos: prefijo, número, vigencia, SIPSE.

## Para qué

`CPS-797-2025 (134075)` lleva cuatro datos pegados en un texto, y quien consume
los necesita por separado para cruzar contra sus propios sistemas — el código
entre paréntesis es el de SIPSE, que es por donde la Alcaldía lo reconoce.
Hoy hay 1.229 referencias que lo traen.

## Por qué el parser es TOLERANTE y no estricto

Porque el origen viene sucio y no lo podemos arreglar: son datos de SECOP tal
como los escribió una persona. Medido sobre las 3.169 referencias, 34 no pasan
un patrón estricto, y casi todas por errores de tecleo recuperables:

    CPS 103-2024          espacio en vez de guión
    CPS- 270-2024         espacio después del guión
    CPS-005-2024.         punto al final
    CPS-425.2024          punto en vez de guión
    CPS-712.-2024         punto Y guión
    CPS-1195-2025 (146874 paréntesis sin cerrar
    CPS-857-2026 ((156167))  paréntesis duplicados
    CPS-1028-2025 ( 142595)  espacios dentro del paréntesis
    CPS-593-2026- (147565)   guión de más
    054-2024              sin prefijo
    FDLK-CCV-556-2024     prefijo compuesto

Rechazarlas dejaría 34 contratos sin poder cruzarse por un espacio de más, que
es exactamente el tipo de pérdida que no se justifica. Pero tampoco se puede
corregir en silencio: cada referencia dice CÓMO se leyó.

    exacto     salió tal cual, sin tocar nada
    corregido  hubo que normalizar separadores o paréntesis
    parcial    se pudo sacar algo, pero no todo
    fallido    no se pudo

Así quien consume decide: si su cruce es delicado, usa solo las `exacto`; si
quiere cobertura, usa todas y sabe cuáles venían torcidas.

## Lo que NO se inventa

`CPS-1070-20224` tiene una vigencia de cinco dígitos. No se adivina que quiso
decir 2024 ni 2022: sale `parcial`, con prefijo y número, y la vigencia en
`null`. Adivinar un año es inventar un dato que alguien va a cruzar.
"""
from __future__ import annotations

import re

#: El código de SIPSE entre paréntesis, tolerando paréntesis de más y espacios
#: adentro: `(134075)`, `( 142595)`, `((156167))`, `(146874` sin cerrar.
_SIPSE = re.compile(r"\(+\s*(\d+)\s*\)*")

#: PREFIJO-NUMERO-VIGENCIA ya normalizado. El prefijo admite guiones internos
#: (`FDLK-CCV`) y puede faltar del todo (`054-2024`).
_PARTES = re.compile(
    r"^(?:(?P<prefijo>[A-ZÑ]+(?:-[A-ZÑ]+)*)-)?(?P<numero>\d+)-(?P<vigencia>\d+)$")


def _normalizar(texto: str) -> str:
    """Deja la referencia en forma canónica sin adivinar contenido.

    Solo toca SEPARADORES y espacios: nunca dígitos ni letras. Un punto entre
    dos números es un guión mal tecleado; un punto al final es basura.
    """
    t = texto.strip().upper()
    t = t.rstrip(". ")                      # 'CPS-005-2024.'
    t = re.sub(r"\s*[-.]\s*", "-", t)       # 'CPS- 270', 'CPS-425.2024', 'CPS-712.-2024'
    t = re.sub(r"\s+", "-", t)              # 'CPS 103-2024'
    t = re.sub(r"-{2,}", "-", t)            # 'CPS-593-2026--'
    return t.strip("-")


def parsear(referencia: str | None) -> dict:
    """Parte una referencia. Siempre devuelve un dict; nunca lanza."""
    original = (referencia or "").strip()
    vacio = {
        "original": original or None,
        "prefijo": None, "numero": None, "vigencia": None,
        "codigo_sipse": None, "normalizada": None, "parseo": "fallido",
    }
    if not original:
        return vacio

    # 1. El código de SIPSE sale primero, para que sus paréntesis no estorben.
    sipse = None
    m = _SIPSE.search(original)
    resto = original
    if m:
        sipse = m.group(1)
        resto = original[:m.start()] + original[m.end():]

    # 2. Separadores en forma canónica.
    limpio = _normalizar(resto)
    partes = _PARTES.match(limpio)
    if not partes:
        return {**vacio, "codigo_sipse": sipse,
                "parseo": "parcial" if sipse else "fallido"}

    prefijo = partes.group("prefijo")
    numero = int(partes.group("numero"))
    vig_txt = partes.group("vigencia")

    # 3. La vigencia son cuatro dígitos. Ni tres ni cinco: no se adivina.
    vigencia = int(vig_txt) if len(vig_txt) == 4 else None

    normalizada = "-".join(x for x in (prefijo, str(numero), vig_txt) if x)
    # `exacto` = la original ya venía en forma canónica, sin contar el SIPSE.
    canonica = f"{normalizada} ({sipse})" if sipse else normalizada
    exacto = original.upper() == canonica

    return {
        "original": original,
        "prefijo": prefijo,
        "numero": numero,
        "vigencia": vigencia,
        "codigo_sipse": sipse,
        "normalizada": normalizada,
        "parseo": ("exacto" if exacto and vigencia
                   else "parcial" if vigencia is None
                   else "corregido"),
    }
