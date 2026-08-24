# Precedencia de fuentes

Regla por campo, no global:

```
FUENTE OFICIAL  >  DATO INTERNO VALIDADO  >  CAPTURA MANUAL
```

## Cómo se aplica

1. **Si hay fuente oficial** para el campo: se precarga y **no se edita**. La
   pantalla muestra de dónde viene (`SECOP ✓`).
2. **Si no la hay**: nace `Pendiente`, lo completa quien está autorizado, y
   queda [[Auditoria|auditado]].
3. **Una captura manual NUNCA sobrescribe en silencio una fuente oficial.** Si
   llega el dato oficial y difiere de lo capturado, gana el oficial y la
   diferencia se registra — no se pisa y ya.

## Por qué importa acá

Lo que hoy está vacío casi nunca es «nadie lo escribió»: es que **nadie miró la
fuente**. Los 25 contratistas faltantes están los 25 en `secop_contrato`. Antes
de pedirle un dato a un funcionario, hay que agotar la fuente.

Relacionado: [[Matriz-de-procedencia]] · [[SECOP]] · [[Auditoria]]
