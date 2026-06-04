import { Routes } from '@angular/router';

/**
 * Rutas del feature Banco de Iniciativas.
 *
 * Conectadas en `app.routes.ts` con `loadChildren` para que todo el
 * feature se cargue lazy (solo cuando el usuario navega a /banco).
 */
export const BANCO_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./inscripciones-list.component').then((m) => m.InscripcionesListComponent),
  },
  {
    path: 'insights',
    loadComponent: () =>
      import('./insights.component').then((m) => m.BancoInsightsComponent),
  },
  {
    path: ':id',
    loadComponent: () =>
      import('./inscripcion-detail.component').then((m) => m.InscripcionDetailComponent),
  },
];
