# Estratificación IDECA — Estado, ejecución y hallazgos

> 🗺️ **El plan de evolución de la plataforma geoespacial vive aparte:**
> [`plan_evolucion_mapa.md`](./plan_evolucion_mapa.md) (ingesta declarativa con GDAL ·
> teselas PMTiles · MapLibre · geocodificador). Este documento es el **registro de
> estado** de la estratificación; aquel es el **plan** hacia adelante.
>
> **Fase 0 del plan (geocodificador) — ejecutada el 2026-07-16:**
> `apps/georeferenciacion/services/geocoder.py` +
> `asignar_estrato_org --por-direccion`. Resuelve el estrato de la organización por
> **dirección → placa domiciliaria de Catastro → punto → manzana**, sin depender de
> M22. Medido sobre el piloto: **6/24 → 14/24**.

> **Documento de trabajo.** Aquí escribo las respuestas para que las leas y copies
> sin depender del chat.
> **Última actualización:** 9 de julio de 2026, tras ejecutar el DDL y la carga.

---

## 1. Lo que se ejecutó hoy (puntos 2 y 3 de tus respuestas)

### ✅ Backup pre-DDL
`~/Proyectos/postgres/backups/poblacion_kennedy_pre_estratificacion_20260709_095242.dump`
(2,3 MB, consistente con los diarios).

> Nota: `pg_dump` desde el host **no funciona** (`pg_hba` rechaza la conexión TCP
> desde `10.100.102.12`). Hay que usar `sudo -u postgres pg_dump` por socket local,
> igual que el script del cron. El runbook dice otra cosa y debe corregirse.

### ✅ DDL Sección A aplicado
- `manzana_estrato` creada · `escuela.estrato_ideca` agregada · owner `innova-bd`.
- Sección B (PostGIS) quedó comentada e intacta. **No se tocó la BD compartida.**

### ✅ Carga de datos
| Paso | Resultado |
|------|-----------|
| `sync_estratificacion` | **18.929 manzanas** de Catastro |
| Distribución manzanas | `0:2456 · 1:2748 · 2:7762 · 3:5455 · 4:490 · 5:18` |
| `asignar_estrato_sedes --write` | **241 sedes** procesadas |

Los números coinciden **exactamente** con lo que predecía el runbook.

### ✅ Housekeeping
- Manuales commiteados en rama nueva **`docs/manuales-banco-mapa`** (desde
  `desarrollo`, no directo a `produccion`): `mapa.md` nuevo (285 líneas),
  `banco.md` con URLs actualizadas al SPA, `README.md` indexado.
  *Worktree:* `.claude/worktrees/docs-manuales/`. **Falta cascadearla — dime si procedo.**
- Borrados los dos duplicados sueltos de `docs/propuestas/` (eran versiones
  **viejas**; las buenas viven en `feat/estratificacion-ideca`).
- Working tree de `produccion` limpio.

> **Corrección a lo que te dije antes:** el cambio pendiente en `banco.md` **no era**
> la actualización de puntaje/ranking/comité. Era la modernización de URLs a Angular.
> `banco.md` sigue con **cero menciones** a puntaje, ranking o panel de comité.
> Ese pendiente **sigue abierto** antes de usarlo con Deportes.

---

## 2-bis. ✅ Hallazgo A — RESUELTO (rama `feat/estratificacion-ideca`, `025d2b6`)

`resolver_estrato()` degrada en tres pasos y **reporta cuál usó** (el dato alimenta
un puntaje: tiene que ser auditable):

1. **`contenido`** — el punto cae dentro de una manzana. Caso normal.
2. **`cercano`** — manzana contigua a ≤ 30 m. Es el andén o la vía.
3. **`entorno`** — voto mayoritario de las manzanas con estrato oficial a ≤ 150 m
   (sede en un parque grande). **El estrato `0` no vota**: significa "sin estrato
   oficial", no puede inferir el del entorno.

`--estricto` reproduce el comportamiento anterior. `estrato_en_punto()` conserva
su firma. **+6 tests** (11/11 verdes) y la suite completa en **537 OK**.

### Distribución re-medida (ya escrita en la BD)

| | antes | **ahora** |
|---|---|---|
| Con estrato oficial (1–6) | 127 | **175** |
| Estrato `0` (sin estrato oficial) | 52 | 65 |
| Sin resolver (`NULL`) | **62** | **1** |

Las 61 sedes recuperadas entraron por `cercano`, ninguna necesitó `entorno`.
La única sin resolver es la sede **225**, cuyas coordenadas caen fuera de Kennedy
y fuera del bbox de descarga. **Se deja en `NULL`: no se infiere.**

`fecha_fuente` ahora persiste `2019-08-15` en las 18.929 filas.

### ⚠ El estrato 1 sigue en cero — pero ya sé por qué, y no es un error

Kennedy **sí tiene** manzanas de estrato 1: son **80**, no 2.748. Las otras 2.668
son de localidades vecinas. Solo **4.826 de las 18.929 manzanas están dentro de
Kennedy** — el bbox de descarga es un rectángulo con margen que arrastra Bosa,
Puente Aranda y Fontibón.

| Estrato | Dentro de Kennedy | Fuera |
|---|---|---|
| 0 | 519 | 1.937 |
| **1** | **80** | 2.668 |
| 2 | 2.377 | 5.385 |
| 3 | 1.816 | 3.639 |
| 4 | 34 | 456 |
| 5 | 0 | 18 |

Con 80 manzanas de estrato 1 sobre 4.826 (1,7 % del territorio), que ninguna de
las 241 sedes caiga en una es **plausible, no un artefacto**. El renglón
*"estrato 1 → puntaje máximo"* del memo seguiría sin activarse nunca. La escala
real que el Comité debe calibrar es sobre los estratos **2, 3 y 4**.

### 🟡 Consecuencia para la capa del mapa (no la toqué)
El endpoint `/geo/api/kennedy/estratificacion/` sirve las 18.929 manzanas: **el
mapa pintaría 3 de cada 4 fuera de la localidad.** Hay que filtrar por el contorno
de Kennedy antes de publicar la capa. Conservar las vecinas en la tabla **sí es
útil** para el *snap* de sedes en el borde (10 de las 61 pegaron a una manzana
vecina), así que el filtro va en el endpoint, no en el sync.

### 🟡 Deuda de datos descubierta
**25 de las 241 sedes están fuera del contorno de Kennedy.** Es un problema de la
tabla `escuela`, ajeno a la estratificación, pero conviene revisarlo.

---

## 2. 🔴 Hallazgo crítico A — el point-in-polygon descarta 1 de cada 4 sedes *(histórico — resuelto arriba)*

**De 241 sedes, solo 127 quedaron con estrato usable (1–6). El 47% no.**

| Resultado | Sedes | Qué significa |
|-----------|-------|---------------|
| Estrato 1–6 | **127** | Cayó dentro de una manzana estratificada |
| Estrato `0` | **52** | Cayó en manzana **sin estrato oficial** (límite real de Catastro) |
| `NULL` | **62** | Cayó **fuera de toda manzana** |

Medí las 62 `NULL`. **No están fuera de Kennedy.** Están a una **mediana de 4 metros**
de una manzana:

```
SUPER MANZANA 2                  0.6 m  → manzana estrato 2
CASA CULTURAL YORUBA             0.4 m  → manzana estrato 3
SALÓN COMUNAL LUCERNA            1.6 m  → manzana estrato 3
SALON COMUNAL LOS PERIODISTAS    3.2 m  → manzana estrato 3
SALON COMUNAL LAS MARGARITAS 1   4.2 m  → manzana estrato 2
SALÓN COMUNAL BOITA              4.4 m  → manzana estrato 3
BIBLIOTECA LA GUARICHA           6.9 m  → manzana estrato 2
FUNDACIÓN REAL PRIMAVERA         9.3 m  → manzana estrato 0
```

**Causa:** las manzanas catastrales no cubren andenes, vías ni parques. El punto de
la sede cae en el borde. No es que la sede "no tenga estrato": es que el polígono
termina a cuatro metros.

**Esto activa el gate de PR-3**, que decía literalmente: *"correr contra sedes de
estrato conocido y validar antes de seguir. Si el PIP no cuadra, se para aquí."*

**El runbook se equivoca** cuando afirma: *"algunas sin_estrato es NORMAL […] No es
error."* Sí es un error corregible.

**Arreglo propuesto:** si el punto no cae en ninguna manzana, asignar la **manzana
más cercana dentro de una tolerancia** (~30 m). Es un cambio pequeño en
`asignar_estrato_sedes`. Las sedes en medio de un parque grande necesitan además
una regla aparte (mayoría de las manzanas del entorno).

---

## 3. Hallazgo B — ninguna *sede* está en estrato 1 (≠ no existe estrato 1)

> ⚠️ **CORREGIDO 2026-07-16 (decisión de Alex).** La conclusión original de esta
> sección era **errada** y por poco se va al memo. Decía que el renglón "estrato 1"
> *"nunca se activaría"* y recomendaba calibrar solo sobre **2, 3 y 4**. Eso confunde
> **dónde están las 241 sedes de hoy** con **qué tiene el territorio**.
>
> **Catastro estratifica por manzana, y Kennedy sí tiene estrato 1: 85 manzanas.**
> Medido en vivo con `ids_manzanas_en_kennedy()` sobre las **4.966** manzanas que
> intersecan el contorno:
>
> | Estrato | Manzanas en Kennedy | % territorio |
> |---------|--------------------:|-------------:|
> | 0 (sin estrato oficial) | 556 | 11,2 % |
> | **1** | **85** | **1,7 %** |
> | 2 | 2.451 | 49,4 % |
> | 3 | 1.837 | 37,0 % |
> | 4 | 37 | 0,7 % |
> | 5 / 6 | **0** | — |
>
> **La tabla de puntos es una regla sobre el TERRITORIO, no un resumen de las sedes
> existentes**: una organización futura puede operar en esas 85 manzanas, y es
> justo el caso que la política quiere priorizar. Suprimir el renglón por no tener
> casos hoy habría borrado el de mayor prioridad.
> **Se calibra sobre 1, 2, 3 y 4.** Lo único inactivo de verdad es **5–6** (cero
> manzanas en Kennedy).

Dato que sigue vigente: de las **241 sedes** registradas, ninguna cae en una manzana
de estrato 1 (82 en estrato 2, 91 en 3, 2 en 4, 65 sin estrato oficial, 1 sin
resolver). Eso describe la oferta de escenarios de hoy, no el territorio.

### Decisión de Alex (2026-07-16) — "sin estrato oficial" = estrato 1

Las manzanas dotacionales (parques, colegios, equipamientos) que Catastro deja sin
estrato **se puntúan como estrato 1** (máximo). Razón: es donde de verdad ocurre lo
recreodeportivo y la ausencia es de la fuente, no de la organización.

**Efecto medido, documentado en el memo (nota 2) para que el Comité lo apruebe con
el dato a la vista:** son **65 de 241 sedes (1 de cada 4)** las que entran al tramo
más alto. Al medir el entorno de esas 65 (voto mayoritario de manzanas vecinas a
150 m, el mismo criterio del paso 3 de `resolver_estrato`), **ninguna está rodeada de
estrato 1**: 38 tienen entorno de estrato 2 y 27 de estrato 3. Consecuencia: un
parque en sector de estrato 3 puntúa por encima de una sede residencial de estrato 2.

> **Ojo si algún día se reabre:** esta regla convive con una tensión en el código.
> `IndiceManzanas.resolver()` paso 3 dice explícitamente *"El 0 significa «sin estrato
> oficial» y **no es un voto válido** para inferir el del entorno"* — es decir, para
> el mismo caso (sede en un parque) el sistema ya eligió **inferir del entorno** en
> vez de asumir un fijo. Hoy ese paso 3 **no se dispara** para estas 65: caen *dentro*
> de una manzana mapeada con estrato 0, así que el paso 1 (`contenido`) resuelve
> primero y devuelve 0. La alternativa (asignar el estrato mayoritario del entorno)
> está implementada y quedó ofrecida al Comité en la nota 2 del memo.

---

## 4. 🔴 Hallazgo crítico C — producción no se puede reconstruir

Esto lo encontré de rebote y **no tiene que ver con estratificación**, pero es lo más
grave del día.

**El contenedor `innova_k` derivó de su imagen y nadie puede recrearlo sin romperlo.**

- Imagen `innovak-innova_k`: construida el **13 de marzo**.
- Contenedor: creado el **29 de abril** desde esa imagen.
- Desde entonces le instalaron **17 paquetes a mano**, que no están en ninguna imagen.

Entre ellos, **toda la pila de la API**: `djangorestframework`, `simplejwt`,
`drf-spectacular`, `django-cors-headers`, `django-ratelimit`, `cryptography`, `redis`.

### Las dos bombas

**1. Un rebuild produce una imagen que no arranca.**
`drf_spectacular` y `corsheaders` están en `INSTALLED_APPS` / `MIDDLEWARE`, pero **no
están en `requirements.txt` ni en `requirements-lock.txt`**. Django falla al importar
`INSTALLED_APPS`. Verificado:

```
$ docker run --rm innovak-innova_k python -c 'import corsheaders'
ModuleNotFoundError: No module named 'corsheaders'
$ docker run --rm innovak-innova_k python -c 'import drf_spectacular'
ModuleNotFoundError: No module named 'drf_spectacular'
```

**2. `.env` ya no tiene la contraseña de la base.**
`DB_PASSWORD=` está **vacío**. El contenedor vivo la tiene en memoria (12 caracteres),
heredada de cuando se creó. Si se recrea, la app **no puede conectarse a Postgres**
y la credencial habría que recuperarla de otro lado.

### Por qué importa hoy
El **Paso 2 del runbook** te instruye a correr `docker compose up -d --build`.
**Eso tumbaría producción.** Por eso la carga de datos la hice en un **contenedor
efímero** (`docker run --rm`), sin tocar `innova_k`, que sigue intacto y sirviendo.

### Arreglo (PR corto, aparte)
1. Agregar a `requirements.txt`: `django-cors-headers==4.4.0`, `drf-spectacular==0.27.2`,
   `django-ratelimit==4.1.0`.
2. Restaurar `DB_PASSWORD` en `.env` (la tengo verificada en el contenedor; **no la
   escribí en ningún archivo ni log**).
3. Recién ahí, un rebuild es seguro. Probarlo primero en un contenedor efímero.

---

## 4-bis. PR de infraestructura — ✅ APLICADO EN PRODUCCIÓN (9 jul, 10:53)

**Producción ya es reconstruible.** Imagen `8c7196bbb4a5`, contenedor recreado,
corte de **8 segundos**. Rollback disponible en `innovak-innova_k:rollback-20260709`.

| Verificación post-rebuild | Resultado |
|---|---|
| Paquetes en el contenedor | **103**, ninguno instalado a mano |
| Conexión a la BD (`.env` restaurado) | ✅ `innova-bd` → 18.929 filas |
| `/` · `/app/` · `/api/docs/` · `/login/` (vía nginx) | 302 · 200 · 200 · 302 |
| Tracebacks en el arranque | **0** |
| Suite de smoke tests (pre-merge, imagen nueva) | **537 OK**, 8 skipped |

Cascada: `desarrollo` `f927908` → `Pruebas` `8136a20` → `produccion` `3fc5268`.
*(Sin `git push` — pendiente de tu OK.)*

---

## 4-ter. Detalle del PR de infraestructura

Rama **`fix/infra-deps-rebuild`** (commit `f4f6e2c`, desde `desarrollo`).

**`.env` — hecho.** Backup en `/home/innova/.env_innovak_backup_20260709`
(chmod 600, fuera del repo). `DB_PASSWORD` restaurada desde el contenedor vivo y
**verificada autenticando** contra Postgres. Nunca se imprimió ni quedó en un log.
35 líneas intactas; git no la ve.

**`requirements.txt`** — agregados los 3 con comentario de por qué existen.
**`requirements-lock.txt`** — regenerado desde la imagen verificada: 89 → 103
paquetes (antes le faltaban DRF, simplejwt y cryptography).

**Verificación en imagen efímera** (`docker build -t innovak-infra-test:tmp`,
sin tocar `innova_k`):

| Prueba | Resultado |
|--------|-----------|
| `import corsheaders, drf_spectacular, django_ratelimit` | ✅ |
| Pila API (DRF 3.15.2, simplejwt, cryptography, redis) | ✅ |
| `manage.py check` contra la BD real | ✅ 0 issues |
| Gunicorn arranca de verdad | ✅ `/` → 302, `/api/docs/` → 200 |
| Tracebacks en logs de arranque | ✅ 0 |
| `pip freeze` vs contenedor vivo | ✅ **103 = 103, nada falta** |

### 🔴 Hallazgo D — `docker compose up -d --build` NO reconstruye nada

Al ejecutarlo, compose respondió `Container innova_k Running` y la imagen siguió
siendo la misma (`ac908013c420`). **El servicio `innova_k` no tiene sección
`build:` en `docker-compose.yml`, solo `image: innovak-innova_k`.**

```yaml
  innova_k:
    image: innovak-innova_k     # ← sin build:, --build es un no-op
    container_name: innova_k
```

**Esta es la raíz de toda la deriva.** La imagen se construyó a mano una vez
(13 de marzo) y nunca más. Como compose no la reconstruye, la única forma que
tenía cualquiera de agregar una dependencia era `pip install` dentro del
contenedor vivo. De ahí los 17 paquetes huérfanos.

El comando que recomienda el runbook **no puede funcionar**. El procedimiento
real de despliegue es:

```bash
# 1. cascadear fix/infra-deps-rebuild → desarrollo → Pruebas → produccion
# 2. construir la imagen A MANO (compose no lo hace):
docker build -t innovak-innova_k:latest .
# 3. recrear el contenedor con la imagen nueva:
docker compose -f docker-compose.yml up -d --force-recreate innova_k
# 4. SPA: solo si cambió frontend/ (el Dockerfile compila static/, NO el SPA):
cd frontend && npx ng build --base-href=/app/
# 5. verificar: /app/ 200 · /api/docs/ 200 · logs sin tracebacks
```

**Rollback:** la imagen anterior quedó etiquetada como
`innovak-innova_k:rollback-20260709` (`ac908013c420`) antes de reconstruir.

**Recomendación:** agregar `build: .` al servicio en `docker-compose.yml` para
que el despliegue sea un solo comando y la imagen no vuelva a derivar. Requiere
doble confirmación (toca `docker-compose.yml`) — **no lo hice.**

> **Hallazgo colateral (no lo toqué):** el `Dockerfile` hace `COPY .env .env`.
> La imagen queda con `DB_PASSWORD`, `SECRET_KEY`, credenciales de Mongo y
> `DOCUMENTOS_AES_KEY` **horneadas dentro**. Cualquiera con acceso a la imagen
> las lee. Lo correcto es pasarlas solo por `environment:` del compose (que ya
> lo hace). Ticket aparte.

---

## 4-quater. Sesión del 9 de julio (tarde) — puntos 1 a 6

### ✅ 1. `git push` de las 3 troncales
`desarrollo` `f927908` · `Pruebas` `8136a20` · `produccion` `3fc5268`. El hook
pre-push corrió 537 tests en cada una.

### ✅ 2. Capa del mapa recortada a Kennedy (`aae7785`)
`ids_manzanas_en_kennedy()` interseca contra el mismo GeoJSON del contorno que ya
sirve el mapa, cacheado 24 h en Redis (0,77 s → 0,4 ms). El endpoint recorta por
defecto y declara `recortado_a_kennedy`; `?todas=1` sirve el bbox completo.

**18.929 → 4.966 features · payload 30,9 MB → 8,7 MB.**

Las manzanas vecinas **se quedan en la tabla**: 10 de las 61 sedes del borde
resolvieron su estrato pegando a una manzana de otra localidad. El recorte es de
presentación, no de datos.

> **Bug encontrado al pasar:** `apis.py` no tenía `logger` definido. La rama del
> `except` que agregué habría lanzado `NameError`. `py_compile` no lo detecta.

### 🔴 3. La vigencia del dato NO es 2019-08-15 (`02be8cd`)

La propuesta lo afirmaba y **el memo se lo iba a decir al Comité**. Es falso.

El servicio no publica `editingInfo`, pero **cada manzana trae el acto
administrativo que le fijó el estrato**:

| Fecha | Acto | Manzanas |
|---|---|---|
| **2017-07-28** | **Decreto 394** | **18.927** |
| 2018-06-15 | Resolución 811 | 1 |
| 2018-03-23 | Resolución 412 | 1 |

`sync_estratificacion` ahora persiste `fecha_fuente` **por manzana** y guarda el
acto en `properties`. Memo y propuesta corregidos.

### ✅ 4. PR-4 — estrato de la organización (`256cf16`)

DDL `010_estrato_ideca_org.sql` aplicado (columna nullable, aditiva, con
rollback). `estrato_de_barrio()` toma la **mayoría de las manzanas del barrio**;
el estrato `0` no vota; empate → gana el más bajo. `asignar_estrato_org --write`
ejecutado. **+5 tests** (16 en el módulo, 537 en la suite).

**Techo real del método, medido:**

| | Inscripciones |
|---|---|
| Resueltas por barrio | **6** |
| Barrio **sin geometría** en la BD | **15** ← deuda M22 |
| Sin barrio declarado | 3 |
| **Total** | 24 |

Los 13 barrios faltantes tampoco están en `barrios_kennedy.geojson`: ese archivo
tiene otro catálogo, más grueso (105 nombres), y el emparejamiento por nombre da
**cero**. Cargar la geometría de `barrio` desbloquea el resto **sin tocar este
código**. Las no resueltas quedan `NULL`: no se infiere.

**Señal temprana de la validación cruzada:** de las 6 resueltas, **4 difieren**
del estrato autodeclarado (una organización declaró estrato 1 y su barrio es 3).

---

### ✅ 6. `fix/infra-secrets` — verificado, **sin aplicar a producción**

Rama `fix/infra-secrets` (`11007ff`, `0f7313a`), ya en `desarrollo` y `Pruebas`.

**(a) Secretos horneados.** Quitar `COPY .env .env` del Dockerfile **no bastaba**:
`COPY . .` (línea 32) metía el `.env` igual, porque **no existía `.dockerignore`**.
Verificado sobre la imagen que corre hoy:

```
/app/.env      → SECRET_KEY, DB_PASSWORD, DOCUMENTOS_AES_KEY, credenciales Mongo
/app/.git       67 MB
/app/.claude   540 MB
```

**(b) `.gitignore` ignoraba `.dockerignore`.** Línea 56. El archivo existía en mi
disco —por eso el build local salió limpio— pero **nunca habría llegado al
servidor**: en un clon nuevo, `COPY . .` volvería a hornear los secretos. Ignorar
el `.dockerignore` es exactamente al revés de lo que se quiere.

**(c) `build:` en compose.** Ahora `docker compose build` construye de verdad
(probado con un override de tag, sin tocar el tag de producción).

Verificado en imagen efímera: `/app/.env`, `/app/.git`, `/app/.claude` y
`node_modules` **no existen**; los únicos `SECRET_KEY=` que quedan son
`${SECRET_KEY}`; gunicorn arranca sin bind-mount (`/` 302, `/api/docs/` 200,
0 tracebacks); `manage.py check` limpio. **Imagen: 2,44 GB → 1,47 GB (−40 %).**

### ✅ 7. Desplegado en producción (`produccion` = `93ce829`)

`docker compose up -d --build innova_k` — **por primera vez reconstruyó de verdad**
(`Container innova_k Recreated`). Corte: **24 s**. SPA reconstruido con
`--base-href=/app/`. Las 3 troncales pusheadas (537 tests en cada push).

| Verificación en vivo | Resultado |
|---|---|
| Imagen sin `/app/.env`, `/app/.git`, `/app/.claude` | ✅ |
| Tamaño de la imagen | 2,44 GB → **1,48 GB** |
| `shapely` presente **sin `pip install` manual** | ✅ 2.1.2 (104 paquetes) |
| `/` · `/app/` · `/api/docs/` | 302 · 200 · 200 |
| Capa de estratificación (default) | **4.966** features, `recortado_a_kennedy: true` |
| Capa con `?todas=1` | 18.929, `recortado: false` |
| Tracebacks en el arranque | **0** |

**Rollback:** `innovak-innova_k:rollback-20260709-b` (2,44 GB, la imagen de la
mañana) y `:rollback-20260709` (la original de marzo).

---

## 5. Hallazgo menor — `fecha_fuente` no se guardó *(histórico — resuelto en 4-quater §3)*

`manzana_estrato.fecha_fuente` quedó **NULL** en las 18.929 filas. El comando reporta
`fuente=desconocida`. La propuesta dice que "registra la fecha de fuente" (2019-08-15),
pero no la persiste. Sin eso no queda trazabilidad de la vigencia del dato, que es
justo el argumento de auditoría del memo.

---

## 6. Punto 4 — PR-4 (estrato de la organización)

**No lo arranqué.** Dos razones, y quiero tu visto bueno antes de gastar el esfuerzo:

1. **Necesita DDL propio** (`estrato_ideca_org SMALLINT` en
   `inscripcion_banco_iniciativa`). Tú autorizaste la **Sección A**; esta columna no
   estaba en ese script. Es aditiva y de bajo riesgo, pero prefiero preguntarte.
2. **El hallazgo A es más urgente.** El arreglo del PIP (media hora) mejora el dato
   que alimenta todo lo demás, incluido el mapa.

Tu decisión sobre el método (aproximar por **barrio declarado**, mayoría/centroide de
sus manzanas, sin geocodificar la dirección) queda registrada y no la cuestiono: es
más robusta y tiene menos partes móviles.

---

## 7. Qué queda

**Todo lo técnico está en producción.** Lo pendiente es de decisión o de datos.

### Bloqueado por una decisión tuya / del Comité
1. **Enviar el memo.** La tabla de puntos se calibra sobre estratos **2, 3 y 4**;
   el estrato 1 no existe entre las sedes. Y `0` (sin estrato oficial, 65 sedes)
   debe puntuarse distinto de `NULL`.
2. **PR-7 — el criterio de scoring.** Sigue sin existir en `puntaje.py`. Espera la
   estructura (opción C recomendada) y la tabla estrato→puntos.

### Bloqueado por datos
3. **Deuda M22 — geometría de `barrio`.** 250 de 325 barrios sin geometría. Es lo
   único que impide resolver `estrato_ideca_org` para 15 de las 24 inscripciones.
   El código ya está: cargar la geometría lo desbloquea sin tocar nada.
4. **25 de 241 sedes con coordenadas fuera del contorno de Kennedy** (tabla
   `escuela`). Anotado, sin tocar, por instrucción tuya.

### Deuda menor anotada
- `banco.md` aún no documenta puntaje /105, ranking ni panel de comité — hay que
  hacerlo **antes de usarlo con Deportes**.
- La capa recortada pesa **8,7 MB**. Nginx la comprime, pero para un móvil sigue
  siendo mucho: valorar simplificación de geometrías si molesta en campo.
- `docs/infra/artefactos/requirements-lock.txt` ya está sincronizado (103 paquetes),
  pero conviene regenerarlo cada vez que cambie `requirements.txt`.

---

## 8. Estado de la base (verificado 2026-07-09)

```
manzana_estrato          18.929 filas   ✅
  distribución total     0:2456 1:2748 2:7762 3:5455 4:490 5:18
  DENTRO de Kennedy      4.826 filas    ⚠ (0:519 1:80 2:2377 3:1816 4:34 5:0)
  fecha_fuente           2019-08-15     ✅ (era NULL)

escuela.estrato_ideca    241 sedes
  con estrato 1-6        175            ✅ (era 127)
  estrato 0              65
  NULL                   1              ✅ (era 62) — sede 225, fuera de Kennedy
  estratos presentes     2, 3, 4        (el 1 no aparece: solo 1,7% del territorio)

PostGIS                  NO instalado   ✅ (BD compartida intacta)
innova_k                 imagen 8c7196bbb4a5, reconstruible ✅
  rollback               innovak-innova_k:rollback-20260709
```

---

## 9. PR-7 (bono por estrato) — BLOQUEADO. Dos hallazgos previos

Antes de escribir código para la rúbrica v4 revisé de dónde saldrían los datos.
No salen. Y al mirar, apareció algo más grande. **No implementé nada.**

### Hallazgo E — La tabla que enlaza inscripción → sede está vacía

`inscripcion_banco_escenario_detalle`: **0 filas**.

Es la tabla donde una inscripción declara en qué escenarios opera (`escuela_id`
→ el punto que ya tiene `estrato_ideca`). No está muerta: la creó el script
`007_banco_escenario_detalle.sql` y el formulario público **sí la escribe**
(`forms/inscripcion.py:945`). El problema es de cronología:

| Qué | Cuándo |
|---|---|
| Las 24 inscripciones del piloto | **2026-05-09** |
| Script 007 (crea `escenario_detalle`) | posterior |
| Scripts 008 / 009 (evaluación, comité) | posteriores |

Las 24 inscripciones **son anteriores a la captura de sedes**. Ninguna tiene sede.

Consecuencia directa sobre los 4 puntos que pediste:

- **Punto 1 (bono por estrato).** Las 24 inscripciones caen todas en la rama
  `NULL → 10 puntos`. El bono sería **una constante +10 para todos**: no ordena
  nada, no cambia un solo puesto del ranking. Los tests que pediste ("confirmar
  que el total ya incluye el bono") **pasarían en verde** mostrando exactamente
  eso, y el número se vería correcto.
- **Punto 2 (recalcular estrato al crear/editar sede).** Correcto y sin bloqueo.
  Es a futuro: aplica a inscripciones nuevas, no a las 24.
- **Punto 3 (filtrar el mapa a sedes del Banco).** Hoy renderiza **0 sedes**.
  Correcto como regla, vacío como resultado, hasta que entren inscripciones nuevas.
- **Punto 4 (tope de 93 cupos).** Hoy hay 24 ≤ 93 → no hay corte que aplicar.

El único estrato disponible por inscripción es `estrato_ideca_org` (por barrio
declarado, PR-4): **6 de 24**. El resto sigue bloqueado por la deuda M22.

### Hallazgo F — El bloque AUTO declara 65 puntos y entrega 10

Al medir los 24 `auto_detalle` ya calculados y guardados en BD:

| Criterio | Máx | Suma real | Prom | Con puntaje > 0 |
|---|---:|---:|---:|---:|
| C1 antigüedad | 10 | 170 | 7,08 | **24/24** ✅ |
| C2 territorialidad | 10 | 0 | 0,00 | 0/24 |
| C3 capacidad | 10 | 0 | 0,00 | 0/24 |
| C4 etario | 10 | 0 | 0,00 | 0/24 |
| C5 diferencial | 15 | 0 | 0,00 | 0/24 |
| C6 inclusión | 10 | 0 | 0,00 | 0/24 |
| **AUTO** | **65** | **170** | **7,08** | |

`puntaje_auto`: min 2 · máx 10 · promedio 7,08 **sobre 65**.
Ninguna de las 24 tiene nota de comité (`puntaje_comite` NULL, estado
`auto_calculado`). Es decir: **hoy el ranking del Banco es, literalmente, la
antigüedad de la organización.**

No es que falten datos. Cada criterio lee una fuente equivocada o vacía:

| Criterio | Lee de | Realidad en BD |
|---|---|---|
| C2 | `escenario_detalle` → `escuela.upz_codigo` | tabla 0 filas **y** `upz_codigo` NULL en las 241 escuelas |
| C3 | `personas_beneficiar` (varchar, claves `mas_41`, `31_40`…) | 0/24 poblado. Los datos viven en `rango_poblacion_codigo` (1–4) |
| C4 | `rango_etario` códigos **6–12** | el formulario persiste códigos **1–5**. El catálogo tiene las dos numeraciones solapadas |
| C5 | `enfoque_propuesta` M2M, códigos {1,2,3} | tabla **0 filas**. Los 28 registros están en `inscripcion_banco_enfoque` |
| C6 | idem, códigos {4,5,6} | idem |

C4 es el más claro: las inscripciones traen rangos etarios reales
(`[1, 2, 3, 5]`), el código busca 6–12, no encuentra, devuelve 0. No es un vacío
de datos, es un desalineamiento de catálogo.

C5/C6 no se arreglan renombrando la tabla: la semántica de los códigos difiere.
La rúbrica asume `{1 géneros diversos, 2 étnico, 3 discapacidad}`; el catálogo
real `enfoque_diferencial` dice `1 = discapacidad, 2 = mujeres, 3 = LGBTQI+`.

### Por qué esto frena PR-7

La rúbrica v4 congelaría una escala de 115 puntos en la que, en la práctica,
se reparten **10 de antigüedad + 10 de estrato**. El estrato pasaría a valer
~50 % del puntaje total — no por decisión de política, sino porque los otros
45 puntos del bloque AUTO están en cero por bugs. Y con el bono en NULL→10 para
las 24, ni siquiera el estrato ordenaría: sería +10 parejo.

Esto asigna 93 cupos de recurso público. Es el peor momento posible para
congelar una rúbrica formal.

### Recomendación

Orden distinto al que pediste, por dependencia de datos, no por preferencia:

1. **PR-A — arreglar C2..C6** (`fix/banco-rubrica-fuentes`). Realinear cada
   criterio a su fuente real, recalcular las 24, y comparar el ranking antes/
   después. Sin DDL. Es donde están los 45 puntos perdidos.
2. **PR-B — poblar las sedes de las 24** o decidir explícitamente que el bono
   se toma de `estrato_ideca_org` (barrio) y no de la sede. Decisión tuya.
3. **PR-C — PR-7 (bono estrato) + rúbrica v4**, ya sobre una base que mide algo.
4. **PR-D — automatización por sede** (tu punto 2). Independiente, sin bloqueo.
5. **PR-E — filtro del mapa** (tu punto 3). Independiente, sin bloqueo.
6. **PR-F — tope 93 dinámico** (tu punto 4). Último: depende de que el total
   signifique algo.

**PRs separados**, respondiendo tu pregunta: tocan modelo, endpoint y ranking,
y sobre todo PR-A cambia números que el Comité ya podría haber visto. Cada uno
debe poder revertirse solo.

### Deuda nueva registrada

- **`auto_detalle` está doble-codificado**: es un `jsonb` que contiene un *string*
  JSON, no un array. `auto_detalle->'C2_territorialidad'` devuelve NULL siempre.
  Cualquier query analítica sobre ese campo falla en silencio.
- `RUBRICA_AUTO["bloque_auto_max"] = 30` mientras `calcular_caracterizacion()`
  devuelve `"max": 65`. El snapshot de `banco_rubrica` guarda el 30.
- `banco_rubrica` no tiene columna `id`.
- `BancoEvaluacionInscripcion` **no tiene columna `bono_estrato`** → PR-C
  necesitará DDL aditivo (nullable) + backup.
- `total` se calcula en **dos** lugares (`guardar_caracterizacion()` y
  `_recalcular_total()`). Ambos habría que tocar.
