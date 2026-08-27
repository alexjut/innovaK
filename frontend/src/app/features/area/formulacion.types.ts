/** Tipos del dominio FORMULACIÓN (espejo de apps/presupuesto/api/formulacion_views.py). */

export type ClaveSemaforo =
  | 'lista' | 'en_proceso' | 'observada' | 'bloqueada' | 'sin_iniciar';

export interface Semaforo {
  clave: ClaveSemaforo;
  icono: string;
  etiqueta: string;
  /** Por qué está en ese color. NUNCA se pinta un estado sin motivo. */
  motivo: string;
}

export interface EstadoFormulacion {
  codigo: number;
  nombre: string;
  orden: number;
  descripcion?: string | null;
  es_final?: boolean;
  bloquea_contratacion: boolean;
}

/** Un requisito del checklist, con su estado en ESTA formulación. */
export interface Requisito {
  codigo: string;
  nombre: string;
  bloque: string;
  orden: number;
  /** ok · pendiente · sin_dato · no_aplica */
  estado: string;
  obligatorio: boolean;
  /** Si falta, la formulación NO puede pasar a contratación. */
  bloquea: boolean;
  exige_evidencia: boolean;
  tiene_evidencia: boolean;
  observacion: string | null;
}

export interface CompletitudDetalle {
  ok: number;
  aplicables: number;
  no_aplica: number;
  /** Cuántos requisitos ha MIRADO alguien. 0 ⇒ no se califica. */
  revisados: number;
  de: number;
}

export interface Formulacion {
  id: number;
  codigo: string;
  actividad_plan_id: number;
  actividad: string;
  vigencia: number;
  objeto: string;
  /** `null` = sin dato. NUNCA 0 por defecto. */
  valor_estimado: number | null;
  estado: EstadoFormulacion;
  estado_fecha: string | null;
  /** `null` cuando no hay requisitos aplicables que medir. */
  completitud: number | null;
  completitud_detalle: CompletitudDetalle;
  bloqueada: boolean;
  faltan_criticos: string[];
  semaforo: Semaforo;
  cancelada: boolean;
  /** Quién RESPONDE por ella. `id: null` con su motivo, nunca un vacío mudo. */
  responsable: { id: number | null; nombre: string | null; motivo: string | null };
  /** Sólo en el detalle. */
  requisitos?: Requisito[];
  destinos?: Array<{ codigo: number; nombre: string }>;
  puede_formular?: boolean;
}

/** Una actividad del plan del área, y en qué vigencias ya está formulada. */
export interface ActividadDisponible {
  id: number;
  descripcion: string;
  formulada_en: number[];
}

export interface FuncionarioRef { id: number; nombre: string; }

/** Un soporte del expediente. El archivo vive cifrado en Mongo. */
export interface DocumentoFormulacion {
  id: number;
  nombre: string;
  /** Código del requisito al que respalda, o null si es un soporte suelto. */
  tipo: string | null;
  mime: string | null;
  tamano_bytes: number | null;
  subido_en: string | null;
  /** Hoy siempre false: OneDrive está cableado y apagado por credenciales. */
  en_onedrive: boolean;
}

export interface ResumenFormulacion {
  n: number;
  listas: number;
  bloqueadas: number;
  en_proceso: number;
  observadas: number;
  sin_iniciar: number;
  canceladas: number;
  /** `null` cuando ninguna tiene valor. Un 0 diría «vale cero pesos». */
  valor_formulado: number | null;
  valor_cobertura: { con: number; de: number };
  valor_motivo: string | null;
  /** La otra mitad del par: de lo formulado, cuánto ya es contrato. */
  contratado: ResumenContratado;
}

export interface ResumenContratado {
  /** Cuántas formulaciones tienen al menos un contrato. Un 0 acá SÍ es un
   *  número: viene con denominador, así que «0 de 6» es una medición. */
  enlazadas: number;
  de: number;
  /** Contratos DISTINTOS. Uno puede cubrir varias formulaciones. */
  contratos: number;
  /** `null` cuando no hay nada que sumar. Nunca 0. */
  valor: number | null;
  valor_cobertura: { con: number; de: number };
  motivo: string | null;
  /** Solo existe si hay formulaciones con valor estimado Y contrato: la resta
   *  entre conjuntos distintos daría un número sin significado. */
  comparable: {
    n: number;
    formulado: number;
    contratado: number | null;
    contratos_sin_valor: number;
    diferencia?: number;
  } | null;
}

/** Por qué el área no tiene formulaciones. Un 0 nunca viaja solo. */
export interface ContextoVacio {
  causa: 'sin_proyectos' | 'sin_lineas_de_plan' | 'todo_contratado' | 'sin_formular_todavia';
  detalle: string;
  lineas_de_plan: number;
  lineas_con_contrato: number;
  proyectos: number;
}

export interface ListaFormulaciones {
  area: { id: number; nombre: string };
  formulaciones: Formulacion[];
  resumen: ResumenFormulacion;
  contexto: ContextoVacio | null;
  estados_catalogo: EstadoFormulacion[];
  /** Lo que hace falta para abrir una formulación desde la pantalla. */
  actividades: ActividadDisponible[];
  funcionarios: FuncionarioRef[];
  /** Por qué no hay a quién asignar, cuando la lista viene vacía. */
  funcionarios_motivo: string | null;
  vigencias: number[];
  puede_formular: boolean;
}

/** Una fila del espejo de SECOP, para elegir el contrato que se enlaza. */
export interface FilaSecop {
  id_contrato: string;
  referencia: string | null;
  anio: number | null;
  objeto: string;
  valor: number | null;
  proveedor: string | null;
  estado_secop: string | null;
  modalidad: string | null;
  url_proceso: string | null;
  /** Si la referencia no parsea, el número no se puede deducir. */
  parseable: boolean;
  /** Id del contrato interno si ya existe. */
  ya_en_innovak: number | null;
  ya_ligado_a_otra: boolean;
}

export interface ContratoLigado {
  contrato_id: number;
  numero: string;
  valor: number | null;
  objeto: string | null;
  etapa: string | null;
  ligado_en: string | null;
}

export interface BusquedaSecop {
  resultados: FilaSecop[];
  total: number;
  mostrados: number;
  criterio: string;
  motivo_vacio: string | null;
}
