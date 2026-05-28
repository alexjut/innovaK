import { Routes } from '@angular/router';

/**
 * Rutas top-level.
 *
 * Convención: todas las features se cargan con `loadComponent` (lazy)
 * para minimizar el bundle inicial. PR-3+ irá agregando una entrada
 * por feature.
 */
export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    loadComponent: () =>
      import('./features/dashboard/landing.component').then((m) => m.LandingComponent),
  },
  {
    // PR-2: UI showcase de componentes `.ui-*` migrados desde Django.
    // En PR-15 se moverá a `/dev/showcase` y se servirá solo fuera de prod.
    path: 'showcase',
    loadComponent: () =>
      import('./features/dashboard/showcase.component').then((m) => m.ShowcaseComponent),
  },
  // PR-4: { path: 'login', loadComponent: ... }
  // PR-5: { path: 'dashboard', canActivate: [authGuard], loadComponent: ... }
  // PR-6+: features de negocio.
  {
    path: '**',
    redirectTo: '',
  },
];
