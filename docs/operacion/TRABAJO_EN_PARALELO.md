# Trabajar dos personas en innovaK sin pisarse

> **Para el Claude de Anderson y para el de Alex.** Léelo entero antes del
> primer `git` o del primer `npm run build`. Son cinco minutos y evitan tumbar
> la aplicación — que ya pasó dos veces.

---

## 1 · Por qué esto necesita reglas

innovaK **no** tiene un ambiente por persona. Tiene:

- **UN** contenedor `innova_k`, que monta el árbol de trabajo: `volumes: .:/app`
- **UN** `frontend/dist`, que está en `.gitignore` y **no viaja con git**
- **UNA** base de datos, externa y compartida (`10.100.102.12`), `managed=False`

Consecuencia directa, y es lo único que hay que interiorizar:

> **Lo que tú compilas o checkouteas en `/home/innova/Proyectos/innovaK`, lo
> ven TODOS.** No existe «mi build» y «tu build». Existe uno.

---

## 2 · Quién trabaja dónde

| | Carpeta | Rama | Qué hace |
|---|---|---|---|
| **Anderson** | `/home/innova/Proyectos/innovaK` | `feat/panel-subgrupo-ux` | Angular / UI. Es el árbol que **sirve el contenedor**, así que ve sus cambios en vivo |
| **Alex / Claude** | `/home/innova/Proyectos/innovaK-backend` | `feat/brain-spec-kit` | backend, Brain, specs, docs. Clon aparte: **no toca lo que se está sirviendo** |

El clon comparte los objetos de git con el original (`--shared`): ocupa 27 MB,
no duplica el repositorio.

### Dos cuentas de Claude en la misma máquina

```bash
claude              # cuenta de Alex      (perfil ~/.claude)
claude-anderson     # cuenta de Anderson  (perfil ~/.claude-anderson)
```

El alias ya está en `~/.bashrc`. Lo que separa las cuentas es
`CLAUDE_CONFIG_DIR`: cada perfil tiene sus credenciales, su historial y sus
tokens. La primera vez, `claude-anderson` pide `/login`.

---

## 3 · Las tres reglas que no se negocian

### Regla 1 — El build SIEMPRE lleva `--base-href=/app/`

```bash
cd frontend && npm run build        # ✅ ya lleva la bandera y se autoverifica
```

**Nunca** `npx ng build` a secas ni `ng build --configuration production`:
`--configuration production` **no** implica el base-href, son cosas distintas.

Sin la bandera, el `index.html` pide `/main.js` y `/chunk-*.js` en la **raíz**
del dominio, recibe 404 y la aplicación sale **en blanco para todo el mundo**.

Lo que hace que este error sea traicionero:

- el contenedor sigue `Up (healthy)`;
- `/app/` responde **200**;
- el build compila **limpio**, sin un solo aviso.

Pasó el 2026-06-18 y **volvió a pasar el 2026-08-24**. Por eso `npm run build`
ahora corre `scripts/verificar_base_href.js` al final y falla si está mal.
Compruébalo tú también:

```bash
grep -o '<base[^>]*>' frontend/dist/innovak-frontend/browser/index.html
# tiene que decir exactamente:  <base href="/app/">
```

### Regla 2 — Nunca `git add -A`, `git add .` ni `git commit -a`

Como el árbol es compartido, «todo» incluye el trabajo sin commitear del otro.

Ya pasó: un `git add -A` dentro de un commit de **documentación** se llevó 380
líneas del panel de subgrupo que Anderson estaba escribiendo. Se rescataron,
pero se pudieron haber perdido.

```bash
git add frontend/src/app/features/subgrupo/subgrupo-panel.component.ts   # ✅
git add -A                                                               # ❌ bloqueado
```

Hay un hook que lo bloquea (`.claude/hooks/no-git-add-all.sh`). Antes de
commitear, mira qué hay suelto y de quién es:

```bash
git status --short
```

### Regla 3 — Avisa antes de cambiar de rama en el árbol servido

`git checkout` cambia el **backend** (Python está bind-mounteado) pero **no**
cambia `frontend/dist` (está gitignored). Si las dos mitades quedan de commits
distintos, la aplicación responde 200 y falla por dentro.

Pasó el 2026-08-24: un checkout a una rama sin los modelos `EtapaContrato` y
`SecopPlanPago` dejó el backend sin ellos mientras el `dist` compilado sí los
pedía.

**Si cambias de rama en `/home/innova/Proyectos/innovaK`, recompila después.**

---

## 4 · Cómo traer el trabajo del otro

Anderson y Alex tocan archivos **disjuntos** hoy — verificado, cero solapamiento.
Aun así, para trabajar sobre lo último:

```bash
git merge feat/expediente-contrato-completo      # ✅ probado: limpio
```

> ### ⚠️ MERGE, nunca REBASE
>
> Probado el 2026-08-24: `git rebase feat/expediente-contrato-completo` sobre
> la rama de Anderson **descarta su commit en silencio**, sin conflicto y sin
> aviso. Git ve su parche como «ya aplicado» porque un commit posterior tocó
> esos mismos archivos.
>
> El merge sí conserva las dos cosas — verificado, y compila.

Después de mergear, **siempre**:

```bash
cd frontend && npm run build
```

---

## 5 · Antes de decir «listo»

```bash
# 1. Compila y el base href es correcto
cd frontend && npm run build

# 2. La aplicación carga de verdad (no basta un 200: mira los assets)
curl -s http://localhost:8034/app/ | grep -o '<base[^>]*>'
docker logs innova_k --since 2m 2>&1 | grep -c "Not Found"     # tiene que dar 0

# 3. Los tests pasan
docker exec innova_k python scripts/run_smoke_tests.py | tail -3

# 4. Accesibilidad y contraste, si tocaste estilos
cd frontend && npm run contraste && node scripts/verificar_iconos_fa.js
```

---

## 6 · Decisiones de estilo ya cerradas — no las revierta

Están medidas y commiteadas. Detalle en
`docs/operacion/dashboard_presupuesto_estado_2026-08-24.md`.

- **Presupuesto SCSS:** el error pasó de 24 kB a **32 kB**; el aviso sigue en 12.
- **Identidad ≠ dato:** el rojo `#D6001C` y el amarillo `#FFC72C` son **marca**,
  nunca codificación de datos. La fila de KPI usa 4 tonos + 1 neutro.
- **Colores de texto:** `$color-{success,warning,danger,info}-hondo` en
  `_tokens.scss`. **No** hardcodear `#166534` ni sus vecinos: ya se hizo siete
  veces en cinco pantallas y por eso existen los tokens.
- **`aria-live`** sólo envuelve mensajes concretos, nunca un panel entero.
- Patrones consolidados (barras, avisos, anillos de foco, chips, pastillas):
  reutilizar, no crear variantes locales.

---

## 6.1 · Pendiente para Anderson — 4 regresiones de contraste (2026-08-26)

`node scripts/verificar_contraste.js` está en **rojo con 4 parejas NUEVAS**,
todas en archivos que ahora mismo tienes sin commitear. Verificado guardando
mis cambios aparte: aparecen igual sin ellos, así que no vienen del backend.

```
4.39:1 (exige 4.5)    14px  #6B7280 sobre #f3f4f6
      actividades-hub.component.ts  ·  .tipo-group__body p
4.39:1 (exige 4.5)  12.5px  #6B7280 sobre #f3f4f6
      eventos-insights.component.ts ·  .area-note
   1:1 (exige 4.5)    16px  #fff   sobre #ffffff
      eventos-list.component.ts     ·  .kpi-tile__icon
4.39:1 (exige 4.5)    11px  #6B7280 sobre #f3f4f6
      eventos-list.component.ts     ·  .ui-search kbd
```

Las tres de 4.39:1 son el mismo caso: `$color-neutral-500` sobre
`$color-neutral-100`. Sobre blanco ese gris da 4.83:1 y pasa; sobre el gris
100 se queda a 0,11 del mínimo. El arreglo es **`$color-neutral-600`**
(6.87:1 sobre neutral-100, 7.56:1 sobre blanco), no aclarar el fondo.

La de 1:1 (`#fff` sobre `#ffffff`) es blanco sobre blanco: o el icono es
decorativo y va a `scripts/_contraste_base.json` **con el motivo escrito**, o
le falta el fondo de color que tenía el patrón original.

No las toqué porque son tus archivos y están sin commitear. Si el icono es
decorativo, la exención es legítima — pero tiene que quedar escrita.

---

## 7 · Cuando esto deje de ser necesario

Todo lo anterior existe porque hay **un** árbol y **un** contenedor. La
solución de fondo —un ambiente por persona, artefacto versionado, CI— está
diagnosticada en
`docs/operacion/descubrimiento_completitud_expediente_2026-08-24.md` §9-§10.

Mientras tanto: estas reglas, y avisar.
