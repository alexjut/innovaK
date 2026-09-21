/**
 * La forma del árbol del Plan, tal como lo manda
 * `GET /dashboard/api/v2/presupuesto/plan-oficial/`.
 *
 * Los cuatro niveles son Objetivo → Programa → Proyecto → Meta, y cada nodo de
 * arriba trae un `resumen` agregado por el backend. El agregado NO se calcula
 * acá: si el componente sumara por su cuenta, el mismo objetivo podría decir
 * una cifra en el árbol y otra en el tablero, que es justo lo que este proyecto
 * ya vivió con el avance físico.
 */

/** Plata de un nodo. `null` es «sin dato», nunca «cero pesos». */
export interface PlataNodo {
  proyectado: number | null;
  apropiacion: number | null;
  comprometido: number | null;
  girado: number | null;
}

/** Avance de un nodo: PROMEDIO entre metas medidas, no suma ni razón. */
export interface AvanceNodo {
  pct: number | null;
  metas_medidas: number;
  /** Metas del nodo que la Matriz todavía no mide. Se dicen, no se cuentan como 0. */
  metas_sin_medir: number;
  regla: string;
}

export interface ResumenNodo {
  n_metas: number;
  plata: PlataNodo;
  avance: AvanceNodo;
  /** `{'Crítico': 41, 'Ejecutada': 23, …}` — el reparto, no un promedio. */
  alertas: Record<string, number>;
  fuente: string;
}

/** El contraste con Datos Abiertos del Distrito. `null` = la meta no está allá. */
export interface EspejoSdp {
  programado: number | null;
  entregado: number | null;
  tipo_anualizacion: string | null;
}

export interface MetaNodo {
  /** Consecutivo interno. Es la llave única; NO es lo que se le muestra a nadie. */
  codigo: number;
  /** El código SEGPLAN («26881»), que es el que la Alcaldía reconoce. */
  codigo_meta: string | null;
  nombre: string;
  proyecto_codigo: string | null;
  proyecto_nombre: string | null;
  programa_codigo: number | null;
  programa_nombre: string | null;
  objetivo_codigo: number | null;
  objetivo_nombre: string | null;
  sector: string | null;
  /** Magnitud que pide la meta, con su unidad. */
  kpi_magnitud: number | null;
  kpi_unidad: string | null;
  proyectado_pdl: number | null;
  apropiacion_poai: number | null;
  comprometido: number | null;
  girado: number | null;
  apropiacion_vigencia_desde: number | null;
  apropiacion_vigencia_hasta: number | null;
  alerta: string | null;
  /** Ya viene en PORCENTAJE. La Matriz lo guarda en tanto por uno y el backend
   *  lo convierte una sola vez — no volver a multiplicar por 100 acá. */
  cumplimiento_pct: number | null;
  magnitud_contratada: number | null;
  magnitud_ejecutada: number | null;
  espejo: EspejoSdp | null;
}

export interface ProyectoNodo {
  codigo: string;
  nombre: string;
  /** `false` = está en el Plan pero no cargado en innovaK. */
  en_innovak: boolean;
  n_metas: number;
  resumen: ResumenNodo;
  metas: MetaNodo[];
}

export interface ProgramaNodo {
  codigo: number;
  nombre: string;
  n_proyectos: number;
  n_metas: number;
  resumen: ResumenNodo;
  proyectos: ProyectoNodo[];
}

export interface ObjetivoNodo {
  codigo: number;
  nombre: string;
  n_programas: number;
  n_proyectos: number;
  n_metas: number;
  resumen: ResumenNodo;
  programas: ProgramaNodo[];
}

export interface PlanArbol {
  objetivos: ObjetivoNodo[];
  resumen: ResumenNodo;
  conteo: { objetivos: number; programas: number; proyectos: number; metas: number };
  /** Metas sin programa. Se publican aparte para que se vean, no en un cajón. */
  sin_clasificar: MetaNodo[];
  fuente: string;
  contraste: string;
}

/** Qué es cada nivel. Se muestra como ayuda para quien abre el Plan por primera vez. */
export const QUE_ES: Record<string, string> = {
  objetivo: 'Raíz estratégica: los propósitos frente a las problemáticas del territorio.',
  programa: 'Pilar sectorial que agrupa líneas de acción de un objetivo.',
  proyecto: 'Nivel operativo: el proyecto de inversión local, con su presupuesto.',
  meta: 'Indicador medible: se evalúa su magnitud, su avance y su plata.',
};

/**
 * De la alerta de la Matriz al color. Mismo reparto que usa
 * `perspectivas-explorador`, para que el Plan no se pinte de dos maneras.
 */
export const BALDE: Record<string, 'rojo' | 'amarillo' | 'verde'> = {
  'Crítico': 'rojo',
  'Desierta': 'rojo',
  'Sin magnitud contratada': 'rojo',
  'En ejecución de acuerdo a cronograma': 'amarillo',
  'Ejecutada': 'verde',
};
