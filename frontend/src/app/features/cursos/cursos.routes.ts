import { Routes } from '@angular/router';

export const CURSOS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./cursos-list.component').then((m) => m.CursosListComponent),
  },
  {
    path: 'insights',
    loadComponent: () =>
      import('./cursos-insights.component').then((m) => m.CursosInsightsComponent),
  },
  {
    path: ':id',
    loadComponent: () =>
      import('./curso-detalle.component').then((m) => m.CursoDetalleComponent),
  },
];
