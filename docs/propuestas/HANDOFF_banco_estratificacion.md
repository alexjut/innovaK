# Handoff — resolver pendientes Banco / Estratificación + cierre RBAC

> Documento de traspaso para la siguiente sesión. Escrito 2026-07-16.
> Self-contained: contexto + comandos inmediatos + revert + backlog priorizado.
> Pégale a Claude el bloque "Prompt para pegar" o trabaja directo desde aquí.

Proyecto **innovaK** (Alcaldía de Kennedy). Django 4.2 + PostgreSQL externa
`poblacion_kennedy` (managed=False). Contenedor `innova_k` **bind-montea `.:/app`**
→ un `restart` toma el código nuevo. Flujo git: `feat → desarrollo → Pruebas →
produccion`. **Nada cascadea a produccion sin OK de Alex.** DDL sólo con backup
<24h. Lee el código actual antes de actuar.

---

## Estado al cierre (2026-07-16)

- ✅ **RBAC dashboard_ia** — el motor de consulta de beneficiarios ya scopea por
  subgrupo/contrato/curso en las 3 rutas (incluida la de KENNY "Consultar datos").
  **En producción** (`produccion=04e9b42`). Reporte:
  `docs/propuestas/rbac_dashboard_ia_scope_fix.md`.
- ✅ **Estratificación IDECA** — todo lo técnico ya está en producción (capa de
  mapa recortada a Kennedy, `estrato_ideca` en 175/241 sedes, `estrato_ideca_org`
  por barrio, infra reconstruible + secretos fuera de la imagen).
- ✅ **PR-A rúbrica Banco v4 — EN PRODUCCIÓN (2026-07-16)**. `produccion=f8d440b`,
  556 tests verdes, contenedor reiniciado, `recalcular_lote(62)` → 24/24 en `v4`.
  Medido en vivo (coincide exacto con el dry-run): AUTO media **7,08 → 25,75**,
  rango 14–40, **23/24 cambian de puesto** (no 21 — el dry-run inicial contó de menos).
  Totales consistentes (`auto+comité+bono`), `v3` congelada para auditoría.
  Snapshot de revert: `~/banco_evals_v3_pre_v4.json`.
  - **Hallazgo:** las 24 **no tienen nota del Comité todavía** (`puntaje_comite=0`
    en las 24) → el recálculo no pisó trabajo de nadie, y el ranking de hoy **es**
    el bloque AUTO. Baja la urgencia de "avisar al Comité": no se sobrescribió nada,
    pero el orden sí cambió respecto de cualquier listado impreso antes del 16/07.

### Qué cambió en PR-A (rúbrica v3 → v4, mismos pesos; sólo cambia la fuente)
| Criterio | Antes (leía) | v4 (lee) |
|---|---|---|
| C3 capacidad | `personas_beneficiar` (vacío) | `rango_poblacion` (codigo 1–4) → 2/5/8/10 |
| C4 etario | `rango_etarios` esperando cód. 6–12 | `rango_etarios` cód. reales 1–5 (se conservan 6–12) |
| C5/C6 enfoque | M2M vacío `enfoques_propuesta` | M2M real `enfoques` (catálogo `enfoque_diferencial`) |
| C2 territorialidad | upz + escenarios | sin cambio; 0 en el piloto (no hay UPZ declarada) |

**Clasificación de enfoques (decisión Alex 2026-07-14):**
Diferencial (máx 15) = {1 discapacidad, 3 LGBTQI+, 4 indígena, 5 NARP, 6 Rrom}.
Inclusión (máx 10) = {8 víctimas, 9 calle, 10 adicciones, 11 rural}.
2 mujeres → sólo bono. 7 mayores → ya cuenta en C4. 12 ninguno → 0.

---

> ⚠️ **Los Pasos 0 y 1 YA SE EJECUTARON el 2026-07-16.** PR-A está en producción y
> las 24 recalculadas en `v4`. Se conservan abajo solo como registro de lo que se
> corrió y porque el REVERT sigue siendo válido. **No vuelvas a correr el Paso 1.**
> Si necesitas verificar el estado, corre solo el Paso 0.

## Paso 0 — ¿PR-A ya está en producción? *(al 16/07: sí — responde `v4` ×24)*
```bash
cd /home/innova/Proyectos/innovaK
git log --oneline -1 produccion | grep -q "rúbrica Banco" && echo "PR-A ya cascadeado" || echo "PR-A PENDIENTE"
docker exec innova_k python -c "import os,django,collections;os.environ.setdefault('DJANGO_SETTINGS_MODULE','core.settings');django.setup();from apps.banco_iniciativas.models import BancoEvaluacionInscripcion as EV;print(collections.Counter(e.rubrica_version for e in EV.objects.filter(inscripcion__evento_id=62)))"
```
Si las 24 dicen `v4` → ya está, salta al backlog. Si `v3` → ejecuta el Paso 1.

## Paso 1 — Cascada PR-A + recálculo en vivo (si aún está en v3)
```bash
cd /home/innova/Proyectos/innovaK
# 1) snapshot v3 para poder revertir (ranking = plata pública)
docker exec innova_k python -c "import os,django,json;os.environ.setdefault('DJANGO_SETTINGS_MODULE','core.settings');django.setup();from apps.banco_iniciativas.models import BancoEvaluacionInscripcion as EV;print(json.dumps([{'inscripcion_id':e.inscripcion_id,'puntaje_auto':float(e.puntaje_auto or 0),'rubrica_version':e.rubrica_version,'total':float(e.total or 0),'auto_detalle':e.auto_detalle} for e in EV.objects.filter(inscripcion__evento_id=62)]))" > ~/banco_evals_v3_pre_v4.json
# 2) cascada
git checkout desarrollo && git merge --ff-only fix/banco-rubrica-fuentes
git checkout Pruebas    && git merge --no-ff desarrollo -m "Merge desarrollo → Pruebas: fix rúbrica Banco fuentes (v4)"
git checkout produccion && git merge --no-ff Pruebas    -m "Merge Pruebas → produccion: fix rúbrica Banco fuentes (v4)"
git push origin desarrollo Pruebas produccion            # el hook corre 556 tests
# 3) desplegar (bind-mount → basta restart)
docker compose -f docker-compose.yml restart innova_k
docker exec innova_k python manage.py check
# 4) recalcular las 24 bajo v4
docker exec innova_k python -c "import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','core.settings');django.setup();from apps.banco_iniciativas.services.puntaje import recalcular_lote;print(recalcular_lote(62))"
```
Esperado: `{'procesadas': 24, 'evento_id': 62}` y puntajes en escala 14–40 (media 25,8).

## REVERT (si el Comité pide marcha atrás)
```bash
docker exec -i innova_k python -c "
import os,django,json,sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE','core.settings'); django.setup()
from apps.banco_iniciativas.models import BancoEvaluacionInscripcion as EV
for d in json.load(sys.stdin):
    ev=EV.objects.filter(inscripcion_id=d['inscripcion_id']).first()
    if not ev: continue
    ev.puntaje_auto=d['puntaje_auto']; ev.rubrica_version=d['rubrica_version']
    ev.auto_detalle=d['auto_detalle']
    ev.total=(d['puntaje_auto'] or 0)+float(ev.puntaje_comite or 0)+float(ev.bono_genero or 0)
    ev.save()
print('revertidas')
" < ~/banco_evals_v3_pre_v4.json
```
(Revert de datos. Para revertir también el código: `git revert` de los merges + restart.)

---

## Backlog priorizado (esto es "terminar el trabajo")

1. ~~Verificar PR-A en vivo~~ ✅ hecho 2026-07-16. **Queda:** avisar al Comité que el
   ranking cambió (23/24 se movieron). C2 sigue en 0 porque las 24 no declararon UPZ.
2. **Deuda M22 — geometría de `barrio`: RECLASIFICADA a BLOQUEADA POR DATO EXTERNO**
   (2026-07-16). Ya **no** es "el código está listo, faltan datos" — es "no tenemos
   el archivo". Medido:
   - `apps/georeferenciacion/data/barrios_kennedy.geojson` **no sirve** para esto:
     recargarlo aporta **3 barrios de los 250** que faltan, y **0 de los 13** que
     bloquean al Banco.
   - **Por qué:** son productos distintos. El geojson es la capa **gruesa** de IDECA
     (111 polígonos: `ALQUERIA`, `BAVARIA`, `CASTILLA`, `TIMIZA`) y además solo 87 de
     esos 111 son de Kennedy (`COD_LOC='08'`; el resto son Bosa/Fontibón/Puente
     Aranda/Tunjuelito/Ciudad Bolívar). La tabla `barrio` es un catálogo **fino** de
     325 (`AGRUPACION DE VIVIENDA PIO XII`, `CIUDAD TECHO 1`, `ALOHA SECTOR NORTE`).
     Cruce: 32/111 por código, 50/325 por nombre (47 de esos ya tienen geometría).
   - **Confirmación:** de los 5 barrios del Banco que sí tienen geometría, 3 vinieron
     de este geojson (los gruesos: CIUDAD KENNEDY CENTRAL, ROMA, TIMIZA) y 2
     (TALAVERA, BOMBAY) de otra fuente.
   - **Qué se necesita:** la capa oficial de barrios de Catastro/IDECA que
     **corresponda al catálogo de 325**. Insumo externo → va al mismo bucket que la
     planilla DANE de M-EDU. **No volver a intentar cargar el geojson del repo.**
   - Aritmética del bloqueo: 24 inscripciones → 21 declaran barrio (3 no) → 18
     barrios distintos → solo **5 con geometría** → **6/24 resuelven**
     `estrato_ideca_org`. 6 + 15 bloqueadas + 3 sin barrio = 24.
3. **PR-7 bono por estrato — SIGUE BLOQUEADO, y la vía alterna también.**
   `inscripcion_banco_escenario_detalle` vacía (las 24 son anteriores a la captura de
   sedes) → el bono por sede sería +10 constante. **La vía alterna por barrio
   (`estrato_ideca_org`, PR-4) tampoco sirve para el piloto:** solo resuelve 6/24 (ver
   punto 2). Conclusión propuesta en el memo: **el criterio rige desde el próximo
   ciclo, no se aplica retroactivamente a las 24.**
   - ⚠️ **NO usar el `estrato` autodeclarado como fallback** (existe en las 24 y es
     tentador). Medido 2026-07-16: de los 6 casos contrastables contra IDECA, **solo
     2 coinciden**; los otros 4 difieren **todos en la misma dirección — el oficial es
     más alto que el declarado** (3vs2, 3vs1, 3vs2, 3vs2). Es el sesgo esperable
     cuando declarar menos da más puntos. n=6, pero el incentivo + la consistencia
     direccional bastan para no fundar plata pública ahí.
   - Si algún día se implementa: DDL aditivo `bono_estrato` (nullable) en
     `banco_evaluacion_inscripcion` + backup. Ojo: `total` se calcula en 2 sitios
     (`guardar_caracterizacion` y `_recalcular_total`) — tocar ambos.
4. ~~Memo al Comité~~ ✅ **actualizado 2026-07-16** (`estratificacion_ideca_memo_comite.md`,
   ya existía del 8/07 — se editó, no se creó). Ahora incluye: aviso del cambio de
   ranking (23/24), tabla calibrada sobre **2, 3 y 4** con la distribución real
   (82/91/2) y los renglones 1 y 5–6 marcados inactivos, separación de **"sin estrato
   oficial" (65 sedes) vs "sin resolver" (1)**, sección 4 nueva de **alcance** (no
   aplica al piloto) y la advertencia sobre el estrato autodeclarado.
   **Queda:** que Alex lo lea y lo envíe. **No se ha enviado a nadie.**
5. **C2 territorialidad**: decidir si se captura UPZ en el form del Banco o se deja en 0.
6. Independientes, menor prioridad: PR-D (auto-estrato al crear/editar sede) · PR-E
   (filtro del mapa a sólo sedes del Banco) · PR-F (tope 93 cupos dinámico).
7. **`docs/propuestas/estratificacion_ideca_estado.md`** sigue **untracked** — decidir
   si se commitea (es el estado de trabajo, muy completo).
8. **`docs/manuales_modulos/banco.md`** no documenta puntaje/105, ranking ni panel de
   comité — hacerlo **antes** de usarlo con Deportes.
9. (RBAC, adyacente) cockpit `api_beneficiarios_perfil` (`views_presupuesto.py`, módulo
   `presupuesto_proyectos`): expone perfiles agregados de beneficiarios cross-subgrupo a
   roles presupuestales. Se dejó SIN scopear a propósito — decidir si se scopea (PR aparte).

---

## Higiene de worktrees (opcional)
`fix/rbac-dashboard-ia-scope` y `fix/banco-rubrica-fuentes` quedan 100% mergeados tras
la cascada → se pueden borrar:
```bash
git worktree remove .claude/worktrees/rbac-dashboard-ia
git worktree remove .claude/worktrees/banco-rubrica
```
Hay otros worktrees viejos (estratificacion-ideca, docs-manuales, infra-*, ia-nl2sql) ya
mergeados — confirmar con `git worktree list` antes de borrar.

## Archivos clave
- `apps/banco_iniciativas/services/puntaje.py` — motor de la rúbrica (v4).
- `apps/banco_iniciativas/tests/test_puntaje.py` — tests (snapshot+restore, no filtran a prod).
- `apps/login/services/scope.py` — helpers RBAC (`personas_beneficiarias_visibles`, etc.).
- `docs/propuestas/estratificacion_ideca_estado.md` — estado detallado (untracked).
- `docs/propuestas/rbac_dashboard_ia_scope_fix.md` — reporte del fix RBAC.
- Catálogos BD: `enfoque_diferencial` (1–12), `rango_poblacion_atendida` (1–4),
  `rango_etario` (1–5). Piloto = evento **62**, 24 inscripciones.

---

## Prompt para pegar (siguiente sesión)
> Retomamos innovaK. Abre `docs/propuestas/HANDOFF_banco_estratificacion.md` y síguelo.
> Primero el Paso 0 (¿PR-A ya en producción?). Si falta, Paso 1 (cascada + recálculo de
> las 24 del evento 62). Luego el backlog: prioriza cargar geometría de `barrio` (M22)
> para desbloquear `estrato_ideca_org`, decidir PR-7 (bono por estrato — hoy bloqueado
> por `escenario_detalle` vacío + falta DDL `bono_estrato`), y preparar el memo al Comité
> calibrando la tabla estrato→puntos sobre estratos 2-3-4.
