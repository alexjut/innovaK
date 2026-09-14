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
  // Las dos pantallas que se fundieron en «Metas». Quedan como redirección y
  // no borradas: hay enlaces y marcadores apuntando acá, y una URL que muere
  // en un 404 es peor que una que lleva al sitio nuevo.
  //
  // `pathMatch: 'full'` es obligatorio: sin él se llevaría por delante el
  // detalle `indicadores/:id`, que sigue vivo y lo sirve `:entidad/:id`.
  { path: 'indicadores', redirectTo: 'metas', pathMatch: 'full' },
  { path: 'meta-proyecto', redirectTo: 'metas', pathMatch: 'full' },
  // `actividad-indicador` era la tabla puente cruda —«Actividad #», «KPI #»—
  // y encima ofrecía los 77 KPIs de la localidad sin filtrar por proyecto.
  // Vive dentro de «Actividades SIPSE» desde el 2026-09-14: ahí la actividad
  // ya estaba en pantalla con sus metas, solo faltaba poder tocarlas.
  //
  // Redirección y no borrado: `/presupuesto/actividad-indicador/` de Django
  // sigue apuntando acá (y su test lo comprueba), así que la cadena es
  // legacy → SPA → actividades.
  { path: 'actividad-indicador', redirectTo: 'actividades', pathMatch: 'full' },
  // `plan-oficial` y `metas` eran la MISMA pantalla. Verificado siguiendo las
  // dos hasta el SQL: las dos terminan en `plan_matriz._metas_crudas()` sin un
  // WHERE que las distinga, y devuelven las mismas 78 filas con las mismas 23
  // claves. La tarjeta de plan-oficial era además un subconjunto estricto de
  // la de metas —mismos 4 stats, misma ruta Objetivo›Programa›Proyecto— hasta
  // con el string de vacío copiado letra por letra.
  //
  // Antes de traer a su gente había que arreglar dos cosas en `metas`, o el
  // merge la empeoraba: el chip ahora muestra `codigo_meta` (el código SEGPLAN
  // que el funcionario reconoce, 26881) y no el consecutivo interno; y el
  // cumplimiento ya no se pinta 100 veces más chico. Sin eso, fundir habría
  // borrado el único sitio donde se ve el código bueno y habría trasladado un
  // defecto a la única pantalla que queda.
  { path: 'plan-oficial', redirectTo: 'metas', pathMatch: 'full' },
  // Dos detalles que caían en tablas MUERTAS y por eso se veían plausibles,
  // que es peor que verse vacíos:
  //   · `programas/<id>` servía la tabla `programas` (7 filas, 3 de prueba) y
  //     como el código no es el id, pedir el 10 devolvía OTRO programa real.
  //   · `cdps/<id>` servía la tabla interna `cdp` (5 filas, 4 placeholders sin
  //     número ni valor) y con un id bajo entregaba un saldo negativo
  //     inventado. El detalle de verdad ya está en el desplegable de /plan/cdps.
  // Ningún enlace de la app las produce, pero sobreviven en marcadores.
  { path: 'programas/:id', redirectTo: 'programas', pathMatch: 'full' },
  { path: 'cdps/:id', redirectTo: 'cdps', pathMatch: 'full' },
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
    // En qué se gasta. Antes del catch-all `:entidad`, que la servía con la
    // tabla interna `concepto_gasto` — una fila, y es una prueba.
    path: 'conceptos',
    loadComponent: () => import('./gasto.component').then((m) => m.GastoComponent),
  },
  {
    // Los CDP del Fondo con sus CRP. Antes del catch-all `:entidad`, que la
    // servía con la tabla interna de 5 filas —cuatro de ellas cáscaras sin
    // número— y una columna Proyecto que salía vacía siempre.
    path: 'cdps',
    loadComponent: () =>
      import('./cdps-fuentes.component').then((m) => m.CdpsFuentesComponent),
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
    // conceptos, cdps, contratos, indicadores, avances, meta-proyecto.
    path: ':entidad',
    loadComponent: () =>
      import('./presupuesto-entidad.component')
        .then((m) => m.PresupuestoEntidadComponent),
  },
];
