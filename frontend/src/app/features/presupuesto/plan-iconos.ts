/**
 * Del icono `fa-*` al nombre de Lucide, por palabra clave.
 *
 * Vivía como método del hub. Se sacó acá cuando el Plan pasó a tener tres
 * pantallas que pintan tarjetas —el hub, Visual y Gestión—: con una copia por
 * componente, agregar un icono obliga a acordarse de tres sitios y el que se
 * olvide cae al icono por defecto sin que nadie lo note.
 *
 * El mapeo es por palabra clave y no por tabla exacta a propósito: los
 * `fa-*` los escribe quien agrega una página, y una tabla exigiría mantener
 * una entrada por cada uno.
 */
export function lucideDe(fa: string | null | undefined): string {
  const s = fa || '';
  if (/diagram|project|proyecto|kanban|folder/i.test(s)) return 'folder-kanban';
  if (/gauge|seguim|kpi|indicad|trend/i.test(s)) return 'gauge';
  if (/invoice|receipt|contrato|factura/i.test(s)) return 'receipt';
  if (/dollar|cdp|coin|money|dinero/i.test(s)) return 'coins';
  if (/wallet/i.test(s)) return 'wallet';
  if (/target|meta|bullseye/i.test(s)) return 'target';
  if (/sitemap|plan|estructura|arbol/i.test(s)) return 'folder-kanban';
  if (/scale|balance|compar/i.test(s)) return 'target';
  if (/layer|sector/i.test(s)) return 'trending-up';
  if (/chart|line|analiz|dashboard/i.test(s)) return 'trending-up';
  if (/file|document/i.test(s)) return 'file-text';
  if (/tag|concepto/i.test(s)) return 'tags';
  if (/list/i.test(s)) return 'list';
  if (/plus|nuev|crear|add/i.test(s)) return 'plus';
  if (/cog|gear|ajuste|settings/i.test(s)) return 'settings';
  if (/eye|ver|visual/i.test(s)) return 'gauge';
  return 'wallet';
}
