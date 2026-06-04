/**
 * Tipos TypeScript del módulo Jóvenes a la E.
 *
 * Reflejan el contrato JSON del backend
 * `apps/jovenes_a_la_e/api/serializers.py`.
 */

export type EntregaEstado = 'enviada' | 'validada' | 'rechazada';

/** Item de la lista paginada. */
export interface EntregaListItem {
  id: number;
  estado: EntregaEstado;
  created_at: string;
  updated_at: string | null;
  evento_id: number | null;
  evento_nombre: string;
  tipo_doc_codigo: string;
  numero_documento: string;
  nombre_completo: string;
  cumplimiento_acceso: boolean;
  cumplimiento_permanencia: boolean;
  nivel_formacion: string | null;
  convenio_codigo: string | null;
}

/** Elemento dotado (M2M con cantidad). */
export interface ElementoEntregado {
  codigo: string | null;
  nombre: string | null;
  cantidad: number;
}

/** Detalle completo (vista 360°). */
export interface EntregaDetail {
  id: number;
  estado: EntregaEstado;
  created_at: string;
  updated_at: string | null;
  evento: { id: number; nombre: string } | null;
  convenio_codigo: string | null;
  proyecto_codigo: string | null;
  metas_codigos: string | null;
  tipo_doc_codigo: string;
  numero_documento: string;
  nombre_completo: string;
  nombre1: string | null;
  nombre2: string | null;
  apellido1: string | null;
  apellido2: string | null;
  telefono: string | null;
  correo: string | null;
  direccion: string | null;
  barrio_codigo: string | null;
  barrio_nombre: string | null;
  upz_codigo: string | null;
  upl_codigo: string | null;
  upl_nombre: string | null;
  cumplimiento_acceso: boolean;
  cumplimiento_permanencia: boolean;
  metas_cumplidas: string[];
  nivel_formacion: string | null;
  nivel_formacion_label: string;
  institucion: string | null;
  programa_academico: string | null;
  periodo_academico: string | null;
  tiene_firma: boolean;
  firma_fecha: string | null;
  observaciones: string | null;
  elementos: ElementoEntregado[];
}

/** Respuesta paginada estándar de DRF. */
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** Filtros del listado. */
export interface EntregaFilters {
  estado?: EntregaEstado | '';
  evento?: number | null;
  q?: string;
  page?: number;
  page_size?: number;
}

/** Body para validar/rechazar. */
export interface EstadoUpdate {
  accion: 'validar' | 'rechazar';
  observaciones?: string;
}

/** Insights agregados (KPIs del módulo). */
export interface JovenesInsights {
  total: number;
  meta_acceso?: number;
  meta_permanencia?: number;
  meta_total?: number;
  funnel?: { borrador: number; enviada: number; validada: number; rechazada: number };
  cumplimiento?: {
    acceso: number;
    permanencia: number;
    ambos: number;
    solo_acceso: number;
    solo_permanencia: number;
  };
  avance_acceso_pct?: number;
  avance_permanencia_pct?: number;
  [extra: string]: unknown;
}
