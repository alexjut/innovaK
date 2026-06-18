import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import {
  AsistenciaMarcas,
  AsistenciaResponse,
  AsistenciaResult,
  CursoDetalle,
  MisCursosResponse,
  NotaBulkItem,
  NotasBulkResult,
  NotasResponse,
  ReporteResponse,
  SesionCrearItem,
  SesionesCrearResult,
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

  misCursos(): Observable<MisCursosResponse> {
    return this.http.get<MisCursosResponse>(this.cfg.url('/api/cursos/mios/'));
  }

  detalle(eventoId: number): Observable<CursoDetalle> {
    return this.http.get<CursoDetalle>(this.cfg.url(`/api/cursos/${eventoId}/`));
  }

  setCupo(eventoId: number, cupo: number | null): Observable<{ id: number; resumen: any }> {
    return this.http.patch<{ id: number; resumen: any }>(
      this.cfg.url(`/api/cursos/${eventoId}/`), { cupo_maximo: cupo },
    );
  }

  crearSesiones(
    eventoId: number,
    sesiones: SesionCrearItem[],
  ): Observable<SesionesCrearResult> {
    return this.http.post<SesionesCrearResult>(
      this.cfg.url(`/api/eventos/${eventoId}/sesiones/`),
      { sesiones },
    );
  }

  notas(eventoId: number): Observable<NotasResponse> {
    return this.http.get<NotasResponse>(this.cfg.url(`/api/eventos/${eventoId}/notas/`));
  }

  guardarNotas(
    eventoId: number,
    notas: NotaBulkItem[],
  ): Observable<NotasBulkResult> {
    return this.http.post<NotasBulkResult>(
      this.cfg.url(`/api/eventos/${eventoId}/notas/`),
      { notas },
    );
  }

  borrarNota(evaluacionId: number): Observable<void> {
    return this.http.delete<void>(this.cfg.url(`/api/notas/${evaluacionId}/`));
  }
}
