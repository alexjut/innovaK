import { Routes } from '@angular/router';

export const ADMIN_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./admin-hub.component').then((m) => m.AdminHubComponent),
  },
  {
    path: ':area',
    loadComponent: () =>
      import('./admin-legacy.component').then((m) => m.AdminLegacyComponent),
  },
];
