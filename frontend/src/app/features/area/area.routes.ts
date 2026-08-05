import { Routes } from '@angular/router';

export const AREA_ROUTES: Routes = [
  {
    // Herramientas que viven DENTRO de un área. Van antes de la ruta del
    // panel para que ':id' no se las trague.
    path: ':id/cai',
    loadComponent: () =>
      import('./area-cai.component').then((m) => m.AreaCaiComponent),
  },
  {
    path: ':id',
    loadComponent: () =>
      import('./area-panel.component').then((m) => m.AreaPanelComponent),
  },
];
