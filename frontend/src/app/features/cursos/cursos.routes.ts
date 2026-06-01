import { Routes } from '@angular/router';

export const CURSOS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./cursos-placeholder.component').then((m) => m.CursosPlaceholderComponent),
  },
];
