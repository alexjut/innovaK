# Georreferenciación

Mapa de Kennedy, capas territoriales (UPZ, barrios, parques) y las escuelas de
Cultura y Deportes. El mapa es **público desde 2026-07-30**: se abre sin login,
salvo la capa de postulantes del Banco, que sigue cerrada.

> **Estado del trabajo en curso:** ver `ESTADO.md` en la raíz del worktree
> `mapa-escuelas`. Ahí está qué se aplicó en la base, qué falta y por dónde
> retomar.

---

## TODO — documentar las cifras de cobertura

TODO(pendiente 2026-07-30 · ver ESTADO.md §3) — falta escribir acá, en prosa y
para alguien que llegue de nuevo, las **dos cifras de cobertura de barrios**,
que son distintas y se confunden con facilidad:

- **155 de 325 barrios con geometría en la base = 47,7 %.**
- **222 polígonos visibles en el mapa**, porque el endpoint sirve la *unión* de
  la base más los sectores del archivo semilla que la base todavía no cubre.

No son la misma medida. La primera dice qué tan completa está la tabla; la
segunda, qué ve el ciudadano. Citar una por la otra ya causó un enredo.

Y falta dejar la **corrección histórica** con su fecha y su motivo:

> El "79 barrios sin geometría" viene del registro de **abril de 2026**, cuando
> la tabla tenía **111 filas**. Era correcto entonces. La tabla creció a **325**
> y ese número nunca se volvió a derivar: se arrastró como vigente hasta el
> 2026-07-30. **El dato correcto de partida era 250**, no 79.

Ese es el tipo de número mal arrastrado que conviene dejar documentado, no
corregido en silencio: sin la fecha y el denominador, el siguiente que lo lea
vuelve a citarlo mal.

---

## Regla que salió de ahí

**Toda cifra se reporta con su denominador y su fecha.** Un porcentaje sin
universo está incompleto, y un número heredado de un documento viejo se
re-deriva contra la base antes de usarlo.

En esta misma tarea se reportaron porcentajes territoriales calculados sobre
424 filas cuando el universo correcto eran las 278 activas — las otras 146
están dadas de baja y no se pintan en el mapa.
