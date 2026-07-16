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

> **Corregido 2026-07-09.** `pg_dump` por TCP desde el host **no funciona**:
> `pg_hba.conf` rechaza la conexión (`no pg_hba.conf entry for host
> "10.100.102.12"`). Postgres solo acepta el socket local y la red de Docker.
> Usa el mismo mecanismo del cron (`sudo -u postgres`, ya en sudoers).

```bash
sudo -u postgres pg_dump -F c -Z 6 poblacion_kennedy \
  > ~/Proyectos/postgres/backups/poblacion_kennedy_pre_estratificacion_$(date +%Y%m%d_%H%M%S).dump
ls -lht ~/Proyectos/postgres/backups/ | head -3
```

No sigas si el `.dump` no quedó con tamaño > 0.

---

## Paso 1 — Aplicar el DDL Sección A

El archivo tiene la Sección B (PostGIS) **comentada**, así que correrlo entero
solo aplica A. Es idempotente (`IF NOT EXISTS`), se puede re-correr sin daño.

> **Corregido 2026-07-09.** `psql -h 10.100.102.12` desde el host tampoco pasa el
> `pg_hba`. Y `sudo -u postgres psql` crearía la tabla con **owner `postgres`**,
> no `innova-bd`, dejando a la app sin permisos. Usa `connection.cursor()` dentro
> del contenedor — el patrón que ya usa el proyecto (ver bitácora del 2026-06-04).

```bash
docker exec innova_k python -c "
import django; django.setup()
from django.db import connection
sql = open('/app/.claude/worktrees/estratificacion-ideca/apps/georeferenciacion/scripts/ddl_estratificacion_ideca.sql').read()
with connection.cursor() as c:
    c.execute(sql)
print('DDL Sección A aplicado.')"
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

> **Corregido 2026-07-09.** `docker compose up -d --build` **no reconstruye nada**:
> el servicio `innova_k` no tiene sección `build:` en `docker-compose.yml`, solo
> `image:`. El `--build` es un no-op silencioso (responde `Container innova_k
> Running`). Hay que construir la imagen a mano.

```bash
# ... cascada feat/estratificacion-ideca -> desarrollo -> Pruebas -> produccion ...
cd /home/innova/Proyectos/innovaK
docker tag innovak-innova_k:latest innovak-innova_k:rollback-$(date +%Y%m%d)  # red de seguridad
docker build -t innovak-innova_k:latest .                                     # compose NO lo hace
docker compose -f docker-compose.yml up -d --force-recreate innova_k
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

> **Ojo (2026-07-09):** de esas 18.929 manzanas, **solo 4.826 están dentro de
> Kennedy**. El bbox de descarga (`BBOX_KENNEDY`) es un rectángulo con margen que
> arrastra Bosa, Puente Aranda y Fontibón. Es útil para el *snap* de sedes en el
> borde, pero **la capa del mapa pintará 3 de cada 4 manzanas fuera de la
> localidad**. Filtrar en el endpoint antes de publicar la capa.
>
> Dentro de Kennedy la distribución real es:
> `0: 519 · 1: 80 · 2: 2377 · 3: 1816 · 4: 34 · 5: 0`

---

## Paso 4 — Asignar estrato a las 241 sedes

```bash
# Dry-run (lee sedes, NO escribe). Reporta con qué método resolvió cada sede.
docker exec innova_k python manage.py asignar_estrato_sedes

# Escritura real
docker exec innova_k python manage.py asignar_estrato_sedes --write

# Para reproducir el point-in-polygon estricto de la versión vieja:
docker exec innova_k python manage.py asignar_estrato_sedes --estricto
```

El comando degrada en tres pasos y lo reporta: `contenido` (dentro de una
manzana) → `cercano` (andén/vía, a ≤30 m) → `entorno` (parque grande: voto de las
manzanas con estrato oficial a ≤150 m). El estrato `0` no vota en el entorno.

### Verificar Paso 4

```sql
SELECT
  count(*) FILTER (WHERE estrato_ideca > 0)    AS con_estrato_oficial,
  count(*) FILTER (WHERE estrato_ideca = 0)    AS sin_estrato_oficial,
  count(*) FILTER (WHERE estrato_ideca IS NULL) AS sin_resolver,
  count(*) AS total
FROM escuela;
-- Resultado real (2026-07-09): 175 con estrato oficial · 65 en estrato 0 · 1 sin
-- resolver · 241 total.
```

> **Lo que decía este runbook y era falso.** La versión anterior afirmaba que las
> sedes `sin_estrato` eran *"NORMAL […] No es error"*. Con point-in-polygon
> estricto quedaban **62 sedes sin estrato (26 %)** — y al medirlas estaban a una
> **mediana de 4 metros** de una manzana. No era un límite de la fuente: era un
> defecto del método. Con la tolerancia quedan **1** (la sede 225, cuyas
> coordenadas caen fuera de Kennedy y del bbox de descarga; ver deuda de datos).
>
> Un `estrato_ideca = 0` **sí** es un límite real de la fuente: la manzana existe
> pero Catastro no le asignó estrato. `0` y `NULL` no son lo mismo y el Comité
> debe puntuarlos distinto.

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
