import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import {
  BancoInsights,
  EstadoUpdate,
  InscripcionDetail,
  InscripcionFilters,
  InscripcionListItem,
  PaginatedResponse,
} from './banco.types';

/**
 * Cliente HTTP del módulo Banco de Iniciativas.
 *
 * Mapea los endpoints DRF de `apps/banco_iniciativas/api/` (Etapa B):
 *   GET    /banco-iniciativas/api/inscripciones/         lista paginada
 *   GET    /banco-iniciativas/api/inscripciones/<id>/    detalle
 *   POST   /banco-iniciativas/api/inscripciones/<id>/estado/  validar/rechazar
 *   GET    /banco-iniciativas/api/insights/              KPIs
 *
 * El JWT lo agrega el `jwtInterceptor` global — aquí no se toca.
 * Gating por módulo `banco_iniciativas` lo hace el backend; el
 * sidebar/hub también filtran por `auth.hasModule('banco_iniciativas')`.
 */
@Injectable({ providedIn: 'root' })
export class BancoApi {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  private readonly base = '/banco-iniciativas/api';

  list(filters: InscripcionFilters = {}): Observable<PaginatedResponse<InscripcionListItem>> {
    let params = new HttpParams();
    if (filters.estado) params = params.set('estado', filters.estado);
    if (filters.evento) params = params.set('evento', String(filters.evento));
    if (filters.q) params = params.set('q', filters.q);
    if (filters.page) params = params.set('page', String(filters.page));
    if (filters.page_size) params = params.set('page_size', String(filters.page_size));

    return this.http.get<PaginatedResponse<InscripcionListItem>>(
      this.cfg.url(`${this.base}/inscripciones/`),
      { params },
    );
  }

  detail(id: number): Observable<InscripcionDetail> {
    return this.http.get<InscripcionDetail>(
      this.cfg.url(`${this.base}/inscripciones/${id}/`),
    );
  }

  updateEstado(id: number, body: EstadoUpdate): Observable<InscripcionDetail> {
    return this.http.post<InscripcionDetail>(
      this.cfg.url(`${this.base}/inscripciones/${id}/estado/`),
      body,
    );
  }

  insights(): Observable<BancoInsights> {
    return this.http.get<BancoInsights>(this.cfg.url(`${this.base}/insights/`));
  }
}
