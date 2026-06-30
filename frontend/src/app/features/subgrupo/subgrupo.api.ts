import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import {
  CrearActividadPayload,
  CrearActividadResp,
  EventoGeoFeatureCollection,
  MisSubgruposResp,
  ProyectoArea,
  SubgrupoPanel,
} from './subgrupo.types';

/**
 * Cliente HTTP del panel operativo por subgrupo (RBAC B3/B4).
 *   GET /presupuesto/api/subgrupos/mios/          → picker (mis subgrupos)
 *   GET /presupuesto/api/subgrupos/<id>/panel/    → panel (tiles + general + contratos)
 *   GET /geo/api/eventos/?subgrupo_id=<id>        → eventos georreferenciados (mini-mapa B5)
 *
 * El scope (subgrupos visibles del usuario) lo aplica el backend; aquí solo
 * se consume el contrato. La cadena de conteo del KPI vive en backend — esta
 * navegación es pura proyección, no la altera.
 */
@Injectable({ providedIn: 'root' })
export class SubgrupoApi {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private readonly base = '/presupuesto/api/subgrupos';

  /** Subgrupos visibles del usuario (entrada/picker del panel). */
  mios(): Observable<MisSubgruposResp> {
    return this.http.get<MisSubgruposResp>(this.cfg.url(`${this.base}/mios/`));
  }

  /** Panel operativo de UN subgrupo (gate de acceso lo hace el backend). */
  panel(subgrupoId: number): Observable<SubgrupoPanel> {
    return this.http.get<SubgrupoPanel>(this.cfg.url(`${this.base}/${subgrupoId}/panel/`));
  }

  /**
   * Eventos georreferenciados del subgrupo (mini-mapa contextual B5).
   * Reusa el endpoint geo existente (`EventoGeoJSONView`), que soporta el
   * filtro `subgrupo_id` server-side.
   */
  eventosGeo(subgrupoId: number): Observable<EventoGeoFeatureCollection> {
    const params = new HttpParams().set('subgrupo_id', String(subgrupoId));
    return this.http.get<EventoGeoFeatureCollection>(
      this.cfg.url('/geo/api/eventos/'), { params },
    );
  }

  // ── PR-A · Crear actividad en el área (solo Coordinador; gate en backend) ──
  /** Proyectos del área + sus indicadores (catálogo del form). */
  proyectosDelArea(subgrupoId: number): Observable<{ results: ProyectoArea[] }> {
    return this.http.get<{ results: ProyectoArea[] }>(
      this.cfg.url(`${this.base}/${subgrupoId}/proyectos/`));
  }

  /** Crea una actividad colgando de un proyecto del área. */
  crearActividad(subgrupoId: number, payload: CrearActividadPayload): Observable<CrearActividadResp> {
    return this.http.post<CrearActividadResp>(
      this.cfg.url(`${this.base}/${subgrupoId}/actividades/`), payload);
  }
}
