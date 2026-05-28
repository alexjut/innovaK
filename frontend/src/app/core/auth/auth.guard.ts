import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';

/**
 * Guard para rutas privadas. Bloquea acceso si no hay token activo.
 *
 * Uso en app.routes.ts:
 *   { path: 'dashboard', canActivate: [authGuard], loadComponent: ... }
 *
 * Si no está autenticado, redirige a /auth/login con `?next=<originalUrl>`
 * para volver a la ruta original tras el login.
 */
export const authGuard: CanActivateFn = (route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (auth.isAuthenticated()) return true;

  const next = state.url && state.url !== '/' ? state.url : null;
  router.navigate(['/auth/login'], { queryParams: next ? { next } : {} });
  return false;
};
