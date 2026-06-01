import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import {
  EntregaDetail,
  EntregaFilters,
  EntregaListItem,
  EstadoUpdate,
  JovenesInsights,
  PaginatedResponse,
} from './jovenes.types';

/**
 * Cliente HTTP del módulo Jóvenes a la E.
 *
 * Endpoints DRF (Etapa B):
 *   GET    /jovenes-a-la-e/api/entregas/         lista paginada
 *   GET    /jovenes-a-la-e/api/entregas/<id>/    detalle 360°
 *   POST   /jovenes-a-la-e/api/entregas/<id>/estado/  validar/rechazar
 *   GET    /jovenes-a-la-e/api/insights/         KPIs
 *
 * Convenios: 773-2025 (becas acceso/permanencia, metas 23771/23772) y
 * 955-2025 (dotación a sedes educativas, meta 23773).
 */
@Injectable({ providedIn: 'root' })
export class JovenesApi {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  private readonly base = '/jovenes-a-la-e/api';

  list(filters: EntregaFilters = {}): Observable<PaginatedResponse<EntregaListItem>> {
    let params = new HttpParams();
    if (filters.estado) params = params.set('estado', filters.estado);
    if (filters.evento) params = params.set('evento', String(filters.evento));
    if (filters.q) params = params.set('q', filters.q);
    if (filters.page) params = params.set('page', String(filters.page));
    if (filters.page_size) params = params.set('page_size', String(filters.page_size));

    return this.http.get<PaginatedResponse<EntregaListItem>>(
      this.cfg.url(`${this.base}/entregas/`),
      { params },
    );
  }

  detail(id: number): Observable<EntregaDetail> {
    return this.http.get<EntregaDetail>(this.cfg.url(`${this.base}/entregas/${id}/`));
  }

  updateEstado(id: number, body: EstadoUpdate): Observable<EntregaDetail> {
    return this.http.post<EntregaDetail>(
      this.cfg.url(`${this.base}/entregas/${id}/estado/`),
      body,
    );
  }

  insights(): Observable<JovenesInsights> {
    return this.http.get<JovenesInsights>(this.cfg.url(`${this.base}/insights/`));
  }
}
