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
 * Cliente HTTP único para todos los endpoints del módulo
 * georreferenciación. Todos los métodos devuelven Observable<T>
 * para componer con RxJS.
 */
@Injectable({ providedIn: 'root' })
export class GeoService {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

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
  escuelasKennedy(): Observable<FeatureCollection> {
    return this.http.get<FeatureCollection>(this.cfg.url('/geo/api/kennedy/escuelas/'));
  }

  /** Lugares históricos georreferenciados (DRF LugarGeoJSONView). */
  lugares(): Observable<FeatureCollection> {
    return this.http.get<FeatureCollection>(this.cfg.url('/geo/api/lugares'));
  }
}
