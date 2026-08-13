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
    // Contratos INTERNOS de innovaK: los que llevan el valor, el CDP del que
    // sale la plata y el enganche a las actividades del plan.
    //
    // Va con ruta propia porque `contratos` la ocupa la lista de SECOP, que es
    // un espejo de SOLO LECTURA. Mientras estuvieron compartiendo camino, el
    // catch-all `:entidad` —que es el que trae el formulario con el campo
    // Valor— quedaba tapado por la de SECOP y no había forma de registrar el
    // dinero de un contrato desde la interfaz. Se llegaba a la pantalla, se
    // veían contratos, y ninguno era editable: el síntoma era «no hay dónde
    // poner el dinero».
    path: 'contratos-internos',
    data: { entidad: 'contratos' },
    loadComponent: () =>
      import('./presupuesto-entidad.component')
        .then((m) => m.PresupuestoEntidadComponent),
  },
  {
    // Lista general de contratos adjudicados (SECOP II). Antes del catch-all.
    path: 'contratos',
    loadComponent: () =>
      import('./contratos-oficiales.component').then((m) => m.ContratosOficialesComponent),
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
