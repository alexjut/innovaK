import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import {
  EntregaFilters,
  EntregaInsumoDetail,
  EntregaInsumoListItem,
  EstadoUpdate,
  PaginatedResponse,
} from './entregas.types';

/**
 * Cliente HTTP del módulo Entregas de insumos.
 *
 * Endpoints DRF autenticados (gateados por módulo `entregas`):
 *   GET    /entregas/api/entregas/              lista paginada + filtros
 *   GET    /entregas/api/entregas/<id>/         detalle 360°
 *   POST   /entregas/api/entregas/<id>/estado/  validar/rechazar → sync KPIs
 */
@Injectable({ providedIn: 'root' })
export class EntregasService {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  private readonly base = '/entregas/api';

  list(filters: EntregaFilters = {}): Observable<PaginatedResponse<EntregaInsumoListItem>> {
    let params = new HttpParams();
    if (filters.estado) params = params.set('estado', filters.estado);
    if (filters.evento) params = params.set('evento', String(filters.evento));
    if (filters.q) params = params.set('q', filters.q);
    if (filters.page) params = params.set('page', String(filters.page));
    if (filters.page_size) params = params.set('page_size', String(filters.page_size));

    return this.http.get<PaginatedResponse<EntregaInsumoListItem>>(
      this.cfg.url(`${this.base}/entregas/`),
      { params },
    );
  }

  detail(id: number): Observable<EntregaInsumoDetail> {
    return this.http.get<EntregaInsumoDetail>(
      this.cfg.url(`${this.base}/entregas/${id}/`),
    );
  }

  updateEstado(id: number, body: EstadoUpdate): Observable<EntregaInsumoDetail> {
    return this.http.post<EntregaInsumoDetail>(
      this.cfg.url(`${this.base}/entregas/${id}/estado/`),
      body,
    );
  }
}
