import { Routes } from '@angular/router';

export const EDUCACION_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./colegios-list.component').then((m) => m.ColegiosListComponent),
  },
  {
    // Antes que ':id' — si no, 'resumen' se leería como un id.
    path: 'resumen/:vigencia',
    loadComponent: () =>
      import('./resumen-vigencia.component').then((m) => m.ResumenVigenciaComponent),
  },
  {
    path: ':id',
    loadComponent: () =>
      import('./colegio-detalle.component').then((m) => m.ColegioDetalleComponent),
  },
];
