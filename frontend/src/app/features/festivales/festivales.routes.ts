import { Routes } from '@angular/router';

export const FESTIVALES_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./festivales-list.component').then((m) => m.FestivalesListComponent),
  },
];
