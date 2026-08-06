# Ledger de scripts DDL — innovaK

> **Generado, no escrito a mano.** Se regenera con:
>
> ```bash
> docker exec -i -e LEDGER=md innova_k python manage.py shell < scripts/ledger_ddl.py
> ```
>
> Última generación: **2026-08-06**.

---

## 1. Para qué sirve

La base de datos es **externa y `managed=False`**: Django no migra nada, así que
cada cambio de esquema vive en un `.sql` que alguien corrió a mano. Había **91
scripts en 14 carpetas** y **ningún registro** de cuáles se habían aplicado.

Eso tiene un costo concreto: cada auditoría volvía a averiguarlo desde cero, y
equivocarse significa correr dos veces un `ALTER` —o peor, dar por aplicado
algo que no lo está y construir encima—.

**El estado NO se declara: se deduce de la base.** El script lee cada `.sql`,
extrae los objetos que declara (tablas, columnas, índices, secuencias, y los
`RENAME COLUMN`) y le pregunta a `information_schema` si existen. Nadie tiene
que acordarse de marcar nada, y por eso el ledger no puede quedar desactualizado
respecto a la realidad — solo hay que volver a correrlo.

Es **solo lectura**: no ejecuta ni un DDL.

## 2. Resultado

| Estado | Scripts | Qué significa |
|---|---|---|
| ✅ aplicado | **60** | todos los objetos que declara existen |
| ⚠️ parcial | **1** | algunos sí y otros no — hay que mirarlo |
| ⬜ pendiente | **1** | ninguno existe todavía |
| DML | 5 | solo mueven datos; no declaran objetos |
| rollback | 24 | inversos; no se evalúan |

**De 91 scripts, solo 2 requieren atención.** El resto está aplicado, es un
rollback o es DML.

### Los dos que hay que mirar

**⚠️ `banco_iniciativas/008_banco_evaluacion.sql`** — 4 de 6 objetos. Faltan
`banco_evaluacion_comite_criterio` y su índice. **No es un error**: el
Documento Maestro del Banco II (2026-07-29) eliminó el comité de la matriz
oficial, así que esa tabla se dejó deliberadamente sin crear. Queda anotado
para que la próxima auditoría no lo lea como un DDL a medio aplicar.

**⬜ `georeferenciacion/021_columnas_espejo_c3.sql`** — 0 de 13. Es el DDL de
las columnas espejo de **C3**, escrito el 2026-08-06 y **a la espera de OK
explícito** para aplicarse. Es correcto que salga pendiente: todavía no se
corrió.

## 3. 🔴 Colisiones de numeración

Son **7 reales**, no las dos que decía el inventario. (Los pares
`NNN_x.sql` / `NNN_x_rollback.sql` **no** son colisión: son un script y su
inverso.)

| Carpeta | Prefijo | Scripts distintos que lo comparten |
|---|---|---|
| `banco_iniciativas` | `005` | `banco_qa_disciplina` · `v2_pr2_soporte_legal` |
| `banco_iniciativas` | `006` | `banco_territorial_upz` · `v2_pr3_escenarios_actuales` |
| `caracterizacion` | `002` | `n20_funcionario_id` · `seguridad_setup` |
| `login` | `003` | `actividades_pr2_tipo_evento_flags` · `n27_limpieza_datos` · `unificar_capacitacion_en_curso` |
| `login` | `004` | `actividades_pr3_subgrupo_linea` · `n22_beneficiario_unique` |
| `login` | `006` | `clase_fecha_hora` · `cursos_cupo_lista_espera` |
| `presupuesto` | `009` | `c3_unifica_synced_at` · `sdp_programa_objetivo` |

**Por qué importa:** el número deja de decir el orden. Con tres scripts `003`
en `login`, «aplicá el 003» es ambiguo, y si dos tocan la misma tabla el orden
entre ellos cambia el resultado.

**No se renumeran.** Renombrar un script ya aplicado rompe las 28 referencias
que hay en docstrings de modelos y comandos (`sync_cai.py` dice «requiere que
`cai` exista: `020_cai_seguridad.sql`»), y esas referencias no fallan: solo
quedarían mintiendo. Se documentan acá y **la convención se aplica de aquí en
adelante**.

## 4. La convención, de aquí en adelante

1. **El número es por carpeta y no se reutiliza.** Antes de crear uno, mirar el
   más alto de esa carpeta y sumar uno. Esta tabla sirve para eso.
2. **Todo script de esquema lleva su `_rollback.sql`.** Hoy lo tienen **24 de
   68** — poco más de un tercio. Sin rollback, deshacer un DDL en una base
   compartida es improvisar bajo presión.
3. **Idempotente siempre**: `IF NOT EXISTS`, `IF EXISTS`. Correrlo dos veces no
   puede fallar — es la única defensa real contra no saber si ya se corrió.
4. **Encabezado con qué hace, por qué, y cuándo se aplicó.** El ledger dice
   *si* se aplicó; el encabezado dice *para qué*.

## 5. Lo que NO se hizo, y por qué

El plan original decía «archivar ~90 scripts SQL». **No se archivaron**, y es
una decisión, no un olvido.

Mover los 60 aplicados a carpetas `aplicados_*` dejaría **28 referencias
apuntando a rutas que ya no existen** — en `CLAUDE.md`, en docstrings de
modelos y en comandos de sincronización. Esas referencias no lanzan ningún
error: simplemente pasan a mentir. Es exactamente el tipo de deuda documental
que este mismo bloque estuvo corrigiendo toda la jornada.

Y el problema que el archivo pretendía resolver —«no saber qué se aplicó»— ya
lo resuelve este ledger, que además no envejece: se regenera contra la base.

Si aun así se quiere archivar, el orden correcto es: mover **y** actualizar las
28 referencias en el mismo commit. Es media hora, pero es de Alex la decisión.

---

## 6. El inventario completo

### `banco_iniciativas`

| Script | Estado | Detalle | Rollback |
|---|---|---|---|
| `002_banco_qa_lote2.sql` | ✅ aplicado | 8 objeto(s) | — |
| `003_banco_qa_lote3.sql` | ✅ aplicado | 1 objeto(s) | — |
| `004_banco_qa_lote4.sql` | ✅ aplicado | 15 objeto(s) | — |
| `005_banco_qa_disciplina.sql` | DML | solo datos | — |
| `005_v2_pr2_soporte_legal.sql` | ✅ aplicado | 1 objeto(s) | — |
| `006_banco_territorial_upz.sql` | ✅ aplicado | 1 objeto(s) | — |
| `006_v2_pr3_escenarios_actuales.sql` | ✅ aplicado | 4 objeto(s) | — |
| `007_banco_escenario_detalle.sql` | ✅ aplicado | 3 objeto(s) | — |
| `008_banco_evaluacion.sql` | ⚠️ parcial | faltan: banco_evaluacion_comite_criterio, idx_banco_eval_comite_eval | — |
| `009_banco_comite_binario.sql` | ✅ aplicado | 1 objeto(s) | — |
| `010_estrato_ideca_org.sql` | ✅ aplicado | 1 objeto(s) | — |
| `011_fuera_kennedy_geo_metodo.sql` | ✅ aplicado | 2 objeto(s) | sí |
| `012_direccion_lonlat.sql` | ✅ aplicado | 2 objeto(s) | sí |
| `013_banco_documento_maestro.sql` | ✅ aplicado | 24 objeto(s) | sí |

### `caracterizacion`

| Script | Estado | Detalle | Rollback |
|---|---|---|---|
| `001_n12_setup.sql` | ✅ aplicado | 8 objeto(s) | sí |
| `002_n20_funcionario_id.sql` | ✅ aplicado | 12 objeto(s) | sí |
| `002_seguridad_setup.sql` | ✅ aplicado | 3 objeto(s) | — |
| `003_paz_setup.sql` | ✅ aplicado | 3 objeto(s) | — |

### `dashboard`

| Script | Estado | Detalle | Rollback |
|---|---|---|---|
| `004_hub_card.sql` | ✅ aplicado | 2 objeto(s) | — |

### `educacion`

| Script | Estado | Detalle | Rollback |
|---|---|---|---|
| `001_educacion_setup.sql` | ✅ aplicado | 9 objeto(s) | — |
| `002_implemento_educativo.sql` | DML | solo datos | — |

### `entregas`

| Script | Estado | Detalle | Rollback |
|---|---|---|---|
| `001_entregas_setup.sql` | ✅ aplicado | 5 objeto(s) | — |

### `festivales`

| Script | Estado | Detalle | Rollback |
|---|---|---|---|
| `001_festivales_setup.sql` | ✅ aplicado | 7 objeto(s) | — |
| `002_festival_geo.sql` | ✅ aplicado | 4 objeto(s) | sí |
| `003_festival_dia.sql` | ✅ aplicado | 7 objeto(s) | — |
| `004_festival_biblioteca.sql` | ✅ aplicado | 4 objeto(s) | — |
| `005_festival_aforo.sql` | ✅ aplicado | 5 objeto(s) | — |
| `006_festival_evaluacion.sql` | ✅ aplicado | 9 objeto(s) | — |
| `007_festival_percepcion.sql` | ✅ aplicado | 4 objeto(s) | — |

### `georeferenciacion`

| Script | Estado | Detalle | Rollback |
|---|---|---|---|
| `011_geocodificacion_cache.sql` | ✅ aplicado | 2 objeto(s) | sí |
| `012_placa_domiciliaria.sql` | ✅ aplicado | 4 objeto(s) | sí |
| `013_capas_territorio.sql` | ✅ aplicado | 5 objeto(s) | sí |
| `014_escuela_censo_julio.sql` | ✅ aplicado | 8 objeto(s) | sí |
| `020_cai_seguridad.sql` | ✅ aplicado | 4 objeto(s) | — |
| `021_columnas_espejo_c3.sql` | ⬜ pendiente | falta todo (13) | sí |
| `ddl_01_geometry_upz_barrio.sql` | ✅ aplicado | 2 objeto(s) | — |
| `ddl_02_create_parque.sql` | ✅ aplicado | 4 objeto(s) | — |
| `ddl_03_create_escuela.sql` | ✅ aplicado | 5 objeto(s) | — |
| `ddl_estratificacion_ideca.sql` | ✅ aplicado | 3 objeto(s) | — |

### `jovenes_a_la_e`

| Script | Estado | Detalle | Rollback |
|---|---|---|---|
| `001_jovenes_setup.sql` | ✅ aplicado | 8 objeto(s) | — |
| `002_fix_puente_id.sql` | ✅ aplicado | 1 objeto(s) | — |

### `login`

| Script | Estado | Detalle | Rollback |
|---|---|---|---|
| `001_n15_setup.sql` | ✅ aplicado | 6 objeto(s) | sí |
| `002_n15_fix_usuario_grupos_unique.sql` | DML | solo datos | — |
| `003_actividades_pr2_tipo_evento_flags.sql` | ✅ aplicado | 2 objeto(s) | — |
| `003_n27_limpieza_datos.sql` | DML | solo datos | sí |
| `003_unificar_capacitacion_en_curso.sql` | DML | solo datos | — |
| `004_actividades_pr3_subgrupo_linea.sql` | ✅ aplicado | 5 objeto(s) | — |
| `004_n22_beneficiario_unique.sql` | ✅ aplicado | 1 objeto(s) | sí |
| `005_curso_sesiones_secuencias.sql` | ✅ aplicado | 11 objeto(s) | sí |
| `006_clase_fecha_hora.sql` | ✅ aplicado | 5 objeto(s) | sí |
| `006_cursos_cupo_lista_espera.sql` | ✅ aplicado | 3 objeto(s) | — |
| `007_evento_escuela.sql` | ✅ aplicado | 2 objeto(s) | — |
| `008_clase_dictada_por.sql` | ✅ aplicado | 2 objeto(s) | sí |
| `009_evento_horas.sql` | ✅ aplicado | 3 objeto(s) | sí |
| `010_usuario_funcionario.sql` | ✅ aplicado | 2 objeto(s) | sí |
| `011_usuario_pertenencia.sql` | ✅ aplicado | 4 objeto(s) | — |
| `012_auditoria_pertenencia.sql` | ✅ aplicado | 3 objeto(s) | — |
| `ddl_01_info_terreno.sql` | ✅ aplicado | 1 objeto(s) | — |

### `onboarding`

| Script | Estado | Detalle | Rollback |
|---|---|---|---|
| `001_onboarding_setup.sql` | ✅ aplicado | 2 objeto(s) | sí |

### `presupuesto`

| Script | Estado | Detalle | Rollback |
|---|---|---|---|
| `003_n3_contrato_id_bigserial.sql` | ✅ aplicado | 2 objeto(s) | sí |
| `004_contratos_infraestructura.sql` | ✅ aplicado | 11 objeto(s) | sí |
| `005_intervencion_parque_direccion.sql` | ✅ aplicado | 1 objeto(s) | sí |
| `006_corte_avance_obra.sql` | ✅ aplicado | 3 objeto(s) | sí |
| `007_sdp_oficial.sql` | ✅ aplicado | 4 objeto(s) | — |
| `008_secop_contrato.sql` | ✅ aplicado | 4 objeto(s) | — |
| `009_c3_unifica_synced_at.sql` | ✅ aplicado | 3 objeto(s) | — |
| `009_sdp_programa_objetivo.sql` | ✅ aplicado | 6 objeto(s) | — |
