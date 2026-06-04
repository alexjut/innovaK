/**
 * Tipos TypeScript del módulo Banco de Iniciativas.
 *
 * Reflejan el contrato JSON REAL del backend DRF
 * (apps/banco_iniciativas/api/serializers.py + views.py).
 */

/** Estado de una inscripción al Banco. */
export type InscripcionEstado = 'borrador' | 'enviada' | 'validada' | 'rechazada';

/** Item de la lista paginada (InscripcionListSerializer). */
export interface InscripcionListItem {
  id: number;
  estado: InscripcionEstado;
  created_at: string;
  updated_at: string | null;
  evento_id: number | null;
  evento_nombre: string;
  organizacion_id: number | null;
  organizacion_nombre: string | null;
  organizacion_nit: string | null;
  rep_nombre: string | null;
  rep_numero_doc: string | null;
  upl: string | null;
  disciplina_principal: string | null;
}

/** Inscripción completa (InscripcionDetailSerializer, vista 360°). */
export interface InscripcionDetail {
  id: number;
  estado: InscripcionEstado;
  created_at: string;
  updated_at: string | null;
  evento: { id: number; nombre: string } | null;
  organizacion: { id: number; nombre: string; nit: string | null } | null;
  proyecto_codigo: string | null;
  // Representante.
  rep_nombre: string | null;
  rep_tipo_doc: string | null;
  rep_numero_doc: string | null;
  // Soporte legal.
  numero_soporte_legal: string | null;
  soporte_legal_url: string | null;
  // Experiencia / formación.
  anios_experiencia: string | null;
  nivel_educativo: string | null;
  titulos_obtenidos: string | null;
  // Ubicación.
  barrio: string | null;
  upl: string | null;
  direccion: string | null;
  // Población.
  rango_poblacion: string | null;
  estrato: number | string | null;
  caracteristica_pob: string | null;
  // Beneficios ALK.
  beneficiada_alk: boolean | null;
  uso_beneficio: string | null;
  // Impacto.
  impacto_politicas: string | null;
  impacto_justificacion: string | null;
  // Disciplina + M2Ms (listas de nombres).
  disciplina_principal: string | null;
  escenarios: string[];
  escenarios_actuales: string[];
  implementos: string[];
  rango_etarios: string[];
  enfoques: string[];
  beneficios_alk: string[];
  // Flags.
  tiene_firma: boolean;
  tiene_soporte_legal: boolean;
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

/** Body para validar/rechazar (InscripcionEstadoUpdateSerializer). */
export interface EstadoUpdate {
  accion: 'validar' | 'rechazar';
}

/** Insights agregados (vista insights del módulo). */
export interface BancoInsights {
  total: number;
  meta: number;
  avance_pct: number;
  funnel: { borrador: number; enviada: number; validada: number; rechazada: number };
  pct_validacion: number;
  por_upl: Array<{ upl__codigo: string; upl__nombre: string; c: number }>;
  upls_cubiertas: number;
  upls_total: number;
  top_disciplinas: Array<{ disciplina_principal__nombre: string; c: number }>;
  top_enfoques: Array<{ enfoque__nombre: string; c: number }>;
  [extra: string]: unknown;
}
