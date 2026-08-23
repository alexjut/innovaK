/**
 * Tipos del EXPEDIENTE DE UN PROYECTO — panel derecho del explorador
 * maestro/detalle de /app/presupuesto/dashboard.
 *
 * Reflejan el contrato de `GET /presupuesto/api/proyectos/<pk>/expediente/`.
 * Cuatro reglas que el tipado hace explícitas y que la UI NO puede violar:
 *
 *  1. Todo lo que puede faltar es `| null` y viaja con SU motivo. El motivo se
 *     pinta al lado del vacío: «sin dato» a secas obliga al funcionario a
 *     adivinar si nadie cargó o si no hay dónde cargarlo.
 *  2. `avance_pct === null` se pinta «sin dato» con el donut apagado, JAMÁS
 *     como 0 %: un 0 % dice «no avanzó» cuando lo cierto es «no se ha medido».
 *  3. `etapa` es `null` en los 25 contratos porque la tabla `contrato` tiene 18
 *     columnas y ninguna es la etapa (medido). El stepper nace en gris. NO se
 *     deduce del estado de SECOP.
 *  4. Las metas llevan `contratos_ids` (punteros), no los contratos anidados:
 *     un contrato que aporta a 3 metas se pintaría 3 veces y se sumaría 3
 *     veces. Los contratos van UNA vez en el array raíz.
 */

/** Estados del semáforo, iguales a los del muro. */
export type EstadoSemaforo = 'al_dia' | 'atrasado' | 'critico' | 'incompleto';

/** Cómo se atribuyó el contrato al proyecto (la unión de las dos vías). */
export type ViaAtribucion = 'contrato_proyecto' | 'contrato_actividad_plan' | string;

/**
 * Las 4 etapas del expediente contractual, en orden. Hoy NINGÚN contrato
 * tiene etapa: la clave existe para el día que entre el DDL, no para
 * adivinarla ahora.
 */
export type ClaveEtapa = 'formulacion' | 'ejecucion' | 'liquidacion' | 'sancionatorio';

export interface Referencia {
  id: number;
  nombre: string;
}

/** Un KPI de la meta. */
export interface IndicadorExpediente {
  id: number;
  nombre: string;
  /** Unidad declarada del indicador. NO se inventa cuando falta. */
  unidad: string | null;
  /** KPI PROGRAMADO (`meta_magnitud`). */
  programado: number | null;
  /** KPI EJECUTADO (suma de avances reportados). */
  ejecutado: number | null;
  pct: number | null;
  /** Por qué no hay ejecutado, cuando el backend lo explica. */
  sin_avance_motivo?: string | null;
  /**
   * Nº de filas de avance que sustentan el `ejecutado`. Es el único campo que
   * distingue «reportaron 0» de «nadie reportó»: sin él, un indicador sin
   * avances y otro con avances que suman cero se ven idénticos. Medido: solo
   * 6 de 23 indicadores tienen avance, así que 17 caerían en ese hueco.
   */
  n_aportes?: number | null;
}

export interface MetaExpediente {
  meta_proyecto_id: number;
  /** `meta_codigo` NO identifica la meta: la misma meta cuelga de 2 proyectos. */
  meta_codigo: string | number | null;
  nombre: string | null;
  descripcion: string | null;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  indicadores: IndicadorExpediente[];
  n_indicadores?: number;
  indicadores_con_avance?: number;
  /** Por qué la meta no tiene indicador. Medido: 2 de 24 metas están así. */
  sin_indicador_motivo?: string | null;
  avance_pct: number | null;
  /** Punteros al array raíz `contratos`, no los contratos. */
  contratos_ids: number[];
}

/** Fila del plan de pago. Hoy `crp` y `forma_pago` tienen 0 filas. */
export interface FilaPlanPago {
  periodo: string | null;
  programado: number | null;
  pagado: number | null;
}

export interface ContratoExpediente {
  id: number;
  numero: string | null;
  objeto: string | null;
  /** Valor del contrato = lo COMPROMETIDO. */
  valor: number | null;
  /** Girado del espejo SECOP. Sin conciliar, no hay girado que valga. */
  girado: number | null;
  conciliado_secop: boolean;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  /** Gauge técnico (`contrato.ejecucion`). Medido: 4 no nulos de 25. */
  ejecucion: number | null;
  categoria: string | null;
  cdp_id: number | null;
  via_atribucion: ViaAtribucion | null;
  /** Metas a las que aporta este contrato (el reverso de `contratos_ids`). */
  metas_ids?: number[];
  /** Cadena concreta por la que el contrato llegó a la meta. */
  via_meta?: string | null;
  vigencia?: number | null;
  /** Hoy null en los 25. Se pinta el stepper apagado con su leyenda. */
  etapa: ClaveEtapa | null;
  etapa_motivo?: string | null;
  plan_pago: FilaPlanPago[];
  plan_pago_motivo?: string | null;

  // ── Opcionales: si el backend los llega a mandar se pintan; si no, la UI
  //    declara el vacío con su causa. NO se calculan a la brava aquí.
  /**
   * Contratista. Medido hoy: `proveedor` tiene 0 filas y los 25 contratos
   * tienen `proveedor_id` NULL, así que hoy nunca llega. El espejo SECOP sí
   * trae `proveedor`, que sería la vía el día que se enganche.
   */
  contratista?: string | null;
  contratista_motivo?: string | null;
  /** Estado del contrato en SECOP. Es informativo: NO es la etapa. */
  estado_secop?: string | null;
  /** Programado por contrato, si algún día existe. */
  programado?: number | null;
  programado_motivo?: string | null;
  /** Saldo por girar del contrato, si el backend lo precalcula. */
  saldo?: number | null;
}

/** Contratos del proyecto que no cuelgan de ninguna meta, con su motivo. */
export interface ContratosSinMeta {
  ids: number[];
  motivo?: string | null;
}

export interface ExpedienteProyecto {
  id: number;
  codigo: string | null;
  nombre: string | null;
  programa: Referencia | null;
  subgrupo: Referencia | null;
  area: string | null;
  dependencia: Referencia | null;
  localidad: string | null;
  localidad_motivo?: string | null;
  estado: string | null;
  estado_motivo?: string | null;

  n_metas: number;
  n_indicadores: number;
  n_contratos: number;
  n_actividades_plan: number;
  contratos_con_valor: number;
  contratos_conciliados: number;

  comprometido: number | null;
  girado: number | null;
  saldo_por_girar: number | null;

  avance_pct: number | null;
  avance_meta_magnitud: number | null;
  avance_magnitud: number | null;
  semaforo: EstadoSemaforo | null;
  semaforo_motivo: string | null;
  pct_girado: number | null;

  /**
   * PROGRAMADO del proyecto. Medido: llega $23.272.260.000 para el proyecto 1
   * con `programado_origen: 'sdp_meta_oficial'`. NO es un vacío: pintarlo
   * «sin dato» escondería una cifra oficial que sí existe.
   */
  programado_oficial: number | null;
  /** De dónde salió el programado. Se muestra: la cifra sin fuente no se audita. */
  programado_origen: string | null;

  /** Recuento de contratos por etapa. Medido hoy: los 15 en `sin_dato`. */
  etapas?: Record<string, number> | null;
  /** Sobre qué se calculó el semáforo (p. ej. `girado_sobre_comprometido`). */
  base_semaforo?: string | null;
  indicadores_con_avance?: number;

  metas: MetaExpediente[];
  contratos: ContratoExpediente[];
  /** Ids de los contratos que no cuelgan de ninguna meta. */
  contratos_sin_meta?: number[] | ContratosSinMeta | null;
  /** Motivo, que el backend manda como clave hermana de la lista. */
  contratos_sin_meta_motivo?: string | null;
}
