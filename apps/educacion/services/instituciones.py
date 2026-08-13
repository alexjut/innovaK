"""Catálogo de instituciones: se llena por uso y se cuenta por vigencia.

## Dos responsabilidades

1. **Sincronizar** desde `entrega_beca`: dar de alta lo que aparezca en los
   cargues y todavía no exista. Sin coordenadas — ubicarlas es del área.
2. **Contar** beneficiarios por institución, por programa y por nivel, siempre
   con la vigencia adentro.

## Agrupa por CÓDIGO, nunca por nombre

El archivo del área trae `ADMINISTRACIÓN` y `ADMINISTRACION` en filas distintas
del mismo programa. Agrupar por nombre partiría ese programa en dos y duplicaría
el conteo de alumnos. El código es el identificador; el nombre es una etiqueta
que se corrige.

De ahí salen los tres casos que la sincronización reporta en vez de resolver
sola:

- **mismo código, nombre distinto** → manda el código, se conserva el nombre ya
  guardado y se avisa con los dos valores. Cambiarlo automáticamente haría que
  el último cargue le pisara el nombre corregido a mano por el área.
- **mismo nombre, códigos distintos** → probablemente un error del archivo. Se
  avisa, **sin fusionar**: fusionar dos instituciones por parecido de nombre es
  irreversible y el sistema no tiene con qué decidirlo.
- **código sin nombre** → se da de alta con el código como nombre provisional,
  para que exista y se pueda corregir, en vez de descartar la fila.

## El acumulado NO es la suma de las vigencias

Una persona con beneficio en 2025 y 2026 es UNA persona. Los conteos por
vigencia se calculan con `COUNT(DISTINCT persona)` **dentro** de cada año, y el
acumulado con su propio DISTINCT sobre todo el período. Es la misma trampa del
recálculo del avance (`jovenes_a_la_e/services/avance.py`); acá tampoco se
resuelve sumando.

## Habeas data

Todo lo que devuelve este servicio son **agregados**: conteos por institución,
programa y nivel. Nunca listados de personas identificadas — un mapa se proyecta
en reuniones y se captura en pantalla, y esa es una superficie de exposición
distinta a la de una ficha de detalle.
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.db.models import Count

from apps.educacion.models import InstitucionEducativa, ProgramaAcademico

logger = logging.getLogger(__name__)

#: Los niveles que son educación superior. `etdh` queda fuera por definición
#: legal (código SIET, sin título de superior). Se importa del lector del
#: cargue para no tener dos listas que puedan divergir.
from apps.jovenes_a_la_e.services.cargue_excel import (  # noqa: E402
    NIVELES_SUPERIOR, NIVEL_ETIQUETAS,
)

#: Un nivel `etdh` implica que la institución está en el SIET, no en el SNIES.
#: Es la única pista que trae el archivo sobre en qué registro está inscrita.
def tipo_registro_de(nivel: str | None) -> str:
    return "SIET" if nivel == "etdh" else "SNIES"


@transaction.atomic
def sincronizar_desde_entregas(*, aplicar: bool = False) -> dict:
    """Da de alta instituciones y programas que aparezcan en las entregas.

    Seco por defecto: sin `aplicar=True` solo informa qué crearía. Devuelve
    también los avisos de los tres casos ambiguos, que no resuelve sola.
    """
    from apps.jovenes_a_la_e.models import EntregaBeca

    filas = (EntregaBeca.objects
             .exclude(snies_ies__isnull=True).exclude(snies_ies="")
             .values("snies_ies", "institucion", "snies_programa",
                     "programa_academico", "nivel_formacion")
             .distinct())

    existentes = {i.codigo_snies: i for i in InstitucionEducativa.objects.all()}
    nombres_vistos: dict[str, str] = {}
    avisos: list[str] = []
    nuevas_inst: dict[str, dict] = {}
    nuevos_prog: dict[tuple, dict] = {}

    for f in filas:
        cod = (f["snies_ies"] or "").strip()
        if not cod:
            continue
        nombre = (f["institucion"] or "").strip() or f"Institución {cod}"
        nivel = f["nivel_formacion"]

        # Caso 1: mismo código, nombre distinto entre filas.
        previo = nombres_vistos.setdefault(cod, nombre)
        if previo != nombre:
            avisos.append(
                f"El código {cod} aparece con dos nombres: «{previo}» y «{nombre}». "
                "Manda el código; corrija el nombre desde la pantalla si hace falta.")

        inst = existentes.get(cod)
        if inst is None:
            nuevas_inst.setdefault(cod, {
                "codigo_snies": cod, "nombre": nombre,
                "tipo_registro": tipo_registro_de(nivel),
            })
        elif inst.nombre.strip() != nombre:
            # Caso 1 contra lo YA guardado: no se pisa. El área pudo corregirlo.
            avisos.append(
                f"«{inst.nombre}» ({cod}) llega en el archivo como «{nombre}». "
                "Se conservó el nombre guardado.")

        cod_prog = (f["snies_programa"] or "").strip()
        if cod_prog:
            nuevos_prog.setdefault((cod, cod_prog), {
                "codigo_snies": cod_prog,
                "nombre": (f["programa_academico"] or "").strip() or f"Programa {cod_prog}",
                "nivel_formacion": nivel,
            })

    # Caso 2: mismo nombre, códigos distintos. Se avisa, no se fusiona.
    por_nombre: dict[str, list[str]] = {}
    for cod, nombre in nombres_vistos.items():
        por_nombre.setdefault(nombre.upper(), []).append(cod)
    for nombre, codigos in por_nombre.items():
        if len(codigos) > 1:
            avisos.append(
                f"«{nombre}» aparece con {len(codigos)} códigos distintos "
                f"({', '.join(sorted(codigos))}). Probable error del archivo: "
                "reviselo, no se fusionan solas.")

    resultado = {
        "instituciones_nuevas": len(nuevas_inst),
        "programas_nuevos": 0,
        "avisos": avisos,
        "aplicado": bool(aplicar),
    }

    if not aplicar:
        # En seco se cuenta lo que DE VERDAD falta, no el total de pares: este
        # servicio lo llama un trabajo diario, y un ensayo que dice «69
        # programas nuevos» cuando ya existen los 69 vuelve ilegible la salida
        # y entrena a la gente a ignorarla. Los de instituciones que aún no
        # existen se cuentan enteros, porque ninguno de sus programas puede
        # estar todavía.
        ya = {(p.institucion.codigo_snies, p.codigo_snies)
              for p in ProgramaAcademico.objects.select_related("institucion")}
        resultado["programas_nuevos"] = sum(
            1 for clave in nuevos_prog if clave not in ya)
        return resultado

    for datos in nuevas_inst.values():
        existentes[datos["codigo_snies"]] = InstitucionEducativa.objects.create(**datos)

    creados = 0
    for (cod_inst, cod_prog), datos in nuevos_prog.items():
        inst = existentes.get(cod_inst)
        if inst is None:
            continue
        _, creado = ProgramaAcademico.objects.get_or_create(
            institucion=inst, codigo_snies=cod_prog, defaults=datos)
        creados += int(creado)
    resultado["programas_nuevos"] = creados
    return resultado


# ══════════════════════════════════════════════════════════════════════════
# Conteos — siempre agregados, siempre con la vigencia adentro
# ══════════════════════════════════════════════════════════════════════════

def _entregas(vigencia: int | None):
    from apps.jovenes_a_la_e.models import EntregaBeca

    qs = EntregaBeca.objects.filter(estado="validada").exclude(snies_ies__isnull=True)
    # `.order_by()` obligatorio: `EntregaBeca` trae `Meta.ordering`, y Django
    # mete esas columnas en el SELECT de un `.values(...).distinct()`. El
    # DISTINCT pasaría a ser sobre (documento, created_at, id) y contaría
    # MATRÍCULAS en vez de personas — justo la distinción que sostiene todo
    # este archivo. Se limpia en el origen para no depender de recordarlo en
    # cada consulta.
    qs = qs.order_by()
    return qs.filter(vigencia=vigencia) if vigencia else qs


def conteos_por_institucion(vigencia: int | None = None) -> dict[str, dict]:
    """`{codigo_ies: {personas, matriculas, programas}}`.

    `personas` es DISTINCT por documento: con vigencia, dentro del año; sin
    vigencia, sobre todo el período — que NO es la suma de los años.
    """
    qs = _entregas(vigencia)
    matriculas = dict(qs.values_list("snies_ies").annotate(n=Count("id")))
    programas = {k: v for k, v in qs.values_list("snies_ies")
                 .annotate(n=Count("snies_programa", distinct=True))}
    personas = {k: v for k, v in qs.values_list("snies_ies")
                .annotate(n=Count("numero_documento", distinct=True))}
    return {
        cod: {"personas": personas.get(cod, 0),
              "matriculas": matriculas.get(cod, 0),
              "programas": programas.get(cod, 0)}
        for cod in matriculas
    }


def conteos_por_programa(codigo_ies: str, vigencia: int | None = None) -> dict[str, dict]:
    """`{codigo_programa: {personas, matriculas}}` de una institución."""
    qs = _entregas(vigencia).filter(snies_ies=codigo_ies)
    matriculas = dict(qs.values_list("snies_programa").annotate(n=Count("id")))
    personas = {k: v for k, v in qs.values_list("snies_programa")
                .annotate(n=Count("numero_documento", distinct=True))}
    return {cod: {"personas": personas.get(cod, 0), "matriculas": matriculas.get(cod, 0)}
            for cod in matriculas}


def desglose_por_nivel(vigencia: int | None = None) -> dict:
    """«174 beneficiarios · 128 educación superior · 47 ETDH», con su matiz.

    Sigue sin resolverse si la formación técnica laboral cuenta para la meta, así
    que la pantalla tiene que poder leerse de las dos formas sin tocar datos. Y
    la suma por grupo puede pasarse del total: quien tiene matrícula en los dos
    aparece en ambos, y eso se dice en vez de repartirlo por un criterio
    inventado.
    """
    qs = _entregas(vigencia)
    niveles, docs_grupo = {}, {"superior": set(), "etdh": set()}
    for nivel, doc in qs.values_list("nivel_formacion", "numero_documento"):
        if not nivel:
            continue
        entrada = niveles.setdefault(nivel, {
            "nivel": nivel, "etiqueta": NIVEL_ETIQUETAS.get(nivel, nivel),
            "es_superior": nivel in NIVELES_SUPERIOR, "matriculas": 0, "_docs": set()})
        entrada["matriculas"] += 1
        entrada["_docs"].add(doc)
        docs_grupo["superior" if nivel in NIVELES_SUPERIOR else "etdh"].add(doc)

    detalle = []
    for e in sorted(niveles.values(), key=lambda x: (not x["es_superior"], x["nivel"])):
        docs = e.pop("_docs")
        detalle.append({**e, "personas": len(docs)})

    return {
        "niveles": detalle,
        "personas_total": qs.values("numero_documento").distinct().count(),
        "superior": {"matriculas": sum(e["matriculas"] for e in detalle if e["es_superior"]),
                     "personas": len(docs_grupo["superior"])},
        "etdh": {"matriculas": sum(e["matriculas"] for e in detalle if not e["es_superior"]),
                 "personas": len(docs_grupo["etdh"])},
        "personas_en_ambos_grupos": len(docs_grupo["superior"] & docs_grupo["etdh"]),
    }


def vigencias_disponibles() -> list[int]:
    from apps.jovenes_a_la_e.models import EntregaBeca
    return sorted(EntregaBeca.objects.order_by()
                  .exclude(vigencia__isnull=True)
                  .values_list("vigencia", flat=True).distinct(), reverse=True)
