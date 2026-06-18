-- 008_clase_dictada_por.sql
-- Registra QUIÉN dictó cada sesión del curso (titular o suplente).
--
-- Contexto: el curso (Evento) tiene un docente titular en
-- evento.funcionario_id. Pero una sesión puntual la puede dictar un
-- suplente (el supervisor lo asigna, p. ej. cuando el titular falta).
-- Esta columna registra el funcionario que REALMENTE dictó la sesión.
-- Si queda NULL, se asume que la dictó el titular del curso.
--
-- FK blanda a funcionario(id) ON DELETE SET NULL (un funcionario borrado
-- no debe tumbar el histórico de sesiones).
--
-- BD externa, managed=False. Aplicar con backup < 24h. Confirmar con Alex.

ALTER TABLE clase
    ADD COLUMN IF NOT EXISTS dictada_por_id INTEGER;

ALTER TABLE clase
    ADD CONSTRAINT fk_clase_dictada_por
    FOREIGN KEY (dictada_por_id) REFERENCES funcionario (id)
    ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_clase_dictada_por ON clase (dictada_por_id);
