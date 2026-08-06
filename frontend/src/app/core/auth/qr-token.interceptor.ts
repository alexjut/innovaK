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
 *
 * Desde S-1 también manda **`evento`**, el id que ya está en el path de la
 * página. El token es HMAC *por evento*, así que sin saber de qué evento se
 * trata no se puede verificar: los endpoints que reciben el id por la URL lo
 * sacan de ahí, pero los que lo reciben por query —`/caracterizacion/api/persona/`
 * y el `validate-voter` de votaciones— no tenían con qué. Mandarlo acá, una vez,
 * evita tocar los cuatro formularios y que uno se olvide.
 */
export const qrTokenInterceptor: HttpInterceptorFn = (req, next) => {
  const enPublico = window.location.pathname.includes('/p/');
  if (!enPublico) return next(req);

  const t = new URLSearchParams(window.location.search).get('t');
  if (!t) return next(req);

  // Solo peticiones same-origin (las páginas públicas solo llaman a la API propia).
  const externa = /^https?:\/\//.test(req.url) && !req.url.startsWith(window.location.origin);
  if (externa || req.params.has('t')) return next(req);

  const extra: Record<string, string> = { t };
  // El id del evento es el último segmento del path público (`/p/<form>/<id>`).
  // Se exige numérico a propósito: hay rutas públicas que terminan en slug
  // (`/p/festival/:slug`), y mandar un slug como `evento` sería ruido.
  const ultimo = window.location.pathname.split('/').filter(Boolean).pop() || '';
  if (/^\d+$/.test(ultimo) && !req.params.has('evento')) extra['evento'] = ultimo;

  return next(req.clone({ setParams: extra }));
};
