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

/**
 * Fecha legible es-CO a partir de un ISO `YYYY-MM-DD` (o ISO completo).
 *
 * GEN-UX-14: las fechas llegan del backend en ISO y se pintaban crudas
 * ("2026-07-15"). Fuera de un contexto técnico eso se lee mal y en Colombia
 * además se confunde con el orden día/mes.
 *
 * Se parsea a mano en vez de `new Date(iso)`: con una fecha SIN hora, el
 * constructor la interpreta como UTC y, al pintarla en America/Bogota (UTC-5),
 * retrocede un día. Una actividad del 1 de agosto se mostraría como 31 de
 * julio, que es un error silencioso y muy difícil de ver.
 */
export function formatFecha(iso: unknown): string {
  if (iso === null || iso === undefined || iso === '') return '—';
  const m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return String(iso);
  const [, y, mes, d] = m;
  const fecha = new Date(Number(y), Number(mes) - 1, Number(d));
  if (isNaN(fecha.getTime())) return String(iso);
  return fecha.toLocaleDateString(LOCALE, {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

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
