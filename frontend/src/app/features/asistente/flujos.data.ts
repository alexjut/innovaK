import { Chip, RespuestaBot } from './kenny-chat.types';

/**
 * Flujos del asistente KENNY definidos como DATA (igual que tours.data.ts).
 * El motor (kenny-chat.service) solo interpreta: cada acción resuelve a una
 * RespuestaBot. Navegación e IA son reales; los flujos ciudadanos (trámites,
 * PQRS, citas) son guiados/demostrativos y quedan listos para conectar a sus
 * pantallas/endpoints reales cuando existan.
 */

export const SALUDO_INICIAL =
  '¡Hola! Soy KENNY 🐦, tu asistente de la Alcaldía Local de Kennedy. ¿Con qué te ayudo hoy?';

export const MENU_CHIPS: Chip[] = [
  { label: 'Trámites y servicios', action: 'tramites' },
  { label: 'Radicar PQRS', action: 'pqrs' },
  { label: 'Agendar cita', action: 'cita' },
  { label: 'Cómo llego / navegar', action: 'navegar' },
  { label: 'Noticias y eventos', action: 'noticias' },
];

const VOLVER: Chip = { label: 'Volver al menú', action: 'menu' };

export const ACCIONES: Record<string, RespuestaBot> = {
  // ── Menú ────────────────────────────────────────────────────
  menu: {
    texto: '¿Qué necesitas? Elige una opción:',
    expr: 'alegre',
    widgets: { chips: MENU_CHIPS },
  },

  // ── Flujo 1 — Trámites ──────────────────────────────────────
  tramites: {
    texto: 'Estos son los trámites más solicitados en Kennedy. Toca el que necesitas:',
    expr: 'atento',
    widgets: {
      cards: [
        { titulo: 'Certificado de residencia', descripcion: 'Constancia de vivienda en la localidad.', action: 'tramite:residencia' },
        { titulo: 'Impuesto predial', descripcion: 'Consulta y pago del predial unificado.', action: 'tramite:predial' },
        { titulo: 'Licencia de construcción', descripcion: 'Permiso para obra nueva o ampliación.', action: 'tramite:licencia' },
        { titulo: 'Registro de mascotas', descripcion: 'Inscribe a tu mascota en el censo local.', action: 'tramite:mascota' },
      ],
    },
  },
  'tramite:residencia': {
    texto: 'Certificado de residencia\nRequisitos: documento de identidad y un recibo de servicios reciente a tu nombre. Se expide en línea o en la sede de Atención al Ciudadano.',
    expr: 'orgulloso',
    widgets: { chips: [{ label: 'Ir al trámite', action: 'nav:tramites-online', primary: true }, VOLVER] },
  },
  'tramite:predial': {
    texto: 'Impuesto predial\nNecesitas el número de matrícula inmobiliaria o el CHIP del predio. El pago se hace por PSE.',
    expr: 'orgulloso',
    widgets: { chips: [{ label: 'Ir al trámite', action: 'nav:pagos', primary: true }, VOLVER] },
  },
  'tramite:licencia': {
    texto: 'Licencia de construcción\nSe tramita ante la Curaduría Urbana. Requisitos: escritura, planos y formulario único nacional.',
    expr: 'orgulloso',
    widgets: { chips: [{ label: 'Ir al trámite', action: 'nav:tramites-online', primary: true }, VOLVER] },
  },
  'tramite:mascota': {
    texto: 'Registro de mascotas\nAporta una foto y los datos de tu mascota. El registro es gratuito.',
    expr: 'orgulloso',
    widgets: { chips: [{ label: 'Ir al trámite', action: 'nav:tramites-online', primary: true }, VOLVER] },
  },

  // ── Flujo 2 — PQRS ──────────────────────────────────────────
  pqrs: {
    texto: '¿Qué tipo de solicitud deseas presentar?',
    expr: 'atento',
    widgets: {
      chips: [
        { label: 'Petición', action: 'pqrs:Petición' },
        { label: 'Queja', action: 'pqrs:Queja' },
        { label: 'Reclamo', action: 'pqrs:Reclamo' },
        { label: 'Sugerencia', action: 'pqrs:Sugerencia' },
      ],
    },
  },

  // ── Flujo 3 — Cita ──────────────────────────────────────────
  cita: {
    texto: '¿Con qué dependencia quieres agendar?',
    expr: 'atento',
    widgets: {
      chips: [
        { label: 'Atención al ciudadano', action: 'cita:dep:Atención al ciudadano' },
        { label: 'Planeación', action: 'cita:dep:Planeación' },
        { label: 'Ambiente', action: 'cita:dep:Ambiente' },
        { label: 'Cultura', action: 'cita:dep:Cultura' },
      ],
    },
  },

  // ── Flujo 4 — Navegar (rutas REALES de innovaK) ─────────────
  navegar: {
    texto: '¿A qué sección te llevo?',
    expr: 'atento',
    widgets: {
      chips: [
        { label: 'Presupuesto', action: 'nav:presupuesto' },
        { label: 'Actividades', action: 'nav:actividades' },
        { label: 'Mapa de Kennedy', action: 'nav:mapa' },
        { label: 'Consulta con IA', action: 'nav:ia' },
      ],
    },
  },
  'nav:presupuesto': {
    texto: 'Te llevo a Presupuesto: proyectos, metas, KPIs y contratos. 👇',
    expr: 'orgulloso',
    navegar: '/presupuesto',
    lanzarTour: 'presupuesto',
    widgets: { chips: [VOLVER] },
  },
  'nav:actividades': {
    texto: 'Te llevo a Actividades: cursos, eventos, caracterizaciones y entregas. 👇',
    expr: 'orgulloso',
    navegar: '/actividades',
    lanzarTour: 'actividades',
    widgets: { chips: [VOLVER] },
  },
  'nav:mapa': {
    texto: 'Te llevo al Mapa de Kennedy: los hechos georreferenciados en el territorio. 👇',
    expr: 'orgulloso',
    navegar: '/mapa',
    widgets: { chips: [VOLVER] },
  },
  'nav:ia': {
    texto: 'Te llevo a la Consulta con IA: pregúntale a los datos en lenguaje natural. 👇',
    expr: 'orgulloso',
    navegar: '/ia',
    widgets: { chips: [VOLVER] },
  },
  'nav:tramites-online': {
    texto: 'Los trámites en línea del portal ciudadano llegarán pronto a innovaK. Por ahora te dejo en el menú.',
    expr: 'alegre',
    widgets: { chips: [VOLVER] },
  },
  'nav:pagos': {
    texto: 'El módulo de pagos y PSE se integrará pronto. Por ahora te dejo en el menú.',
    expr: 'alegre',
    widgets: { chips: [VOLVER] },
  },

  // ── Flujo 5 — Noticias ──────────────────────────────────────
  noticias: {
    texto: 'Esto es lo más reciente en la localidad:',
    expr: 'alegre',
    widgets: {
      news: [
        { fecha: 'Esta semana', titulo: 'Jornada de participación ciudadana', descripcion: 'Inscríbete en los encuentros por UPZ para priorizar proyectos.' },
        { fecha: 'Este mes', titulo: 'Festival cultural de Kennedy', descripcion: 'Agenda de conciertos, danza y teatro en escenarios de la localidad.' },
        { fecha: 'Abierto', titulo: 'Banco de iniciativas recreodeportivas', descripcion: 'Postula tu colectivo u organización deportiva.' },
      ],
    },
  },
};

/** Palabras clave → acción, para texto libre (fallback antes de IA). */
export const KEYWORDS: { test: RegExp; action: string }[] = [
  { test: /pqrs|queja|petici|reclamo|sugerenc/i, action: 'pqrs' },
  { test: /cita|agenda|turno/i, action: 'cita' },
  { test: /tr[aá]mite|certificad|predial|licencia|mascota/i, action: 'tramites' },
  { test: /noticia|evento|festival/i, action: 'noticias' },
  { test: /presupuesto|proyecto|contrato|kpi|meta/i, action: 'nav:presupuesto' },
  { test: /actividad|curso|evento|caracteriz|entrega/i, action: 'nav:actividades' },
  { test: /mapa|territorio|georref|ubicaci/i, action: 'nav:mapa' },
  { test: /navegar|secci[oó]n|d[oó]nde|llego/i, action: 'navegar' },
];
