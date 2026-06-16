import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';

/** Campo data-driven de una ficha (ver fichas_schema.py). */
export interface FichaCampo {
  name: string;
  label: string;
  type: 'text' | 'textarea' | 'number' | 'date' | 'select' | 'checkbox' | 'file';
  required?: boolean;
  catalogo?: string;
  options?: string[];
  map_to?: string;
  grupo: string;
}

export interface FichaEncabezado {
  proyecto: string | null;
  meta: string | null;
  numero_contrato: string | null;
  proceso_contractual: string | null;
  fecha_intervencion: string | null;
}

export interface FichaEvento {
  id: number;
  nombre: string;
  actividad_plan_id: number | null;
  encabezado: FichaEncabezado;
}

export interface FichaSchema {
  titulo: string;
  target?: string;
  disponible?: boolean;
  mensaje?: string;
  campos?: FichaCampo[];
  catalogos?: Record<string, { value: string; label: string }[]>;
}

export interface FichaRegistro {
  id: number;
  nombre_legal: string | null;
  numero_documento: string | null;
  evento_id: number;
  evento_nombre: string | null;
  estado: string;
  created_at: string | null;
}

export interface FichaRegistros {
  count: number;
  page: number;
  page_size: number;
  results: FichaRegistro[];
}

/**
 * Cliente de las fichas INTERNAS de caracterización, parametrizado por sector.
 *   /api/caracterizacion/fichas/<sector>/...   (cultura, seguridad, …)
 */
@Injectable({ providedIn: 'root' })
export class FichasCulturaApi {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  private base(sector: string): string {
    return `/api/caracterizacion/fichas/${sector}`;
  }

  contexto(sector: string): Observable<{ eventos: FichaEvento[] }> {
    return this.http.get<{ eventos: FichaEvento[] }>(this.cfg.url(`${this.base(sector)}/contexto/`));
  }

  schema(sector: string, target: string): Observable<FichaSchema> {
    return this.http.get<FichaSchema>(this.cfg.url(`${this.base(sector)}/${target}/schema/`));
  }

  crear(sector: string, target: string, fd: FormData): Observable<{ id: number; detail: string }> {
    return this.http.post<{ id: number; detail: string }>(
      this.cfg.url(`${this.base(sector)}/${target}/`),
      fd,
    );
  }

  registros(
    sector: string,
    target: string,
    opts: { evento?: number; q?: string; page?: number } = {},
  ): Observable<FichaRegistros> {
    let params = new HttpParams();
    if (opts.evento) params = params.set('evento', String(opts.evento));
    if (opts.q) params = params.set('q', opts.q);
    if (opts.page) params = params.set('page', String(opts.page));
    return this.http.get<FichaRegistros>(
      this.cfg.url(`${this.base(sector)}/${target}/registros/`),
      { params },
    );
  }
}
