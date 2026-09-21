-- 030 — Rastro de quién consultó la identificación de un contratista.
--
-- El endpoint interno entrega NOMBRE y DOCUMENTO de personas naturales a otro
-- equipo del Distrito. Eso es tratamiento de datos personales (Ley 1581), y la
-- Alcaldía tiene que poder responder QUIÉN consultó QUÉ y CUÁNDO. Sin esta
-- tabla, la respuesta sería «no sabemos», que es la peor de todas.
--
-- Se guarda el NOMBRE del consumidor, nunca su token. Y se registra el hecho
-- del acceso —a qué contrato— no el dato entregado: duplicar la cédula en una
-- bitácora sería multiplicar el problema que se está cuidando.

BEGIN;

CREATE TABLE IF NOT EXISTS acceso_identificacion (
    id              bigserial PRIMARY KEY,
    consumidor      text NOT NULL,
    ip              inet,
    id_contrato     text NOT NULL,
    -- `false` cuando se rechazó (token o IP inválidos): un intento fallido es
    -- justo lo que hay que poder auditar.
    concedido       boolean NOT NULL DEFAULT true,
    motivo_rechazo  text,
    consultado_en   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_acceso_ident_fecha
    ON acceso_identificacion (consultado_en DESC);
CREATE INDEX IF NOT EXISTS ix_acceso_ident_consumidor
    ON acceso_identificacion (consumidor, consultado_en DESC);

COMMENT ON TABLE acceso_identificacion IS
    'Bitácora de acceso a datos personales de contratistas (Ley 1581). No guarda el dato entregado ni el token.';

COMMIT;
