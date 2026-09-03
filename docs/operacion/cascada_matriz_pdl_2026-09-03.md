# Cascada del 2026-09-03 — Matriz PDL como fuente de verdad

19 commits de `feat/formulacion-dominio-propio` hacia las tres troncales, con
**cinco DDL**. Este documento es el orden, y sobre todo el motivo del orden.

---

## Lo primero, porque cambia todo lo demás

**Hay UNA sola base y UN solo árbol.** Verificado el 2026-09-03:

```
docker inspect innova_k → /home/innova/Proyectos/innovaK  →  /app
DB_NAME = poblacion_kennedy      (único contenedor de app en la máquina)
```

`desarrollo`, `Pruebas` y `produccion` son **ramas de git**, no tres entornos
con base propia. De ahí se siguen dos cosas que conviene no confundir:

1. **Los cinco DDL ya están aplicados** —se aplicaron el 2026-09-03 contra
   `poblacion_kennedy`—, así que cascadear NO requiere volver a correrlos.
   Cascadear es una operación de git.
2. **Y por eso mismo hay que tener cuidado con la otra dirección**: el
   contenedor sirve el ÁRBOL, no el commit. Que la app funcione no prueba nada
   sobre lo que quedó commiteado. Ver `el-contenedor-monta-el-arbol` en la
   memoria: ya hubo una rama pusheada y rota al mismo tiempo.

---

## El orden de los DDL — para una base NUEVA

Si algún día esto arranca contra otra base (otra máquina, un entorno de
verdad separado, una restauración desde cero), **el código NO puede llegar
antes que su DDL**: las consultas nuevas nombran columnas y tablas que no
existirían, y revientan en la primera pantalla.

El orden es obligatorio y no es alfabético: cada uno depende del anterior.

| # | DDL | Qué crea | Depende de |
|---|---|---|---|
| 1 | `021_alerta_meta.sql` | alerta y magnitudes sobre `presu_presupuesto_meta_vigencia` | DDL 020 (ya aplicado antes de esta tanda) |
| 2 | `022_objetivo_estrategico.sql` | `metas.objetivo_estrategico` | — |
| 3 | `023_sector_catalogo.sql` | `presu_sector`, `presu_sector_alias`, `metas.sector_id` | — |
| 4 | `024_objetivo_programa.sql` | `presu_objetivo_estrategico`, `presu_programa`, `metas.programa_id` | — |
| 5 | `025_matriz_carga.sql` | `presu_matriz_carga` **+ las 6 FK** hacia ella | **023 y 024**: las FK se crean sobre sus columnas |

El 025 va último por una razón concreta: crea las seis claves foráneas sobre
`carga_origen_id` / `carga_retiro_id`, que nacen en el 023 y el 024. Si corre
antes, esas FK se saltan en silencio (el DDL las crea condicionalmente) y hay
que volver a correrlo. Es idempotente, así que rehacerlo no cuesta nada, pero
nadie se entera de que falta si no lo mira.

**El 022 quedó en el orden aunque su columna ya no se usa.** `metas.objetivo_estrategico`
dejó de escribirse y de leerse en esta misma tanda; la columna sigue ahí a
propósito (ver abajo). Saltarse el 022 en una base nueva haría fallar al 024,
que la referencia en un comentario, no en código — pero sobre todo dejaría la
base distinta a la de desarrollo, que es la que se probó.

### Cómo se corren

Cada uno tiene su aplicador con `--seco` (ensaya y hace ROLLBACK) y su
`--rollback`:

```bash
docker exec innova_k python apps/presupuesto/scripts/apply_023_sector_catalogo.py --seco
docker exec innova_k python apps/presupuesto/scripts/apply_023_sector_catalogo.py
```

Los tres nuevos (023, 024, 025) son **aditivos e idempotentes**: correrlos dos
veces no duplica nada. Los tres exigen **aprobación explícita de Alex y backup
< 24 h** (Constitución VII).

El 023 y el 024 además **siembran desde el Excel**, no desde una lista escrita
a mano: necesitan la Matriz PDL en la raíz del repo. El archivo está en
`.gitignore` —pertenece a su carga, no al repo, que es público—, así que en una
máquina nueva hay que ponerlo antes de correrlos.

---

## Qué NO se hizo, y por qué

**No se borraron las columnas viejas** (`metas.sector`, `codprog`, `nomprog`,
`objetivo_estrategico`), aunque ya no las escribe ni las lee nadie —verificado
antes de desenganchar el importador—.

El motivo: las 78 filas todavía tienen ese texto, y es la **única copia** del
valor que el área cargó a mano. Tres de esos valores no mapean a ningún sector
del catálogo:

    'Infraestructura'                    → mapea a DOS sectores oficiales
    'CPS y Planta'                       → es un tipo de contratación
    'Relacionamiento Interinstitucional' → no es un sector

Ese texto es hoy la evidencia de qué hay que revisar con la ALK. El `DROP
COLUMN` es una línea y tiene su rollback, pero es irreversible sobre el dato:
conviene esperar a que la ALK conteste, y borrarlo entonces en una pasada
propia.

---

## Qué se aplicó el 2026-09-03, con sus backups

| Cuándo | Qué | Backup previo |
|---|---|---|
| 11:22 | DDL 023 | `poblacion_kennedy_pre_sector_ddl023_20260903_112240.dump` (190 MB, verificado con `pg_restore --list`: 2.623 objetos) |
| 13:32 | DDL 024 y 025 | `poblacion_kennedy_pre_objprog_ddl024_20260903_113536.dump` (190 MB, posterior al 023) |

Estado resultante, medido: 13 sectores (3 alias) · 5 objetivos · 22 programas ·
**78 de 78 metas con programa**, 77 con sector (la 10 no es de ningún sector) ·
0 cargas registradas.

---

## Verificación antes de cascadear

- `manage.py test apps.presupuesto.tests apps.dashboard.tests -t /app` → **396 OK**
  (sin `-t /app` el descubrimiento revienta: `apps/` no tiene `__init__.py`)
- `manage.py check` → sin issues
- `npm run build` → limpio, `<base href="/app/">` verificado
- CSS del dashboard: **26,09 kB**, con el error del build en 32 — quedan 5,91 kB
