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

  /** Oferta formativa: escuelas con nº de cursos activos (mapa de calor). */
  ofertaFormativa(): Observable<{ items: any[]; total_escuelas: number; total_cursos: number }> {
    return this.http.get<{ items: any[]; total_escuelas: number; total_cursos: number }>(
      this.cfg.url('/geo/api/oferta-formativa/'));
  }

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
