/**
 * Tipos del módulo Infraestructura (contratos de obra: vías + parques).
 * Contratos espejo de los endpoints DRF de `apps/presupuesto` — NO inventar
 * campos: cada interface refleja la respuesta JSON real del backend.
 */

export type CategoriaInfra = 'VIAS' | 'PARQUES' | 'INTERVENTORIA';

/** Estado de avance de un tramo/parque (derivado del % de avance). */
export type EstadoAvance = 'sin_iniciar' | 'parcial' | 'terminado';

/** Estado de resolución geográfica de un tramo vial. */
export type GeoStatus = 'OK' | 'PENDIENTE' | 'NO_ENCONTRADO' | string;

// ── Panel ──────────────────────────────────────────────────────────
export interface InfraTiles {
  n_contratos: number;
  valor_total: number;
  avance_global: number;
  n_tramos: number;
  n_parques: number;
}

export interface ContratoInfraLite {
  id: number;
  numero: string;
  categoria: CategoriaInfra;
  objeto: string | null;
  proyecto_codigo: string | null;
  proyecto_nombre: string | null;
  valor: number | null;
  ejecucion: number | null;
  interventoria_contrato: string | null;
  n_tramos: number;
  n_parques: number;
}

export interface InfraPanel {
  tiles: InfraTiles;
  contratos: ContratoInfraLite[];
}

// ── Detalle del contrato ───────────────────────────────────────────
export interface TramoVial {
  id: number;
  civ: number;
  eje_vial: string | null;
  desde: string | null;
  hasta: string | null;
  valor_intervencion: number | null;
  pct_avance: number;
  geo_status: GeoStatus;
  estado: EstadoAvance;
}

export interface ParqueIntervencion {
  id: number;
  parque_id: number | null;
  codigo_parque: number | string | null;
  nombre: string | null;
  direccion: string | null;
  pct_avance: number;
  estado: EstadoAvance;
}

export interface ContratoInfraDetalle {
  id: number;
  numero: string;
  categoria: CategoriaInfra;
  objeto: string | null;
  proyecto_codigo: string | null;
  proyecto_nombre: string | null;
  valor: number | null;
  ejecucion: number | null;
  interventoria_contrato: string | null;
  interventoria_valor: number | null;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  tramos: TramoVial[];
  parques: ParqueIntervencion[];
}

// ── Catálogos (para los forms de alta) ─────────────────────────────
export interface CategoriaOpcion {
  codigo: CategoriaInfra;
  label: string;
  captura: 'tramos' | 'parques' | 'ninguna';
}

export interface ProyectoInfra {
  id: number;
  codigo: string;
  nombre: string;
}

export interface ParqueCatalogo {
  id: number;
  codigo_parque: number | string;
  nombre: string;
}

export interface InfraCatalogos {
  categorias: CategoriaOpcion[];
  proyectos: ProyectoInfra[];
  parques: ParqueCatalogo[];
}

// ── Insights ───────────────────────────────────────────────────────
export interface InfraInsightsKpis {
  n_contratos: number;
  valor_total: number;
  n_tramos: number;
  tramos_terminados: number;
  pct_tramos_terminados: number;
  n_parques: number;
  geo_pendientes: number;
}

export interface AvancePorContrato {
  contrato: string;
  categoria: CategoriaInfra;
  ejecucion: number;
  valor: number;
}

export interface ValorPorCategoria {
  categoria: CategoriaInfra;
  valor: number;
}

export interface InfraInsights {
  kpis: InfraInsightsKpis;
  tramos_por_estado: Record<EstadoAvance, number>;
  valor_tramos_por_estado: Record<EstadoAvance, number>;
  avance_por_contrato: AvancePorContrato[];
  valor_por_categoria: ValorPorCategoria[];
}

// ── Inputs de creación ─────────────────────────────────────────────
export interface ContratoInfraInput {
  numero: string;
  categoria: CategoriaInfra | '';
  proyecto_id: number | null;
  objeto: string;
  valor: number | null;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  ejecucion: number | null;
  interventoria_contrato: string | null;
  interventoria_valor: number | null;
}

export interface TramoInput {
  valor_intervencion: number | null;
  civ: number | null;
  pk_id: number | null;
  eje_vial: string | null;
  desde: string | null;
  hasta: string | null;
  pct_avance: number | null;
}

export interface ParqueInput {
  parque_id: number | null;
  direccion: string | null;
  // El punto de la dirección elegida en Catastro. Viaja con el texto para no
  // tener que geocodificar después.
  direccion_lon: number | null;
  direccion_lat: number | null;
  pct_avance: number | null;
}

// ── Respuestas puntuales ───────────────────────────────────────────
export interface ContratoCreadoResp {
  id: number;
  numero: string;
  detail: string;
}

export interface TramoCreadoResp {
  id: number;
  geo_status: GeoStatus;
  en_mapa: boolean;
  detail: string;
}

export interface ParqueVinculadoResp {
  id: number;
  codigo_parque: number | string;
  en_mapa: boolean;
  detail: string;
}

export interface AvanceActualizadoResp {
  id: number;
  pct_avance: number;
  ejecucion_contrato: number;
}

// ── Seguimiento por cortes ─────────────────────────────────────────
/** A qué objeto del contrato aplica un corte de avance. */
export type ObjetoCorte = 'contrato' | 'tramo' | 'parque';

/** Un corte de avance (un registro histórico de % en una fecha). */
export interface CorteAvance {
  id: number;
  objeto_tipo: ObjetoCorte;
  objeto_id: number | null;
  fecha: string;
  pct: number;
  observacion: string | null;
  tiene_foto_antes: boolean;
  tiene_foto_despues: boolean;
  autor_id: number | null;
}

/** Filtros del listado de cortes (todos opcionales salvo contrato_id). */
export interface CorteFiltros {
  contrato_id: number;
  objeto_tipo?: ObjetoCorte;
  objeto_id?: number | null;
}

/** Datos de un corte a registrar (se envía como multipart). */
export interface CorteInput {
  contrato_id: number;
  objeto_tipo: ObjetoCorte;
  objeto_id: number | null;
  fecha: string;
  pct: number;
  observacion: string;
  foto_antes: File | null;
  foto_despues: File | null;
}

export interface CorteCreadoResp {
  id: number;
  pct: number;
  tiene_foto_antes: boolean;
  tiene_foto_despues: boolean;
  detail: string;
}

// ── GeoJSON del contrato (mini-mapa) ───────────────────────────────
export interface GeojsonProps {
  tipo: 'tramo' | 'parque';
  pct_avance: number;
  eje_vial?: string | null;
  desde?: string | null;
  hasta?: string | null;
  civ?: number | null;
  codigo_parque?: number | string | null;
  nombre?: string | null;
}

export interface InfraFeature {
  type: 'Feature';
  geometry: {
    type: 'LineString' | 'Point' | string;
    coordinates: number[] | number[][];
  } | null;
  properties: GeojsonProps;
}

export interface InfraFeatureCollection {
  type: 'FeatureCollection';
  features: InfraFeature[];
}
