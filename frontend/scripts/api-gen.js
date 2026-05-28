#!/usr/bin/env node
/**
 * api-gen — Generador del cliente Angular desde el schema OpenAPI.
 *
 * Requiere Java 11+ o Docker (openapi-generator-cli es un wrapper sobre el JAR).
 *
 * Uso:
 *   npm run api:gen                            # default localhost:8034
 *   INNOVAK_API_SCHEMA=http://prod/api/schema/ npm run api:gen
 *
 * Resultado: sobrescribe `src/app/api/` con services TS tipados +
 * interfaces de cada response. Los archivos generados NO se editan a
 * mano. Si falta un campo, se agrega en el backend y se regenera.
 */

const { execSync } = require('node:child_process');
const { writeFileSync, existsSync, mkdirSync } = require('node:fs');
const { join } = require('node:path');

const SCHEMA_URL = process.env.INNOVAK_API_SCHEMA || 'http://localhost:8034/api/schema/';
const OUT_DIR = 'src/app/api';

function fail(msg) {
  console.error(`\n❌ api-gen: ${msg}\n`);
  process.exit(1);
}

function info(msg) {
  console.log(`▸ ${msg}`);
}

function hasJava() {
  try {
    execSync('java -version', { stdio: 'pipe' });
    return true;
  } catch {
    return false;
  }
}

function hasDocker() {
  try {
    execSync('docker --version', { stdio: 'pipe' });
    return true;
  } catch {
    return false;
  }
}

(async function main() {
  info(`Descargando schema desde: ${SCHEMA_URL}`);

  let schema;
  try {
    const res = await fetch(SCHEMA_URL);
    if (!res.ok) fail(`HTTP ${res.status} al descargar el schema`);
    schema = await res.text();
  } catch (e) {
    fail(`No se pudo descargar el schema: ${e.message}`);
  }

  if (!existsSync('tmp')) mkdirSync('tmp');
  const schemaPath = join('tmp', 'openapi.yml');
  writeFileSync(schemaPath, schema);
  info(`Schema guardado en ${schemaPath} (${schema.length} bytes).`);

  const args = [
    'generate',
    '-i', schemaPath,
    '-g', 'typescript-angular',
    '-o', OUT_DIR,
    '--additional-properties=ngVersion=18.0.0,providedInRoot=true,fileNaming=kebab-case,supportsES6=true,withInterfaces=true',
  ];

  if (hasJava()) {
    info('Java detectado — usando openapi-generator-cli (npx).');
    try {
      execSync(`npx --yes @openapitools/openapi-generator-cli@2.13.0 ${args.join(' ')}`, {
        stdio: 'inherit',
      });
    } catch (e) {
      fail(`Generación falló: ${e.message}`);
    }
  } else if (hasDocker()) {
    info('Java NO detectado pero Docker sí — usando imagen oficial.');
    try {
      execSync(
        `docker run --rm -v "${process.cwd()}:/local" openapitools/openapi-generator-cli:v7.14.0 ` +
          args.map((a) => a.replace(/\/local\//g, 'src/app/api/')).join(' '),
        { stdio: 'inherit' },
      );
    } catch (e) {
      fail(`Generación falló: ${e.message}`);
    }
  } else {
    fail(
      'Ni Java ni Docker disponibles.\n' +
        '  Instala uno de los dos para regenerar el cliente:\n' +
        '    sudo apt install default-jre\n' +
        '  o:\n' +
        '    sudo apt install docker.io\n\n' +
        '  Mientras tanto, ver `src/app/api/README.md` para el modo manual.',
    );
  }

  info(`✅ Cliente generado en ${OUT_DIR}/`);
})();
