#!/usr/bin/env node
/**
 * Verifica que cada icono `fa-*` que usa el proyecto exista de verdad en el
 * Font Awesome Free que tenemos instalado.
 *
 * Existe porque el modo de falla de los iconos es SILENCIOSO: un `fa-` que no
 * existe no lanza error, no rompe el build y no aparece en ningún log — solo
 * deja un hueco en la pantalla. Así estuvieron los 620 iconos del proyecto
 * hasta el 2026-08-06, cuando resultó que Font Awesome ni siquiera estaba
 * instalado.
 *
 *     node scripts/verificar_iconos_fa.js
 *
 * Sale con código 1 si algún icono usado no existe. Pensado para correr en CI
 * o antes de un despliegue.
 */
const fs = require('fs');
const path = require('path');

const RAIZ = path.resolve(__dirname, '../..');
const FA = path.resolve(__dirname, '../node_modules/@fortawesome/fontawesome-free/css');
// El barrido es el MISMO que usa el generador del subset. Tenerlo por
// duplicado ya falló una vez: el verificador miraba el `fa-subset.css`
// generado y contaba sus propias custom properties como iconos rotos.
const { iconosUsados } = require('./_iconos_usados');

function leerCss(...archivos) {
  return archivos.map((f) => {
    const p = path.join(FA, f);
    if (!fs.existsSync(p)) {
      console.error(`✗ No existe ${p}. ¿Falta npm install?`);
      process.exit(1);
    }
    return fs.readFileSync(p, 'utf8');
  }).join('\n');
}

// Los nombres que el CSS instalado sabe resolver a un glifo.
//
// Font Awesome 7 no usa `.fa-x::before { content: … }` como las versiones
// viejas, sino una custom property:
//
//     .fa-arrow-left { --fa: "\f060"; }
//     .fa.fa-refresh { --fa: "\f021"; }      ← en v4-shims, con el `.fa` delante
//
// Por eso el selector se busca por el bloque que define `--fa`, y no por el
// pseudo-elemento.
// Se valida contra el SUBSET que realmente se despacha, no contra el paquete
// completo: si se comprobara contra el paquete, un icono nuevo pasaría la
// verificación y aun así no pintaría, porque no está en el subset. El
// verificador tiene que mirar lo mismo que ve el navegador.
const SUBSET = path.resolve(__dirname, '../src/styles/fa-subset.css');
if (!fs.existsSync(SUBSET)) {
  console.error('✗ Falta src/styles/fa-subset.css. Corre:');
  console.error('    node scripts/generar_subset_fa.js');
  process.exit(1);
}
const css = fs.readFileSync(SUBSET, 'utf8')
  + leerCss('solid.css', 'regular.css');
const disponibles = new Set();
for (const m of css.matchAll(/(\.fa-[a-z0-9-]+|\.fa\.fa-[a-z0-9-]+)\s*\{\s*--fa:/g)) {
  disponibles.add(m[1].replace(/^\.fa\./, '').replace(/^\./, ''));
}

const usados = iconosUsados(RAIZ);
const faltantes = [...usados.keys()].filter((i) => !disponibles.has(i)).sort();

console.log(`Iconos en el subset que se despacha:     ${disponibles.size}`);
console.log(`Iconos usados por el proyecto:            ${usados.size}`);
console.log(`Faltantes:                                ${faltantes.length}`);

if (faltantes.length) {
  console.error('\n✗ Estos iconos NO existen y van a dejar un hueco en pantalla:\n');
  for (const i of faltantes) {
    const donde = usados.get(i);
    console.error(`  ${i}`);
    for (const d of donde.slice(0, 3)) console.error(`      ${d}`);
    if (donde.length > 3) console.error(`      … y ${donde.length - 3} archivo(s) más`);
  }
  console.error('\nBusca el nombre correcto en https://fontawesome.com/search?o=r&m=free');
  process.exit(1);
}

console.log('\n✓ Todos los iconos usados existen en Font Awesome Free.');
