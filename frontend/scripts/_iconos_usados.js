/**
 * Qué iconos `fa-*` usa el proyecto, y dónde.
 *
 * Vive aparte porque lo consumen DOS scripts —el generador del subset y el
 * verificador— y si cada uno tuviera su propio barrido acabarían discrepando:
 * el generador dejaría fuera un icono que el verificador cree presente, o al
 * revés. La lista de qué cuenta como icono tiene que ser una sola.
 */
const fs = require('fs');
const path = require('path');

// `scripts` es esta misma carpeta: sus comentarios nombran iconos y archivos de
// fuente, y si se barre a sí misma el generador cree que el proyecto usa lo que
// la documentación menciona.
const EXCLUIR = new Set(['node_modules', '.git', 'dist', 'staticfiles',
                         '__pycache__', '_historico', '.claude', 'scripts']);
const EXT = new Set(['.ts', '.html', '.js', '.py', '.scss', '.css']);

/** Tamaño, giro y estilo: son modificadores, no iconos. */
const MODIFICADORES = new Set([
  'fa-fw', 'fa-lg', 'fa-sm', 'fa-xs', 'fa-2x', 'fa-3x', 'fa-4x', 'fa-5x',
  'fa-spin', 'fa-pulse', 'fa-border', 'fa-pull-left', 'fa-pull-right',
  'fa-stack', 'fa-stack-1x', 'fa-stack-2x', 'fa-inverse', 'fa-li', 'fa-ul',
  'fa-rotate-90', 'fa-rotate-180', 'fa-rotate-270', 'fa-flip-horizontal',
  'fa-flip-vertical', 'fa-beat', 'fa-fade', 'fa-shake', 'fa-spin-pulse',
  'fa-solid', 'fa-regular', 'fa-brands', 'fa-light', 'fa-subset',
  // Nombres de los ARCHIVOS de fuente. Aparecen en comentarios y en el CSS de
  // Font Awesome, y sin esto el barrido los confunde con iconos.
  'fa-solid-900', 'fa-regular-400', 'fa-brands-400', 'fa-v4compatibility',
  'fa-font-face', 'fa-shims',
]);

/**
 * @returns {Map<string, string[]>} icono → archivos (rutas relativas a `raiz`)
 *
 * Se barren también los `.py`: hay 12 iconos que solo existen en el registro
 * de módulos del backend (`modulos_area.py`) y llegan al template por
 * interpolación (`class="fa {{ m.icono }}"`). Un barrido que solo mirara
 * `class="…"` los perdería, y son justo los que nadie nota que faltan.
 */
function iconosUsados(raiz) {
  const usados = new Map();
  (function recorrer(dir) {
    for (const entrada of fs.readdirSync(dir, { withFileTypes: true })) {
      if (EXCLUIR.has(entrada.name)) continue;
      const p = path.join(dir, entrada.name);
      if (entrada.isDirectory()) { recorrer(p); continue; }
      if (!EXT.has(path.extname(entrada.name))) continue;
      // El propio subset generado se ignora: si no, se validaría a sí mismo.
      if (entrada.name === 'fa-subset.css') continue;
      const txt = fs.readFileSync(p, 'utf8');
      const rel = path.relative(raiz, p);
      // `(?<![-\w])` descarta las custom properties de Font Awesome
      // (`--fa-bounce-height`, `--fa-border-color`…): llevan `fa-` dentro pero
      // son variables de estilo, no iconos. Sin esto el barrido «encuentra»
      // noventa iconos inexistentes que en realidad son el propio CSS.
      for (const m of txt.matchAll(/(?<![-\w])fa-[a-z0-9-]+\b/g)) {
        const icono = m[0];
        if (MODIFICADORES.has(icono)) continue;
        if (!usados.has(icono)) usados.set(icono, []);
        const lista = usados.get(icono);
        if (!lista.includes(rel)) lista.push(rel);
      }
    }
  })(raiz);
  return usados;
}

module.exports = { iconosUsados, MODIFICADORES, EXCLUIR, EXT };
