/**
 * Tipos del panel operativo por SUBGRUPO (RBAC B3/B4).
 *
 * Espejo exacto de los endpoints DRF de `apps/presupuesto`:
 *   GET /presupuesto/api/subgrupos/mios/
 *   GET /presupuesto/api/subgrupos/<id>/panel/
 *
 * NO inventar campos: cada interface refleja la respuesta JSON real
 * (apps/presupuesto/services/panel_subgrupo.py).
 */

// ── Picker / entrada (mis subgrupos) ───────────────────────────────
export interface SubgrupoLite {
  id: number;
  /** Slug para la URL (`educacion`). Lo deriva el backend del nombre. */
  slug?: string;
  nombre: string | null;
  dependencia: string | null;
  n_eventos: number;
}

export interface MisSubgruposResp {
  results: SubgrupoLite[];
}

// ── Panel de un subgrupo ───────────────────────────────────────────
export interface SubgrupoRef {
  id: number;
  nombre: string | null;
  dependencia: string | null;
}

export interface SubgrupoTiles {
  n_proyectos: number;
  n_actividades: number;
  n_eventos: number;
  n_contratos: number;
  valor_contratado: number;
}

/** Un evento del subgrupo (proyección del panel; campos mínimos). */
export interface EventoSubgrupo {
  id: number;
  nombre: string | null;
  tipo_codigo: string | null;
  tipo_nombre: string | null;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  activo: boolean;
  /** Path del formulario público (null si el tipo no tiene). Para QR/Formulario. */
  url_publica: string | null;
}

/**
 * Grupo "General": eventos del subgrupo agrupados por ActividadPlan.
 * `actividad_plan_id` puede ser null (eventos sueltos sin actividad).
 */
export interface GrupoGeneral {
  actividad_plan_id: number | null;
  actividad_plan_descripcion: string | null;
  proyecto_codigo: string | null;
  proyecto_nombre: string | null;
  n_eventos: number;
  eventos: EventoSubgrupo[];
}

/** Contrato del subgrupo (nodo lateral, vía ContratoProyecto). */
export interface ContratoSubgrupo {
  id: number;
  numero: string;
  objeto: string | null;
  valor: number | null;
  ejecucion: number | null;
}

export interface SubgrupoPanel {
  subgrupo: SubgrupoRef;
  tiles: SubgrupoTiles;
  general: GrupoGeneral[];
  contratos: ContratoSubgrupo[];
}

// ── PR-A · Crear actividad en el área (solo Coordinador) ───────────
export interface IndicadorLite {
  id: number;
  nombre: string;
  unidad: string;
}

/** Proyecto del área + sus indicadores, para el form de crear actividad. */
export interface ProyectoArea {
  id: number;
  codigo: string | null;
  nombre: string | null;
  indicadores: IndicadorLite[];
}

export interface CrearActividadPayload {
  proyecto_id: number;
  descripcion: string;
  indicador_id?: number | null;
}

export interface CrearActividadResp {
  id: number;
  indicador_vinculado: boolean;
  detail: string;
}

// ── GeoJSON de eventos (mini-mapa B5) ──────────────────────────────
export interface EventoGeoProps {
  id: number;
  nombre: string | null;
  tipo_evento_codigo: string | null;
  tipo_evento_nombre: string | null;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  subgrupo: string | null;
  subgrupo_id: number | null;
  dependencia: string | null;
  funcionario: string | null;
  direccion: string | null;
  activo: boolean;
}

export interface EventoGeoFeature {
  type: 'Feature';
  geometry: { type: 'Point'; coordinates: [number, number] } | null;
  properties: EventoGeoProps;
}

export interface EventoGeoFeatureCollection {
  type: 'FeatureCollection';
  features: EventoGeoFeature[];
  count?: number;
}
