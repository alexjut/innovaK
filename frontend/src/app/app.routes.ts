import { Routes } from '@angular/router';
import { authGuard } from './core/auth/auth.guard';
import { AuthLayoutComponent } from './core/layout/auth-layout/auth-layout.component';
import { LayoutComponent } from './core/layout/layout.component';

/**
 * Rutas top-level con dos layouts:
 *   - LayoutComponent: con topbar + sidebar + footer (área autenticada).
 *   - AuthLayoutComponent: gradiente institucional sin menú (login, etc.).
 */
export const routes: Routes = [
  // Rutas con layout autenticado.
  {
    path: '',
    component: LayoutComponent,
    children: [
      {
        path: '',
        pathMatch: 'full',
        loadComponent: () =>
          import('./features/dashboard/landing.component').then((m) => m.LandingComponent),
      },
      {
        // PR-2: UI showcase de componentes `.ui-*` migrados desde Django.
        path: 'showcase',
        loadComponent: () =>
          import('./features/dashboard/showcase.component').then((m) => m.ShowcaseComponent),
      },
      // PR-5+: features de negocio (gated por authGuard).
      // { path: 'dashboard', canActivate: [authGuard], loadComponent: ... },
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
      // PR futuro: reset password, registro.
    ],
  },

  // Compat: /login → /auth/login para que el interceptor JWT pueda
  // hacer redirect simple.
  {
    path: 'login',
    redirectTo: 'auth/login',
    pathMatch: 'full',
  },

  // Fallback.
  {
    path: '**',
    redirectTo: '',
  },
];
