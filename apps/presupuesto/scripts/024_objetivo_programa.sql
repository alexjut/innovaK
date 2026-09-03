-- 024 · Objetivo Estratégico y Programa como TABLAS — la pieza 2
--
-- POR QUÉ. Los dos niveles de arriba de la jerarquía del PDL viven hoy como
-- texto suelto, repetido en dos tablas:
--
--     metas.objetivo_estrategico   VARCHAR   (DDL 022)
--     metas.codprog / metas.nomprog          (backfill del importador)
--     sdp_meta_oficial.objetivo / .programa  (espejo de SDP)
--
-- Cuatro copias del mismo nombre, sin nada que garantice que digan lo mismo.
-- Y no hay dónde colgar `activo`, así que la regla «la carga nunca borra» no
-- tiene dónde escribirse: si la ALK retira un programa, hoy simplemente deja
-- de aparecer en el texto y nadie se entera.
--
-- LO QUE NO ES. La tabla `objetivo` (6 filas, de las cuales 4 se llaman
-- «prueba») NO es esta: es el catálogo de objetivos del Banco de Iniciativas,
-- otro dominio. Y `programas` (7 filas, con 5 de 31 proyectos enganchados)
-- tampoco: `proyecto.programa_id` apunta ahí y no son los 22 programas del
-- PDL. Por eso van tablas nuevas con prefijo `presu_` y no un backfill de las
-- existentes, que significan otra cosa.
--
-- LA FORMA, MEDIDA CONTRA EL ARCHIVO (2026-09-03, hoja «Seguimiento»):
--
--     5 objetivos   códigos 1..5, densos
--    22 programas   códigos 1,2,3,4,5,7,10,12,…,39 — ESPARCIDOS: son la
--                   numeración distrital del PDL, no un consecutivo local
--    78 metas       16+25+7+16+14 por objetivo, cuadra
--
-- Cada programa cuelga de UN solo objetivo — verificado, cero programas con
-- dos padres—, así que la FK va en `presu_programa` y no hace falta una tabla
-- puente. Y los 27 nombres parsean como «N - nombre», así que el código sale
-- del propio texto y no hay que inventarlo.
--
-- POR QUÉ `codigo` ES ENTERO Y ÚNICO GLOBAL. Los 22 códigos de programa no se
-- repiten entre objetivos (verificado). Si algún día se repitieran, el UNIQUE
-- avisaría en la carga en vez de dejar dos programas distintos con el mismo
-- número conviviendo en silencio.
--
-- ADITIVO. Dos tablas nuevas y UNA columna nullable en `metas`. Ni
-- `objetivo_estrategico` ni `codprog`/`nomprog` se tocan: se conservan hasta
-- que los lectores se muden, y se borran en una pasada posterior.
--
-- Rollback en rollback_024_objetivo_programa.sql.

BEGIN;

CREATE TABLE IF NOT EXISTS presu_objetivo_estrategico (
    id              SERIAL PRIMARY KEY,
    codigo          INTEGER      NOT NULL,
    nombre          VARCHAR(200) NOT NULL,
    activo          BOOLEAN      NOT NULL DEFAULT TRUE,

    -- La carga que lo trajo y la que lo retiró. La carga NUNCA borra: marca
    -- inactivo. Enteros sueltos hasta que exista `MatrizPDLCarga`.
    carga_origen_id INTEGER,
    carga_retiro_id INTEGER,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_presu_objetivo_codigo UNIQUE (codigo)
);

COMMENT ON TABLE presu_objetivo_estrategico IS
    'Los 5 ejes del PDL 2025-2028. Salen de la columna "Objetivo Estrategico" '
    'de la hoja Seguimiento de la Matriz PDL. NO confundir con la tabla '
    '"objetivo", que es del Banco de Iniciativas.';

CREATE TABLE IF NOT EXISTS presu_programa (
    id              SERIAL PRIMARY KEY,
    codigo          INTEGER      NOT NULL,
    nombre          VARCHAR(250) NOT NULL,

    -- NOT NULL: un programa sin objetivo no existe en el PDL, y permitir el
    -- hueco invitaría a cargar filas a medias que después nadie repara.
    objetivo_id     INTEGER      NOT NULL
                    REFERENCES presu_objetivo_estrategico (id),

    activo          BOOLEAN      NOT NULL DEFAULT TRUE,
    carga_origen_id INTEGER,
    carga_retiro_id INTEGER,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_presu_programa_codigo UNIQUE (codigo)
);

CREATE INDEX IF NOT EXISTS idx_presu_programa_objetivo
    ON presu_programa (objetivo_id);

COMMENT ON TABLE presu_programa IS
    'Los 22 programas del PDL 2025-2028, cada uno bajo UN objetivo. Los '
    'codigos son la numeracion distrital (esparcida: 1,2,3,4,5,7,10,...,39), '
    'no un consecutivo local. NO confundir con la tabla "programas".';

-- ─────────────────────────────────────────────────────────────────────────────
-- El enganche en `metas`
-- ─────────────────────────────────────────────────────────────────────────────
-- El objetivo NO lleva columna propia en `metas`: se llega por
-- programa → objetivo. Duplicar la FK permitiría que una meta declarara un
-- objetivo distinto al de su programa, que es exactamente la incoherencia que
-- este DDL viene a cerrar.
ALTER TABLE metas
    ADD COLUMN IF NOT EXISTS programa_id INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_metas_programa'
    ) THEN
        ALTER TABLE metas
            ADD CONSTRAINT fk_metas_programa
            FOREIGN KEY (programa_id) REFERENCES presu_programa (id)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_metas_programa_id ON metas (programa_id);

COMMENT ON COLUMN metas.programa_id IS
    'Programa del PDL (presu_programa). Se llena desde la Matriz por la llave '
    'estable (proyecto_codigo, codind). El objetivo se alcanza por '
    'programa -> objetivo, sin columna propia, para que una meta no pueda '
    'declarar un objetivo distinto al de su programa.';

COMMIT;
