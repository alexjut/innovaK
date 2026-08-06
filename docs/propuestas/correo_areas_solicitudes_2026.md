# Borrador de correo a las áreas — cómo pedir, qué hay hoy, y 2026

> **Borrador, 2026-08-06.** No enviado. Revisar destinatarios y firma.
>
> Va **uno por subgrupo**, con la ficha de esa área adjunta. La ficha la genera
> `scripts/ficha_area.py` **fuera del repositorio**: lleva números de contrato y
> objetos contractuales, y este repositorio es público.
>
> El cuerpo de abajo es el mismo para todas; solo cambia la ficha.

---

## Por qué este correo, y por qué ahora

Estamos a agosto y **el sistema no tiene un solo contrato de la vigencia 2026**.
Tiene 22 de 2025 (dos siguen con fecha de terminación futura), uno de 2024 y uno
de 2015. De eventos de 2026 hay **nueve en total**, todos de dos áreas.

No es que las áreas no estén trabajando: es que lo que hacen **no está llegando
al sistema**, o llega de una forma que no se puede enganchar. Y ahí está el
punto de fondo:

> **De los 24 contratos cargados, 20 no tienen CDP.** Sin CDP no hay proyecto, y
> sin proyecto no hay área: esos 20 contratos existen en el sistema pero **no se
> le pueden atribuir a nadie**. No es un error de captura — es que llegaron sin
> el dato que los conecta.

Por eso el correo no pide un reporte más. Pide **acordar cómo llegan las cosas**
antes de que 2026 termine como 2025.

---

**Para:** Coordinación de [SUBGRUPO]
**Copia:** Planeación · Presupuesto · Despacho
**Asunto:** Cómo radicar solicitudes ante el sistema · lo que hoy figura de su área · planeación 2026

---

Cordial saludo.

Escribimos a cada subgrupo por separado con tres propósitos concretos: dejar
claro **cómo deben llegarnos las solicitudes**, mostrarles **qué figura hoy en
el sistema a nombre de su área** —que en varios casos es poco o nada—, y
pedirles la información que necesitamos para que **2026 quede bien armado desde
el principio**.

## 1. Cómo debe llegar una solicitud

Todo lo que el área ejecuta tiene que poder rastrearse hasta la meta a la que
aporta y hasta la plata con que se pagó. Esa cadena es la que produce los
reportes, y **si falta un eslabón, lo ejecutado no aparece en ningún tablero
por más que se haya hecho**:

```
Proyecto → Meta → Indicador (KPI)
                        ↑
   CDP → Contrato → Actividad del plan → Evento → Beneficiarios
```

Cuando el área vaya a pedir algo —una actividad, una contratación, un evento,
una entrega— necesitamos, en este orden:

| # | Qué | Por qué |
|---|---|---|
| 1 | **Proyecto y meta** a la que aporta | sin esto no suma a nada |
| 2 | **Actividad del plan** dentro de ese proyecto | es lo que agrupa la ejecución |
| 3 | **CDP** que la respalda | es el eslabón que hoy falta en 20 de 24 contratos |
| 4 | **Contrato**, cuando exista | conecta la plata con la actividad |
| 5 | **Quién responde** por el área | para poder devolver preguntas |

**El punto 3 es el que más duele.** Un contrato que llega sin CDP no se puede
atribuir a un área ni a un proyecto: queda flotando. Si el CDP todavía no
existe, díganlo — se registra la solicitud como pendiente y se engancha después.
Lo que no funciona es que llegue sin mención alguna.

## 2. Lo que hoy figura de su área

**Ver la ficha adjunta.** Trae, con corte de hoy: proyectos, actividades del
plan, contratos que logramos atribuirle, eventos registrados y cuántos de ellos
son de 2026.

Si la ficha les parece corta o equivocada, esa es exactamente la conversación
que queremos tener. **Una ficha vacía no significa que el área no haya hecho
nada** — significa que lo que hizo no llegó al sistema, y eso es lo que hay que
corregir.

## 3. Lo que les pedimos

**a) ¿Qué información manejan hoy fuera del sistema?**
Planillas de Excel, listados de asistencia en papel, bases propias, carpetas
compartidas. No es para auditar a nadie: es para saber qué se puede cargar y en
qué formato llega. Si el área ya tiene el dato, no tiene sentido volver a
pedírselo a la ciudadanía.

**b) ¿Cómo va a ser 2026 para su área?**
Concretamente: qué actividades tienen previstas, con qué proyecto y meta,
cuántas personas esperan atender, y con qué contratos piensan pagarlo. Aunque
sea aproximado. Con eso podemos dejar creada la estructura **antes** de que
empiecen a ejecutar, y no reconstruyéndola en diciembre.

**c) ¿Quién es el responsable de datos del subgrupo?**
Una persona a la que podamos preguntarle. Hoy, cuando un dato no cuadra, no
sabemos a quién escribirle.

## 4. Qué ganan ustedes con esto

No es un trámite adicional. Con la cadena completa, el área obtiene sin pedirlo:

- **Su avance de metas en vivo**, sin armar el reporte a mano.
- **Cuánta plata tiene comprometida y cuánta libre**, por contrato.
- **A cuántas personas ha atendido**, con desagregación.
- El respaldo de que lo ejecutado **quedó registrado** — que es lo que se pide
  cuando llega una auditoría o un derecho de petición.

Hoy, la mayoría de las áreas no puede responder ninguna de esas cuatro cosas
desde el sistema.

## 5. Cómo responder

Basta con contestar este correo. Si prefieren reunión, la coordinamos por
subgrupo: son 30 minutos y sale más rápido que escribirlo. En ese caso solo
necesitaríamos la confirmación posterior por este medio, para que quede el
soporte.

Quedamos atentos.

Cordialmente,

**[Nombre]**
[Cargo] · Alcaldía Local de Kennedy

---

## Notas para quien envía (NO van en el correo)

- **44 subgrupos existen en el sistema; 37 no tienen absolutamente nada.** No
  tiene sentido escribirle a los 44: la lista real de destinatarios son los que
  ejecutan. Los siete con algún dato son Deporte, Cultura, Seguridad,
  Relacionamiento Interinstitucional, Educación, CPS y Planta, y Desarrollo
  Estratégico y Mejora.
- **Los dos contratos con fecha de terminación futura son de vigencia 2025**,
  no de 2026 — uno va hasta agosto de 2026 y otro hasta febrero. Conviene no
  llamarlos «vigentes 2026» en la conversación, porque no lo son.
- Hay **5 CDP** en el sistema, 4 de ellos de 2026. Es el único indicio de que
  2026 arrancó, y no está conectado a ningún contrato todavía.
- La ficha por área **no se commitea**: la genera `scripts/ficha_area.py` a un
  archivo fuera del repositorio. Lleva números y objetos de contrato.
