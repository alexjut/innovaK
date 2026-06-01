import { Routes } from '@angular/router';

export const CURSOS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./cursos-list.component').then((m) => m.CursosListComponent),
  },
  {
    path: ':id',
    loadComponent: () =>
      import('./curso-detalle.component').then((m) => m.CursoDetalleComponent),
  },
];
