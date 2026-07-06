import { ACCIONES, KEYWORDS, MENU_CHIPS } from './flujos.data';
import { Widgets } from './kenny-chat.types';

/**
 * Test de humo de los flujos de KENNY definidos como DATA. Verifica la
 * integridad del grafo de acciones sin necesitar TestBed: que toda acción
 * referenciada (chips/cards/keywords) exista en ACCIONES o sea un paso
 * dinámico válido que el motor maneja por prefijo.
 */
describe('KENNY flujos.data', () => {
  const esDinamica = (a: string) =>
    /^(pqrs:|cita:dep:|cita:date:|cita:time:)/.test(a);
  const existe = (a: string) => esDinamica(a) || a in ACCIONES;

  const widgetsDe = (r: (typeof ACCIONES)[string]): Widgets | undefined =>
    typeof r.widgets === 'function' ? undefined : r.widgets;

  it('el menú principal (interno/externo/IA) es válido', () => {
    expect(MENU_CHIPS.length).toBe(3);
    MENU_CHIPS.forEach((c) => expect(existe(c.action)).withContext(c.action).toBe(true));
  });

  it('toda acción de chips/cards resuelve a una acción existente o dinámica', () => {
    Object.values(ACCIONES).forEach((r) => {
      const w = widgetsDe(r);
      w?.chips?.forEach((c) => expect(existe(c.action)).withContext(c.action).toBe(true));
      w?.cards?.forEach((c) => expect(existe(c.action)).withContext(c.action).toBe(true));
    });
  });

  it('los KEYWORDS del texto libre mapean a acciones existentes', () => {
    KEYWORDS.forEach((k) => expect(existe(k.action)).withContext(k.action).toBe(true));
  });

  it('las navegaciones apuntan a rutas internas del SPA', () => {
    Object.values(ACCIONES).forEach((r) => {
      if (r.navegar) expect(r.navegar.startsWith('/')).withContext(r.navegar).toBe(true);
    });
  });

  it('cada acción tiene texto y expresión de marca', () => {
    Object.entries(ACCIONES).forEach(([id, r]) => {
      expect(r.texto).withContext(id).toBeTruthy();
      expect(['alegre', 'atento', 'orgulloso']).withContext(id).toContain(r.expr);
    });
  });
});
