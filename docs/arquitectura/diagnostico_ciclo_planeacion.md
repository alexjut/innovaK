# Diagnóstico del ciclo de planeación

**Fecha:** 2026-08-26 · **Estado:** diagnóstico, no diseño
**Alcance:** qué existe hoy, medido. **No** propone modelo, **no** propone DDL,
**no** se implementó nada.

> **Continúa en** [`specs/004-formulacion/plan.md`](../../specs/004-formulacion/plan.md):
> el análisis A–G y el plan por fases del dominio **Formulación** (2026-08-26).

> **Para qué existe este documento.** Antes de adaptar innovaK al ciclo
> `Plan de Desarrollo → Proyecto → Vigencia → Meta → Programación → PAA/apropiación
> → CDP → CRP → Contrato/compromiso → Ejecución → Seguimiento → Cumplimiento`,
> hay que saber cuánto de ese ciclo ya está construido. La respuesta corta es
> que **está construido casi entero como esquema y casi vacío como datos**, y
> que el tramo del medio —el dinero— nunca se conectó.

---

## 0 · Cómo se midió, y por qué importa

Todo lo que sigue está medido contra la base real `poblacion_kennedy`
(PostgreSQL 16.15) y contra el código del repositorio el **2026-08-26**. Nada
viene de los documentos: varios de ellos están vencidos y se señalan abajo.

Dos reglas de lectura que este proyecto ya pagó caras:

1. **Un `0` puede ser un JOIN vacío, no un dato faltante.** Cada tabla en cero
   de este informe dice además *por qué* está en cero: nadie la llena, el
   código nunca la lee, o ambas.
2. **Buscar un nombre no es verificar una propiedad.** Las afirmaciones sobre
   relaciones se comprobaron contando las filas que de verdad empatan, no
   leyendo el modelo.

**Este diagnóstico no asume equivalencias.** Las que parecen ciertas
(`Actividad = Meta`, `Contrato = Compromiso`) están en §8 como **hipótesis con
su evidencia**, no como hechos.

---

## 1 · Estado actual

### 1.1 El tamaño real

| | |
|---|---|
| Tablas en `public` | **268** + 4 vistas |
| Tablas **con datos** | **160** |
| Tablas **vacías** | **108** (40 %) |
| Modelos Django registrados | **204** (176 clases + 28 de bases abstractas) |
| Modelos con `managed=True` | **1** (`login.Sisben`, 0 filas) |

El esquema está diseñado muy por delante de lo que se llenó. Y las tablas
vacías no están repartidas al azar: **casi todo el tramo presupuestal del ciclo
está en cero.**

### 1.2 El ciclo, de un vistazo

```
Plan de Desarrollo   ▓▓▓▓▓▓▓░░░  espejo oficial cargado, cadena interna a medias
Proyecto             ▓▓▓▓▓▓▓▓▓░  12 internos contra 28 oficiales
Vigencia             ▓▓░░░░░░░░  catálogo sano (8 filas) que casi nadie usa
Meta                 ▓▓▓▓▓▓▓░░░  24 metas, 11 con código oficial
Programación         ▓▓▓░░░░░░░  la física existe; la presupuestal está vacía
PAA / apropiación    ░░░░░░░░░░  NO EXISTE — ni tabla, ni código, ni mención
CDP                  ▓▓░░░░░░░░  5 filas, 4 son marcadores sin número ni valor
CRP                  ░░░░░░░░░░  0 filas — y el tablero las suma igual
Contrato             ▓▓▓▓▓▓▓▓░░  25 internos, 3.074 en el espejo de SECOP
Compromiso           ░░░░░░░░░░  0 filas, y la tabla es un catálogo, no un hecho
Ejecución física     ▓▓▓▓░░░░░░  9 avances, repartidos en cinco mecanismos
Seguimiento de metas ▓▓▓░░░░░░░  6 de 23 indicadores tienen algún avance
Cumplimiento del PDL ▓▓░░░░░░░░  5 de 12 proyectos llegan a un programa
```

### 1.3 Los tres hechos que mandan sobre todo lo demás

**a) La mitad presupuestal del ciclo existe como esquema y está vacía.**
`crp` 0 · `compromiso` 0 · `rubro` 0 · `fondo` 0 · `fuente_financiacion` 0 ·
`centro_gestor` 0 · `cuenta_contable` 0 · `periodo_fiscal` 0 · `elemento_pep` 0 ·
`modalidad_seleccion` 0 · `tipo_cdp` 0 · `tipo_crp` 0 · `tipo_compromiso` 0 ·
`tipo_proceso` 0 · `presupuesto_proyecto` 0 · `presupuesto_tiempo` 0 ·
`reservas` 0 · `recursos` 0 · `contrato_plan_pago` 0.

No es dato perdido: es el esqueleto de **BogData** que alguien creó con sus FKs
y que nunca recibió una carga. `crp` tiene **48 columnas y 15 FKs** —
`no_compromiso`, `numero_de_crp`, `rubro_codigo`, `fondo_codigo`,
`elemento_pep`, `autorizacion_giro`— y **cero filas**.

**b) Y el tablero las suma igual.** `apps/presupuesto/services/metrics.py:74,148,201,237`
agrega `Crp.objects` con `Coalesce(Sum(...), Value(0))`. Se llama en vivo desde
`apps/presupuesto/api/views.py:1154` y `apps/festivales/api/views.py:506`. El
resultado es **$0 comprometido** — no porque no haya compromisos, sino porque
la tabla que los guardaría nunca se alimentó. Es el caso de manual del cero que
es un JOIN vacío.

**c) La cadena nunca llega a la persona.** Medido hoy:

- De los **23 eventos** enganchados a una actividad del plan, **0** tienen participantes.
- De los **28 eventos** con participantes, **0** están enganchados al plan.
- De los **5 contratos** enganchados al plan, **0** tienen beneficiarios.
- Hay 2.545 participantes y 2.950 vínculos contrato↔beneficiario. Ninguno cruza.

El corte es doble y en los dos extremos. Hoy no se puede responder *«a cuántas
personas llegó esta meta»* por la cadena; solo por fuera de ella.

### 1.4 Documentos que hoy dicen algo falso

| Documento | Dice | La base dice |
|---|---|---|
| `apps/presupuesto/models/core.py:127-129` (y `seed_seguridad_convivencia.py:478`) | `contrato.id` no tiene secuencia — **deuda S5** | Es `GENERATED BY DEFAULT AS IDENTITY`, secuencia `contrato_id_seq`, `last_value=386`. Comprobado con un INSERT real revertido: asignó el 386 |
| `docs/RUMBO.md:119` | El cron de sincronización **nunca se instaló** | `crontab -l` lo tiene desde el 2026-08-07; hay 20 días de logs y hoy corrió a las 03:30 con las 11 fuentes en OK |
| `docs/arquitectura/ARQUITECTURA.md:298` | `contrato_actividad` tiene **98 filas** | 18 |
| `CLAUDE.md` §3 | Varias clases sobre la misma `db_table`: Evento, Actividad, Programa, Zona | Solo quedan dos pares: `TipoDiscapacidad` y `OrientacionSexual` (login vs banco_iniciativas). Los demás se retiraron |
| `docs/GLOSARIO.md:17` | El Proyecto «tiene código, subgrupo, **vigencia**» | `proyecto` tiene 7 columnas y **ninguna es vigencia** |
| `specs/003…/spec.md:201` | No hay UNIQUE sobre la identidad del contrato | Hay **dos, idénticos**: `uq_contrato_tripleta` y `uq_contrato_tripleta_idx` sobre (tipo, número, vigencia) |
| `CLAUDE.md` §3 | «Prefijo `public.` en `db_table`: solo 3 clases lo usan» | **Cero clases.** `grep 'db_table = "public.'` no da un solo resultado |
| `docs/RUMBO.md:1.2` | La cadena medida: 11 proyectos, 24 contratos, 4 ligados a actividad | Hoy: 12 proyectos, 25 contratos, **5** ligados. Cifras de agosto 5, no de hoy |

La afirmación de la deuda S5 está repetida en **nueve sitios** entre código,
specs, `brain/` y documentos de operación. Y no es inocua: el código que la
«compensa» inserta ids explícitos (106, 107…) que **no avanzan la secuencia**,
hoy en 386. El día que un INSERT sin id tome el 387 y alguien vuelva al
`MAX(id)+1`, chocan.

---

## 2 · Modelo de datos existente

### 2.1 Las piezas del ciclo

Todas `managed=False` salvo donde se indique.

| Modelo | App | Tabla | Filas | Función | Observación crítica |
|---|---|---|---|---|---|
| `Proyecto` | presupuesto | `proyecto` | **12** | Proyecto de inversión | Mapea 5 de 7 columnas. **No mapea `dependencia_id`** (FK real) ni `nombre_ci` |
| — | — | `proyectos` | **0** | Tabla gemela muerta | **Sin modelo Django.** Es la que SÍ tenía `vigencia` y `codigo_meta` |
| `Vigencia` | presupuesto | `vigencia` | **8** | 2020–2027 con fechas | Catálogo sano. Solo lo usan `programas`, `concepto_gasto` (1 fila de prueba) y `proyectos` (muerta) |
| `Objetivo` | presupuesto | `objetivo` | **6** | Nivel alto del plan interno | Sin trazabilidad al plan oficial |
| `Programa` | presupuesto | `programas` | **7** | Programa del plan | 3 de las 7 son filas de prueba («prueba planig programa») |
| `MetaBD` | presupuesto | `metas` | **24** | Catálogo de metas | **19 columnas, el modelo mapea 3.** `codigo_meta` (el enganche con SEGPLAN) no está mapeado y solo 11 de 24 lo tienen |
| `MetaProyectoBD` | presupuesto | `meta_proyecto` | **24** | Meta asignada a proyecto | El enganche vivo. Solo 1 de 24 tiene fechas |
| `Actividad` | presupuesto | `actividad` | **74** | Catálogo plano de nombres | **36 huérfanas** |
| `ActividadPlan` | presupuesto | `actividad_plan` | **54** | Actividad del plan de un proyecto | Solo 35 apuntan al catálogo |
| `Indicador` | presupuesto | `presu_indicador_meta_proyecto` | **23** | KPI de la meta | Cubre 22 de 24 metas |
| `ActividadIndicador` | presupuesto | `actividad_indicador` | **20** | N:N actividad ↔ KPI | Cubre 19 de 54 actividades |
| `AvanceIndicador` | presupuesto | `presu_avance_ind_periodo` | **9** | Ejecución física | `periodo` es `char(7)` **mensual** (`YYYY-MM`), no trimestral |
| `SdpMetaOficial` | presupuesto | `sdp_meta_oficial` | **280** | Espejo de Planeación | **Cero FK.** Ver §2.3 |
| `Cdp` | presupuesto | `cdp` | **5** | Disponibilidad presupuestal | **4 son marcadores** con número, fecha y valor en NULL |
| `Crp` | presupuesto | `crp` | **0** | Registro presupuestal | **48 columnas en la tabla, 5 mapeadas.** El mapeo más incompleto del repo |
| `Contrato` | presupuesto | `contrato` | **25** | Contrato | 24 columnas, todas mapeadas. `contrato_vigencia` es un entero suelto **sin FK** a `vigencia` |
| `PresupuestoProyecto` | presupuesto | `presupuesto_proyecto` | **0** | Asignado/comprometido/obligado/pagado | Carga perezosa (§2.2) |
| `PresupuestoTiempo` | presupuesto | `presupuesto_tiempo` | **0** | Cronograma planeado vs real + `avance_pct` | Carga perezosa. **La única estructura que ata proyecto + actividad + fase en el tiempo** |
| `FaseProyecto` | presupuesto | `fase_proyecto` | **3** | Planeación / Ejecución / Cierre | Carga perezosa |
| `ProyectoInversion` | presupuesto | `proyecto_inversion` | **3** | Apropiación | **Las 3 son de prueba**: «prueba», «proyectpo invercion», «prueba 2 proyecto inver» |

### 2.2 Once modelos que Django no registra al arrancar

`apps.get_models()` devuelve **196 tablas**; tras importar a mano tres módulos
aparecen **11 más**. Sus módulos no están en ningún `__init__.py`:

- `apps/presupuesto/models/financiero.py` → `fase_proyecto`, `proyecto_inversion`,
  `proyecto_inversion_item`, `presupuesto_proyecto`, `presupuesto_tiempo`
- `apps/login/models/permisos.py` → `modulo`, `rol_modulo`, `rol_meta`,
  `usuario_pertenencia`, `auditoria_pertenencia`
- `apps/login/models/captura_generica.py` → `captura_generica`

**Cinco de las once son piezas centrales del ciclo presupuestal.** Existen,
están escritas, y el proyecto se comporta como si no existieran.

### 2.3 Lo que hay en la base y nadie modeló

22 tablas con datos y sin modelo Django. Las que importan:

| Tabla | Filas | Por qué importa |
|---|---|---|
| `contrato_beneficiario` | **2.950** | **El puente más grande del expediente.** Contrato → beneficiario. Solo se toca por SQL crudo en `apps/login/management/commands/conectar_beneficiarios.py:86-127` |
| `stg_beneficiarios` | **5.985** | Staging del cargue, con proyecto/meta/actividad/contrato. Sin PK, columnas con espacios y tildes |
| `presu_indicador` | 3 | Generación anterior de indicadores |
| `presu_impacto_actividad_indicador` | 3 | Los «Impactos» del ciclo: existen como 3 filas que nadie lee |
| `proyecto_inversion` / `_item` | 3 / 4 | Apropiación (datos de prueba) |
| `fase_proyecto` | 3 | Fase del proyecto |
| `tipo_contrato` | 5 | **No es el catálogo de `contrato.contrato_tipo`** (§8) |
| `placa_domiciliaria` | 3.542.454 | Y un `_bak` con 1.771.088 |

---

## 3 · Relaciones encontradas

### 3.1 La cadena, como funciona de verdad

```
                    ┌── meta_proyecto (24) ── presu_indicador_meta_proyecto (23)
                    │                              │
   proyecto (12) ───┤                              ├── actividad_indicador (20)
   [subgrupo_id]    │                              │
                    └── actividad_plan (54) ───────┘
                              │
                              ├── contrato_actividad_plan (15) ── contrato (25)
                              │        14 de 15 con monto = 0        │
                              │                                      ├── cdp (5)  ✗ crp (0)
                              └── evento (23 de 55)                  └── contrato_beneficiario (2.950)
                                        │                                     [sin modelo Django]
                                        └── participante_evento (2.545)
                                              ↑
                                        ✗ NUNCA los mismos eventos
```

### 3.2 Cuántas filas empatan de verdad

| Salto | Empata | De |
|---|---|---|
| proyecto → meta_proyecto | 12 | 12 |
| meta_proyecto → indicador | 22 | 24 |
| indicador → actividad (via `actividad_indicador`) | 19 | 54 actividades |
| actividad_plan → contrato (via plan) | 13 | 54 |
| contrato → actividad del plan | **5** | 25 |
| contrato → proyecto | 20 | 25 |
| contrato → CDP | **4** | 25 |
| contrato → CRP | **0** | 25 |
| contrato → etapa contractual | **0** | 25 |
| evento → actividad del plan | 23 | 55 |
| indicador → algún avance | **6** | 23 |
| proyecto → programa (llegar al PDL) | **5** | 12 |
| proyecto interno → proyecto oficial SDP | 11 | 12 (normalizando ceros a la izquierda) |
| meta interna → meta oficial SEGPLAN | **11** | 24 |

### 3.3 Cuatro vías contrato → proyecto, y todas coinciden

| Vía | Cubre | ¿La lee el código? |
|---|---|---|
| `contrato_proyecto` | 20 de 25 | Sí |
| `contrato_actividad_plan` | 5 de 25 | Sí |
| `contrato_actividad` → `actividad_plan` | 16 contratos | **No, ningún servicio** |
| `contrato.proyecto_codigo` | 5 de 25 | Parcialmente |

Pares (contrato, proyecto) que las vías C o D afirman y las dos primeras no: **0**.
Contratos con más de un proyecto sumando las cuatro: **0**. La unión de A y B
cubre 24 de 25 sin una sola contradicción — por eso el código usa la unión.

### 3.4 Un defecto vivo: `panel_area` no usa la unión

`apps/presupuesto/services/panel_area.py:144-146` lee **solo**
`ContratoProyecto`. Los otros cuatro servicios del mismo módulo usan la unión.

Medido: el subgrupo **38 (Seguridad)** tiene **0 contratos** por
`contrato_proyecto` y **4** por `contrato_actividad_plan`, por
**$6.944.742.446**. En su propio panel de área, esa plata no aparece.

> *(Al medirlo hay que agrupar antes de sumar: la consulta ingenua con JOIN a
> actividades devuelve $28.857 millones porque cada contrato se cuenta una vez
> por actividad. Es el mismo fan-out que ya infló el denominador del avance.)*

### 3.5 Eslabones que el modelo permite y los datos dejan vacíos

`contrato_actividad_plan.meta_proyecto_id` 0/15 · `.concepto_gasto_id` 0/15 ·
`contrato.etapa_codigo` 0/25 · `contrato.forma_pago_codigo` 0/25 ·
`contrato.ejecucion` 4/25 · `cdp.valor` 1/5 · `metas.proyecto_id` 0/24 ·
`evento.linea_id` 0/55 (aunque `subgrupo_linea` tiene 19 filas).

**El más caro es el primero:** `meta_proyecto_id` es la columna que cerraría
contrato → meta. Existe, y está vacía en las 15 filas.

### 3.6 Eslabones que los datos necesitan y el modelo no ofrece

- **No hay tabla evento ↔ beneficiario.** El único `beneficiario_id` del ciclo
  está en `contrato_beneficiario` y en `crp`.
- **No hay columna de vigencia** en `proyecto`, `meta_proyecto` ni `actividad_plan`.
- **No hay columna de trimestre ni de corte** en ninguna tabla del esquema.
- **No hay FK** de `secop_contrato`, `secop_plan_pago` ni `sdp_meta_oficial`
  hacia lo interno: se unen por llave natural de texto.

---

## 4 · Información disponible

### 4.1 Lo propio del sistema

| Qué | Tabla | Filas | Observación |
|---|---|---|---|
| Proyectos | `proyecto` | 12 | 12/12 con subgrupo; 5/12 con programa; 1/12 con dependencia |
| Metas | `metas` | 24 | 11 con código SEGPLAN; `proyecto_id` NULL en las 24 |
| Meta ↔ Proyecto | `meta_proyecto` | 24 | El enganche vivo |
| Actividades del plan | `actividad_plan` | 54 | Sobre 9 proyectos |
| Actividades (catálogo) | `actividad` | 74 | 36 huérfanas |
| Indicadores | `presu_indicador_meta_proyecto` | 23 | 23/23 con magnitud y unidad |
| Avances | `presu_avance_ind_periodo` | 9 | 3 períodos: 2025-12, 2026-06, 2026-08 |
| Contratos | `contrato` | 25 | **Ninguno de 2026**: 23 de 2025, 1 de 2024, 1 de 2015 |
| CDP | `cdp` | 5 | 1 real, 4 marcadores |
| Eventos | `evento` | 55 | 23 con actividad, 19 con indicador |
| Personas | `persona` | 7.120 | |
| Beneficiarios | `beneficiario` | 5.598 | 5.573 persona / 25 organización |
| Contrato ↔ beneficiario | `contrato_beneficiario` | 2.950 | Sobre 15 contratos |
| Participantes de evento | `participante_evento` | 2.545 | Sobre 28 eventos |
| Funcionarios | `funcionario` | 26 | En 15 de 46 subgrupos |
| Auditoría | `auditoria_dato` | **0** | Código listo, uso cero |

### 4.2 Completitud del contrato, tras la precarga de SECOP

| Campo | Tiene |
|---|---|
| valor | **25 / 25** |
| objeto | **25 / 25** |
| fechas | 24 / 25 |
| contratista | 23 / 25 |
| CDP | 4 / 25 |
| ejecución | 4 / 25 |
| **etapa contractual** | **0 / 25** |
| **forma de pago** | **0 / 25** |

### 4.3 Lo externo pesa cien veces más que lo propio

| Espejo | Filas | Frescura |
|---|---|---|
| `secop_contrato` | **3.074** | Hoy 03:31 (2024: 1.135 · 2025: 1.184 · **2026: 755**) |
| `secop_plan_pago` | **36.232** | Hoy 03:32 · 5.047 contratos · $503.991 M |
| `sdp_meta_oficial` | **280** | **2026-07-23** — un mes sin cambiar |

**El contraste que define la fase:** el sistema tiene 25 contratos internos y
**ninguno de 2026**, mientras SECOP publica 755 contratos de Kennedy de esta
vigencia. Y `contrato_plan_pago` tiene 0 filas frente a 36.232 del espejo.

### 4.4 Ejemplos de la cadena completa

| Proyecto | Metas | Actividades | Contratos | Valor |
|---|---|---|---|---|
| 2780 · Kennedy Proyecta Talento + 2788 · Impulso Creativo (Cultura) | — | — | 15 | $713.221.534 |
| Educación (subgrupo 8) | — | — | 1 | $23.168.769.452 |
| Infraestructura (subgrupo 37) | — | — | 4 | $9.165.473.810 |
| Seguridad (subgrupo 38) | — | — | 4 | $6.944.742.446 — **invisible en su panel** (§3.4) |

> **Un detalle que muerde a quien cuente personas.** El documento de identidad
> vive en **dos caminos casi disjuntos**: 1.886 personas lo tienen solo en
> `persona.documento`, 4.558 solo por la FK `persona_documento`, **1 en ambos**
> y 675 en ninguno. Donde coexisten, coinciden (cero discrepancias). Contar por
> una sola vía pierde entre el 26 % y el 64 % de las personas identificadas.

**38 de los 46 subgrupos no tienen ni un proyecto.** Los 12 proyectos se
reparten entre 8 subgrupos, y solo 4 tienen contratos.

---

## 5 · Información faltante

Ordenada por lo que bloquea el ciclo objetivo.

### 5.1 Falta el dato, la estructura existe

- **Etapa contractual**: catálogo de 5, endpoint escrito, stepper en pantalla,
  **0 de 25 contratos con etapa**. Sin esto, «ejecución» y «liquidación» del
  ciclo no tienen respaldo.
- **CRP / compromiso**: tabla con 48 columnas y 15 FKs, **0 filas**.
- **CDP real**: 1 de 5.
- **Plan de pago interno**: 0 filas, pantalla y endpoint completos.
- **Auditoría**: 0 filas, con 8 llamadas a `registrar_cambio` en producción.
- **13 metas sin código SEGPLAN**: no se pueden comparar contra el Plan.
- **16 proyectos oficiales sin proyecto interno**.

### 5.2 Falta la estructura entera

- **PAA / Plan Anual de Adquisiciones**: cero tablas, cero columnas, cero
  código, cero menciones en `apps/`, `frontend/`, `docs/` y `brain/`.
- **Apropiación**: lo más cercano es `proyecto_inversion`, con 3 filas de prueba.
- **Reserva presupuestal**: **no existe.** La tabla `reservas` es de salones
  (`FOREIGN KEY (sala_id) REFERENCES salas(id)`).
- **Vigencia como dimensión**: el catálogo existe y ninguna pieza viva del
  ciclo cuelga de él.
- **Corte trimestral**: ninguna tabla del esquema tiene columna de trimestre.
  Lo más cercano es `presu_avance_ind_periodo.periodo`, texto **mensual**, con
  9 filas.
- **POAI**: 5 menciones en todo el repo, todas en
  `docs/propuestas/plan_trabajo_2026-07-29.md`, donde figura como *«pendiente de
  recibir el archivo»*.
- **Evento ↔ beneficiario**: no hay tabla.

### 5.3 Falta el permiso

`modulo` tiene 28 filas y solo tres tocan el ciclo: `presupuesto_proyectos`,
`presupuesto_metas`, `presupuesto_cdp`. **No hay módulo para PAA, CRP,
apropiaciones, POAI ni SEGPLAN.** Aunque mañana hubiera pantalla, no habría
permiso que la gobierne.

---

## 6 · Fuentes externas

### 6.1 Lo que entra solo

El cron **sí está instalado** (`crontab -l`, desde el 2026-08-07) y corre a
diario: 03:30 sincronización, 04:00 mantenimiento. Hoy las 11 fuentes
reportaron OK en 135 segundos.

| Dato | Fuente | Mecanismo | Frecuencia | Automatizable |
|---|---|---|---|---|
| Contratos adjudicados | SECOP II (datos.gov.co) | `ingest_secop_contratos` | Diaria ✅ | Ya lo está |
| Plan de pagos | SECOP II | `ingest_secop_plan_pagos` | Diaria ✅ | Ya lo está |
| Metas y actividades del Plan | SDP / SEGPLAN | `ingest_sdp_datos_abiertos` | Diaria ✅ | Ya lo está |
| Estratificación, sectores, barrios | IDECA | `sync_estratificacion`, `sync_capa` | Diaria ✅ | Ya lo está |
| Colegios y matrícula | SED | `sync_colegios` | Diaria ✅ | Ya lo está |
| CAI | SCJ | `sync_cai` | Diaria ✅ | Ya lo está |
| Malla vial | IDU | `resolver_geometria_tramos` | Bajo demanda | Sí |
| Placas domiciliarias | Catastro | `--incluir-pesadas` | Manual (1,77 M filas) | Parcial |

> **Ojo con el «OK».** El log dice `SDP-PDL (Planeación): OK` todos los días, y
> `sdp_meta_oficial.synced_at` sigue en **2026-07-23**. La ingesta es
> idempotente por `hash_fila`: si la fuente no cambió, no toca nada. **«OK»
> significa «corrió», no «hay dato nuevo».**

### 6.2 Lo que se carga a mano

| Dato | Mecanismo | Responsable | Automatizable |
|---|---|---|---|
| Beneficiarios de becas | Cargue de Excel → `stg_beneficiarios` | Área | Ya lo está, falta el paso de parseo (§8.4) |
| Etapa contractual, forma de pago | Pantalla del expediente | Coordinador del área | **No** — no hay fuente |
| CDP | `/app/presupuesto/cdps` | Área | **No** — SECOP no publica el CDP |
| Ejecución técnica | Pantalla | Área | No |
| Dotación, acceso/permanencia | Pantalla | Área | No |

### 6.3 Las dos fuentes nuevas: dónde aterrizarían

**(a) SEGPLAN trimestral.** Hoy `sdp_meta_oficial` guarda una foto **anual** por
meta. Su índice único es `uq_sdp_meta (vigencia, codigo_proyecto,
plan_meta_producto_id, actividad_codigo)` — **sin columna de período**. Dos
cargas del mismo año se pisarían.

Lo que sí tiene, y es lo valioso: `magnitud_programada`, `magnitud_comprometida`,
`magnitud_entregada`, `total_programado`, `total_comprometido`, `total_girado`,
`valor_programado`, `pct_entregado`, `avance_financiero` — **es el único sitio
de toda la base donde conviven programación y ejecución, física y presupuestal,
por proyecto/meta/actividad.** La forma del ciclo objetivo ya está ahí.

> **Pero la vigencia de esa tabla es artificial.** Las 70 filas se repiten
> **idénticas** en 2025, 2026, 2027 y 2028: mismas magnitudes, mismos totales,
> un solo `synced_at`. Son 280 filas que son 70 datos copiados cuatro veces.
> **Sumar por vigencia multiplica por cuatro.** No hay serie temporal — y eso
> es exactamente lo que la entrega trimestral vendría a dar.

**(b) POAI con avance físico.** Arranca de cero: sin tabla, sin columna, sin
comando de ingesta. Y llegaría a un terreno donde **el avance físico ya vive
repartido en cinco sitios con granos distintos**:

| Mecanismo | Grano | Filas |
|---|---|---|
| `presu_avance_ind_periodo` | mes / indicador | 9 |
| `tramo_vial_contrato.pct_avance` | tramo vial | 30 |
| `intervencion_parque.pct_avance` | parque | 14 |
| `corte_avance_obra` | corte de obra | 1 |
| `sdp_meta_oficial.magnitud_entregada` | vigencia / meta | 280 |

Ninguno se agrega con otro. **El POAI sería el sexto** si antes no se decide
cuál manda.

---

## 7 · Comparación con el ciclo objetivo

🟢 ya existe y sirve · 🟡 existe pero hay que adaptarlo · 🔴 no existe ·
⚠️ existe pero el modelo o la relación es problemático

| # | Pieza del ciclo | | Qué hay hoy | Qué falta |
|---|---|---|---|---|
| 1 | **Plan de Desarrollo** | 🟡 | Espejo `sdp_meta_oficial` (280) con 28 proyectos, 70 metas, objetivos y programas oficiales. Pantalla `/presupuesto/plan-oficial` | No hay tabla propia del Plan. El interno (`objetivo` 6, `programas` 7) no tiene trazabilidad al oficial y **3 de sus 7 programas son de prueba** |
| 2 | **Proyecto** | 🟡 | `proyecto`, 12 filas, 12/12 con subgrupo | **16 de los 28 proyectos oficiales no existen internamente.** El modelo no mapea `dependencia_id` |
| 3 | **Vigencia** | ⚠️ | Catálogo `vigencia` (8 filas, 2020-2027) sano y completo | **Ninguna pieza viva del ciclo cuelga de él.** `proyecto` no tiene la columna; `contrato_vigencia` es un entero suelto sin FK. Y el catálogo tiene **dos claves** (PK `codigo` + UNIQUE `id`) y la base usa las dos |
| 4 | **Meta** | 🟡 | `metas` 24 + `meta_proyecto` 24. 22 de 24 con indicador | **Solo 11 de 24 tienen código SEGPLAN.** `metas.proyecto_id` apunta a la tabla muerta y está NULL en las 24. El modelo mapea 3 de 19 columnas |
| 5 | **Programación física** | 🟡 | `presu_indicador_meta_proyecto.meta_magnitud` (23/23) | Es **un número único, sin año ni período**. No hay programación anualizada ni por trimestre |
| 6 | **Programación presupuestal** | 🔴 | `presupuesto_proyecto` y `presupuesto_tiempo` existen con las columnas correctas | **0 filas las dos**, sin pantalla, sin endpoint, y sus modelos ni siquiera se registran al arrancar |
| 7 | **PAA / apropiación** | 🔴 | Nada | **Todo.** Cero tablas, cero columnas, cero código, cero menciones. `proyecto_inversion` (3 filas de prueba) es lo más parecido y no es lo mismo |
| 8 | **CDP** | ⚠️ | Tabla, modelo, pantalla completa con alta y edición, endpoint | **5 filas y 4 son marcadores** sin número, fecha ni valor. Solo 4 de 25 contratos tienen CDP. Pantalla completa sobre una tabla casi vacía: parece que funciona |
| 9 | **CRP** | ⚠️ | Tabla con 48 columnas y 15 FKs, calcada de BogData. Modelo con 5 columnas | **0 filas — y `metrics.py` la suma igual** y publica $0 comprometido. Sin pantalla, sin endpoint, sin ingesta |
| 10 | **Contrato** | 🟢 | 25 internos + 3.074 del espejo SECOP. Cuatro vías al proyecto, todas coherentes. Expediente, completitud, etapa, plan de pago | **Ninguno de 2026.** La etapa está en 0/25 |
| 11 | **Compromiso** | 🔴 | `compromiso` es un catálogo `(id, nombre, descripcion)` con 0 filas | No existe el compromiso como hecho. Lo que hoy se rotula «comprometido» es `contrato.valor` — ver §8.3 |
| 12 | **Ejecución presupuestal** | 🟡 | `secop_plan_pago` (36.232 filas, $503.991 M) da el girado real por contrato | Interno: `contrato_plan_pago` 0 filas. El girado se deriva del espejo, no se registra |
| 13 | **Ejecución física** | ⚠️ | `presu_avance_ind_periodo` (9) + 4 mecanismos más | **Cinco granos distintos que no se agregan entre sí** (§6.3b). Solo 6 de 23 indicadores tienen avance |
| 14 | **Seguimiento de metas** | 🟡 | La cadena meta → indicador → actividad → evento existe y funciona | **Tres cuartas partes de los indicadores nunca recibieron un avance.** Un «% de cumplimiento» agregado hoy sería engañoso |
| 15 | **Avance del proyecto** | 🟡 | Vista 360° `/presupuesto/proyectos/:id` | Se calcula sobre 6 indicadores con dato |
| 16 | **Cumplimiento del PDL** | ⚠️ | `sdp_meta_oficial` trae `pct_entregado` y `avance_financiero` oficiales | **Solo 5 de 12 proyectos llegan a un programa**, y el enganche meta↔SEGPLAN cubre 11 de 24. El extremo alto del ciclo está desconectado |
| 17 | **Beneficiarios** | ⚠️ | 5.598 beneficiarios, 2.950 vínculos a contrato, 2.545 participantes | `contrato_beneficiario` **no tiene modelo Django** y se opera por SQL crudo. **La cadena nunca los alcanza desde el plan** (§1.3c) |
| 18 | **Indicadores** | 🟢 | 23 activos con magnitud, unidad y tipo de agregación | Conviven con una generación anterior de 6 filas que nadie lee (§8.2) |
| 19 | **Impactos** | 🔴 | `presu_impacto_actividad_indicador`, 3 filas | Sin modelo, sin endpoint, sin pantalla. Existe como tres filas huérfanas |
| 20 | **Fuentes externas** | 🟢 | 11 fuentes, cron instalado y corriendo a diario, licencias declaradas | SDP lleva un mes sin cambiar y el log igual dice OK |

**Resultado: de las 20 piezas, 3 están completas (🟢), 8 requieren adaptación
(🟡), 5 son problemáticas (⚠️) y 4 no existen (🔴).**

---

## 8 · Duplicidades potenciales

### 8.1 Tablas gemelas — una viva y una muerta

| Par | Viva | Muerta | Qué se perdió al morir la segunda |
|---|---|---|---|
| `proyecto` / `proyectos` | **12 filas** | **0 filas, sin modelo** | La muerta es la que tenía **`vigencia`** y `codigo_meta`. Y `metas.proyecto_id` **apunta a la muerta** → NULL en las 24 filas |
| `area` / `areas` | ninguna: el área real es `subgrupo` (46) | `areas` 0 · `area` 10 filas cuya única FK entrante viene de `proyecto_inversion` (3 filas de prueba) | El catálogo `area` está muerto. `muro_subgrupos.py:53-67` resuelve el área **por nombre del subgrupo**, no por FK |
| `presu_indicador_meta_proyecto` / `presu_indicador` | **23 filas** | **3 filas, sin modelo** | La vieja tenía `linea_base`, `formula`, `verificado`, `evidencia_url` — campos que la viva **no tiene**. Y sus 3 filas son **indicadores reales**: «becas» (meta 170), «Porcentaje de» (1.000 personas) y «cantidad mujeres» (1.000), de los proyectos 2377, 2711 y uno de prueba. **El sistema no los ve** |
| `presu_avance_ind_periodo` / `presu_avance_indicador` | **9 filas** | **0 filas, sin modelo** | — |
| `contrato_actividad_plan` / `contrato_actividad` | 15 filas, la lee el código | 18 filas, **ningún servicio la lee** | La «vieja» tiene **más filas** (18/16 contratos) que la «nueva» (15/5 contratos) |
| `metas` / `sdp_meta_oficial.plan_meta_producto_id` | 24 internas | 70 oficiales | Dos niveles del mismo concepto, unidos por texto en 11 casos |
| `presupuesto_proyecto` / `proyecto_inversion` | ninguna: las dos vacías o de prueba | — | Dos diseños de apropiación, ninguno usado |

### 8.2 Nombres que mienten

| Nombre | Sugiere | Es |
|---|---|---|
| `reservas` | Reserva presupuestal | **Reservas de salón** (`FOREIGN KEY (sala_id) REFERENCES salas(id)`). La reserva presupuestal no tiene tabla |
| `tipo_contrato` | Catálogo de `contrato.contrato_tipo` (CPS, CIA…) | Tipo de **vinculación de una persona**: *Prestación de servicios, Planta, Nombramiento provisional, Contratista externo, Otro*. `contrato_tipo` es texto libre **sin catálogo** |
| `compromiso` | El compromiso presupuestal | Un **catálogo** `(id, nombre, descripcion)`. El hecho vendría de `crp.no_compromiso` |
| `validacion_documental` | Validación del expediente contractual | Validar papeles de un **participante** del Banco de Iniciativas |
| `persona.usuario_id` | Qué usuario es esa persona | **Quién la registró** (autoría). Un solo usuario tiene 131 personas colgando |
| `actividad` | La actividad del plan | Catálogo plano de 74 nombres. La del plan es `actividad_plan` |
| `area` | El área ejecutora | Catálogo muerto de 10 filas. El área real es `subgrupo` |
| `indicador_id` | La misma columna en las dos puentes | **Apunta a tablas distintas**: `actividad_indicador.indicador_id → presu_indicador_meta_proyecto`, pero `presu_impacto_actividad_indicador.indicador_id → presu_indicador`. Dos universos de ids que no se cruzan |
| `vigencia` (la columna) | Un año | **Depende de a cuál de las dos llaves apunte.** `vigencia` tiene PK `codigo` (2020…2027) **y** una columna `id` identity (1…8). `programas.vigencia_id → vigencia.id`; `proyectos.vigencia → vigencia.codigo`. «vigencia = 6» significa 2025 si es el id, y nada si es el código |
| `persona.acceso_salud_codigo` | Apunta a `acceso_salud` | Apunta a **`calidad_acceso_salud`**. Y `acceso_servicios_salud_id` apunta a `acceso_salud`: los nombres están cruzados. Hoy no muerde porque las dos están vacías |

### 8.3 Hipótesis — equivalencias que NO se dan por ciertas

> Estas quedan escritas como preguntas abiertas, con su evidencia. **Ninguna se
> resuelve en este diagnóstico.**

**H1 · ¿`Contrato` = `Compromiso`?** *Probablemente no, pero el código actúa
como si sí.*
A favor: `metrics.py:15` comenta literalmente *«Crp, # compromisos por
proyecto»*, y el muro y el expediente rotulan «comprometido» a `contrato.valor`.
En contra: `compromiso` es un catálogo de 3 columnas con 0 filas, y `crp` tiene
columnas propias `no_compromiso` y `compromiso_id`. Es decir, `compromiso`
parece ser un **tipo** de compromiso, no el compromiso. No se puede confirmar:
la tabla está vacía y ningún código la usa.

**H2 · ¿`contrato_actividad` es la versión vieja de `contrato_actividad_plan`?**
A favor: la segunda tiene monto, fechas, `meta_proyecto_id` y `concepto_gasto_id`;
la primera es solo `(contrato_id, actividad_id)`. En contra de darlo por
resuelto: **la «vieja» tiene más uso** — 18 filas sobre 16 contratos, contra 15
filas sobre 5 contratos. Migrarla o retirarla exige DML con aprobación.

**H3 · ¿`metas` (24 internas) y `plan_meta_producto_id` (70 oficiales) son lo
mismo en dos niveles?**
A favor: existe un comando dedicado, `sdp_mapear_codigo_meta.py`, que puebla
`metas.codigo_meta`. En contra: **el mapeo es por similitud de nombre, no por
identidad**, y 13 de 24 siguen sin código. Nadie ha verificado la tasa de
acierto de esos 11.

**H4 · ¿`presupuesto_tiempo` era la «programación física y presupuestal»?**
A favor: 0 filas pero con modelo, FKs a proyecto + actividad_plan + fase_proyecto
(que sí tiene sus 3 filas), `avance_pct`, y la lee `metrics.py:245`. **Es la
única estructura del esquema que ata proyecto, actividad y fase en el tiempo.**
En contra: ni documentación ni datos que lo confirmen.

**H5 · ¿La actividad oficial de SDP es una TERCERA clase de actividad?**
`sdp_meta_oficial.actividad_codigo` trae 70 valores distintos, sin tabla propia
ni FK hacia `actividad` (74) ni hacia `actividad_plan` (54). Nada en el código
las cruza. Si son tres universos separados, el glosario —que ya documenta tres
sentidos de «actividad»— se queda corto.

### 8.4 Un dato cargado que nadie puede usar

`stg_beneficiarios` tiene **5.985 filas** con proyecto, meta, actividad, tipo de
proceso, espacio y contrato. La vista `vw_stg_contrato_proyecto` existe para
unirlo con `contrato`… y **devuelve 0 filas**.

La causa, medida: las columnas `contrato_tipo`, `contrato_numero` y
`contrato_vigencia` de la staging están **NULL en las 5.985 filas**. El dato
crudo está en la columna `No. de Contrato`; **el paso que lo parsea nunca corrió.**
(En la tabla son `NULL`; la vista las convierte a cadena vacía con `COALESCE`,
así que el JOIN compara vacío contra `CPS`.)

**Y hay un segundo JOIN vacío del mismo tipo.** La vista `programa_cdp` —de la
que sale el «asignado por programa» del tablero— devuelve 0 filas porque el
único `proyecto_inversion_item` con CDP cuelga del proyecto 2807, que tiene
`programa_id` en NULL. El KPI dice $0 para todos los programas por una columna
vacía en una fila, no porque no haya CDPs.

---

## 9 · Riesgos

| | Riesgo | Evidencia | Por qué importa |
|---|---|---|---|
| 🔴 | **Cifras que hoy se publican como $0 sin serlo** | `metrics.py:74,148,201,237` suma `crp` (0 filas) con `Coalesce(...,0)`; la vista `programa_cdp` da 0 | Un tablero que dice «$0 comprometido» ante un ente de control no está diciendo «no hay»: está diciendo «no medimos». Y no se distingue |
| 🔴 | **Un área ve $6.944 millones de menos en su propio panel** | `panel_area.py:144-146` no usa la unión de vías; Seguridad tiene 0 por una vía y 4 contratos por la otra | Defecto vivo, no de diseño. Se corrige con la misma unión que ya usan los otros cuatro servicios |
| 🔴 | **Sumar `sdp_meta_oficial` por vigencia multiplica por cuatro** | Las 70 filas son idénticas en 2025-2028; totales iguales en las cuatro | Cualquier reporte que agrupe por vigencia sobre ese espejo da una cifra cuatro veces mayor que la real |
| 🟠 | **Datos de prueba mezclados con institucionales** | `proyecto_inversion`: «prueba», «proyectpo invercion», «prueba 2 proyecto inver» ($12.000.000). `concepto_gasto`: «prueba concepto». 3 de 7 `programas` | Cualquier tablero que sume presupuesto de ahí suma basura. Hay que separarlos antes de construir encima |
| 🟠 | **`contrato_actividad_plan` no tiene ni una sola FK real** | `pg_constraint` no devuelve ninguna `contype='f'` para esa tabla; Django declara 4 | La integridad del puente central del dinero la sostiene solo el ORM. Un `DELETE` por SQL deja huérfanos sin aviso |
| 🟠 | **`evento` declara 3 FKs que la base no tiene** | `dependencia_id`, `funcionario_id`, `subgrupo_id` sin constraint en `pg_constraint` | Lo mismo, al revés: el modelo promete una garantía que la base no da |
| 🟠 | **La reserva presupuestal no existe** | `reservas` es de salones | Es un paso obligatorio al cierre de vigencia. Quien la busque por el nombre diagnosticará mal |
| 🟠 | **El 40 % de las tablas está vacío y no se distingue lo pendiente de lo muerto** | 108 de 268 | Sin esa distinción, cada sesión nueva vuelve a investigar si `rubro` es un pendiente o un fósil |
| 🟡 | **Seis pares de FK duplicadas, una con `ON DELETE` contradictorio** | `cdp.proyecto_id` tiene `SET NULL` en una y `NO ACTION` en la otra | El comportamiento real depende de cuál evalúe Postgres primero |
| 🟡 | **Una FK `NOT VALID`** | `contrato_forma_pago_fk` | Valida las filas nuevas, nunca comprobó las 25 existentes |
| 🟡 | **Sin triggers: los saldos no se mantienen solos** | Un único trigger en todo el esquema, y es de votaciones | `presupuesto_proyecto.monto_asignado/comprometido/obligado/pagado` no los actualiza nada |
| 🟠 | **Un JOIN «obvio» entre las dos familias de indicadores devuelve datos falsos** | `indicador_id` apunta a `presu_indicador_meta_proyecto` en una puente y a `presu_indicador` en la otra | No da error: da filas equivocadas. Y hay 3 indicadores reales en la tabla que el sistema no lee |
| 🟠 | **La secuencia de `contrato.id` y el `MAX(id)+1` van por caminos distintos** | `contrato_id_seq` en 386, `MAX(id)` en 105 | Mientras el código inserte ids explícitos, la secuencia no avanza. El día que un INSERT sin id tome 387 y otro vuelva al MAX+1, chocan |
| 🟡 | **38 catálogos con filas y cero referencias reales** | Medido recorriendo todas las FKs y contando columnas referenciantes no nulas | No todos sobran: `etapa_contrato` y `forma_pago` están en cero **a propósito**. Pero sin distinguirlos, no se sabe cuál es fósil y cuál es pendiente |
| 🟡 | **Habeas data** | `docs/arquitectura/DEUDA_TECNICA.md` P1 · repo público | `stg_beneficiarios` tiene nombres, cédulas y direcciones. Ninguna consulta de este diagnóstico las reprodujo, y ninguna futura debe hacerlo |

---

## 10 · GAP funcional y técnico

### 10.1 GAP funcional — las tres capas

Para cada pieza: ¿hay pantalla, hay API, hay dato?

| Pieza | Pantalla | API | Dato | Capa que falta |
|---|---|---|---|---|
| Proyectos | ✅ | ✅ | ✅ 12 | — (falta contenido: 16 oficiales) |
| Metas | ✅ | ✅ | ✅ 24 | — (falta el código oficial en 13) |
| Indicadores | ✅ | ✅ | ✅ 23 | — |
| Contratos | ✅ | ✅ | ✅ 25 | — (falta la vigencia 2026) |
| Vigencias | ❌ | ✅ | ✅ 8 | **Pantalla** |
| CDP | ✅ | ✅ | ⚠️ 1 real | **Dato** |
| CRP | ❌ | ❌ | ❌ 0 | **Pantalla, API y dato** |
| Compromisos | ❌ | ❌ | ❌ 0 | **Las tres** |
| PAA | ❌ | ❌ | ❌ | **Las tres, y la tabla** |
| Apropiaciones | ❌ | ❌ | ⚠️ prueba | **Pantalla, API y dato real** |
| Programación presupuestal | ❌ | ❌ | ❌ 0 | **Pantalla y API** (tabla y modelo existen) |
| Impactos | ❌ | ❌ | ⚠️ 3 | **Pantalla, API y modelo** |

**Patrón:** lo que tiene pantalla funciona; lo que falta, falta entero. Y hay un
caso peor que faltar — **CDP tiene pantalla completa sobre una tabla casi
vacía**, así que parece resuelto.

### 10.2 GAP técnico

1. **La vigencia no es una dimensión del modelo.** Es el gap estructural más
   grande: el ciclo objetivo exige `Proyecto → Vigencia → Meta` y hoy ninguna de
   esas tres tablas tiene la columna.
2. **No hay dimensión de período/corte** en ninguna parte. La entrega trimestral
   no tiene dónde aterrizar sin pisar la carga anterior.
3. **Programación y ejecución no están separadas** salvo en el espejo de SEGPLAN.
   Internamente solo se guarda un objetivo (`meta_magnitud`) y unos aportes.
4. **El avance físico tiene cinco implementaciones** que no se agregan.
5. **Cinco modelos del ciclo presupuestal no se registran al arrancar.**
6. **Los espejos no tienen FK a lo interno**: se unen por texto. Funciona (22 de
   25 contratos, 11 de 24 metas) pero es frágil y hay 8 referencias de SECOP que
   el regex no parsea.
7. **El catálogo de módulos RBAC no cubre el ciclo nuevo.**

---

## 11 · Qué podemos reutilizar

Esto es lo que **no hay que volver a construir**:

| | Por qué sirve |
|---|---|
| **`sdp_meta_oficial`** | Es el ciclo objetivo hecho tabla: programación y ejecución, física y presupuestal, por proyecto/meta/actividad. Ya ingerido y con cron |
| **`secop_contrato` + `secop_plan_pago`** | 3.074 contratos y 36.232 pagos, frescos hoy. La contratación y el girado reales ya están en la base |
| **La conciliación por (número, año)** | `_REF_SECOP_RX` empata 22 de 25. Probada, documentada y con su historia de por qué no se hace de otra forma |
| **La cadena meta → indicador → actividad → evento** | Existe, funciona y está bien modelada. Le faltan datos, no diseño |
| **El catálogo `vigencia`** | 2020-2027 con fechas. Sano y sin usar: está esperando |
| **`etapa_contrato` + su endpoint + el stepper** | Las tres capas construidas y probadas. Solo falta que alguien registre etapas |
| **`auditoria_dato` + `registrar_cambio`** | Auditoría diseñada antes que el formulario, con 8 llamadas en producción |
| **`presupuesto_tiempo` y `presupuesto_proyecto`** | Las columnas de la programación presupuestal ya están pensadas (H4) |
| **El scope por subgrupo y los gates de rol** | `subgrupos_visibles` + `puede_crear_en_area`, con el patrón de tres gates ya probado |
| **El cron y el orquestador de fuentes** | 11 fuentes, licencias declaradas, seco por defecto, corriendo a diario |
| **La estructura de espejo (`managed=False`, `hash_fila`, `synced_at`)** | El molde para cualquier fuente nueva, incluido el POAI |

---

## 12 · Qué debemos adaptar

| | Qué | Por qué |
|---|---|---|
| 1 | **`panel_area` a la unión de vías** | Defecto vivo: $6.944 M invisibles para Seguridad |
| 2 | **`metas.proyecto_id`** | Su FK apunta a la tabla muerta. O se reapunta o se retira la columna |
| 3 | **El modelo `MetaBD`** | Mapea 3 de 19 columnas y esconde `codigo_meta`, que es el enganche con SEGPLAN |
| 4 | **El modelo `Crp`** | 5 de 48 columnas. Si va a entrar BogData, el mapeo tiene que existir |
| 5 | **`sdp_meta_oficial`** | Su clave única no contempla período: sin eso, la entrega trimestral pisa la anterior |
| 6 | **El comentario de la deuda S5** | Es falso: `contrato.id` sí tiene identity. Mientras siga escrito, cada INSERT nuevo copiará un `MAX(id)+1` innecesario |
| 7 | **Los `__init__.py` de modelos** | Cinco piezas del ciclo presupuestal no se registran al arrancar |
| 8 | **El parseo de `stg_beneficiarios`** | Tres columnas en NULL dejan 5.985 filas inservibles |
| 9 | **El catálogo `modulo`** | No hay permiso para las piezas nuevas |
| 10 | **Los datos de prueba** | Separar o retirar lo que dice «prueba» antes de construir tableros encima |

---

## 13 · Qué realmente habría que crear

Solo lo que no existe de ninguna forma. **Esta lista NO es un diseño**: es el
inventario de lo que quedaría en cero después de reutilizar y adaptar.

| | Pieza | Nota |
|---|---|---|
| 1 | **La dimensión VIGENCIA en la cadena** | Decidir si es columna, si es fila, o si el proyecto es plurianual y la vigencia cuelga de la meta. **Es la decisión de fondo del rediseño** |
| 2 | **La dimensión PERÍODO / CORTE** | Para el trimestre de SEGPLAN y para cualquier serie |
| 3 | **PAA / Plan Anual de Adquisiciones** | Cero absoluto |
| 4 | **Apropiación real** | `proyecto_inversion` solo tiene pruebas |
| 5 | **Reserva presupuestal** | El nombre está ocupado por otra cosa |
| 6 | **Programación física anualizada** | Hoy `meta_magnitud` es un número sin año |
| 7 | **Espejo del POAI** | Con el molde de los otros espejos |
| 8 | **La ingesta trimestral de SEGPLAN** | Y la decisión de qué hacer con los cortes anteriores |
| 9 | **El puente evento ↔ beneficiario** | Para que la cadena llegue a la persona |
| 10 | **Modelo Django de `contrato_beneficiario`** | 2.950 filas operadas por SQL crudo |
| 11 | **Un solo lugar para el avance físico** | O una regla explícita de precedencia entre los cinco |
| 12 | **Módulos RBAC de las piezas nuevas** | Sin ellos no hay forma de gobernar las pantallas |

---

## Resumen ejecutivo — las decisiones que hay que tomar

1. **La mitad presupuestal del ciclo existe como esquema y está vacía.** 19
   tablas en cero. ¿Se llenan con BogData, se llenan a mano, o se retiran?
2. **Decidir si `crp` es el camino.** Tiene 48 columnas calcadas de BogData y
   cero filas. O llega la integración, o esa tabla es un fósil que confunde.
3. **Mientras tanto, `metrics.py` publica $0 comprometido leyendo tablas
   vacías.** Hay que decidir si eso se apaga, se marca como «sin medir» o se
   recalcula desde `contrato.valor`. Hoy miente en silencio.
4. **La vigencia es la decisión de fondo.** No existe en `proyecto`, `meta_proyecto`
   ni `actividad_plan`. ¿Columna, tabla, o meta anualizada? Todo lo demás
   depende de esta respuesta.
5. **Decidir el grano del período.** SEGPLAN entregará trimestral;
   `presu_avance_ind_periodo` es mensual en texto libre; `periodo_fiscal` está
   diseñada mensual y vacía. Hay que elegir uno y que los demás se deriven.
6. **`sdp_meta_oficial` es el ciclo objetivo hecho tabla — pero su vigencia es
   una copia.** 70 filas repetidas cuatro veces. Decidir si la entrega trimestral
   la convierte en serie real o si se crea una tabla de cortes aparte.
7. **16 de los 28 proyectos oficiales no existen internamente.** ¿Se crean todos,
   se crean bajo demanda, o el proyecto interno se deriva del oficial?
8. **13 de 24 metas no tienen código SEGPLAN**, y las 11 que lo tienen se
   mapearon **por similitud de nombre**. Hay que validar ese mapeo antes de
   construir reportes sobre él.
9. **Decidir qué manda para el avance físico**: hoy hay cinco mecanismos con
   granos distintos y el POAI sería el sexto.
10. **La cadena nunca llega a la persona.** 23 eventos con actividad y cero
    participantes; 28 eventos con participantes y cero actividad. Decidir si se
    cierra por evento, por contrato, o por los dos.
11. **`contrato_beneficiario` son 2.950 filas sin modelo Django**, operadas por
    SQL crudo. Es el puente más grande del expediente.
12. **Resolver H1: ¿Contrato = Compromiso?** El código actúa como si sí y la
    base sugiere que no. Afecta a cómo se calcula todo el comprometido.
13. **Resolver H2: `contrato_actividad` (18 filas, 0 lectores) vs
    `contrato_actividad_plan` (15 filas).** Migrar, leer ambas o retirar. Exige DML.
14. **Ningún contrato interno es de 2026**, mientras SECOP publica 755 de esta
    vigencia. Decidir si los contratos internos se crean desde el espejo, a
    mano, o ambas — es la pregunta que dejó abierta el spec 003.
15. **La etapa contractual está en 0 de 25** con todas sus capas construidas.
    Es dato, no código: decidir quién la registra y cuándo.
16. **Separar los datos de prueba de los institucionales** antes de construir
    tableros encima (`proyecto_inversion`, `concepto_gasto`, 3 de 7 `programas`).
17. **Arreglar `panel_area`**: es un defecto vivo con $6.944 M invisibles, y se
    corrige con la unión que ya usan los otros cuatro servicios.
18. **Distinguir, tabla por tabla, lo pendiente de lo muerto.** 108 tablas
    vacías sin esa marca hacen que cada sesión vuelva a investigar lo mismo.
19. **Ampliar el catálogo de módulos RBAC** antes de las pantallas nuevas, o
    nacerán sin gobierno.
20. **Actualizar los seis documentos que hoy dicen algo falso** (§1.4), empezando
    por la deuda S5 y por el cron que sí está instalado. Un documento con fichas
    falsas hace que se desconfíe de todas.

---

## Anexo · Qué NO se hizo en este diagnóstico

- **No se implementó nada.** Sin código nuevo, sin DDL, sin migraciones, sin
  cambios de modelo.
- **No se escribió en la base.** Todas las consultas fueron `SELECT`. La única
  excepción fue un `INSERT` de prueba **dentro de una transacción revertida**,
  para comprobar que `contrato.id` recibe su valor de la identity: dejó 25 filas
  y cero basura.
- **No se resolvieron las hipótesis de §8.3.** Están planteadas con su
  evidencia, para decidirlas con Alex.
- **No se reprodujo ningún dato personal.** El repositorio es público.
