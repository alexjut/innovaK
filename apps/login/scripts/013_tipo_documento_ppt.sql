-- 013 — Agrega el PPT al catálogo `tipo_documento`.
--
-- NO ES DDL: es un INSERT en un catálogo de 6 filas. Aun así lo aplica Alex
-- (o Claude con su OK explícito), porque escribe en la base compartida.
-- Decisión de Alex, 2026-08-12.
--
-- POR QUÉ. El **Permiso por Protección Temporal** es un documento de identidad
-- oficial de Migración Colombia, y en Kennedy hay población migrante. El
-- catálogo solo tenía CC, TI, CE, PA, NIT y «Otro», así que un PPT solo podía
-- entrar como «Otro» —perdiendo el dato— o, peor, colapsado en cédula. Con
-- cualquiera de las dos, un reporte de población migrante pedido después es
-- irreconstruible: la información ya no está.
--
-- El caso que lo destapó: el archivo de beneficiarios de educación posmedia
-- 2025 trae al menos un PPT (de 7 dígitos, no 10 — no asuma longitud fija).
--
-- ALCANCE. `tipo_documento` lo referencian cuatro tablas por FK
-- (`persona_documento`, `beneficiario`, `crp`, `inscripcion_banco_iniciativa`).
-- Agregar una fila es aditivo: ninguna fila existente cambia y ninguna FK se
-- invalida. La fila nueva aparecerá en los desplegables que listan el catálogo,
-- que es justamente lo que se busca.
--
-- `codigo` es PK sin secuencia (no tiene DEFAULT), así que va explícito. Se usa
-- el 7 porque el máximo actual es 6; el `WHERE NOT EXISTS` lo hace idempotente.

INSERT INTO tipo_documento (codigo, nombre, descripcion)
SELECT 7,
       'Permiso por Protección Temporal',
       'PPT — documento de identificación de Migración Colombia para población '
       'migrante venezolana con estatus de protección temporal.'
 WHERE NOT EXISTS (SELECT 1 FROM tipo_documento WHERE codigo = 7);
