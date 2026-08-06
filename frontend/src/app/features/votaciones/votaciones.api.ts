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
    // Organizador: ?all=1 trae también los eventos finalizados/inactivos.
    return this.http.get<EventosResponse>(
      this.cfg.url('/votaciones/api/v2/eventos/?all=1'),
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

  /**
   * QR del evento: URL pública firmada + PNG en base64 (S-4).
   *
   * Antes la pantalla pedía `/votaciones/qr/event/<id>.png` directo desde un
   * `<img src>`, y ese endpoint era público: acuñaba el QR de cualquier id,
   * existiera o no. Ahora exige `votaciones_admin`, y por eso el PNG viaja en
   * base64 dentro del JSON — un `<img src>` no puede mandar el header
   * `Authorization`, así que servirlo como imagen gateada rompería la pantalla.
   */
  qrEvento(eventId: number): Observable<{ url_publica: string; qr_base64: string }> {
    return this.http.get<any>(this.cfg.url(`/votaciones/api/v2/eventos/${eventId}/qr/`));
  }

  // ── CRUD organizador ──────────────────────────────────────────────
  curules(): Observable<{ results: { value: string; label: string; group: string }[] }> {
    return this.http.get<any>(this.cfg.url('/votaciones/api/v2/curules/'));
  }
  crearEvento(body: any): Observable<any> {
    return this.http.post(this.cfg.url('/votaciones/api/v2/eventos/crear/'), body);
  }
  editarEvento(id: number, body: any): Observable<any> {
    return this.http.patch(this.cfg.url(`/votaciones/api/v2/eventos/${id}/editar/`), body);
  }
  toggleEvento(id: number): Observable<any> {
    return this.http.post(this.cfg.url(`/votaciones/api/v2/eventos/${id}/toggle/`), {});
  }
  eliminarEvento(id: number): Observable<any> {
    return this.http.delete(this.cfg.url(`/votaciones/api/v2/eventos/${id}/editar/`));
  }
  candidatosAdmin(eventId: number): Observable<any> {
    return this.http.get(this.cfg.url(`/votaciones/api/v2/eventos/${eventId}/candidatos-admin/`));
  }
  crearCandidato(body: any): Observable<any> {
    return this.http.post(this.cfg.url('/votaciones/api/v2/candidatos/crear/'), body);
  }
  editarCandidato(id: number, body: any): Observable<any> {
    return this.http.patch(this.cfg.url(`/votaciones/api/v2/candidatos/${id}/editar/`), body);
  }
  toggleCandidato(id: number): Observable<any> {
    return this.http.post(this.cfg.url(`/votaciones/api/v2/candidatos/${id}/toggle/`), {});
  }
  eliminarCandidato(id: number): Observable<any> {
    return this.http.delete(this.cfg.url(`/votaciones/api/v2/candidatos/${id}/editar/`));
  }

  // ── Votantes (padrón) ─────────────────────────────────────────────
  votantesTipos(): Observable<{ results: { codigo: number; nombre: string }[] }> {
    return this.http.get<any>(this.cfg.url('/votaciones/api/v2/votantes/tipos-documento/'));
  }
  votantesBuscar(doc: string): Observable<any> {
    return this.http.get<any>(this.cfg.url(`/votaciones/api/v2/votantes/buscar/?document_number=${encodeURIComponent(doc)}`));
  }
  votantesRegistrar(body: any): Observable<any> {
    return this.http.post(this.cfg.url('/votaciones/api/v2/votantes/registrar/'), body);
  }
  votantesList(eventId?: number): Observable<any> {
    const q = eventId ? `?event_id=${eventId}` : '';
    return this.http.get<any>(this.cfg.url(`/votaciones/api/v2/votantes/${q}`));
  }
}
