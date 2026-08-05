-- =====================================================================
-- Módulo Educación — DDL-2: categoría 'educativo' en el catálogo compartido
--
-- Va en script aparte del 001 a propósito: 001 solo CREA tablas nuevas y no
-- toca nada existente. Esto sí modifica un objeto compartido (`implemento`,
-- que usa el Banco de Iniciativas de Deportes y el módulo Entregas), y esa
-- diferencia de riesgo merece poder aplicarse y revertirse por separado.
--
-- POR QUÉ categoría propia y no 'general':
--   El catálogo nació para Deportes. Si los insumos de Educación entran como
--   'general', aparecen en los filtros del Banco como si fueran suyos. Una
--   categoría propia los deja comparables (mismo catálogo, mismas cifras) sin
--   ensuciar la vista de la otra área.
--
-- DOS COSAS QUE SE DESCUBRIERON AL APLICAR (2026-08-05) y que explican la forma
-- rara del INSERT:
--   1. `implemento.codigo` es identity GENERATED ALWAYS → no se le puede pasar
--      un código; hay que omitir la columna y dejar que la BD lo asigne.
--   2. `implemento_categoria_check` restringe la categoría a cuatro valores.
--      De ahí el ALTER de abajo.
--   Existe además UNIQUE (nombre, categoria), que es lo que hace idempotente
--   al INSERT sin necesidad de un NOT EXISTS.
--
-- APLICAR tras backup < 24 h (~/Proyectos/postgres/backup_postgres.sh).
-- REVERSA al final del archivo.
-- =====================================================================
BEGIN;

-- Aditivo: los cuatro valores que ya existían siguen siendo válidos, así que
-- ninguna fila actual queda en violación.
ALTER TABLE implemento DROP CONSTRAINT IF EXISTS implemento_categoria_check;
ALTER TABLE implemento ADD CONSTRAINT implemento_categoria_check
    CHECK (categoria IN ('deportivo', 'tecnologico', 'logistico',
                         'general', 'educativo'));

INSERT INTO implemento (nombre, categoria, activo, orden)
SELECT v.nombre, 'educativo', TRUE, 1000 + v.n * 10
FROM (VALUES
    (1, 'Dotación de aula'),
    (2, 'Material didáctico'),
    (3, 'Textos y material de lectura'),
    (4, 'Equipos de cómputo'),
    (5, 'Mobiliario escolar'),
    (6, 'Kit escolar'),
    (7, 'Instrumentos musicales'),
    (8, 'Implementación deportiva escolar'),
    (9, 'Insumos de laboratorio'),
    (10, 'Otro insumo educativo')
) AS v(n, nombre)
ON CONFLICT (nombre, categoria) DO NOTHING;

COMMIT;

-- =====================================================================
-- REVERSA (si hay que deshacer):
--   BEGIN;
--   DELETE FROM implemento WHERE categoria = 'educativo';
--   ALTER TABLE implemento DROP CONSTRAINT implemento_categoria_check;
--   ALTER TABLE implemento ADD CONSTRAINT implemento_categoria_check
--       CHECK (categoria IN ('deportivo','tecnologico','logistico','general'));
--   COMMIT;
-- Ojo: el DELETE falla si alguna entrega ya referencia uno de esos códigos
-- (FK desde entrega_insumo_colegio). Eso es deliberado — no se borra un
-- catálogo que ya tiene datos colgando.
-- =====================================================================
