import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';

/**
 * Guard para rutas privadas. Bloquea acceso si no hay token activo.
 *
 * Uso en app.routes.ts:
 *   { path: 'dashboard', canActivate: [authGuard], loadComponent: ... }
 */
export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (auth.isAuthenticated()) return true;
  router.navigateByUrl('/login');
  return false;
};
