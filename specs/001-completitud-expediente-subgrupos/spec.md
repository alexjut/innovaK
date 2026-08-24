# Spec 001 · Completitud del expediente por subgrupo

**Estado:** borrador · **Creada:** 2026-08-24
**Constitución:** `.specify/memory/constitution.md`
**Evidencia:** `docs/operacion/descubrimiento_completitud_expediente_2026-08-24.md`

---

## 1 · Problema

El [[Explorador 360°]] muestra huecos: **0 de 25** contratos tienen etapa
contractual, **0 de 25** tienen contratista, **1 de 25** no llega a ningún
proyecto. La vista gerencial enseña vacíos sin dueño ni explicación.

Hoy no hay dónde completar eso. Mi Área muestra qué está suelto a nivel de
**relaciones** (`sueltos`), pero no a nivel de **campo por contrato**.

## 2 · Resultado esperado

Cada subgrupo completa, **contrato por contrato**, únicamente lo que falta —
después de que el sistema haya agotado las fuentes oficiales. Lo completado
aparece en el 360° sin copias del dato.

## 3 · Alcance

### Entra

- Precarga desde fuentes oficiales de todo lo disponible.
- Vista de completitud del expediente por proyecto y por contrato.
- Captura de lo que **ninguna** fuente provee: etapa contractual y forma de pago.
- Enganche contrato ↔ proyecto / actividad para lo que no llegó.
- Auditoría de todo dato capturado.
- Consumo en el 360°.

### No entra

- Rehacer el Dashboard 360°.
- Tabla `contrato_meta` — ver §5.1.
- Cambiar la cadena Proyecto → Meta → KPI.
- Separación de ambientes — spec propia.

## 4 · Requisitos

### RF-1 · Precarga antes que captura
El sistema llena desde `secop_contrato` todo campo con fuente oficial: objeto,
valor, fechas, contratista. **No** se le pide al funcionario.
*Constitución II.* Medido: cubre 25 contratistas, 3 valores, 5 fechas, 1 objeto.

### RF-2 · Origen visible
Cada campo precargado muestra su fuente (`SECOP ✓`) y **no es editable**.
*Constitución II, VI.*

### RF-3 · Completitud calculada, nunca escrita
El porcentaje de completitud se calcula al vuelo desde los campos reales. No se
persiste ni se cachea en una columna. *Constitución III.*

### RF-4 · Captura sólo de lo que ninguna fuente da
Únicamente **etapa contractual** y **forma de pago**. Todo lo demás se precarga
o se deriva.

### RF-5 · Metas en plural
Se muestra el **conjunto** de metas derivado de la cadena
contrato → actividad → indicador → meta. Una sola: «✓ determinada
automáticamente». Varias: se listan. **Nunca** se pide elegir. *Constitución I.*

### RF-6 · Sin dato ≠ cero
`Sin dato` y `$0` se distinguen visualmente y en el payload. *Constitución I.*

### RF-7 · Autorización en backend
Toda escritura valida que **el contrato Y el destino** pertenezcan al ámbito del
usuario. *Constitución V.* Cierra el hueco de
`brain/Seguridad/Scope-por-subgrupo.md`.

### RF-8 · Auditoría de toda captura
quién · cuándo · antes · después · proyecto · contrato · fuente.
*Constitución IV.* Se implementa **antes** que los formularios.

### RF-9 · Un solo dato
Lo registrado en Mi Área lo lee el 360° de la misma columna. *Constitución III.*

### RF-10 · Reutilizable, sin casos especiales
Cero `if subgrupo == "Educacion"`. Se valida con un segundo subgrupo.

## 5 · Decisiones tomadas con evidencia

### 5.1 · Contrato ↔ Meta se deriva, NO se persiste
Cardinalidad real **N**: de 5 contratos, cuatro tocan 3, 7, 2 y 2 metas.
Sólo uno resuelve a una. Ver `brain/Relaciones/Contrato-Meta.md`.

### 5.2 · Etapa contractual: el modelo YA existe
`EtapaContrato` + `Contrato.etapa/etapa_fecha/etapa_usuario` (DDL 010, aplicado
2026-08-23). Está en 0/25 porque **nadie la ha capturado**, no porque falte
dónde. **No se crea nada.**

### 5.3 · Plan de pago: ya se ingiere
`SecopPlanPago`, 36.210 filas, cubre 20 de 25. No se digita. No se asumen cuatro
trimestres: la periodicidad sale de la fuente.

### 5.4 · Forma de pago: lo único que falta persistir
No existe en ninguna tabla ni en SECOP. `SecopContrato.modalidad` es modalidad
de *contratación*, otra cosa.

### 5.5 · Ejecución técnica: pendiente de decidir
`Contrato.ejecucion` existe (4/25). **Antes** de volverlo captura manual hay que
determinar si se deriva de los KPIs. *Constitución III.*

## 6 · Preguntas abiertas (CLARIFY)

| # | Pregunta | Bloquea |
|---|---|---|
| C-1 | ¿Ejecución técnica se deriva de KPIs o la reporta el subgrupo? | RF-4, §5.5 |
| C-2 | ¿Forma de pago es catálogo cerrado o texto? ¿Qué valores? | §5.4, modelo |
| C-3 | ¿Quién captura: cualquiera del subgrupo o un rol específico? | RF-7 |
| C-4 | ¿La completitud pondera todos los campos igual? | RF-3 |
| C-5 | ¿El contrato sin proyecto se engancha desde Mi Área o es dato malo? | alcance |

## 7 · Criterios de aceptación

- [ ] Contratista pasa de **0/25** a lo que SECOP permita, **sin formularios**
- [ ] Un funcionario de Educación completa la etapa del contrato 105 y aparece
      en el 360° sin recargar caché ni duplicar el dato
- [ ] Un usuario de Educación **no** puede tocar un contrato de Seguridad, ni
      cambiando el id en la petición
- [ ] Toda captura deja rastro consultable
- [ ] Un contrato con varias metas las muestra **todas**
- [ ] `Sin dato` y `$0` se distinguen en pantalla
- [ ] Funciona igual en un segundo subgrupo, sin tocar código
- [ ] Cero cadenas técnicas en la UI gerencial

## 8 · Riesgos

| Riesgo | Mitigación |
|---|---|
| La BD es única: un DDL afecta a los tres ambientes | Backup <24 h + OK de Alex. Aditivo y nullable |
| `contrato.id` sin secuencia (deuda S5) | No insertar contratos nuevos en esta fase |
| Educación es piloto pequeño (1 proyecto, 1 contrato) y **no ejercita la cardinalidad N** | El segundo subgrupo no es opcional: Seguridad (3 proyectos) |
| Precargar puede pisar un dato bueno | Precedencia explícita + auditoría del cambio |
