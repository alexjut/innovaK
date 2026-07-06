-- ============================================================================
-- ONBOARDING guiado (mascota Kenny) — progreso de tours por usuario.
-- Modelo Django managed=False: OnboardingProgreso.
-- PK BIGSERIAL. NO aplicar sin backup < 24h + confirmación explícita de Alex.
-- Rollback: 001_onboarding_setup_rollback.sql
-- ============================================================================

CREATE TABLE IF NOT EXISTS onboarding_progreso (
    id          BIGSERIAL PRIMARY KEY,
    usuario_id  INTEGER     NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    tour_id     VARCHAR(64) NOT NULL,
    completado  BOOLEAN     NOT NULL DEFAULT FALSE,
    fecha       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_onboarding_usuario_tour UNIQUE (usuario_id, tour_id)
);

CREATE INDEX IF NOT EXISTS idx_onboarding_usuario ON onboarding_progreso(usuario_id);
