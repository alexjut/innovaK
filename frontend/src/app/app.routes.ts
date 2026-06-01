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
      {
        // PR-7 Etapa D: feature Jóvenes a la E (organizador).
        path: 'jovenes',
        loadChildren: () =>
          import('./features/jovenes-a-la-e/jovenes.routes').then((m) => m.JOVENES_ROUTES),
      },
      {
        // PR-8 Etapa D: 6 sectores de Caracterización ciudadana.
        path: 'caracterizacion',
        loadChildren: () =>
          import('./features/caracterizacion/caracterizacion.routes').then(
            (m) => m.CARACTERIZACION_ROUTES,
          ),
      },
      {
        // PR-9 Etapa D: Presupuesto (proyectos, indicadores, CDPs, contratos).
        path: 'presupuesto',
        loadChildren: () =>
          import('./features/presupuesto/presupuesto.routes').then(
            (m) => m.PRESUPUESTO_ROUTES,
          ),
      },
      {
        // PR-10 Etapa D: Eventos (placeholder; CRUD completo cuando llegue DRF).
        path: 'eventos',
        loadChildren: () =>
          import('./features/eventos/eventos.routes').then((m) => m.EVENTOS_ROUTES),
      },
      {
        // PR-11 Etapa D: Cursos del docente (placeholder; cliente API listo).
        path: 'cursos',
        loadChildren: () =>
          import('./features/cursos/cursos.routes').then((m) => m.CURSOS_ROUTES),
      },
      {
        // PR-12 Etapa D: Mapa Kennedy (iframe al mapa Django).
        path: 'mapa',
        loadChildren: () =>
          import('./features/mapa/mapa.routes').then((m) => m.MAPA_ROUTES),
      },
      // PR-13+: admin, votaciones.
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
