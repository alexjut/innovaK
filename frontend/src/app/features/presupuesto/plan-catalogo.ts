/**
 * Qué páginas tiene el Plan, a cuál entrada pertenece cada una y qué módulo
 * hace falta para verla. **Una sola lista para las tres pantallas.**
 *
 * ## Por qué vive aparte y no dentro de cada componente
 *
 * `/app/plan`, `/app/plan/visual` y `/app/plan/gestion` describen el mismo
 * conjunto de páginas desde tres ángulos: el hub las cuenta para decidir si
 * ofrece una entrada, Visual pinta las suyas y Gestión las suyas. Con tres
 * copias, agregar una página obliga a acordarse de tres sitios y la que se
 * olvide queda invisible o, peor, ofrecida y rota.
 *
 * ## El reparto
 *
 * No es «quién puede escribir» —eso lo decide el backend— sino **qué se mira
 * contra qué se opera**:
 *
 *   · `visual`  lo que se consulta: el árbol del Plan y los tres tableros.
 *               Es donde van aterrizando las cosas nuevas que se piden, así
 *               que la lista está pensada para crecer.
 *   · `gestion` lo operativo, conservando los agrupadores que ya existían.
 *
 * Cada página pertenece a UNA sola entrada. Que apareciera en las dos haría
 * que su breadcrumb dependiera de por dónde se llegó, y ese es justo el tipo
 * de detalle que nadie mantiene.
 *
 * ## El gating
 *
 * `modulo` es el que exige el ENDPOINT de esa página, no una invención de la
 * interfaz: si no se tiene, la pantalla responde 403 y ofrecerla es mandar a
 * alguien a chocarse. El hub no filtraba nada hasta hoy —pintaba las once
 * tarjetas a todo el mundo— y con dos entradas eso deja de ser un detalle.
 *
 * `alcanceGlobal` es aparte y más estricto: «Cargar Matriz PDL» exige, además
 * del módulo, que el backend considere que el usuario ve toda la localidad
 * (`matriz_views._AlcanceGlobal`). Hoy eso equivale a ser superusuario. Un
 * usuario con el módulo pero sin alcance ve la pantalla y recibe 403 al
 * aplicar, que es la peor forma de enterarse.
 */

export type Entrada = 'visual' | 'gestion';

export interface PaginaPlan {
  titulo: string;
  subtitulo: string;
  /** Icono Font Awesome; el hub lo traduce a Lucide con `lucideDe()`. */
  icono: string;
  color: 'primary' | 'accent' | 'info' | 'warning';
  ruta: string;
  entrada: Entrada;
  /** El agrupador dentro de su entrada. */
  seccion: string;
  /** Módulo que exige el endpoint de la página. */
  modulo: string;
  /** `true` si además hace falta alcance global (hoy: ser superusuario). */
  alcanceGlobal?: boolean;
}

export const PAGINAS: PaginaPlan[] = [
  // ── VISUAL — lo que se mira ────────────────────────────────────────
  {
    titulo: 'Tablero', subtitulo: 'La cadena Apropiación → Comprometido → Girado, por año',
    icono: 'fa-chart-pie', color: 'primary', ruta: '/plan/dashboard',
    entrada: 'visual', seccion: 'Los tableros', modulo: 'presupuesto_proyectos',
  },
  {
    titulo: 'Avance por sector', subtitulo: 'Qué dice la Matriz de cada sector, y cuánto ha cargado el área',
    icono: 'fa-layer-group', color: 'primary', ruta: '/plan/sectores',
    entrada: 'visual', seccion: 'Los tableros', modulo: 'presupuesto_proyectos',
  },
  {
    titulo: 'En qué se gasta', subtitulo: 'Por tipo de compromiso, modalidad de selección o rubro',
    icono: 'fa-tags', color: 'warning', ruta: '/plan/conceptos',
    entrada: 'visual', seccion: 'Los tableros', modulo: 'presupuesto_proyectos',
  },

  // ── GESTIÓN — lo que se opera ──────────────────────────────────────
  {
    titulo: 'Objetivos del Plan', subtitulo: 'Los cinco ejes, con sus programas y proyectos',
    icono: 'fa-bullseye', color: 'primary', ruta: '/plan/objetivos',
    entrada: 'gestion', seccion: 'El Plan', modulo: 'presupuesto_proyectos',
  },
  {
    titulo: 'Programas', subtitulo: 'Programas del Plan, bajo su objetivo',
    icono: 'fa-diagram-project', color: 'info', ruta: '/plan/programas',
    entrada: 'gestion', seccion: 'El Plan', modulo: 'presupuesto_metas',
  },
  {
    titulo: 'Proyectos', subtitulo: 'Los proyectos de inversión de la localidad',
    icono: 'fa-folder-tree', color: 'primary', ruta: '/plan/proyectos',
    entrada: 'gestion', seccion: 'El Plan', modulo: 'presupuesto_metas',
  },
  {
    titulo: 'Metas', subtitulo: 'El Plan meta a meta: su proyecto, su magnitud, su avance y su plata',
    icono: 'fa-flag-checkered', color: 'accent', ruta: '/plan/metas',
    entrada: 'gestion', seccion: 'El Plan', modulo: 'presupuesto_metas',
  },
  {
    titulo: 'Contratos', subtitulo: 'Contratos adjudicados de Kennedy (SECOP II)',
    icono: 'fa-file-signature', color: 'info', ruta: '/plan/contratos',
    entrada: 'gestion', seccion: 'La plata', modulo: 'presupuesto_proyectos',
  },
  {
    titulo: 'CDPs', subtitulo: 'Certificados de disponibilidad presupuestal',
    icono: 'fa-file-invoice-dollar', color: 'info', ruta: '/plan/cdps',
    entrada: 'gestion', seccion: 'La plata', modulo: 'presupuesto_proyectos',
  },
  {
    titulo: 'Actividades SIPSE', subtitulo: 'Por área: sus metas, sus eventos y su plata',
    icono: 'fa-list-check', color: 'info', ruta: '/plan/actividades',
    entrada: 'gestion', seccion: 'La ejecución', modulo: 'presupuesto_proyectos',
  },
  {
    titulo: 'Avances', subtitulo: 'Registro de avances de las metas',
    icono: 'fa-chart-line', color: 'accent', ruta: '/plan/avances',
    entrada: 'gestion', seccion: 'La ejecución', modulo: 'presupuesto_proyectos',
  },
  {
    titulo: 'Fuentes', subtitulo: 'La Matriz frente a BogData, proyecto por proyecto',
    icono: 'fa-scale-balanced', color: 'primary', ruta: '/plan/fuentes',
    entrada: 'gestion', seccion: 'Las fuentes', modulo: 'presupuesto_proyectos',
  },
  {
    titulo: 'Contratos por fuente', subtitulo: 'Cada contrato como lo ven SECOP, BogData e innovaK',
    icono: 'fa-scale-balanced', color: 'info', ruta: '/plan/contratos-fuentes',
    entrada: 'gestion', seccion: 'Las fuentes', modulo: 'presupuesto_proyectos',
  },
  {
    titulo: 'Cargar Matriz PDL', subtitulo: 'Subir el corte nuevo, revisarlo y aplicarlo',
    icono: 'fa-file-arrow-up', color: 'accent', ruta: '/plan/matriz',
    entrada: 'gestion', seccion: 'Las fuentes', modulo: 'presupuesto_proyectos',
    // Ver el docstring: el backend exige alcance global para APLICAR.
    alcanceGlobal: true,
  },
  {
    titulo: 'Comparación con Planeación', subtitulo: 'La Matriz frente al espejo del Distrito',
    icono: 'fa-scale-balanced', color: 'primary', ruta: '/plan/comparacion-sdp',
    entrada: 'gestion', seccion: 'Las fuentes', modulo: 'presupuesto_proyectos',
  },
];

/** El orden en que se pintan los agrupadores dentro de cada entrada. */
export const ORDEN_SECCIONES: Record<string, string[]> = {
  visual: ['Los tableros'],
  gestion: ['El Plan', 'La plata', 'La ejecución', 'Las fuentes'],
};

/** Una frase por agrupador. Va bajo el título de la sección. */
export const SUBTITULO_SECCION: Record<string, string> = {
  'Los tableros': 'Las cifras del Plan, ya agregadas.',
  'El Plan': 'Los ejes, sus programas, sus proyectos y sus metas.',
  'La plata': 'Cuánto se apropió, cuánto se comprometió y cuánto se giró.',
  'La ejecución': 'Qué se ha hecho, y cómo suma a las metas del Plan.',
  'Las fuentes': 'De dónde sale cada cifra, y contra qué se contrasta.',
};

/**
 * Las páginas de una entrada que este usuario SÍ puede abrir.
 *
 * `tieneModulo` y `alcanceGlobal` se pasan desde el componente para que este
 * archivo no dependa de `AuthService` — así se puede probar sin levantar
 * Angular entero.
 */
export function paginasDe(
  entrada: Entrada,
  tieneModulo: (codigo: string) => boolean,
  alcanceGlobal: boolean,
): PaginaPlan[] {
  return PAGINAS.filter(p =>
    p.entrada === entrada
    && tieneModulo(p.modulo)
    && (!p.alcanceGlobal || alcanceGlobal));
}

/** Agrupa por sección, en el orden declarado y sin secciones vacías. */
export function seccionesDe(
  entrada: Entrada,
  tieneModulo: (codigo: string) => boolean,
  alcanceGlobal: boolean,
): { titulo: string; subtitulo: string; paginas: PaginaPlan[] }[] {
  const visibles = paginasDe(entrada, tieneModulo, alcanceGlobal);
  return (ORDEN_SECCIONES[entrada] ?? [])
    .map(titulo => ({
      titulo,
      subtitulo: SUBTITULO_SECCION[titulo] ?? '',
      paginas: visibles.filter(p => p.seccion === titulo),
    }))
    .filter(s => s.paginas.length > 0);
}
