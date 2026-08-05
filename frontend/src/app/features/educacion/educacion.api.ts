import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import {
  ColegioDetalle, ColegiosResponse, Entrega, EntregaInput, Insumo,
  ResumenVigencia,
} from './educacion.types';

/**
 * Cliente HTTP del módulo Educación.
 *   GET  /educacion/api/colegios/geojson/     (público — también lo usa el mapa)
 *   GET  /educacion/api/colegios/<id>/
 *   GET  /educacion/api/entregas/
 *   POST /educacion/api/entregas/crear/
 *   POST /educacion/api/entregas/<id>/eliminar/
 *   GET  /educacion/api/insumos/
 *   GET  /educacion/api/resumen/<vigencia>/
 */
@Injectable({ providedIn: 'root' })
export class EducacionApi {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private readonly base = '/educacion/api';

  colegios(filtros: {
    clase?: number[]; upz?: number[]; solo_principales?: boolean; q?: string;
  } = {}): Observable<ColegiosResponse> {
    let params = new HttpParams();
    for (const c of filtros.clase ?? []) params = params.append('clase', String(c));
    for (const u of filtros.upz ?? []) params = params.append('upz', String(u));
    if (filtros.solo_principales) params = params.set('solo_principales', '1');
    if (filtros.q) params = params.set('q', filtros.q);
    return this.http.get<ColegiosResponse>(
      this.cfg.url(`${this.base}/colegios/geojson/`), { params });
  }

  detalle(sedeId: number): Observable<ColegioDetalle> {
    return this.http.get<ColegioDetalle>(this.cfg.url(`${this.base}/colegios/${sedeId}/`));
  }

  entregas(filtros: {
    vigencia?: number; contrato?: number; sede?: number; implemento?: number;
  } = {}): Observable<{ items: Entrega[]; count: number }> {
    let params = new HttpParams();
    if (filtros.vigencia) params = params.set('vigencia', String(filtros.vigencia));
    if (filtros.contrato) params = params.set('contrato', String(filtros.contrato));
    if (filtros.sede) params = params.set('sede', String(filtros.sede));
    if (filtros.implemento) params = params.set('implemento', String(filtros.implemento));
    return this.http.get<{ items: Entrega[]; count: number }>(
      this.cfg.url(`${this.base}/entregas/`), { params });
  }

  crearEntrega(data: EntregaInput): Observable<{ ok: boolean; entrega: Entrega }> {
    return this.http.post<{ ok: boolean; entrega: Entrega }>(
      this.cfg.url(`${this.base}/entregas/crear/`), data);
  }

  eliminarEntrega(id: number): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>(
      this.cfg.url(`${this.base}/entregas/${id}/eliminar/`), {});
  }

  insumos(): Observable<{ items: Insumo[]; count: number }> {
    return this.http.get<{ items: Insumo[]; count: number }>(
      this.cfg.url(`${this.base}/insumos/`));
  }

  resumen(vigencia: number): Observable<ResumenVigencia> {
    return this.http.get<ResumenVigencia>(this.cfg.url(`${this.base}/resumen/${vigencia}/`));
  }
}
