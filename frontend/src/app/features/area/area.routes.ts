import { Routes } from '@angular/router';

/**
 * `/app/mi-area/<nombre-del-area>/...`
 *
 * El segmento es el slug del subgrupo (`educacion`, `paz-memoria-y-
 * reconciliacion`), no su id. Verificado sobre los 45 subgrupos: 45 slugs
 * distintos, cero colisiones. El backend acepta slug o id, así que los
 * enlaces con id siguen resolviendo.
 */
export const AREA_ROUTES: Routes = [
  {
    // Herramientas que viven DENTRO de un área. Van antes de la ruta del
    // panel para que ':slug' no se las trague.
    path: ':slug/cai',
    loadComponent: () =>
      import('./area-cai.component').then((m) => m.AreaCaiComponent),
  },
  {
    // Formulación: lo que el área prepara ANTES de que exista el contrato.
    // Va antes de ':slug' como el CAI, para que el catch-all no se la trague.
    path: ':slug/formulacion',
    loadComponent: () =>
      import('./area-formulacion.component').then((m) => m.AreaFormulacionComponent),
  },
  {
    path: ':slug',
    loadComponent: () =>
      import('./area-panel.component').then((m) => m.AreaPanelComponent),
  },
];
