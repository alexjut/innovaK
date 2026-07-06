import { Chip, RespuestaBot } from './kenny-chat.types';

/**
 * Flujos del asistente KENNY definidos como DATA. KENNY tiene dos ejes,
 * ambos basados en lo que innovaK realmente tiene:
 *   - INTERNO: usar la plataforma (navegar a módulos + recorridos guiados).
 *   - EXTERNO: los proyectos de inversión que la localidad ejecuta.
 * Más la Consulta IA (lenguaje natural sobre la población atendida).
 */

export const SALUDO_INICIAL =
  '¡Hola! Soy KENNY 🐦, tu asistente de la Alcaldía Local de Kennedy. Te ayudo a usar la plataforma o a conocer nuestros proyectos. ¿Con qué empezamos?';

export const MENU_CHIPS: Chip[] = [
  { label: 'Usar la plataforma', action: 'interno', primary: true },
  { label: 'Nuestros proyectos', action: 'externo' },
  { label: 'Consultar datos con IA', action: 'ia' },
];

const VOLVER: Chip = { label: 'Volver al menú', action: 'menu' };

export const ACCIONES: Record<string, RespuestaBot> = {
  // ── Menú ────────────────────────────────────────────────────
  menu: {
    texto: '¿Qué necesitas?',
    expr: 'alegre',
    widgets: { chips: MENU_CHIPS },
  },

  // ── INTERNO: usar la plataforma ─────────────────────────────
  interno: {
    texto: '¿A qué parte te llevo? Te dejo en la sección y, si es tu primera vez, te hago un recorrido guiado.',
    expr: 'atento',
    widgets: {
      chips: [
        { label: 'Presupuesto', action: 'nav:presupuesto' },
        { label: 'Actividades', action: 'nav:actividades' },
        { label: 'Mapa de Kennedy', action: 'nav:mapa' },
        { label: 'Festivales', action: 'nav:festivales' },
        { label: 'Votaciones', action: 'nav:votaciones' },
        { label: 'Administración', action: 'nav:admin' },
        { label: 'Recorrido del inicio', action: 'nav:inicio' },
        VOLVER,
      ],
    },
  },

  // ── EXTERNO: nuestros proyectos ─────────────────────────────
  externo: {
    texto:
      'Kennedy ejecuta proyectos de inversión local en Cultura, Deporte, Educación y Participación ciudadana: cursos, festivales, becas (Jóvenes a la E), el Banco de Iniciativas Recreodeportivas y más. ¿Qué quieres ver?',
    expr: 'alegre',
    widgets: {
      chips: [
        { label: 'Proyectos y presupuesto', action: 'nav:presupuesto' },
        { label: '¿Cómo vamos? (avances)', action: 'nav:cockpit' },
        { label: 'Actividades en territorio', action: 'nav:actividades' },
        { label: 'Preguntar a la IA', action: 'ia' },
        VOLVER,
      ],
    },
  },

  // ── IA: consulta en lenguaje natural ────────────────────────
  ia: {
    texto:
      'Pregúntame en lenguaje natural sobre la población atendida. Por ejemplo: «beneficiarios por localidad», «¿cuántos por sexo?» o «personas por grupo etario». Escribe tu pregunta 👇',
    expr: 'atento',
    inputMode: 'ia',
    inputPlaceholder: 'Ej.: beneficiarios por UPZ…',
    widgets: { chips: [{ label: 'Abrir Consulta IA', action: 'nav:ia' }, VOLVER] },
  },

  // ── Navegaciones (rutas REALES de innovaK) ──────────────────
  'nav:presupuesto': {
    texto: 'Te llevo a Presupuesto: proyectos, metas, KPIs y contratos. 👇',
    expr: 'orgulloso', navegar: '/presupuesto', lanzarTour: 'presupuesto',
    widgets: { chips: [VOLVER] },
  },
  'nav:actividades': {
    texto: 'Te llevo a Actividades: cursos, eventos, caracterizaciones y entregas. 👇',
    expr: 'orgulloso', navegar: '/actividades', lanzarTour: 'actividades',
    widgets: { chips: [VOLVER] },
  },
  'nav:mapa': {
    texto: 'Te llevo al Mapa de Kennedy: los hechos georreferenciados en el territorio. 👇',
    expr: 'orgulloso', navegar: '/mapa',
    widgets: { chips: [VOLVER] },
  },
  'nav:festivales': {
    texto: 'Te llevo a Festivales: registro, galería, aforo y jurados de Cultura. 👇',
    expr: 'orgulloso', navegar: '/festivales',
    widgets: { chips: [VOLVER] },
  },
  'nav:votaciones': {
    texto: 'Te llevo a Votaciones: eventos, candidatos y resultados. 👇',
    expr: 'orgulloso', navegar: '/votaciones',
    widgets: { chips: [VOLVER] },
  },
  'nav:admin': {
    texto: 'Te llevo a Administración: roles, organizaciones y personas. 👇',
    expr: 'orgulloso', navegar: '/admin',
    widgets: { chips: [VOLVER] },
  },
  'nav:cockpit': {
    texto: 'Te llevo al panel de avances: ejecución presupuestal y cadena por proyecto. 👇',
    expr: 'orgulloso', navegar: '/presupuesto/dashboard',
    widgets: { chips: [VOLVER] },
  },
  'nav:ia': {
    texto: 'Te llevo a la Consulta con IA completa, con gráficas. 👇',
    expr: 'orgulloso', navegar: '/ia',
    widgets: { chips: [VOLVER] },
  },
  'nav:inicio': {
    texto: 'Vamos al inicio y te muestro cómo se organiza todo. 👇',
    expr: 'orgulloso', navegar: '/', lanzarTour: 'hub-principal',
    widgets: { chips: [VOLVER] },
  },
};

/** Palabras clave → acción, para texto libre (modo 'free', antes de IA). */
export const KEYWORDS: { test: RegExp; action: string }[] = [
  { test: /presupuesto|proyecto|contrato|cdp|kpi|meta/i, action: 'nav:presupuesto' },
  { test: /actividad|curso|evento|caracteriz|entrega|banco|beca/i, action: 'nav:actividades' },
  { test: /mapa|territorio|georref|ubicaci/i, action: 'nav:mapa' },
  { test: /festival|cultura/i, action: 'nav:festivales' },
  { test: /votac|elecci/i, action: 'nav:votaciones' },
  { test: /avance|ejecuci|c[oó]mo vamos/i, action: 'nav:cockpit' },
  { test: /usar|plataforma|c[oó]mo (uso|funciona)|tutorial|recorrido|ayuda/i, action: 'interno' },
  { test: /proyecto.*(tenemos|hacemos)|invers[ií]on/i, action: 'externo' },
];
