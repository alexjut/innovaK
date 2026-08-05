import { CAPAS_MAPA, capaPorClave, defaultsCapas } from './capas.registry';

/**
 * Contrato del registro de capas (C2 — PR-0). Espeja
 * `apps/georeferenciacion/tests/test_capas.py`: el registro del backend tiene un
 * test que exige el mínimo de cada entrada; éste hace lo mismo en el frontend.
 *
 * El test clave es el de `publica`: es el guardián de B1. Si un endpoint del
 * mapa cambia de permiso en el backend, este test obliga a reflejarlo aquí (o
 * al revés), en vez de que la divergencia se descubra por un 401 en producción.
 */
describe('Registro de capas del mapa (CAPAS_MAPA)', () => {
  it('cada descriptor declara el mínimo', () => {
    for (const c of CAPAS_MAPA) {
      expect(c.clave).withContext('clave').toBeTruthy();
      expect(c.label).withContext(`label de ${c.clave}`).toBeTruthy();
      expect(['poligono', 'punto', 'linea']).withContext(`render de ${c.clave}`).toContain(c.render);
      expect(typeof c.lazy).toBe('boolean');
      expect(typeof c.publica).toBe('boolean');
      expect(typeof c.checkbox).toBe('boolean');
      expect(typeof c.defaultOn).toBe('boolean');
    }
  });

  it('las claves son únicas', () => {
    const claves = CAPAS_MAPA.map(c => c.clave);
    expect(new Set(claves).size).toBe(claves.length);
  });

  it('publica espeja el backend: solo el Banco requiere login', () => {
    for (const c of CAPAS_MAPA) {
      expect(c.publica).withContext(`publica de ${c.clave}`).toBe(c.clave !== 'banco');
    }
  });

  it('toda capa con checkbox tiene swatch', () => {
    for (const c of CAPAS_MAPA.filter(x => x.checkbox)) {
      expect(c.swatch).withContext(`swatch de ${c.clave}`).toBeTruthy();
    }
  });

  it('las capas sin checkbox son las escuelas (las gobierna el subgrupo)', () => {
    const sinCheckbox = CAPAS_MAPA.filter(c => !c.checkbox).map(c => c.clave).sort();
    expect(sinCheckbox).toEqual(['escuelasCultura', 'escuelasDeporte']);
  });

  it('solo la localidad arranca encendida (paridad con el objeto capas actual)', () => {
    const on = CAPAS_MAPA.filter(c => c.defaultOn).map(c => c.clave);
    expect(on).toEqual(['localidad']);
  });

  it('capaPorClave resuelve y devuelve undefined para lo que no existe', () => {
    expect(capaPorClave('banco')?.render).toBe('punto');
    expect(capaPorClave('inexistente')).toBeUndefined();
  });

  it('defaultsCapas cubre las 13 claves', () => {
    const d = defaultsCapas();
    expect(Object.keys(d).length).toBe(13);
    expect(d['localidad']).toBe(true);
    expect(d['parques']).toBe(false);
  });
});
