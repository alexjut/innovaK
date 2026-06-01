import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../config/config.service';

export interface AdminCard {
  codigo: string;
  nombre: string;
  subtitulo: string;
  icono: string;
  color: string;
  visible: boolean;
  ruta: string;
}

export interface TipoActividad {
  codigo: string;
  nombre: string;
  descripcion: string;
  icono: string;
  color_hex: string;
  permite_caracterizacion: boolean;
  permite_inscripcion: boolean;
  num_eventos: number;
}

export interface HubTiposResponse {
  cards_admin: AdminCard[];
  tipos: TipoActividad[];
}

export interface SubgrupoActividad {
  id: number;
  nombre: string;
  dependencia_id: number;
  dependencia_nombre: string | null;
  num_eventos: number;
}

export interface SectorCaracterizacion {
  codigo: string;
  nombre: string;
  descripcion: string;
  icono: string;
}

export interface SubgruposResponse {
  tipo: {
    codigo: string;
    nombre: string;
    descripcion: string;
    icono?: string;
    color_hex?: string;
    permite_caracterizacion: boolean;
    permite_inscripcion?: boolean;
  };
  subgrupos: SubgrupoActividad[];
  sectores: SectorCaracterizacion[];
}

export interface EventoFila {
  id: number;
  nombre: string;
  linea: string | null;
  linea_id: number | null;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  activo: boolean;
  funcionario_nombre: string;
  actividad_plan_id: number | null;
}

export interface EventosResponse {
  tipo: {
    codigo: string;
    nombre: string;
    permite_caracterizacion: boolean;
    permite_inscripcion: boolean;
  };
  subgrupo: { id: number; nombre: string; dependencia_nombre: string | null };
  lineas_disponibles: { id: number; nombre: string }[];
  linea_id_actual: number | null;
  eventos: EventoFila[];
  total: number;
}

/**
 * Cliente HTTP para los endpoints DRF de Actividades.
 * Reemplaza la dependencia del iframe al hub Django.
 */
@Injectable({ providedIn: 'root' })
export class ActividadesService {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  /** Catálogo de tipos de actividad para el hub principal. */
  tipos(): Observable<HubTiposResponse> {
    return this.http.get<HubTiposResponse>(
      this.cfg.url('/api/actividades/tipos/'),
    );
  }

  /** Subgrupos o sectores (si caracterización) para un tipo dado. */
  subgrupos(codigo: string): Observable<SubgruposResponse> {
    return this.http.get<SubgruposResponse>(
      this.cfg.url(`/api/actividades/tipo/${encodeURIComponent(codigo)}/subgrupos/`),
    );
  }

  /** Eventos del par (tipo, subgrupo), con filtro opcional por línea. */
  eventos(
    codigo: string,
    subgrupoId: number,
    linea?: number | null,
  ): Observable<EventosResponse> {
    const lineaQs = linea ? `?linea=${linea}` : '';
    return this.http.get<EventosResponse>(
      this.cfg.url(
        `/api/actividades/tipo/${encodeURIComponent(codigo)}/subgrupo/${subgrupoId}/eventos/${lineaQs}`,
      ),
    );
  }
}
