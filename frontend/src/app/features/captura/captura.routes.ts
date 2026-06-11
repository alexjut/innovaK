import { Routes } from '@angular/router';

export const CAPTURA_ROUTES: Routes = [
  {
    path: 'insights',
    loadComponent: () =>
      import('./captura-insights.component').then((m) => m.CapturaInsightsComponent),
  },
  {
    path: '',
    loadComponent: () =>
      import('./captura-list.component').then((m) => m.CapturaListComponent),
  },
];
