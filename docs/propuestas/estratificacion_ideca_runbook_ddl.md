# Runbook — Aplicar Sección A del DDL + carga de estratificación IDECA

> Lo ejecuta **Alex**. Objetivo: crear `manzana_estrato` + `escuela.estrato_ideca`,
> poblar las manzanas desde Catastro y asignar estrato a las 241 sedes.
>
> **Riesgo bajo:** la Sección A es **puramente aditiva** (una tabla nueva + una
> columna nullable nueva). NO modifica ni borra datos de ningún sistema que use
> la BD compartida. Por eso el rollback normal es un `DROP`, no un restore.

---

## Prerrequisito importante (orden real)

1. **DDL** (SQL) — independiente del código. Se puede aplicar solo.
2. **Desplegar la rama** `feat/estratificacion-ideca` al contenedor y **rebuild**
   de la imagen. Esto es obligatorio antes de los comandos porque:
   - `sync_estratificacion` y `asignar_estrato_sedes` son código de la rama.
   - `asignar_estrato_sedes` usa `shapely` (backend default), que se instala en
     el rebuild (está en `requirements.txt`).
3. **Comandos** sync + asignar. Como la BD es compartida/externa, el sync se
   corre **una sola vez** desde cualquier entorno que tenga la rama + shapely.

---

## Paso 0 — Backup pre-DDL

```bash
pg_dump -h 10.100.102.12 -U innova-bd -d poblacion_kennedy -Fc \
  -f ~/Proyectos/postgres/backups/poblacion_kennedy_pre_estratificacion_$(date +%Y%m%d_%H%M%S).dump
# (password en .env)
ls -lht ~/Proyectos/postgres/backups/ | head -3
```

No sigas si el `.dump` no quedó con tamaño > 0.

---

## Paso 1 — Aplicar el DDL Sección A

Método recomendado (psql desde el host — el contenedor NO trae psql). El archivo
tiene la Sección B (PostGIS) **comentada**, así que correrlo entero solo aplica A.
Es idempotente (`IF NOT EXISTS`), se puede re-correr sin daño.

```bash
cd /home/innova/Proyectos/innovaK/.claude/worktrees/estratificacion-ideca   # o donde esté desplegada la rama
psql -h 10.100.102.12 -U innova-bd -d poblacion_kennedy \
  -f apps/georeferenciacion/scripts/ddl_estratificacion_ideca.sql
```

O bien, pegar el SQL exacto (idéntico a la Sección A del archivo):

```sql
CREATE TABLE IF NOT EXISTS manzana_estrato (
    id             BIGSERIAL PRIMARY KEY,
    codigo_manzana TEXT NOT NULL UNIQUE,
    estrato        SMALLINT,
    geometry       JSONB NOT NULL,
    properties     JSONB,
    fecha_fuente   DATE,
    created_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_manzana_estrato_estrato ON manzana_estrato (estrato);
ALTER TABLE escuela ADD COLUMN IF NOT EXISTS estrato_ideca SMALLINT;
```

### Verificar Paso 1

```sql
-- tabla creada y vacía
SELECT count(*) FROM manzana_estrato;                    -- espera: 0
-- columna nueva presente
SELECT column_name FROM information_schema.columns
 WHERE table_name='escuela' AND column_name='estrato_ideca';   -- espera: 1 fila
```

---

## Paso 2 — Desplegar la rama + rebuild (prerequisito de los comandos)

Sigue el flujo estándar (cascada + rebuild que ya instala shapely). Como la BD es
compartida, basta con que la rama corra en **un** entorno para poder cargar los
datos; luego se cascada normal.

```bash
# ... cascada feat/estratificacion-ideca -> desarrollo -> Pruebas -> produccion ...
# rebuild + restart del contenedor (instala shapely de requirements.txt):
docker compose -f /home/innova/Proyectos/innovaK/docker-compose.yml up -d --build innova_k
```

### Verificar Paso 2

```bash
docker exec innova_k python -c "import shapely; print('shapely', shapely.__version__)"   # espera: 2.x
docker exec innova_k python manage.py help sync_estratificacion | head -1                # existe el comando
```

---

## Paso 3 — Poblar las manzanas (Catastro → BD)

```bash
# Opcional primero: descarga y reporta sin escribir (no toca BD)
docker exec innova_k python manage.py sync_estratificacion --dry-run

# Carga real (~19k manzanas, ~22s)
docker exec innova_k python manage.py sync_estratificacion
```

### Verificar Paso 3

```sql
SELECT count(*) FROM manzana_estrato;                    -- espera: ~18 900 (validación: 18 929)
SELECT estrato, count(*) FROM manzana_estrato GROUP BY estrato ORDER BY estrato;
-- distribución esperada (aprox):
--   0: 2456   1: 2748   2: 7762   3: 5455   4: 490   5: 18
```

Si el conteo es 0 o muy bajo → revisar red hacia Catastro (el comando reporta el
error). NO continúes al Paso 4 hasta tener ~19k filas.

---

## Paso 4 — Asignar estrato a las 241 sedes

```bash
# Primero dry-run (lee sedes, NO escribe): revisa que los estratos tengan sentido
docker exec innova_k python manage.py asignar_estrato_sedes

# Escritura real
docker exec innova_k python manage.py asignar_estrato_sedes --write
```

### Verificar Paso 4

```sql
SELECT
  count(*) FILTER (WHERE estrato_ideca IS NOT NULL) AS con_estrato,
  count(*) FILTER (WHERE estrato_ideca IS NULL)     AS sin_estrato,
  count(*) AS total
FROM escuela;
-- La mayoría con_estrato; algunas sin_estrato es NORMAL (sedes que caen fuera de
-- toda manzana estratificada — en la validación, 2 de 8 sedes de muestra). No es error.
```

---

## Paso 5 — Confirmar que el mapa pinta colores reales

1. Endpoint ya devuelve datos:
   ```sql
   -- proxy rápido: si hay filas en manzana_estrato, el endpoint las sirve
   SELECT count(*) FROM manzana_estrato;   -- > 0
   ```
2. En el navegador: `/app/` → Mapa de Kennedy → panel **Capas** → marcar
   **"Estratificación (IDECA)"**. Antes del sync se veía vacío; ahora debe
   pintar las manzanas coloreadas por estrato y el clic muestra el popup
   "Manzana <código> · Estrato N".

---

## Si algo falla a mitad de camino

**Regla de oro (BD compartida):** para deshacer la Sección A **NO restaures el
backup completo** — eso revertiría también los datos de los otros sistemas que
comparten `poblacion_kennedy`. Como la Sección A solo agrega objetos nuevos, el
rollback correcto es soltarlos:

```sql
-- rollback quirúrgico (no toca nada ajeno)
DROP TABLE IF EXISTS manzana_estrato;
ALTER TABLE escuela DROP COLUMN IF EXISTS estrato_ideca;
```

- **Falla en el sync (Paso 3):** no deja estado inconsistente (upsert idempotente).
  Se puede re-correr `sync_estratificacion` las veces que haga falta.
- **Falla en asignar (Paso 4):** `--write` es idempotente por sede; re-correrlo
  recalcula. Para limpiar: `UPDATE escuela SET estrato_ideca = NULL;` y reintentar.
- **Restore completo del backup:** solo como último recurso ante corrupción real,
  y coordinando con los otros sistemas de la BD compartida — no para deshacer esta
  carga aditiva.
```pg_restore -h 10.100.102.12 -U innova-bd -d poblacion_kennedy --clean <dump>```
