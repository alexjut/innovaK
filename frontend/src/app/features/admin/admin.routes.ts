import { Routes } from '@angular/router';

export const ADMIN_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./admin-hub.component').then((m) => m.AdminHubComponent),
  },
  {
    path: 'roles',
    loadComponent: () =>
      import('./admin-roles.component').then((m) => m.AdminRolesComponent),
  },
  {
    path: 'roles/:id',
    loadComponent: () =>
      import('./admin-rol-detalle.component').then((m) => m.AdminRolDetalleComponent),
  },
  {
    path: 'org',
    loadComponent: () =>
      import('./admin-org.component').then((m) => m.AdminOrgComponent),
  },
  {
    path: 'personas',
    loadComponent: () =>
      import('./admin-personas.component').then((m) => m.AdminPersonasComponent),
  },
];
