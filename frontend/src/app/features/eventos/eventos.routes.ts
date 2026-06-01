import { Routes } from '@angular/router';

export const EVENTOS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./eventos-placeholder.component').then((m) => m.EventosPlaceholderComponent),
  },
];
