# Constitución de innovaK

Reglas que gobiernan **qué se puede construir y cómo**. Cuando una spec y la
constitución se contradigan, manda la constitución. Cuando algo no esté acá y
haga falta, se agrega — con su motivo.

Versión 1.0 · 2026-08-24

---

## I. No se inventan datos institucionales

Ningún dato que represente realidad institucional se rellena, se estima ni se
asume por defecto.

- Ausencia se dice **`Sin dato`**, nunca `0`. `$0` significa «medimos y es
  cero». Convertir ausencia en cero es inventar.
- Una etapa contractual **NULL** significa «pendiente de registrar», nunca
  «Ejecución».
- Lo que la fuente no permita determinar **se declara indeterminado**. Si un
  contrato toca varias metas, se muestran varias — no se elige una.

## II. La fuente oficial prevalece

```
FUENTE OFICIAL  >  DATO INTERNO VALIDADO  >  CAPTURA MANUAL
```

- Hay fuente oficial → se **precarga** y **no se edita**. La pantalla dice de
  dónde viene.
- No la hay → nace `Pendiente`, lo completa quien está autorizado, queda
  auditado.
- Una captura manual **nunca** sobrescribe en silencio un dato oficial.
- **Antes de pedirle un dato a un funcionario, se agota la fuente.** El
  funcionario no vuelve a escribir lo que la Administración ya sabe.

## III. No se duplica información

Un dato vive en **un** sitio. Si el Dashboard y Mi Área muestran la etapa, leen
la misma columna.

No se crean catálogos que ya existen. No se crea una tabla para una relación
que ya es derivable — si se deriva, se deriva.

## IV. Todo cambio sensible es auditable

Sobre información contractual o presupuestal, el dato sin autor ni fecha **no
vale**: no se puede defender ante un ente de control.

Se registra: **quién · cuándo · valor anterior · valor nuevo · proyecto ·
contrato · fuente**.

La auditoría se diseña **antes** que el formulario que la necesita.

## V. Los permisos se validan en el backend

Ocultar un botón **no** es autorizar. Toda escritura verifica en el servidor que
el objeto **y** el destino pertenezcan al ámbito del usuario.

Un id enviado por el cliente es **entrada no confiable**, siempre.

## VI. La UI gerencial no expone detalles internos

El Alcalde no lee nombres de tabla, ni «falta DDL», ni conteos de filas. Lee
`Sin dato` o `Pendiente por diligenciar`.

El diagnóstico técnico vive en `docs/` y en el Brain, no en la pantalla.

## VII. Las migraciones son seguras

- La BD es **externa, compartida y `managed=False`**: no hay base por ambiente.
  Un DDL afecta a todos a la vez.
- Todo DDL: backup <24 h + aprobación explícita de Alex. Sin excepción.
- Aditivo y nullable por omisión. Compatible hacia adelante siempre que se pueda.
- Nunca una migración destructiva automática en producción.
- Todo DDL viaja con su script de rollback.

## VIII. Se reutiliza la arquitectura existente

Antes de crear: buscar. Vale para catálogos, servicios, endpoints, componentes,
tokens de estilo y patrones de UI.

Si algo existe y no sirve, se dice **por qué** y se deja escrito.

## IX. La spec gobierna el comportamiento

Para trabajo complejo, primero la spec. Si la implementación se aparta, se
actualiza la spec o se corrige la implementación — no se dejan divergir.

## X. El Brain conserva el conocimiento estable

Lo que costó descubrir se destila en `brain/`. Cardinalidades reales, por qué se
tomó una decisión, dónde miente un nombre.

**No** es base de datos operacional: cero datos de ciudadanos, cero secretos.

## XI. Los cambios son reproducibles entre ambientes

Un cambio se programa **una** vez. El mismo artefacto probado se promueve:

```
commit → build → tests → Development → Testing → Production
```

Las diferencias entre ambientes viven en variables de entorno y secretos,
**nunca** en código de rama distinta.

## XII. Ningún ambiente se mantiene con cambios manuales no versionados

Si algo «sólo funciona en desarrollo» porque alguien tocó archivos a mano, eso
es un defecto y se corrige de raíz.

Todo cambio: **versionado, reproducible, promovible, auditable**.

> Hoy esto se incumple: `frontend/dist` está gitignored y hay que rebuildearlo a
> mano en cada máquina. Está reconocido como deuda en
> `docs/operacion/descubrimiento_completitud_expediente_2026-08-24.md` §10 y en
> `brain/Arquitectura/Ambientes-y-despliegue.md`. La constitución fija el
> destino, no describe el presente.
