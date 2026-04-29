# Análisis de valor del software — innovaK

> **Fecha:** 2026-04-29
> **Autor:** Análisis técnico hecho por Claude Code después de ~2
> semanas trabajando dentro del repo (sesiones 2026-04-20 a 2026-04-29).
> **Audiencia:** Alex (dueño), líderes de la Alcaldía Local de Kennedy.
> **Tono:** directo, sin diplomacia inflada. La idea es que sirva para
> tomar decisiones, no para vender el sistema.

---

## TL;DR

innovaK es un **MVP funcional** que reemplaza Excel/papel para una
alcaldía local con cadena financiera real. Su valor concreto hoy es
**alto para Kennedy** (digitaliza un proceso que era 100% manual,
genera trazabilidad presupuestal end-to-end y reduce riesgo de errores
auditables). Su valor para vender a otras alcaldías es **bajo todavía**
(falta multi-tenant, hardening, tests, documentación). El código está
mejor de lo que parece — la deuda está ordenada y se ataca
sistemáticamente, pero la cobertura de tests (~2% de líneas) y la
ausencia de CI/CD son riesgos serios de cara a producción regulada.

---

## 1. Métricas reales (al 2026-04-29)

| Métrica | Valor |
|--------|-------|
| Líneas de código de producción | 17,936 |
| Líneas de tests | 405 (~2.3% ratio) |
| Smoke tests automatizados | 46 |
| Templates HTML | 132 |
| Endpoints HTTP (paths) | 202 |
| Modelos Django | ~98 |
| Apps activas | 7 |

| Datos en BD (uso real) | Valor |
|-----------------------|-------|
| Personas | 6,939 |
| Funcionarios activos | 19 |
| Proyectos | 18 |
| Tipos de evento | 5 |
| Eventos (activos) | 99 |
| Metas vinculadas a proyectos | 40 |
| KPIs (indicadores) | 35 |
| Avances de KPI registrados | 62 |
| Organizaciones | 59 |
| Beneficiarios | 3,580 |
| CDPs | 1 |
| ContratoActividadPlan | 0 |

Las dos últimas filas son la pista más importante: **la cadena
presupuestal arriba (Proyecto/Meta/KPI) se está usando, pero la cadena
financiera abajo (CDP/Contrato/Vinculación) prácticamente no**. Eso
significa que el sistema entrega valor en los reportes operativos
(eventos, beneficiarios, organizaciones), pero **el control
presupuestal real sigue probablemente en Excel**.

---

## 2. Lo que YA entrega valor (concreto y verificable)

### 2.1 Población atendida — 6,939 personas registradas

Antes esta data probablemente estaba en hojas de cálculo dispersas. Hoy
hay un modelo de datos con `Persona` + 26 catálogos (sexo, etnia,
discapacidad, estrato, etc.) que permite reportes cruzados. Esto es
**valioso para auditorías** y para responder preguntas tipo "¿a cuántas
personas con discapacidad hemos atendido en UPZ X en el último año?".

### 2.2 Trazabilidad de eventos — 99 eventos vivos en territorio

Cada evento tiene fecha, lugar (con coordenadas), funcionario
responsable, dependencia, subgrupo y tipo. Eso permite el mapa de
Kennedy (`/geo/mapa-kennedy/`) que es **visibilidad operativa real**
para el alcalde y los líderes — algo que ningún Excel produce.

### 2.3 Cadena presupuestal a medias

Los 40 MetaProyecto + 35 KPIs + 62 avances **prueban que se está
usando**, pero los 0 ContratoActividadPlan revelan que los contratos
legacy (96 con valor=NULL) no están conectados. La cadena completa
existe en el modelo, pero los datos históricos no se han migrado.

### 2.4 Banco de Iniciativas — recién en producción

Convocatoria del proyecto 2784 (280 colectivos recreodeportivos). El
QR funciona, el formulario público está mobile-first, las reglas de
validación están implementadas. **Inscripciones reales esperadas: 4-11
de mayo**. Es la prueba más limpia del valor del sistema: digitaliza
un proceso que sería 100% papel.

### 2.5 Validaciones bloqueantes (reducción de errores)

Implementadas en sesión 2026-04-28:
- `Σ contratos.valor ≤ CDP.saldo` (no se sobre-asigna un CDP).
- `Σ vinculaciones ≤ contrato.valor` (no se sobre-asigna un contrato).

Estas validaciones **previenen errores presupuestales que en Excel son
invisibles** hasta la auditoría. Es un seguro real para Alex y para la
Contraloría.

### 2.6 Stack moderno y mantenible

Django 4.2 + Postgres + Redis + Docker. No hay magia, no hay frameworks
exóticos. Cualquier dev Django senior se sube en 1 día. Eso protege
contra el riesgo de "el sistema murió cuando se fue Fulano".

---

## 3. Lo que NO entrega valor todavía (honesto)

### 3.1 Dashboard IA (`apps.dashboard`)

OpenAI + Plotly, vistas instaladas. Pero ¿se usa? ¿genera decisiones
reales? Sin medir engagement, esto es feature factory. **Recomendación:
medir uso por 30 días; si <2 usuarios distintos por semana, considerar
removerlo** (o dejarlo como demo, no como módulo del producto).

### 3.2 Votaciones (`apps.votaciones`)

Módulo aislado, en inglés (deuda C5), sin integración con el resto. Si
es para una elección puntual, OK. Si es módulo del producto, debería
estar en español y conectado con `Persona`/`Beneficiario`. **Estado:
deuda viva, decisión pendiente con Alex.**

### 3.3 Hub `/dashboard/` con 6 cards top-level

PR-C lo entregó, está en producción. Pero ¿la jerarquía de 6 cards →
sub-hubs → 12 cards en presupuesto refleja cómo trabajan los
funcionarios? Sin métricas de navegación reales, es UX a ciegas.

### 3.4 Cadena financiera operativa apenas en uso

1 CDP, 0 vinculaciones a actividad. Si queremos que esto sea **el**
sistema de gestión presupuestal, hace falta:
- Migrar los 96 contratos legacy con sus CDP correctos.
- Que Alex y los contadores **dejen Excel** y entren al sistema. Ese
  cambio cultural es probablemente **el bloqueante real**, no el
  software.

---

## 4. Riesgos arquitectónicos (los que vale la pena conocer)

### 🔴 R1 — BD compartida `managed=False`

innovaK no es dueño del schema. Si otro sistema externo modifica
`poblacion_kennedy`, innovaK puede romperse en runtime sin aviso. No
hay tests que ejerciten esa frontera. **Mitigación recomendada:**
contract tests sobre las 10 tablas críticas (smoke ampliado a
`describe table` + columnas esperadas).

### 🟠 R2 — Cobertura de tests del 2%

405 líneas de tests vs 17,936 de producción. Los 46 smoke tests
**solo verifican que las URLs no exploten**, no que la lógica funcione.
Una regresión de cálculo (saldo de CDP, magnitud aportada al KPI) no
se detecta. **Esto es el mayor riesgo técnico**. La skill
`pytest-coverage` está instalada — usarla.

### 🟠 R3 — APIs sin versionar, sin DRF

Los endpoints son `JsonResponse` directos. Si mañana hay una app móvil
o integración con SIPSE bidireccional, hay que reescribir todo. No es
bloqueante hoy, pero **define límites de crecimiento**.

### 🟡 R4 — Modelos duplicados (M1 viva)

`Actividad`, `Programa`, `Zona` con misma `db_table` en apps distintas.
Cualquier desarrollador nuevo se equivocará al elegir. Bug latente.

### 🟡 R5 — Sin CI/CD ni staging real

El hook pre-push corre los smokes localmente. No hay GitHub Actions,
no hay deploy automatizado, no hay ambiente de staging separado de
producción. **Pruebas y producción comparten BD.** Cuando algún test
escriba a BD por error, contamina prod.

### 🟢 R6 — Static files patológicos

Documentado en CLAUDE.md. No es bloqueante hoy pero es feo.

---

## 5. Madurez técnica — puntuación honesta

| Dimensión | 0-10 | Comentario |
|-----------|------|------------|
| **Funcionalidad** | 7 | Cubre los flujos reales de Kennedy. Faltan ENTREGA/CURSO específicos. |
| **Confiabilidad** | 5 | Tests insuficientes, sin staging. Confiamos en que "anda" porque se ve andar. |
| **Seguridad** | 7 | Hotfix S1-S4 aplicado. Hardening pre-gov.net listo. CSRF correcto. Falta auditoría externa. |
| **Performance** | 7 | Redis cache + índices + paginación. Buen estado. |
| **Mantenibilidad** | 6 | Convenciones documentadas, deuda priorizada, agentes especializados. Pero `eventos.py` 993 líneas, M1 sin resolver. |
| **Documentación** | 8 | Después de la reorganización 2026-04-29, esto es 8/10. Antes 5. CLAUDE.md + agentes + bitácora son ejemplares. |
| **Operabilidad** | 5 | Sin CI, sin staging, sin alertas. Despliegue manual. Logs estructurados son recientes. |
| **Accesibilidad** | 4 | Parche WCAG en PR-J1, pero auditoría completa pendiente. Riesgo regulatorio. |

**Promedio: 6.1** — un sistema joven que entrega valor real pero con
huecos visibles en confiabilidad y operabilidad. Suficiente para una
alcaldía con Alex supervisando. Insuficiente para multi-tenancy o
gov.net sin trabajo previo.

---

## 6. Cómo lo veo si fuera mi proyecto (criterio personal)

### Lo que me impresiona

1. **Disciplina del flujo git** — feat/* → desarrollo → Pruebas →
   produccion, con cascada documentada. Esto es muy raro en proyectos
   de un solo dueño.
2. **Bitácora de sesiones en CLAUDE.md** — registro honesto de qué se
   hizo, qué falló, qué quedó pendiente. Vale más que cualquier ADR.
3. **Deuda priorizada** (DEUDA_TECNICA.md) con IDs estables. 33
   resueltos en pocas semanas. Eso es ritmo de equipo grande.
4. **Agentes especializados** (backend, bd, estilos, arquitectura, qa,
   skills) con prompts maduros. Eso multiplica la productividad de
   forma medible.
5. **Patrón managed=False asumido como decisión consciente, no como
   accidente**. Eso muestra que las restricciones del entorno se
   tomaron en serio en lugar de pelearlas.

### Lo que me preocupa

1. **Cobertura de tests insuficiente para algo que toca dinero.** Si
   esto fuera mi código, no dormiría tranquilo con 46 smoke tests
   protegiendo la cadena CDP→Contrato→Avance.
2. **Apps muertas viven en el repo más tiempo del necesario.**
   `apps.documento`/`kordial`/`VitalK` ya se borraron, pero la regla de
   "borrar lo muerto rápido" debería ser parte de cada PR.
3. **`apps/login/views/eventos.py` 993 líneas** es un olor a Dios-class.
   Refactor en services es la salida — **deuda M6 viva**.
4. **El dueño es bottleneck** — Alex aprueba todo: DDL, merges, deploys.
   Eso protege calidad pero limita escalabilidad humana.

### Si tuviera que ponerle precio

- **Para Kennedy hoy:** este sistema le ahorra a la alcaldía probablemente
  $15-25M COP/año en horas de funcionarios + reduce riesgo de hallazgos
  en auditoría (impagable). El costo de producirlo (6-9 meses dev senior)
  ya está pagado en valor.
- **Para vender a otra alcaldía:** no está listo. Falta multi-tenant,
  hardening, tests, soporte, SLA. **Estimación de trabajo para llegar:
  3-4 meses adicionales.**
- **Para licenciar a la Secretaría Distrital de Gobierno (20 alcaldías):**
  proyecto serio, 6-12 meses, requiere refactor a multi-tenant y APIs
  versionadas. ROI potencial muy alto, riesgo técnico moderado.

---

## 7. Foco recomendado próximos 3 meses

Si fuera el roadmap que yo defendería:

### Mes 1 — fortalecer la base operativa que ya entrega valor

1. **Subir cobertura de tests al 40%** en presupuesto + banco_iniciativas
   + eventos. Skill `pytest-coverage` + `django-tdd` ya están listas.
2. **Migrar los 96 contratos legacy** (valor=NULL, cdp_id=NULL) — bloquea
   la utilidad de la cadena financiera. Requiere session presencial con
   Alex para verificar valores.
3. **Cerrar M1** (modelos duplicados) — 1 día de trabajo, mucho mejor
   onboarding después.

### Mes 2 — preparar para gov.net

1. **Auditoría WCAG 2.2 AA** completa con `accessibility` skill +
   remediación. Esto es **regulatorio**.
2. **CI/CD básico**: GitHub Actions corriendo smokes en cada PR.
3. **Staging real**: container separado conectado a BD réplica.

### Mes 3 — habilitar crecimiento

1. **API versionada con DRF** para las 10 rutas más importantes (no
   reemplazar todo, abrir la puerta).
2. **Multi-tenant evaluation**: ¿es viable que innovaK soporte 20
   alcaldías? Spike de 1 semana con prototipo de partición por
   `localidad_codigo`.
3. **Documentar API pública** con drf-spectacular o equivalente.

Y siempre, en paralelo: **quitar deuda viva** según prioridad de
DEUDA_TECNICA.md.

---

## 8. Apreciación final

innovaK no es código perfecto. Tiene 11 ítems de deuda activa, ~2% de
cobertura de tests, modelos duplicados y un archivo de 993 líneas. Lo
es **suficiente** para entregar valor real a Kennedy hoy. Y eso es lo
que importa: software que produce > software perfecto que no produce.

La disciplina con que se documenta y se ataca la deuda es
**inusualmente buena** para un proyecto de un solo dueño. Si esa
disciplina se mantiene 6 meses más y se le agrega cobertura de tests,
esto puede pasar de MVP de Kennedy a producto licenciable a la
Secretaría Distrital. La oportunidad está sobre la mesa.

El riesgo más serio no es técnico. Es operativo: **si Alex se enferma,
se cae por una semana, ¿quién toma decisiones de DDL, de merge a
producción, de qué deuda atacar?** Hay que documentar esos criterios
o entrenar un segundo aprobador. La calidad del código no protege
contra el bus factor de un solo dueño.

— Si vas a mostrar este análisis a stakeholders, mi recomendación es
que sea con la sección 5 (puntuación) destacada y un compromiso visible
sobre el roadmap del §7. Eso convierte una conversación defensiva
("¿por qué falta X?") en una proactiva ("aquí está el plan").
