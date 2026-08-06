#!/usr/bin/env node
/**
 * Genera `docs/propuestas/fa_a_lucide.csv` para DIMENSIONAR la migración de
 * Font Awesome a lucide. No migra nada.
 *
 *     node scripts/mapeo_fa_lucide.js
 *
 * El emparejamiento es por nombre normalizado y es una PISTA, no una decisión:
 * `fa-users` y lucide `users` casi seguro son lo mismo, pero `fa-bullseye` →
 * `target` hay que mirarlo. Por eso el CSV trae una columna `confianza` y otra
 * `revisar`, y los que no casan salen vacíos para que alguien los complete.
 *
 * Lo que sí es exacto es el CONTEO y el número de archivos: eso es lo que
 * permite decir cuánto cuesta la migración sin abrir 80 archivos.
 */
const fs = require('fs');
const path = require('path');

const RAIZ = path.resolve(__dirname, '../..');
const SALIDA = path.join(RAIZ, 'docs/propuestas/fa_a_lucide.csv');
const { iconosUsados } = require('./_iconos_usados');

// ── Los nombres que lucide expone ────────────────────────────────────────
//
// lucide-angular no publica una lista: publica un `.d.ts` por icono en
// `icons/`, con el nombre en kebab-case (`arrow-left.d.ts`). El directorio ES
// el catálogo.
function nombresLucide() {
  const dir = path.resolve(__dirname, '../node_modules/lucide-angular/icons');
  if (!fs.existsSync(dir)) return new Set();
  return new Set(
    fs.readdirSync(dir)
      .filter((f) => f.endsWith('.d.ts'))
      .map((f) => f.replace(/\.d\.ts$/, ''))
  );
}

/** `arrow-left` → `ArrowLeft`, que es como se importa en el componente. */
const aPascal = (kebab) =>
  kebab.split('-').map((p) => p.charAt(0).toUpperCase() + p.slice(1)).join('');

/** `fa-arrow-left` → `arrowleft`; lucide `ArrowLeft` → `arrowleft`. */
const norm = (s) => s.replace(/^fa-/, '').replace(/[^a-z0-9]/gi, '').toLowerCase();

// Sinónimos que el nombre no revela. Solo los evidentes; el resto va a mano.
const SINONIMOS = {
  'fa-times': 'X', 'fa-xmark': 'X', 'fa-remove': 'X', 'fa-close': 'X',
  'fa-check': 'Check', 'fa-spinner': 'LoaderCircle', 'fa-refresh': 'RefreshCw',
  'fa-trash': 'Trash2', 'fa-pencil': 'Pencil', 'fa-edit': 'Pencil',
  'fa-search': 'Search', 'fa-magnifying-glass': 'Search',
  'fa-bullseye': 'Target', 'fa-chart-line': 'TrendingUp',
  'fa-chart-pie': 'ChartPie', 'fa-chart-column': 'ChartColumn',
  'fa-exclamation-triangle': 'TriangleAlert', 'fa-triangle-exclamation': 'TriangleAlert',
  'fa-info-circle': 'Info', 'fa-circle-info': 'Info',
  'fa-exclamation-circle': 'CircleAlert', 'fa-check-circle': 'CircleCheck',
  'fa-plus-circle': 'CirclePlus', 'fa-futbol': 'Volleyball',
  'fa-graduation-cap': 'GraduationCap', 'fa-shield-halved': 'Shield',
  'fa-vote-yea': 'Vote', 'fa-box-open': 'PackageOpen',
  'fa-chalkboard-user': 'Presentation', 'fa-file-contract': 'FileText',
};

const lucide = nombresLucide();
const usados = iconosUsados(RAIZ);

const filas = [];
let exactos = 0, sinonimos = 0, sinMapeo = 0;

for (const [icono, archivos] of [...usados.entries()]
    .sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]))) {
  let destino = '', confianza = '', revisar = 'sí';

  const n = norm(icono);
  const exacto = [...lucide].find((l) => norm(l) === n);
  if (exacto) {
    // El nombre coincide carácter por carácter: es el caso barato.
    destino = aPascal(exacto); confianza = 'exacto'; revisar = 'no'; exactos++;
  } else if (SINONIMOS[icono]) {
    destino = SINONIMOS[icono]; confianza = 'sinonimo'; sinonimos++;
  } else {
    confianza = 'sin-candidato'; sinMapeo++;
  }
  filas.push([icono, archivos.length, destino, confianza, revisar,
              archivos.slice(0, 2).join(' | ')]);
}

const csv = ['clase_fa,archivos,lucide_propuesto,confianza,revisar_a_mano,ejemplos']
  .concat(filas.map((f) => f.map((c) =>
    String(c).includes(',') ? `"${c}"` : c).join(',')))
  .join('\n') + '\n';

fs.writeFileSync(SALIDA, csv, 'utf8');

console.log(`Iconos lucide detectados en el paquete: ${lucide.size}`);
console.log(`Iconos FA usados:                       ${usados.size}`);
console.log(`  · coincidencia exacta de nombre:      ${exactos}`);
console.log(`  · sinónimo conocido (revisar):        ${sinonimos}`);
console.log(`  · sin candidato (a mano):             ${sinMapeo}`);
console.log(`\nCSV: ${path.relative(RAIZ, SALIDA)}`);
