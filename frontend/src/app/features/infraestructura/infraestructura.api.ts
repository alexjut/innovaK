import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import {
  AvanceActualizadoResp,
  ContratoCreadoResp,
  ContratoInfraDetalle,
  ContratoInfraInput,
  InfraCatalogos,
  InfraInsights,
  InfraPanel,
  ParqueInput,
  ParqueVinculadoResp,
  TramoCreadoResp,
  TramoInput,
} from './infraestructura.types';

/**
 * Cliente HTTP del módulo Infraestructura (contratos de obra: vías + parques).
 *   GET   /presupuesto/api/infraestructura/             → panel (tiles + contratos)
 *   GET   /presupuesto/api/infraestructura/catalogos/   → categorías, proyectos, parques
 *   GET   /presupuesto/api/infraestructura/insights/    → agregados Chart.js
 *   GET   /presupuesto/api/infraestructura/contratos/<id>/  → detalle (tramos + parques)
 *   POST  /presupuesto/api/infraestructura/contratos/   → crea contrato
 *   POST  .../contratos/<id>/tramos/   → agrega tramo (geometría automática)
 *   POST  .../contratos/<id>/parques/  → vincula parque
 *   PATCH/DELETE .../tramos/<id>/      → avance / quitar tramo
 *   PATCH/DELETE .../parques/<id>/     → avance / quitar parque
 */
@Injectable({ providedIn: 'root' })
export class InfraestructuraApi {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private readonly base = '/presupuesto/api/infraestructura';

  panel(): Observable<InfraPanel> {
    return this.http.get<InfraPanel>(this.cfg.url(`${this.base}/`));
  }

  catalogos(): Observable<InfraCatalogos> {
    return this.http.get<InfraCatalogos>(this.cfg.url(`${this.base}/catalogos/`));
  }

  insights(): Observable<InfraInsights> {
    return this.http.get<InfraInsights>(this.cfg.url(`${this.base}/insights/`));
  }

  detalle(id: number): Observable<ContratoInfraDetalle> {
    return this.http.get<ContratoInfraDetalle>(this.cfg.url(`${this.base}/contratos/${id}/`));
  }

  crearContrato(data: ContratoInfraInput): Observable<ContratoCreadoResp> {
    return this.http.post<ContratoCreadoResp>(this.cfg.url(`${this.base}/contratos/`), data);
  }

  agregarTramo(contratoId: number, data: TramoInput): Observable<TramoCreadoResp> {
    return this.http.post<TramoCreadoResp>(
      this.cfg.url(`${this.base}/contratos/${contratoId}/tramos/`), data,
    );
  }

  vincularParque(contratoId: number, data: ParqueInput): Observable<ParqueVinculadoResp> {
    return this.http.post<ParqueVinculadoResp>(
      this.cfg.url(`${this.base}/contratos/${contratoId}/parques/`), data,
    );
  }

  actualizarTramo(tramoId: number, pctAvance: number): Observable<AvanceActualizadoResp> {
    return this.http.patch<AvanceActualizadoResp>(
      this.cfg.url(`${this.base}/tramos/${tramoId}/`), { pct_avance: pctAvance },
    );
  }

  quitarTramo(tramoId: number): Observable<void> {
    return this.http.delete<void>(this.cfg.url(`${this.base}/tramos/${tramoId}/`));
  }

  actualizarParque(intervencionId: number, pctAvance: number): Observable<AvanceActualizadoResp> {
    return this.http.patch<AvanceActualizadoResp>(
      this.cfg.url(`${this.base}/parques/${intervencionId}/`), { pct_avance: pctAvance },
    );
  }

  quitarParque(intervencionId: number): Observable<void> {
    return this.http.delete<void>(this.cfg.url(`${this.base}/parques/${intervencionId}/`));
  }
}
