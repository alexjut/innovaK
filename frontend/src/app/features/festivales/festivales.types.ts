export type EstadoFestival = 'planeado' | 'ejecutado' | 'cerrado';

export interface Festival {
  id: number;
  nombre: string;
  tipo_festival: number | null;
  tipo_festival_nombre: string | null;
  vigencia: number;
  numero_edicion: number | null;
  estado: EstadoFestival;
  estado_display: string;
  subgrupo_id: number | null;
  responsable: number | null;
  responsable_nombre: string | null;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  lugar_texto: string | null;
  descripcion: string | null;
  documentado: boolean;
  publicado: boolean;
  publicado_en: string | null;
  slug: string | null;
  n_eventos: number;
  n_dias: number;
  upl_codigo?: number | null;
  latitud?: number | string | null;
  longitud?: number | string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface TipoFestival {
  codigo: number;
  nombre: string;
}

export interface FestivalEvento {
  id: number;
  nombre: string;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  tipo_evento_nombre: string | null;
  subgrupo_nombre: string | null;
  funcionario_nombre: string | null;
  festival_dia_id: number | null;
  aforo: number;
  aforo_proyectado: number | null;
}

/** Día del festival (PR-A programación multi-día). */
export interface FestivalDia {
  id: number;
  festival: number;
  fecha: string;
  nombre: string | null;
  escenario_texto: string | null;
  responsable: number | null;
  responsable_nombre: string | null;
  orden: number | null;
  descripcion: string | null;
  n_actos: number;
  actos: FestivalEvento[];
  created_at?: string | null;
  updated_at?: string | null;
}

export type FestivalDiaInput = Partial<
  Pick<FestivalDia, 'fecha' | 'nombre' | 'escenario_texto' | 'responsable' | 'orden' | 'descripcion'>
>;

/** Detalle del festival: agenda por día + actos sin ubicar. */
export interface FestivalDetalle extends Festival {
  dias: FestivalDia[];
  eventos: FestivalEvento[];
  actos_sin_dia: FestivalEvento[];
}

// ── PR-E · Lineup / jurados / criterios / evaluación ──────────────────
export interface FestivalArtista {
  id: number;
  festival_dia: number | null;
  dia_fecha: string | null;
  nombre: string;
  tipo: 'artista' | 'grupo' | 'invitado';
  tipo_display: string;
  descripcion: string | null;
  orden: number | null;
}
export interface FestivalJurado {
  id: number;
  nombre: string;
  perfil: string | null;
}
export interface FestivalCriterio {
  id: number;
  nombre: string;
  peso: number | string;
  orden: number | null;
}
export interface RankingFila {
  artista_id: number;
  nombre: string;
  tipo: string;
  n_jurados_calificaron: number;
  consolidado: number | null;
  posicion: number | null;
}
export interface EvaluacionCelda {
  artista_id: number;
  jurado_id: number;
  criterio_id: number;
  puntaje: number;
}
export interface RankingData {
  festival_id: number;
  cerrado: boolean;
  artistas: FestivalArtista[];
  jurados: FestivalJurado[];
  criterios: FestivalCriterio[];
  evaluaciones: EvaluacionCelda[];
  ranking: RankingFila[];
}

export type TipoArchivo = 'foto' | 'video' | 'acta' | 'listado' | 'soporte';

/** Evidencia de la biblioteca del festival (PR-B). */
export interface FestivalArchivo {
  id: number;
  festival: number;
  festival_dia: number | null;
  dia_fecha: string | null;
  tipo: TipoArchivo;
  tipo_display: string;
  nombre_archivo: string | null;
  mime: string | null;
  tamano_bytes: number | null;
  descripcion: string | null;
  es_imagen: boolean;
  archivo_url: string;
  subido_por_nombre: string | null;
  created_at: string | null;
}

export interface FestivalResumen {
  vigencia: number | null;
  planeados: number;
  ejecutados: number;
  cerrados: number;
  meta_anual: number;
}

// ── PR-C · Tablero de seguimiento ──────────────────────────────────────
export interface KpiAvance {
  id: number;
  nombre: string;
  unidad: string;
  meta_magnitud: number;
  avance_total: number;
  avance_festivales: number;
  pct: number | null;
}

export interface FestivalInsightFila {
  id: number;
  nombre: string;
  estado: EstadoFestival;
  estado_display: string;
  tipo: string | null;
  n_actos: number;
  n_dias: number;
  n_archivos: number;
  aforo: number;
}

export interface FestivalInsights {
  vigencia: number | null;
  vigencias: number[];
  festivales: FestivalInsightFila[];
  kpis: KpiAvance[];
  presupuesto: { asignado: number; ejecutado: number; disponible: number };
  resumen: {
    n_festivales: number;
    planeados: number;
    ejecutados: number;
    cerrados: number;
    total_actos: number;
    actos_contabilizados: number;
    aforo_total: number;
  };
}

export interface UplOpcion {
  value: number;
  label: string;
}

export interface ResponsableOpcion {
  value: number;
  label: string;
}

export interface FestivalCatalogos {
  tipos_festival: TipoFestival[];
  vigencias: number[];
  estados: { value: EstadoFestival; label: string }[];
  upls?: UplOpcion[];
  responsables?: ResponsableOpcion[];
  max_fotos?: number;
  tipos_archivo?: { value: string; label: string }[];
  resumen?: FestivalResumen;
}

export type FestivalInput = Partial<
  Pick<
    Festival,
    | 'nombre'
    | 'tipo_festival'
    | 'vigencia'
    | 'numero_edicion'
    | 'estado'
    | 'fecha_inicio'
    | 'fecha_fin'
    | 'lugar_texto'
    | 'descripcion'
    | 'subgrupo_id'
    | 'responsable'
    | 'upl_codigo'
    | 'latitud'
    | 'longitud'
  >
>;

// ── PR-G · encuesta de percepción ────────────────────────────────────
export interface PercepcionQR {
  publicado: boolean;
  url: string | null;
  path: string | null;
  qr_base64: string | null;
}
export interface PercepcionDistItem { label: string; valor: number; }
export interface PercepcionPregunta { campo: string; label: string; datos: PercepcionDistItem[]; }
export interface PercepcionInsights {
  festival: { id: number; nombre: string; publicado: boolean; slug: string | null };
  total: number;
  preguntas: PercepcionPregunta[];
  genero: PercepcionDistItem[];
  rango_edad: PercepcionDistItem[];
}
