-- 025 · La CARGA de la Matriz PDL — la pieza 3
--
-- POR QUÉ. Hoy la matriz entra por consola: `importar_matriz_pdl_alk`, seco por
-- defecto, idempotente, y deja UNA entrada en `auditoria_dato`. Funciona, pero
-- no hay entidad detrás. En concreto faltan cuatro cosas que el plan pide y que
-- no se pueden improvisar desde un comando:
--
--   1. RECHAZAR UN DUPLICADO. Sin hash del archivo, subir dos veces el mismo
--      corte es indistinguible de subir uno nuevo.
--   2. VER ANTES DE APLICAR. El diff (altas, cambios campo por campo, retiros,
--      filas con error) tiene que existir como dato guardado, no como texto
--      que pasó por una terminal y se perdió.
--   3. UN ESTADO. `borrador` → `aplicada` | `descartada`. Sin él no hay forma
--      de subir algo y decidirlo después, que es el flujo de tres pantallas.
--   4. DE QUÉ CARGA SALIÓ CADA FILA. Los DDL 023 y 024 ya dejaron
--      `carga_origen_id` / `carga_retiro_id` en sus tablas, como enteros
--      sueltos, esperando exactamente esta tabla. Acá se convierten en FK.
--
-- LA REGLA QUE ESTO HACE POSIBLE: **la carga nunca borra.** Lo que desaparece
-- de la matriz se marca `activo = FALSE` con la carga que lo retiró. Un DELETE
-- perdería la respuesta a «¿desde cuándo dejó de existir este programa?», que
-- es justo lo que un plan de desarrollo necesita poder contestar.
--
-- POR QUÉ EL HASH ES DEL ARCHIVO Y NO DEL CONTENIDO NORMALIZADO. Se quiere
-- detectar «este archivo ya lo subiste», no «estos datos ya los tenés». Un
-- Excel reguardado sin cambios de dato cambia de bytes, y tiene que poder
-- subirse: el diff dirá que no cambia nada, y esa es la respuesta correcta.
-- Rechazarlo por contenido escondería que la ALK mandó un corte nuevo.
--
-- ADITIVO: una tabla nueva y cuatro FK sobre columnas que YA existen y hoy
-- están todas en NULL, así que ninguna fila viola la restricción al crearse.
--
-- Rollback en rollback_025_matriz_carga.sql.

BEGIN;

CREATE TABLE IF NOT EXISTS presu_matriz_carga (
    id                SERIAL PRIMARY KEY,

    -- El archivo, tal como llegó.
    archivo_nombre    VARCHAR(255) NOT NULL,
    hash_sha256       CHAR(64)     NOT NULL,
    archivo_bytes     INTEGER,

    -- La fecha de corte que declara quien sube, NO la de subida: dos personas
    -- pueden subir el mismo corte en días distintos y sigue siendo ese corte.
    corte_oficial     DATE         NOT NULL,

    estado            VARCHAR(12)  NOT NULL DEFAULT 'borrador',

    -- El diff calculado en la previsualización, guardado tal cual se le mostró
    -- a quien decidió. JSONB y no texto: se consulta («¿qué cargas tocaron el
    -- programa 16?») sin volver a parsear el Excel.
    diff              JSONB,

    -- Contadores desnormalizados del diff, para listar sin abrirlo.
    n_altas           INTEGER      NOT NULL DEFAULT 0,
    n_cambios         INTEGER      NOT NULL DEFAULT 0,
    n_retiros         INTEGER      NOT NULL DEFAULT 0,
    n_errores         INTEGER      NOT NULL DEFAULT 0,

    subido_por_id     INTEGER,
    subido_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    aplicado_por_id   INTEGER,
    aplicado_at       TIMESTAMPTZ,
    nota              TEXT,

    -- El hash es único: subir el mismo archivo dos veces se rechaza en la
    -- base, no solo en la aplicación. Es la única garantía que sobrevive a que
    -- alguien llame al importador por otro camino.
    CONSTRAINT uq_presu_matriz_carga_hash UNIQUE (hash_sha256),

    CONSTRAINT ck_presu_matriz_carga_estado
        CHECK (estado IN ('borrador', 'aplicada', 'descartada')),

    -- Una carga aplicada tiene que decir cuándo. Sin esto, `estado` podría
    -- mentir y no habría forma de ordenar dos cargas del mismo día.
    CONSTRAINT ck_presu_matriz_carga_aplicada
        CHECK (estado <> 'aplicada' OR aplicado_at IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_presu_matriz_carga_estado
    ON presu_matriz_carga (estado);
CREATE INDEX IF NOT EXISTS idx_presu_matriz_carga_corte
    ON presu_matriz_carga (corte_oficial DESC);

COMMENT ON TABLE presu_matriz_carga IS
    'Una subida de la Matriz PDL: archivo, hash, corte declarado, diff y '
    'estado (borrador/aplicada/descartada). La carga NUNCA borra: lo que sale '
    'de la matriz se marca inactivo apuntando a la carga que lo retiro.';
COMMENT ON COLUMN presu_matriz_carga.hash_sha256 IS
    'SHA-256 del ARCHIVO, no del contenido normalizado: detecta "este archivo '
    'ya lo subiste". Un Excel reguardado sin cambios de dato cambia de bytes y '
    'debe poder subirse; el diff dira que no cambia nada.';
COMMENT ON COLUMN presu_matriz_carga.corte_oficial IS
    'Fecha de corte que declara quien sube, NO la fecha de subida.';

-- ─────────────────────────────────────────────────────────────────────────────
-- Las FK que los DDL 023 y 024 dejaron pendientes
-- ─────────────────────────────────────────────────────────────────────────────
-- Las cuatro columnas existen y están TODAS en NULL (el sembrado inicial no
-- vino de una carga registrada), así que ninguna fila viola la restricción al
-- crearse. ON DELETE SET NULL y no CASCADE: borrar una carga no puede llevarse
-- por delante los sectores y programas que trajo.
DO $$
DECLARE
    par RECORD;
BEGIN
    FOR par IN
        SELECT * FROM (VALUES
            ('presu_sector',               'carga_origen_id', 'fk_sector_carga_origen'),
            ('presu_sector',               'carga_retiro_id', 'fk_sector_carga_retiro'),
            ('presu_objetivo_estrategico', 'carga_origen_id', 'fk_objetivo_carga_origen'),
            ('presu_objetivo_estrategico', 'carga_retiro_id', 'fk_objetivo_carga_retiro'),
            ('presu_programa',             'carga_origen_id', 'fk_programa_carga_origen'),
            ('presu_programa',             'carga_retiro_id', 'fk_programa_carga_retiro')
        ) AS t(tabla, columna, restriccion)
    LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_schema = 'public' AND table_name = par.tabla)
           AND NOT EXISTS (SELECT 1 FROM information_schema.table_constraints
                           WHERE constraint_name = par.restriccion)
        THEN
            EXECUTE format(
                'ALTER TABLE %I ADD CONSTRAINT %I FOREIGN KEY (%I) '
                'REFERENCES presu_matriz_carga (id) ON DELETE SET NULL',
                par.tabla, par.restriccion, par.columna);
        END IF;
    END LOOP;
END $$;

COMMIT;
