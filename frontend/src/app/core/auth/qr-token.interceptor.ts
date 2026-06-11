import { HttpInterceptorFn } from '@angular/common/http';

/**
 * Interceptor del token HMAC de los QR públicos (hardening fase 1).
 *
 * Los QR generados por el backend apuntan a `/app/p/<form>/<id>?t=<HMAC>`.
 * Este interceptor lee el `t` de la URL de la página actual y lo reenvía
 * como query param en toda petición API relativa, para que
 * `QrTokenPermission` (backend) pueda validarlo.
 *
 * - Solo actúa en páginas públicas (`/p/` en el path) que traen `t`.
 * - No pisa un `t` que la petición ya traiga explícito.
 * - En el resto del SPA no hace nada.
 */
export const qrTokenInterceptor: HttpInterceptorFn = (req, next) => {
  const enPublico = window.location.pathname.includes('/p/');
  if (!enPublico) return next(req);

  const t = new URLSearchParams(window.location.search).get('t');
  if (!t) return next(req);

  // Solo peticiones same-origin (las páginas públicas solo llaman a la API propia).
  const externa = /^https?:\/\//.test(req.url) && !req.url.startsWith(window.location.origin);
  if (externa || req.params.has('t')) return next(req);

  return next(req.clone({ setParams: { t } }));
};
