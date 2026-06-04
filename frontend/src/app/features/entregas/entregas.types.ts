/**
 * Tipos TypeScript del módulo Entregas de insumos.
 *
 * Reflejan el contrato JSON del backend
 * `apps/entregas/api/serializers.py`.
 */

export type EntregaEstado = 'enviada' | 'validada' | 'rechazada';

/** Item de la lista paginada (EntregaInsumoListSerializer). */
export interface EntregaInsumoListItem {
  id: number;
  estado: EntregaEstado;
  created_at: string;
  updated_at: string | null;
  evento_id: number | null;
  evento_nombre: string;
  tipo_doc_codigo: string | null;
  numero_documento: string;
  nombre_completo: string;
}

/** Insumo entregado con cantidad (M2M a través de EntregaInsumoElemento). */
export interface ElementoEntregado {
  codigo: string | null;
  nombre: string | null;
  categoria: string | null;
  cantidad: number;
}

/** Detalle completo — vista 360° (EntregaInsumoDetailSerializer). */
export interface EntregaInsumoDetail {
  id: number;
  estado: EntregaEstado;
  created_at: string;
  updated_at: string | null;
  evento: { id: number; nombre: string } | null;
  tipo_doc_codigo: string | null;
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
  upl_codigo: string | null;
  upl_nombre: string | null;
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

/** Body para validar/rechazar (EntregaEstadoUpdateSerializer). */
export interface EstadoUpdate {
  accion: 'validar' | 'rechazar';
  observaciones?: string;
}
