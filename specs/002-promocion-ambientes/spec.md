# Spec 002 · Promoción entre ambientes

**Estado:** borrador · **Creada:** 2026-08-24
**Constitución:** XI y XII
**Evidencia:** `docs/operacion/descubrimiento_completitud_expediente_2026-08-24.md` §9-§10

---

## 1 · Problema, con la causa medida

**Los ambientes no divergen: no existen.**

1. `desarrollo`, `Pruebas` y `produccion` comparten el **mismo hash de árbol**
   (`0831ed0f…`). `git diff` entre cualquier par: **cero**.
2. Un solo checkout del repositorio en el host, un solo contenedor.
3. `volumes: - .:/app` — el contenedor sirve el **working tree**.
4. **No hay CI.**

**Por qué «no cascadea» el frontend:** `frontend/dist` está gitignored —0
archivos en el índice, 147 en disco— y `spa.py` lo sirve del filesystem. El
frontend **no viaja con el repositorio**.

Por eso lo que no aparece es siempre lo mismo —dashboard, estilos,
accesibilidad— y el backend sí, porque está bind-mounteado.

## 2 · Resultado esperado

```
commit SHA → build → tests → Development → Testing → Production
```

El **mismo artefacto** promovido, no recompilado por ambiente. Poder responder
«¿qué versión corre cada ambiente?» con un SHA.

## 3 · Requisitos

### RF-1 · El frontend viaja con el artefacto
Multi-stage build en el `Dockerfile` que compile la SPA **con
`--base-href=/app/`**. Deja de existir el paso manual en el servidor.

### RF-2 · Identificación de versión
Cada ambiente expone `commit SHA · build · fecha · ambiente` por vía técnica o
administrativa. No al Alcalde. *Constitución VI.*

### RF-3 · Un solo artefacto
Imagen etiquetada por SHA de commit, promovida tal cual entre ambientes.
*Constitución XI.*

### RF-4 · Configuración por ambiente
Sólo variables de entorno, secretos, URLs y flags. **Nunca** código de rama
distinta. *Constitución XI.*

### RF-5 · Health check tras el deploy
La aplicación responde · **los assets resuelven** · migraciones aplicadas · API
principal responde · Dashboard carga · Mi Área carga · smoke tests pasan.

> Un `200` en `/app/` **no** alcanza: el 2026-08-24 la aplicación respondía 200
> con el contenedor sano y estaba en blanco, porque los assets daban 404. El
> health check tiene que resolver los assets del `index.html`.

### RF-6 · Migraciones controladas
Nunca automáticas ni destructivas en producción. Aditivas y nullable. Con
rollback. *Constitución VII.*

### RF-7 · Rollback
Código: artefacto anterior conocido, por SHA. Base de datos: **no** se asume
reversible — las migraciones nuevas se diseñan compatibles hacia adelante.

### RF-8 · Detección de drift
Detectar y reportar cuando un ambiente tenga algo que no venga del artefacto.
*Constitución XII.*

## 4 · Restricción dura

> **La BD es única y compartida.** `managed=False`, PostgreSQL externa. **No hay
> base por ambiente**: un DDL afecta a los tres a la vez.
>
> Separar ambientes de verdad exige infraestructura nueva —incluida la decisión
> sobre las bases—, no un cambio de código. Esta spec **no** puede resolverlo
> sola.

## 5 · Preguntas abiertas (CLARIFY)

| # | Pregunta | Bloquea |
|---|---|---|
| C-1 | ¿Tres máquinas, o tres contenedores en una? | topología |
| C-2 | ¿Una BD por ambiente o sigue compartida? | RF-6, riesgo mayor |
| C-3 | ¿Dónde vive el registry de imágenes? | RF-3 |
| C-4 | ¿CI en GitHub Actions o en la máquina? | RF-1 |
| C-5 | ¿Quién aprueba la promoción a producción? | flujo |

## 6 · Criterios de aceptación

- [ ] Un `git push` produce un artefacto con la SPA **ya compilada** y con base href correcto
- [ ] Los tres ambientes reportan su SHA y se puede ver cuál está rezagado
- [ ] Promover no recompila
- [ ] El health check **detecta** el caso de assets en 404 con la app respondiendo 200
- [ ] Nadie necesita correr `ng build` a mano en un servidor
- [ ] Rollback probado al menos una vez

## 7 · Mientras tanto

Con un árbol y un contenedor, las reglas de convivencia están en
`docs/operacion/TRABAJO_EN_PARALELO.md`. Son un parche consciente, no la
solución.
