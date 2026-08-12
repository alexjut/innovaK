/**
 * Modelo del formulario público del Banco de Iniciativas — DOCUMENTO MAESTRO
 * (versión 2026-07-29, 9 secciones).
 *
 * Los nombres de las propiedades que viajan al servidor son EXACTAMENTE los
 * campos de `CabeceraDocumentoMaestroMixin` / `InscripcionBancoIniciativa`.
 * Cuando el nombre local difiere del que espera el POST (porque acá describe
 * mejor la UI), la traducción está en un solo lugar: `construirPayload()` del
 * componente. No se traduce en el template.
 *
 * Este archivo NO importa Angular a propósito: es dato y tipos, así se puede
 * testear sin TestBed y lo puede reusar la vista del organizador.
 */

// ═══════════════════════════════════════════════════════════════════════
// Catálogos que devuelve GET /banco-iniciativas/api/publico/<id>/catalogos/
// ═══════════════════════════════════════════════════════════════════════

export interface CatalogoItem {
  codigo: string | number;
  nombre: string;
}

export interface EscenarioItem extends CatalogoItem {
  /** FK → red(codigo). Es lo que empareja el escenario con su nivel (§4.2/§7.9.1). */
  categoria_pot?: string | null;
}

export interface RangoEtarioItem extends CatalogoItem {
  edad_min?: number | null;
  edad_max?: number | null;
}

export interface ChoiceItem {
  valor: string;
  etiqueta: string;
}

/** §5.2 y §7.8 — familia (checkbox de primer nivel) con su submenú en cascada. */
export interface FamiliaEnfoque {
  codigo: string;
  nombre: string;
  opciones: { codigo: string; nombre: string }[];
}

/**
 * Solo se declaran las claves que el formulario consume. El endpoint devuelve
 * más (catálogos de lotes anteriores que el Documento Maestro retiró de la
 * captura); no se listan para que nadie las vuelva a pintar por inercia.
 */
export interface BancoCatalogos {
  evento: { id: number; nombre: string; fecha_fin?: string };
  // §1
  tipos_organizacion: CatalogoItem[];
  tipos_documento: CatalogoItem[];
  niveles_educativos: CatalogoItem[];
  // §2
  upzs: CatalogoItem[];
  barrios: CatalogoItem[];
  estratos: number[];
  // §3
  rangos_experiencia: CatalogoItem[];
  rangos_poblacion: CatalogoItem[];
  // §4 y §7.9.1
  redes: CatalogoItem[];
  escenarios: EscenarioItem[];
  modalidades: CatalogoItem[];
  disciplinas_deportivas: CatalogoItem[];
  // §5
  rangos_etarios: RangoEtarioItem[];
  enfoques_familias_52: FamiliaEnfoque[];
  // §6
  instancias_concertacion: CatalogoItem[];
  tipos_beneficio_alk: CatalogoItem[];
  // §7
  cobertura_staff_choices: ChoiceItem[];
  cobertura_comunidad_choices: ChoiceItem[];
  cobertura_indirectos_choices: ChoiceItem[];
  diversidad_genero_choices: ChoiceItem[];
  enfoques_familias_78: FamiliaEnfoque[];
  /**
   * Umbrales que el servidor valida, publicados por el endpoint para que el
   * contador que ve el ciudadano y el validador que rechaza el POST sean el
   * MISMO número. Opcional en el tipo a propósito: si un despliegue viejo del
   * backend no los manda, el formulario cae a las constantes de este archivo en
   * lugar de quedarse sin mínimos.
   */
  reglas?: {
    narrativa_min_caracteres?: number;
    ambiental_min_palabras?: number;
    metodologia_max_caracteres?: number;
    objetivos_especificos?: number;
    enfoques_52?: { max_familias?: number; max_adicionales?: number };
    presupuesto?: {
      tope_maximo_cop?: number;
      mensaje_bloqueo?: string;
      regla?: string;
    };
  };
}

// ═══════════════════════════════════════════════════════════════════════
// Filas de las colecciones (§5.2, §7.8, §8)
// ═══════════════════════════════════════════════════════════════════════

/**
 * Familia de enfoque activada. **La posición en el arreglo es el dato**: §7.8
 * puntúa por el orden en que el ciudadano activó las etiquetas, así que el
 * `orden` que viaja al servidor es el índice + 1 de este arreglo, nunca el
 * orden del catálogo.
 */
export interface SeleccionEnfoque {
  familia: string;
  opciones: Set<string>;
}

/** §8.2 + §8.3 · Actividad con las celdas de su cronograma (`"mes-semana"`). */
export interface FilaActividad {
  nombre: string;
  descripcion: string;
  celdas: Set<string>;
}

/** §8.4 · Integrante del equipo de trabajo. */
export interface FilaEquipo {
  nombre: string;
  nivel_formacion_codigo: string;
  rol: string;
}

/**
 * §8.5 · Rubro del presupuesto. `valor_total` NO está: es columna generada en
 * la BD (`cantidad * valor_unitario`) y solo se muestra calculada en vivo.
 */
export interface FilaPresupuesto {
  actividad_idx: number | null;
  descripcion_rubro: string;
  cantidad: number | null;
  valor_unitario: number | null;
}

/** Anexos documentales. Viven fuera del modelo persistible: un File no se serializa. */
export interface BancoAnexos {
  soporte_legal: File | null;
  cedula_representante: File | null;
  rut: File | null;
  reconocimiento_deportivo: File | null;
  /** §1 · elegibilidad territorial. No puntúa. */
  residencia_representante: File | null;

  // ── Soportes que CONDICIONAN el puntaje del Bloque 1 ─────────────────
  // Documento Guía: «una opción puntuable sin su archivo indexado congela la
  // calificación del criterio». El backend los exige solo cuando la respuesta
  // del proponente puntúa; acá se declaran todos y la UI los pide donde toca.
  staff_listado: File | null;                 // §3.1
  trayectoria: File | null;                   // §3.2
  composicion_genero: File | null;            // §3.3
  beneficiarios_listado: File | null;         // §3.4
  arraigo_uso_espacio: File | null;           // §4.2
  caracterizacion_demografica: File | null;   // §5.1
  instancias_actas: File | null;              // §6.1
  declaracion_antecedentes: File | null;      // §6.2

  firma: File | null;
}

// ═══════════════════════════════════════════════════════════════════════
// Estado del formulario
// ═══════════════════════════════════════════════════════════════════════

export interface BancoForm {
  // ── §1 · Registro de la organización ────────────────────────────────
  nombre_organizacion: string;
  tipo_organizacion: string;
  numero_soporte_legal: string;
  rep_nombre1: string;
  rep_nombre2: string;
  rep_apellido1: string;
  rep_apellido2: string;
  rep_tipo_doc: string;
  rep_numero_doc: string;
  nivel_educativo: string;
  titulos_obtenidos: string;

  // ── §2 · Contacto y ubicación ──────────────────────────────────────
  telefono: string;
  correo: string;
  /** Compuerta de §2: si es `false`, 2.3/2.4/2.5 quedan en NULL controlado. */
  tiene_sede_fisica: boolean | null;
  upz: string;
  /**
   * Código del catálogo `barrio`. El servidor exige el código cuando hay sede
   * (`barrio`, ModelChoiceField), no el nombre escrito: `barrio_texto` se
   * deriva del código al armar el payload y existe solo para el histórico.
   */
  barrio: string;
  direccion: string;
  direccion_lon: number | null;
  direccion_lat: number | null;
  estrato: string;
  redes_web: string;
  redes_facebook: string;
  redes_instagram: string;

  // ── §3 · Capacidad de la organización ──────────────────────────────
  tamano_staff_num: number | null;
  anios_experiencia: string;
  composicion_organizacion: string;
  rango_poblacion: string;

  // ── §4 · Arraigo territorial ───────────────────────────────────────
  modalidad_actividad: string;
  disciplina_actividad: string;
  disciplina_actividad_otro: string;
  arraigo_red: string;
  /** Botones del nivel elegido → puente `escenarios_actuales`. */
  arraigo_escenarios: Set<string>;
  arraigo_escenario_otro: string;
  arraigo_espacio_nombre: string;
  arraigo_direccion: string;
  arraigo_lon: number | null;
  arraigo_lat: number | null;
  arraigo_estrato: string;
  arraigo_actividad: string;

  // ── §5 · Diversidad e inclusión comunitaria ────────────────────────
  rango_etarios: Set<string>;
  enfoques_52: SeleccionEnfoque[];

  // ── §6 · Participación ─────────────────────────────────────────────
  participa_espacio: boolean | null;
  instancias: Set<string>;
  beneficio_alk: string;

  // ── §7 · Formulación de la iniciativa ──────────────────────────────
  problematica: string;
  justificacion: string;
  modalidad_propuesta: string;
  disciplina_principal: string;
  otros_deportes: string;
  objetivo_general: string;
  objetivos_especificos: string[];
  cobertura_staff: string;
  cobertura_comunidad: string;
  cobertura_indirectos: string;
  ciclo_vital: Set<string>;
  diversidad_genero_propuesta: string;
  enfoques_78: SeleccionEnfoque[];
  ejecucion_red: string;
  /** Botones del nivel elegido → puente `escenarios`. */
  ejecucion_escenarios: Set<string>;
  ejecucion_escenario_otro: string;
  nombre_espacio_ejecucion: string;
  direccion_espacio_ejecucion: string;
  ejecucion_lon: number | null;
  ejecucion_lat: number | null;
  /** Estrato DECLARADO. El que puntúa lo certifica IDECA en el servidor. */
  ejecucion_estrato: string;
  sostenibilidad_ambiental: boolean | null;
  sostenibilidad_sustento: string;

  // ── §8 · Gestión operativa, financiera y presupuesto ───────────────
  metodologia: string;
  actividades: FilaActividad[];
  equipo: FilaEquipo[];
  presupuesto: FilaPresupuesto[];

  // ── §9 · Presentación de la iniciativa ─────────────────────────────
  compromiso_redes: boolean;
  compromiso_carta_1ano: boolean;
  compromiso_actualizacion: boolean;
  firma_cedula: string;
  firma_fecha: string;
  declaracion_buena_fe: boolean;
}

export function filaActividadVacia(): FilaActividad {
  return { nombre: '', descripcion: '', celdas: new Set<string>() };
}

export function filaEquipoVacia(): FilaEquipo {
  return { nombre: '', nivel_formacion_codigo: '', rol: '' };
}

export function filaPresupuestoVacia(): FilaPresupuesto {
  return {
    actividad_idx: null,
    descripcion_rubro: '',
    cantidad: null,
    valor_unitario: null,
  };
}

export function anexosVacios(): BancoAnexos {
  return {
    soporte_legal: null,
    cedula_representante: null,
    rut: null,
    reconocimiento_deportivo: null,
    residencia_representante: null,
    staff_listado: null,
    trayectoria: null,
    composicion_genero: null,
    beneficiarios_listado: null,
    arraigo_uso_espacio: null,
    caracterizacion_demografica: null,
    instancias_actas: null,
    declaracion_antecedentes: null,
    firma: null,
  };
}

/** Estado inicial. Función y no constante: cada carga necesita Sets propios. */
export function formInicial(): BancoForm {
  return {
    nombre_organizacion: '',
    tipo_organizacion: '',
    numero_soporte_legal: '',
    rep_nombre1: '',
    rep_nombre2: '',
    rep_apellido1: '',
    rep_apellido2: '',
    rep_tipo_doc: '',
    rep_numero_doc: '',
    nivel_educativo: '',
    titulos_obtenidos: '',

    telefono: '',
    correo: '',
    tiene_sede_fisica: null,
    upz: '',
    barrio: '',
    direccion: '',
    direccion_lon: null,
    direccion_lat: null,
    estrato: '',
    redes_web: '',
    redes_facebook: '',
    redes_instagram: '',

    tamano_staff_num: null,
    anios_experiencia: '',
    composicion_organizacion: '',
    rango_poblacion: '',

    modalidad_actividad: '',
    disciplina_actividad: '',
    disciplina_actividad_otro: '',
    arraigo_red: '',
    arraigo_escenarios: new Set<string>(),
    arraigo_escenario_otro: '',
    arraigo_espacio_nombre: '',
    arraigo_direccion: '',
    arraigo_lon: null,
    arraigo_lat: null,
    arraigo_estrato: '',
    arraigo_actividad: '',

    rango_etarios: new Set<string>(),
    enfoques_52: [],

    participa_espacio: null,
    instancias: new Set<string>(),
    beneficio_alk: '',

    problematica: '',
    justificacion: '',
    modalidad_propuesta: '',
    disciplina_principal: '',
    otros_deportes: '',
    objetivo_general: '',
    objetivos_especificos: ['', '', ''],
    cobertura_staff: '',
    cobertura_comunidad: '',
    cobertura_indirectos: '',
    ciclo_vital: new Set<string>(),
    diversidad_genero_propuesta: '',
    enfoques_78: [],
    ejecucion_red: '',
    ejecucion_escenarios: new Set<string>(),
    ejecucion_escenario_otro: '',
    nombre_espacio_ejecucion: '',
    direccion_espacio_ejecucion: '',
    ejecucion_lon: null,
    ejecucion_lat: null,
    ejecucion_estrato: '',
    sostenibilidad_ambiental: null,
    sostenibilidad_sustento: '',

    metodologia: '',
    actividades: [filaActividadVacia()],
    equipo: [filaEquipoVacia()],
    presupuesto: [filaPresupuestoVacia()],

    compromiso_redes: false,
    compromiso_carta_1ano: false,
    compromiso_actualizacion: false,
    firma_cedula: '',
    firma_fecha: new Date().toISOString().slice(0, 10),
    declaracion_buena_fe: false,
  };
}

// ═══════════════════════════════════════════════════════════════════════
// Constantes de la UI
// ═══════════════════════════════════════════════════════════════════════

/** Las 9 secciones del documento, con el mismo nombre en todo el aplicativo. */
export const SECCIONES = [
  { n: 1, corto: 'Organización', titulo: 'Registro de la organización' },
  { n: 2, corto: 'Contacto', titulo: 'Contacto y ubicación' },
  { n: 3, corto: 'Capacidad', titulo: 'Capacidad de la organización' },
  { n: 4, corto: 'Arraigo', titulo: 'Arraigo territorial' },
  { n: 5, corto: 'Inclusión', titulo: 'Diversidad e inclusión comunitaria' },
  { n: 6, corto: 'Participación', titulo: 'Participación' },
  { n: 7, corto: 'Formulación', titulo: 'Formulación de la iniciativa y enfoques' },
  { n: 8, corto: 'Operación', titulo: 'Gestión operativa, financiera y presupuesto' },
  { n: 9, corto: 'Firma', titulo: 'Presentación de la iniciativa' },
] as const;

export const TOTAL_SECCIONES = SECCIONES.length;

/**
 * §4.2 y §7.9.1 · Los 4 niveles de espacio, EN EL ORDEN DEL DOCUMENTO.
 *
 * `red` es el código real del catálogo `red`, que es también el valor de
 * `escenario.categoria_pot`: de ahí salen los botones dinámicos de cada nivel
 * sin una segunda tabla ni un mapa hardcodeado de etiquetas.
 *
 * El orden es el del documento (barrial → dotacional → proximidad →
 * estructurante), no el `orden` del catálogo, que es el inverso. No se
 * muestran los puntos de cada nivel: el modelo es ciego por diseño.
 */
export const NIVELES_ESPACIO = [
  {
    red: 'otros_practica',
    etiqueta: 'Opción 1 · Espacios de práctica barrial o no convencional',
    descripcion: 'Espacios informales, de cercanía, sin infraestructura formalizada.',
  },
  {
    red: 'otros_dotacionales',
    etiqueta: 'Opción 2 · Espacios dotacionales y ambientales de la localidad',
    descripcion: 'Equipamientos comunitarios y entornos de uso colectivo institucional.',
  },
  {
    red: 'red_proximidad',
    etiqueta: 'Opción 3 · Parques de la red de proximidad',
    descripcion: 'Parques vecinales y de bolsillo, menores a una hectárea de extensión.',
  },
  {
    red: 'red_estructurante',
    etiqueta: 'Opción 4 · Parques de la red estructurante',
    descripcion: 'Grandes parques metropolitanos y zonales integrados del distrito.',
  },
] as const;

/**
 * §3.3 · Composición y liderazgo de género. Los códigos son los que ya guarda
 * `composicion_organizacion`; las etiquetas se homologan milimétricamente con
 * los sectores sociales LGTBIQ+ como pide el documento.
 */
export const COMPOSICION_GENERO_OPCIONES: ChoiceItem[] = [
  { valor: 'solo_mujeres', etiqueta: 'Únicamente mujeres' },
  { valor: 'mayor_mujeres', etiqueta: 'Mayoritariamente mujeres (más del 60 %)' },
  { valor: 'diversas', etiqueta: 'Poblaciones diferenciales por género (LGTBIQ+)' },
  { valor: 'equitativo', etiqueta: 'Composición mixta' },
  { valor: 'mayor_hombres', etiqueta: 'Mayoritariamente hombres' },
  { valor: 'solo_hombres', etiqueta: 'Únicamente hombres' },
];

/** §5.2 · Familia con asignación propia; las demás cuentan como "adicionales". */
export const FAMILIA_MUJER_GENERO_52 = 'c52_mujer_genero';

/** §5.2 · Cuántas familias adicionales a "Mujer y Género" se pueden marcar. */
export const MAX_ENFOQUES_ADICIONALES_52 = 3;

/** §7.1 y §7.2 · Extensión mínima exigida en frontend. */
export const MIN_CARACTERES_NARRATIVA = 200;

/** §7.10 · El sustento ambiental se mide en palabras, no en caracteres. */
export const MIN_PALABRAS_SUSTENTO = 100;

/**
 * §8.1 · Control restrictivo de longitud de la metodología. Mismo valor que
 * `MAX_CARACTERES_METODOLOGIA` del form del servidor: si el frontend corta más
 * corto, el ciudadano pierde texto que era válido.
 */
export const MAX_CARACTERES_METODOLOGIA = 5000;

/**
 * §8.5 · Techo absoluto de la escala de topes ($17M para las posiciones 1-31).
 * Se usa SOLO para avisar; el tope real depende del ranking, que el ciudadano
 * no conoce ni debe conocer. El bloqueo definitivo lo aplica el servidor.
 */
export const TOPE_PRESUPUESTO_MAXIMO = 17_000_000;

export const MESES_CRONOGRAMA = [1, 2, 3, 4] as const;
export const SEMANAS_CRONOGRAMA = [1, 2, 3, 4] as const;

// ═══════════════════════════════════════════════════════════════════════
// Utilidades
// ═══════════════════════════════════════════════════════════════════════

export function codigoStr(v: string | number): string {
  return String(v);
}

/** Cuenta palabras reales (colapsa espacios y saltos de línea). */
export function contarPalabras(texto: string): number {
  const limpio = (texto ?? '').trim();
  return limpio ? limpio.split(/\s+/).length : 0;
}

/** `true` si la familia es la opción excluyente "Ninguno" del catálogo. */
export function esNinguno(familia: FamiliaEnfoque): boolean {
  return familia.nombre.trim().toLowerCase() === 'ninguno';
}

/** Total de un rubro. Espeja la columna generada de la BD, solo para mostrar. */
export function totalRubro(fila: FilaPresupuesto): number {
  const cantidad = Number(fila.cantidad ?? 0);
  const unitario = Number(fila.valor_unitario ?? 0);
  if (!Number.isFinite(cantidad) || !Number.isFinite(unitario)) return 0;
  return cantidad * unitario;
}

export function totalPresupuesto(filas: FilaPresupuesto[]): number {
  return filas.reduce((suma, fila) => suma + totalRubro(fila), 0);
}
