import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import {
  Festival, FestivalArchivo, FestivalArtista, FestivalCatalogos, FestivalCriterio,
  FestivalDetalle, FestivalDia, FestivalDiaInput, FestivalInput, FestivalInsights,
  FestivalJurado, RankingData, PercepcionQR, PercepcionInsights,
} from './festivales.types';

/**
 * Cliente HTTP del módulo Festivales (CRUD de la cabecera).
 *   GET/POST   /festivales/api/festivales/
 *   GET        /festivales/api/festivales/catalogos/
 *   GET/PATCH/DELETE /festivales/api/festivales/<id>/
 */
@Injectable({ providedIn: 'root' })
export class FestivalesApi {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private readonly base = '/festivales/api/festivales';

  list(filtros?: { vigencia?: number; estado?: string; tipo?: number }): Observable<Festival[]> {
    let params = new HttpParams();
    if (filtros?.vigencia) params = params.set('vigencia', String(filtros.vigencia));
    if (filtros?.estado) params = params.set('estado', filtros.estado);
    if (filtros?.tipo) params = params.set('tipo', String(filtros.tipo));
    return this.http.get<Festival[]>(this.cfg.url(`${this.base}/`), { params });
  }

  catalogos(vigencia?: number): Observable<FestivalCatalogos> {
    let params = new HttpParams();
    if (vigencia) params = params.set('vigencia', String(vigencia));
    return this.http.get<FestivalCatalogos>(this.cfg.url(`${this.base}/catalogos/`), { params });
  }

  insights(vigencia?: number): Observable<FestivalInsights> {
    let params = new HttpParams();
    if (vigencia) params = params.set('vigencia', String(vigencia));
    return this.http.get<FestivalInsights>(this.cfg.url(`${this.base}/insights/`), { params });
  }

  detalle(id: number): Observable<FestivalDetalle> {
    return this.http.get<FestivalDetalle>(this.cfg.url(`${this.base}/${id}/`));
  }

  crear(data: FestivalInput): Observable<Festival> {
    return this.http.post<Festival>(this.cfg.url(`${this.base}/`), data);
  }

  editar(id: number, data: FestivalInput): Observable<Festival> {
    return this.http.patch<Festival>(this.cfg.url(`${this.base}/${id}/`), data);
  }

  eliminar(id: number): Observable<void> {
    return this.http.delete<void>(this.cfg.url(`${this.base}/${id}/`));
  }

  /** Publica o despublica la ficha web del festival. */
  publicar(id: number, publicado: boolean): Observable<{ publicado: boolean; slug: string | null; url: string | null }> {
    return this.http.post<{ publicado: boolean; slug: string | null; url: string | null }>(
      this.cfg.url(`${this.base}/${id}/publicar/`), { publicado });
  }

  // ── PR-G · encuesta de percepción ──────────────────────────────────
  percepcionQR(festivalId: number): Observable<PercepcionQR> {
    return this.http.get<PercepcionQR>(this.cfg.url(`${this.base}/${festivalId}/percepcion/qr/`));
  }
  percepcionInsights(festivalId: number): Observable<PercepcionInsights> {
    return this.http.get<PercepcionInsights>(this.cfg.url(`${this.base}/${festivalId}/percepcion/insights/`));
  }

  // ── PR-A · programación multi-día ──────────────────────────────────
  dias(festivalId: number): Observable<FestivalDia[]> {
    return this.http.get<FestivalDia[]>(this.cfg.url(`${this.base}/${festivalId}/dias/`));
  }

  crearDia(festivalId: number, data: FestivalDiaInput): Observable<FestivalDia> {
    return this.http.post<FestivalDia>(this.cfg.url(`${this.base}/${festivalId}/dias/`), data);
  }

  editarDia(diaId: number, data: FestivalDiaInput): Observable<FestivalDia> {
    return this.http.patch<FestivalDia>(this.cfg.url(`/festivales/api/dias/${diaId}/`), data);
  }

  eliminarDia(diaId: number): Observable<void> {
    return this.http.delete<void>(this.cfg.url(`/festivales/api/dias/${diaId}/`));
  }

  /** Ubica (o saca, con diaId=null) un acto en un día de la agenda. */
  asignarActoDia(eventoId: number, diaId: number | null): Observable<unknown> {
    return this.http.patch(this.cfg.url(`/festivales/api/actos/${eventoId}/dia/`), {
      festival_dia_id: diaId,
    });
  }

  /** Fija la meta de aforo de un acto. */
  setAforoProyectado(eventoId: number, valor: number | null): Observable<unknown> {
    return this.http.patch(this.cfg.url(`/festivales/api/actos/${eventoId}/aforo-proyectado/`), {
      aforo_proyectado: valor,
    });
  }

  // ── PR-B · biblioteca / evidencias ─────────────────────────────────
  biblioteca(festivalId: number): Observable<FestivalArchivo[]> {
    return this.http.get<FestivalArchivo[]>(this.cfg.url(`${this.base}/${festivalId}/biblioteca/`));
  }

  subirArchivo(festivalId: number, data: FormData): Observable<FestivalArchivo> {
    return this.http.post<FestivalArchivo>(this.cfg.url(`${this.base}/${festivalId}/biblioteca/`), data);
  }

  eliminarArchivo(archivoId: number): Observable<void> {
    return this.http.delete<void>(this.cfg.url(`/festivales/api/biblioteca/${archivoId}/`));
  }

  /** Descarga el binario (descifrado en el server) como blob autenticado. */
  blob(archivoUrl: string): Observable<Blob> {
    return this.http.get(this.cfg.url(archivoUrl), { responseType: 'blob' });
  }

  // ── PR-E · lineup / jurados / criterios / evaluación / ranking ─────
  crearArtista(fid: number, data: Partial<FestivalArtista>): Observable<FestivalArtista> {
    return this.http.post<FestivalArtista>(this.cfg.url(`${this.base}/${fid}/artistas/`), data);
  }
  eliminarArtista(id: number): Observable<void> {
    return this.http.delete<void>(this.cfg.url(`/festivales/api/artistas/${id}/`));
  }
  crearJurado(fid: number, data: Partial<FestivalJurado>): Observable<FestivalJurado> {
    return this.http.post<FestivalJurado>(this.cfg.url(`${this.base}/${fid}/jurados/`), data);
  }
  eliminarJurado(id: number): Observable<void> {
    return this.http.delete<void>(this.cfg.url(`/festivales/api/jurados/${id}/`));
  }
  crearCriterio(fid: number, data: Partial<FestivalCriterio>): Observable<FestivalCriterio> {
    return this.http.post<FestivalCriterio>(this.cfg.url(`${this.base}/${fid}/criterios/`), data);
  }
  eliminarCriterio(id: number): Observable<void> {
    return this.http.delete<void>(this.cfg.url(`/festivales/api/criterios/${id}/`));
  }
  evaluar(artistaId: number, juradoId: number, criterioId: number, puntaje: number): Observable<unknown> {
    return this.http.post(this.cfg.url(`/festivales/api/evaluaciones/`), {
      artista_id: artistaId, jurado_id: juradoId, criterio_id: criterioId, puntaje,
    });
  }
  ranking(fid: number): Observable<RankingData> {
    return this.http.get<RankingData>(this.cfg.url(`${this.base}/${fid}/ranking/`));
  }
}
