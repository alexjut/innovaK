# Estado del worktree — mapa de escuelas, censo julio 2026

Rama `feat/mapa-escuelas-censo-julio`.

**Historial de la decisión, que cambió:**

- **2026-07-30** — el gate a `desarrollo` **NO pasó**. Nada commiteado.
- **2026-08-03** — commiteado como checkpoint (`cfd0d14`) y, por decisión
  expresa de Alex ese mismo día, **cascadeado a producción con los pendientes
  §2.5 y §2.6 todavía abiertos**. El gate se levantó a mano; no se cerró.

Lo que sigue pendiente lo sigue estando, y ahora está en producción: los tres
CSV para el área **sin revisar** (§2.5) y el README del módulo **como stub con
un TODO** (§2.6). Eso es deuda asumida a conciencia, no trabajo terminado.

Este archivo existe para poder retomar sin reconstruir contexto. Si algo acá
contradice al chat, manda esto.

---

## 1. Aplicado en la base y verificado

Estas tres cosas **ya están escritas en `poblacion_kennedy`**, que es la misma
base que sirve producción. No son un borrador.

| | Estado |
|---|---|
| **DDL 014** (15 columnas, 3 constraints, 4 índices) | Aplicado. Probado aplicar→revertir: la tabla queda idéntica |
| **Carga del censo** | Aplicada. **Idempotencia verificada**: segunda corrida da 0 bajas, 0 actualizadas, 0 nuevas, 0 escrituras |
| **Fix de doble codificación** en `barrio.geometry` | Aplicado. Verificado: las 155 geometrías parsean a objeto en un paso |
| **Resolución territorial** | Corrida **después** del fix, sobre las 424 filas |

Backup previo a todo: `poblacion_kennedy_pre_escuelas_20260730_113647.dump`
(57 MB, integridad verificada).

**Sobre el "bug de doble codificación": la alarma inicial era falsa en parte.**
Que el JSONB vuelva como texto por cursor crudo es comportamiento del conector
de este proyecto, no el bug — `upz.geometry` también vuelve como texto y la
resolución de UPZ funciona perfecto. El bug real era que al parsear una vez
quedaba **texto otra vez**. La prueba correcta es esa: parsear una vez y ver si
queda objeto. Hoy no queda ninguna mal.

---

## 2. NO hecho — punto exacto de reanudación

**Se arranca por los tres tests. Son los más baratos y los que más protegen.**

1. ~~**Test de doble codificación**~~ — HECHO. `DobleCodificacionTests`
   (6 tests) + `parsea_en_un_paso()` en el servicio.
2. ~~**Test de cruces en cero**~~ — HECHO. `CrucesEnCeroTests` (8 tests) +
   `exigir_cruces()`/`CrucesEnCeroError`, enganchado en el comando.
3. ~~**Test de idempotencia**~~ — HECHO. `IdempotenciaRealTests` (5 tests):
   dos corridas contando `execute`, no leyendo el resumen.
4. ~~**Barrido de fallos silenciosos**~~ — HECHO. `services/diagnostico.py`
   con cuatro desenlaces (`ok` / `sin_hit` / `no_intentado` / `error`), los dos
   comandos anotando y el bloque impreso al cerrar. Ver §8.
5. **Revisión de los tres CSV** del área — sin columnas internas, encabezados
   legibles sin contexto técnico, y cada fila diciendo qué se necesita de ellos.
6. **README del módulo** — con las dos cifras de cobertura y la corrección
   histórica (§4).

---

## 3. Cifras corregidas, con su denominador · 2026-07-30

**Toda cifra va con el universo sobre el que se calculó.** Ese fue el error de
método que se cometió acá (§4).

### Universo

```
424 filas en `escuela`
 ├── 278 ACTIVAS   =  85 Cultura  + 193 Deportes (SEDES, no las 247 de detalle)
 └── 146 INACTIVAS =  70 Cultura  +  76 Deportes   (abril, no reportadas en julio)
```

Verificado con:
`SELECT tipo, estado, COUNT(*) FROM escuela GROUP BY tipo, estado ORDER BY 1,2;`

Las 278 activas son **exactamente** el censo de julio. El conteo de sedes (193)
y el de detalle (247) **no se cruzaron** en ningún punto del pipeline.

### Territorio — sobre las 278 ACTIVAS

| | n |
|---|---|
| Barrio resuelto | 182 |
| Cercano a 80 m del borde | 24 |
| Sin polígono de barrio | 29 |
| Sin coordenada | 43 |
| **Con barrio, de las 235 pintables** | **206 = 87,7 %** |

UPZ: **381 de 381 filas con coordenada** quedaron ubicadas (incluye las 146
inactivas). Ninguna fila con coordenada quedó sin ubicación administrativa.

### Barrios — DOS cifras distintas, no confundirlas

| | |
|---|---|
| **Con geometría en la base** | **155 de 325 = 47,7 %** |
| **Polígonos que muestra el mapa** | **222** |

El mapa muestra más porque sirve la **unión**: la base (fuente de verdad) más
los sectores del archivo semilla que la base todavía no cubre. Servir solo de
base habría sido un retroceso — la cobertura del archivo sobre el contorno de
Kennedy es 99,2 % contra 66,8 % de la base sola.

### Corrección histórica: el "79 sin geometría"

El número **79** viene del registro de **abril de 2026**, cuando la tabla
`barrio` tenía **111 filas** y 32 con geometría. Era correcto entonces.

La tabla creció a **325 filas** desde entonces y ese número **nunca se volvió a
derivar**: se arrastró como si siguiera vigente, y así entró al diagnóstico de
esta tarea.

**El dato correcto de partida era 250 sin geometría** (325 − 75), no 79.

Reconciliación: 75 antes de IDECA + 80 recuperados = 155 con geometría hoy;
325 − 155 = 170 sin casar.

---

## 4. Los dos errores de método, y cómo se evitan

Estos dos no son bugs de código: son de razonamiento, y son los que causaron el
enredo. Quedan escritos para no repetirlos.

### a) Porcentajes calculados sobre el universo equivocado

Se reportó *"288 resueltas, 42 cercanas, 51 sin polígono"* sumando **activas e
inactivas**. Las 146 dadas de baja no cuentan para la cobertura del mapa: no se
pintan. El porcentaje real es sobre las 278 activas.

**Cómo se evita:** ninguna cifra se reporta sin decir sobre qué universo se
calculó. Si un número no trae denominador, está incompleto.

### b) Número arrastrado sin fecha ni denominador

El "79" se citó durante toda la tarea sin verificar que su denominador (111
filas) siguiera siendo el actual (325).

**Cómo se evita:** todo número heredado de un documento viejo se re-deriva
contra la base antes de usarlo, o se cita con su fecha y su denominador
explícitos. Un número sin fecha es una afirmación sin respaldo.

---

## 5. Hallazgos técnicos que conviene no perder

- **PostGIS no está disponible** y no es cuestión de permisos: la extensión ni
  siquiera está instalada en el servidor (`postgis.control` no existe) y
  `innova-bd` no es superusuario. El cruce punto-en-polígono va en Python sobre
  el JSONB. Decisión de Alex: no insistir ni escalar.
- **El endpoint de barrios servía un archivo estático.** Recuperar geometrías de
  IDECA no habría ampliado el hover ni un barrio. Ya se corrigió (unión BD +
  semilla), pero es el tipo de desconexión que hace invisible un trabajo entero.
- **Sin emparejamiento difuso en barrios**, a propósito: con umbral 0,88 el
  algoritmo proponía `PATIO BONITO I` → `PATIO BONITO II`. Son barrios distintos
  y habrían quedado sedes en el lugar equivocado con cara de dato resuelto.
- **La marca de discrepancia compara dos vocabularios.** El área digita el nombre
  popular (CASTILLA, BELLAVISTA) y el catálogo usa el catastral. Sin filtrar por
  vocabulario comparable se marcaba el 93 % en rojo, y un reporte así no lo
  revisa nadie.

  **Corrección de la cifra (2026-07-30, re-derivada contra la BD).** Acá decía
  *"52 de 85 nombres declarados no existen en el catálogo"*, y ese 52 no sale de
  ningún lado — cayó en el error de método §4a, un número sin denominador. Lo
  medido, con su universo cada uno:

  | | n |
  |---|---|
  | Filas con barrio declarado | **85** |
  | Nombres DISTINTOS declarados | **63** |
  | De esos nombres distintos, fuera del catálogo | **47 de 63** |
  | Filas cuyo nombre no es comparable | **61 de 85** |
  | Filas auditables (declarado y resuelto, ambos en el catálogo) | **19** |
  | De esas, discrepan de verdad | **14** |

  Las 14 discrepancias reales se sostienen. El "52" era una mezcla de dos
  denominadores distintos.
- **Los 31 sin dirección son 29 sedes** (31 filas de detalle, dos nombres
  repetidos). **Las direcciones vacías eran 2, no 6.** **Aparearon 95, no 105.**
  Las tres cifras del diagnóstico inicial estaban infladas.

---

## 6. Mapa de archivos — dónde está cada cosa

Todo cuelga de `apps/georeferenciacion/`.

| Archivo | Qué es |
|---|---|
| `services/resolver_territorio.py` | Cruce punto-en-polígono en Python. **Acá van los tests 1 y 2.** Entradas: `punto_en_geometria(x, y, geom)`, `resolver_barrio(...)`, `resolver_upz(...)`, `resolver_punto(...)`. La clase `Poligono(codigo, nombre, geom)` envuelve cada candidato |
| `services/capa_barrios.py` | Arma la unión BD + semilla que sirve el mapa |
| `management/commands/cargar_censo_escuelas.py` | Carga y reconciliación. **Acá va el test 3** (idempotencia). `--dry-run` por defecto, `--apply` escribe |
| `management/commands/resolver_territorio_escuelas.py` | Aplica la resolución a la tabla |
| `management/commands/recuperar_barrios_ideca.py` | Trae geometrías de IDECA |
| `services/diagnostico.py` | Contadores del barrido de fallos silenciosos: cuatro desenlaces (`ok`/`sin_hit`/`no_intentado`/`error`), motivos y cuadre (`sin_anotar`) |
| `tests/test_resolver_territorio.py` | Cruce espacial + `DobleCodificacionTests` y `CrucesEnCeroTests` |
| `tests/test_censo_escuelas.py` | Carga + `IdempotenciaRealTests` (cuenta escrituras, no lee el resumen) |
| `tests/test_diagnostico.py` | El barrido: desenlaces, geometría anotada, apareo y `Ubicador` |
| `scripts/014_escuela_censo_julio.sql` | El DDL, con su rollback al lado |
| `data/m22_barrios_sin_geometria.csv` | Los 170 barrios sin casar |
| `views/apis.py` | `api_kennedy_escuelas` y `api_kennedy_barrios` |

Frontend: `frontend/src/app/features/mapa/mapa.component.ts` (popup + hover) y
`core/geo/geo.service.ts`.

Fuentes del censo, fuera del repo, en `/home/innova/Proyectos/`:
`escuelas_cultura.json` (85), `escuelas_deportes_sedes.json` (193),
`escuelas_deportes_detalle.json` (247).

### Cómo correr los tests

```bash
docker exec innova_k python scripts/run_smoke_tests.py
```

**Línea base: 991 corridos, 0 fallos, 9 saltados** dentro del worktree (el árbol
principal da 872 porque no tiene este código). Los tres módulos nuevos están
registrados en `scripts/run_smoke_tests.py`.

> **Corrección de la línea base anterior.** Acá decía "948 OK, 9 saltados". El
> 948 era el número de tests CORRIDOS, no de tests en verde, y entre ellos había
> **uno en rojo**: `DiscrepanciaTests.test_en_la_resolucion_completa` afirmaba
> discrepancia sobre un nombre declarado que no está en el catálogo, o sea
> contradecía el filtro de vocabulario de §5. Es una aserción anterior a esta
> sesión —quedó cuando se agregó el filtro— y se reparó en commit aparte.

Los tests son `unittest.TestCase` puro con datos inventados — el repo es
**público**, así que nada de cédulas, nombres ni direcciones reales de la base.
Los del resolver usan polígonos de juguete y no tocan BD, que es justamente por
lo que el cruce se escribió sin dependencias geométricas.

---

## 7. Cómo correr los comandos

El contenedor `innova_k` monta el **árbol principal**, no este worktree. Para
correr con este código hace falta un contenedor efímero:

```bash
docker run --rm \
  --env-file /home/innova/Proyectos/innovaK/.env \
  -e DJANGO_SETTINGS_MODULE=core.settings -e REDIS_URL=redis://redis:6379/0 \
  --network innovak_default \
  --add-host host.docker.internal:host-gateway \
  -v /home/innova/Proyectos/innovaK/.claude/worktrees/mapa-escuelas:/app \
  -v /home/innova/Proyectos:/tmp \
  -w /app innovak-innova_k python manage.py <comando>
```

El `--add-host` **no es opcional**: sin él la base no resuelve. Y las fuentes
JSON tienen que quedar montadas en `/tmp`, que es donde el comando las busca.

---

## 8. Barrido de fallos silenciosos — qué mide y qué encontró

`services/diagnostico.py`. Cuatro desenlaces, excluyentes a propósito:

```
ok            encontró
sin_hit       buscó y no encontró          ← "no encontré"
no_intentado  ni siquiera llegó a buscar   ← "encontré nada"
error         reventó y alguien se tragó la excepción
```

`no_intentado` es el que faltaba. Un resumen que dice "2 sin resolver" cuando
hubo 2 sin hit **y 134 que jamás se intentaron** no informa: tranquiliza.

### Lo que apareció al correrlo (dry-run, 2026-07-30)

- **`url_maps`: 146 de 149 intentos NO se intentaron.** 134 por `--sin-red`, 10
  sedes sin enlace, 2 con enlace sin coordenada que no es corto — esos 2 eran el
  agujero original, invisibles en el resumen viejo.
- **El apareo cuadra: 278 sedes del censo = 278 anotadas.** Si no cuadra, hay una
  rama del join comiéndose registros y el comando lo grita.
- **Las 155 geometrías de barrio parsean en un paso, 0 dobles.** El fix de §1
  aguantó, y ahora se comprueba en cada corrida en vez de a mano.
- **UPZ: 381 resueltas de 381 con coordenada** (43 sin punto). Cuadra con §3.
- **El barrido encontró un fallo en el propio barrido.** La primera versión
  etiquetaba 66 filas como "vocabulario no comparable" cuando solo 61 lo son:
  las otras 5 tienen el nombre en el catálogo y quedaron sin comparar porque no
  se resolvió barrio. Dos causas distintas bajo una etiqueta — exactamente el
  pecado que esto persigue. Corregido: ahora son `no_intentado` y `sin_hit`.

### Floats y fechas: auditados, sin hallazgo

No hay comparación de floats por igualdad en ningún cruce (las distancias van
con `<`/`<=` contra umbrales con nombre). El único `==` es la guarda de segmento
degenerado en `_dist_punto_segmento`, donde la igualdad exacta ES lo correcto.
Y no hay comparación de fechas entre tipos: `fecha_baja` se escribe pero no se
relee para decidir nada.
