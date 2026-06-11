import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { ConfigService } from './config/config.service';

/**
 * Descargas autenticadas (full Angular, PR-0).
 *
 * Reemplaza a `window.open(urlExport)`: un window.open no puede mandar
 * el header `Authorization: Bearer`, así que dependía de la sesión
 * Django del HTML viejo. Este servicio baja el archivo vía HttpClient
 * (el interceptor JWT agrega el Bearer) y dispara la descarga local.
 */
@Injectable({ providedIn: 'root' })
export class DescargasService {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  /** Descarga `path` (relativo al backend) y la guarda con `nombre`
   *  (o el filename del Content-Disposition si no se pasa). */
  descargar(path: string, nombre?: string): void {
    this.http
      .get(this.cfg.url(path), { responseType: 'blob', observe: 'response' })
      .subscribe({
        next: (res) => {
          const cd = res.headers.get('Content-Disposition') || '';
          const m = /filename\*?=(?:UTF-8'')?"?([^";]+)/i.exec(cd);
          const filename = nombre || (m ? decodeURIComponent(m[1].trim()) : 'descarga');
          const url = URL.createObjectURL(res.body as Blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = filename;
          a.click();
          URL.revokeObjectURL(url);
        },
        error: () => {
          alert('No se pudo descargar el archivo. Intenta de nuevo.');
        },
      });
  }
}
