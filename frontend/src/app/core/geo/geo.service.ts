import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../config/config.service';

export interface UpzLite { codigo: string; nombre: string; }
export interface BarrioLite { codigo: string; nombre: string; upz_codigo: string | null; }
export interface TipoEventoLite {
  codigo: string;
  nombre: string;
  color_hex: string;
  icono: string;
  css_slug: string;
  permite_caracterizacion?: boolean;
  permite_inscripcion?: boolean;
  requiere_actividad_plan?: boolean;
  requiere_horario?: boolean;
}
export interface DependenciaLite { id: number; nombre: string; }
export interface SubgrupoLite {
  id: number;
  nombre: string;
  dependencia_id: number;
  dependencia_nombre: string | null;
}
export interface ConteoSubgrupo { total: number; proximos: number; ejecutados: number; }

export interface MapaCatalogos {
  upz: UpzLite[];
  barrios: BarrioLite[];
  tipos_evento: TipoEventoLite[];
  dependencias: DependenciaLite[];
  subgrupos: SubgrupoLite[];
  subgrupos_inversion_local: SubgrupoLite[];
  conteos_subgrupo: Record<number, ConteoSubgrupo>;
}

export interface EventoFiltros {
  tipo_evento?: string[];
  subgrupo_id?: number[];
  dependencia_id?: number;
  desde?: string;
  hasta?: string;
}

export interface FeatureCollection {
  type: 'FeatureCollection';
  features: GeoFeature[];
}

export interface GeoFeature {
  type: 'Feature';
  geometry: { type: string; coordinates: any };
  // properties es un sobre dinámico — el contrato exacto depende del
  // endpoint. Usamos `any` para que el cliente pueda hacer dot access
  // sin TS4111 strict, a costa de validar en runtime.
  properties: any;
}

/**
 * Una disciplina dictada en una sede (columna `escuela.actividades`, JSONB).
 * Las claves se leen de forma tolerante en el componente: la puebla el cargue
 * del censo y conviene no acoplarse a un nombre exacto.
 */
export interface EscuelaActividad {
  actividad?: string;
  disciplina?: string;
  horarios?: string;
  horario?: string;
  edades?: string;
  edad?: string;
  formador?: string;
  responsable?: string;
  telefono?: string;
  [clave: string]: unknown;
}

/** Properties de una escuela tal como las sirve `api_kennedy_escuelas`. */
export interface EscuelaProps {
  id: number;
  nombre: string | null;
  tipo: string | null;
  direccion: string | null;
  estado?: string | null;
  activo?: boolean | null;
  origen?: string | null;
  censo_origen?: string | null;
  url_maps?: string | null;
  estrato_ideca?: number | null;
  actividades?: EscuelaActividad[];
  upz_codigo?: string | null;
  upz_nombre?: string | null;
  upz_fuente?: 'geometria' | 'declarado' | null;
  barrio_codigo?: string | null;
  barrio_nombre?: string | null;
  barrio_fuente?: 'geometria' | 'declarado' | null;
  barrio_declarado?: string | null;
  barrio_estado?: string | null;
  discrepancia?: boolean | null;
  revision_requerida?: boolean | null;
  revision_detalle?: string | null;
  geolocalizado?: boolean | null;

  /** El punto NO es el de la sede: es el de respaldo (Alcaldía). */
  ubicacion_aproximada?: boolean | null;
  /** Por qué no tiene punto propio — cada caso se resuelve distinto. */
  motivo_ubicacion?: 'sin_direccion' | 'direccion_no_ubicada' | null;
  /** Tiene punto real, pero cae fuera del contorno de la localidad. */
  fuera_de_kennedy?: boolean | null;
}

/** Properties de una sede de colegio distrital (`api_colegios_geojson`). */
export interface ColegioProps {
  id: number;
  dane_sede: string;
  dane_establecimiento: string;
  colegio: string;
  sede: string;
  orden_sede: string | null;
  es_principal: boolean;
  clase: number | null;
  clase_nombre: string;
  direccion: string | null;
  barrio: string | null;
  telefono: string | null;
  upz_codigo: number | null;
  estrato_ideca: number | null;
  matricula_total: number | null;
  /** La matrícula tiene OTRA fecha de corte que el resto de la ficha. */
  matricula_corte: string | null;
  fecha_corte: string | null;
  /** Solo con sesión: resumen de insumos entregados. Ausente para anónimos. */
  entregas_n?: number;
  entregas_valor?: number;
}

export interface ColegiosResponse extends FeatureCollection {
  /** Sedes que la fuente reporta sin coordenada: se listan, no se pintan. */
  sin_ubicacion?: ColegioProps[];
  count_sin_ubicacion?: number;
  colegios?: number;
  matricula_total?: number;
  /** false = la tabla todavía no está aplicada en ese entorno. */
  disponible?: boolean;
}

/** Properties de un CAI (`api_kennedy_cai`). */
export interface CaiProps {
  codigo: string;
  nombre: string;
  tipo: 'FIJO' | 'MOVIL';
  es_movil: boolean;
  direccion: string | null;
  telefono: string | null;
  horario: string | null;
  upz_codigo: number | null;
  upz_nombre: string | null;
  fuente: string;
  fecha_corte: string | null;
}

export interface CaiResponse extends FeatureCollection {
  count?: number;
  count_fijos?: number;
  count_moviles?: number;
  disponible?: boolean;
}

export interface EscuelasResponse extends FeatureCollection {
  sin_ubicacion?: EscuelaProps[];
  count_sin_ubicacion?: number;
  count_fuera_de_kennedy?: number;
}

/**
 * Cliente HTTP único para todos los endpoints del módulo
 * georreferenciación. Todos los métodos devuelven Observable<T>
 * para componer con RxJS.
 */
@Injectable({ providedIn: 'root' })
export class GeoService {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  // El mapa se sirve igual con y sin sesión: `/app/mapa` es público y los
  // endpoints de geo también (2026-07-30). No hay dos versiones que mantener.

  catalogos(): Observable<MapaCatalogos> {
    return this.http.get<MapaCatalogos>(this.cfg.url('/geo/api/mapa/catalogos/'));
  }

  eventos(filtros: EventoFiltros = {}): Observable<FeatureCollection> {
    let params = new HttpParams();
    if (filtros.tipo_evento?.length) {
      for (const t of filtros.tipo_evento) params = params.append('tipo_evento', t);
    }
    if (filtros.subgrupo_id?.length) {
      for (const s of filtros.subgrupo_id) params = params.append('subgrupo_id', String(s));
    }
    if (filtros.dependencia_id) params = params.set('dependencia_id', String(filtros.dependencia_id));
    if (filtros.desde) params = params.set('desde', filtros.desde);
    if (filtros.hasta) params = params.set('hasta', filtros.hasta);
    return this.http.get<FeatureCollection>(
      this.cfg.url('/geo/api/eventos/'), { params },
    );
  }

  contornoKennedy(): Observable<FeatureCollection> {
    return this.http.get<FeatureCollection>(this.cfg.url('/geo/api/kennedy/contorno/'));
  }
  upzKennedy(): Observable<FeatureCollection> {
    return this.http.get<FeatureCollection>(this.cfg.url('/geo/api/kennedy/upz/'));
  }
  barriosKennedy(): Observable<FeatureCollection> {
    return this.http.get<FeatureCollection>(this.cfg.url('/geo/api/kennedy/barrios/'));
  }
  parquesKennedy(): Observable<FeatureCollection> {
    return this.http.get<FeatureCollection>(this.cfg.url('/geo/api/kennedy/parques/'));
  }
  /**
   * Escuelas de Cultura y Deporte. Además de los puntos devuelve
   * `sin_ubicacion`: las que el censo reporta pero no tienen coordenada.
   * No se pintan (no hay dónde), pero se listan para que el área vea qué
   * le falta por completar.
   */
  escuelasKennedy(): Observable<EscuelasResponse> {
    return this.http.get<EscuelasResponse>(this.cfg.url('/geo/api/kennedy/escuelas/'));
  }
  /**
   * Sedes de colegios distritales de Kennedy (fuente: Secretaría de Educación
   * vía IDECA). Además de los puntos devuelve `sin_ubicacion`: las sedes que
   * la fuente reporta sin coordenada.
   */
  colegiosKennedy(filtros: {
    clase?: number[]; upz?: number[]; solo_principales?: boolean; q?: string;
  } = {}): Observable<ColegiosResponse> {
    let params = new HttpParams();
    for (const c of filtros.clase ?? []) params = params.append('clase', String(c));
    for (const u of filtros.upz ?? []) params = params.append('upz', String(u));
    if (filtros.solo_principales) params = params.set('solo_principales', '1');
    if (filtros.q) params = params.set('q', filtros.q);
    return this.http.get<ColegiosResponse>(
      this.cfg.url('/educacion/api/colegios/geojson/'), { params });
  }

  /** CAI de la Secretaría de Seguridad. `tipo` separa fijos de móviles. */
  cai(tipo?: 'FIJO' | 'MOVIL'): Observable<CaiResponse> {
    let params = new HttpParams();
    if (tipo) params = params.set('tipo', tipo);
    return this.http.get<CaiResponse>(
      this.cfg.url('/geo/api/kennedy/cai/'), { params });
  }

  /** Manzanas de estratificación (IDECA/Catastro). Filtro opcional por estrato. */
  estratificacionKennedy(estratos?: number[]): Observable<FeatureCollection> {
    let params = new HttpParams();
    for (const e of estratos ?? []) params = params.append('estrato', String(e));
    return this.http.get<FeatureCollection>(
      this.cfg.url('/geo/api/kennedy/estratificacion/'), { params });
  }

  /** Organizaciones del Banco de Iniciativas (Deporte) como puntos. Filtro opcional por evento. */
  bancoKennedy(evento?: number): Observable<FeatureCollection> {
    let params = new HttpParams();
    if (evento) params = params.set('evento', String(evento));
    return this.http.get<FeatureCollection>(
      this.cfg.url('/geo/api/kennedy/banco/'), { params });
  }

  // `ofertaFormativa()` se retiró el 2026-08-05 con su capa del mapa: agrupaba
  // cursos por `evento.escuela_id`, columna NULL en el 100% de los eventos, así
  // que el endpoint no podía devolver un solo punto. El endpoint Django sigue
  // en pie (`/geo/api/oferta-formativa/`) — borrarlo es decisión de Alex.

  /** Lugares históricos georreferenciados (DRF LugarGeoJSONView). */
  lugares(): Observable<FeatureCollection> {
    return this.http.get<FeatureCollection>(this.cfg.url('/geo/api/lugares'));
  }

  /** Festivales con punto (lat/lon) como FeatureCollection (FEST-F-11). */
  festivalesGeojson(filtros: {
    tipo_festival?: number; vigencia?: number; estado?: string;
  } = {}): Observable<FeatureCollection> {
    let params = new HttpParams();
    if (filtros.tipo_festival != null) params = params.set('tipo_festival', String(filtros.tipo_festival));
    if (filtros.vigencia != null) params = params.set('vigencia', String(filtros.vigencia));
    if (filtros.estado) params = params.set('estado', filtros.estado);
    return this.http.get<FeatureCollection>(
      this.cfg.url('/festivales/api/festivales/geojson/'), { params },
    );
  }

  /** Tramos viales intervenidos por contratos de infraestructura (LineStrings). */
  tramosViales(filtros: {
    contrato?: number; proyecto?: string; avance_min?: number; avance_max?: number;
  } = {}): Observable<FeatureCollection> {
    let params = new HttpParams();
    if (filtros.contrato != null) params = params.set('contrato', String(filtros.contrato));
    if (filtros.proyecto) params = params.set('proyecto', filtros.proyecto);
    if (filtros.avance_min != null) params = params.set('avance_min', String(filtros.avance_min));
    if (filtros.avance_max != null) params = params.set('avance_max', String(filtros.avance_max));
    return this.http.get<FeatureCollection>(
      this.cfg.url('/geo/api/mapa/tramos-viales/'), { params },
    );
  }

  /** Parques con obras de infraestructura (Points). */
  parquesObras(filtros: {
    contrato?: number; proyecto?: string;
  } = {}): Observable<FeatureCollection> {
    let params = new HttpParams();
    if (filtros.contrato != null) params = params.set('contrato', String(filtros.contrato));
    if (filtros.proyecto) params = params.set('proyecto', filtros.proyecto);
    return this.http.get<FeatureCollection>(
      this.cfg.url('/geo/api/mapa/parques-obras/'), { params },
    );
  }
}
