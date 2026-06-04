import { Routes } from '@angular/router';

export const VOTACIONES_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./votaciones-list.component').then((m) => m.VotacionesListComponent),
  },
  {
    path: 'votantes',
    loadComponent: () =>
      import('./votaciones-votantes.component').then((m) => m.VotacionesVotantesComponent),
  },
  {
    path: ':id',
    loadComponent: () =>
      import('./votaciones-detail.component').then((m) => m.VotacionesDetailComponent),
  },
];
