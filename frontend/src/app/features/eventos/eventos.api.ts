import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';

export interface EventoLite {
  id: number;
  nombre: string | null;
  tipo_codigo: string | null;
  tipo_nombre: string | null;
  subgrupo_id: number | null;
  subgrupo_nombre: string | null;
  dependencia_id: number | null;
  dependencia_nombre: string | null;
  linea_id: number | null;
  linea_nombre: string | null;
  funcionario_id: number | null;
  funcionario_nombre: string;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  actividad_plan_id: number | null;
  activo: boolean;
}

export interface EventoDetalle extends EventoLite {
  descripcion: string;
  lugar_incidencia_id: number | null;
  indicador_id: number | null;
  indicador_nombre: string | null;
  magnitud_aportada: string | null;
  sector_caracterizacion: string | null;
  hora_inicio: string | null;
  hora_fin: string | null;
  // Al enviar al backend usamos tipo_evento_id (== tipo_codigo, el FK
  // tiene to_field='codigo'). El detalle del GET trae `tipo_codigo`.
  tipo_evento_id?: string | null;
}

export interface EventosListaResponse {
  count: number;
  page: number;
  page_size: number;
  results: EventoLite[];
}

export interface EventosFiltros {
  q?: string;
  tipo?: string;
  dependencia_id?: number;
  subgrupo_id?: number;
  activo?: '1' | '0' | '';
  page?: number;
  page_size?: number;
}

@Injectable({ providedIn: 'root' })
export class EventosApi {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  lista(f: EventosFiltros = {}): Observable<EventosListaResponse> {
    let p = new HttpParams();
    if (f.q) p = p.set('q', f.q);
    if (f.tipo) p = p.set('tipo', f.tipo);
    if (f.dependencia_id) p = p.set('dependencia_id', String(f.dependencia_id));
    if (f.subgrupo_id) p = p.set('subgrupo_id', String(f.subgrupo_id));
    if (f.activo) p = p.set('activo', f.activo);
    if (f.page) p = p.set('page', String(f.page));
    if (f.page_size) p = p.set('page_size', String(f.page_size));
    return this.http.get<EventosListaResponse>(
      this.cfg.url('/api/eventos/lista/'), { params: p },
    );
  }

  detalle(id: number): Observable<EventoDetalle> {
    return this.http.get<EventoDetalle>(
      this.cfg.url(`/api/eventos/${id}/detalle/`),
    );
  }

  crear(payload: Partial<EventoDetalle>): Observable<{ id: number; detail: string }> {
    return this.http.post<{ id: number; detail: string }>(
      this.cfg.url('/api/eventos/'), payload,
    );
  }

  actualizar(
    id: number,
    payload: Partial<EventoDetalle>,
  ): Observable<{ id: number; detail: string }> {
    return this.http.patch<{ id: number; detail: string }>(
      this.cfg.url(`/api/eventos/${id}/actualizar/`), payload,
    );
  }

  toggleActivo(id: number): Observable<{ id: number; activo: boolean }> {
    return this.http.post<{ id: number; activo: boolean }>(
      this.cfg.url(`/api/eventos/${id}/toggle-activo/`), {},
    );
  }
}
