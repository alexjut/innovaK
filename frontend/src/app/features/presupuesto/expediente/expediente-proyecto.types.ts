/**
 * Tipos del EXPEDIENTE DE UN PROYECTO — panel derecho del explorador
 * maestro/detalle de /app/presupuesto/dashboard.
 *
 * Reflejan el contrato de `GET /presupuesto/api/proyectos/<pk>/expediente/`
 * y el de `GET|PATCH /presupuesto/api/contratos/<id>/etapa/`.
 *
 * Cinco reglas que el tipado hace explícitas y que la UI NO puede violar:
 *
 *  1. Todo lo que puede faltar es `| null` y viaja con SU motivo. El motivo se
 *     pinta al lado del vacío: «sin dato» a secas obliga al funcionario a
 *     adivinar si nadie cargó o si no hay dónde cargarlo.
 *  2. `avance_pct === null` se pinta «sin dato» con el donut apagado, JAMÁS
 *     como 0 %: un 0 % dice «no avanzó» cuando lo cierto es «no se ha medido».
 *     Lo mismo en dinero: `null` y `0` son estados distintos y se ven distinto.
 *  3. `etapa` es un OBJETO `{codigo, nombre, orden}` o `null`, y `null`
 *     significa «pendiente de registrar». Medido hoy: los 25 contratos en
 *     null — NADIE ha registrado etapa. No se deduce del estado de SECOP:
 *     «Modificado» (20 de 25) dice que hubo otrosí, no en qué etapa está.
 *  4. Las metas llevan `contratos_ids` (punteros), no los contratos anidados:
 *     un contrato que aporta a 3 metas se pintaría 3 veces y se sumaría 3
 *     veces. Los contratos van UNA vez en el array raíz.
 *  5. Los cuatro bloques de detalle —etapa, ejecución presupuestal, ejecución
 *     técnica y financiera, plan de pago— pertenecen al CONTRATO, no a la
 *     meta. Por eso viven en `ContratoExpediente` y se pintan igual dentro de
 *     una meta que en la lista de contratos sin meta.
 */

/** Estados del semáforo, iguales a los del muro. */
export type EstadoSemaforo = 'al_dia' | 'atrasado' | 'critico' | 'incompleto';

/** Cómo se atribuyó el contrato al proyecto (la unión de las dos vías). */
export type ViaAtribucion = 'contrato_proyecto' | 'contrato_actividad_plan' | string;

export interface Referencia {
  id: number;
  nombre: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// ETAPA CONTRACTUAL
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Una etapa del catálogo `etapa_contrato`. Son filas reales de la base, no una
 * constante del frontend: el `codigo` es la clave que viaja en el PATCH y el
 * `orden` decide qué tramo del stepper está recorrido.
 *
 * Cuántas son se lee de la tabla y no se escribe acá. Fueron cuatro hasta el
 * 2026-08-26, cuando entró «En elaboración» (orden 0) para el contrato que el
 * área todavía está estructurando y aún no está en SECOP.
 */
export interface EtapaCatalogo {
  codigo: number;
  nombre: string;
  orden: number;
  descripcion?: string | null;
}

/** La etapa registrada de un contrato. Nunca se infiere. */
export interface EtapaContrato {
  codigo: number;
  nombre: string;
  orden: number;
}

/** Respuesta de `GET|PATCH /presupuesto/api/contratos/<id>/etapa/`. */
export interface EstadoEtapaContrato {
  contrato_id: number;
  numero: string | number | null;
  vigencia: number | null;
  etapa: EtapaContrato | null;
  etapa_fecha: string | null;
  etapa_registrada_por: Referencia | null;
  etapa_motivo: string | null;
  etapas_catalogo: EtapaCatalogo[];
  /** Lo decide el backend cruzando módulo + scope por área. La UI obedece. */
  puede_registrar_etapa?: boolean;
  /** Por qué no puede, en texto de pantalla. `null` cuando sí puede. */
  puede_registrar_etapa_motivo?: string | null;
}

// ─────────────────────────────────────────────────────────────────────────────
// INDICADORES (los KPI que se mudaron desde el listado global del dashboard)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Cadena real que cuelga de un KPI. Estos tres campos son OPCIONALES a
 * propósito y hoy el backend NO los manda: se pintan si llegan y no se pintan
 * si no. Medido contra la base el 2026-08-23:
 *
 *   · KPI → actividad          `actividad_indicador` (activo): 20 de 23 KPI
 *   · KPI → actividad → evento `evento.actividad_plan_id`:      23 eventos
 *   · …→ evento → beneficiario `participante_evento`:            0 filas
 *
 * O sea: los dos primeros eslabones EXISTEN y el tercero se corta —los 2.545
 * participantes cuelgan de los otros 32 eventos, ninguno enganchado a una
 * actividad del plan—. Por eso el renglón de beneficiarios no se pinta: no
 * es un cero, es una cadena que no llega.
 */
export interface CadenaIndicador {
  /** Actividades del plan que miden este indicador. */
  actividades?: Referencia[] | null;
  /** Eventos registrados que cuelgan de esas actividades. */
  eventos?: Referencia[] | null;
  /** Beneficiarios atribuibles al indicador por esa cadena. */
  beneficiarios?: number | null;
  /** Por qué la cadena se corta, cuando el backend lo explica. */
  cadena_motivo?: string | null;
}

/** Un KPI de la meta. */
export interface IndicadorExpediente extends CadenaIndicador {
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
  /** Lo que el área prepara antes de que exista el contrato. Puede venir
   *  vacío: un entorno sin el DDL 019 no tiene el dominio. */
  formulaciones?: Array<{
    id: number;
    codigo: string;
    vigencia: number;
    objeto: string;
    /** `null` = sin dato. NUNCA se pinta como 0. */
    valor_estimado: number | null;
    estado: string;
    lista_para_contratacion: boolean;
    cancelada: boolean;
  }>;
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
  /** Por qué la meta se quedó sin contratos, en castellano de pantalla. */
  sin_contratos_motivo?: string | null;
  avance_pct: number | null;
  /** Punteros al array raíz `contratos`, no los contratos. */
  contratos_ids: number[];
}

// ─────────────────────────────────────────────────────────────────────────────
// CONTRATO
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Una fila del plan de pagos, tal como la publica SECOP II (recurso
 * `uymx-8p3j`). El `periodo` es el que trae el dato: NO se generan trimestres
 * ni meses que nadie reportó.
 */
export interface FilaPlanPago {
  /** Id del pago dentro del contrato, tal como lo numera SECOP. */
  id_pago?: string | number | null;
  /** «Pagado», «Aprobado», «Rechazado», «Enviado Por Proveedor»… */
  estado?: string | null;
  periodo: string | null;
  programado: number | null;
  pagado: number | null;
  fecha_estimada?: string | null;
  fecha_real?: string | null;
}

/**
 * Ejecución presupuestal DEL CONTRATO. Cada cifra viaja con su origen y su
 * motivo porque los huecos son de naturalezas distintas y se arreglan
 * distinto: «no tiene CDP» manda a crear el CDP, «el CDP no trae valor» manda
 * a completarlo. Medido: programado en 0 de 24 contratos atribuidos, y de
 * esos, 4 sí tienen CDP pero con `valor` NULL.
 */
export interface EjecucionPresupuestalContrato {
  programado: number | null;
  programado_origen?: string | null;
  programado_motivo?: string | null;
  comprometido: number | null;
  comprometido_motivo?: string | null;
  girado: number | null;
  girado_origen?: string | null;
  girado_motivo?: string | null;
  /** `comprometido − girado`, y SOLO si los dos son de este contrato. */
  saldo: number | null;
  saldo_formula?: string | null;
  saldo_motivo?: string | null;
  pct_girado?: number | null;
}

export interface ContratoExpediente {
  id: number;
  numero: string | number | null;
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
  /** El mismo dato en castellano, listo para pintar. */
  via_atribucion_texto?: string | null;
  /** Metas a las que aporta este contrato (el reverso de `contratos_ids`). */
  metas_ids?: number[];
  /** Cadena concreta por la que el contrato llegó a la meta (códigos). */
  via_meta?: string[] | string | null;
  /** La misma cadena, ya redactada. */
  via_meta_texto?: string[] | string | null;
  vigencia?: number | null;

  /** Etapa registrada. `null` = pendiente de registrar, NO «formulación». */
  etapa: EtapaContrato | null;
  etapa_fecha?: string | null;
  etapa_registrada_por?: Referencia | null;
  etapa_motivo?: string | null;

  /** Los cuatro números del contrato, cada uno con su fuente y su motivo. */
  ejecucion_presupuestal?: EjecucionPresupuestalContrato | null;

  plan_pago: FilaPlanPago[];
  plan_pago_motivo?: string | null;

  /**
   * Contratista. Llega desde el 2026-08-26: la precarga desde SECOP llenó
   * `contrato.proveedor_id` en 23 de 25 y el expediente ya lo lee.
   *
   * Estuvo vacío meses por dos motivos distintos que se arreglaron por
   * separado: primero `proveedor` no tenía filas, y después —ya con el dato
   * en la base— la consulta del expediente no lo traía. Precargar un dato no
   * es mostrarlo.
   */
  contratista?: string | null;
  /** NIT del contratista, cuando SECOP lo trae. */
  contratista_nit?: string | null;
  contratista_motivo?: string | null;
  /** Estado del contrato en SECOP. Es informativo: NO es la etapa. */
  estado_secop?: string | null;
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
   * PROGRAMADO del proyecto. Medido: llega $23.272.260.000 para el proyecto 1.
   * NO es un vacío: pintarlo «sin dato» escondería una cifra oficial que sí
   * existe.
   */
  programado_oficial: number | null;

  /**
   * Apropiación POAI acumulada del proyecto. Encabeza la cadena real de
   * ejecución (Apropiación → Comprometido → Girado); `programado_oficial` es
   * la meta aspiracional del cuatrienio, que es otra cosa.
   *
   * Las vigencias viajan con la cifra a propósito: el POAI se apropia año a
   * año y hoy solo cubre 2025-2026. Sin ellas, la suma se leería como
   * cuatrienio y parecería la mitad de lo que debería.
   */
  apropiacion_oficial: number | null;
  apropiacion_vigencia_desde: number | null;
  apropiacion_vigencia_hasta: number | null;
  apropiacion_origen: string | null;
  apropiacion_motivo: string | null;

  /**
   * Comprometido/girado de la Matriz PDL — NUNCA la misma cifra que
   * `comprometido`/`girado` de arriba, que salen de contratos reales
   * registrados en innovaK. Existen para el caso medido en la auditoría del
   * 2026-09-02: 18 de 31 proyectos con meta y apropiación pero sin un solo
   * contrato cargado — ahí `comprometido` sale `null` aunque la Alcaldía SÍ
   * reportó plata comprometida y girada en la matriz oficial. Un proyecto
   * puede tener las dos cifras, solo una, o ninguna.
   */
  comprometido_oficial: number | null;
  girado_oficial: number | null;
  ejecucion_oficial_origen: string | null;
  ejecucion_oficial_motivo: string | null;
  /** De dónde salió, ya redactado. La cifra sin fuente no se audita. */
  programado_origen: string | null;
  /** El mismo origen como código, para lógica. No se pinta. */
  programado_origen_codigo?: string | null;

  /** Recuento de contratos por código de etapa + `sin_dato`. */
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
