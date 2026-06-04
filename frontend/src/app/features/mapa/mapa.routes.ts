import { Routes } from '@angular/router';

export const MAPA_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./mapa.component').then((m) => m.MapaKennedyComponent),
  },
];
