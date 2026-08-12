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

/* ── Motor de puntaje · MATRIZ OFICIAL (Documento Maestro 2026-07-29) ───── */

/** Estado de la evaluación (independiente del estado de la inscripción).
 *  `calculada` es el terminal de la matriz oficial: no hay comité después. */
export type EvaluacionEstado =
  | 'pendiente' | 'calculada'
  | 'auto_calculado' | 'puntuado'   // estados del motor anterior
  | string;

/** Un subcriterio del desglose oficial (§3.1, §7.9.2, …). */
export interface SubcriterioOficial {
  id: string;
  nombre: string;
  max: number;
  estado: 'implementado' | 'pendiente' | 'sin_captura' | 'bloqueado' | string;
  pts: number;
  detalle: string;
  campo_faltante?: string | null;
}

/** Uno de los 12 criterios de la matriz oficial. */
export interface CriterioOficial {
  id: string;
  nombre: string;
  max: number;
  max_calculable: number;
  pts: number;
  estado: 'implementado' | 'pendiente' | 'sin_captura' | 'bloqueado' | string;
  origen: string;
  subcriterios: SubcriterioOficial[];
  campos_faltantes: string[];
}

/** Una de las 3 decisiones que Deportes todavía no ratifica. */
export interface DecisionPendiente {
  pregunta: string;
  constante: string;
  valor_hoy: unknown;
  opciones?: string[];
  recomendacion: string;
  por_que: string;
  impacto: string;
}

export interface BloqueResumen {
  pts: number;
  max: number;
  max_calculable: number;
}

/**
 * GET /banco-iniciativas/api/inscripciones/<id>/evaluacion/
 * POST idem → la calcula y la persiste.
 */
export interface EvaluacionDetalle {
  inscripcion_id: number;
  motor: 'oficial' | string;
  estado: EvaluacionEstado;
  rubrica_version: string;
  puntaje_auto: number;
  total: number;
  total_max: number;
  bloque1: BloqueResumen;
  bloque2: BloqueResumen;
  criterios: CriterioOficial[];
  tope_presupuestal: number;
  regla_tope_presupuestal: string;
  /** La inscripción no trae ningún campo del Documento Maestro: puntaje no comparable. */
  formulario_anterior: boolean;
  decisiones_pendientes: Record<string, DecisionPendiente>;
  advertencias: string[];
  persistida: boolean;
  motivo_sin_comite: string;
  // Solo si está persistida:
  ranking_pos?: number | null;
  cupos?: number;
  postuladas?: number;
  adjudicada?: boolean;
  /** Presente cuando había una evaluación del motor anterior sin recalcular. */
  evaluacion_previa_obsoleta?: {
    rubrica_version: string;
    total: number | null;
    nota: string;
  };
  // Vestigios del contrato anterior (siempre nulos con la matriz oficial).
  puntaje_comite?: number | null;
  bono_genero?: number | null;
  comite?: null;
}

/** Una fila del ranking de adjudicación.
 *  GET /banco-iniciativas/api/evaluacion/ranking/?evento_id=<id> */
export interface RankingFila {
  inscripcion_id: number;
  organizacion: string | null;
  ranking_pos: number | null;
  total: number;
  bloque1: number | null;
  bloque2: number | null;
  tope_presupuestal: number | null;
  formulario_anterior: boolean;
  adjudicada: boolean;
}

export interface RankingRespuesta {
  motor: string;
  version: string;
  evento_id: number;
  cupos: number;
  postuladas: number;
  cupos_insuficientes: boolean;
  decisiones_pendientes: Record<string, DecisionPendiente>;
  ranking: RankingFila[];
}

/* Los tipos del comité (CriterioComite, ComiteContexto, ComitePost,
   ComiteResultado) se retiraron el 2026-08-10: el Documento Maestro elimina el
   comité de evaluación y su endpoint responde 409. El motor anterior sigue en
   `services/puntaje.py` del backend, pero ya no tiene superficie en la UI. */

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
