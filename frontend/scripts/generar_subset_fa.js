#!/usr/bin/env node
/**
 * Genera `src/styles/fa-subset.css`: solo los iconos que el proyecto usa.
 *
 * Font Awesome Free trae 2.171 nombres de icono; innovaK usa 200. El CSS
 * completo son 18 KB gzip solo en el mapa de nombres, y la red de la Alcaldía
 * no es rápida ni siempre está.
 *
 *     node scripts/generar_subset_fa.js
 *
 * El archivo generado NO se edita a mano: se regenera. Y `verificar_iconos_fa.js`
 * comprueba que todo icono usado esté en el subset, así que si alguien agrega
 * un `fa-` nuevo y olvida regenerar, el verificador lo dice — que es
 * exactamente lo que no pasaba antes, cuando un icono inexistente solo dejaba
 * un hueco mudo en la pantalla.
 *
 * OJO: esto NO recorta la FUENTE (fa-solid-900.woff2, 117 KB), que lleva los
 * 2.171 glifos. Recortarla necesita `pyftsubset` de fonttools y bajaría a unos
 * 15 KB. Ver docs/propuestas/font_awesome_selfhost.md.
 */
const fs = require('fs');
const path = require('path');

const RAIZ = path.resolve(__dirname, '../..');
const FA = path.resolve(__dirname, '../node_modules/@fortawesome/fontawesome-free/css');
const SALIDA = path.resolve(__dirname, '../src/styles/fa-subset.css');

const { iconosUsados, MODIFICADORES } = require('./_iconos_usados');

const usados = iconosUsados(RAIZ);

// Reglas de icono de FA7:  .fa-arrow-left { --fa: "\f060"; }
//                          .fa.fa-refresh { --fa: "\f021"; }   (v4-shims)
const REGLA = /(\.fa\.fa-[a-z0-9-]+|\.fa-[a-z0-9-]+)\s*\{\s*--fa:\s*"([^"]+)";?\s*\}/g;

function reglasDe(archivo) {
  const txt = fs.readFileSync(path.join(FA, archivo), 'utf8');
  const out = new Map();
  for (const m of txt.matchAll(REGLA)) {
    const nombre = m[1].replace(/^\.fa\./, '').replace(/^\./, '');
    if (!out.has(nombre)) out.set(nombre, m[0]);
  }
  return out;
}

const deBase = reglasDe('fontawesome.css');
const deShims = reglasDe('v4-shims.css');

const conservadas = [];
const faltantes = [];
for (const icono of [...usados.keys()].sort()) {
  if (MODIFICADORES.has(icono)) continue;
  const regla = deBase.get(icono) || deShims.get(icono);
  if (regla) conservadas.push(regla);
  else faltantes.push(icono);
}

if (faltantes.length) {
  console.error('✗ Estos iconos no existen en Font Awesome Free y no se pueden');
  console.error('  incluir en el subset:\n');
  for (const i of faltantes) console.error(`    ${i}`);
  process.exit(1);
}

// La BASE de fontawesome.css —la regla `.fa`, el `::before` que pinta el
// glifo, los tamaños, `fa-fw`, las animaciones— hay que conservarla entera:
// sin ella los 200 `--fa` no pintan nada. Lo que se quita son las 2.307
// reglas de nombre de icono, que es donde está el peso.
const base = fs.readFileSync(path.join(FA, 'fontawesome.css'), 'utf8')
  .replace(REGLA, '')
  .replace(/\n{3,}/g, '\n\n');

const version = require(
  path.resolve(__dirname, '../node_modules/@fortawesome/fontawesome-free/package.json')
).version;

const cabecera = `/* ─────────────────────────────────────────────────────────────
 * GENERADO — no editar a mano.
 *   node scripts/generar_subset_fa.js
 *
 * Subset de Font Awesome Free ${version}: ${conservadas.length} iconos de los
 * ${deBase.size + deShims.size} que trae el paquete. Incluye la base de
 * fontawesome.css (la regla .fa, el ::before, tamaños y animaciones) sin las
 * 2.307 reglas de nombre, que es donde estaba el peso.
 *
 * Iconos: CC BY 4.0 · Fuentes: SIL OFL 1.1 · Código: MIT
 * Font Awesome Free — https://fontawesome.com
 * ───────────────────────────────────────────────────────────── */

${base}

/* ── Los ${conservadas.length} iconos que este proyecto usa ── */

`;

fs.mkdirSync(path.dirname(SALIDA), { recursive: true });
fs.writeFileSync(SALIDA, cabecera + conservadas.join('\n') + '\n', 'utf8');

console.log(`✓ ${conservadas.length} iconos escritos en ${path.relative(RAIZ, SALIDA)}`);
console.log(`  (el paquete trae ${deBase.size + deShims.size})`);
