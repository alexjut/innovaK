/**
 * Tipos del módulo Caracterización. 6 sectores comparten estructura
 * básica + cada uno tiene campos específicos.
 */

export type CaractSector =
  | 'cultura'
  | 'seguridad'
  | 'deporte'
  | 'mujer'
  | 'salud'
  | 'poblacional'
  | 'participacion'
  | 'paz';

export const SECTORES: { codigo: CaractSector; label: string; icon: string; color: string }[] = [
  { codigo: 'cultura', label: 'Cultura', icon: 'fa-music', color: 'primary' },
  { codigo: 'seguridad', label: 'Seguridad y Convivencia', icon: 'fa-shield-halved', color: 'danger' },
  { codigo: 'deporte', label: 'Deporte', icon: 'fa-running', color: 'success' },
  { codigo: 'mujer', label: 'Mujer', icon: 'fa-venus', color: 'accent' },
  { codigo: 'salud', label: 'Salud', icon: 'fa-heartbeat', color: 'danger' },
  { codigo: 'poblacional', label: 'Poblacional', icon: 'fa-users', color: 'info' },
  { codigo: 'participacion', label: 'Participación Ciudadana', icon: 'fa-handshake', color: 'warning' },
  { codigo: 'paz', label: 'Paz, Memoria y Reconciliación', icon: 'fa-dove', color: 'info' },
];

/** Campos comunes de cualquier item de lista. */
export interface CaractListItem {
  id: number;
  evento_id: number | null;
  evento_nombre: string | null;
  persona_id: number | null;
  persona_nombre: string | null;
  funcionario_id: number | null;
  /** Algunos sectores: nivel_educativo_codigo, presenta_discapacidad, etc. */
  [extra: string]: unknown;
}

/** Detalle (mismos campos + específicos del sector). */
export interface CaractDetail extends CaractListItem {
  motivacion_personal?: string | null;
  hogar?: Record<string, unknown> | null;
  tiene_firma?: boolean;
  [extra: string]: unknown;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface CaractFilters {
  evento_id?: number;
  persona_id?: number;
  page?: number;
  page_size?: number;
}

export interface CaractInsights {
  por_sector: Record<string, number>;
  total: number;
  [extra: string]: unknown;
}
