import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import {
  AvanceActualizadoResp,
  ContratoCreadoResp,
  ContratoInfraDetalle,
  ContratoInfraInput,
  CorteAvance,
  CorteCreadoResp,
  CorteFiltros,
  InfraCatalogos,
  InfraFeatureCollection,
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

  // ── Seguimiento por cortes + geometrías del contrato ───────────────
  /** GeoJSON del contrato: tramos (LineString) + parques (Point). */
  contratoGeojson(contratoId: number): Observable<InfraFeatureCollection> {
    return this.http.get<InfraFeatureCollection>(
      this.cfg.url(`${this.base}/contratos/${contratoId}/geojson/`),
    );
  }

  /** Historial de cortes; filtra por objeto (contrato/tramo/parque). */
  cortes(filtros: CorteFiltros): Observable<CorteAvance[]> {
    let qs = `contrato_id=${filtros.contrato_id}`;
    if (filtros.objeto_tipo) qs += `&objeto_tipo=${filtros.objeto_tipo}`;
    if (filtros.objeto_id != null) qs += `&objeto_id=${filtros.objeto_id}`;
    return this.http.get<CorteAvance[]>(this.cfg.url(`${this.base}/cortes/?${qs}`));
  }

  /** Registra un corte (multipart: incluye la foto tal cual si la hay). */
  registrarCorte(fd: FormData): Observable<CorteCreadoResp> {
    return this.http.post<CorteCreadoResp>(this.cfg.url(`${this.base}/cortes/`), fd);
  }

  /** URL del backend para una foto (antes/después) de un corte (cárgala como blob+Bearer). */
  fotoCortePath(corteId: number, cual: 'antes' | 'despues'): string {
    return `${this.base}/cortes/${corteId}/foto/${cual}/`;
  }
}
