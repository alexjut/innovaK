# Plan de trabajo — 2026-07-29

Cuatro frentes abiertos en la misma jornada. Este documento es el plan; nada de
esto está ejecutado salvo lo marcado como ✅.

| Frente | Qué es | Bloqueado por |
|---|---|---|
| **A. Banco de Deportes** | Reingeniería del formulario y del motor de puntaje según el *Documento Maestro* oficial | 3 decisiones de Deportes (§A.5) |
| **B. Documentos → OneDrive** | Carpeta por organización, cargue real dentro del app, quitar campos de URL | Credenciales (ya las tiene Alex) |
| **C. Rubros presupuestales** | Sembrar el catálogo `concepto_gasto` y enlazar cada contrato | Fuente oficial del clasificador |
| **D. Objetivos del POAI** | Reemplazar los objetivos internos por los legítimos del POAI | El archivo del POAI |

---

## Frente A — Banco de Iniciativas de Deportes

### A.1 Qué cambia de fondo

El *Documento Maestro* (27 pág., 4 documentos, entregado 2026-07-29) **reemplaza
la matriz del 2026-07-17** y resuelve los 5 bloqueos que teníamos abiertos:

| Bloqueo anterior | Cómo queda resuelto |
|---|---|
| Bloque 2 detallaba 80 pero declaraba 70 | Redistribuido: 14+10+12+10+18+6 = **70 exactos** |
| Tope FDL sin definir | Topes por posición en el ranking: $17M / $14M / $11M |
| Catálogo `tipo_beneficio_alk` no coincidía | Nueva escala inversa de 5 opciones (§6.2) |
| Protocolo IDEARR sin definir | **Eliminado por completo** del backend |
| "Usuarios recurrentes" ambiguo | Renombrado: «Cantidad actual de personas que beneficia o atiende su organización» (3.4) |

**Y cambian dos cosas grandes más:**

1. **El total pasa de 105 a 100 puntos.** El bono preferencial de género (5 pts)
   desaparece como bono suelto: se absorbe en el criterio 7.7 (12 pts).
2. **Se elimina el comité humano y la subsanación.** Todo autoliquidado,
   `ORDER BY puntaje_total DESC`, y las primeras **93 posiciones** ganan.

### A.2 La matriz nueva (100 pts)

**Bloque 1 — Caracterización (30 pts, secciones 1–6)**

| # | Criterio | Pts | Origen |
|---|---|---|---|
| 1 | Capacidad de la organización | 12 | §3.1 + §3.2 + §3.3 + §3.4 (3 pts c/u) |
| 2 | Arraigo territorial | 4 | §4.2 (bracket de 4 niveles) |
| 3 | Inclusión — rango etario | 4 | §5.1 (acumulador, tope 4) |
| 4 | Inclusión — enfoques poblacionales | 6 | §5.2 (Mujer y Género = 3 fijos + 1 por casilla) |
| 5 | Participación — instancias | 2 | §6.1 (+1 por opción, tope 2) |
| 6 | Democratización del fomento | 2 | §6.2 (escala inversa) |

**Bloque 2 — Propuesta técnica (70 pts, sección 7)**

| # | Criterio | Pts | Origen |
|---|---|---|---|
| 7 | Cobertura cuantitativa | 14 | §7.5.1 (4.66) + §7.5.2 (4.66) + §7.5.3 (4.68) |
| 8 | Enfoque por ciclo vital | 10 | §7.6 (acumulador, tope 10) |
| 9 | Impacto en diversidad de género | 12 | §7.7 (escala fija de 6 niveles) |
| 10 | Enfoques poblacionales | 10 | §7.8 (decreciente 4/3/2/1/0 por **orden de activación**) |
| 11 | Focalización territorial | 18 | §7.9.1 tipo de espacio (9) + §7.9.2 estrato IDECA (9) |
| 12 | Sostenibilidad medioambiental | 6 | §7.10 (binario SÍ/NO) |

Sección 8 (metodología, cronograma, equipo, presupuesto) **vale 0 puntos**: es
requisito formal del IDRD y compuerta presupuestal, no criterio.

### A.3 Qué pasa con el formulario actual

Inventario contra `apps/banco_iniciativas/forms/inscripcion.py`:

**Se queda (se reusa tal cual o con ajuste menor):**
`nombre_organizacion`, `tipo_organizacion`, `numero_soporte_legal`, `correo`,
`telefono`, `redes_facebook`, `redes_instagram`, representante legal completo,
`nivel_educativo`, `titulos_obtenidos`, `barrio`/`direccion` + lat/lon,
`estrato`, `rango_etarios`, `enfoques`, `ciclo_vital`, `enfoques_propuesta`,
`composicion_organizacion`, `tamano_organizacion`, `anios_experiencia`,
`disciplina_principal`, los 3 compromisos y el bloque de firma.

**Se borra:**

| Campo | Por qué |
|---|---|
| `soporte_legal_url`, `propuesta_url`, `firma_imagen_url` | Se reemplazan por cargue real (Frente B) |
| `redes_otra` | El documento fija solo web, Facebook e Instagram |
| `impacto_politicas`, `impacto_justificacion` | No existe en la matriz nueva |
| `uso_beneficio` | §6.2 ahora es selección única con escala inversa |
| `implementos`, `categorias_material`, `requerimiento_detalle`, `tipos_apoyo` | Se reemplazan por la tabla de presupuesto de §8.5 |
| `espacio_participacion` (select único) + `_otro` | §6.1 pasa a multiselección |
| Estrato 5 en el select | El documento lo elimina explícitamente: solo 1–4 |
| Todo lo del protocolo IDEARR | Suprimido por orden expresa |

**Es nuevo (no existe hoy):**

- §3.1 tamaño de staff como **número exacto** con brackets (hoy es un select de rangos).
- §4.2 clasificación de entornos: 4 opciones que despliegan botones dinámicos + bloque de localización obligatorio.
- §5.2 checkboxes en cascada con submenús (6 familias con sus subopciones).
- §7.1–7.4: problemática, justificación, objetivo general + 3 específicos (mín. 200 caracteres los textos largos).
- §7.5: los 3 selects de cobertura.
- §7.8: **orden de activación** de los chips — hay que persistir la secuencia, no solo el conjunto.
- §7.9.2: certificación de estrato vía **API IDECA** (ya tenemos la integración).
- §7.10: radio SÍ/NO + textarea de mínimo 100 palabras.
- §8 completa: metodología, actividades, cronograma matricial (Mes 1–4 × Semana 1–4), tabla de equipo de trabajo, tabla de presupuesto con total calculado.
- §9: cédula del firmante con validación cruzada contra §1.7, fecha de firma, y el juramento de buena fe (Art. 83 CN).

### A.3.1 Retirar los campos de URL no es un borrado simple

Rastreo hecho el 2026-07-29. Los tres campos que el documento reemplaza por cargue
real de archivo (`soporte_legal_url`, `propuesta_url`, `firma_imagen_url`) tienen
**cinco puntos de contacto**. Quitar solo la declaración deja el formulario roto:

| Archivo | Qué hay que hacer |
|---|---|
| `forms/inscripcion.py:208, 360, 402` | Las tres declaraciones de campo |
| `forms/inscripcion.py:528` | `self.fields["propuesta_url"].required = True` en `__init__` |
| `forms/inscripcion.py:708` | La validación cruzada de firma en `clean()` usa `firma_imagen_url` |
| `forms/inscripcion.py:870` | `save()` escribe `soporte_legal_url` |
| `tests/test_smoke.py:158-164` | Afirma `"soporte_legal_url" in f.fields`; hay que reescribir la intención del test, no solo borrarlo |

**Lo que NO se toca:** las columnas homónimas del modelo
(`models/inscripcion.py:461, 579, 590`) se quedan, y con ellas todo lo que las
lee: `views/organizador.py:148-150, 189`, `api/serializers.py:101, 196` y
`api/views.py:284`. Las 24 inscripciones del piloto tienen dato ahí y el panel
del organizador lo muestra.

Ojo también con los homónimos de otros módulos, que son independientes y no se
tocan: `apps/jovenes_a_la_e`, `apps/entregas` y `apps/login/models/captura_generica.py`
tienen su propio `firma_imagen_url`.

### A.4 Orden de ejecución propuesto

| PR | Alcance | Estimado |
|---|---|---|
| **PR-1** | DDL: tablas nuevas (cronograma, equipo de trabajo, presupuesto, objetivos específicos) + columnas para los campos nuevos + orden de chips en §7.8 | 1 d |
| **PR-2** | Motor `matriz_oficial.py` reescrito: los 12 criterios sobre 100 pts, con tests unitarios por criterio | 2 d |
| **PR-3** | Secciones 1–6 del formulario Angular (Bloque 1) | 2 d |
| **PR-4** | Sección 7 (Bloque 2), incluida la focalización con IDECA | 2 d |
| **PR-5** | Sección 8 (cronograma, equipo, presupuesto) + compuerta presupuestal | 2 d |
| **PR-6** | Sección 9 + consolidado PDF tipo «Tu Pago» + panel de ranking | 1.5 d |

El motor va **antes** que el formulario a propósito: es lo que Deportes tiene que
validar, y se puede probar con datos sintéticos sin esperar la UI.

### A.5 ⚠️ Tres contradicciones del documento — resueltas provisionalmente

Las tres se decidieron el 2026-07-29 para no bloquear el desarrollo. **Quedan
marcadas como provisionales en el código y Deportes debe ratificarlas.**

**1. Contradicción de pesos en Arraigo Territorial (§4.2).**
El cuerpo del documento (pág. 11) dice: barrial = 4.0, dotacional = 2.0,
proximidad = 1.0, estructurante = 0.0.
La matriz de síntesis (pág. 22, criterio 2) dice lo contrario: *"Espacios
dotacionales locales = 4.0 | Parques barriales = 2.0"*.
Son cuatro puntos que cambian de dueño.

→ **DECIDIDO: manda el cuerpo (barrial = 4.0).** Dos pasajes contra uno: §7.9.1
también premia lo barrial con el puntaje más alto (9.0) y castiga lo estructurante
con 0.0. La tabla de síntesis es la que está invertida.

**2. El tope presupuestal por ranking es lógicamente imposible como está escrito.**
El documento dice que el sistema bloquea el avance si el monto no cabe en el tope
de **su posición en el ranking**. Pero la posición no existe mientras la
convocatoria esté abierta: depende de cuántos y con qué puntaje se postulen
después. No se puede calcular en el momento en que el ciudadano llena §8.5.

Dos salidas posibles:
- **Opción A (recomendada):** topes por **banda de puntaje absoluto**, no por
  posición. Deportes fija los cortes (ej. ≥75 pts → $17M; 60–74 → $14M; <60 → $11M).
  Funciona en tiempo real y conserva la intención de premiar el mérito.
- **Opción B:** el ciudadano radica sin tope; al cerrar la convocatoria el sistema
  calcula el ranking y notifica a quien deba ajustar el presupuesto. Requiere una
  etapa de ajuste posterior — que es justo lo que el documento quiere eliminar.

→ **DECIDIDO: Opción A.** Los cortes quedan como constantes parametrizables en el
motor, así que si Deportes prefiere otros valores se cambian sin tocar la lógica.

**3. Qué pasa si llegan menos de 93 postulaciones.**
La regla dice "las primeras 93 posiciones ganan" y los topes están amarrados a
tramos de 31. Si llegan 60, ¿ganan las 60? ¿Y qué tramo de tope les aplica?

→ **DECIDIDO: ganan todas las que haya** y los tramos de tope se calculan por
tercios sobre el total real de postulaciones, no sobre 93 fijos.

---

## Frente B — Documentos a OneDrive

### B.1 Dónde van las credenciales

**Nunca en el repositorio** — innovaK es público. Van en `.env`, que no se
commitea y ya está protegido por `.gitignore` (junto con `credenciales_*` y
`*.local.txt`).

Variables a agregar:

```
ONEDRIVE_TENANT_ID=
ONEDRIVE_CLIENT_ID=
ONEDRIVE_CLIENT_SECRET=
ONEDRIVE_DRIVE_ID=
ONEDRIVE_CARPETA_RAIZ=Banco de Iniciativas
```

Pásamelas por un canal que no sea el repo y las dejo cargadas. Después: reinicio
del contenedor y listo.

### B.2 Arquitectura propuesta

**Mongo sigue siendo el sistema de registro** (ya está cifrado, ya funciona en
Banco, Jóvenes y Caracterización, y es lo que protege los datos personales).
**OneDrive es el espejo legible** para que el área pueda ver y descargar sin
entrar al aplicativo.

Estructura de carpetas:

```
Banco de Iniciativas/
  2026/
    <NIT o documento>-<NOMBRE DE LA ORGANIZACIÓN>/
      1_soporte_legal.pdf
      2_cedula_representante.pdf
      3_rut.pdf
      4_reconocimiento_deportivo.pdf
      9_firma.pdf
      CONSOLIDADO_<nombre organización>.pdf
```

La carpeta se crea sola al radicar, con el nombre de la organización. El
`CONSOLIDADO` es el requisito «Tu Pago» del documento: todos los anexos unidos en
un solo PDF al momento de descargar.

### B.3 Quitar los campos de URL

Hoy el formulario acepta que el ciudadano **pegue un enlace** a su documento
(`soporte_legal_url`, `propuesta_url`, `firma_imagen_url`). Eso se va: el
documento exige que los archivos vivan dentro del aplicativo. Los campos se
reemplazan por `input type="file"` obligatorio, y en el detalle del organizador
el enlace deja de ser texto pegado para ser la descarga autenticada del archivo real.

Migración de lo ya cargado: las inscripciones del piloto que tengan URL externa se
quedan como están (histórico), pero se marcan para que el área sepa que ese
soporte no está bajo custodia nuestra.

---

## Frente C — Rubros presupuestales

**Estado:** `concepto_gasto` tiene **1 sola fila y es de prueba** (`"prueba
concepto"`). `contrato_actividad_plan` tiene 14 filas, **0 con rubro**. Y
`secop_contrato` **no trae la columna** — ya lo verifiqué contra los 27 campos que
ingerimos de SECOP II.

**Plan:**

1. **Borrar** la fila de prueba del catálogo.
2. **Sembrar** el catálogo real de conceptos de gasto con un management command
   idempotente (`seed_conceptos_gasto`), siguiendo el patrón de `seed_modulos`.
3. **Enlazar** cada contrato a su rubro vía `contrato_actividad_plan.concepto_gasto_id`.

### C.1 Búsqueda de la fuente — resultado (2026-07-29)

Rastreo hecho sobre datos abiertos. **Conclusión: el rubro de Kennedy no está en
ninguna fuente automatizable.**

| Fuente probada | Resultado |
|---|---|
| `secop_contrato` (los 27 campos que ingerimos) | No trae rubro |
| **SECOP II — Rubros Presupuestales** (`datos.gov.co`, `cwhv-7fnp`) | Enlaza rubro ↔ contrato por `id_contrato`… pero es **SIIF (entidades nacionales)**. 5.891.594 filas y **cero** para los contratos de Kennedy (probados 5 `id_contrato` distintos). Bogotá usa PREDIS/BogData, no SIIF. |
| *Ejecución Conceptos de Gasto de los FDL* (Datos Abiertos Bogotá) | Es de Salud: los "objetos de gasto" son nombres de programas, no el clasificador |
| Rankings PAC-FDL (Hacienda) | Agregados por localidad, sin desglose por rubro |

**La fuente real es el Decreto Local de liquidación del presupuesto del FDL.**
El **Decreto Local 019 de 2025** (expedido 23/12/2025) liquida el presupuesto de
Kennedy para la vigencia 2026 —$355.825.093.000, de los cuales $346.239.153.000 son
inversión— y trae los rubros codificados. El texto del articulado está publicado en
SISJUR, pero **el anexo de gastos con el detalle de rubros no está en datos abiertos**:
hay que sacarlo del PDF del decreto o pedirlo al área de presupuesto.

**Siguiente paso concreto:** conseguir el anexo de gastos del Decreto Local 019 de
2025 (o el del decreto de liquidación de la vigencia que corresponda) y de ahí sale
el `seed_conceptos_gasto` con códigos oficiales. No se inventa ningún rubro.

---

## Frente D — Objetivos del POAI

**Estado:** tabla `objetivo` con 6 filas y `programas` con 7, ambas internas y sin
trazabilidad al plan oficial. `proyecto.programa_id` → `programas`, y
`programas.objetivo_id` → `objetivo`.

Mientras tanto `sdp_meta_oficial` (280 filas, SEGPLAN) ya trae `codigo_objetivo`,
`objetivo`, `codigo_programa` y `programa` — la estructura legítima del Distrito.

**Plan:**

1. Recibir el archivo del **POAI** con los objetivos oficiales.
2. Cruzar los 6 objetivos internos contra los del POAI y levantar el mapa de
   equivalencias (cuál es cuál, cuáles sobran, cuáles faltan).
3. Sembrar los objetivos legítimos y **reapuntar** `programas.objetivo_id` a ellos.
4. Borrar los internos huérfanos, ya sin nada colgando.
5. Recién ahí decidir si las páginas `/presupuesto/objetivos` y
   `/presupuesto/programas` se quedan como CRUD o se vuelven vistas de solo
   lectura derivadas del plan oficial.

**Regla:** no se borra nada antes del paso 3. Cada objetivo interno tiene programas
colgando y cada programa tiene proyectos; borrar primero deja proyectos huérfanos.

---

## Lo que necesito de Alex para desbloquear

1. Las **3 decisiones de Deportes** de §A.5 (pesos de arraigo, tope presupuestal, y qué pasa con menos de 93).
2. Las **credenciales de OneDrive** (van al `.env`, no al repo).
3. El **archivo del POAI** con los objetivos oficiales.
4. La **fuente del clasificador de rubros** (SIPSE, SIPLANIN o el archivo del área).
