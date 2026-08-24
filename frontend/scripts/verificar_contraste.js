#!/usr/bin/env node
/**
 * Verifica el CONTRASTE de las parejas texto/fondo de todos los componentes.
 *
 *     node scripts/verificar_contraste.js          # reporta lo nuevo
 *     node scripts/verificar_contraste.js --todo   # reporta también la línea base
 *     node scripts/verificar_contraste.js --sellar # regraba la línea base
 *
 * Existe por el mismo motivo que `verificar_iconos_fa.js`: el modo de falla es
 * SILENCIOSO. Un gris de 2.5:1 no rompe el build, no sale en ningún log y en la
 * pantalla del que lo escribió —monitor bueno, luz de oficina— se ve bien. Lo
 * descubre el que lo usa en un portátil contra una ventana, y no lo reporta:
 * asume que así es el sistema.
 *
 * QUÉ MIDE. Compila cada hoja (los .scss y los `styles:` incrustados en los
 * .ts) y, para cada regla con `color`, resuelve el fondo subiendo por el
 * selector, mezcla los alfas y calcula el ratio WCAG 2.1. Exige 4.5:1 en texto
 * normal y 3:1 en texto grande (>=24px, o >=18.66px en negrilla).
 *
 * QUÉ NO MIDE, y hay que saberlo para no confiarse:
 *   - Fondos que vienen de una clase hermana (BEM plano: `.hero__subtitle` no
 *     "sabe" que vive dentro de `.hero`). Salen como «fondo supuesto blanco».
 *   - Fondos puestos desde el TypeScript o por un binding.
 *   - Imágenes de fondo.
 * Por eso hay línea base: lo que el script no puede decidir se revisa a mano
 * UNA vez, se sella con su motivo, y no vuelve a molestar.
 *
 * LÍNEA BASE. `scripts/_contraste_base.json` guarda lo ya conocido. El script
 * sale con código 1 SOLO si aparece algo que no estaba: sirve en CI desde el
 * primer día sin tener que arreglar antes toda la app.
 */
const fs = require('fs');
const path = require('path');
const sass = require(path.resolve(__dirname, '../node_modules/sass'));

const RAIZ = path.resolve(__dirname, '..');
const BASE = path.join(__dirname, '_contraste_base.json');
const BLANCO = [255, 255, 255];

// ── WCAG 2.1 ────────────────────────────────────────────────────────────────
const canal = (c) => { const s = c / 255; return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); };
const lum = ([r, g, b]) => 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b);
function ratio(a, b) { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); }

function rgb(txt) {
  if (!txt) return null;
  txt = txt.trim();
  let m = txt.match(/^#([0-9a-f]{3})$/i);
  if (m) return m[1].split('').map((c) => parseInt(c + c, 16));
  m = txt.match(/^#([0-9a-f]{6})$/i);
  if (m) return [0, 2, 4].map((i) => parseInt(m[1].slice(i, i + 2), 16));
  m = txt.match(/^rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)\s*(?:[,/]\s*([\d.]+)\s*)?\)$/i);
  if (m) return [+m[1], +m[2], +m[3], m[4] === undefined ? 1 : +m[4]];
  return null;
}
const sobre = (fg, bg) => (fg.length < 4 || fg[3] === 1 ? fg.slice(0, 3)
  : [0, 1, 2].map((i) => Math.round(fg[i] * fg[3] + bg[i] * (1 - fg[3]))));

// ── Compilación ─────────────────────────────────────────────────────────────
function compilar(scss, dir) {
  return sass.compileString(scss, {
    loadPaths: [dir, path.join(RAIZ, 'src'), path.join(RAIZ, 'src/styles')],
    logger: { warn: () => {}, debug: () => {} },
  }).css;
}

// ── Análisis de una hoja ya compilada ───────────────────────────────────────
function analizar(css) {
  // Los comentarios se quitan ANTES: sass los deja en la salida y quedan
  // pegados al selector de la regla siguiente, que entonces no se encuentra.
  const limpio = css.replace(/\/\*[\s\S]*?\*\//g, '');
  const reglas = [];
  for (const m of limpio.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    const decls = {};
    for (const d of m[2].split(';')) { const i = d.indexOf(':'); if (i > 0) decls[d.slice(0, i).trim()] = d.slice(i + 1).trim(); }
    reglas.push({ sel: m[1].trim().replace(/\s+/g, ' '), decls });
  }

  const fondos = new Map();
  for (const r of reglas) {
    const b = r.decls.background || r.decls['background-color'];
    if (!b) continue;
    // Un degradado no tiene UN fondo sino un rango: se guardan todos los stops
    // y luego se evalúa contra el PEOR, no contra un extremo cómodo.
    const cs = /gradient\(/i.test(b)
      ? (b.match(/#[0-9a-f]{3,6}|rgba?\([^)]*\)/gi) || []).map(rgb).filter(Boolean)
      : [rgb(b.split(' ')[0])].filter(Boolean);
    if (cs.length) for (const s of r.sel.split(',')) fondos.set(s.trim(), cs);
  }

  const pelado = (t) => t.replace(/::?[a-z-]+(\([^)]*\))?/g, '');
  // En CSS compilado el anidamiento BEM desaparece: `.hero__subtitle` es un
  // selector plano, sin relación con `.hero`. Pero en la PANTALLA sí está
  // dentro, y hereda su fondo. Sin este paso, todo texto sobre el hero rojo se
  // evaluaba contra blanco. Se sube por el nombre: `.a__b--c` → `.a__b` → `.a`.
  function ascendenciaBem(t) {
    const out = [];
    let m = t.match(/^(\.[A-Za-z][\w-]*?)(--[\w-]+)$/);
    if (m) { out.push(m[1]); t = m[1]; }
    while ((m = t.match(/^(\.[A-Za-z][\w-]*?)__[\w-]+$/))) { out.push(m[1]); t = m[1]; }
    return out;
  }
  function fondoDe(sel) {
    const partes = sel.split(' ');
    const cands = [];
    for (let n = partes.length; n > 0; n--) {
      const p = partes.slice(0, n).join(' ');
      cands.push(p, pelado(p));
      if (n === partes.length) cands.push(...ascendenciaBem(pelado(partes[n - 1])));
    }
    cands.push(partes[partes.length - 1], pelado(partes[partes.length - 1]));
    for (const c of cands) if (c && fondos.has(c)) return fondos.get(c).map((x) => sobre(x, BLANCO));
    return null;
  }

  const tam = new Map();
  for (const r of reglas) if (r.decls['font-size']) for (const s of r.sel.split(',')) tam.set(s.trim(), r.decls['font-size']);
  function px(sel, decls) {
    let f = decls['font-size'];
    if (!f) { const p = sel.split(' '); for (let n = p.length; n > 0 && !f; n--) f = tam.get(p.slice(0, n).join(' ')); }
    const m = f && f.match(/^([\d.]+)(px|rem)$/);
    return m ? (m[2] === 'rem' ? +m[1] * 16 : +m[1]) : null;
  }

  const fallos = [];
  let cegados = 0;
  for (const r of reglas) {
    if (!r.decls.color) continue;
    const fg0 = rgb(r.decls.color);
    if (!fg0) continue;
    for (const s of r.sel.split(',')) {
      const sel = s.trim();
      if (!sel || sel.startsWith('@')) continue;
      const bgs = fondoDe(sel);
      let mejor = null;
      for (const b of bgs || [BLANCO]) {
        const rr = ratio(sobre(fg0, b), b);
        if (!mejor || rr < mejor.r) mejor = { r: rr, bg: b };
      }
      const size = px(sel, r.decls);
      const peso = parseInt(r.decls['font-weight']) || 400;
      const grande = size !== null && (size >= 24 || (size >= 18.66 && peso >= 700));
      const exige = grande ? 3 : 4.5;
      // Cuando el fondo NO se pudo resolver y el color del texto es CLARO, lo
      // que falla es la herramienta, no el diseño: nadie escribe texto blanco
      // esperando que caiga sobre blanco — ese texto vive sobre algo oscuro
      // que el script no ve (fondo declarado en una clase hermana, puesto
      // desde el .ts, o una imagen). Contarlo como fallo es ruido, y un
      // verificador ruidoso se termina ignorando entero. Va aparte.
      // Solo el texto CASI BLANCO se da por indeterminado. Un gris claro sobre
      // fondo desconocido es casi siempre un fallo real —los grises se usan de
      // texto atenuado sobre superficies claras—, y con el umbral flojo (0.4)
      // el script se tragaba justo ese caso: se probó metiendo un #D1D5DB a
      // mano y salió en verde.
      const cegado = !bgs && lum(sobre(fg0, BLANCO)) > 0.85;
      if (cegado) cegados++;
      if (mejor.r < exige && !cegado) {
        fallos.push({
          sel, exige, ratio: +mejor.r.toFixed(2), size,
          color: r.decls.color.trim(),
          fondo: '#' + mejor.bg.map((c) => c.toString(16).padStart(2, '0')).join(''),
          heredado: !bgs,
        });
      }
    }
  }
  fallos.cegados = cegados;
  return fallos;
}

// ── Recolección de hojas: .scss sueltos + `styles:` dentro de los .ts ───────
function hojas() {
  const out = [];
  (function rec(dir) {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name);
      if (e.isDirectory()) { rec(p); continue; }
      if (e.name.endsWith('.component.scss')) {
        out.push({ id: path.relative(RAIZ, p), scss: fs.readFileSync(p, 'utf8'), dir: path.dirname(p) });
      } else if (e.name.endsWith('.ts')) {
        const src = fs.readFileSync(p, 'utf8');
        // styles: [`…`]  ·  styles: `…`   — el backtick es el delimitador real
        const m = src.match(/styles:\s*\[?\s*`([\s\S]*?)`\s*\]?\s*,?\s*\n\s*\}\)/);
        if (m && m[1].trim()) {
          out.push({ id: path.relative(RAIZ, p), scss: m[1], dir: path.dirname(p), inline: true });
        }
      }
    }
  })(path.join(RAIZ, 'src/app'));
  return out;
}

// ── Ejecución ───────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
const clave = (id, f) => `${id}::${f.sel}::${f.color}`;

const encontrados = new Map();
let sinCompilar = 0;
let ciegos = 0;
for (const h of hojas()) {
  let css;
  try { css = compilar(h.scss, h.dir); } catch { sinCompilar++; continue; }
  const hallados = analizar(css);
  ciegos += hallados.cegados;
  for (const f of hallados) encontrados.set(clave(h.id, f), { id: h.id, ...f });
}

if (args.includes('--sellar')) {
  const base = {};
  for (const [k, v] of encontrados) base[k] = { ratio: v.ratio, exige: v.exige, motivo: 'PENDIENTE DE REVISAR — escribe aquí por qué se acepta, o arréglalo' };
  fs.writeFileSync(BASE, JSON.stringify(base, null, 2) + '\n');
  console.log(`Línea base sellada: ${Object.keys(base).length} parejas en ${path.relative(RAIZ, BASE)}`);
  console.log('Escribe el motivo de cada una. Las que no tengan motivo real, arréglalas.');
  process.exit(0);
}

const base = fs.existsSync(BASE) ? JSON.parse(fs.readFileSync(BASE, 'utf8')) : {};
const nuevos = [...encontrados.entries()].filter(([k]) => !(k in base));
const conocidos = [...encontrados.entries()].filter(([k]) => k in base);

console.log(`Hojas analizadas: ${hojas().length}${sinCompilar ? ` (${sinCompilar} no compilaron sueltas)` : ''}`);
if (ciegos) console.log(`Indeterminadas (texto claro sobre un fondo que el script no ve): ${ciegos} — no cuentan`);
console.log(`Parejas bajo el mínimo: ${encontrados.size}  ·  en línea base: ${conocidos.length}  ·  NUEVAS: ${nuevos.length}`);

function pinta([, f]) {
  const t = f.size ? `${f.size}px` : ' ? ';
  console.log(`  ${String(f.ratio).padStart(5)}:1  (exige ${f.exige})  ${t.padStart(6)}  ${f.color} sobre ${f.fondo}${f.heredado ? '  [fondo supuesto blanco]' : ''}`);
  console.log(`         ${f.id}`);
  console.log(`         ${f.sel.slice(0, 96)}`);
}

if (args.includes('--todo') && conocidos.length) {
  console.log('\n— en línea base (ya revisadas) —');
  conocidos.forEach(pinta);
}

if (nuevos.length) {
  console.error(`\n✗ ${nuevos.length} pareja(s) NUEVAS por debajo del contraste mínimo:\n`);
  nuevos.forEach(pinta);
  console.error('\n  Arréglalas, o —si el caso está exento (icono decorativo, control');
  console.error('  deshabilitado, fondo que el script no puede ver)— agrégalas a');
  console.error(`  ${path.relative(RAIZ, BASE)} CON EL MOTIVO ESCRITO.`);
  process.exit(1);
}

console.log('\n✓ Sin contrastes nuevos por debajo del mínimo.');
