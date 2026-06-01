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
    path: ':id/editar',
    loadComponent: () =>
      import('./evento-form.component').then((m) => m.EventoFormComponent),
  },
];
