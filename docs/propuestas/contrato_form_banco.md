# Contrato del POST — Formulario público del Banco de Iniciativas

**Documento Maestro oficial 2026-07-29** · 9 secciones · 100 puntos autoliquidados.
Backend implementado en `apps/banco_iniciativas/forms/inscripcion.py` y expuesto por
`apps/banco_iniciativas/api/public.py`. Este archivo es el contrato que consume el
wizard Angular (`frontend/src/app/features/publico/banco-publico.component.ts`).

```
GET  /banco-iniciativas/api/publico/<evento_id>/catalogos/   → catálogos + reglas
POST /banco-iniciativas/api/publico/<evento_id>/inscribir/   → radica (multipart)
```

`Content-Type: multipart/form-data` **obligatorio**: en el mismo POST viajan los
cinco anexos. Las colecciones van como **texto JSON** dentro de campos del
multipart (no como `application/json`).

Respuestas: `201 {id, detail}` · `400 {detail, errors:{campo:[msg]}}` ·
`410` convocatoria cerrada · `404` evento que no admite inscripción.

---

## 1. Cabecera — nombres de campo del modelo

`req` = obligatorio server-side. `cond` = obligatorio según otra respuesta.

### §1 Registro de la organización

| Campo | Tipo | Oblig. | Nota |
|---|---|---|---|
| `nombre_organizacion` | texto (255) | req | §1.1 |
| `tipo_organizacion` | código (int) | req | §1.2 · catálogo `tipos_organizacion` |
| `numero_soporte_legal` | texto (100) | opt | §1.3 · NIT/resolución. Se denormaliza a `organizacion.nit` solo si el tipo es 8 (personería jurídica) |
| `rep_nombre1`, `rep_apellido1` | texto (80) | req | §1.5 |
| `rep_nombre2`, `rep_apellido2` | texto (80) | opt | §1.5 |
| `rep_tipo_doc` | código (int) | req | §1.6 · excluye NIT (código 5) |
| `rep_numero_doc` | texto | req | §1.7 · 5–15 dígitos |
| `nivel_educativo` | código (int) | opt | §1.9 |
| `titulos_obtenidos` | texto largo | opt | §1.10 |

### §2 Contacto y ubicación

| Campo | Tipo | Oblig. | Nota |
|---|---|---|---|
| `telefono` | texto (50) | req | §2.1 |
| `correo` | email | req | §2.2 |
| `tiene_sede_fisica` | `si` \| `no` | req | compuerta condicional |
| `barrio` | código | cond | §2.3 · req si `tiene_sede_fisica=si` |
| `direccion` | texto | cond | §2.4 · req si `tiene_sede_fisica=si` |
| `direccion_lon`, `direccion_lat` | float | opt | del picker (Catastro + pin). Viajan juntos o se descartan los dos |
| `estrato` | 1–4 | cond | §2.5 · req si `tiene_sede_fisica=si`. **No existe el 5** |
| `redes_web`, `redes_facebook`, `redes_instagram` | url | opt | §2.6–§2.8 → JSONB `organizacion.redes_sociales` |
| `upl`, `upz`, `barrio_texto` | código/texto | opt | no están en el documento; la UPZ se resuelve del punto si no la mandan |

Con `tiene_sede_fisica=no` el servidor guarda `barrio`, `direccion`, `estrato`,
`upl`, `upz` y el punto en **NULL controlado** y no reporta error.

### §3 Capacidad de la organización (12 pts)

| Campo | Tipo | Oblig. | Nota |
|---|---|---|---|
| `tamano_staff_num` | entero ≥ 1 | req | §3.1 · **número exacto** (los brackets >41/31-40/21-30 no se derivan del rango legacy) |
| `anios_experiencia` | código | req | §3.2 · bandas nuevas del 013 (códigos 6–10) |
| `composicion_organizacion` | código corto | req | §3.3 · `solo_mujeres`\|`mayor_mujeres`\|`diversas`\|`equitativo`\|`mayor_hombres`\|`solo_hombres` |
| `rango_poblacion` | código | req | §3.4 · bandas nuevas del 013 (códigos 5–8) |

`tamano_organizacion` (rango legacy) lo **deriva el servidor** del número exacto.

### §4 Arraigo territorial (4 pts)

| Campo | Tipo | Oblig. | Nota |
|---|---|---|---|
| `modalidad_actividad` | código (1–5) | req | §4.1 |
| `disciplina_actividad` | código | cond | §4.1 · req si no manda `disciplina_actividad_otro` |
| `disciplina_actividad_otro` | texto (150) | cond | §4.1 "Otros" |
| `arraigo_red` | código de `red` | req | §4.2 · **el nivel es lo que puntúa** |
| `escenarios_actuales` | lista de códigos | cond | botones del nivel; req si no manda `arraigo_escenario_otro` |
| `arraigo_escenario_otro` | texto (150) | cond | |
| `arraigo_espacio_nombre` | texto (150) | req | bloque de localización |
| `arraigo_direccion` | texto (200) | req | bloque de localización |
| `arraigo_lon`, `arraigo_lat` | float | opt | del picker |
| `arraigo_estrato` | 1–4 | req | |
| `arraigo_actividad` | texto largo | req | |

Los escenarios marcados **tienen que pertenecer al nivel elegido**
(`escenario.categoria_pot == arraigo_red`). Mezclar niveles hace el puntaje
indefendible y el servidor lo rechaza.

### §5 Diversidad e inclusión (10 pts)

| Campo | Tipo | Oblig. | Nota |
|---|---|---|---|
| `rango_etarios` | lista de códigos | req | §5.1 |
| `enfoques` | JSON (ver §2 de este doc) | req | §5.2 **y** §7.8 |

### §6 Participación (4 pts)

| Campo | Tipo | Oblig. | Nota |
|---|---|---|---|
| `participa_espacio` | `si` \| `no` | req | compuerta |
| `instancias` | lista de códigos (1–5) | cond | §6.1 · req si `participa_espacio=si`. Solo se persisten si declaró `si` |
| `beneficio_alk` | código (1–8) | req | §6.2 · selección **única**, escala inversa |

`beneficiada_alk` y el M2M `beneficios_alk` los **deriva el servidor** de
`beneficio_alk` (código 7 «Sin apoyos previos» → `beneficiada_alk=false`).

### §7 Formulación de la iniciativa (70 pts)

| Campo | Tipo | Oblig. | Nota |
|---|---|---|---|
| `problematica` | texto largo | req | §7.1 · **mínimo 200 caracteres** |
| `justificacion` | texto largo | req | §7.2 · **mínimo 200 caracteres** |
| `modalidad_propuesta` | código (1–5) | req | §7.3 |
| `disciplina_principal` / `otros_deportes` | código / texto | cond | §7.3 · uno de los dos |
| `objetivo_general` | texto (500) | req | §7.4.1 |
| `objetivos_especificos` | JSON `["t1","t2","t3"]` | req | §7.4.2 · **exactamente 3** |
| `cobertura_staff` | `ge_50`\|`11_49`\|`4_10`\|`min_3` | req | §7.5.1 |
| `cobertura_comunidad` | `gt_80`\|`51_80`\|`41_60`\|`21_40`\|`min_20` | req | §7.5.2 |
| `cobertura_indirectos` | `gt_200`\|`101_200`\|`51_100`\|`hasta_50` | req | §7.5.3 |
| `ciclo_vital` | lista de códigos | req | §7.6 · distinto de `rango_etarios` |
| `diversidad_genero_propuesta` | `solo_mujeres`\|`mayor_mujeres`\|`lgtbiq`\|`mixta_diversidades`\|`mayor_hombres`\|`solo_hombres` | req | §7.7 |
| `ejecucion_red` | código de `red` | req | §7.9.1 |
| `escenarios` | lista de códigos | cond | botones del nivel de §7.9.1 |
| `ejecucion_escenario_otro` | texto (150) | cond | |
| `nombre_espacio_ejecucion` | texto (150) | req | §7.9.2 |
| `direccion_espacio_ejecucion` | texto (200) | req | §7.9.2 |
| `ejecucion_lon`, `ejecucion_lat` | float | opt | del picker · **sin punto no hay certificación de estrato → 0 pts en §7.9.2** |
| `ejecucion_estrato` | 1–4 | req | lo **declarado** (no puntúa) |
| `sostenibilidad_ambiental` | `si` \| `no` | req | §7.10 |
| `sostenibilidad_sustento` | texto largo | cond | §7.10 · **mínimo 100 palabras** si respondió `si` |

**`ejecucion_estrato_ideca`, `ejecucion_fuera_kennedy` y `ejecucion_geo_metodo`
no son campos del POST.** Los certifica el servidor con la capa de manzanas de
Catastro/IDECA sobre `ejecucion_lon`/`ejecucion_lat`
(`forms.inscripcion.certificar_estrato_ejecucion`). Si el punto no resuelve →
`NULL`, que son 0 puntos: no se infiere del declarado ni del de la sede.
Estratos 5 y 6 se guardan como `NULL` (el CHECK de la BD es 1–4).

### §8 Gestión operativa (0 pts, compuerta presupuestal)

| Campo | Tipo | Oblig. | Nota |
|---|---|---|---|
| `metodologia` | texto (≤5000) | req | §8.1 |
| `actividades` | JSON | req | §8.2 |
| `cronograma` | JSON | req | §8.3 |
| `equipo` | JSON | req | §8.4 |
| `presupuesto` | JSON | req | §8.5 |

### §9 Presentación

| Campo | Tipo | Oblig. | Nota |
|---|---|---|---|
| `compromiso_redes`, `compromiso_carta_1ano`, `compromiso_actualizacion` | bool | req | los 3 checkboxes de ley |
| `declaracion_buena_fe` | bool | req | juramento Art. 83 CN, jurídicamente separado |
| `firma_cedula` | texto | req | **debe ser igual a `rep_numero_doc`** |
| `firma_fecha` | fecha | req | no puede ser futura |
| `firma` | archivo | req | lienzo (PNG/JPG) o PDF firmado |

`radicado_at` lo pone el servidor. El estado nace en `enviada`.

---

## 2. Colecciones

Todas viajan como **texto JSON** en un campo del multipart. Si el POST llega
como `application/json`, también se aceptan ya deserializadas.

### `instancias` — §6.1
Lista plana de códigos: `instancias=1&instancias=3` (o `[1,3]` en JSON).

### `enfoques` — §5.2 y §7.8

```json
[
  {"seccion": "5.2", "familia": "c52_mujer_genero", "orden": 1,
   "opciones": ["c52_mujer_genero__femenino"]},
  {"seccion": "5.2", "familia": "c52_discapacidad", "orden": 2,
   "opciones": ["c52_discapacidad__fisica"]},
  {"seccion": "7.8", "familia": "p78_mujer", "orden": 1,
   "opciones": ["p78_mujer__liderazgo"]},
  {"seccion": "7.8", "familia": "p78_genero", "orden": 2, "opciones": []}
]
```

- `orden` = **orden de activación del ciudadano**, no el orden del catálogo.
  En §7.8 reparte 4/3/2/1/0 puntos. Dos familias no pueden reclamar la misma
  posición dentro de una sección.
- La familia tiene que existir, estar activa y pertenecer a `seccion`.
- Cada opción tiene que pertenecer a su familia.
- §5.2: `c52_ninguno` es excluyente; máximo **4 familias** («Mujer y Género» +
  3 adicionales). §7.8: `p78_ninguno` es excluyente, sin tope de familias
  (la quinta en adelante vale 0).
- §5.2 es **obligatoria** (si no atiende ninguna población, `c52_ninguno`).
  §7.8 es opcional.
- Persistencia: `InscripcionBancoEnfoqueFamilia.reemplazar()` — **nunca
  `.set()`**, que no conserva el orden.

### `objetivos_especificos` — §7.4.2
`["Objetivo 1", "Objetivo 2", "Objetivo 3"]` — exactamente 3.
También se acepta `[{"texto": "..."}]`.

### `actividades` — §8.2
```json
[{"nombre": "Taller semanal", "descripcion": "..."}]
```
Mínimo 1. `nombre` ≤ 200. **La posición en esta lista (`0`-based) es el
`actividad_idx`** que usan el cronograma y el presupuesto.

### `cronograma` — §8.3
```json
[{"actividad_idx": 0, "mes": 1, "semana": 1}]
```
Matriz cerrada `mes 1..4` × `semana 1..4`. Celdas repetidas se ignoran.
**Toda actividad necesita al menos una celda**, y `actividad_idx` tiene que
existir en `actividades`.

### `equipo` — §8.4
```json
[{"nombre": "...", "nivel_formacion_codigo": 10, "rol": "Coordinación",
  "nivel_formacion_otro": null}]
```
Mínimo 1. `nombre` y `rol` obligatorios; el nivel de formación puede ir por
código (catálogo `niveles_educativos`) o como texto en `nivel_formacion_otro`.

### `presupuesto` — §8.5
```json
[{"actividad_idx": 0, "descripcion_rubro": "...", "cantidad": 10,
  "valor_unitario": 100000}]
```
Mínimo 1. `cantidad > 0`, `valor_unitario >= 0` (CHECK en BD).

**`valor_total` NO se manda.** En la BD es
`GENERATED ALWAYS AS (cantidad * valor_unitario) STORED`: si lo calculara el
navegador, un POST directo podría radicar un total que no corresponde y
saltarse el tope. Si llega, se ignora.

**Compuerta:** si `Σ cantidad × valor_unitario` supera el tope máximo
(hoy $17.000.000) el POST responde 400 con «Ajuste de presupuesto requerido».
El tope exacto depende de la banda de puntaje y no de la posición en el
ranking — ver `matriz_oficial.REGLA_TOPE_PRESUPUESTAL` y §A.5 del plan de
trabajo. El endpoint de catálogos publica el tope en `reglas.presupuesto`.

### Anexos (multipart binario)

| Clave | Oblig. | MIME |
|---|---|---|
| `soporte_legal` | sí | `application/pdf` |
| `cedula_representante` | sí | `application/pdf` |
| `rut` | no | `application/pdf` |
| `reconocimiento_deportivo` | no | `application/pdf` |
| `firma` | sí | `image/png`, `image/jpeg`, `application/pdf` |

Tamaño máximo por archivo: `DOCUMENTOS_MAX_UPLOAD_BYTES` (2 MB).
La misma clave se usa en el POST, en `InscripcionBancoAnexo.tipo` y en
`onedrive_storage.NOMBRES_ANEXOS`.

Flujo: `mongo_storage.guardar()` (cifrado, **sistema de registro**) → fila en
`inscripcion_banco_anexo` → `onedrive_storage.espejar_soportes()`
(**best-effort**, incluye el consolidado «Tu Pago»). *Un fallo de OneDrive
nunca tumba la radicación.*

---

## 3. Lo que retiró el formulario

Se retira la **captura**; las columnas se quedan porque las 24 inscripciones
del piloto tienen dato y el panel del organizador las lee.

`soporte_legal_url` · `propuesta_url` · `firma_imagen_url` · `firma_imagen` ·
`redes_otra` · `impacto_politicas` · `impacto_justificacion` · `uso_beneficio` ·
`implementos` · `categorias_material` · `requerimiento_detalle` · `tipos_apoyo` ·
`espacio_participacion` (+`_otro`) · estrato 5 · todo IDEARR.

Campos históricos que siguen aceptándose como **opcionales** (el organizador los
reporta): `caracteristica_pob`, `propuesta_descripcion`, `enfoques_propuesta`,
`discapacidades`, `orientaciones`, `identidades_genero`, `grupos_etnicos`,
`habitabilidades`, `desplazamientos`, `poblaciones_rurales`,
`victima_conflicto`, `red_detalle_json`, `escenarios_opera_json`,
`escenarios_solicita_json`.

### Derivaciones que hace el servidor (no se preguntan dos veces)

| Columna histórica | Se deriva de |
|---|---|
| `tamano_organizacion` | `tamano_staff_num` |
| `actividad_principal` | nombre de `modalidad_actividad` |
| `beneficiada_alk` + M2M `beneficios_alk` | `beneficio_alk` |
| `enfoque_genero_mujer` | `diversidad_genero_propuesta` |
| M2M `enfoques` (`enfoque_diferencial`) | familias §5.2 (mapa 1:1) |
| M2M `enfoques_propuesta` | familias §7.8 (mapa **con pérdida**, ver abajo) |
| M2M `entorno_red` | `ejecucion_red` |
| `rep_nombre` | los 4 campos separados del representante |
| `upz` | punto de la sede, si no la declaran |

---

## 4. Desalineaciones abiertas (para el motor de puntaje)

Estas cuatro **no se pueden cerrar desde el formulario** y hoy le cuestan
puntos al proponente. El arreglo va en `services/matriz_oficial.py` (o en los
modelos), no acá.

1. **Códigos de §7.5 y §7.7.** La BD (CHECK del script 013) acepta `gt_80`,
   `gt_200`, `lgtbiq`, `mixta_diversidades`; `matriz_oficial` busca `mas_80`,
   `mas_200`, `diversas`, `equitativo`. El form emite lo que la BD acepta
   (emitir lo otro = INSERT rechazado), así que esos brackets liquidan **0**.
2. **`_valor(insc, "...")` con nombre de columna, no de atributo.** Los
   criterios 2, 6 y 11.1 leen `arraigo_red_codigo`, `beneficio_alk_codigo` y
   `ejecucion_red_codigo`; en Django esos atributos se llaman
   `arraigo_red_id`, `beneficio_alk_id` y `ejecucion_red_id` (el `db_column` no
   cambia el `attname`). Hoy caen siempre al camino de respaldo.
3. **`insc.instancias` no existe.** El criterio 5 (§6.1, 2 pts) espera un M2M
   `instancias` en la cabecera; el DDL creó la tabla puente pero el modelo no
   declara el M2M espejo. El form escribe `inscripcion_banco_instancia`
   correctamente, pero el criterio se queda en `sin_captura`.
4. **§7.8 pierde granularidad al derivar el M2M histórico.** El catálogo viejo
   `enfoque_propuesta` tiene 7 opciones y el documento 10: «Mujer» y «Género»
   colapsan en una, los tres étnicos en una, y «Población Campesina o Rural» no
   tiene equivalente. Como el criterio 10 puntúa por CANTIDAD de etiquetas,
   puede quedar por debajo. El dato fiel está en
   `inscripcion_banco_enfoque_familia` con `seccion='7.8'` y su
   `orden_activacion`: el criterio debería leer de ahí.

---

## 5. Notas para el wizard Angular

- **No mostrar puntajes ni ranking**: el modelo es ciego por diseño.
- Los mínimos (`200` caracteres, `100` palabras, `3` objetivos, matriz `4×4`,
  tope presupuestal, tope de enfoques de §5.2, estratos válidos) vienen en
  `reglas` del endpoint de catálogos. **Úsalos desde ahí**: si el contador de
  la UI y el validador del servidor divergen, el ciudadano llena 45 minutos y
  el POST lo rechaza.
- `enfoques_familias_52` y `enfoques_familias_78` llegan **ya agrupados**
  familia → opciones.
- Las direcciones (sede, §4.2, §7.9.2) **nunca son texto libre**: autocompletar
  contra Catastro + pin en el mapa, y se envían `*_lon`/`*_lat`. Sin punto en
  §7.9.2 se pierden hasta 9 puntos de focalización.
- El total del presupuesto se calcula en vivo y es **de solo lectura**; no se
  envía.
- Build: `cd frontend && npx ng build --base-href=/app/`.
