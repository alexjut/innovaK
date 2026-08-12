# Banco de Iniciativas — dónde quedó el trabajo (2026-08-12)

Punto de retomada tras dos jornadas sobre `feat/banco-matriz-oficial-cableado`.
**Nada está commiteado**: 32 archivos en el árbol de trabajo, 1.184 tests en
verde. Este documento es para poder volver sin releer el código.

---

## 1. Lo que quedó funcionando

### La matriz oficial ya es la que califica

Hasta el 2026-08-10 el motor de 100 puntos existía y estaba probado, pero **no
era el que calificaba**: la API seguía corriendo `services/puntaje.py` (el
modelo viejo de 65 automáticos + 35 de comité + 5 de bono). El ranking que veía
el usuario no era el del documento vigente.

- `services/ranking_oficial.py` (nuevo) — persiste, rankea y resuelve cupos.
- `api/evaluacion_views.py` — corre la matriz oficial; el endpoint del comité
  responde **409** con el motivo (la ruta sobrevive para que un cliente viejo
  no reciba un 404 mudo).
- `api/evaluacion/ranking/` (nuevo) — orden de adjudicación del evento.
- Frontend: el panel de comité salió; en su lugar van los 12 criterios, el tope
  financiable, la posición y los supuestos que están corriendo.
- `recalcular_matriz_oficial` (comando nuevo), **seco por defecto**.

**Sin DDL**: cabe en el schema viejo (`puntaje_auto` = total de 100,
`puntaje_comite` = NULL, `bono_genero` = 0).

**Ya aplicado**: las 24 del piloto quedaron en `oficial-2026-07-29`, ranking
1–24. Las rúbricas v1–v4 quedan congeladas en `banco_rubrica` para auditoría.

### Arraigo territorial (§4.2) — cerrado

El Documento Guía lo resolvió por una **tercera vía**: el tipo de espacio dejó
de puntuar en la caracterización (sigue valiendo 9 puntos en §7.9.1, que es de
la propuesta) y los 4.0 pasaron al **estrato del entorno**: 1 y 2 → 4.0,
3 → 2.0, 4 → 0.0.

**Sin estrato 0**, por decisión de Alex: los CHECK de la tabla son 1–4, así que
un 0 no puntuaría mal — haría que Postgres **rechazara la radicación entera**;
y el recibo de servicio público que el propio documento exige como soporte no
existe para un predio sin estratificar.

### Guardado progresivo — dos capas

`localStorage` ya existía; se le sumó `PUT …/publico/<id>/borrador/`
(Mongo cifrado, token `<mongo_id>.<hmac>`). Al retomar gana **el más reciente
de los dos**, no el servidor por ser servidor: si alguien siguió escribiendo
sin señal, lo bueno está en el aparato.

El borrador **no cabe en Postgres** (la tabla tiene 7 columnas NOT NULL) y
lleva cédulas adentro, así que va a Mongo cifrado. Purga a los 30 días con
`purgar_borradores_banco` (seco por defecto) — **falta meterla al cron**.

### Soportes que condicionan el puntaje

```
puntúa y no sube soporte  →  ese subcriterio queda en 0
puntúa y sí lo sube       →  puntúa normal
no puntúa                 →  no se le pide nada
piloto (formulario viejo) →  exento, intacto
```

**DDL 014 aplicado** (OK de Alex, backup verificado): el CHECK de
`inscripcion_banco_anexo.tipo` pasó de 8 a 17 tipos + prefijo `enfoque\_%`.
Script y rollback en `apps/banco_iniciativas/scripts/`.

La compuerta es **por subcriterio**, no por criterio: que falte el listado del
staff no puede tumbar la trayectoria, que sí está certificada.

---

## 2. Tres trampas que costaron rato

No son evidentes y volverían a costar lo mismo:

1. **`banco_evaluacion_inscripcion.rubrica_version` tiene FK a
   `banco_rubrica.version`.** Sin registrar antes el snapshot de la rúbrica,
   guardar una evaluación revienta con ForeignKeyViolation.

2. **`auto_detalle` es JSONB y no siempre es un dict.** El motor viejo guarda
   una **lista**; la matriz oficial guarda el dict completo. Un `.get()` a
   ciegas tumba los insights. Todo pasa por `detalle_oficial()`.

3. **`now()` de PostgreSQL es la hora de inicio de la TRANSACCIÓN.** Filas
   creadas juntas comparten `created_at` al microsegundo, y el desempate «gana
   quien radicó primero» se queda sin criterio — el orden lo decidía la base,
   al azar, justo donde se decide quién recibe \$17 M. Cierre: el número de
   radicación como último desempate.

Y una cuarta, del propio trabajo de estos días:

4. **`es_formulario_anterior` no alcanza sola** para decidir a quién se le
   exigen soportes: mira 8 columnas del Documento Maestro y `arraigo_estrato`
   no está entre ellas. `exige_soportes()` decide en 3 pasos —
   `forzar_soportes` → `radicado_at` → la heurística como respaldo.

---

## 3. Lo que falta

### De código (nuestro)

| | Qué | Notas |
|---|---|---|
| 1 | **§5.2 dinámico** — un cargue por cada casilla de enfoque marcada | La base ya lo acepta por prefijo: **no vuelve a necesitar DDL** |
| 2 | **Pre-validación por sección en Angular** | Hoy el error sale al enviar. Deliberado: no se duplicó la lógica de puntaje en el frontend |
| 3 | **Commitear y cascadear** | 32 archivos, nada commiteado |
| 4 | Meter `purgar_borradores_banco` al cron | Habeas data: borradores con cédulas |
| 5 | Borrar `ONEDRIVE_TOKEN` y `ONEDRIVE_UPLOAD_URL` de `core/settings.py` | Variables muertas que nadie lee; inducen a error |

### De Deportes (bloquean publicar ranking)

Todo está escrito en `docs/propuestas/banco_decisiones_deportes_2026-08-10.md`.
Son cinco líneas de respuesta:

1. **Tope §8.5** — aprobar bandas por puntaje (75/60/0). Sin esto §8.5 no se
   puede activar: la posición no existe al radicar.
2. **Menos de 93 postulaciones** — ¿todas entran, o hay puntaje mínimo?
3. **Piloto de mayo** — ¿las 24 se repostulan, o se cierra aparte? Su techo es
   30, no 100.
4. **Estrato 0** — ratificar que se descarta.
5. **Desempate** — ratificar la regla aplicada.

Menor: **«Incentivos económicos»** (código 5) sigue sin aparecer en la escala
de democratización del documento. Hoy corre en 0.0 por supuesto nuestro.

### De la Alcaldía

- **Credenciales de Entra ID** para activar OneDrive: `TENANT_ID`, `CLIENT_ID`,
  `CLIENT_SECRET`. El `.env` ya tiene las casillas creadas y vacías. El
  `DRIVE_ID` ya no hace falta: basta `ONEDRIVE_USUARIO` con el correo.
  Ver [[onedrive-espejo-soportes]] y el texto para TI en la sesión.
  **Los anexos NO dependen de esto** — Mongo guarda los originales; OneDrive es
  solo la copia legible.
- **`ONEDRIVE_CARPETA_RAIZ`** en el `.env` dice `Banco de Iniciativas` y eso
  pisa el default nuevo. Cambiar a `Banco/aspirantes`.
- **Certificado de residencia (§1)**: decidir si es regla de elegibilidad
  excluyente o solo informativa. Hoy se pide sin bloquear.

---

## 4. Cabo suelto que no es de este frente

Tres archivos staged de **estratificación** (`sync_estratificacion --bogota`,
`capas.py`, `sync_fuentes_oficiales`) venían de antes y viajan en esta rama.
Rompían 3 tests de `test_sync_orquestador`, que **se invirtieron** para que el
guardia proteja la decisión nueva: que nadie devuelva estratificación a
`sync_capa`, que es lo que dejaba 26.122 manzanas sin `fecha_fuente`.
