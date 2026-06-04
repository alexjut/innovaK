import { Routes } from '@angular/router';

export const ACTIVIDADES_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./actividades-hub.component').then((m) => m.ActividadesHubComponent),
  },
  {
    path: 'tipo/:codigo',
    loadComponent: () =>
      import('./actividades-tipo.component').then((m) => m.ActividadesTipoComponent),
  },
  {
    path: 'tipo/:codigo/sub/:subgrupo',
    loadComponent: () =>
      import('./actividades-eventos.component').then((m) => m.ActividadesEventosComponent),
  },
];
