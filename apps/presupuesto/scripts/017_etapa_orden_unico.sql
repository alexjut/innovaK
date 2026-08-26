-- 017_etapa_orden_unico.sql — dos etapas no pueden ocupar el mismo puesto.
--
-- POR QUÉ. `etapa_contrato.orden` es lo que dibuja el stepper: la pantalla
-- ordena por ese número, no por el código. Hoy nada impide insertar dos etapas
-- con el mismo `orden`, y si pasa, PostgreSQL las devuelve en un orden no
-- determinista: el stepper pintaría dos nodos intercambiándose de puesto entre
-- una carga y otra, sin que nadie sepa por qué. Verificado: la tabla solo tiene
-- PRIMARY KEY (codigo) y UNIQUE (nombre).
--
-- DEFERRABLE INITIALLY DEFERRED, y esto es lo importante:
--
-- Un UNIQUE normal rompería el reordenamiento obvio —`UPDATE etapa_contrato
-- SET orden = orden + 1 WHERE orden >= 2`— porque PostgreSQL comprueba fila por
-- fila y a mitad del UPDATE hay dos filas con el mismo orden aunque al final no
-- quede ninguna. Sería una restricción que impide justo la operación legítima
-- que uno querría hacer sobre esta tabla.
--
-- Diferida, la comprobación ocurre AL HACER COMMIT: los estados intermedios se
-- permiten y lo que se garantiza es que en reposo nunca hay dos etapas en el
-- mismo puesto. Que es exactamente el invariante, ni más ni menos.
--
-- ADITIVA: no toca ni una fila. Si hubiera duplicados previos el ALTER falla y
-- no deja nada a medias — se comprueba antes para poder decir cuáles son.

BEGIN;

DO $$
DECLARE dup text;
BEGIN
    SELECT string_agg(orden::text, ', ') INTO dup
      FROM (SELECT orden FROM etapa_contrato
            GROUP BY orden HAVING count(*) > 1) t;
    IF dup IS NOT NULL THEN
        RAISE EXCEPTION 'Ya hay etapas repitiendo el orden: %. Arreglalas antes.', dup;
    END IF;
END $$;

ALTER TABLE etapa_contrato
    ADD CONSTRAINT etapa_contrato_orden_key UNIQUE (orden)
    DEFERRABLE INITIALLY DEFERRED;

COMMIT;
