/**
 * Registro declarativo de las capas del Mapa de Kennedy (C2 — PR-0).
 *
 * Hoy, agregar una capa al mapa obliga a tocar 5 sitios dispersos del componente
 * (`mapa.component.ts`, ~2.480 líneas) y mantenerlos sincronizados a mano: el
 * `<label>` del checkbox, una entrada en el objeto `capas`, una rama en
 * `toggleCapa()`, un método `cargarXxx()` y un campo privado `xxxLayer`. Este
 * archivo es la fuente única de verdad de la que —en los PRs siguientes— se
 * derivan el template y la lógica, de modo que una capa nueva pase a ser UNA
 * entrada de este array.
 *
 * Es el mismo patrón que el proyecto ya usa en el backend
 * (`apps/georeferenciacion/services/capas.py`, con su test que exige el mínimo
 * de cada entrada): C2 no inventa nada, lo lleva al frontend.
 *
 * **Este PR-0 es aditivo: define el registro y su contrato (spec), pero todavía
 * NO cablea el componente.** El rewiring (template → toggle → loaders) va en PRs
 * siguientes, capa por capa, con verificación visual — un bug de orden de capas
 * ya se coló una vez sin que consola ni tipos lo cazaran (ver memoria del
 * proyecto sobre la estratificación en canvas), así que esa parte no se hace a
 * ciegas.
 *
 * **`publica` es lo que resuelve B1 de forma estructural.** Hoy "el Banco exige
 * login" es implícito: el anónimo marca el check, recibe un 401 y solo entonces
 * el mapa lo traduce a "requiere iniciar sesión". Declararlo aquí (espejo de
 * `@jwt_or_session_required` en `apps/georeferenciacion/views/apis.py`) hace que
 * el componente lo sepa ANTES del clic, y deja la superficie pública del mapa
 * declarada en un solo array que se puede comparar contra el backend.
 */

/** Clave estable de cada capa. Unión (no `string`) para que `capas[clave]`
 *  type-chequee y el acceso por punto (`capas.parques`) siga permitido bajo
 *  `noPropertyAccessFromIndexSignature`. */
export type ClaveCapa =
  | 'eventos'
  | 'parques' | 'barrios' | 'upz' | 'estratificacion' | 'banco' | 'localidad'
  | 'festivales' | 'colegios' | 'cai' | 'tramosViales' | 'parquesObras'
  | 'escuelasCultura' | 'escuelasDeporte';

export type RenderCapa = 'poligono' | 'punto' | 'linea';

/** Bloque especial que aparece bajo el checkbox de ciertas capas. */
export type SubLeyenda = 'estrato' | 'cai' | 'avance';

export interface CapaDescriptor {
  /** Clave estable; coincide con la propiedad del objeto `capas` del componente. */
  clave: ClaveCapa;
  /** Texto del `<label>` en el panel. */
  label: string;
  /** Clase(s) CSS COMPLETAS del swatch (cuadro/línea/punto de color) junto al
   *  label. Vacío si la capa no tiene checkbox propio. */
  swatch: string;
  /** Emoji dentro del swatch, para las capas que lo usan (★/🎓/🛡/🌳). */
  swatchIcon?: string;
  render: RenderCapa;
  /** Se descarga al marcar el check, no al abrir el mapa. */
  lazy: boolean;
  /** Espeja el permiso del backend: `false` = requiere login. Hoy solo el Banco. */
  publica: boolean;
  /** Tiene checkbox propio en el panel. `false` = se activa por otra vía. */
  checkbox: boolean;
  /** Arranca encendida al abrir el mapa. */
  defaultOn: boolean;
  /** Sub-leyenda especial bajo el check (filtro de estrato, tipos de CAI, avance). */
  subLeyenda?: SubLeyenda;
}

/**
 * Las 14 capas conmutables del mapa. El orden es el del panel.
 *
 * Las escuelas (Cultura/Deporte) no tienen checkbox propio: las gobierna la
 * pestaña de subgrupo (decisión Alex 2026-06-03), por eso `checkbox:false`.
 *
 * **Ninguna capa de datos arranca encendida (MAP-03, decisión Alex 2026-08-06):
 * el mapa abre solo con el croquis de Kennedy.** `localidad` es la única con
 * `defaultOn:true` y es justamente el croquis — no trae datos, dibuja el borde.
 * Antes, eventos y escuelas se cargaban sin pasar por este registro: 38,9 KB
 * gzip en el arranque contra los 10,8 KB de hoy. Si alguna capa vuelve a
 * cargarse fuera del registro, este archivo deja de describir lo que pasa.
 */
export const CAPAS_MAPA: CapaDescriptor[] = [
  { clave: 'eventos', label: 'Actividades', swatch: 'mapa-dot mapa-dot--evento', render: 'punto', lazy: true, publica: true, checkbox: true, defaultOn: false },
  { clave: 'parques', label: 'Parques', swatch: 'mapa-poly mapa-poly--parque', render: 'poligono', lazy: true, publica: true, checkbox: true, defaultOn: false },
  { clave: 'barrios', label: 'Barrios', swatch: 'mapa-poly mapa-poly--barrio', render: 'poligono', lazy: true, publica: true, checkbox: true, defaultOn: false },
  { clave: 'upz', label: 'UPZ', swatch: 'mapa-poly mapa-poly--upz', render: 'poligono', lazy: true, publica: true, checkbox: true, defaultOn: false },
  { clave: 'estratificacion', label: 'Estratificación (IDECA)', swatch: 'mapa-poly mapa-poly--estrato', render: 'poligono', lazy: true, publica: true, checkbox: true, defaultOn: false, subLeyenda: 'estrato' },
  { clave: 'banco', label: 'Iniciativas del Banco (Deporte)', swatch: 'mapa-dot mapa-dot--banco', render: 'punto', lazy: true, publica: false, checkbox: true, defaultOn: false },
  { clave: 'localidad', label: 'Localidad', swatch: 'mapa-line mapa-line--localidad', render: 'linea', lazy: false, publica: true, checkbox: true, defaultOn: true },
  { clave: 'festivales', label: 'Festivales', swatch: 'mapa-festival-dot', swatchIcon: '★', render: 'punto', lazy: true, publica: true, checkbox: true, defaultOn: false },
  { clave: 'colegios', label: 'Colegios distritales', swatch: 'mapa-colegio-dot', swatchIcon: '🎓', render: 'punto', lazy: true, publica: true, checkbox: true, defaultOn: false },
  { clave: 'cai', label: 'CAI (Policía)', swatch: 'mapa-cai-dot', swatchIcon: '🛡', render: 'punto', lazy: true, publica: true, checkbox: true, defaultOn: false, subLeyenda: 'cai' },
  { clave: 'tramosViales', label: 'Malla vial / obras', swatch: 'mapa-line mapa-line--obra', render: 'linea', lazy: true, publica: true, checkbox: true, defaultOn: false, subLeyenda: 'avance' },
  { clave: 'parquesObras', label: 'Parques (obras)', swatch: 'mapa-obra-dot', swatchIcon: '🌳', render: 'punto', lazy: true, publica: true, checkbox: true, defaultOn: false, subLeyenda: 'avance' },
  { clave: 'escuelasCultura', label: 'Escuelas de Cultura', swatch: '', render: 'punto', lazy: true, publica: true, checkbox: false, defaultOn: false },
  { clave: 'escuelasDeporte', label: 'Escuelas de Deporte', swatch: '', render: 'punto', lazy: true, publica: true, checkbox: false, defaultOn: false },
];

/** El descriptor de una capa por su clave, o `undefined` si no existe. */
export function capaPorClave(clave: string): CapaDescriptor | undefined {
  return CAPAS_MAPA.find(c => c.clave === clave);
}

/** Objeto `{clave: defaultOn}` — el estado inicial del panel, derivado del registro. */
export function defaultsCapas(): Record<ClaveCapa, boolean> {
  return Object.fromEntries(
    CAPAS_MAPA.map(c => [c.clave, c.defaultOn]),
  ) as Record<ClaveCapa, boolean>;
}
