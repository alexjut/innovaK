import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import { Festival, FestivalCatalogos, FestivalDetalle, FestivalInput } from './festivales.types';

/**
 * Cliente HTTP del módulo Festivales (CRUD de la cabecera).
 *   GET/POST   /festivales/api/festivales/
 *   GET        /festivales/api/festivales/catalogos/
 *   GET/PATCH/DELETE /festivales/api/festivales/<id>/
 */
@Injectable({ providedIn: 'root' })
export class FestivalesApi {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private readonly base = '/festivales/api/festivales';

  list(filtros?: { vigencia?: number; estado?: string; tipo?: number }): Observable<Festival[]> {
    let params = new HttpParams();
    if (filtros?.vigencia) params = params.set('vigencia', String(filtros.vigencia));
    if (filtros?.estado) params = params.set('estado', filtros.estado);
    if (filtros?.tipo) params = params.set('tipo', String(filtros.tipo));
    return this.http.get<Festival[]>(this.cfg.url(`${this.base}/`), { params });
  }

  catalogos(vigencia?: number): Observable<FestivalCatalogos> {
    let params = new HttpParams();
    if (vigencia) params = params.set('vigencia', String(vigencia));
    return this.http.get<FestivalCatalogos>(this.cfg.url(`${this.base}/catalogos/`), { params });
  }

  detalle(id: number): Observable<FestivalDetalle> {
    return this.http.get<FestivalDetalle>(this.cfg.url(`${this.base}/${id}/`));
  }

  crear(data: FestivalInput): Observable<Festival> {
    return this.http.post<Festival>(this.cfg.url(`${this.base}/`), data);
  }

  editar(id: number, data: FestivalInput): Observable<Festival> {
    return this.http.patch<Festival>(this.cfg.url(`${this.base}/${id}/`), data);
  }

  eliminar(id: number): Observable<void> {
    return this.http.delete<void>(this.cfg.url(`${this.base}/${id}/`));
  }
}
