# API pública de contratación — Alcaldía Local de Kennedy

Datos abiertos de la contratación de Kennedy, para que un tercero los consuma
igual que innovaK consume SECOP II de datos.gov.co.

## Lo que hay que saber antes de tocar esto

**Es la única superficie del sistema pensada para que la lea cualquiera.** Todo
lo demás de innovaK es interno. Acá cada campo que se agrega es una decisión
pública y difícil de revertir: un dato publicado se copia, se indexa y se cita.

Tres reglas que no se negocian:

1. **Ningún dato personal de persona natural sale sin decisión escrita.** El
   documento de un contratista persona natural es una cédula. Ver
   `services/contratos.py`, sección «datos personales».
2. **`null` nunca es `0`.** Un cero que en realidad significa «no sabemos» es
   una afirmación falsa sobre gasto público. Cada `null` viaja con su motivo.
3. **Ninguna cifra sin su corte.** `/metadatos/` declara de cuándo es el dato y
   qué cobertura tiene cada campo.
