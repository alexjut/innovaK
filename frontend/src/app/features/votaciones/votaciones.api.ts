import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import {
  CandidatosResponse,
  EventosResponse,
  Resultados,
} from './votaciones.types';

@Injectable({ providedIn: 'root' })
export class VotacionesApi {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  eventos(): Observable<EventosResponse> {
    return this.http.get<EventosResponse>(
      this.cfg.url('/votaciones/api/v2/eventos/'),
    );
  }

  candidatos(eventId: number): Observable<CandidatosResponse> {
    return this.http.get<CandidatosResponse>(
      this.cfg.url(`/votaciones/api/v2/eventos/${eventId}/candidatos/`),
    );
  }

  /** Pasa eventId=0 para obtener los del último evento activo. */
  resultados(eventId: number): Observable<Resultados> {
    if (eventId === 0) {
      return this.http.get<Resultados>(
        this.cfg.url('/votaciones/api/v2/eventos/0/resultados/latest/'),
      );
    }
    return this.http.get<Resultados>(
      this.cfg.url(`/votaciones/api/v2/eventos/${eventId}/resultados/`),
    );
  }
}
