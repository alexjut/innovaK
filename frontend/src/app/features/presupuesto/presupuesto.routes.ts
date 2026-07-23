import { Routes } from '@angular/router';

export const PRESUPUESTO_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./presupuesto-hub.component').then((m) => m.PresupuestoHubComponent),
  },
  {
    // Vista 360° del proyecto (ruta específica, tiene precedencia).
    path: 'proyectos/:id',
    loadComponent: () =>
      import('./proyecto-360.component').then((m) => m.Proyecto360Component),
  },
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./presupuesto-dashboard.component')
        .then((m) => m.PresupuestoDashboardComponent),
  },
  {
    // Actividades SIPSE agrupadas por subgrupo (antes del catch-all :entidad).
    path: 'actividades',
    loadComponent: () =>
      import('./actividades-subgrupo.component')
        .then((m) => m.ActividadesSubgrupoComponent),
  },
  {
    // Avance por sector = subgrupo (alineación Visor SDP-PDL). Antes del catch-all.
    path: 'sectores',
    loadComponent: () =>
      import('./sectores.component').then((m) => m.PresupuestoSectoresComponent),
  },
  {
    // Comparación interno vs oficial SDP (Planeación). Antes del catch-all.
    path: 'comparacion-sdp',
    loadComponent: () =>
      import('./comparacion-sdp.component').then((m) => m.ComparacionSdpComponent),
  },
  {
    // Detalle rico de KPI / CDP / contrato.
    path: ':entidad/:id',
    loadComponent: () =>
      import('./presupuesto-detail.component')
        .then((m) => m.PresupuestoDetailComponent),
  },
  {
    // Catch-all por entidad: proyectos, programas, objetivos, metas,
    // conceptos, cdps, contratos, indicadores, avances,
    // meta-proyecto, actividad-indicador.
    path: ':entidad',
    loadComponent: () =>
      import('./presupuesto-entidad.component')
        .then((m) => m.PresupuestoEntidadComponent),
  },
];
