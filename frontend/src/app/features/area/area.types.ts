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
