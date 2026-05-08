# Banco de Iniciativas Recreodeportivas — Propuesta v2

> **Estado:** propuesta — pendiente de aprobación de Alex.
> **Fecha:** 2026-05-08.
> **Origen:** sugerencias del área de deportes sobre el formulario público
> actual (`/banco-iniciativas/<evento_id>/inscribir/`).
> **Análisis crítico:** del pedido literal (15 cambios) se descartan 3 por
> redundancia o sobre-ingeniería; los 12 restantes se agrupan en 3 PRs.

---

## 1. Resumen ejecutivo

| Aspecto | Cifras |
|---|---|
| Cambios pedidos por el revisor | ~15 |
| Cambios aceptados | 12 |
| Cambios descartados (con justificación) | 3 |
| PRs propuestos | 3 (sin DDL → DDL pequeño → DDL mediano) |
| Columnas BD nuevas | 3 |
| Tablas BD nuevas | 1 (puente M2M) |
| Catálogos refinados (sin tabla nueva) | 2 |
| Registros legacy afectados | 4 inscripciones (sin firma, no validadas) |

---

## 2. Lectura crítica del pedido

### 2.1. Lo que se descarta y por qué

#### ❌ Catálogo nuevo `tipo_identificacion_organizacion`

El revisor propuso un desplegable con 4 opciones (Reconocimiento /
Aval / NIT / Carta de conformación) como "tipo de identificación". Estos
NO son tipos de identificación equivalentes:

| Opción | Qué es realmente |
|---|---|
| Reconocimiento deportivo | Acto administrativo IDRD. Soporte legal. |
| Aval deportivo | Documento de liga/federación. Soporte legal. |
| NIT | Identificación tributaria DIAN. |
| Carta de conformación | Documento de colectivo informal. Soporte legal. |

Mezclan identificadores tributarios con papeles que prueban existencia.
Además, son las mismas 4 categorías que hoy maneja el catálogo
`tipo_organizacion`.

**En su lugar** → refinamos `tipo_organizacion` (sección 4.1).

#### ❌ Catálogos `categoria_espacio` + `tipo_espacio_actividad`

Pedido implícito: jerarquía Red Estructurante → Tipo de espacio. Eso
duplicaría el catálogo `escenario` que ya existe y se usa en la sección
7 ("Escenarios requeridos").

**En su lugar** → agregar columna `categoria_pot` al catálogo `escenario`
existente, agrupar visualmente los checkboxes y crear una sola tabla
puente nueva para "uso actual".

#### ❌ Lat/lon de la sede administrativa con mapa Leaflet

El revisor mencionó "para georreferenciación". El postulante está en
celular, dispuesto a llenar mínimo. Si la sede es opcional y nadie
consume hoy `sede_lat/sede_lon`, agregar Leaflet es sobre-ingeniería.

**En su lugar** → barrio + UPL + dirección textual son suficientes. Si
en el futuro se requiere geo, se hace batch desde la dirección.

---

### 2.2. Inconsistencia interna del pedido

El revisor pidió simultáneamente:
- **1.d**: agregar "Ubicación de sede administrativa" en Sección 1.
- **3.a**: renombrar Sección 3 "Ubicación de la organización" →
  "Escenarios de Actividades".
- **3.b**: en Sección 3 mantener orden jerárquico Dirección/Barrio/UPL.

Si la sección 3 deja de hablar de la organización, los campos
barrio/UPL/dirección **no tienen sentido ahí**. Se contradicen los puntos
3.a y 3.b.

**Resolución**: migrar barrio/UPL/dirección de Sección 3 → Sección 1
("Sede administrativa", opcional). Sección 3 queda exclusivamente para
"Escenarios donde desarrolla actividades". El orden jerárquico (UPL →
Barrio → Dirección, de mayor a menor unidad territorial) se aplica en
Sección 1.

---

### 2.3. Aciertos del pedido (cambios sin reservas)

- **2.a (Quitar NIT del tipo doc del representante)**: bug pre-existente.
  Una persona natural no tiene NIT; ese valor del catálogo
  `tipo_documento` no debe aparecer en el desplegable del representante.
- **6 (Reformular pregunta de impacto)**: la pregunta actual es ilógica
  ("¿qué tanto su iniciativa impacta políticas?"). La nueva mide
  percepción del beneficio recibido por la organización, que es lo que
  realmente sirve como criterio de evaluación.
- **7 (Mover descripción al inicio de Sección 7)**: lógica pedagógica:
  primero el qué, después los recursos.

---

## 3. PRs propuestos (orden y alcance)

### PR-1 — Cambios triviales sin DDL (1 día)

Solo template + form (labels, choices, queryset, orden de campos).

- **2.a** Filtrar `TipoDocumento` queryset del representante:
  excluir `codigo=5` (NIT), ordenar "Otro" (`codigo=6`) al final.
- **4** Renombrar label `rango_poblacion`:
  "Población aproximada que atenderá" → "Población que atiende
  actualmente". Subtítulo de Sección 4 también.
- **6** Reformular Sección 6:
  - Pregunta: "¿Considera que las políticas públicas distritales o
    locales del deporte, recreación y actividad física han impactado
    positivamente a su organización?"
  - `IMPACTO_CHOICES` (mantener `value` técnicos):
    ```python
    ("mucho", "Sí, mucho")
    ("parcial", "Sí, parcialmente")
    ("nada", "No, no han tenido impacto")
    ("no_conozco", "No conozco las políticas públicas")
    ```
  - Label de `impacto_justificacion`: "¿Por qué? (Responda brevemente)".
  - Mantener validación cruzada: si respuesta ≠ `no_conozco`, justificación
    obligatoria.
- **7** Reordenar Sección 7:
  - `propuesta_descripcion` arriba (encabezado, después del subtítulo).
  - Disciplina principal / otros deportes / escenarios / implementos /
    URL siguen abajo.

**Riesgo**: nulo. Solo afecta UX. Datos legacy compatibles.

---

### PR-2 — DDL pequeño: refinar tipo_organizacion + soporte legal (1-2 días)

#### DDL

```sql
-- 2.1. Agregar columnas a inscripcion_banco_iniciativa
ALTER TABLE inscripcion_banco_iniciativa
  ADD COLUMN numero_soporte_legal TEXT NULL,
  ADD COLUMN soporte_legal_mongo_id VARCHAR(64) NULL;

-- 2.2. Refinar catálogo tipo_organizacion
-- Renombres (mantener códigos para no romper FKs existentes)
UPDATE tipo_organizacion SET nombre = 'Club o escuela con Reconocimiento deportivo (IDRD)',
       orden = 1
 WHERE codigo = 1;
UPDATE tipo_organizacion SET nombre = 'Persona jurídica con NIT (ESAL, fundación, asociación)',
       orden = 3
 WHERE codigo = 2;
UPDATE tipo_organizacion SET nombre = 'Colectivo con carta de conformación',
       orden = 4
 WHERE codigo = 3;
-- "Otro" se desactiva (no se borra para preservar FKs históricas)
UPDATE tipo_organizacion SET activo = false WHERE codigo = 4;
-- Nueva opción: Aval deportivo
INSERT INTO tipo_organizacion (codigo, nombre, activo, orden)
VALUES (5, 'Club con Aval deportivo (liga/federación)', true, 2);
```

Resultado del catálogo (los 4 que ven los postulantes, ordenados):
1. Club o escuela con Reconocimiento deportivo (IDRD)
2. Club con Aval deportivo (liga/federación)
3. Persona jurídica con NIT (ESAL, fundación, asociación)
4. Colectivo con carta de conformación

#### Form

- Reemplazar campo `nit` por `numero_soporte_legal` (texto libre,
  opcional). Label sugerido: "Número del soporte legal (resolución IDRD,
  número de aval, NIT, etc.)".
- Agregar campo `soporte_legal_archivo` (`forms.FileField`, opcional).
  Validar tipo (PDF/PNG/JPG) y tamaño (≤5 MB).
- Validación cruzada en `clean()`: al menos uno de
  (`soporte_legal_url`, `soporte_legal_archivo`) debe estar lleno.
- Persistir el archivo cifrado a Mongo (mismo patrón que firma):
  `mongo_storage.guardar(blob, mime, owner={"tipo": "banco_iniciativa",
  "inscripcion_id": insc.id, "campo": "soporte_legal"})` →
  guardar el `_id` en `soporte_legal_mongo_id`.
- Persistir `numero_soporte_legal` en cabecera.
- Compatibilidad con `Organizacion.nit`: si `tipo_organizacion.codigo
  ∈ {2, 5}` (NIT o Aval que típicamente también lleva NIT), copiar el
  número a `Organizacion.nit` cuando la organización se cree.

#### Template

- Reemplazar input de NIT por `numero_soporte_legal`.
- Agregar uploader de archivo (igual UX que firma: botón visible +
  preview + clear).
- Mantener `<details>` colapsable para URL externa (alternativa).

#### Riesgo

Bajo. Las 4 inscripciones legacy referencian códigos 1-4 del catálogo
(no se borran, solo se renombran y desactivan). El campo `nit` viejo
queda en `Organizacion.nit` como cero-impacto histórico.

---

### PR-3 — DDL mediano: migrar sede + escenarios de uso actual (2-3 días)

#### DDL

```sql
-- 3.1. Categoría POT en catálogo escenario
ALTER TABLE escenario
  ADD COLUMN categoria_pot VARCHAR(20) NULL;

-- Categorización de las 13 filas existentes (ejemplo, ajustar con Alex)
UPDATE escenario SET categoria_pot = 'red_estructurante'
  WHERE codigo IN (3, 7, 9, 10);  -- Polideportivo, Pista atletismo, Piscina, Coliseo
UPDATE escenario SET categoria_pot = 'red_proximidad'
  WHERE codigo IN (1, 2, 6, 8);   -- Cancha fútbol, multi, gimnasio, patinódromo
UPDATE escenario SET categoria_pot = 'otros_dotacionales'
  WHERE codigo = 5;                -- Salón comunal/casa cultura
UPDATE escenario SET categoria_pot = NULL
  WHERE codigo IN (4, 11, 12, 13); -- Parque abierto, propio, sin escenario, otro

-- INSERT filas faltantes (POT 2022)
INSERT INTO escenario (codigo, nombre, activo, orden, categoria_pot) VALUES
  (14, 'Plazoleta', true, 14, 'otros_dotacionales'),
  (15, 'Humedal', true, 15, 'otros_dotacionales'),
  (16, 'Sendero o zona verde', true, 16, 'otros_dotacionales'),
  (17, 'Escenario NTD (No Tradicional Deportivo)', true, 17, 'red_proximidad');

-- CHECK constraint para integridad (opcional pero recomendado)
ALTER TABLE escenario
  ADD CONSTRAINT escenario_categoria_pot_check
  CHECK (categoria_pot IN ('red_estructurante', 'red_proximidad',
                           'otros_dotacionales') OR categoria_pot IS NULL);

-- 3.2. Tabla puente para "uso actual" (Sección 3 nueva)
CREATE TABLE inscripcion_banco_escenario_actual (
  id BIGSERIAL PRIMARY KEY,
  inscripcion_id BIGINT NOT NULL
    REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
  escenario_codigo SMALLINT NOT NULL
    REFERENCES escenario(codigo) ON DELETE RESTRICT,
  CONSTRAINT uq_insc_banco_esc_actual UNIQUE (inscripcion_id, escenario_codigo)
);
CREATE INDEX idx_insc_banco_esc_actual_insc
  ON inscripcion_banco_escenario_actual(inscripcion_id);
```

#### Modelo Django

```python
# apps/banco_iniciativas/models/inscripcion.py
class InscripcionBancoEscenarioActual(models.Model):
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa",
        on_delete=models.CASCADE,
        db_column="inscripcion_id",
        related_name="rel_escenarios_actuales",
    )
    escenario = models.ForeignKey(
        "banco_iniciativas.Escenario",
        on_delete=models.PROTECT,
        db_column="escenario_codigo",
        to_field="codigo",
        related_name="rel_inscripciones_uso_actual",
    )
    class Meta:
        managed = False
        db_table = "inscripcion_banco_escenario_actual"
        unique_together = (("inscripcion", "escenario"),)


# En InscripcionBancoIniciativa
escenarios_actuales = models.ManyToManyField(
    "banco_iniciativas.Escenario",
    through="banco_iniciativas.InscripcionBancoEscenarioActual",
    through_fields=("inscripcion", "escenario"),
    related_name="inscripciones_uso_actual",
)
```

```python
# apps/banco_iniciativas/models/catalogos.py — agregar a Escenario
class Escenario(_CatalogoBase):
    categoria_pot = models.CharField(max_length=20, null=True, blank=True)
    # ...
```

#### Form / Template

**Sección 1** (cambios):
- Agregar bloque "Sede administrativa (si tiene)" con campos:
  - `upl` (ModelChoiceField, opcional)
  - `barrio` (ModelChoiceField, opcional, dependiente de UPL si se quiere
    cascada — opcional para no complicar)
  - `direccion` (CharField, opcional)
- Estos 3 campos **se mueven** desde Sección 3 (no se duplican).

**Sección 3** (rediseño completo):
- Título: "3. Escenarios de actividades"
- Subtítulo: "Espacios donde tu organización desarrolla actualmente sus
  actividades."
- Body: tres bloques de checkboxes (M2M
  `inscripcion_banco_escenario_actual`):
  - **Parques de la Red Estructurante** (parques metropolitanos y zonales,
    >1 ha): muestra escenarios con `categoria_pot='red_estructurante'`.
  - **Parques de la Red de Proximidad** (parques vecinales y de bolsillo,
    <1 ha): muestra escenarios con `categoria_pot='red_proximidad'`.
  - **Otros espacios dotacionales**: muestra escenarios con
    `categoria_pot='otros_dotacionales'` (salones comunales, plazoletas,
    humedales, senderos).
- Los escenarios sin categoría (parque abierto genérico, "no contamos con
  escenario fijo", "otro") se muestran al final como "Sin categoría POT".

#### Riesgo

Medio. Cambio de estructura semántica de Sección 3. Las 4 inscripciones
legacy:
- Sus campos `barrio`, `upl`, `direccion` mantienen los valores
  guardados (las columnas no cambian de tabla — solo se reasignan
  visualmente en el form).
- No tienen registros en `inscripcion_banco_escenario_actual` (tabla
  nueva). Se interpreta como "no marcaron escenarios actuales", que es
  consistente con que la sección no existía.

---

## 4. Detalle por sección

### 4.1. Sección 1 — Datos de la organización

**Antes (campos)**:
1. nombre_organizacion
2. nit (libre, opcional)
3. tipo_organizacion (4 opciones, incluye "Otro")
4. correo, telefono
5. redes (facebook, instagram, otra)

**Después (campos)**:
1. nombre_organizacion
2. tipo_organizacion (4 opciones refinadas, sin "Otro")
3. numero_soporte_legal (libre, opcional, etiqueta clara según contexto)
4. soporte_legal_archivo + soporte_legal_url (al menos uno)
5. correo, telefono
6. **Sede administrativa (opcional)**: upl → barrio → dirección
7. redes (facebook, instagram, otra)

### 4.2. Sección 2 — Representante legal

**Único cambio**: queryset de `rep_tipo_doc` filtra `exclude(codigo=5)` y
ordena con "Otro" al final.

Implementación:
```python
# en __init__ del form
qs = TipoDocumento.objects.exclude(codigo=5)  # quita NIT
# orden: primero por nombre, "Otro" al final
self.fields["rep_tipo_doc"].queryset = sorted(
    qs, key=lambda t: (1 if t.nombre.lower() == "otro" else 0, t.nombre)
)
```

(Alternativa más simple: agregar columna `orden` al catálogo
`tipo_documento` y poblarlo. Pero requiere DDL adicional y este filtro
JS-side es suficiente.)

### 4.3. Sección 3 — Escenarios de actividades

Ver PR-3.

### 4.4. Sección 4 — Población que atiende actualmente

- Label de `rango_poblacion`: cambiar a "Población que atiende
  actualmente".
- Subtítulo de la sección: "Indique la magnitud y características de
  la población que atiende hoy. Esta información es relevante para
  evaluar la experiencia de su organización."
- Sin cambios en BD.

### 4.5. Sección 5 — Beneficios previos ALK

Sin cambios.

### 4.6. Sección 6 — Impacto en políticas

- Label de la pregunta: "¿Considera que las políticas públicas
  distritales o locales del deporte, recreación y actividad física han
  impactado positivamente a su organización?"
- Choices (solo labels, values técnicos quedan):
  ```python
  IMPACTO_CHOICES = [
      ("", "— Selecciona —"),
      ("mucho", "Sí, mucho"),
      ("parcial", "Sí, parcialmente"),
      ("nada", "No, no han tenido impacto"),
      ("no_conozco", "No conozco las políticas públicas"),
  ]
  ```
- Label de justificación: "¿Por qué? (Responda brevemente)".
- Mantener validación cruzada (si ≠ `no_conozco`, justificación
  obligatoria).

### 4.7. Sección 7 — Propuesta

Reordenamiento en template (form sin cambios):

```html
<!-- Antes (orden actual): -->
<!-- 1. disciplina_principal + otros_deportes -->
<!-- 2. escenarios -->
<!-- 3. implementos -->
<!-- 4. propuesta_url -->
<!-- 5. propuesta_descripcion (al final) -->

<!-- Después (orden propuesto): -->
<!-- 1. propuesta_descripcion (al inicio, etiqueta destacada) -->
<!-- 2. disciplina_principal + otros_deportes -->
<!-- 3. escenarios -->
<!-- 4. implementos -->
<!-- 5. propuesta_url -->
```

### 4.8. Sección 8 — Compromisos y firma

Sin cambios.

---

## 5. Compatibilidad con datos legacy

| Tabla / dato | Filas legacy | Impacto |
|---|---|---|
| `inscripcion_banco_iniciativa` | 4 | Cero. Solo nuevas columnas (NULL OK). |
| `tipo_organizacion` | 4 filas catálogo | Códigos preservados; renombre semántico. Insert código 5. |
| `escenario` | 13 filas catálogo | Columna nueva `categoria_pot` (NULL OK). Insert 4 filas. |
| `inscripcion_banco_escenario` | n filas | Sin cambios. Sección 7 sigue igual. |
| `inscripcion_banco_escenario_actual` | 0 (tabla nueva) | Las 4 inscripciones legacy quedan sin escenarios actuales (semántica correcta: la sección no existía). |
| `Organizacion.nit` | n filas | Sin cambios. Se sigue poblando cuando aplique. |

---

## 6. Tests a actualizar / agregar

- `apps/banco_iniciativas/tests/test_smoke.py`:
  - Asegurar que el form acepta `numero_soporte_legal` opcional.
  - Test de validación cruzada `soporte_legal_archivo` OR `soporte_legal_url`.
  - Test de filtro queryset `rep_tipo_doc` (no aparece NIT).
  - Test de form en sección 3 que persiste M2M
    `inscripcion_banco_escenario_actual`.

Estimado: +6 a +8 smoke tests. (Hoy: 105 OK).

---

## 7. Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| FK `tipo_organizacion_codigo` rota tras refinamiento | Baja | Alto | Renombramos sin borrar (códigos 1-4 vivos). |
| Datos legacy con sentido alterado en Sección 6 | Cierta | Bajo | 4 inscripciones, ninguna validada. Documentar en CLAUDE.md. |
| Mongo cae al subir soporte legal | Baja | Medio | Mismo patrón de la firma (try/except, logs). El form no rompe si Mongo falla — solo no guarda el blob. |
| Duplicación visual entre "escenarios actuales" (S3) y "requeridos" (S7) | Cierta | Bajo | Subtítulos claros: "actualmente" vs "para esta propuesta". |

---

## 8. Próximos pasos

1. **Aprobación de Alex** sobre este documento.
2. **PR-1** (triviales, sin DDL) → 1 día → cascadear a producción.
3. **PR-2** (DDL pequeño) → 1-2 días → DDL coordinado con Alex
   (`apps/banco_iniciativas/scripts/005_v2_pr2_soporte_legal.sql`) →
   cascadear.
4. **PR-3** (DDL mediano) → 2-3 días → DDL coordinado
   (`apps/banco_iniciativas/scripts/006_v2_pr3_escenarios_actuales.sql`)
   → cascadear.
5. Smoke E2E con organización real para validar end-to-end (post PR-3).
6. Capacitación al equipo de deportes (Daniel Lugo) sobre los cambios
   de UX visibles.

---

## 9. Decisiones explícitas que requieren tu visto bueno

- [ ] ✅ **Sección 1.a**: refinar `tipo_organizacion` (no crear catálogo
      nuevo). Insertar código 5 "Aval deportivo".
- [ ] ✅ **Sección 1.c**: aceptar archivo (PDF/PNG/JPG, ≤5 MB) o URL
      externa, al menos uno.
- [ ] ✅ **Sección 1.d**: migrar barrio/UPL/dirección de Sección 3 a
      Sección 1 como "Sede administrativa". Sin lat/lon, sin Leaflet.
- [ ] ✅ **Sección 3.b**: orden jerárquico **UPL → Barrio → Dirección**
      (de mayor a menor unidad territorial), aplicado en Sección 1.
- [ ] ✅ **Sección 3.c**: reusar catálogo `escenario` con columna
      `categoria_pot`, agregar 4 filas (Plazoleta, Humedal, Sendero,
      Escenario NTD), crear tabla puente `inscripcion_banco_escenario_actual`.
- [ ] ✅ **Sección 6**: cambiar labels de `IMPACTO_CHOICES` (mantener
      `value` técnicos para no romper datos).
- [ ] ⚠️ **Soporte legal obligatorio**: ¿el archivo o URL del soporte
      legal debe ser **obligatorio** para todas las postulaciones? Hoy
      es opcional. Recomendación: obligatorio (si la organización
      postula, debe acreditar existencia).
- [ ] ⚠️ **Nuevas categorías POT en `escenario`**: la categorización
      tentativa de las 13 filas existentes (sección DDL del PR-3)
      requiere validación con Daniel Lugo o conocimiento de POT 2022.
