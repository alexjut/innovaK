import { Routes } from '@angular/router';
import { authGuard } from './core/auth/auth.guard';
import { AuthLayoutComponent } from './core/layout/auth-layout/auth-layout.component';
import { LayoutComponent } from './core/layout/layout.component';

/**
 * Rutas top-level con dos layouts:
 *   - LayoutComponent: con topbar + sidebar + footer (área autenticada).
 *   - AuthLayoutComponent: gradiente institucional sin menú (login, etc.).
 *
 * El authGuard protege la ruta raíz: si el visitante no tiene token,
 * va a /auth/login automáticamente.
 */
export const routes: Routes = [
  {
    path: '',
    component: LayoutComponent,
    canActivate: [authGuard],
    children: [
      {
        path: '',
        pathMatch: 'full',
        loadComponent: () =>
          import('./features/dashboard/hub.component').then((m) => m.HubComponent),
      },
      {
        path: 'showcase',
        loadComponent: () =>
          import('./features/dashboard/showcase.component').then((m) => m.ShowcaseComponent),
      },
      {
        path: 'landing',
        loadComponent: () =>
          import('./features/dashboard/landing.component').then((m) => m.LandingComponent),
      },
      {
        // PR-6 Etapa D: feature Banco de Iniciativas (organizador).
        path: 'banco',
        loadChildren: () =>
          import('./features/banco-iniciativas/banco.routes').then((m) => m.BANCO_ROUTES),
      },
      // PR-7+: jovenes, caracterizacion, presupuesto, eventos, cursos, mapa, votaciones, admin.
    ],
  },

  // Rutas sin sidebar/topbar (login, reset, etc.).
  {
    path: 'auth',
    component: AuthLayoutComponent,
    children: [
      {
        path: 'login',
        loadComponent: () =>
          import('./features/auth/login.component').then((m) => m.LoginComponent),
      },
    ],
  },

  // Compat: /login → /auth/login.
  { path: 'login', redirectTo: 'auth/login', pathMatch: 'full' },

  // Fallback.
  { path: '**', redirectTo: '' },
];
