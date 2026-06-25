import { Routes } from '@angular/router';

export const SUBGRUPO_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./subgrupo-panel.component').then((m) => m.SubgrupoPanelComponent),
  },
  {
    path: ':id',
    loadComponent: () =>
      import('./subgrupo-detalle.component').then((m) => m.SubgrupoDetalleComponent),
  },
];
