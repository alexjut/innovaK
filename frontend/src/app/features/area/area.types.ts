/** Tipos del panel de ÁREA (espejo de apps/presupuesto/services/panel_area.py). */

export interface AreaRef {
  id: number;
  /** Slug del área, tal como aparece en la URL. */
  slug: string;
  nombre: string | null;
  dependencia: string | null;
  es_inversion: boolean;
}

export interface AreaTiles {
  n_proyectos: number;
  n_actividades: number;
  n_actividades_con_kpi: number;
  n_eventos: number;
  n_eventos_con_actividad: number;
  n_contratos: number;
  n_contratos_enganchados: number;
  valor_contratado: number;
}

export interface ModuloArea {
  codigo: string;
  nombre: string;
  descripcion: string;
  icono: string;
  ruta: string;
  conteo: number | null;
  etiqueta_conteo: string | null;
  /** true = herramienta compartida entre áreas; false = propia del área. */
  transversal: boolean;
}

export interface KpiLite { id: number; nombre: string; unidad: string; meta: number | null; }
export interface ContratoDeActividad { id: number; numero: string; monto: number | null; }
export interface EventoDeActividad {
  id: number; nombre: string | null; tipo_codigo: string | null;
  tipo_nombre: string | null; fecha_inicio: string | null; activo: boolean;
}

export interface FilaPlan {
  actividad_plan_id: number;
  descripcion: string;
  proyecto_codigo: string | null;
  proyecto_nombre: string | null;
  kpis: KpiLite[];
  contratos: ContratoDeActividad[];
  eventos: EventoDeActividad[];
  n_eventos: number;
  monto_contratado: number;
  sin_kpi: boolean;
  sin_contrato: boolean;
}

export interface ContratoArea {
  id: number;
  numero: string;
  objeto: string | null;
  valor: number | null;
  ejecucion: number | null;
  tiene_cdp: boolean;
  enganchado: boolean;
}

/** Un tipo de cosa suelta: cuántas de cuántas, y cuáles. */
export interface Suelto<T = unknown> {
  n: number;
  de: number;
  que_significa: string;
  items: T[];
}

export interface AreaSueltos {
  actividades_sin_contrato: Suelto<{ id: number; descripcion: string }>;
  actividades_sin_kpi: Suelto<{ id: number; descripcion: string }>;
  eventos_sin_actividad: Suelto<EventoDeActividad>;
  contratos_sin_actividad: Suelto<ContratoArea>;
}

export interface AreaPanel {
  area: AreaRef;
  tiles: AreaTiles;
  proyectos: { id: number; codigo: string | null; nombre: string | null }[];
  plan: FilaPlan[];
  contratos: ContratoArea[];
  sueltos: AreaSueltos;
  modulos: ModuloArea[];
}

// ── Completitud del expediente ───────────────────────────────────────────
// Lo que responde `GET /presupuesto/api/areas/<slug>/completitud/`.
// El backend manda el estado YA decidido: el front no recalcula si algo falta
// ni si alguien puede editarlo — sólo lo pinta.

/** `ok` hay dato · `pendiente`/`sin_dato` falta · `no_aplica` fuera del cálculo. */
export type EstadoCampo = 'ok' | 'pendiente' | 'sin_dato' | 'no_aplica';

export interface CampoExpediente {
  clave: string;
  bloque: string;
  etiqueta: string;
  estado: EstadoCampo;
  valor: unknown;
  /** De dónde salió. `null` = ninguna fuente oficial lo provee: lo captura el área. */
  fuente: string | null;
  editable: boolean;
}

export interface BloqueCompletitud {
  clave: string;
  etiqueta: string;
  completos: number;
  total: number;
}

export interface ContratoCompletitud {
  contrato_id: number;
  numero: string;
  objeto: string | null;
  /** `null` cuando no hay campos aplicables. NO es 0 %. */
  pct: number | null;
  completos: number;
  aplicables: number;
  campos: CampoExpediente[];
  bloques: BloqueCompletitud[];
  faltantes: string[];
  n_faltantes: number;
}

export interface ProyectoCompletitud {
  id: number;
  codigo: string;
  nombre: string;
  n_contratos: number;
  n_faltantes: number;
  pct: number | null;
  contratos: ContratoCompletitud[];
}

export interface CompletitudArea {
  subgrupo_id: number;
  area: { id: number; nombre: string };
  /** El área no tiene proyectos en el plan. No es un panel roto. */
  sin_plan: boolean;
  motivo?: string;
  proyectos: ProyectoCompletitud[];
  tiles: {
    n_proyectos: number;
    n_contratos: number;
    n_faltantes: number;
    pct: number | null;
  };
  /** Lo decide el SERVIDOR (rol Coordinador del área). No se reimplementa acá. */
  puede_capturar: boolean;
}

/** Lo que el área puede ELEGIR al completar. Viene del servidor filtrado:
 *  los CDP son sólo los de sus proyectos. */
export interface OpcionesCaptura {
  etapas: { codigo: number; nombre: string }[];
  formas_pago: { codigo: number; nombre: string }[];
  cdps: { id: number; etiqueta: string; proyecto_id: number | null }[];
}
