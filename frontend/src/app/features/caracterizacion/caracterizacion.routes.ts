import { Routes } from '@angular/router';

export const CARACTERIZACION_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./caracterizacion-hub.component').then((m) => m.CaracterizacionHubComponent),
  },
  {
    // Cultura y Seguridad tienen página propia con las 3 fichas
    // (Individuo/Organización/Lugar). El sector llega por `data`.
    path: 'cultura',
    data: { sector: 'cultura' },
    loadComponent: () =>
      import('./cultura-fichas.component').then((m) => m.CulturaFichasComponent),
  },
  {
    path: 'seguridad',
    data: { sector: 'seguridad' },
    loadComponent: () =>
      import('./cultura-fichas.component').then((m) => m.CulturaFichasComponent),
  },
  {
    path: ':sector',
    loadComponent: () =>
      import('./caracterizacion-list.component').then((m) => m.CaracterizacionListComponent),
  },
  {
    path: ':sector/:id',
    loadComponent: () =>
      import('./caracterizacion-detail.component').then(
        (m) => m.CaracterizacionDetailComponent,
      ),
  },
  {
    // Caracterizaciones capturadas para un evento específico.
    // Llega desde Actividades → tipo CARACTERIZACION → click "Caracterizaciones".
    path: 'evento/:id',
    loadComponent: () =>
      import('./caracterizaciones-evento.component').then(
        (m) => m.CaracterizacionesEventoComponent,
      ),
  },
];
