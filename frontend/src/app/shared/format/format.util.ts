/**
 * Helpers de formato compartidos para todo el SPA.
 *
 * GEN-UX-05: las magnitudes/avances llegan del backend como NUMERIC y se
 * pintaban crudas ("150.0000"). `formatNumero` las muestra con separadores
 * es-CO y sin decimales cuando son enteras.
 *
 * GEN-UX-08: el dashboard mostraba el `tipo_evento_codigo` crudo
 * ("ESTIMULO_CULTURAL"). `tipoEventoNombre` lo traduce al nombre de display
 * del catálogo canónico de tipo_evento.
 */

const LOCALE = 'es-CO';

/**
 * Número legible es-CO. Enteros sin decimales; con decimales conserva hasta
 * `maxDecimals` significativos (por defecto 2) y elimina ceros sobrantes.
 */
export function formatNumero(
  value: unknown,
  maxDecimals = 2,
): string {
  if (value === null || value === undefined || value === '') return '—';
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  return n.toLocaleString(LOCALE, {
    minimumFractionDigits: 0,
    maximumFractionDigits: maxDecimals,
  });
}

/** Moneda COP sin decimales (estilo institucional). */
export function formatMoneda(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  return '$' + n.toLocaleString(LOCALE, { maximumFractionDigits: 0 });
}

/**
 * Catálogo canónico de tipo_evento (código → nombre de display).
 * Fuente: catálogo `tipo_evento` de innovaK (memoria
 * reference_catalogo_tipos_evento). Si llega un código desconocido se devuelve
 * el propio código capitalizado de forma legible.
 */
export const TIPO_EVENTO_NOMBRES: Record<string, string> = {
  BANCO_INICIATIVAS: 'Banco de Iniciativas',
  CARACTERIZACION: 'Caracterización',
  CAPACITACION: 'Clase / Capacitación',
  CURSO: 'Curso',
  ENTREGA: 'Entrega de insumos',
  JOVENES_BECA: 'Entrega de becas',
  INFO_TERRENO: 'Información en terreno',
  CULTURA_ORG: 'Beneficio a organización',
  ESTIMULO_CULTURAL: 'Estímulo cultural',
  PROYECTO_CULTURAL: 'Proyecto financiado',
  GENERICO: 'Genérico',
};

/** Traduce un código de tipo_evento a su nombre de display. */
export function tipoEventoNombre(codigo: unknown): string {
  if (codigo === null || codigo === undefined || codigo === '') return '—';
  const code = String(codigo);
  if (TIPO_EVENTO_NOMBRES[code]) return TIPO_EVENTO_NOMBRES[code];
  // Fallback legible: SNAKE_CASE → "Snake case".
  return code
    .toLowerCase()
    .replace(/_/g, ' ')
    .replace(/^\w/, (c) => c.toUpperCase());
}
