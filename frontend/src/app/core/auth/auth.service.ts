import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
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
 * Perfil del usuario autenticado.
 *
 * Lo devuelve `GET /api/me/` (apps/login/api/views.py::MeView).
 */
export interface UserProfile {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  is_superuser: boolean;
  is_staff: boolean;
  groups: string[];
  modules: string[];
}

/**
 * Servicio singleton de autenticación.
 *
 * Estado reactivo con signals:
 *   - isAuthenticated(): hay access token o no.
 *   - user(): perfil del usuario (null mientras no se haya cargado).
 *   - modules(): Set<string> de códigos de módulo N15 del usuario.
 *   - displayName(): nombre legible para topbar.
 *   - hasModule(codigo): helper para gating de UI (cards, sidebar items).
 *
 * Flujo:
 *   - login() POST /api/token/ → guarda tokens → fetchMe() → user().
 *   - logout() limpia tokens y user → redirect /auth/login.
 *   - Al boot, si hay token, llama fetchMe() automáticamente.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private tokens = inject(TokenStorage);
  private cfg = inject(ConfigService);
  private router = inject(Router);

  /** Hay access token (NO verifica expiración). */
  readonly isAuthenticated = signal<boolean>(false);

  /** Perfil del usuario (null si no cargado). */
  readonly user = signal<UserProfile | null>(null);

  /** Set de módulos asignados al usuario (más rápido para .has()). */
  readonly modules = computed<Set<string>>(
    () => new Set(this.user()?.modules ?? []),
  );

  /** Nombre legible para mostrar en topbar. */
  readonly displayName = computed<string>(() => {
    const u = this.user();
    if (!u) return 'Invitado';
    const name = `${u.first_name} ${u.last_name}`.trim();
    return name || u.username;
  });

  constructor() {
    this.isAuthenticated.set(this.tokens.hasAccess());
    if (this.tokens.hasAccess()) {
      this.fetchMe().subscribe({
        error: () => {
          // Token presente pero rechazado → forzar logout silencioso.
          this.tokens.clear();
          this.isAuthenticated.set(false);
        },
      });
    }
  }

  login(payload: LoginRequest): Observable<LoginResponse> {
    return this.http
      .post<LoginResponse>(this.cfg.url('/api/token/'), payload)
      .pipe(
        tap((res) => {
          this.tokens.setAccess(res.access);
          this.tokens.setRefresh(res.refresh);
          this.isAuthenticated.set(true);
          // Cargar perfil en paralelo (no bloquea el resolve del login).
          this.fetchMe().subscribe();
        }),
      );
  }

  /**
   * GET /api/me/ — actualiza el signal user() con la respuesta.
   * Devuelve Observable para que el caller decida si necesita esperar.
   */
  fetchMe(): Observable<UserProfile> {
    return this.http.get<UserProfile>(this.cfg.url('/api/me/')).pipe(
      tap((profile) => this.user.set(profile)),
    );
  }

  logout(): void {
    this.tokens.clear();
    this.user.set(null);
    this.isAuthenticated.set(false);
    this.router.navigateByUrl('/auth/login');
  }

  /** Helper de gating: ¿el usuario tiene este módulo asignado? */
  hasModule(codigo: string): boolean {
    if (this.user()?.is_superuser) return true;
    return this.modules().has(codigo);
  }
}
