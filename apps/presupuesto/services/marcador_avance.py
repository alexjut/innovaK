"""Marcador de trazabilidad de `presu_avance_ind_periodo.observaciones`.

Cinco módulos escriben avance de KPI a partir de un hecho suyo —una entrega, una
captura, un acto de festival, un contrato de obra— y necesitan poder volver a
encontrar ESA fila para no duplicarla al revalidar y para borrarla al revertir.
Como la tabla no tiene columna de referencia externa, la referencia se guarda
dentro del texto de `observaciones`.

## Por qué existe este archivo

El idioma era `entrega_beca=11` buscado con `observaciones__contains`, o sea un
`LIKE '%entrega_beca=1%'`. **Ese `LIKE` empareja por prefijo**: buscar la fila 1
encuentra la 11, la 19 y la 100. Las consecuencias son las dos peores posibles y
ninguna deja rastro:

- al validar, la fila 1 se cree ya sincronizada porque existe la de la 11, y su
  avance **nunca se suma**;
- al revertir, borrar la 1 **borra también la de la 11**.

Delimitar lo cierra sin tocar la base: `[entrega_beca=1]` no está contenido en
`[entrega_beca=11]` porque el corchete de cierre no coincide. El costo es un
`LIKE` igual de barato sobre una tabla que hoy tiene 7 filas.

Estaba copiado cinco veces con cinco redacciones distintas, que es justo cómo
un defecto sobrevive a que lo arreglen en un solo sitio. Acá vive una vez.

## Formato

    [<clave>=<valor>]  seguido, opcionalmente, de texto para humanos

    [entrega_beca=11] metas=23771,23772
    [captura=11] tipo=CULTURA_ORG
    [festival=7][acto=90]
    [infra_contrato=103] unidades terminadas (seguimiento infraestructura)

El valor va tal cual: son ids enteros. No metas texto libre en la clave ni en el
valor — para eso está la nota, que nadie busca.

## Filas anteriores al 2026-08-12

Las 6 filas con marcador viejo se migraron **explícitamente** al formato nuevo
(`apps/presupuesto/scripts/003_marcador_avance_delimitado.sql`) en vez de
enseñarle al buscador a entender los dos formatos. El motivo: tolerar el
formato viejo obliga a conservar para siempre la búsqueda ambigua que es
exactamente el defecto que se está cerrando, y a cambio de eso solo se ahorra
un UPDATE de 6 filas sobre una tabla de 7. El script debe correr ANTES de
desplegar este código; si no, el recálculo de infraestructura no reconocería
sus filas viejas y crearía duplicados que el KPI sumaría dos veces.
"""
from __future__ import annotations


def marcador(clave: str, valor) -> str:
    """`("entrega_beca", 11)` → `"[entrega_beca=11]"`.

    Es a la vez lo que se ESCRIBE en `observaciones` y lo que se BUSCA con
    `observaciones__contains`. Que sean la misma cadena es el punto: si el que
    escribe y el que busca se construyen por separado, vuelven a divergir.
    """
    clave = (clave or "").strip()
    if not clave:
        raise ValueError("marcador: la clave es obligatoria")
    if valor is None or str(valor).strip() == "":
        raise ValueError(f"marcador: el valor de '{clave}' es obligatorio")
    return f"[{clave}={valor}]"


def observaciones(marcadores: str, nota: str = "") -> str:
    """Une los marcadores con la nota legible: `"[a=1] texto"`.

    La nota va DESPUÉS y separada por un espacio, para que el marcador quede
    siempre al principio y se pueda leer de un vistazo en la tabla.
    """
    nota = (nota or "").strip()
    return f"{marcadores} {nota}".strip() if nota else marcadores
