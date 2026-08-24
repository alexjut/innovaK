import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import { AreaPanel, CompletitudArea, FilaPlanPago, OpcionesCaptura, PlanPago } from './area.types';

/**
 * Cliente del panel de ÁREA.
 *   GET  /presupuesto/api/areas/<id>/panel/
 *   GET  /presupuesto/api/areas/<id>/completitud/
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

  /** Qué le falta al expediente del área, por proyecto y por contrato. */
  completitud(area: string): Observable<CompletitudArea> {
    return this.http.get<CompletitudArea>(
      this.cfg.url(`/presupuesto/api/areas/${area}/completitud/`));
  }

  /** Le da dueño a un contrato huérfano: lo engancha a un proyecto del área.
   *  El servidor rechaza con 409 si ya es de otra. */
  asignarProyecto(area: string, contratoId: number, proyectoId: number,
                  observacion?: string): Observable<{ ok: boolean; creado: boolean }> {
    return this.http.post<{ ok: boolean; creado: boolean }>(
      this.cfg.url(`/presupuesto/api/areas/${area}/contratos/${contratoId}/asignar/`),
      { proyecto_id: proyectoId, observacion });
  }

  /** Suelta un contrato de ESTA área. Queda libre para quien corresponda. */
  soltarContrato(area: string, contratoId: number): Observable<{ ok: boolean }> {
    return this.http.delete<{ ok: boolean }>(
      this.cfg.url(`/presupuesto/api/areas/${area}/contratos/${contratoId}/asignar/`));
  }

  /** El plan de pago de un contrato: de SECOP si lo publica, capturado si no. */
  planPago(area: string, contratoId: number): Observable<PlanPago> {
    return this.http.get<PlanPago>(
      this.cfg.url(`/presupuesto/api/areas/${area}/contratos/${contratoId}/plan-pago/`));
  }

  /** Reemplaza el plan capturado. El servidor rechaza si el plan es de SECOP. */
  guardarPlanPago(area: string, contratoId: number,
                  filas: Partial<FilaPlanPago>[]): Observable<PlanPago> {
    return this.http.put<PlanPago>(
      this.cfg.url(`/presupuesto/api/areas/${area}/contratos/${contratoId}/plan-pago/`),
      { filas });
  }

  /** Los catálogos que el área puede elegir al completar. */
  opcionesCaptura(area: string): Observable<OpcionesCaptura> {
    return this.http.get<OpcionesCaptura>(
      this.cfg.url(`/presupuesto/api/areas/${area}/opciones-captura/`));
  }

  /** Captura un dato que ninguna fuente oficial provee. El servidor valida
   *  scope, rol y pertenencia del contrato — acá no se decide nada. */
  capturarDato(area: string, contratoId: number, cuerpo: {
    campo: 'etapa' | 'ejecucion_tec' | 'cdp' | 'forma_pago';
    valor: number | null;
    fecha_corte?: string;
    observacion?: string;
  }): Observable<{ ok: boolean; campo: string; valor: unknown }> {
    return this.http.post<{ ok: boolean; campo: string; valor: unknown }>(
      this.cfg.url(`/presupuesto/api/areas/${area}/contratos/${contratoId}/capturar/`),
      cuerpo);
  }

  vincularContrato(area: string, contratoId: number, actividadPlanId: number,
                   monto?: number): Observable<{ ok: boolean; creado: boolean }> {
    return this.http.post<{ ok: boolean; creado: boolean }>(
      this.cfg.url(`/presupuesto/api/areas/${area}/contratos/vincular/`),
      { contrato_id: contratoId, actividad_plan_id: actividadPlanId, monto });
  }
}
