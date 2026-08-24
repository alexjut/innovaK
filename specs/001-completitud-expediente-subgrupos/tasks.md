# Tasks · Spec 001

Del plan a tareas verificables. `[B]` = bloqueante · `[A]` = necesita a Alex.

---

## Etapa 0 · Scope de escritura  `[B]`

- [ ] **T0.1** Validar `contrato_id` contra los contratos del área en
      `VincularContratoActividadPlanView` — unión de `ContratoProyecto` y
      `ContratoActividadPlan`, la misma regla del panel
- [ ] **T0.2** Test de acceso cruzado: usuario de Educación con un contrato de
      Seguridad → **403**
- [ ] **T0.3** Barrer los demás endpoints de escritura de presupuesto buscando
      el mismo patrón (validar destino y no origen)

## Etapa 1 · Auditoría  `[B]` `[A]`

- [ ] **T1.1** `[A]` Aprobar el DDL de la tabla de auditoría — **único DDL de la
      fase**. Backup <24 h + script de rollback
- [ ] **T1.2** Modelo `managed=False` + servicio `registrar_cambio()`
- [ ] **T1.3** Campos: quién · cuándo · antes · después · proyecto · contrato ·
      fuente
- [ ] **T1.4** Test: una captura deja exactamente una fila legible

## Etapa 2 · Modelo `Crp`

- [ ] **T2.1** Mapear `contrato_id`, `forma_pago_codigo`, `plazo_dias`,
      `periodo_codigo`, `valor_neto`, `autorizacion_giro`
- [ ] **T2.2** Verificar que `metrics.py` sigue igual (hoy lee 0 filas)
- [ ] **T2.3** `[A]` **¿De dónde salen los CRP?** ¿BOGDATA, PREDIS, archivo de
      Hacienda? Sin fuente, la forma de pago es captura manual — pero en `crp`
- [ ] **T2.4** ¿Existe catálogo de códigos de forma de pago, o hay que crearlo?

## Etapa 3 · Precarga desde SECOP

- [ ] **T3.1** Comando `precargar_desde_secop`, en la línea de los `ingest_*`
- [ ] **T3.2** Llenar objeto, valor, fechas y **contratista** donde falten
- [ ] **T3.3** Nunca pisar en silencio: diferencia con dato existente → auditoría
- [ ] **T3.4** Test de idempotencia: correrlo dos veces no cambia nada
- [ ] **T3.5** Verificar contratista **0/25 → N/25** y reportar el número real
- [ ] **T3.6** Enganchar al cron junto a `sync_fuentes_oficiales`

## Etapa 4 · Servicio de completitud

- [ ] **T4.1** `services/completitud_expediente.py`, calculado al vuelo
- [ ] **T4.2** Por campo: valor · estado · fuente · editable
- [ ] **T4.3** `$0` distinto de `Sin dato` en el payload
- [ ] **T4.4** Metas **en plural**, derivadas
- [ ] **T4.5** Tests: contrato 105 → 1 meta «determinada»; contrato 98 → 7;
      contrato 104 → `0 %` como cero real
- [ ] **T4.6** Área sin proyectos → «no tiene plan asignado», no un cero mudo

## Etapa 5 · API

- [ ] **T5.1** Extender `AreaPanelView` con la completitud (no duplicar)
- [ ] **T5.2** Endpoint de captura: etapa, forma de pago, ejecución técnica
- [ ] **T5.3** Validar contrato **y** destino contra el área
- [ ] **T5.4** Toda escritura llama a `registrar_cambio()`
- [ ] **T5.5** Tests de manipulación de ids

## Etapa 6 · Pantalla  `[A]`

> ⚠️ **Coordinar con Anderson** — trabaja en `feat/panel-subgrupo-ux`.
> Ver `docs/operacion/TRABAJO_EN_PARALELO.md`.

- [ ] **T6.1** `[A]` **C-3: ¿quién captura?** Recomendación: roles `Coordinador*`
- [ ] **T6.2** `[A]` **C-4: ¿ponderación?** Recomendación: cifra plana,
      presentación por bloques
- [ ] **T6.3** Resumen: proyectos · contratos · pendientes · `Todos` / `Solo pendientes`
- [ ] **T6.4** Proyecto → contratos con su completitud
- [ ] **T6.5** Ficha contrato por contrato
- [ ] **T6.6** Precargados no editables, con origen visible
- [ ] **T6.7** Reutilizar tokens y patrones ya consolidados
- [ ] **T6.8** `npm run contraste` y `verificar_iconos_fa.js` en verde

## Etapa 7 · 360°

- [ ] **T7.1** Verificar que la etapa capturada aparece en el stepper
- [ ] **T7.2** Confirmar que no hay copia del dato
- [ ] **T7.3** Cero cadenas técnicas en la UI gerencial

## Etapa 8 · Segundo subgrupo

- [ ] **T8.1** Probar con **Seguridad** (3 proyectos), no Educación
- [ ] **T8.2** Verificar el caso de metas múltiples de punta a punta
- [ ] **T8.3** `grep -rn "if.*subgrupo.*==" ` → **cero**

## Etapa 9 · Calidad

- [ ] **T9.1** `npm run contraste` en CI: baseline + no-regresión
- [ ] **T9.2** Borrar `ENTIDADES` con TS + tests + build en verde
- [ ] **T9.3** Los 5 gráficos del expediente: decorativo si repite la cifra que
      ya está al lado
- [ ] **T9.4** Retomar la auditoría del expediente **en lotes de 5-6 agentes**
- [ ] **T9.5** Medir la altura en navegador cuando haya salida a Internet

---

## Definition of Done

**Funcional** — un funcionario completa un contrato en Mi Área → persiste →
queda auditado → el 360° lo consume → aparece bien.

**Entre ambientes** — el mismo comportamiento validado en Desarrollo y Pruebas,
con ruta reproducible a Producción. **Depende de la spec 002.**

---

## Pendientes de Alex

| | Qué | Bloquea |
|---|---|---|
| **T1.1** | aprobar el DDL de auditoría | toda la captura |
| **T2.3** | de dónde salen los CRP | forma de pago |
| **T6.1** | quién captura (rec.: `Coordinador*`) | la pantalla |
| **T6.2** | ponderación (rec.: plana + bloques) | la pantalla |
