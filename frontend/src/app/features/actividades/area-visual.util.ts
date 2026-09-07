/**
 * Ícono y color por nombre de área/subgrupo — misma línea visual que ya usa
 * el hub de Actividades (/actividades) en su sidebar de áreas y en el mapa.
 * El backend no entrega icono/color por subgrupo todavía, así que se mapea
 * aquí por nombre exacto (mismo patrón que ya traía actividades-hub antes de
 * esta extracción; ahora queda compartido para no duplicarlo entre pantallas).
 *
 * AREA_COLORES replica `sector_colors` de GET /api/actividades/tipos/ (el
 * mismo origen que pinta los puntos del mapa y el sidebar del hub). Si el
 * backend cambia esa paleta, hay que actualizar los valores aquí también.
 */
export const AREA_ICONOS: Record<string, string> = {
  'Relacionamiento Interinstitucional': 'landmark',
  'Desarrollo Estratégico y Mejora': 'trending-up',
  'Seguridad': 'shield',
  'Cultura': 'music',
  'Deporte': 'target',
  'Educación': 'graduation-cap',
  'Infraestructura': 'building-2',
  'CPS y Planta': 'users',
  'Subsidio tipo C': 'coins',
};

export const AREA_COLORES: Record<string, string> = {
  'Cultura': '#8B5CF6',
  'Deporte': '#10B981',
  'Mujer': '#EC4899',
  'Salud': '#14B8A6',
  'Participación': '#3B82F6',
  'Seguridad': '#DC2626',
  'Juventud': '#F59E0B',
  'Educación': '#0EA5E9',
};

export function areaIcono(nombre: string): string {
  return AREA_ICONOS[nombre] ?? 'layout-dashboard';
}

export function areaColor(nombre: string): string {
  return AREA_COLORES[nombre] ?? '#6B7280';
}
