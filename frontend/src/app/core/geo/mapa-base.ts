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
export const MAPA_BASE_URL = '/tiles/v1/{z}/{x}/{y}{r}.png';

/**
 * EL `v1` ES UN FUSIBLE, no decoración.
 *
 * nginx sirve estas respuestas con `immutable`, así que el navegador no
 * las revalida nunca. El 2026-10-08, mientras se diagnosticaba el mapa, se
 * sirvieron por esta ruta las teselas de aviso de CartoDB con ese
 * encabezado: quien cargó el mapa en esos minutos se quedó con la imagen
 * mala clavada, y ni recargando se iba.
 *
 * Al cambiar de proveedor o de estilo se SUBE a v2 y el problema se
 * resuelve solo. Pedirle a la gente que limpie la caché no es un arreglo:
 * el siguiente visitante tendría lo mismo.
 */

/**
 * La BARRA INICIAL de arriba es obligatoria, y cuesta ver por qué.
 *
 * El SPA se sirve con `<base href="/app/">`, así que una ruta SIN barra se
 * resuelve contra él: `tiles/10/292/492.png` se pide como
 * `/app/tiles/10/292/492.png`, y eso **devuelve 200 con el index.html del
 * SPA** —13 KB de HTML— porque el catch-all de Angular contesta cualquier
 * ruta desconocida. Leaflet recibiría HTML en lugar de un PNG y el mapa
 * seguiría roto, ahora con un 200 que se ve perfectamente sano. Se probó y
 * pasó exactamente eso.
 *
 * Esto es lo CONTRARIO de la regla de los archivos de `frontend/public`, que
 * van sin barra justamente porque viven bajo `/app/`. Acá el recurso lo sirve
 * nginx en la raíz del dominio, no el SPA.
 *
 * `subdomains` ya no viaja: repartía las peticiones entre a/b/c/d del
 * proveedor y ahora hay un solo origen, el nuestro. Dejarlo haría que Leaflet
 * pidiera `a.`, `b.`… de nuestro propio dominio, que no existen.
 */
export const MAPA_BASE_OPCIONES: TileLayerOptions = {
  // Obligatoria por la licencia de OpenStreetMap y de CARTO, aunque las
  // baldosas pasen por nuestro proxy: la fuente sigue siendo la suya.
  attribution: '&copy; OpenStreetMap &copy; CARTO',
  maxZoom: 19,
};
