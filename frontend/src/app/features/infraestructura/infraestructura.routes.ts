import { Routes } from '@angular/router';

export const INFRAESTRUCTURA_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./infra-panel.component').then((m) => m.InfraPanelComponent),
  },
  {
    // Insights antes de :id para que no lo capture el comodín de detalle.
    path: 'insights',
    loadComponent: () =>
      import('./infra-insights.component').then((m) => m.InfraInsightsComponent),
  },
  {
    path: ':id',
    loadComponent: () =>
      import('./infra-detalle.component').then((m) => m.InfraDetalleComponent),
  },
];
