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
  // Puntaje de la evaluación (motor v3). ranking_pos solo cuando orden=puntaje.
  puntaje_total: number | null;
  puntaje_auto: number | null;
  estado_evaluacion: string | null;
  ranking_pos?: number;
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

/* ── Motor de puntaje / Evaluación (PR-1) ──────────────────────────────── */

/** Estado de la evaluación (independiente del estado de la inscripción). */
export type EvaluacionEstado = 'pendiente' | 'auto_calculado' | 'puntuado' | string;

/** Un criterio del bloque AUTO (calculado del formulario, read-only). */
export interface AutoCriterio {
  codigo: string;
  nombre: string;
  pts: number;
  max: number;
  detalle: string;
}

/**
 * GET /banco-iniciativas/api/inscripciones/<id>/evaluacion/
 * Los campos del comité solo vienen cuando `persistida === true`.
 */
export interface EvaluacionDetalle {
  inscripcion_id: number;
  estado: EvaluacionEstado;
  rubrica_version: string;
  puntaje_auto: number;
  auto_detalle: AutoCriterio[];
  persistida: boolean;
  // Solo si persistida:
  puntaje_comite?: number | null;
  bono_genero?: number | null;
  total?: number | null;
  viabilidad_cumple?: boolean | null;
  ambiental_cumple?: boolean | null;
  innovacion_cumple?: boolean | null;
  bono_mujeres?: boolean | null;
  comite_observacion?: string | null;
  evaluador_id?: number | null;
}

/** Un criterio binario del comité con el puntaje que otorga si cumple. */
export interface CriterioComite {
  codigo: 'viabilidad' | 'ambiental' | 'innovacion' | string;
  valor: number;
}

/**
 * GET /banco-iniciativas/api/inscripciones/<id>/evaluacion/comite/
 * Contexto para armar el panel del comité.
 */
export interface ComiteContexto {
  inscripcion_id: number;
  criterios_comite: CriterioComite[];
  /** Pre-señal del form: la propuesta declaró enfoque de mujeres. */
  bono_disponible: boolean;
  /** Chips {4,5,6} marcados por la org — YA suman en el AUTO (solo referencia). */
  inclusion_referencia: Array<{ codigo: number; nombre: string }>;
}

/** Body del POST del comité. */
export interface ComitePost {
  viabilidad: boolean;
  ambiental: boolean;
  innovacion: boolean;
  bono: boolean;
  observacion: string | null;
}

/** Respuesta del POST del comité. */
export interface ComiteResultado {
  detail: string;
  puntaje_auto: number;
  puntaje_comite: number | null;
  bono_genero: number;
  total: number | null;
  estado: EvaluacionEstado;
}

/** Resumen de puntaje/ranking del bloque insights (motor v3). */
export interface BancoPuntajeResumen {
  n_puntuadas: number;
  n_pendientes: number;
  promedio_total: number;
  promedio_auto: number;
  max_total: number;
  min_total: number;
}

/** Un bucket de la distribución de puntajes. */
export interface BancoDistribucionPuntaje {
  rango: string;
  n: number;
}

/** Una fila del top ranking (top 10 por total). */
export interface BancoTopRanking {
  pos: number;
  id: number;
  organizacion: string;
  total: number | null;
  auto: number | null;
  comite: number | null;
  bono: number | null;
  estado: string;
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
  // Bloque puntaje/ranking (motor v3).
  puntaje: BancoPuntajeResumen;
  distribucion_puntaje: BancoDistribucionPuntaje[];
  top_ranking: BancoTopRanking[];
  [extra: string]: unknown;
}
