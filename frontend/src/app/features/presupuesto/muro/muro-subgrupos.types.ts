/**
 * Tipos del MURO DE SUBGRUPOS (Fase 1 del panel de área).
 *
 * Reflejan al pie de la letra el contrato acordado con backend. Tres reglas
 * que el tipado hace explícitas y que la UI NO puede violar:
 *
 *  1. `avance` es `number | null`. El null significa «ningún indicador tiene
 *     avance cargado», y se pinta como «sin avance cargado», JAMÁS como 0%.
 *  2. `sin_subgrupo.saldo` es `null` fijo: el girado sale de un contrato cuyo
 *     valor en innovaK es NULL, así que restar daría un saldo falso.
 *  3. Los campos que hoy no tienen dónde guardarse (etapa, forma de pago)
 *     nacen declarados en 0 —no omitidos— para que el día que llegue el DDL
 *     el frontend no cambie.
 */

/** Estados del semáforo. NO existe «meta vencida»: el PDL corre 2025→2028. */
export type EstadoSemaforo = 'al_dia' | 'atrasado' | 'critico' | 'incompleto';

/** Bloque visual al que pertenece la tarjeta. */
export type GrupoTarjeta = 'con_inversion' | 'con_proyecto_sin_contrato' | 'sin_nada';

/** `inversion` = dependencia INVERSIÓN LOCAL; `apoyo` = el resto. */
export type NaturalezaSubgrupo = 'inversion' | 'apoyo';

/** Una etapa del catálogo, tal como la manda el servidor. */
export interface EtapaCatalogo {
  codigo: number;
  nombre: string;
  orden: number;
  descripcion: string | null;
}

/**
 * Chip de completitud de la cabecera. `causa` distingue dos vacíos que NO
 * son el mismo problema:
 *   - `columna_inexistente` → no hay dónde guardarlo (requiere DDL)
 *   - `tabla_vacia`         → sí hay dónde, falta cargar
 *   - `dato_faltante`       → hay dónde y hay filas, faltan valores
 */
export interface ChipCompletitud {
  clave?: string;
  etiqueta?: string;
  con: number;
  de: number;
  pct: number;
  causa?: string;
  detalle?: string;
  accion?: string;
}

/** Ventana del PDL. `pct_tiempo_transcurrido` es el umbral del semáforo. */
export interface VentanaPdl {
  pct_tiempo_transcurrido: number;
  inicio?: string;
  fin?: string;
  dias_transcurridos?: number;
  dias_totales?: number;
}

export interface CabeceraMuro {
  /** max(secop_contrato.synced_at) */
  corte: string | null;
  /** max(sdp_meta_oficial.synced_at) — es OTRO corte, más viejo. */
  corte_pdl_oficial: string | null;
  ventana_pdl: VentanaPdl;
  /** El backend puede mandarlo como diccionario o como lista; se normaliza. */
  chips: Record<string, ChipCompletitud> | ChipCompletitud[];
  /** El catálogo vivo de etapas. La pantalla NO congela nombres ni códigos. */
  etapas_catalogo?: EtapaCatalogo[];
}

/** Cifra del ledger. Puede llegar como número plano o como objeto anotado. */
export interface CifraLedger {
  valor: number | null;
  unidad_origen?: string;
  factor_aplicado?: number | null;
  cobertura?: { con?: number; de?: number; pct?: number } | null;
  descartado?: unknown;
  nota?: string;
}

export interface LedgerMuro {
  programado: CifraLedger | number | null;
  comprometido: CifraLedger | number | null;
  girado: CifraLedger | number | null;
  /** comprometido − girado. NO es programado − comprometido (dos universos). */
  saldo: CifraLedger | number | null;
}

/** Conteo por etapa. Las 4 primeras claves nacen en 0, no omitidas. */
/**
 * Conteo de contratos por etapa. Las claves son los CÓDIGOS del catálogo
 * (llegan como texto en JSON) más `sin_dato`.
 *
 * Antes eran cinco claves congeladas en el frontend —`planeacion`,
 * `contratacion`…— que el catálogo real nunca tuvo, y una de ellas se pintaba
 * «Formulación». Los nombres los pone ahora `cabecera.etapas_catalogo`.
 */
export interface EtapasTarjeta {
  /** Los que nadie ha registrado. NUNCA se reparte entre las otras etapas. */
  sin_dato?: number;
  /** El resto de claves es el CÓDIGO de la etapa, como texto. */
  [codigo: string]: number | undefined;
}

export interface AvanceDetalle {
  indicadores: number;
  con_avance: number;
  meta_magnitud: number | null;
  avance_magnitud: number | null;
}

/** Una fila de la lista de pendientes: el vacío con dueño. */
export interface PendienteTarjeta {
  que: string;
  cuantos?: number | null;
  detalle?: string | null;
}

export interface CoberturaTarjeta {
  contratos_conciliados: number;
  de: number;
  contratos_con_valor: number;
}

export interface TarjetaSubgrupo {
  id: number;
  nombre: string;
  dependencia?: string | null;
  /** Mapa PLANIG en backend (10 entradas). null en 35 de 45. */
  area?: string | null;
  naturaleza?: NaturalezaSubgrupo;
  grupo: GrupoTarjeta;

  n_proyectos: number;
  n_metas: number;
  n_contratos: number;

  comprometido: number | null;
  girado: number | null;
  saldo: number | null;

  programado_oficial?: number | null;
  /** Declara por qué vía se atribuyó: 'proyecto' o 'sector'. */
  programado_origen?: string | null;

  etapas?: EtapasTarjeta;

  /** null ⇒ sin avance cargado. NUNCA 0.0 por defecto. */
  avance: number | null;
  avance_detalle?: AvanceDetalle;

  semaforo: EstadoSemaforo;
  semaforo_motivo?: string | null;
  pct_girado?: number | null;
  base_semaforo?: string | null;

  pendientes?: PendienteTarjeta[];
  cobertura?: CoberturaTarjeta;
}

/** Los contratos que no cuelgan de ningún subgrupo. Para que la suma cuadre. */
export interface SinSubgrupo {
  n_contratos: number;
  comprometido: number | null;
  girado?: number | null;
  /** null FIJO por contrato: publicar la resta sería inventar un dato. */
  saldo: null;
  pendientes?: PendienteTarjeta[];
  detalle?: string | null;
}

export interface CoberturaPdlResumen {
  oficiales: number;
  cargados: number;
  faltan: number;
  innovak_sin_par_oficial: number;
}

export interface CoberturaPdlSector {
  sector: string;
  area_planig?: string | null;
  subgrupo_id?: number | null;
  mapeo?: string | null;
  oficiales: number;
  cargados: number;
  faltan: number;
  programado_oficial?: number | null;
  faltantes?: Array<{ codigo?: string; nombre?: string } | string> | null;
}

export interface CoberturaPdl {
  resumen: CoberturaPdlResumen;
  por_sector?: CoberturaPdlSector[];
}

/** Respuesta completa del endpoint del muro. */
export interface MuroSubgrupos {
  cabecera: CabeceraMuro;
  ledger: LedgerMuro;
  tarjetas: TarjetaSubgrupo[];
  sin_subgrupo: SinSubgrupo;
  cobertura_pdl?: CoberturaPdl;
}
