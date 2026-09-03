import { EstadoSemaforo } from '../muro/muro-subgrupos.types';

/**
 * Las 5 categorías que trae la hoja «Alertas» de la Matriz PDL, ya
 * resueltas por la ALK — acá no se recalcula el umbral, solo se pinta.
 *
 * `'En ejecución de acuerdo a cronograma'` y no «según»: es el valor
 * LITERAL de la columna, verificado corriendo el importador contra el
 * Excel real — el dato manda, no el título del gráfico de la hoja.
 */
export type AlertaCumplimiento =
  | 'Crítico' | 'En ejecución de acuerdo a cronograma' | 'Ejecutada'
  | 'Desierta' | 'Sin magnitud contratada';

/**
 * En orden de severidad, de peor a mejor. Es la MISMA lista que
 * `ORDEN_SEVERIDAD_ALERTA` en `apps/presupuesto/services/expediente_proyecto.py`
 * — un proyecto/programa/perspectiva no se ve mejor de lo que es su meta
 * más comprometida. `valor` viaja tal cual al filtro (tiene que calzar
 * exacto con la columna); `etiqueta` es la que lee el usuario.
 */
export const ALERTAS: Array<{ valor: AlertaCumplimiento; etiqueta: string; clase: string }> = [
  { valor: 'Crítico', etiqueta: 'Crítico', clase: 'critico' },
  { valor: 'Desierta', etiqueta: 'Desierta', clase: 'desierta' },
  { valor: 'Sin magnitud contratada', etiqueta: 'Sin magnitud contratada', clase: 'sin-magnitud' },
  { valor: 'En ejecución de acuerdo a cronograma', etiqueta: 'En ejecución según cronograma', clase: 'cronograma' },
  { valor: 'Ejecutada', etiqueta: 'Ejecutada', clase: 'ejecutada' },
];

const RANGO_SEVERIDAD: Record<string, number> = Object.fromEntries(
  ALERTAS.map((a, i) => [a.valor, i]),
);

/**
 * «Peor alerta gana», calculado en el cliente sobre un grupo de proyectos
 * ya trae cada uno su propia alerta (peor entre SUS metas, calculada en
 * el backend). Válido para agrupar por programa o por perspectiva porque
 * cada proyecto que devuelve `/objetivos-estrategicos/` aporta metas a UN
 * solo programa dentro de ese árbol — «peor entre los proyectos del
 * programa» y «peor entre las metas del programa» dan el mismo resultado.
 * `null` si ningún proyecto del grupo tiene alerta cargada — no se inventa
 * una.
 */
export function peorAlerta(alertas: Array<AlertaCumplimiento | null | undefined>): AlertaCumplimiento | null {
  let peor: AlertaCumplimiento | null = null;
  let rango = Infinity;
  for (const a of alertas) {
    if (!a) continue;
    const r = RANGO_SEVERIDAD[a] ?? Infinity;
    if (r < rango) { rango = r; peor = a; }
  }
  return peor;
}

/**
 * Una fila de proyecto tal como la manda tanto
 * `/proyectos/expediente/` como cada nodo `programas[].proyectos[]` de
 * `/objetivos-estrategicos/` — es EL MISMO shape en las dos rutas porque el
 * backend arma el árbol reagrupando la misma lista, nunca recalculando.
 */
export interface ProyectoLista {
  id: number;
  codigo: string | null;
  nombre: string | null;
  subgrupo: string | null;
  subgrupo_id: number | null;
  area: string | null;
  dependencia: string | null;
  avance_pct: number | null;
  n_metas: number | null;
  n_contratos: number | null;
  semaforo: EstadoSemaforo | null;
  semaforo_motivo: string | null;
  alerta: AlertaCumplimiento | null;
  alerta_conteo: Record<string, number> | null;
  programado_oficial: number | null;
  apropiacion_oficial: number | null;
  apropiacion_vigencia_desde: number | null;
  apropiacion_vigencia_hasta: number | null;
  comprometido: number | null;
  girado: number | null;
  saldo_por_girar: number | null;
  comprometido_oficial: number | null;
  girado_oficial: number | null;
  ejecucion_oficial_origen: string | null;
}

export interface ObjetivoPrograma {
  nombre: string;
  proyectos: ProyectoLista[];
  resumen: { n_proyectos: number; n_criticos: number; n_con_alerta: number };
}

export interface ObjetivoEstrategico {
  nombre: string;
  programas: ObjetivoPrograma[];
  resumen: {
    n_proyectos: number; n_criticos: number; n_con_alerta: number;
    apropiacion_total: number | null; comprometido_total: number | null;
  };
}

/** Saldo por girar «real → si no, oficial», el mismo patrón que ya usa el
 *  expediente de detalle (`saldoOficial()`), aplicado acá a cualquier
 *  proyecto de la jerarquía. */
export function saldoPorGirar(p: ProyectoLista): number | null {
  if (p.saldo_por_girar != null) return p.saldo_por_girar;
  if (p.comprometido_oficial == null || p.girado_oficial == null) return null;
  return p.comprometido_oficial - p.girado_oficial;
}

/** Comprometido «real si hay contrato, si no oficial» — mismo criterio que
 *  ya vive en expediente-proyecto.component.html: `n_contratos` decide,
 *  porque `comprometido` real nunca es null (es un `sum()`, da 0 con cero
 *  contratos, no null). */
export function comprometidoDe(p: ProyectoLista): { valor: number | null; esOficial: boolean } {
  if ((p.n_contratos ?? 0) > 0) return { valor: p.comprometido, esOficial: false };
  if (p.comprometido_oficial != null) return { valor: p.comprometido_oficial, esOficial: true };
  return { valor: null, esOficial: false };
}

export function giradoDe(p: ProyectoLista): { valor: number | null; esOficial: boolean } {
  if (p.girado != null) return { valor: p.girado, esOficial: false };
  if (p.girado_oficial != null) return { valor: p.girado_oficial, esOficial: true };
  return { valor: null, esOficial: false };
}
