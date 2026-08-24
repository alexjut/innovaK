# innovaK — Brain

Conocimiento **destilado** del sistema de la Alcaldía Local de Kennedy.
Vault de Obsidian: los enlaces internos arman el grafo.

> [!important] Qué es y qué no es
> - **No** es base de datos operacional. Cero datos de ciudadanos, cero secretos.
> - **No** duplica `docs/`. Las notas **apuntan** allá; si algo ya está bien
>   explicado, acá va el enlace y la idea en una frase.
> - **Sí** guarda lo que cuesta volver a descubrir: cardinalidades reales, por
>   qué se decidió algo, dónde miente un nombre.

Cada cifra dice **cómo se midió**. Si no se midió, se dice.

## Por dónde entrar

| Si buscas… | Empieza en |
|---|---|
| **el sistema completo** | [[Mapa-del-sistema]] — las 13 apps y qué hace cada una |
| qué significa cada cosa | [[Proyecto]] · [[Contrato]] · [[Meta]] · [[Indicador]] · [[Actividad]] · [[Subgrupo]] |
| cómo entran los datos del ciudadano | [[Captura-ciudadana]] |
| el territorio | [[Territorio]] |
| de dónde sale cada dato | [[Matriz-de-procedencia]] · [[SECOP]] · [[SEGPLAN]] · [[PDL]] · [[CDP-CRP]] · [[Precedencia-de-fuentes]] |
| cómo se enganchan las cosas | [[Contrato-Proyecto]] · [[Contrato-Meta]] |
| las pantallas | [[Mi-Area]] · [[Dashboard-360]] · [[Contraste-y-accesibilidad]] |
| quién puede qué | [[Permisos-y-roles]] · [[Scope-por-subgrupo]] · [[Auditoria]] |
| por qué no cascadean los ambientes | [[Ambientes-y-despliegue]] |
| decisiones cerradas | [[2026-08-24-contrato-meta-derivada]] · [[2026-08-24-precarga-antes-que-formulario]] · [[2026-08-24-auditoria-antes-que-captura]] |
| lo que está abierto | [[Abiertos]] |
| cómo nos repartimos el trabajo | [[Como-trabajamos]] |

## Cómo se usa

- **Antes de construir**, busca acá si ya está resuelto. *Constitución VIII.*
- **Después de descubrir algo que costó**, destílalo en una nota. No copies
  código: escribe la conclusión y enlaza al archivo.
- **Si una nota y el código se contradicen**, manda el código — y corrige la nota
  en el mismo momento. Una nota que envejece hace más daño que no tenerla.

## Fuentes de verdad fuera del Brain

| | |
|---|---|
| `CLAUDE.md` | cómo se trabaja en el repositorio — manda sobre todo |
| `.specify/memory/constitution.md` | qué se puede construir y cómo |
| `specs/` | comportamiento esperado de cada cambio complejo |
| `docs/RUMBO.md` | auditoría de 8 frentes con el orden de ataque |
| `docs/arquitectura/ARQUITECTURA.md` | la arquitectura mantenida |
| `docs/GLOSARIO.md` | vocabulario institucional |
| `docs/operacion/TRABAJO_EN_PARALELO.md` | reglas mientras se comparte una sola máquina |
