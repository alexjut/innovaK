import { HttpClient } from '@angular/common/http';
import { Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';
import { ConfigService } from '../config/config.service';
import { TokenStorage } from './token.storage';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
}

/**
 * Servicio singleton de autenticación.
 *
 * Usa signals (Angular 17+) para el estado reactivo del usuario.
 * Hace login contra `/api/token/` y guarda tokens vía TokenStorage.
 *
 * Para que sea reusable en otra alcaldía con su mismo backend:
 * solo cambia `apiBaseUrl` en environment.ts y este servicio sigue
 * funcionando idéntico.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  /** Signal reactivo: true si hay access token. No verifica expiración. */
  readonly isAuthenticated = signal<boolean>(false);

  constructor(
    private http: HttpClient,
    private tokens: TokenStorage,
    private cfg: ConfigService,
    private router: Router,
  ) {
    this.isAuthenticated.set(this.tokens.hasAccess());
  }

  login(payload: LoginRequest): Observable<LoginResponse> {
    return this.http
      .post<LoginResponse>(this.cfg.url('/api/token/'), payload)
      .pipe(
        tap((res) => {
          this.tokens.setAccess(res.access);
          this.tokens.setRefresh(res.refresh);
          this.isAuthenticated.set(true);
        }),
      );
  }

  logout(): void {
    this.tokens.clear();
    this.isAuthenticated.set(false);
    this.router.navigateByUrl('/login');
  }
}
