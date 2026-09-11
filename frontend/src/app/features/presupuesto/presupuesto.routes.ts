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
    // La Matriz frente a BogData, proyecto por proyecto. Vive en la sección
    // «Las fuentes» del hub y NO como pestaña del tablero: el tablero es
    // página única a propósito, y sus cinco pestañas se quitaron por esconder
    // el contenido tras dos clics.
    path: 'fuentes',
    loadComponent: () =>
      import('./fuentes.component').then((m) => m.FuentesComponent),
  },
  {
    // Comparación interno vs oficial SDP (Planeación). Antes del catch-all.
    path: 'comparacion-sdp',
    loadComponent: () =>
      import('./comparacion-sdp.component').then((m) => m.ComparacionSdpComponent),
  },
  {
    // Subir la Matriz PDL. Antes del catch-all como el resto.
    path: 'matriz',
    loadComponent: () =>
      import('./matriz-carga.component').then((m) => m.MatrizCargaComponent),
  },
  {
    // Objetivos estratégicos del PDL. Va ANTES del catch-all porque sin ruta
    // propia caía en `:entidad`, que la servía con la tabla `objetivo` —el
    // catálogo del Banco de Iniciativas, con filas llamadas «prueba»— en vez
    // de los 5 ejes del Plan.
    path: 'objetivos',
    loadComponent: () =>
      import('./objetivos/objetivos-pdl.component').then((m) => m.ObjetivosPdlComponent),
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
    // El mismo contrato visto por SECOP, BogData e innovaK. Va antes de
    // `contratos` y del catch-all: si quedara después, `:entidad` se la comía.
    path: 'contratos-fuentes',
    loadComponent: () =>
      import('./contratos-fuentes.component').then((m) => m.ContratosFuentesComponent),
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
