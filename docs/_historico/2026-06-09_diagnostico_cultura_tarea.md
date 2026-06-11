# Tarea para Claude Code — Diagnóstico SOLO LECTURA (motor genérico de captura / Cultura)

## Contexto

Vamos a construir un **motor genérico de captura manejado por `tipo_evento`**
(reusable por cualquier subgrupo, no solo Cultura). Sus primeros 5 consumidores
serán las metas de Cultura de los proyectos **2780** y **2788**. Antes de proponer
schema, necesito verificar el estado REAL de la BD.

**Esta tarea es SOLO LECTURA. No es la construcción.**

## Reglas

- NO ejecutes DDL ni DML. NO borres nada. Solo SELECT / inspección.
- El contenedor NO tiene `psql`. Usá:
  `docker exec -it innova_k python manage.py shell` con
  `from django.db import connection; cur = connection.cursor()`, o `inspectdb`.
- Verificá contra el código y la BD actuales; si un doc dice algo distinto,
  manda el código/BD.
- Al final entregá **UN reporte en markdown** con las 3 secciones (A, B, C).
  Si algo no existe, decilo explícito ("no existe la tabla X").

## A) Anclas de la cadena (Cultura)

1. `proyecto`: filas con codigo/id **2780** y **2788**. Confirmá si son DOS filas
   distintas o un duplicado de nombre. Traé id, codigo, nombre, subgrupo_id.
2. `subgrupo`: cuál es el de **Cultura** (id + nombre) y su `dependencia`.
3. Para cada proyecto, contá qué YA existe en la cadena:
   `meta_proyecto` (cuántas y cuáles), `presu_indicador_meta_proyecto` (KPIs),
   `cdp`, `contrato`, `actividad_plan`, `actividad_indicador`.
   Quiero saber qué FALTA que Alex arme por la UI de presupuesto.

## B) Piezas reusables del motor (schema real)

4. `tipo_evento`: listá TODOS los codigos existentes y sus flags
   (`permite_inscripcion`, `permite_caracterizacion`, `requiere_actividad_plan`
   y cualquier otra columna/flag de la tabla).
5. `evento`: todas las columnas con su tipo. ¿Tiene ya alguna columna **JSONB**?
6. `beneficiario`: columnas + cómo discrimina persona/proveedor/organizacion
   (campo polimórfico). Nº de filas.
7. `organizacion`: columnas (incl. `tipo_organizacion_codigo`, `redes_sociales`).
8. `implemento`: columnas + nº filas + valores distintos de `categoria` y `aplica_a`.
9. `upl` y `barrio`: columnas clave (codigo, nombre) para selects.
10. Patrón de captura existente — traé el schema de: `entrega_beca`,
    `entrega_beca_elemento`, `entrega_insumo`, `entrega_insumo_elemento`,
    `inscripcion_banco_iniciativa`, `participante_evento`. Quiero ver cabecera +
    puente M2M + `firma_mongo_id`.
11. Sync de avance: schema de `presu_avance_ind_periodo` y `actividad_indicador`,
    y mostrá el código que crea avances al validar (Jóvenes J2 / Entregas).
12. ¿Hay ALGÚN precedente de columna **JSONB** usada para captura en el repo o la BD?
    (esto decide si los campos extra por tipo van en JSONB o relacional).

## C) Inventario de demos (SOLO LISTAR, NO BORRAR)

13. Listá eventos seed/test/demo: nombres tipo PRUEBA/TEST/DEMO, el evento
    Jóvenes `id=100055`, los ~10 eventos seed del mapa, los eventos ENTREGA de
    demo cerrados. Para cada uno: id, nombre, tipo_evento, fecha, y si tiene
    beneficiarios/avances colgando.
14. Beneficiarios/personas/avances huérfanos de pruebas.
    **NO borres**: solo la lista, para que Alex confirme antes de limpiar.

## Entregable

Reporte markdown con las secciones A, B y C. **No toques código ni BD.**
