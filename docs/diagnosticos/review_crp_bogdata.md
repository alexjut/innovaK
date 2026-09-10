# Revisión adversarial del módulo CRP (BogData)

**2026-09-07.** Seis lentes independientes sobre la ingesta del CRP —corrección
de la carga, datos personales, rendimiento, DDL, normalizador e integración—
con verificación adversarial: cada hallazgo se volvió a mirar con voluntad de
refutarlo, abriendo el código y reproduciéndolo contra la base real en
transacciones revertidas.

| | |
|---|---:|
| Hallazgos brutos | 15 |
| **Confirmados** | **12** |
| Refutados al verificar | 3 |

> La revisión quedó **incompleta**: 13 de 34 agentes murieron por límite de
> sesión, todos en la fase de verificación de las lentes `normalizador` e
> `integracion`. Lo que sigue es lo que sí se confirmó; esos dos frentes
> quedaron sin verificar y hay que revisarlos.

El detalle íntegro está en
[`review_crp_bogdata.datos.json`](./review_crp_bogdata.datos.json).

---

## Confirmados

### 1. Subir un corte más viejo revierte el tablero sin una sola advertencia, y el hash impide deshacerlo

> ✅ **Cerrado el 2026-09-07** — ver la bitácora al final.

`apps/presupuesto/services/crp_carga.py:477` · gravedad **alta**

**Qué pasa.** El barrido `UPDATE crp SET vigente=FALSE WHERE vigente AND carga_id IS DISTINCT FROM <esta carga>` asume que todo archivo es una foto completa del mismo universo, y nada lo comprueba: no se compara `fecha_corte` contra la última carga, no se compara la vigencia, no se exige que el conteo o el total no retrocedan. Como todos los endpoints filtran `c.vigente`, lo que quede marcado desaparece del…

**Cómo falla.** Cargué el corte real de septiembre y encima, por error, un corte de agosto con 1.200 filas (el mismo archivo recortado, con Fecha Final 2026-08-07). El cargador no objetó nada: 0 insertadas, 1.200 actualizadas, 1.429 marcadas no vigentes. El neto que muestran `/crp/` y `/crp/resumen-por-proyecto/` cayó de $226.744.982.139 a $89.066.656.294 — se fueron $137.678 M de plata real — y los valores de las 1.200 filas que sí venían retrocedieron a los de agosto. Intenté arreglarlo re-subiendo el archivo de septiembre y quedé encerrado: «Este archivo ya se cargó: corte 2026-09-07…». La base se queda en 1.200 filas vigentes y $89.067 M hasta que alguien borre a mano la fila de `crp_carga`. Peor, la…

**Medido.** Corrido en `transaction.atomic()` revertida contra la BD real. Secuencia medida: septiembre → (2630 vigentes, 226.744.982.139); agosto → (1200 vigentes, 89.066.656.294); re-subir septiembre → CargaError por hash; estado final (1200, 89.066.656.294). `crp_carga` quedó con las tres filas y fechas de corte 2026-09-07, 2026-10-05 y 2026-08-07 en ese orden de id, sin ninguna queja. El sweep está en crp_carga.py:477-481; el bloqueo por hash en crp_carga.py:351-357.

**Arreglo.** Antes de crear la carga, comparar el corte entrante contra el vigente: si `fecha_corte` es anterior al máximo ya cargado —o si el conteo de filas o el valor neto retroceden de forma significativa— abortar con CargaError explicando qué se venía a pisar, y exigir un consentimiento explícito para seguir (`--permitir-retroceso` en el comando, casilla equivalente en la pantalla). Acotar además el barrido al mismo universo (misma vigencia, y solo las filas de la carga anterior) para que un reporte…

---

### 2. `carga_id ON DELETE CASCADE` sobre un puntero que el upsert reescribe: borrar una carga vacía toda la tabla

> ✅ **Cerrado el 2026-09-07** — ver la bitácora al final.

`apps/presupuesto/scripts/026_crp_bogdata.sql:150` · gravedad **alta**

**Qué pasa.** `crp.carga_id` no significa «la carga que trajo esta fila» sino «la última carga que la tocó»: el upsert hace `carga_id = EXCLUDED.carga_id` en cada corte. Con `ON DELETE CASCADE`, borrar la carga más reciente borra TODAS las filas de `crp`, incluidas las que existían desde el primer corte.

**Cómo falla.** Se carga el corte de septiembre (carga 1, 2.630 filas). Se carga el de octubre (carga 2): las mismas filas se actualizan y su `carga_id` pasa a 2. Alguien nota que el archivo de octubre estaba mal y hace `DELETE FROM crp_carga WHERE id=2` para deshacerlo. La cascada se lleva las 2.630 filas; queda la carga 1 en el historial diciendo «2.630 filas leídas, $226.745 M» y `crp` en cero. La regla «lo que desaparece se marca, nunca se borra» la rompe la propia FK, y el rollback del 026 tampoco protege acá porque esto no pasa por el script.

**Medido.** Reproducido en una transacción revertida contra la base real: dos cargas, dos filas upserteadas → `SELECT carga_id, count(*) FROM crp GROUP BY 1` da `[(33, 2)]` (todo apuntando a la carga 2); tras `DELETE FROM crp_carga WHERE id=33` → `SELECT count(*) FROM crp` = 0, y `crp_carga` conserva la fila de septiembre con `filas_leidas=2`. La cláusula está viva en la base: `crp_carga_id_fkey FOREIGN KEY (carga_id) REFERENCES crp_carga(id) ON DELETE CASCADE`.

**Arreglo.** Cambiar el FK a `ON DELETE SET NULL`, que es lo que ya hacen los otros dos punteros del mismo ALTER y lo único coherente con «nunca se borra»: la fila queda viva con `carga_id` nulo y la siguiente carga se lo vuelve a poner. Como el 026 ya está aplicado, va en un script nuevo (`027_crp_carga_fk.sql`) que aplica una persona: `ALTER TABLE crp DROP CONSTRAINT crp_carga_id_fkey; ALTER TABLE crp ADD CONSTRAINT crp_carga_id_fkey FOREIGN KEY (carga_id) REFERENCES crp_carga(id) ON DELETE SET NULL;` — y…

---

### 3. tercero_sap colapsa siete entidades distritales bajo el NIT compartido 899999061 — $34.771 M, el 15,3 % del neto, atribuidos a la entidad equivocada

> ✅ **Cerrado el 2026-09-10** (DDL 028 + nombre de la fila en la lista) — ver la bitácora al final.

`apps/presupuesto/services/crp_carga.py:268` · gravedad **media**

**Qué pasa.** `_upsert_terceros` llavea por `(tipo_doc, num_doc)` y deja que gane el último nombre visto, partiendo de que los nombres repetidos son variantes de escritura del mismo tercero. Pero 899999061 es el NIT de Bogotá D.C., compartido por todas las entidades distritales: en el archivo lo llevan siete personas jurídicas distintas. El campo que sí las separa, `bp_sap`, se carga y hasta se indexa en el…

**Cómo falla.** Tras cargar el archivo real quedó UNA fila `tercero_sap` (id 31208, NITC 899999061) con nombre 'SECRETARIA DISTRITAL DE CULTURA RECREACION Y DEPORTE' y bp_sap 119, colgando 19 filas de CRP por $34.771.287.368. De esos, $31.127.780.186 (13,7 % del archivo entero) son dos convenios de la SECRETARÍA DISTRITAL DE INTEGRACIÓN SOCIAL, y la pantalla los muestra a nombre de Cultura. También caen ahí Desarrollo Económico ($1.349 M), Seguridad ($796 M), el FDL de Santa Fe ($242 M), Ambiente ($31 M) y la Tesorería. El filtro `?tercero=31208` suma los siete como si fueran uno. Y cuál de los siete nombres gana depende del orden de las filas en el Excel, así que el próximo corte puede renombrar el mismo…

**Medido.** Medido sobre las 2.630 filas: el único documento con más de un nombre es ('NITC','899999061'), con 7 nombres y 7 bp_sap distintos (0000000003, 0000000103, 0000000117, 0000000119, 0000000122, 0000000126, 0000000137). Tras la carga en transacción revertida: SELECT sobre tercero_sap JOIN crp devolvió (31208, 'NITC', '899999061', 'SECRETARIA DISTRITAL DE CULTURA RECREACION Y DEPORTE', 119, 19 filas, 34.771.287.368). Los 7 nombres reales siguen en `crp.nombre_bp_beneficiario`, que ningún endpoint…

**Arreglo.** Dos partes; la primera no toca la base y se puede hacer ya. 1. Mitigación inmediata, sin DDL y sin recargar. En `CrpListView` (apps/presupuesto/api/crp_views.py:118) devolver el nombre de la fila, que ya está guardado y es correcto: agregar `c.nombre_bp_beneficiario` y `c.bp_beneficiario` al SELECT y usarlos en el dict `"tercero"`, con `t.nombre` como respaldo cuando la fila venga sin nombre. Con eso las 19 filas dejan de mentir. El filtro `?tercero=` sigue conflacionando: mientras dure la…

---

### 4. El enmascarado de la cédula nunca corre: `ve_doc` pregunta por el mismo módulo que ya exigió el permiso

`apps/presupuesto/api/crp_views.py:130` · gravedad **media**

**Qué pasa.** La vista se gatea con `ModuloRequiredPermission("presupuesto_proyectos")` (línea 18/46) y después decide si muestra el documento completo con `ve_doc = superusuario_o_modulo(request.user, "presupuesto_proyectos")` — la misma condición. Quien no la cumple ya recibió 403 y nunca llegó a la línea 130, así que `ve_doc` es SIEMPRE `True`, `_enmascarar()` es código muerto y `documento_visible` siempre…

**Cómo falla.** El usuario `miguel.arias` (rol `Lider_contrato`, no superusuario) tiene `presupuesto_proyectos` pero NO `presupuesto_cdp`. Según la regla escrita en el propio archivo debería ver `520•••86`; hace `GET /presupuesto/api/crp/?por=200` y recibe el `num_doc` completo de cada tercero. Paginando 14 veces se lleva las 1.244 cédulas de personas naturales del corte, con nombre al lado. Lo mismo aplica a cualquier titular de `presupuesto_proyectos` (hoy Admin, Lider, Lider_contrato, Planeacion, Visor): para nadie se enmascara.

**Medido.** Simulado en el contenedor: `ModuloRequiredPermission('presupuesto_proyectos')().has_permission()` → True para miguel.arias en GET; `superusuario_o_modulo(miguel.arias,'presupuesto_proyectos')` → True; `superusuario_o_modulo(miguel.arias,'presupuesto_cdp')` → False. En BD `rol_modulo`: `presupuesto_cdp` = {Admin, Lider, Planeacion, Visor} y `presupuesto_proyectos` = esos cuatro + `Lider_contrato`. `grep -rn presupuesto_cdp apps/presupuesto/api/` no da ninguna coincidencia. Ningún test toca…

**Arreglo.** Ojo: NO es el cambio de una palabra. Poner ve_doc = superusuario_o_modulo(user, "presupuesto_cdp") aplica la regla del docstring al pie de la letra, pero deja el resultado invertido: enmascararía para Lider_contrato (el líder de contratos) y mostraría la cédula completa a Visor (solo lectura). Hay que decidir la regla antes de codificarla. Tres caminos, en orden de preferencia: (a) SI EL DOCUMENTO ES PARA TODO EL QUE LLEGA AL ENDPOINT: borrar _enmascarar(), ve_doc y documento_visible de…

---

### 5. `metrics.py` suma el CRP sin mirar `vigente`, así que lo que se dio de baja sigue contando

`apps/presupuesto/services/metrics.py:148` · gravedad **media**

**Qué pasa.** La columna `crp.vigente` la introduce el DDL 026 (línea 173) y el cargador la usa para dar de baja lo que deja de venir en un corte nuevo. Pero los tres lectores viejos de `metrics.py` —`resumen_programa` (74), `resumen_inversion` (148) y `resumen_proyecto` (237)— hacen `Crp.objects.all()` / `.filter(proyecto_id=...)` sin `vigente=True`. Los endpoints nuevos sí filtran (`crp_views.py:52`), así…

**Cómo falla.** Hoy no se nota porque `crp` está en cero. Al cargar el segundo corte, todo CRP anulado o retirado entre los dos cortes queda `vigente=FALSE` y sigue sumando en `resumen_programa`: `/presupuesto/api/programas/<id>/` (views.py:1199) y el panel de festivales (`apps/festivales/api/views.py:507`) reportarán un comprometido inflado por los compromisos dados de baja, mientras `/api/crp/resumen-por-proyecto/` —que sí filtra— muestra el correcto. Dos pantallas, dos cifras, ninguna marcada como sospechosa.

**Medido.** `grep -n vigente apps/presupuesto/services/metrics.py` → 0 coincidencias. `ADD COLUMN IF NOT EXISTS vigente BOOLEAN NOT NULL DEFAULT TRUE` en `apps/presupuesto/scripts/026_crp_bogdata.sql:173` (columna nueva de este cambio). Consumidores vivos confirmados: `apps/presupuesto/api/views.py:1184-1199` y `apps/festivales/api/views.py:506-507`.

**Arreglo.** Filtrar por `vigente` en los tres lectores de `metrics.py`, y de paso alinear la medida. Ojo con dos trampas: el modelo `Crp` (apps/presupuesto/models/sql.py:49-67) NO declara la columna `vigente`, así que `.filter(vigente=True)` revienta con FieldError tal como está; y `metrics.py` define `resumen_programa` DOS veces (líneas 61 y 189) — la que corre es la segunda, pero conviene arreglar ambas o borrar la muerta. Pasos: (1) en `models/sql.py`, agregar al modelo `Crp` el campo `vigente =…

---

### 6. `_upsert_terceros` hace 8.472 consultas y deja 1.412 filas bloqueadas con FOR UPDATE toda la transacción

> ✅ **Cerrado el 2026-09-10** — ver la bitácora al final.

`apps/presupuesto/services/crp_carga.py:272` · gravedad **media**

**Qué pasa.** El bucle llama `TerceroSap.objects.update_or_create()` una vez por tercero distinto. Django 4.2 implementa eso como `SAVEPOINT` + `SELECT … LIMIT 21 FOR UPDATE` + `INSERT`/`UPDATE` + `RELEASE`: seis sentencias por tercero, y un bloqueo exclusivo de fila que se sostiene hasta que confirma el `@transaction.atomic` de `cargar_crp` completo. `cur` se recibe como parámetro y no se usa.

**Cómo falla.** Dos cargas concurrentes por `POST /presupuesto/api/crp/cargas/` —un corte nuevo y un archivo corregido, o dos personas del área— toman los mismos terceros en el orden en que aparecen en cada archivo, porque `vistos` es un dict poblado en orden de fila. Órdenes distintos sobre las mismas filas = ciclo de bloqueo. Lo reproduje contra la tabla real con dos conexiones: la transacción A muere con `DeadlockDetected: deadlock detected`. El endpoint solo atrapa `CargaError` y `KeyError`, así que ese `OperationalError` sale como 500 sin mensaje accionable: el usuario ve un error genérico y no sabe que su carga se cayó por la del otro. El caso benigno —el mismo archivo subido dos veces por doble…

**Medido.** Medido con `connection.execute_wrapper` en transacción revertida: 8.472 de las 11.210 sentencias de la carga (75,6 %) y 710 ms de los 1.740 ms salen de esta función, para 1.412 terceros distintos. Capturé el SQL exacto que emite el ORM y termina en `… LIMIT 21 FOR UPDATE`. Deadlock reproducido con dos conexiones psycopg2 sobre `tercero_sap` (filas de prueba borradas, tabla verificada en 0). Prototipo medido del reemplazo: 1 sentencia, 23 ms — 31× más rápido, 8.471 sentencias menos, mismos 1.412…

**Arreglo.** Reemplazar el bucle por una sola sentencia, usando el `cur` que ya se recibe (hoy sin usar), y con las claves ORDENADAS para que dos cargas concurrentes tomen las filas en el mismo orden canónico — eso es lo que de verdad mata el riesgo de deadlock en esta tabla, no el número de sentencias. En `apps/presupuesto/services/crp_carga.py:256`, dejar `_upsert_terceros` así (el bucle de `vistos` se conserva tal cual, incluido el criterio de «el último nombre visto gana»): claves = sorted(vistos)…

---

### 7. El corte anterior deja de ser consultable en cuanto entra uno nuevo, y el historial lo sigue anunciando

> ✅ **Cerrado el 2026-09-10** — ver la bitácora al final.

`apps/presupuesto/scripts/026_crp_bogdata.sql:44` · gravedad **media**

**Qué pasa.** `crp_carga` existe —lo dice su propio comentario— para que «dos cortes distintos» no sean indistinguibles. Pero `crp` guarda un solo `carga_id` que el upsert pisa, así que después del segundo corte ninguna fila apunta ya al primero. Los dos endpoints filtran el corte con `g.fecha_corte = %s` sobre ese join, de modo que todo corte que no sea el último devuelve vacío.

**Cómo falla.** Con dos cortes cargados, `GET /presupuesto/api/crp/?corte=2026-09-07` devuelve `total=0`, `suma_valor_neto=0` y cero items — igual `resumen-por-proyecto/?corte=2026-09-07`. Mientras tanto `CrpCargaListView` sigue listando esa carga con su `fecha_corte` y su `total_valor_neto` de $226.745 M, así que la pantalla ofrece un corte que al seleccionarlo se ve como si la localidad no hubiera comprometido un peso. No hay error ni aviso: es un cero que parece medido.

**Medido.** Medido en transacción revertida con la consulta literal de `crp_views.py`: con carga 1 (corte 2026-09-07) y carga 2 (corte 2026-10-07), `WHERE c.vigente AND g.fecha_corte='2026-09-07'` → `(0, 0)`; `='2026-10-07'` → `(2, 350)`. Los totales por carga sí quedan guardados en `crp_carga` (`total_valor_neto`), pero el detalle por fila del corte viejo es irrecuperable.

**Arreglo.** Hacer que `corte` no pueda mentir, sin DDL y sin tocar el diseño de foto (que es correcto). En crp_views.py, en los dos endpoints, resolver el corte contra crp_carga antes de consultar y filtrar por `c.carga_id = %s` en vez de por `g.fecha_corte`: - corte que no existe en crp_carga → 400 «no hay ninguna carga con ese corte». - corte que existe pero NO es el de la carga más reciente → 409 (o 400) explicando que el CRP guarda el estado al último corte y que del corte pedido solo sobreviven los…

---

### 8. El 026 no se puede reaplicar, y el rollback deja la base en un estado donde reaplicarlo es imposible

`apps/presupuesto/scripts/026_crp_bogdata.sql:135` · gravedad **media**

**Qué pasa.** El script está escrito con `IF NOT EXISTS` en cada CREATE, lo que anuncia idempotencia, pero tres sentencias fallan si los tipos ya están cambiados. Y el rollback, a propósito, NO revierte los tipos ni suelta `crp_rubro_codigo_fkey`: deja exactamente el estado en el que esas tres sentencias explotan. El ciclo aplicar → revertir → volver a aplicar está roto en una sola dirección.

**Cómo falla.** Lunes 8am: hay que deshacer la ingesta. Se corre el rollback (funciona: `crp` vuelve a 48 columnas, se van `crp_carga` y `tercero_sap`). Se corrige lo que haya que corregir y se intenta volver a aplicar el 026 → muere en `ALTER COLUMN anulaciones TYPE BIGINT USING NULLIF(anulaciones, '')::bigint` con `invalid input syntax for type bigint: ""`, porque la columna ya es bigint y Postgres coacciona el literal `''` en tiempo de plan (falla incluso con la tabla vacía). Detrás vienen otras dos: `EXTRACT(YEAR FROM ejercicio)` da `function pg_catalog.extract(unknown, integer) does not exist`, y `ADD CONSTRAINT crp_rubro_codigo_fkey` da `already exists`. El operador queda con el 026 revertido y sin…

**Medido.** Ciclo completo medido en una transacción revertida: se ejecutó el cuerpo del rollback (OK: 48 columnas, 0 tablas de las dos nuevas, FK `crp_rubro_codigo_fkey` presente) e inmediatamente después el cuerpo del 026 → `DataError: invalid input syntax for type bigint: ""`. Cada sentencia probada por separado sobre la base actual: anulaciones y reintegros fallan igual, `ejercicio` falla, `ADD CONSTRAINT` falla; `rubro.codigo` y `valor_neto` sí son reaplicables.

**Arreglo.** Hacer que el bloque de cambio de tipos sea insensible al estado previo. El script ya tiene el idioma correcto en su propia línea 200: un `DO $$` que consulta `information_schema` antes de actuar. Envolver el `ALTER TABLE crp … TYPE …` (líneas 130-146) en la misma guarda: DO $$ BEGIN IF (SELECT data_type FROM information_schema.columns WHERE table_name='crp' AND column_name='anulaciones') = 'character varying' THEN EXECUTE ' ALTER TABLE crp ALTER COLUMN valor_crp TYPE NUMERIC(20,2), ... ALTER…

---

### 9. `vigente` es invisible para el consumidor que ya existía: el comprometido del cockpit suma filas no vigentes

`apps/presupuesto/services/metrics.py:148` · gravedad **media**

**Qué pasa.** El 026 mete un borrado lógico (`vigente BOOLEAN NOT NULL DEFAULT TRUE`) en `crp`, una tabla que ya tenía consumidor: `metrics.py` la lee por el modelo `Crp` de `sql.py`, que no declara la columna y no la filtra en ninguna de sus cuatro agregaciones. Los endpoints nuevos sí filtran `c.vigente`; los viejos, no.

**Cómo falla.** Llega el corte de octubre y un CRP anulado desaparece del reporte. El cargador hace lo correcto: `vigente=FALSE`. `/crp/` y `/crp/resumen-por-proyecto/` bajan la cifra; `resumen_proyecto`, `resumen_programa` y `resumen_inversion` la siguen sumando, porque hacen `Crp.objects.filter(proyecto_id=...).aggregate(Sum('valor_crp'))` sin condición. El «comprometido» y el «disponible» del cockpit quedan por encima del real y nunca bajan, y las dos pantallas del mismo tablero muestran números distintos para el mismo proyecto sin que nada avise.

**Medido.** `apps/presupuesto/models/sql.py:49-66` — el modelo `Crp` declara 4 campos y ninguno es `vigente`. `metrics.py` líneas 74, 148, 201 y 237: cuatro `Crp.objects...aggregate(Sum("valor_crp"))`, cero filtros. Contra eso, `crp_views.py:47` y `:172` arrancan el WHERE con `["c.vigente"]`. Hoy no se nota porque `crp` está en 0 filas: la divergencia aparece en el segundo corte.

**Arreglo.** Dos líneas, sin DDL (la columna ya existe; el modelo es managed=False y solo hay que declararla). 1) apps/presupuesto/models/sql.py, en `class Crp` (después de `valor_crp`): vigente = models.BooleanField(default=True) 2) apps/presupuesto/services/metrics.py — agregar `.filter(vigente=True)` a las cuatro agregaciones: · línea ~74 (resumen_programa muerto): Crp.objects.filter(proyecto_id__in=proys, vigente=True) · línea ~148 (resumen_inversion): qs_crp = Crp.objects.filter(vigente=True) · línea…

---

### 10. El INSERT de `crp` va fila por fila: 2.630 ida y vuelta con `fetchone()` en cada una

`apps/presupuesto/services/crp_carga.py:406` · gravedad **baja**

**Qué pasa.** El bucle ejecuta un `INSERT … ON CONFLICT … RETURNING (xmax = 0)` por fila y hace `fetchone()` para llevar la cuenta de insertadas contra actualizadas. Son 2.630 ida y vuelta que podrían ser seis, porque `execute_values` con `fetch=True` devuelve el `RETURNING` de todo el lote y la cuenta se puede sumar igual.

**Cómo falla.** El costo de la carga lo fija la CANTIDAD de sentencias, no el volumen de datos, y la carga corre síncrona dentro del POST. Acá la base está en el mismo host y un round-trip cuesta 0,015 ms, así que las 11.210 sentencias dan 1,74 s y no falla. Pero `DB_HOST` sale del entorno y en el despliegue de Kubernetes apunta a una Postgres por red: con 1 ms por round-trip —conservador para una base remota— la misma carga son ~11 s de pura latencia dentro de una petición HTTP, contra ~0,1 s si va por lotes. Y mientras dure, las 2.630 filas de `crp` más los 1.412 terceros del hallazgo anterior siguen bloqueados: alargar la transacción ensancha la ventana del deadlock.

**Medido.** Medido: 2.630 sentencias y 436 ms de los 1.740 ms de la carga — el mayor costo SQL después de los terceros. Benchmark sobre las mismas 2.630 filas en transacción revertida: fila por fila 209 ms contra `execute_values(page_size=500)` 85 ms, 6 sentencias, mismas 2.630 insertadas (el benchmark usó un subconjunto de columnas; lo que traslada es la razón 2,5×). Latencia base medida con `SELECT 1` ×2000 = 31 ms.

**Arreglo.** Sacar el INSERT del loop, dejando el loop solo para lo que es cálculo en Python (`sin_contrato`, `sin_proyecto`, `choques_pep`). 1. Subir `_tipo_doc_codigo` fuera del bucle: son 5 tipos distintos en 2.630 filas, se resuelven de una con `{td: _tipo_doc_codigo(cur, td) for td in {f["tipo_doc"]… }}`. 2. Acumular los parámetros en una lista en vez de ejecutar, y al final: from psycopg2.extras import execute_values SQL = "INSERT INTO crp (…52 columnas…) VALUES %s ON CONFLICT … RETURNING (xmax = 0)"…

---

### 11. El `COMMIT;` embebido escapa de `transaction.atomic()`: probar el rollback «en seco» lo aplica de verdad

`apps/presupuesto/scripts/026_crp_bogdata_rollback.sql:68` · gravedad **baja**

**Qué pasa.** Los dos scripts traen su propio `BEGIN;`/`COMMIT;`. La vía de aplicación que este repo documenta —`connection.cursor().execute(open(script).read())`, porque el contenedor no tiene `psql`— no aísla eso: el `COMMIT` del archivo confirma dentro del bloque del que llama, y un rollback posterior del `transaction.atomic()` no deshace nada.

**Cómo falla.** El hábito de la casa es «lo pruebo en `transaction.atomic()` y lanzo una excepción al final para revertir». Quien haga eso con el rollback del 026 antes de decidir si lo corre, lo corre: se van `crp_carga`, `tercero_sap` y las 17 columnas nuevas de `crp`, y la excepción final no revierte nada porque el archivo ya confirmó. El guard del principio no ayuda: solo mira si hay cargas registradas, y en un ensayo típico no las hay.

**Medido.** Medido: dentro de `transaction.atomic()` se ejecutó `"BEGIN;\nCREATE TABLE _zz_probe_commit (i int);\nCOMMIT;"` y luego se lanzó la excepción que revierte el atomic — `SELECT to_regclass('_zz_probe_commit')` devolvió la tabla, viva (la borré). Es la misma forma exacta de los dos .sql del 026. Aparte, el guard sí funciona en esa vía cuando hay cargas: un `RAISE` en un `DO $$` cancela el resto del string multi-sentencia (verificado).

**Arreglo.** No tocar los .sql: el `BEGIN;`/`COMMIT;` tiene que quedarse para `psql -f`. Agregar `apps/presupuesto/scripts/apply_026_crp_bogdata.py` copiando el patrón de `apply_025_matriz_carga.py`: un `correr_sql()` que lea el archivo y filtre las líneas cuyo `strip().upper()` sea exactamente `"BEGIN;"` o `"COMMIT;"` (el `BEGIN` del bloque `DO $$ … END $$;` no lleva punto y coma y no se toca), más `--seco` que envuelva todo en `transaction.atomic()` y levante una excepción interna al final, y `--rollback`…

---

### 12. La PK natural no es NOT NULL, así que el índice único no la puede imponer y el upsert se puede burlar

> ✅ **Cerrado el 2026-09-10** (guarda en `validar` + DDL 028) — ver la bitácora al final.

`apps/presupuesto/scripts/026_crp_bogdata.sql:179` · gravedad **baja**

**Qué pasa.** `uq_crp_interno_posicion` se crea sobre `n_interno_crp` y `n_posicion_crp`, las dos nullables. En Postgres los NULL son distintos entre sí dentro de un índice único, así que el `ON CONFLICT (n_interno_crp, n_posicion_crp)` del cargador nunca dispara para una fila con la llave vacía.

**Cómo falla.** Un corte trae una fila con la celda «N° Interno CRP» en blanco (el lector la convierte en `None` con `_int`, y `validar()` no revisa nulos en la PK). Esa fila se inserta. El corte siguiente trae el mismo registro, otra vez sin interno: `ON CONFLICT` no encuentra nada y se inserta una fila NUEVA en vez de actualizar la vieja. Con doce cortes quedan doce copias del mismo CRP; once con `vigente=FALSE`, que los endpoints nuevos esconden pero `metrics.py` suma once veces al comprometido del proyecto (ver el hallazgo de `vigente`). `filas_insertadas` también miente: la cuenta como fila nueva cada mes.

**Medido.** Estado real de la base: `n_interno_crp bigint` e `n_posicion_crp integer`, ambas `is_nullable = YES`, y `uq_crp_interno_posicion` es un índice único plano sobre las dos, sin `NULLS NOT DISTINCT`. `crp_carga.py:_int()` devuelve `None` ante celda vacía o no numérica, y `validar()` solo verifica duplicados exactos con `Counter`, que trata `(None, 1)` como una llave más.

**Arreglo.** Dos arreglos independientes; el primero no necesita DDL y cierra el hueco hoy. 1. Guardia en `apps/presupuesto/services/crp_carga.py`, dentro de `validar()`, junto al chequeo de duplicados (que ya está ahí por la misma invariante): ```python sin_pk = [(i, f["numero_crp"]) for i, f in enumerate(filas, start=2) if f["interno_crp"] is None or f["posicion_crp"] is None] if sin_pk: raise CargaError( f"{len(sin_pk)} filas sin (N° Interno CRP, N° Posición CRP). " f"Ejemplos (fila del Excel, N° de…

---

## Bitácora

### 2026-09-07 — los dos graves, cerrados el mismo día

**`ON DELETE CASCADE` en `crp.carga_id`** (DDL 027). `carga_id` no significa
«la carga que trajo esta fila» sino «la última que la tocó» —el upsert lo
reescribe en cada corte—, así que borrar la carga más reciente se llevaba las
2.630 filas. Riesgo vivo: la carga real ya estaba aplicada. Pasó a `RESTRICT`;
verificado que las filas quedaron intactas.

**Un corte más viejo pisaba al nuevo.** Subir agosto encima de septiembre
entraba sin objeción y el tablero retrocedía $137.678 M —de $226.745 M a
$89.067 M—, con el agravante de que re-subir septiembre quedaba bloqueado por
el hash. Ahora se rechaza salvo `--permitir-retroceso` explícito, y el barrido
de `vigente=FALSE` se acotó a la misma vigencia: un reporte de otro año ya no
marca no vigente lo que ni venía a reemplazar.

Probado con el corte real cargado: el archivo de agosto rebota y los
$226.745 M quedan intactos.

### 2026-09-09 — metrics, y los dos frentes que faltaba verificar

**`metrics.resumen_inversion` sumaba `valor_crp` en vez de `valor_neto`** y
calculaba `disponible = asignado − comprometido` con `asignado = 0` (porque
`programa_cdp` está vacía). Con el CRP cargado eso ya no mostraba $0: mostraba
**−$264.234 M**, un déficit que no existe. Antes de la carga el defecto estaba
tapado por el vacío. Ahora suma el neto, filtra `vigente` y el disponible es
`None` con su motivo escrito cuando no hay con qué restar. De paso salió una
`resumen_programa` duplicada y muerta —Python se queda con la última— que
calculaba lo mismo con otro criterio.

**Los dos frentes que quedaron sin verificar** (`normalizador` e
`integracion`) se cerraron con una pasada adversarial de 15 agentes, cada uno
con el encargo de REFUTAR su hallazgo abriendo el código y midiendo contra la
base real en transacciones revertidas. De 19: 4 ya los cubría el arreglo de
metrics, **6 no sobrevivieron** y **9 eran reales**.

Los seis refutados vale la pena dejarlos escritos, porque volverán a
proponerse:

| # | Lo que decía | Por qué no |
|---|---|---|
| 2, 10 | los endpoints de CRP no aplican `subgrupos_visibles`/`aplicar_subgrupo` | el hecho es cierto pero no hay asimetría: en todo `apps/presupuesto` hay UN solo uso de `aplicar_subgrupo`. Es la convención del módulo, no un descuido de éste |
| 5 | los 2.209 compromisos sin contrato no se pueden re-enganchar nunca porque el hash bloquea | el upsert recalcula `contrato_id` en cada carga, así que el próximo corte los reengancha. Lo que impide el cruce es que `contrato` tiene 25 filas contra 2.227 pares del CRP: no hay a qué enganchar |
| 6 | tres índices que ninguna consulta puede usar | medido con `EXPLAIN ANALYZE`: cuatro se usan y el planificador los elige |
| 16 | `tipo_de_rubro` manda las obligaciones de funcionamiento al balde de inversión | da lo contrario: `O219001/O219002` devuelven `obligacion_por_pagar`, nunca `inversion` |
| 18 | `proyecto_de_pep` devuelve «0008», un proyecto que no existe | el valor nunca se consume ni se persiste: su único lector está guardado por `cod_proy` truthy, que para esas filas es `None` |

Los nueve confirmados quedaron cerrados en `d5e7b56`. Dos merecen quedar
anotados por lo que enseñan:

**El permiso de escritura no existía.** Subir el CRP o aplicar la Matriz no
editan una fila: sustituyen el libro entero. El endpoint solo pedía
`presupuesto_proyectos`, que también tiene el rol provisionado para UN
contrato. Reproducido con su JWT real y un `.xlsx` de una sola fila: el
comprometido de la localidad pasaba de $226.744 M a $56 M, y no se deshace
desde la pantalla porque el hash impide resubir el corte legítimo y el FK es
RESTRICT. Se gateó con `presupuesto_cdp` y **no** con el alcance de `ve_todo`,
que sería lo conceptualmente exacto: hoy `ve_todo` solo es cierto para
superusuarios —los Admin que no lo son quedan acotados a su subgrupo porque su
pertenencia global todavía no está creada—, así que exigirlo habría dejado el
cargue en manos de cuatro cuentas. Cuando el refactor de RBAC por subgrupos
complete esas pertenencias, el gate correcto es el alcance.

**El upsert congelaba 37 de 50 columnas.** El `DO UPDATE SET` estaba escrito a
mano con 13, y las tres derivadas estaban entre ellas: en el corte siguiente la
fila quedaba con el proyecto nuevo y el rubro viejo, con el tercero nuevo y la
cédula del anterior. Contradiciéndose consigo misma, sin error. La lección no
es «faltaban columnas» sino que una lista escrita al lado de otra se separa: el
SQL ahora se deriva de una única lista de columnas, así que el SET es el INSERT
menos la llave por construcción. Medido: el corte de octubre entra 100 % por la
rama UPDATE, o sea que esto se activaba entero en la siguiente carga.

### Lo que queda abierto

**La atribución por contrato aplica desde el próximo corte.** Las 23 filas de
obligaciones por pagar cuyo contrato sí está en innovaK —$11.200 M— siguen con
`proyecto_id` NULL en la base: el arreglo corre en la carga, y el corte de
septiembre ya está aplicado. Se corrige solo en octubre. Si hace falta antes,
el camino sancionado es reguardar el Excel (bytes distintos, dato idéntico →
hash distinto) y volver a subirlo; recargarlo hoy sin tocar nada es un no-op
exacto salvo por esas 23 filas.

**El comprometido es el del PDL 2025-2028, no el del estado de cuenta**
(decisión de Alex, 2026-09-09: «las vigencias pasadas no las contemos… solo el
cuatrienio 2025-2028»). El corte va por el AÑO DEL COMPROMISO y no por
`es_obligacion_por_pagar`, y la distinción no es cosmética: de los $135.078 M
de obligaciones por pagar, **$93.209 M son de compromisos de 2025** —dentro del
Plan, ejecución legítima suya— y solo $41.906 M vienen de 2024 hacia atrás,
hasta 2013. Cortar por la bandera habría sacado los $93.209 M junto con el
resto.

| | |
|---|---|
| Estado de cuenta completo (lo que manda BogData) | $226.744.982.139 |
| Comprometido del PDL 2025-2028 (lo que publica el módulo) | **$184.839.187.185** |
| Anterior al PDL, separado y visible | $41.905.794.954 |

Las 140 filas sin año de compromiso se quedan DENTRO: son las que traen un
número que no es un contrato («EDIL 4 FDLK», «EPS017», documentos SAP), todas
del ejercicio 2026. No tener año parseable no las vuelve viejas.

La lista cruda de `/presupuesto/api/crp/` sigue trayendo todo, que es lo
correcto para un estado de cuenta; `solo=pdl` y `solo=anterior_al_pdl`
reproducen los dos lados para que la diferencia contra el módulo se pueda
explicar sin abrir el código.

**Los que siguen abiertos tras el 2026-09-10**: el 8 (el 026 no se puede
reaplicar), el 10 (el INSERT fila por fila) y el 11 (el `COMMIT;` embebido).
Ninguno escribe datos equivocados en el corte siguiente. El 4 (enmascarado)
quedó decidido: se mantiene el comportamiento actual.

### 2026-09-10 — los cuatro que caducaban con el corte de octubre

Los cuatro fallaban **solo en el segundo corte**, que es lo que los hacía
urgentes: en octubre habrían dejado datos que reparar en vez de código que
arreglar.

**La PK natural (12).** `validar()` rechaza la fila sin
`(N° Interno CRP, N° Posición CRP)` nombrando la fila del Excel, y el **DDL
028** pone las dos columnas NOT NULL. Las 2.630 del corte real la traen
completa, así que el ALTER no perdió nada.

**El NIT distrital (3).** `bp_sap` entró en la llave del tercero —índice único
sobre `(tipo_doc, num_doc, COALESCE(bp_sap, -1))`, porque en Postgres dos NULL
no chocan y un corte sin business partner crearía una fila por carga—. Probado
con el archivo real en transacción revertida: las siete entidades quedan
separadas y **Integración Social recupera sus $31.127.780.186**. Además la
lista devuelve `crp.nombre_bp_beneficiario`, que es el nombre correcto de cada
fila y estaba guardado desde la primera carga.

**El upsert de terceros (6).** Una sola sentencia con las claves ORDENADAS, que
es lo que de verdad quita el deadlock. Medido sobre el archivo real: de 8.472
sentencias a 1 y de 710 ms a 36 ms; la carga entera pasa de 11.210 sentencias y
1,74 s a **2.741 y 0,5 s**.

**El corte que mentía (7).** `_resolver_corte` lo resuelve contra `crp_carga`
antes de consultar y filtra por `carga_id`: un corte que no existe da 400 y uno
anterior al último da **409** diciendo que del corte pedido solo queda el total
en el historial. Antes devolvía `total=0` y `suma=0`, un cero que parece
medido, mientras la pantalla seguía ofreciendo esa carga con sus $226.745 M.

**Un test que encodificaba el defecto.** `test_la_matriz_manda_sobre_secop_al_
calificar_la_plata` exigía que un SECOP en 0 % produjera la anotación «las dos
fuentes no coinciden» — justo lo que la regla nueva prohíbe. Se reescribió con
una discrepancia real (20 % contra 80 %) y se agregaron los dos casos del cero
ambiguo. La lección es la misma del cargue de la Matriz: cuando el número era
un proxy de la invariante, se reemplaza por la invariante.

**Quedan sin tocar** los hallazgos 4, 8, 10 y 11 —el enmascarado (decidido:
se queda como está), el 026 no reaplicable, el INSERT fila por fila y el
`COMMIT;` embebido—. Ninguno escribe datos equivocados en el corte siguiente.
