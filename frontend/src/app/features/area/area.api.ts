import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import { AreaPanel } from './area.types';

/**
 * Cliente del panel de ÁREA.
 *   GET  /presupuesto/api/areas/<id>/panel/
 *   POST /presupuesto/api/areas/<id>/contratos/vincular/
 */
@Injectable({ providedIn: 'root' })
export class AreaApi {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  panel(area: string): Observable<AreaPanel> {
    return this.http.get<AreaPanel>(
      this.cfg.url(`/presupuesto/api/areas/${area}/panel/`));
  }

  vincularContrato(area: string, contratoId: number, actividadPlanId: number,
                   monto?: number): Observable<{ ok: boolean; creado: boolean }> {
    return this.http.post<{ ok: boolean; creado: boolean }>(
      this.cfg.url(`/presupuesto/api/areas/${area}/contratos/vincular/`),
      { contrato_id: contratoId, actividad_plan_id: actividadPlanId, monto });
  }
}
