import { Injectable } from '@angular/core';
import { ConfigService } from '../config/config.service';

/**
 * Storage de tokens JWT en localStorage.
 *
 * - access token: vida 15 min (lo refrescamos antes que expire).
 * - refresh token: vida 7 días (se elimina al logout).
 *
 * Encapsulado aquí para que mañana podamos cambiar a IndexedDB,
 * cookies httpOnly o sessionStorage sin tocar el resto del código.
 */
@Injectable({ providedIn: 'root' })
export class TokenStorage {
  constructor(private cfg: ConfigService) {}

  getAccess(): string | null {
    return localStorage.getItem(this.cfg.jwtAccessKey);
  }

  setAccess(token: string): void {
    localStorage.setItem(this.cfg.jwtAccessKey, token);
  }

  getRefresh(): string | null {
    return localStorage.getItem(this.cfg.jwtRefreshKey);
  }

  setRefresh(token: string): void {
    localStorage.setItem(this.cfg.jwtRefreshKey, token);
  }

  clear(): void {
    localStorage.removeItem(this.cfg.jwtAccessKey);
    localStorage.removeItem(this.cfg.jwtRefreshKey);
  }

  hasAccess(): boolean {
    return !!this.getAccess();
  }
}
