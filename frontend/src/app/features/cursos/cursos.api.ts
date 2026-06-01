import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import {
  AsistenciaMarcas,
  AsistenciaResponse,
  AsistenciaResult,
  ReporteResponse,
  SesionesResponse,
} from './cursos.types';

@Injectable({ providedIn: 'root' })
export class CursosApi {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  sesiones(eventoId: number): Observable<SesionesResponse> {
    return this.http.get<SesionesResponse>(
      this.cfg.url(`/api/eventos/${eventoId}/sesiones/`),
    );
  }

  asistencia(claseId: number): Observable<AsistenciaResponse> {
    return this.http.get<AsistenciaResponse>(
      this.cfg.url(`/api/sesiones/${claseId}/asistencia/`),
    );
  }

  tomarLista(claseId: number, body: AsistenciaMarcas): Observable<AsistenciaResult> {
    return this.http.post<AsistenciaResult>(
      this.cfg.url(`/api/sesiones/${claseId}/asistencia/`),
      body,
    );
  }

  reporte(eventoId: number): Observable<ReporteResponse> {
    return this.http.get<ReporteResponse>(
      this.cfg.url(`/api/eventos/${eventoId}/reporte/`),
    );
  }
}
