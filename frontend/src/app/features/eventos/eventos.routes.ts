import { Routes } from '@angular/router';

export const EVENTOS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./eventos-list.component').then((m) => m.EventosListComponent),
  },
  {
    path: 'nueva',
    loadComponent: () =>
      import('./evento-form.component').then((m) => m.EventoFormComponent),
  },
  {
    path: 'tipos',
    loadComponent: () =>
      import('./tipos-evento.component').then((m) => m.TiposEventoComponent),
  },
  {
    path: 'insights',
    loadComponent: () =>
      import('./eventos-insights.component').then((m) => m.EventosInsightsComponent),
  },
  {
    path: ':id/editar',
    loadComponent: () =>
      import('./evento-form.component').then((m) => m.EventoFormComponent),
  },
  {
    path: ':id/qr',
    loadComponent: () =>
      import('./evento-qr.component').then((m) => m.EventoQrComponent),
  },
];
