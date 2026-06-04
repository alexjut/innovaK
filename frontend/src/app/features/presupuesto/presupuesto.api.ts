import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import { PaginatedResponse, PresupEntidad, PresupItem } from './presupuesto.types';

/**
 * Cliente HTTP del módulo Presupuesto. Endpoints DRF (Etapa B):
 *   GET /presupuesto/api/<entidad>/         lista paginada
 *   GET /presupuesto/api/<entidad>/<id>/    detalle
 *
 * Donde <entidad> ∈ {proyectos, indicadores, cdps, contratos, avances}.
 */
@Injectable({ providedIn: 'root' })
export class PresupuestoApi {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  private readonly base = '/presupuesto/api';

  list(
    entidad: PresupEntidad,
    page = 1,
  ): Observable<PaginatedResponse<PresupItem>> {
    const params = new HttpParams().set('page', String(page));
    return this.http.get<PaginatedResponse<PresupItem>>(
      this.cfg.url(`${this.base}/${entidad}/`),
      { params },
    );
  }

  detail(entidad: PresupEntidad, id: number): Observable<PresupItem> {
    return this.http.get<PresupItem>(this.cfg.url(`${this.base}/${entidad}/${id}/`));
  }
}
