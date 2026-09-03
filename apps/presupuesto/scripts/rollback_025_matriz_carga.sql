-- Rollback del 025 · la carga de la Matriz PDL
--
-- ORDEN: primero las seis FK que apuntan a `presu_matriz_carga`, después la
-- tabla. Al revés, el DROP chocaría con ellas.
--
-- Las columnas `carga_origen_id` / `carga_retiro_id` NO se sueltan: pertenecen
-- a los DDL 023 y 024, que siguen en pie. Vuelven a ser enteros sueltos, que es
-- exactamente como nacieron.
--
-- ⚠️ Este rollback PIERDE las cargas registradas y sus diffs. Si hay alguna
-- fila en `presu_matriz_carga`, exportarla antes: no se puede reconstruir a
-- partir de los datos que dejó.

BEGIN;

ALTER TABLE IF EXISTS presu_sector
    DROP CONSTRAINT IF EXISTS fk_sector_carga_origen,
    DROP CONSTRAINT IF EXISTS fk_sector_carga_retiro;

ALTER TABLE IF EXISTS presu_objetivo_estrategico
    DROP CONSTRAINT IF EXISTS fk_objetivo_carga_origen,
    DROP CONSTRAINT IF EXISTS fk_objetivo_carga_retiro;

ALTER TABLE IF EXISTS presu_programa
    DROP CONSTRAINT IF EXISTS fk_programa_carga_origen,
    DROP CONSTRAINT IF EXISTS fk_programa_carga_retiro;

DROP TABLE IF EXISTS presu_matriz_carga;

COMMIT;
