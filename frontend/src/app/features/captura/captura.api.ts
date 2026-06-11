import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';

export interface CapturaItem {
  id: number;
  evento_id: number;
  tipo_codigo: string;
  nombre_legal: string | null;
  numero_documento: string | null;
  estado: string;
  created_at: string | null;
}
export interface CampoDef { name: string; label: string; type: string; }
export interface CapturaDetalle extends CapturaItem {
  titulo_tipo: string;
  campos: CampoDef[];
  datos: Record<string, any>;
  firma_mongo_id: string | null;
  observaciones: string | null;
  evento_nombre: string | null;
}
export interface CapturaInsights {
  tipo: string;
  titulo: string;
  total: number;
  validadas: number;
  por_estado: { label: string; valor: number }[];
  distribuciones: { campo: string; label: string; datos: { label: string; valor: number }[] }[];
}

@Injectable({ providedIn: 'root' })
export class CapturaApi {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private base = '/api/captura/organizador';

  list(opts: { evento?: number; estado?: string; q?: string; page?: number } = {}): Observable<{ count: number; results: CapturaItem[] }> {
    let p = new HttpParams().set('page', String(opts.page ?? 1));
    if (opts.evento) p = p.set('evento', String(opts.evento));
    if (opts.estado) p = p.set('estado', opts.estado);
    if (opts.q) p = p.set('q', opts.q);
    return this.http.get<{ count: number; results: CapturaItem[] }>(this.cfg.url(`${this.base}/`), { params: p });
  }
  detalle(id: number): Observable<CapturaDetalle> {
    return this.http.get<CapturaDetalle>(this.cfg.url(`${this.base}/${id}/`));
  }
  estado(id: number, accion: 'validar' | 'rechazar', observaciones = ''): Observable<{ estado: string; detail: string; kpi_aportes: number }> {
    return this.http.post<{ estado: string; detail: string; kpi_aportes: number }>(
      this.cfg.url(`${this.base}/${id}/estado/`), { accion, observaciones });
  }
  insights(tipo?: string, evento?: number): Observable<CapturaInsights> {
    let p = new HttpParams();
    if (tipo) p = p.set('tipo', tipo);
    if (evento) p = p.set('evento', String(evento));
    return this.http.get<CapturaInsights>(this.cfg.url('/api/captura/insights/'), { params: p });
  }
}
