/**
 * Tipos TypeScript del módulo Banco de Iniciativas.
 *
 * Reflejan el contrato JSON del backend DRF (Etapa B). Cuando se
 * habilite el codegen del OpenAPI (Java/Docker), estos tipos los
 * reemplazará el auto-generado en `src/app/api/`.
 */

/** Estado de una inscripción al Banco. */
export type InscripcionEstado = 'enviada' | 'validada' | 'rechazada';

/** Item de la lista paginada (subset de la inscripción completa). */
export interface InscripcionListItem {
  id: number;
  estado: InscripcionEstado;
  created_at: string;
  updated_at: string | null;
  evento_id: number | null;
  evento_nombre: string;
  numero_documento: string;
  nombre_completo: string;
  organizacion_nombre: string | null;
  upl_codigo: string | null;
  upl_nombre: string | null;
  total_personas: number | null;
}

/** Inscripción completa (vista 360°). */
export interface InscripcionDetail extends InscripcionListItem {
  // Datos de la persona representante.
  nombre1: string | null;
  nombre2: string | null;
  apellido1: string | null;
  apellido2: string | null;
  telefono: string | null;
  correo: string | null;
  direccion: string | null;
  barrio_codigo: string | null;
  barrio_nombre: string | null;
  // Datos del colectivo.
  organizacion_id: number | null;
  tipo_organizacion_codigo: string | null;
  redes_sociales: Record<string, string> | null;
  // Caracterización del proyecto.
  observaciones: string | null;
  enfoques: string[];
  escenarios: string[];
  implementos: string[];
  beneficios_alk: string[];
  // Firma.
  firma_mongo_id: string | null;
  firma_url: string | null;
}

/** Respuesta paginada estándar de DRF. */
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** Filtros del listado. */
export interface InscripcionFilters {
  estado?: InscripcionEstado | '';
  evento?: number | null;
  q?: string;
  page?: number;
  page_size?: number;
}

/** Body para validar/rechazar. */
export interface EstadoUpdate {
  estado: Extract<InscripcionEstado, 'validada' | 'rechazada'>;
  observacion?: string;
}

/** Insights agregados (KPIs del módulo). */
export interface BancoInsights {
  total: number;
  por_estado: Array<{ estado: string; count: number }>;
  por_mes: Array<{ mes: string; count: number }>;
  meta_convocatoria: number;
  porcentaje_avance: number;
  [extra: string]: unknown;
}
