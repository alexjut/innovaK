# Georreferenciación

Mapa de Kennedy, capas territoriales (UPZ, barrios, parques) y las escuelas de
Cultura y Deportes.

El mapa es **público desde 2026-07-30**: `/app/mapa` se abre sin login. Cuatro
capas siguen exigiendo sesión —Festivales, Malla vial / obras, Parques (obras) e
Iniciativas del Banco—; el panel lo dice al lado del check en vez de fallar en
silencio.

---

## 1. Cobertura de barrios: son DOS cifras, no una

Se confunden con facilidad y ya causaron un enredo. Ambas al 2026-07-30:

| Medida | Valor | Qué responde |
|---|---|---|
| Barrios con geometría **en la base** | **155 de 325 = 47,7 %** | Qué tan completa está la tabla `barrio` |
| Polígonos **que muestra el mapa** | **222** | Qué ve efectivamente el ciudadano |

El mapa muestra más porque el endpoint sirve la **unión**: la base (fuente de
verdad) más los sectores del archivo semilla que la base todavía no cubre. Servir
solo desde la base habría sido un retroceso — la cobertura del archivo sobre el
contorno de Kennedy es 99,2 % contra 66,8 % de la base sola.

Citar una por la otra da una idea equivocada del estado del dato. Si vas a
reportar cobertura, di cuál de las dos estás usando.

### Corrección histórica: el "79 sin geometría"

El número **79** viene del registro de **abril de 2026**, cuando la tabla
`barrio` tenía **111 filas** y 32 con geometría. Era correcto entonces.

La tabla creció a **325 filas** y ese número **nunca se volvió a derivar**: se
arrastró como si siguiera vigente hasta el 2026-07-30, y así entró al
diagnóstico de esa tarea. **El dato correcto de partida era 250 sin geometría**
(325 − 75), no 79.

Reconciliación: 75 antes de IDECA + 80 recuperados de IDECA = 155 con geometría
hoy; 325 − 155 = **170 sin casar** (`data/m22_barrios_sin_geometria.csv`).

Queda escrito en vez de corregido en silencio: sin la fecha y el denominador, el
siguiente que lo lea vuelve a citarlo mal.

---

## 2. La regla que salió de ahí

**Toda cifra se reporta con su denominador y su fecha.**

Un porcentaje sin universo está incompleto, y un número heredado de un documento
viejo se re-deriva contra la base antes de usarlo.

En esa misma tarea se reportaron porcentajes territoriales calculados sobre las
424 filas de `escuela` cuando el universo correcto eran las **278 activas** — las
otras 146 están dadas de baja y no se pintan en el mapa.

---

## 3. Qué hay en el módulo

| Archivo | Qué es |
|---|---|
| `services/resolver_territorio.py` | Cruce punto-en-polígono en Python. PostGIS **no está instalado** en el servidor (la extensión no existe, no es un tema de permisos), así que el cruce va sobre el JSONB. Son 278 escuelas contra 325 barrios: cómputo trivial |
| `services/capa_barrios.py` | Arma la unión BD + semilla que sirve el mapa (§1) |
| `services/diagnostico.py` | Separa cuatro desenlaces: `ok`, `sin_hit` (buscó y no encontró), `no_intentado` (ni llegó a buscar) y `error` (reventó y alguien se tragó la excepción) |
| `management/commands/cargar_censo_escuelas.py` | Carga y reconciliación del censo. `--dry-run` por defecto; escribe solo con `--apply` |
| `management/commands/resolver_territorio_escuelas.py` | Aplica la resolución territorial a la tabla |
| `management/commands/recuperar_barrios_ideca.py` | Trae geometrías de IDECA |
| `api/views.py` · `views/apis.py` | Endpoints del mapa (`/geo/api/*`) |

### Por qué `no_intentado` es su propia categoría

Un resumen que dice "2 sin resolver" cuando hubo 2 sin hit **y 134 que jamás se
intentaron** no informa: tranquiliza. Al correr el barrido apareció justo eso —
146 de 149 intentos de `url_maps` nunca se hicieron, y 2 de ellos eran un agujero
real invisible en el resumen viejo.

### Sin emparejamiento difuso, a propósito

Con umbral 0,88 el algoritmo proponía `PATIO BONITO I` → `PATIO BONITO II`. Son
barrios distintos: habrían quedado sedes en el lugar equivocado, con cara de dato
resuelto. **Se prefiere el hueco visible al dato falso**, y ese criterio se
aplica en todo el módulo — es también el que gobierna cómo el mapa trata las
actividades sin ubicación (§4).

---

## 4. Actividades sin ubicación propia

`get_lugar_incidencia_default()` (en `utils.py`) ubica en la **sede de la
Alcaldía** todo evento creado sin coordenadas. Es una decisión de 2026-06-11 para
que ningún evento desaparezca del mapa.

El efecto secundario es que se apilan en un mismo punto y parecen hechos
ocurridos ahí. Por eso el GeoJSON marca **`ubicacion_aproximada`**: el mapa los
desapila en abanico, los pinta con borde punteado, lo advierte en el popup y los
cuenta aparte. No se les inventa coordenada.

La solución de fondo es capturar la dirección real en la actividad, con
autocompletado contra Catastro y pin en el mapa (ya existe
`shared/direccion/direccion-picker.component.ts` en el frontend).

---

## 5. Cómo correr los tests

```bash
docker exec innova_k python scripts/run_smoke_tests.py
```

Los tests del resolver son `unittest.TestCase` puro con **polígonos de juguete**
y no tocan BD — por eso el cruce se escribió sin dependencias geométricas. El
repo es **público**: nada de cédulas, nombres ni direcciones reales de la base en
tests, docs ni mensajes de commit.
