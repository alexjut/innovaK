import { Routes } from '@angular/router';

export const PRESUPUESTO_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./presupuesto-hub.component').then((m) => m.PresupuestoHubComponent),
  },
  {
    path: ':entidad',
    loadComponent: () =>
      import('./presupuesto-list.component').then((m) => m.PresupuestoListComponent),
  },
  {
    path: ':entidad/:id',
    loadComponent: () =>
      import('./presupuesto-detail.component').then((m) => m.PresupuestoDetailComponent),
  },
];
