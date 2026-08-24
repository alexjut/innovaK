# Ambientes y despliegue

> [!danger] Los ambientes no divergen: NO EXISTEN
> Medido el 2026-08-24.

## La evidencia

1. `desarrollo`, `Pruebas` y `produccion` comparten el **mismo hash de árbol**
   (`0831ed0f…`). `git diff` entre cualquier par: **cero**. Los commits de
   «adelanto» son sólo merges.
2. Hay **un** checkout del repositorio en el host y **un** contenedor.
3. `docker-compose.yml` monta el código: `volumes: - .:/app`. El contenedor
   sirve **el working tree**, sea cual sea la rama checkouteada.
4. **No hay CI.** Sólo un hook local `pre-push`.

## Por qué «no cascadean» los cambios de frontend

**`frontend/dist` está gitignored** — 0 archivos en el índice, 147 en disco. Y
`apps/login/views/spa.py` sirve la SPA leyendo esa carpeta del filesystem.

O sea: **el frontend no viaja con el repositorio.** Hay que rebuildearlo a mano
en cada máquina. Por eso lo que «no aparece» es siempre lo mismo —dashboard,
estilos, accesibilidad— y el backend sí, porque está bind-mounteado.

El dossier de k8s ya lo advertía el 2026-06-24:
*«El Dockerfile no compila la SPA Angular»*. Nadie lo actuó.

## El error que tumba la aplicación sin parecer un error

Un build sin `--base-href=/app/` deja el `index.html` pidiendo los assets en la
raíz del dominio → 404 → **pantalla en blanco para todos**. Y mientras tanto:

- el contenedor sigue `Up (healthy)`;
- `/app/` responde **200**;
- el build compila **limpio**.

Pasó el 2026-06-18 y **volvió a pasar el 2026-08-24**. Por eso `npm run build`
ya lleva la bandera y verifica solo. Ver `docs/operacion/TRABAJO_EN_PARALELO.md`.

## Adónde hay que llegar

```
commit SHA → build → tests → Development → Testing → Production
```

Mismo **artefacto** promovido, no recompilado por ambiente. Diferencias sólo en
variables de entorno, nunca en código de rama distinta. Y poder responder
«¿qué versión corre cada ambiente?» con un SHA.

> [!warning] La BD es única y compartida
> `managed=False`, PostgreSQL externa. **No hay base por ambiente**: un DDL
> afecta a los tres a la vez. Separar ambientes es infraestructura nueva, no un
> cambio de código.

Relacionado: [[Dashboard-360]] · [[Mi-Area]]
