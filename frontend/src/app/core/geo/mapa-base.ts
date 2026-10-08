/**
 * El mapa base, declarado UNA vez.
 *
 * ## Por qué existe este archivo
 *
 * Esta URL estaba escrita a mano en OCHO componentes —el mapa de Kennedy, el
 * detalle de subgrupo, el de infraestructura, las instituciones educativas, el
 * formulario de evento, los CAI del área, los festivales y el selector de
 * dirección—. El 8 de octubre de 2026 las baldosas dejaron de llegar a los
 * navegadores de la Alcaldía: el servidor sí las obtiene (PNG real de 256×256,
 * verificado), pero el navegador del funcionario sale por otra red y por ahí
 * algo responde «key required». Cambiar de proveedor, o apuntar a un proxy
 * propio, significaba editar ocho archivos y no olvidar ninguno.
 *
 * Ahora es un sitio. Si mañana hay que cambiarlo, se cambia acá.
 *
 * ## Las baldosas las pide el NAVEGADOR, no el servidor
 *
 * Es la parte que cuesta ver cuando algo falla: nuestro backend no interviene.
 * Si la red del visitante bloquea el proveedor, el mapa se rompe aunque todo
 * lo nuestro esté sano — los seis endpoints geo responden con dato, Leaflet va
 * empaquetado local y su CSS está en el bundle. Por eso la salida de fondo es
 * servir las baldosas por nuestro propio dominio.
 */
import type { TileLayerOptions } from 'leaflet';

/**
 * De dónde salen las baldosas.
 *
 * Para servirlas por nuestro dominio —y dejar de depender de la red de cada
 * visitante— esta constante pasa a una ruta relativa (por ejemplo
 * `tiles/{z}/{x}/{y}.png`) y nginx hace el `proxy_pass` con caché. El resto de
 * la aplicación no se entera.
 */
export const MAPA_BASE_URL =
  'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png';

/** La atribución es obligatoria por la licencia de OpenStreetMap y de CARTO. */
export const MAPA_BASE_OPCIONES: TileLayerOptions = {
  attribution: '&copy; OpenStreetMap &copy; CARTO',
  subdomains: 'abcd',
  maxZoom: 19,
};
