-- 012_auditoria_dato.sql — el rastro de todo dato que escribe una persona.
--
-- POR QUÉ HACE FALTA (medido 2026-08-24, no supuesto):
--   · Barrido de las 268 tablas por `auditor|audit|bitacora|historial|log_`:
--     sólo `auditoria_pertenencia`, que es de PERMISOS (quién entró a qué
--     grupo). No sirve para datos.
--   · Lo que hay es rastro POR CAMPO, cosido a mano donde alguien se acordó:
--     `contrato.etapa_fecha` + `etapa_usuario_id`, y `created_at/updated_at`
--     sueltos en algunos modelos. Funciona para un campo y no escala a once.
--   · Sobre información contractual, un dato sin autor ni fecha no se puede
--     defender ante un ente de control. No es una mejora: es el requisito.
--
-- Va ANTES que los formularios a propósito. Si los campos de captura nacen
-- primero, nacen sin rastro y después nadie vuelve.
--
-- ADITIVA Y NO DESTRUCTIVA: crea una tabla nueva. No toca, no altera y no
-- borra nada de lo que ya existe. Su rollback es un DROP de lo que ella misma
-- creó.

BEGIN;

CREATE TABLE IF NOT EXISTS auditoria_dato (
    id              bigserial    PRIMARY KEY,

    -- QUIÉN y CUÁNDO. `usuario_id` sin FK formal a propósito: el resto del
    -- esquema hace lo mismo (`contrato.etapa_usuario_id`) y una FK real
    -- impediría borrar un usuario sin perder su rastro — que es justo lo que
    -- una auditoría no puede permitir.
    usuario_id      integer      NOT NULL,
    usuario_nombre  varchar(150),          -- congelado al momento del cambio
    fecha           timestamptz  NOT NULL DEFAULT now(),

    -- QUÉ se tocó. `entidad` es el nombre de la tabla; `entidad_id` su llave.
    entidad         varchar(60)  NOT NULL,
    entidad_id      bigint       NOT NULL,
    campo           varchar(60)  NOT NULL,

    -- El CONTEXTO institucional, denormalizado a propósito. Sin esto, saber a
    -- qué proyecto pertenece un cambio de hace dos años exige reconstruir
    -- relaciones que para entonces pueden haber cambiado. Una auditoría tiene
    -- que poder leerse sola.
    proyecto_id     integer,
    contrato_id     integer,
    subgrupo_id     integer,

    -- EL CAMBIO. Texto y no jsonb: lo que se guarda es cómo se veía el dato,
    -- no una estructura para consultar. NULL en `valor_anterior` significa que
    -- el campo estaba vacío — distinto de la cadena '0', que es un cero real.
    valor_anterior  text,
    valor_nuevo     text,

    -- DE DÓNDE VINO. Distingue «lo escribió una persona» de «llegó de SECOP»,
    -- que es lo que sostiene la regla de precedencia de fuentes.
    fuente          varchar(30)  NOT NULL DEFAULT 'MANUAL',
    observacion     text
);

COMMENT ON TABLE auditoria_dato IS
    'Rastro de cambios sobre datos institucionales. Aditiva: no se actualiza ni se borra.';
COMMENT ON COLUMN auditoria_dato.fuente IS
    'MANUAL | SECOP | SEGPLAN | BOGDATA | SISTEMA. Sostiene la precedencia de fuentes.';
COMMENT ON COLUMN auditoria_dato.valor_anterior IS
    'NULL = el campo estaba vacío. La cadena ''0'' es un cero real, no una ausencia.';

-- Los tres accesos que la pantalla necesita, y ninguno más: un índice que
-- nadie usa se paga en cada INSERT y esta tabla sólo crece.
CREATE INDEX IF NOT EXISTS idx_auditoria_dato_entidad
    ON auditoria_dato (entidad, entidad_id, fecha DESC);
CREATE INDEX IF NOT EXISTS idx_auditoria_dato_contrato
    ON auditoria_dato (contrato_id, fecha DESC) WHERE contrato_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_auditoria_dato_usuario
    ON auditoria_dato (usuario_id, fecha DESC);

COMMIT;
