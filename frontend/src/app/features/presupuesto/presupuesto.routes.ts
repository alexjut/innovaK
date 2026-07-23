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
    // Estructura oficial del Plan (Programa→Objetivo→Proyecto→Meta). Antes del catch-all.
    path: 'plan-oficial',
    loadComponent: () =>
      import('./plan-oficial.component').then((m) => m.PlanOficialComponent),
  },
  // Listas OFICIALES (reemplazan el catálogo interno viejo en la UI). Antes del catch-all.
  {
    path: 'metas',
    data: { tipo: 'metas' },
    loadComponent: () => import('./oficial-lista.component').then((m) => m.OficialListaComponent),
  },
  {
    path: 'proyectos',
    data: { tipo: 'proyectos' },
    loadComponent: () => import('./oficial-lista.component').then((m) => m.OficialListaComponent),
  },
  {
    path: 'programas',
    data: { tipo: 'programas' },
    loadComponent: () => import('./oficial-lista.component').then((m) => m.OficialListaComponent),
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
