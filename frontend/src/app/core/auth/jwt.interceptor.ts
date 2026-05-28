import { HttpErrorResponse, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, catchError, switchMap, throwError } from 'rxjs';
import { ConfigService } from '../config/config.service';
import { TokenStorage } from './token.storage';

/**
 * Interceptor JWT global (Angular 17+ functional style).
 *
 * Responsabilidades:
 *
 * 1. Agregar `Authorization: Bearer <access>` a toda petición que vaya
 *    al `apiBaseUrl` (no agrega para llamadas a otros dominios).
 *
 * 2. Cuando un endpoint devuelve 401 (token expirado), intenta refrescar
 *    con `/api/token/refresh/` UNA SOLA VEZ. Si el refresh funciona,
 *    reintenta la petición original con el nuevo access token. Si el
 *    refresh falla, limpia tokens y redirige a /login.
 *
 * 3. Si el endpoint es AllowAny (formularios públicos), el backend ignora
 *    el header y todo sigue normal. Por eso es seguro agregar el header
 *    siempre que se tenga token, sin distinguir endpoints.
 */
export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  const tokens = inject(TokenStorage);
  const cfg = inject(ConfigService);
  const router = inject(Router);

  // No tocamos peticiones a dominios externos.
  if (!req.url.startsWith(cfg.apiBaseUrl) && !req.url.startsWith('/')) {
    return next(req);
  }

  const access = tokens.getAccess();
  const authed = access ? attachToken(req, access) : req;

  return next(authed).pipe(
    catchError((err: HttpErrorResponse) => {
      const isRefreshAttempt = req.url.includes('/api/token/refresh/');
      if (err.status === 401 && access && !isRefreshAttempt) {
        return refreshAndRetry(authed, tokens, cfg, router);
      }
      return throwError(() => err);
    }),
  );
};

function attachToken(req: HttpRequest<unknown>, token: string): HttpRequest<unknown> {
  return req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
}

function refreshAndRetry(
  originalReq: HttpRequest<unknown>,
  tokens: TokenStorage,
  cfg: ConfigService,
  router: Router,
): Observable<any> {
  const refreshToken = tokens.getRefresh();
  if (!refreshToken) {
    tokens.clear();
    router.navigateByUrl('/login');
    return throwError(() => new Error('No refresh token'));
  }

  // Intentamos refrescar usando fetch nativo para no recursar en el interceptor.
  return new Observable<string>((subscriber) => {
    fetch(cfg.url('/api/token/refresh/'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: refreshToken }),
    })
      .then(async (r) => {
        if (!r.ok) throw new Error(`refresh failed ${r.status}`);
        const data = (await r.json()) as { access: string };
        tokens.setAccess(data.access);
        subscriber.next(data.access);
        subscriber.complete();
      })
      .catch((e) => subscriber.error(e));
  }).pipe(
    switchMap((newAccess) => {
      const retried = attachToken(originalReq, newAccess);
      // Re-ejecutar la petición. Como ya tenemos nuevo access, no
      // entra en bucle.
      return new Observable((subscriber) => {
        fetch(retried.url, {
          method: retried.method,
          headers: { Authorization: `Bearer ${newAccess}` },
        }).then((r) => {
          subscriber.next(r);
          subscriber.complete();
        });
      });
    }),
    catchError((e) => {
      tokens.clear();
      router.navigateByUrl('/login');
      return throwError(() => e);
    }),
  );
}
