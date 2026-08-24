# Cómo trabajamos — reparto de responsabilidades

**Acordado 2026-08-24.**

## Alex trabaja como siempre

Pide lo que necesita en lenguaje normal. **No** tiene que:

- recordar la ceremonia del Spec Kit;
- decidir en qué rama va cada cosa;
- acordarse de mergear, cascadear ni rebuildear;
- llevar la cuenta de qué ambiente tiene qué.

Lo que sí decide, porque es suyo:

- **qué** se construye y en qué orden;
- todo **DDL** sobre la base compartida (`CLAUDE.md` §9, sin excepción);
- los **merges a `desarrollo`, `Pruebas` y `produccion`**;
- las preguntas marcadas **CLARIFY** en las specs: son las que no se pueden
  responder mirando el código.

## Claude integra

- Elige la rama, mantiene los árboles separados y evita los choques con Anderson.
- Escribe la spec **antes** de implementar lo complejo, y la actualiza si la
  implementación se aparta. *Constitución IX.*
- Destila en el [[00-Inicio|Brain]] lo que costó descubrir, en el momento en que
  se descubre — no «después».
- Verifica antes de decir «listo»: build con base href correcto, assets que
  resuelven, tests, contraste, iconos.
- **Avisa** cuando algo requiere decisión de Alex, en vez de asumir.

## Lo que Claude NO hace sin preguntar

- DDL sobre la base compartida.
- Merge a `desarrollo`, `Pruebas` o `produccion`.
- `git push`.
- Borrar código que parezca muerto.
- Tocar `docker-compose.yml`, `nginx.conf`, `Dockerfile` o `.env`.

## La regla de fondo

> Si un paso del proceso obliga a Alex a acordarse de algo mecánico, el paso
> está mal diseñado. Se automatiza o se verifica solo.
>
> Por eso `npm run build` ya lleva `--base-href=/app/` y se autoverifica, y por
> eso hay un hook que bloquea `git add -A`: las dos veces que fallaron, fallaron
> por memoria.

Relacionado: [[Abiertos]] · [[Ambientes-y-despliegue]]
