import { Routes } from '@angular/router';

export const VOTACIONES_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./votaciones-list.component').then((m) => m.VotacionesListComponent),
  },
  {
    path: ':id',
    loadComponent: () =>
      import('./votaciones-detail.component').then((m) => m.VotacionesDetailComponent),
  },
];
