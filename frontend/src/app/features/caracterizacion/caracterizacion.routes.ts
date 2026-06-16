import { Routes } from '@angular/router';

export const CARACTERIZACION_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./caracterizacion-hub.component').then((m) => m.CaracterizacionHubComponent),
  },
  {
    // Wizard INTERNO (funcionario sin QR). Reusa el mismo componente
    // schema-driven del público en modo 'interno': el sector va en la URL
    // y escribe a la tabla dedicada del sector.
    path: 'registrar/:sector',
    data: { modo: 'interno' },
    loadComponent: () =>
      import('../publico/caracterizacion-publico.component').then(
        (m) => m.CaracterizacionPublicoComponent,
      ),
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
