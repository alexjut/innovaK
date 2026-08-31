import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, Input, computed, signal,
} from '@angular/core';
import { formatMoneda, formatNumero } from '../../../shared/format/format.util';
import {
  CifraLedger, ChipCompletitud, CoberturaPdlSector,
  EstadoSemaforo, GrupoTarjeta, MuroSubgrupos, TarjetaSubgrupo,
} from './muro-subgrupos.types';

/**
 * Color de cada etapa, buscado POR NOMBRE normalizado. Ninguna usa el rojo
 * institucional: «sancionatorio» no se puede leer como «alcaldía».
 *
 * Es un mapa de presentación, no un catálogo: los nombres y el orden los manda
 * el servidor en `cabecera.etapas_catalogo`. Una etapa que no esté acá se pinta
 * con el neutro y se sigue viendo — antes, una etapa que el frontend no
 * conociera simplemente desaparecía de la tarjeta.
 */
const COLOR_ETAPA: Record<string, { fondo: string; texto: string }> = {
  'en elaboracion': { fondo: '#DBEAFE', texto: '#1E40AF' },
  formulacion:     { fondo: '#FEF3C7', texto: '#92400E' },
  ejecucion:       { fondo: '#DCFCE7', texto: '#166534' },
  liquidacion:     { fondo: '#CCFBF1', texto: '#0F766E' },
  sancionatorio:   { fondo: '#FEE2E2', texto: '#991B1B' },
};
const COLOR_NEUTRO = { fondo: '#F1F5F9', texto: '#334155' };

/** Sin tildes y en minúscula, para que «Ejecución» encuentre su color. */
function _clave(nombre: string): string {
  return (nombre || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
}

/** Etiqueta escrita de cada estado. El color NUNCA va solo (WCAG 1.4.1). */
export const SEMAFORO_TEXTO: Record<EstadoSemaforo, string> = {
  al_dia: 'Al día',
  atrasado: 'Atrasado',
  critico: 'Crítico',
  incompleto: 'Sin datos para calificar',
};

const GRUPO_ORDEN: GrupoTarjeta[] = ['con_inversion', 'con_proyecto_sin_contrato', 'sin_nada'];

// ══ Helpers exportables ═══════════════════════════════════════════════
// Viven a nivel de módulo, no como métodos, porque el explorador
// maestro/detalle del dashboard los necesita para pintar el resumen
// superior compacto. Antes eran métodos privados del muro y el shell
// habría tenido que duplicarlos: tres formateadores de plata en la
// misma página es exactamente lo que no se quiere.

/**
 * Fecha legible es-CO sin depender de `registerLocaleData`: el SPA no
 * registra el locale, así que un DatePipe con 'es-CO' reventaría en runtime.
 */
export function fechaLegible(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleString('es-CO', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

/** Acepta número plano u objeto anotado; devuelve siempre el objeto. */
export function cifraLedger(v: CifraLedger | number | null | undefined): CifraLedger {
  if (v == null) return { valor: null };
  if (typeof v === 'number') return { valor: v };
  return v;
}

/** Pesos a millones legibles: 33047464796 → «$33.047 M». */
export function enMillones(n: number | null | undefined): string {
  if (n == null) return '—';
  if (n === 0) return '$0';
  const mm = n / 1e6;
  return '$' + mm.toLocaleString('es-CO', { maximumFractionDigits: mm >= 100 ? 0 : 1 }) + ' M';
}

/** Cobertura de una cifra del ledger, en una línea. */
export function coberturaLedgerTexto(c: CifraLedger): string | null {
  const cob = c.cobertura;
  if (!cob || cob.con == null || cob.de == null) return null;
  return `${cob.con} de ${cob.de} contratos`;
}

/**
 * MURO DE SUBGRUPOS — Fase 1 del panel de área.
 *
 * Se monta DENTRO de /app/presupuesto/dashboard, encima del dashboard
 * clásico, que no se toca. Tres piezas en este orden: franja de corte,
 * ledger de cuatro cifras y muro de tarjetas.
 *
 * Reglas de pintura que este componente NO negocia:
 *  - El gris de «sin dato» SIEMPRE va con la palabra escrita al lado. El
 *    color nunca es el único portador del significado (WCAG 1.4.1): el
 *    semáforo lleva punto + texto.
 *  - Las 37 tarjetas sin nada van en GRIS, jamás en rojo: nadie cargó, no es
 *    que hayan incumplido.
 *  - Ninguna tarjeta sale con la lista de pendientes vacía; si el backend no
 *    manda ninguno se dice explícitamente que no se declararon.
 *  - `avance === null` se pinta «sin avance cargado», nunca 0%.
 */
@Component({
  standalone: true,
  selector: 'app-muro-subgrupos',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule],
  templateUrl: './muro-subgrupos.component.html',
  styleUrl: './muro-subgrupos.component.scss',
})
export class MuroSubgruposComponent {
  /** Payload del muro. `null` = todavía cargando o el endpoint falló. */
  @Input({ required: true }) set datos(v: MuroSubgrupos | null) { this._datos.set(v); }
  /** Mensaje de error del contenedor (el muro no hace su propio fetch). */
  @Input() error: string | null = null;

  /**
   * Modo compacto: oculta la franja de corte y el ledger de cuatro cifras.
   *
   * No se borraron: se MOVIERON al resumen superior del explorador
   * maestro/detalle, que es quien manda hoy en /app/presupuesto/dashboard.
   * Pintarlos dos veces en la misma página sería decir el mismo número
   * dos veces y dejar al lector preguntándose cuál es el bueno.
   */
  @Input() compacto = false;

  // ── Filtros: el CONTROL vive afuera, el MECANISMO sigue acá ──────────
  // Los selects de área/subgrupo y el buscador se movieron al panel
  // izquierdo del explorador (ahora filtran PROYECTOS). El muro conserva
  // `pasaFiltro`, que es el mecanismo, y recibe el estado por Input para
  // que al filtrar «Cultura» arriba el pliegue de abajo no siga mostrando
  // los 45 subgrupos como si nada hubiera pasado.
  @Input() set filtroArea(v: string) { this.areaSel.set(v || ''); }
  @Input() set filtroSubgrupoId(v: number | null) { this.subgrupoSel.set(v ?? null); }
  @Input() set filtroBusqueda(v: string) { this.busqueda.set(v || ''); }

  private _datos = signal<MuroSubgrupos | null>(null);

  formatNumero = formatNumero;
  formatMoneda = formatMoneda;

  /** La tira de «sin nada» arranca plegada: son 37 de 45. */
  tiraAbierta = signal(false);
  coberturaAbierta = signal(false);

  muro = computed(() => this._datos());

  // ── Cabecera ────────────────────────────────────────────────────────────
  /** El backend puede mandar `chips` como diccionario o como lista. */
  chips = computed<Array<ChipCompletitud & { clave: string }>>(() => {
    const c = this._datos()?.cabecera?.chips;
    if (!c) return [];
    const lista = Array.isArray(c)
      ? c.map((x, i) => ({ ...x, clave: x.clave ?? String(i) }))
      : Object.entries(c).map(([clave, x]) => ({ ...(x as ChipCompletitud), clave }));
    return lista;
  });

  pctTiempo = computed(() => this._datos()?.cabecera?.ventana_pdl?.pct_tiempo_transcurrido ?? null);

  /**
   * Fecha legible es-CO sin depender de `registerLocaleData`: el SPA no
   * registra el locale, así que un DatePipe con 'es-CO' reventaría en runtime.
   */
  fecha = fechaLegible;

  etiquetaChip(c: ChipCompletitud & { clave: string }): string {
    if (c.etiqueta) return c.etiqueta;
    return ({
      etapa: 'Etapa del contrato',
      forma_pago: 'Forma de pago',
      vinculo_proyecto: 'Contrato con proyecto',
    } as Record<string, string>)[c.clave] ?? c.clave.replace(/_/g, ' ');
  }

  /** Traduce la causa a algo que un funcionario pueda accionar. */
  textoCausa(causa?: string): string {
    return ({
      columna_inexistente: 'no hay dónde guardarlo todavía',
      tabla_vacia: 'la tabla existe pero está vacía',
      dato_faltante: 'hay dónde guardarlo, faltan valores',
    } as Record<string, string>)[causa ?? ''] ?? (causa ?? 'sin causa declarada');
  }

  // ── Ledger ──────────────────────────────────────────────────────────────
  /** Acepta número plano u objeto anotado; devuelve siempre el objeto. */
  cifra = cifraLedger;

  ledgerProgramado = computed(() => this.cifra(this._datos()?.ledger?.programado));
  ledgerComprometido = computed(() => this.cifra(this._datos()?.ledger?.comprometido));
  ledgerGirado = computed(() => this.cifra(this._datos()?.ledger?.girado));
  ledgerSaldo = computed(() => this.cifra(this._datos()?.ledger?.saldo));

  enMillones = enMillones;
  coberturaTexto = coberturaLedgerTexto;

  // ── Estado del filtro (lo escribe el panel izquierdo por @Input) ──────
  //
  // Estos tres signals y `pasaFiltro` son los MISMOS que vivían acá con sus
  // selects propios. Lo que se movió al explorador son los controles
  // (`areas()`, `subgruposDelArea()`, `cambiarArea()`, `cambiarSubgrupo()`,
  // `limpiarFiltros()`) porque allá filtran PROYECTOS, que es la unidad que
  // manda ahora. Al cambiar de área el subgrupo se limpia igual que antes:
  // el handler es el mismo, sólo cambió de casa.
  areaSel = signal<string>('');
  subgrupoSel = signal<number | null>(null);
  busqueda = signal<string>('');

  /** Quita tildes para que «Educación» se encuentre escribiendo «educacion». */
  private plano(t: string): string {
    return (t || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  }

  private pasaFiltro(t: TarjetaSubgrupo): boolean {
    if (this.areaSel() && t.area !== this.areaSel()) return false;
    if (this.subgrupoSel() != null && t.id !== this.subgrupoSel()) return false;
    const q = this.plano(this.busqueda().trim());
    if (q && !this.plano(t.nombre).includes(q)
          && !this.plano(t.area || '').includes(q)
          && !this.plano(t.dependencia || '').includes(q)) return false;
    return true;
  }

  /** Cuántas tarjetas quedan tras filtrar — el contador de la plantilla. */
  visibles = computed(() =>
    (this._datos()?.tarjetas ?? []).filter(t => this.pasaFiltro(t)).length);
  totalTarjetas = computed(() => (this._datos()?.tarjetas ?? []).length);

  // ── Tarjetas ────────────────────────────────────────────────────────────
  private porGrupo(g: GrupoTarjeta): TarjetaSubgrupo[] {
    return (this._datos()?.tarjetas ?? [])
      .filter(t => t.grupo === g)
      .filter(t => this.pasaFiltro(t));
  }
  conInversion = computed(() => this.porGrupo('con_inversion'));
  conProyecto = computed(() => this.porGrupo('con_proyecto_sin_contrato'));
  sinNada = computed(() => this.porGrupo('sin_nada'));

  /** Las tarjetas cuyo `grupo` no reconocemos no se pierden: van al final. */
  otras = computed(() =>
    (this._datos()?.tarjetas ?? [])
      .filter(t => !GRUPO_ORDEN.includes(t.grupo))
      .filter(t => this.pasaFiltro(t)));

  textoSemaforo(s: EstadoSemaforo): string { return SEMAFORO_TEXTO[s] ?? s; }

  /** Etapas con conteo > 0, nombradas y ordenadas por el catálogo del servidor. */
  etapasVisibles(t: TarjetaSubgrupo): Array<{ etiqueta: string; n: number; fondo: string; texto: string }> {
    const e = t.etapas;
    if (!e) return [];
    const catalogo = this.muro()?.cabecera?.etapas_catalogo ?? [];
    return catalogo
      .slice()
      .sort((a, b) => a.orden - b.orden)
      .map(x => ({ etapa: x, n: e[String(x.codigo)] ?? 0 }))
      .filter(x => x.n > 0)
      .map(x => ({
        etiqueta: x.etapa.nombre,
        n: x.n,
        ...(COLOR_ETAPA[_clave(x.etapa.nombre)] ?? COLOR_NEUTRO),
      }));
  }
  sinDato(t: TarjetaSubgrupo): number { return t.etapas?.sin_dato ?? 0; }

  /** Nombres de los proyectos faltantes de un sector, en una línea. */
  faltantesTexto(s: CoberturaPdlSector): string {
    const f = s.faltantes;
    if (!f || !f.length) return '';
    return f.map(x => (typeof x === 'string' ? x : [x.codigo, x.nombre].filter(Boolean).join(' ')))
      .join(' · ');
  }

  alternarTira(): void { this.tiraAbierta.update(v => !v); }
  alternarCobertura(): void { this.coberturaAbierta.update(v => !v); }
}
