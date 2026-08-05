/** Tipos del módulo Educación (colegios distritales + insumos entregados). */

export interface ColegioSede {
  id: number;
  dane_sede: string;
  dane_establecimiento: string;
  colegio: string;
  sede: string;
  orden_sede: string | null;
  es_principal: boolean;
  clase: number | null;
  clase_nombre: string;
  direccion: string | null;
  barrio: string | null;
  telefono: string | null;
  email?: string | null;
  upz_codigo: number | null;
  estrato_ideca: number | null;
  matricula_total: number | null;
  /** Corte propio: la matrícula viene de otra capa que la ficha de la sede. */
  matricula_corte: string | null;
  fecha_corte: string | null;
  latitud?: number | null;
  longitud?: number | null;
  /** Solo con sesión (lo agrega el endpoint del mapa). */
  entregas_n?: number;
  entregas_valor?: number;
}

export interface Entrega {
  id: number;
  colegio_sede_id: number;
  colegio: string | null;
  sede: string | null;
  contrato_id: number | null;
  contrato: string | null;
  vigencia: number;
  implemento_codigo: number | null;
  insumo: string;
  descripcion: string | null;
  cantidad: number;
  unidad: string | null;
  valor_unitario: number | null;
  valor_total: number | null;
  beneficiarios: number | null;
  fecha_entrega: string | null;
  acta_numero: string | null;
  observacion: string | null;
}

export interface EntregaInput {
  colegio_sede_id: number;
  vigencia: number;
  implemento_codigo?: number | null;
  descripcion?: string | null;
  cantidad?: number;
  unidad?: string | null;
  valor_unitario?: number | null;
  valor_total?: number | null;
  beneficiarios?: number | null;
  fecha_entrega?: string | null;
  acta_numero?: string | null;
  contrato_id?: number | null;
  observacion?: string | null;
}

export interface ColegioDetalle {
  sede: ColegioSede;
  /** Las otras sedes del mismo colegio: evita registrar en la equivocada. */
  sedes_hermanas: ColegioSede[];
  entregas: Entrega[];
  totales: { entregas: number; valor: number; beneficiarios: number };
}

export interface ColegiosResponse {
  type: 'FeatureCollection';
  features: { properties: ColegioSede }[];
  count: number;
  sin_ubicacion: ColegioSede[];
  count_sin_ubicacion: number;
  colegios: number;
  matricula_total: number;
  /** false = la tabla todavía no está aplicada en este entorno. */
  disponible: boolean;
}

export interface Insumo {
  codigo: number;
  nombre: string;
  categoria: string;
}

export interface ResumenVigencia {
  vigencia: number;
  por_insumo: {
    insumo: string; cantidad: number; valor: number; sedes: number;
  }[];
  por_colegio: {
    dane_establecimiento: string; colegio: string; entregas: number;
    valor: number; beneficiarios: number; matricula: number; sedes: number;
  }[];
  totales: { entregas: number; valor: number; sedes: number };
}
