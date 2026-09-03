-- 022 · Objetivo Estratégico por meta — el tercer nivel de la jerarquía del PDL
--
-- POR QUÉ. La Matriz PDL trae, en la hoja «Seguimiento», dos columnas de
-- clasificación que hoy `metas` ya reconoce a medias:
--     Objetivo  Estrategico | Programa | Linea de Inversión | Concepto | ...
-- `Programa` YA vive en `metas.nomprog`/`codprog` (backfill de
-- `importar_matriz_pdl_alk` desde el día que se cargó la matriz). El nivel
-- de arriba —«Objetivo Estratégico», los 5 grandes ejes del Plan de
-- Desarrollo Local que agrupan los 22 programas— nunca se guardó: no hay
-- columna, verificado contra information_schema.
--
-- QUÉ ES. NO es el «área ejecutora» (dependencia, ya resuelta) ni el
-- «área PLANIG» (`AREA_PLANIG_POR_SUBGRUPO`, un mapa cosmético aparte). Es
-- la clasificación PROGRAMÁTICA del propio PDL: 5 objetivos, cada uno con
-- varios programas, cada programa con varias metas. Ejemplo real: la meta
-- 23772 (proyecto 2377, Educación) vive bajo «3 - Bogotá confía en su
-- potencial» → «16 - Atención Integral a la Primera Infancia y Educación
-- como Eje del Potencial Humano».
--
-- ADITIVO: una columna nueva sobre `metas`, la misma tabla que ya tiene
-- `sector`/`linea`/`concepto`/`componente`/`nomprog` del mismo origen.
-- Rollback en rollback_022_objetivo_estrategico.sql.

BEGIN;

ALTER TABLE metas
    ADD COLUMN IF NOT EXISTS objetivo_estrategico VARCHAR(200);

COMMENT ON COLUMN metas.objetivo_estrategico IS
    'Objetivo Estratégico del PDL 2025-2028 (columna "Objetivo  Estrategico" '
    'de la hoja Seguimiento, Matriz PDL ALK) — el nivel que agrupa los 22 '
    'programas de metas.nomprog en los 5 ejes del Plan. Backfill por '
    'codigo_meta exacto, vía importar_matriz_pdl_alk (mismo mecanismo que '
    'sector/linea/concepto/componente/nomprog, no la coincidencia de texto '
    'usada para la alerta de cumplimiento).';

COMMIT;
