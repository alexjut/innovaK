import { Routes } from '@angular/router';

/**
 * Rutas del feature Jóvenes a la E.
 * Conectadas en `app.routes.ts` con `loadChildren` (lazy).
 */
export const JOVENES_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./entregas-list.component').then((m) => m.EntregasListComponent),
  },
  {
    path: 'insights',
    loadComponent: () =>
      import('./insights.component').then((m) => m.JovenesInsightsComponent),
  },
  {
    path: ':id',
    loadComponent: () =>
      import('./entrega-detail.component').then((m) => m.EntregaDetailComponent),
  },
];
