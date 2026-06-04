import { Routes } from '@angular/router';

/**
 * Rutas del feature Entregas de insumos (organizador autenticado).
 * Conectadas en `app.routes.ts` con `loadChildren` (lazy).
 */
export const ENTREGAS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./entregas-list.component').then((m) => m.EntregasListComponent),
  },
  {
    path: ':id',
    loadComponent: () =>
      import('./entrega-detail.component').then((m) => m.EntregaDetailComponent),
  },
];
