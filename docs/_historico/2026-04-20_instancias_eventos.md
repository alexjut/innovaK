# Requisito nuevo: Instancias de eventos

## Fecha: 2026-04-20 (noche)

## Contexto

Usuario Javier Alexander Aguilar identificó que los eventos en innovaK
necesitan agrupar participantes por "instancias" — grupos de personas u
organizaciones que participan colectivamente en un evento.

## Modelo conceptual

```
Evento 1 ──tiene N──► Instancia
```

Una Instancia:

- Agrupa personas (M2M con Persona) Y/O
- Agrupa organizaciones (M2M con Organizacion)

## Respuestas del usuario (intuición inicial 2026-04-20)

1. **Cardinalidad**: un evento tiene VARIAS instancias (1:N).
2. **Contenido**: las instancias agrupan personas Y organizaciones
   (pueden coexistir).
3. **Multi-pertenencia**: una persona PUEDE estar en varias instancias
   del mismo evento (roles distintos: participante, organizador,
   logística).

## Ejemplo concreto

Evento: "Feria de emprendimiento Kennedy 2026"

Instancias posibles:

- "Mujeres cabeza de hogar - Patio Bonito" (15 personas)
- "Asociación Comerciantes Calle 38" (8 organizaciones)
- "Jóvenes emprendedores Kennedy" (22 personas)

## 7 decisiones técnicas pendientes

1. **Naming**: ¿por qué "instancia" y no "grupo"? ¿Viene de SIPSE?
2. **Reusabilidad**: ¿instancias reutilizables entre eventos o únicas
   por evento?
3. **Atributos de Instancia**: cupo máx, responsable, localidad, tipo,
   descripción, estado.
4. **Jerarquía**: ¿sub-instancias o estructura plana?
5. **Relación con Persona/Organizacion**: M2M con through; rol (líder,
   participante, suplente).
6. **Inscripción**: ¿cómo se inscribe? ¿QR de evento o de instancia?
   ¿Excel masivo?
7. **UI**: ¿crear instancias al crear evento o después? ¿editar
   después?

## Impacto en el modelo de datos

- Tabla nueva `instancia` (managed=False).
- Tabla nueva `instancia_persona` (M2M through).
- Posible tabla `instancia_organizacion` (M2M si aplica).
- Sin cambios en Evento (Instancia apunta a Evento).
- Cambios en UI + views + URLs + admin.

## Estimación: 1 semana de trabajo concentrado

## Prioridad

Decisión pendiente. NO bloquea el refactor de `crear_evento` actual.

## Siguiente paso

Coordinar reunión con Alex para resolver las 7 decisiones técnicas.
