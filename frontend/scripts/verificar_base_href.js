#!/usr/bin/env node
/**
 * Comprueba que el build tenga `<base href="/app/">`.
 *
 * Existe porque este error ya tumbó la aplicación DOS veces (2026-06-18 y
 * 2026-08-24) y las dos veces costó rato encontrarlo, por un motivo concreto:
 * **no se parece a una caída**. El contenedor sigue `Up (healthy)`, `/app/`
 * responde 200 y el build compila sin un solo error. Lo único que pasa es que
 * el `index.html` pide sus assets en la raíz del dominio en vez de bajo
 * `/app/`, así que el navegador recibe 404 en todo y pinta una página en
 * blanco.
 *
 * Agravante: `frontend/dist` está gitignored y el contenedor monta el árbol de
 * trabajo, así que quien compile mal deja a TODOS sin aplicación.
 *
 *     node scripts/verificar_base_href.js
 *
 * Corre solo al final de `npm run build`. Sale con código 1 si está mal.
 */
const fs = require('fs');
const path = require('path');

const INDEX = path.resolve(__dirname, '../dist/innovak-frontend/browser/index.html');
const ESPERADO = '/app/';

if (!fs.existsSync(INDEX)) {
  console.error(`✗ No existe ${path.relative(process.cwd(), INDEX)} — ¿corrió el build?`);
  process.exit(1);
}

const html = fs.readFileSync(INDEX, 'utf8');
const m = html.match(/<base[^>]*href="([^"]*)"/i);

if (!m) {
  console.error('✗ El index.html no tiene etiqueta <base>. La SPA no va a encontrar sus assets.');
  process.exit(1);
}

if (m[1] !== ESPERADO) {
  console.error(`✗ base href = "${m[1]}", debería ser "${ESPERADO}".`);
  console.error('');
  console.error('  Así compilado, el navegador pide /main.js y /chunk-*.js en la RAÍZ');
  console.error('  del dominio y recibe 404: la aplicación sale en blanco aunque el');
  console.error('  contenedor esté sano y /app/ responda 200.');
  console.error('');
  console.error('  Recompila con el comando correcto:');
  console.error('      npm run build');
  console.error('  (que ya lleva --base-href=/app/; `ng build` a secas NO lo lleva,');
  console.error('   y `--configuration production` tampoco lo implica).');
  process.exit(1);
}

console.log(`✓ base href = "${m[1]}"`);
