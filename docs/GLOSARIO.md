# Glosario de dominio — innovaK

Vocabulario del sistema para quien llega nuevo. Mezcla términos de gobierno
(Alcaldía de Bogotá / SIPSE) con conceptos propios de innovaK. Ordenado por
temas, no alfabético, para que se lea como una explicación.

---

## Cadena de gestión (el corazón del sistema)

Todo dato capturado se engancha a esta cadena. De arriba (planeación) hacia
abajo (ejecución en territorio):

- **SIPSE** — Sistema oficial de Información y Seguimiento a Proyectos y
  Estrategias de la Alcaldía de Bogotá. Marco al que innovaK se alinea.
  Ver [`referencia/SIPSE.md`](referencia/SIPSE.md).
- **Proyecto** — proyecto de inversión local (tiene código, subgrupo,
  vigencia). Ej.: *2784 – Kennedy fuerza local*.
- **Meta** — meta general del cuatrienio (catálogo `metas`). Es el enunciado
  "grande" (ej.: *capacitar 4000 personas*).
- **MetaProyecto** — asociación de una Meta a un Proyecto concreto (tabla
  `meta_proyecto`).
- **Indicador / KPI** — indicador medible de una MetaProyecto (tabla
  `presu_indicador_meta_proyecto`). Lleva unidad de medida, magnitud objetivo
  y tipo de agregación (SUMA/ÚLTIMO/PROMEDIO/MAX). Es el **aporte de la
  vigencia**, distinto del número general de la Meta.
- **ActividadPlan** — actividad del plan de acción (SIPSE) que ejecuta un KPI
  (tabla `actividad_plan`).
- **Formulación** — lo que el área prepara ANTES de que exista el contrato:
  necesidad, objeto, estudios previos, presupuesto estimado, modalidad,
  requisitos y revisiones. Una Meta tiene varias. **No es una etapa del
  contrato**: es un dominio propio que vive entre la Meta y la contratación
  (decisión del 2026-08-27, `specs/004-formulacion/plan.md`). Termina —o no—
  en un contrato, y la relación se conserva en los dos sentidos.
- **Evento** — la unidad de ejecución en territorio (un curso, una entrega,
  una caracterización, un festival…). Al validarse, **suma avance al KPI**.
  En innovaK `Evento` es el modelo **unificado** (antes había apps separadas
  como `kactivo`; se fusionaron aquí).

> **⚠️ "Actividad" nombra TRES cosas distintas.** Es la ambigüedad más cara del
> proyecto; tenerla clara evita leer la tabla equivocada:
>
> | En la UI / código | Tabla | Qué es |
> |---|---|---|
> | **Evento** (la UI lo llama "actividad") | `evento` | lo que se ejecuta en territorio |
> | **ActividadPlan** | `actividad_plan` | la línea del plan/SIPSE que aporta al KPI |
> | **Actividad** (catálogo, ~74 filas) | `actividad` | catálogo de tipos de actividad SIPSE |
>
> Y hay **dos puentes contrato↔actividad, vivas y distintas**:
>
> | Puente | Tabla | Apunta a | ¿Llega a Proyecto→Meta→KPI? |
> |---|---|---|---|
> | **ContratoActividadPlan** ✅ | `contrato_actividad_plan` | ActividadPlan (plan) | **Sí** — es la de la cadena |
> | **ContratoActividad** | `contrato_actividad` | Actividad (catálogo) | **No** — no alcanza el plan |
>
> El **panel de área lee solo la del plan** (`ContratoActividadPlan`), por eso
> reporta "20 de 24 contratos sueltos": ignora las vinculaciones de
> `contrato_actividad`. Esas filas legacy son una **decisión pendiente** (migrar,
> leer ambas, o retirar el catálogo) — requiere DML con OK de Alex.
> `VincularContratoActividadPlanView` escribe en la puente del **plan**
> (el nombre viejo, sin "Plan", engañaba).
- **Beneficiario** — persona/organización atendida por un Evento.
- **AvanceIndicador** — cada avance registrado contra un KPI (tabla
  `presu_avance_ind_periodo`); su origen puede ser EVENTO, MANUAL o AJUSTE.

> **Regla de oro (memoria del proyecto):** cuando entra un proyecto nuevo,
> antes de diseñar schema hay que verificar que cada pieza se conecte hacia
> arriba en la cadena. No se inventan columnas sueltas: todo se liga para
> poder derivar las **matrices de reporte** (presupuestal + ejecución
> contractual).

---

## Lado financiero

- **CDP** — Certificado de Disponibilidad Presupuestal. Reserva dinero de un
  proyecto. Tiene saldo disponible.
- **Contrato** — contrato que compromete dinero de un CDP (`contrato.valor <=
  cdp.saldo_disponible`). Puede tener convenio asociado.
- **ContratoActividadPlan** — vincula un Contrato a una ActividadPlan con un
  monto (`Σ vinculaciones <= contrato.valor`). Cierra la cadena dinero →
  ejecución.
- **CRP** — Certificado de Registro Presupuestal (registro del compromiso; se
  menciona en el marco SIPSE). ⚠️ La tabla `crp` existe con 48 columnas y
  **0 filas**, y `metrics.py` la suma igual: por eso el «comprometido» de esas
  pantallas sale en $0. No es que no haya compromisos: es que no se miden.
- **Saldo presupuestal** — Σ CDPs − Σ comprometido (tile de la vista 360° del
  proyecto).

---

## Organización y personas

- **Dependencia** — unidad organizativa de primer nivel (ej.: *Inversión
  Local*).
- **Subgrupo** — subdivisión de una dependencia; es el **eje de trabajo y de
  permisos** (ej.: *Deporte*, *Educación*, *Cultura*). Casi todo se ordena y
  se filtra por subgrupo.
- **Funcionario** — persona vinculada laboralmente a un subgrupo; puede ser
  responsable de eventos o docente de cursos.
- **Persona** — registro de una persona natural (modelo central `Persona` +
  ~26 catálogos). Una misma Persona puede ser participante, beneficiario,
  contratista o funcionario.
- **Participante / ParticipanteEvento** — inscripción de una Persona a un
  Evento (cupo y lista de espera).

---

## Roles y permisos (RBAC dinámico)

- **Módulo** — unidad de permiso (ej.: `eventos`, `banco_iniciativas`,
  `presupuesto_proyectos`, `roles`). El acceso se calcula por módulo, no por
  nombre de grupo. Catálogo sembrado por el command `seed_modulos`.
- **Rol** — grupo de Django con un conjunto de módulos asignados (tablas
  `modulo`, `rol_modulo`, `rol_meta`). Editable desde la UI (`/app/org/roles`).
  Caché de permisos en Redis, invalidada con un `INCR` de versión.
- **Prefijo `Coordinador` = poder de creación.** Cualquier grupo cuyo nombre
  **empiece por `Coordinador`** (Coordinador, CoordinadorDeportes…) obtiene
  poder de **creación** de actividades/eventos en su área. ⚠️ **Nunca** nombres
  así a un rol de solo lectura — entraría a los flujos de creación sin querer.
- **Admin** — rol protegido (bypass `is_superuser`); no se puede desactivar ni
  quedar sin módulo `roles` ni sin último usuario.

---

## Captura de datos

- **Tipo de evento (`tipo_evento`)** — clasifica un Evento y decide su flujo de
  captura (ej.: `CURSO`, `ENTREGA`, `BANCO_INICIATIVAS`, `CARACTERIZACION`,
  `JOVENES_BECA`, `CULTURA_ORG`). Data-driven por flags
  (`permite_inscripcion`, `permite_caracterizacion`, `requiere_actividad_plan`).
- **Captura genérica (`captura_generica`)** — motor de captura manejado por
  `tipo_evento` con datos en JSONB. Agregar una captura nueva = una entrada en
  un diccionario de schema, sin DDL ni componente nuevo.
- **Caracterización** — encuestas poblacionales por sector (6 wizards: Cultura,
  Deporte, Mujer, Salud, Poblacional, Participación Ciudadana, + Seguridad en
  curso). Datos sensibles → firma cifrada en MongoDB.
- **QR público** — cada evento de captura genera un QR que apunta a un
  formulario Angular público (`/app/p/*`, sin login) que el ciudadano llena
  desde el celular. Protegido con token HMAC (`QR_TOKEN_ENFORCE`).
- **Firma / PII cifrada** — las firmas y documentos de identidad se cifran con
  `DOCUMENTOS_AES_KEY` y se guardan en MongoDB (`apps.documentos`), no en
  PostgreSQL.

---

## Territorio (georreferenciación)

- **Localidad / UPZ / UPL / Barrio** — jerarquía territorial de Bogotá.
  Kennedy es la localidad; se subdivide en UPZ y UPL (Unidades de Planeamiento
  Local, POT 2022), y estas en barrios.
- **LugarIncidencia** — punto geográfico donde ocurre un Evento. Si un evento
  se crea sin coordenadas, se ubica por defecto en la **Alcaldía**
  (LugarIncidencia 100055) para que igual aparezca en el mapa.
- **Escuela / Parque** — capas de puntos culturales/deportivos del territorio
  (no son colegios formales; para colegios ver deuda M-EDU `sede_educativa`).

---

## Términos técnicos innovaK

- **`managed=False`** — todos los modelos Django tienen esto porque la BD es
  **externa y compartida**; Django no genera ni aplica migraciones. Un cambio
  de schema (DDL) lo aplica Alex directamente en PostgreSQL.
- **Vigencia (multi-año)** — metas/actividades/eventos se repiten por año con
  el mismo nombre, diferenciados por VIGENCIA. Nunca se sobrescribe ni se
  borra lo del año anterior; se filtra por vigencia.
- **Angular-ready** — regla del proyecto: todo lo nuevo nace con la lógica
  separada de la presentación y los datos exponibles como JSON.
- **Kenny** — la mascota del sistema. **En producción desde 2026-07-06**, en dos
  frentes: el **onboarding guiado** (`apps/onboarding/` + tours en
  `frontend/src/app/features/onboarding/`) y el **asistente de chat con LLM**
  (`frontend/src/app/features/asistente/` + `apps/dashboard/services/kenny_llm.py`,
  que apunta a Mistral). El spec original se archivó en
  [`_historico/2026-07-06_onboarding_kenny.md`](_historico/2026-07-06_onboarding_kenny.md).

---

Si un término te falta aquí, probablemente esté en
[`arquitectura/ARQUITECTURA.md`](arquitectura/ARQUITECTURA.md),
[`referencia/SIPSE.md`](referencia/SIPSE.md) o en la bitácora de
[`/CLAUDE.md`](../CLAUDE.md).
