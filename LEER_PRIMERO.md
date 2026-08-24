# Por dónde empezar a leer

Son 2.762 líneas. **No hay que leerlas todas**, y menos de corrido. Este índice
va de mayor a menor densidad: los primeros 20 minutos dan el 80 %.

---

## Si tienes 10 minutos — lee esto y nada más

**`specs/001-completitud-expediente-subgrupos/contrapeso.md`** · 204 líneas

Los ocho supuestos del plan que **no sobreviven a la base de datos**. Es lo que
cambia el trabajo, y lo único que de verdad hay que discutir. Los tres primeros
son los importantes.

---

## Si tienes 30 minutos

1. **`contrapeso.md`** — lo de arriba
2. **`specs/001-.../clarify.md`** · 151 líneas — las 5 preguntas abiertas: 3 se
   resolvieron mirando la BD, 2 necesitan tu decisión. **Empieza por el resumen
   del final.**
3. **`specs/001-.../tasks.md`** · 117 líneas — sólo la tabla final:
   **«Pendientes de Alex»**, 4 decisiones

---

## Si vas a decidir sobre la fase completa

| Orden | Documento | Qué te da |
|---|---|---|
| 1 | `contrapeso.md` | dónde el plan y la realidad no coinciden |
| 2 | `clarify.md` | las 5 preguntas, 3 ya respondidas con evidencia |
| 3 | `specs/001-.../spec.md` | qué se va a construir: 10 requisitos |
| 4 | `specs/001-.../plan.md` | cómo, en 10 etapas con dependencias |
| 5 | `specs/001-.../tasks.md` | las tareas, y qué te bloquea a ti |
| 6 | `.specify/memory/constitution.md` | las 12 reglas que gobiernan todo |
| 7 | `specs/002-promocion-ambientes/spec.md` | los ambientes, spec aparte |

---

## Si quieres entender el sistema, no la fase

**`brain/00-Inicio.md`** — es el índice del vault. Ábrelo con Obsidian
(`brain/` como vault) y navega por el grafo; en texto plano funciona igual pero
se pierde lo mejor.

Las cinco notas que más se enlazan, si sólo vas a leer cinco:

1. `brain/Arquitectura/Mapa-del-sistema.md` — las 13 apps
2. `brain/Relaciones/Contrato-Meta.md` — por qué es N y no 1
3. `brain/Fuentes/SECOP.md` — de dónde sale casi todo, y sus dos trampas
4. `brain/UI/Mi-Area.md` — la pantalla que hay que construir
5. `brain/Arquitectura/Ambientes-y-despliegue.md` — por qué no cascadea

---

## Documentos de operación (viven en `docs/`)

| | |
|---|---|
| `docs/operacion/descubrimiento_completitud_expediente_2026-08-24.md` | 231 líneas · la evidencia cruda que originó todo lo demás |
| `docs/operacion/TRABAJO_EN_PARALELO.md` | 179 líneas · cómo trabajan dos personas sin tumbar la app. **Léelo si vas a tocar el repo con Anderson trabajando** |
| `docs/operacion/dashboard_presupuesto_estado_2026-08-24.md` | 393 líneas · lo que se hizo en el dashboard. Ya está aplicado; es referencia |

---

## Lo que necesito de ti

Están en la última tabla de `tasks.md`. En corto:

| | Decisión | Bloquea |
|---|---|---|
| **T1.1** | aprobar el DDL de auditoría (único de la fase, aditivo, con rollback) | toda la captura |
| **T2.3** | ¿de dónde salen los CRP? ¿BOGDATA, PREDIS, archivo de Hacienda? | la forma de pago |
| **T6.1** | ¿quién captura? *(recomiendo: roles `Coordinador*`)* | la pantalla |
| **T6.2** | ¿la completitud pondera igual? *(recomiendo: cifra plana, presentación por bloques)* | la pantalla |

Las dos primeras desbloquean el trabajo de fondo. Las dos últimas sólo la
pantalla, y tienen recomendación — si no dices nada, sigo por ahí.
