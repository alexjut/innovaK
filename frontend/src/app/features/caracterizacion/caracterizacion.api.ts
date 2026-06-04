import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import {
  CaractDetail,
  CaractFilters,
  CaractInsights,
  CaractListItem,
  CaractSector,
  PaginatedResponse,
} from './caracterizacion.types';

/**
 * Cliente HTTP de los 6 sectores de caracterización.
 *
 * Endpoints DRF (Etapa B):
 *   GET /caracterizacion/api/<sector>/         lista por sector
 *   GET /caracterizacion/api/<sector>/<id>/    detalle
 *   GET /caracterizacion/api/insights/         agregados
 */
@Injectable({ providedIn: 'root' })
export class CaracterizacionApi {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  private readonly base = '/caracterizacion/api';

  list(
    sector: CaractSector,
    filters: CaractFilters = {},
  ): Observable<PaginatedResponse<CaractListItem>> {
    let params = new HttpParams();
    if (filters.evento_id) params = params.set('evento_id', String(filters.evento_id));
    if (filters.persona_id) params = params.set('persona_id', String(filters.persona_id));
    if (filters.page) params = params.set('page', String(filters.page));
    if (filters.page_size) params = params.set('page_size', String(filters.page_size));

    return this.http.get<PaginatedResponse<CaractListItem>>(
      this.cfg.url(`${this.base}/${sector}/`),
      { params },
    );
  }

  detail(sector: CaractSector, id: number): Observable<CaractDetail> {
    return this.http.get<CaractDetail>(this.cfg.url(`${this.base}/${sector}/${id}/`));
  }

  insights(): Observable<CaractInsights> {
    return this.http.get<CaractInsights>(this.cfg.url(`${this.base}/insights/`));
  }
}
