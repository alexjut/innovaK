-- ─────────────────────────────────────────────────────────────────────────
-- 005 — Secuencias para tablas de curso/sesiones (PR-A módulo Curso Docente)
-- ─────────────────────────────────────────────────────────────────────────
-- Fecha: 2026-05-27
-- Contexto: las tablas `clase`, `horario_clase`, `asistencia_clase` y `grupo`
-- existen en BD con estructura razonable pero su PK `id` NO tiene secuencia
-- (deuda S5 del proyecto). Antes de poblarlas desde Django con managed=False,
-- conviene tener secuencias + DEFAULT nextval() — patrón canónico del
-- proyecto (CLAUDE.md §3: "MAX(id)+1 manual es deuda, prefiere secuencia BD").
--
-- Idempotente: CREATE SEQUENCE IF NOT EXISTS + setval al MAX actual antes
-- del DEFAULT, para que si la tabla tuviera filas (hoy todas en 0) las
-- nuevas inserciones no choquen con ids existentes.
--
-- Backup previo: poblacion_kennedy_pre_sesiones_20260527_162525.dump
-- Rollback: en 005_curso_sesiones_secuencias_rollback.sql
-- ─────────────────────────────────────────────────────────────────────────

BEGIN;

-- ── clase ────────────────────────────────────────────────────────────────
CREATE SEQUENCE IF NOT EXISTS clase_id_seq;
SELECT setval('clase_id_seq', COALESCE((SELECT MAX(id) FROM clase), 0) + 1, false);
ALTER TABLE clase ALTER COLUMN id SET DEFAULT nextval('clase_id_seq');
ALTER SEQUENCE clase_id_seq OWNED BY clase.id;

-- ── horario_clase ────────────────────────────────────────────────────────
CREATE SEQUENCE IF NOT EXISTS horario_clase_id_seq;
SELECT setval('horario_clase_id_seq', COALESCE((SELECT MAX(id) FROM horario_clase), 0) + 1, false);
ALTER TABLE horario_clase ALTER COLUMN id SET DEFAULT nextval('horario_clase_id_seq');
ALTER SEQUENCE horario_clase_id_seq OWNED BY horario_clase.id;

-- ── asistencia_clase ─────────────────────────────────────────────────────
CREATE SEQUENCE IF NOT EXISTS asistencia_clase_id_seq;
SELECT setval('asistencia_clase_id_seq', COALESCE((SELECT MAX(id) FROM asistencia_clase), 0) + 1, false);
ALTER TABLE asistencia_clase ALTER COLUMN id SET DEFAULT nextval('asistencia_clase_id_seq');
ALTER SEQUENCE asistencia_clase_id_seq OWNED BY asistencia_clase.id;

-- ── grupo ────────────────────────────────────────────────────────────────
CREATE SEQUENCE IF NOT EXISTS grupo_id_seq;
SELECT setval('grupo_id_seq', COALESCE((SELECT MAX(id) FROM grupo), 0) + 1, false);
ALTER TABLE grupo ALTER COLUMN id SET DEFAULT nextval('grupo_id_seq');
ALTER SEQUENCE grupo_id_seq OWNED BY grupo.id;

-- ── UNIQUE para evitar duplicar asistencia (clase_id, participante_id, fecha)
-- Una persona NO puede tener 2 marcas de asistencia para la misma clase y fecha.
CREATE UNIQUE INDEX IF NOT EXISTS ux_asistencia_clase_participante_fecha
  ON asistencia_clase (clase_id, participante_id, fecha);

-- ── Índices de lectura frecuente ─────────────────────────────────────────
CREATE INDEX IF NOT EXISTS ix_clase_evento ON clase (evento_id);
CREATE INDEX IF NOT EXISTS ix_horario_clase ON horario_clase (clase_id);
CREATE INDEX IF NOT EXISTS ix_asistencia_clase_fecha ON asistencia_clase (clase_id, fecha);
CREATE INDEX IF NOT EXISTS ix_asistencia_participante ON asistencia_clase (participante_id);
CREATE INDEX IF NOT EXISTS ix_evaluacion_evento ON evaluacion_participante (evento_id);
CREATE INDEX IF NOT EXISTS ix_evaluacion_participante ON evaluacion_participante (participante_id);

COMMIT;

-- Verificación post-aplicación:
--   SELECT pg_get_serial_sequence('clase', 'id');
--   SELECT pg_get_serial_sequence('horario_clase', 'id');
--   SELECT pg_get_serial_sequence('asistencia_clase', 'id');
--   SELECT pg_get_serial_sequence('grupo', 'id');
