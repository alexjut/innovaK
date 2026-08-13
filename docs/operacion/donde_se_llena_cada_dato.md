# Dónde se llena cada dato — y qué pasa cuando se llena

**Actualizado:** 2026-08-13

Este documento responde una pregunta concreta que salió en producción: *«si no
está en las fuentes ni en SECOP, ¿dónde lo lleno?»*.

La regla que lo ordena todo, acordada con Alex:

> **Lo que llega de una fuente oficial se sincroniza solo. Lo que no está en
> ninguna fuente lo llena el área a mano — pero desde la aplicación, y quedando
> conectado con el resto.**

---

## 1. Lo que se llena solo (no lo toque nadie)

Estas capas las trae un sincronizador y se refrescan sin intervención. Editarlas
a mano es trabajo perdido: el siguiente sync las pisa.

| Dato | Fuente | Comando |
|---|---|---|
| Estratificación | Catastro / IDECA | `sync_estratificacion --bogota` |
| Sectores catastrales, barrios legalizados | IDECA | `sync_capa` |
| Colegios distritales y matrícula | SED vía IDECA | `sync_colegios` |
| CAI | Secretaría de Seguridad | `sync_cai` |
| Metas y actividades del Plan | SEGPLAN / SDP | `ingest_sdp_datos_abiertos` |
| Contratos adjudicados | SECOP II (datos.gov.co) | `ingest_secop_contratos` |

Corren desde el cron a las 03:30 (`scripts/cron_sync_oficial.sh`).

---

## 2. Lo que NO está en ninguna fuente, y por qué

### El CDP no lo trae SECOP

Verificado el 2026-08-13 contra la API de datos.gov.co (dataset `jbjy-vk9h`):
para `CIA-773-2025`, SECOP publica **84 campos** y **ninguno es el número del
CDP**. El único relacionado es `saldo_cdp`, que llega en `0` —no lo reportan— y
además es un saldo, no un identificador.

Tiene una razón de fondo: **SECOP es el sistema de CONTRATACIÓN y el CDP es un
documento PRESUPUESTAL.** El certificado se expide en PREDIS/Hacienda antes de
contratar, así que nunca va a estar en SECOP. No hay integración que lo resuelva:
lo tiene el área.

### Los demás

| Dato | Por qué no hay fuente |
|---|---|
| Acceso / permanencia por beneficiario | Es una decisión del área sobre cada persona, no un dato publicado |
| Dotación entregada a cada sede | Sale del acta de liquidación del contrato |
| Coordenadas de las instituciones | El SNIES no publica geolocalización de sedes |
| Barrio de residencia del beneficiario | No viene en el archivo del área |

---

## 3. Dónde se llena cada uno

Todos verificados el 2026-08-13.

| Qué | Dónde | Cómo |
|---|---|---|
| **CDP** | `/app/presupuesto/cdps` | Botón crear: proyecto, número, valor, fecha |
| **Asignar CDP a un contrato** | `/app/presupuesto/contratos-internos` | Editar el contrato y elegir su CDP |
| **Valor de un contrato** | `/app/presupuesto/contratos-internos` | La lista de SECOP es SOLO LECTURA; el valor se registra acá |
| **Contrato → actividad del plan** | `/app/presupuesto/proyectos/<id>` | Vincular, con su monto |
| **Acceso / permanencia** | `/app/jovenes/cargue` | Volver a subir el archivo con esa columna: actualiza sin duplicar |
| **Beneficiarios de becas** | `/app/jovenes/cargue` | Revisar → preparar → procesar |
| **Dotación a colegios** | `/app/educacion` | Registrar la entrega en la SEDE, no en el colegio |
| **Ubicar instituciones** | `/app/educacion/instituciones` | Clic en la fila, pegar lat/lon y guardar |
| **Cuenta de acceso de una persona** | `/app/admin/personas` | Botón «Crear usuario» |

---

## 4. Qué pasa cuando se llena — comprobado, no prometido

El 2026-08-13 se simuló el CDP del convenio `CIA-773-2025` dentro de una
transacción, se midió el efecto y **se deshizo** (la base quedó intacta):

```
                         antes            después
cockpit · CDP registrado  $52.000.000  →  $23.220.769.452
cadena  · Educación cdp   $0           →  $23.168.769.452
panel   · sueltos         0                0
```

**No hay que tocar nada más.** El dato entra por la pantalla y se propaga solo al
tablero ejecutivo, a la cadena por proyecto y al panel del área. Lo mismo aplica
al resto: cada pantalla escribe en la cadena, no en una copia.

---

## 5. Lo que el sistema NO va a inventar

Ninguna de estas casillas se rellena con un valor plausible cuando falta el dato:

- **Números de CDP.** Son certificados con número y fecha que alguien expidió.
  Ponerles cifras verosímiles sería fabricar documentos que después se reportan
  al Distrito como ejecución real.
- **Acceso o permanencia por persona.** Define ejecución de meta oficial.
- **Coordenadas verificadas.** La geolocalización asistida existe
  (`geolocalizar_instituciones`) pero deja cada punto **marcado como aproximado**
  y con su procedencia, para que se distinga de uno que revisó una persona.

Un cero honesto se ve y se corrige. Un número inventado no se distingue de uno
real, y a los seis meses nadie sabe cuál era cuál.

---

## 6. Lo que se pone al día solo, a diario

`scripts/cron_mantenimiento_diario.sh` (04:00) corre `mantenimiento_diario
--aplicar`:

1. **Avances** de los KPI de becas, por vigencia.
2. **Catálogo de instituciones** desde los beneficiarios cargados.
3. **Purga de borradores** del Banco vencidos (habeas data: llevan cédulas).

Las tres **recalculan en vez de acumular**, así que si un día no corre, el
siguiente se pone al día solo. Una tarea que falla no tumba a las demás.

> **Pendiente:** instalar la línea en el crontab del host. El script y el comando
> ya están; falta el `crontab -e`.
