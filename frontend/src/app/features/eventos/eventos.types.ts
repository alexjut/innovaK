/**
 * Tipos del módulo Eventos. Lectura desde el listado paginado del
 * backend (apps/login/views/eventos/). Etapa B aún no expone una API
 * REST completa de Evento (solo /api/eventos/<id>/inscripciones/),
 * así que este feature consume el listado HTML legacy parseado o
 * un endpoint público mínimo cuando exista.
 *
 * Estructura mínima — se expandirá cuando llegue el endpoint DRF.
 */

export interface EventoItem {
  id: number;
  nombre: string | null;
  tipo_evento_id: string | null;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  activo: boolean;
  subgrupo_nombre: string | null;
  funcionario_nombre: string | null;
  inscritos_count?: number;
  [extra: string]: unknown;
}
