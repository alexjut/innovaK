import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import {
  AfterViewInit, Component, ElementRef,
  OnInit, ViewChild, computed, inject, signal,
} from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { Chart, registerables } from 'chart.js';
import { firstValueFrom, forkJoin, of, timer } from 'rxjs';
import { catchError, timeout } from 'rxjs/operators';
import { AuthService } from '../../core/auth/auth.service';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';
import { formatNumero, tipoEventoNombre } from '../../shared/format/format.util';
import { StatGridComponent, StatItem } from '../../shared/ui/stat-grid.component';
import { ObjetivosResumenComponent } from './objetivos/objetivos-resumen.component';
import { PerspectivasExploradorComponent } from './objetivos/perspectivas-explorador.component';
import { ObjetivoEstrategico, aplanarObjetivos } from './objetivos/objetivos.types';
import {
  MuroSubgruposComponent,
  cifraLedger, coberturaLedgerTexto, enMillones, fechaLegible,
} from './muro/muro-subgrupos.component';
import { MuroSubgrupos } from './muro/muro-subgrupos.types';

Chart.register(...registerables);

interface ResumenEjecutivo {
  proyectos: number; metas_pdd: number; indicadores: number;
  eventos_mes: number; avances: number; en_riesgo: number;
}
interface EventosMesTipo {
  por_mes: { mes: string; total: number }[];
  por_tipo: { tipo: string; total: number }[];
}
type TopSectores = Array<{
  sector: string; porcentaje: number; n_kpis: number; avance: number; meta: number;
}>;
interface MetasProgreso {
  stats: { total: number; cumplidas: number; en_progreso: number;
           en_riesgo: number; sin_avance: number };
  metas: Array<{
    codigo: string; nombre: string; sector?: string;
    porcentaje: number; meta_total?: number; avance_total?: number;
    estado: 'cumplida' | 'en_progreso' | 'en_riesgo' | 'sin_avance';
    fecha_fin?: string; num_indicadores?: number;
  }>;
}
// ── Cockpit ejecutivo (additivo) ──────────────────────────────
interface EjecucionFinanciera {
  contratado_total: number; n_contratos: number; n_con_valor: number;
  pct_ejecucion: number; cdp_asignado: number; cdp_n: number; cdp_con_valor: number;
  por_categoria: Array<{ categoria: string; n: number; valor: number; ejecucion: number | null }>;
  top_proyectos: Array<{ codigo: string; nombre: string; n: number; valor: number }>;
  vigencias: number[]; vigencia_activa: number | null;
}
interface BeneficiariosPerfil {
  beneficiarios: number; organizaciones: number;
  genero: Array<{ nombre: string; total: number }>; pct_mujeres: number;
  participantes: number; eventos_con_participacion: number;
  participantes_por_estado: Array<{ estado: string; total: number }>;
  caracterizaciones: number;
}

// `ObjetivoEstrategico` se importa de `./objetivos/objetivos.types` — es
// el mismo árbol que consumen `<app-objetivos-resumen>` y
// `<app-perspectivas-explorador>`, una sola definición para los tres en
// vez de repetirla acá.

/** Los cuatro acordeones del pie. Nacen cerrados, todos. */
type Clave = 'muro';

@Component({
  standalone: true,
  selector: 'app-presupuesto-dashboard',
  imports: [
    CommonModule, RouterLink, MuroSubgruposComponent,
    StatGridComponent,
    ObjetivosResumenComponent, PerspectivasExploradorComponent,
  ],
  template: `
    <div class="page">
      @let p = plata();
      @let g = gente();
      @let r = resumen();

      <header class="hero-compacto">
        <div class="hero-compacto__texto">
          <span class="rotulo">Alcaldía Local de Kennedy</span>
          <h1>Presupuesto e Inversión Local</h1>
          <p class="hero-compacto__sub">Control ejecutivo del Plan de Desarrollo Local</p>
        </div>
        <div class="hero-compacto__meta">
          @if (corteTexto() || corteMatrizTexto() || cortePdlTexto() || pctTiempo() != null) {
            <div class="datebox">
              @if (corteTexto(); as c) {
                <div class="datebox__row"><span>Corte SECOP</span><strong>{{ c }}</strong></div>
              }
              <!-- La Matriz primero: es de donde sale la Apropiación POAI, que
                   es la cifra que encabeza este tablero. -->
              @if (corteMatrizTexto(); as c) {
                <div class="datebox__row"><span>Matriz PDL · ALK</span><strong>{{ c }}</strong></div>
              }
              @if (cortePdlTexto(); as c) {
                <div class="datebox__row"><span>SDP · Datos Abiertos</span><strong>{{ c }}</strong></div>
              }
              @if (pctTiempo() != null) {
                <div class="datebox__row"><span>Tiempo del PDL</span><strong>{{ pctTiempo() }} %</strong></div>
              }
            </div>
          }
          @if (p && p.vigencias.length) {
            <div class="vigencia" role="group" aria-labelledby="vigencia-rot">
              <span class="vigencia__rotulo rotulo" id="vigencia-rot">Vigencia</span>
              <div class="vigencia__opciones">
                <button type="button" class="vchip" [class.vchip--on]="!vigencia()"
                        [attr.aria-pressed]="!vigencia()"
                        (click)="setVigencia(null)">Todas</button>
                <!-- Solo 2025/2026: p.vigencias trae años sueltos de
                     contratos legacy (2015, 2024…) que no son vigencias
                     del PDL actual. La lógica de setVigencia() no cambia. -->
                @for (v of vigenciasVisibles(p.vigencias); track v) {
                  <button type="button" class="vchip" [class.vchip--on]="vigencia() === v"
                          [attr.aria-pressed]="vigencia() === v"
                          (click)="setVigencia(v)">{{ v }}</button>
                }
              </div>
            </div>
          }
        </div>
      </header>

      @if (errorMsg()) {
        <div class="error-card">
          <i class="fa fa-triangle-exclamation" aria-hidden="true"></i>
          <strong>{{ errorMsg() }}</strong>
          <button class="ui-btn ui-btn--sm" (click)="recargar()">
            <i class="fa fa-rotate" aria-hidden="true"></i> Reintentar
          </button>
        </div>
      }

      <!-- ═══════════════════════════════════════════════════════════════════
           PÁGINA ÚNICA — sin pestañas. Antes había 5 (Resumen/Proyectos/
           Metas/Áreas/Analítica); a pedido de Alex se retiró la navegación
           y todo se apila en orden: KPIs, estado de la inversión, requiere
           atención, perspectivas del PDL, analítica. Proyectos y Metas ya
           no viven acá — la jerarquía de perspectivas los cubre, y sus
           listados propios están en otras rutas (/presupuesto/proyectos,
           /presupuesto/metas). Áreas queda oculto por ahora (mostrarAreas).
           ═══════════════════════════════════════════════════════════════════ -->

      <div id="vpanel-resumen">
        <section class="resumen-kpis" aria-label="Indicadores ejecutivos de inversión">
          <app-stat-grid [stats]="kpisEjecutivos()" />
        </section>

        <!-- ════════ Layout de 2 columnas: perspectivas a la izquierda,
             barra lateral fija a la derecha (Alertas, Resumen del plan,
             Impacto/analítica) — mismo espíritu del mockup de Alex. ═══ -->
        <div class="content-grid">
          <section class="perspectivas-seccion" aria-labelledby="persp-seccion-tit">
            <h2 class="perspectivas-seccion__tit" id="persp-seccion-tit">Perspectivas del Plan de Desarrollo Local</h2>
            <app-perspectivas-explorador [objetivos]="objetivos()" />
          </section>

          <aside class="side">
            <app-objetivos-resumen [objetivos]="objetivos()" [modoSidebar]="true" />

            <section class="panel" aria-labelledby="side-impacto-tit">
              <h3 id="side-impacto-tit">Impacto / analítica</h3>
              @if (g) {
                <div class="metric-row"><span>Beneficiarios</span><strong>{{ formatNumero(g.beneficiarios) }}</strong></div>
                <div class="metric-row"><span>Participantes</span><strong>{{ formatNumero(g.participantes) }}</strong></div>
                <div class="metric-row"><span>Organizaciones</span><strong>{{ formatNumero(g.organizaciones) }}</strong></div>
                @if (r) {
                  <div class="metric-row"><span>Eventos este mes</span><strong>{{ r.eventos_mes }}</strong></div>
                }
              } @else {
                <p class="sin-dato">midiendo…</p>
              }
              @if (mostrarAnalitica) {
                <a class="mini__ver" href="#analitica-seccion">
                  Ver detalle abajo <i class="fa fa-arrow-down-long" aria-hidden="true"></i>
                </a>
              }
            </section>

            <section class="panel" aria-labelledby="side-metas-tit">
              <h3 id="side-metas-tit">Metas del plan</h3>
              @if (metas(); as m) {
                <div class="side-donut">
                  <canvas #chartMetas></canvas>
                  <div class="side-donut__centro">
                    <b>{{ m.stats.total }}</b>
                    <span>metas</span>
                  </div>
                </div>
                <div class="metric-row"><span>Cumplidas</span><strong>{{ m.stats.cumplidas }}</strong></div>
                <div class="metric-row"><span>En progreso</span><strong>{{ m.stats.en_progreso }}</strong></div>
                <div class="metric-row"><span>En riesgo</span><strong>{{ m.stats.en_riesgo }}</strong></div>
                <div class="metric-row"><span>Sin avance</span><strong>{{ m.stats.sin_avance }}</strong></div>
              } @else {
                <p class="sin-dato">midiendo…</p>
              }
              <a class="mini__ver" routerLink="/presupuesto/metas">
                Ver listado <i class="fa fa-arrow-right-long" aria-hidden="true"></i>
              </a>
            </section>
          </aside>
        </div>
      </div>
      <!-- ════════ ANALÍTICA · beneficiarios/género + eventos — oculta por
           ahora a pedido de Alex; queda el código para reactivarla con un
           flip de mostrarAnalitica. ═══ -->
      @if (mostrarAnalitica) {
      <div id="analitica-seccion">

      <!-- ── Personas beneficiadas ───────────────────────────────────── -->
      <section class="acc acc--abierto acc--fijo">
        <h2 class="acc__h">
          <div class="acc__cabeza acc__cabeza--fija" id="acc-gente-bt">
            <span class="acc__icono acc__icono--gente" aria-hidden="true"><i class="fa fa-users"></i></span>
            <span class="acc__titulo">Personas beneficiadas</span>
            <span class="acc__resumen">
              @if (g) {
                <b>{{ formatNumero(g.beneficiarios) }}</b> beneficiarios
                · <b>{{ formatNumero(g.participantes) }}</b> participantes
                · <b>{{ formatNumero(g.organizaciones) }}</b> organizaciones
              } @else {
                <span class="sin-dato">midiendo…</span>
              }
            </span>
          </div>
        </h2>
        <div class="acc__cuerpo" id="acc-gente" role="region" aria-labelledby="acc-gente-bt">
          <div class="acc__inner">
            <div class="band band--llana" [class.skeleton]="!g">
            <div class="band__grid">
              <article class="big-stat big-stat--people">
                <div class="big-stat__value">{{ g ? formatNumero(g.beneficiarios) : '…' }}</div>
                <div class="big-stat__label">Beneficiarios</div>
              </article>
              <article class="big-stat">
                <div class="big-stat__value">{{ g ? formatNumero(g.pct_mujeres) + ' %' : '…' }}</div>
                <div class="big-stat__label">Mujeres</div>
              </article>
              <article class="big-stat">
                <div class="big-stat__value">{{ g ? formatNumero(g.participantes) : '…' }}</div>
                <div class="big-stat__label">Participantes · {{ g?.eventos_con_participacion }} eventos</div>
              </article>
              <article class="band__chart">
                <canvas #chartGenero></canvas>
              </article>
            </div>
            @if (g && g.caracterizaciones === 0) {
              <p class="band__note band__note--info">
                <i class="fa fa-circle-info" aria-hidden="true"></i>
                Edad, etnia y enfoque diferencial fino se activan cuando se diligencie la caracterización.
              </p>
            }
            </div>
            <!-- Contratación por categoría — comparte esta misma cabecera:
                 las dos se redibujan con la misma llamada (dibujarCockpitCharts). -->
            <h3 class="sub-bloque__titulo rotulo">Contratación por categoría</h3>
            <div class="chart-card">
              <canvas #chartCategoria></canvas>
            </div>
          </div>
        </div>
      </section>
      <!-- ── Eventos y analítica ─────────────────────────────────────── -->
      <section class="acc acc--abierto acc--fijo">
        <h2 class="acc__h">
          <div class="acc__cabeza acc__cabeza--fija" id="acc-eventos-bt">
            <span class="acc__icono acc__icono--eventos" aria-hidden="true"><i class="fa fa-chart-line"></i></span>
            <span class="acc__titulo">Eventos y analítica</span>
            <span class="acc__resumen">
              @if (r) {
                <b>{{ r.eventos_mes }}</b> {{ r.eventos_mes === 1 ? 'evento' : 'eventos' }} este mes
              } @else {
                <span class="sin-dato">midiendo…</span>
              }
            </span>
          </div>
        </h2>
        <div class="acc__cuerpo" id="acc-eventos" role="region" aria-labelledby="acc-eventos-bt">
          <div class="acc__inner">
            <div class="charts-row">
              <article class="chart-card">
                <header><h3><i class="fa fa-chart-line" aria-hidden="true"></i> Eventos por mes</h3></header>
                <canvas #chartMes></canvas>
              </article>
              <article class="chart-card">
                <header><h3><i class="fa fa-chart-pie" aria-hidden="true"></i> Eventos por tipo</h3></header>
                <canvas #chartTipo></canvas>
              </article>
              <!-- Si no hay sectores la tarjeta SE ENCOGE: reservar 220 px de alto
                   para un vacío es exactamente lo que hace que el tablero se lea
                   como un formulario a medio llenar. -->
              <article class="chart-card" [class.chart-card--vacio]="sectores() && !sectores()!.length">
                <header><h3><i class="fa fa-ranking-star" aria-hidden="true"></i> Top sectores</h3></header>
                @if (sectores() && !sectores()!.length) {
                  <p class="chart-card__vacio">Sin información de sectores disponible.</p>
                } @else {
                  <canvas #chartSect></canvas>
                }
              </article>
            </div>
          </div>
        </div>
      </section>
      </div>
      }

      <!-- ── Dinero y pendientes por área (el muro) — oculto por ahora,
           a pedido de Alex; queda el código para reactivarlo con un flip
           de mostrarAreas. ─────────────────────────────────────────── -->
      @if (mostrarAreas) {
      <div id="vpanel-areas">
      <section class="acc" [class.acc--abierto]="abierto('muro')">
        <h2 class="acc__h">
          <button type="button" class="acc__cabeza" id="acc-muro-bt"
                  [attr.aria-expanded]="abierto('muro')" aria-controls="acc-muro"
                  (click)="alternar('muro')">
            <i class="fa fa-chevron-right acc__flecha" aria-hidden="true"></i>
            <span class="acc__icono acc__icono--muro" aria-hidden="true"><i class="fa fa-layer-group"></i></span>
            <span class="acc__titulo">Dinero y pendientes por área</span>
            <span class="acc__resumen">
              @if (muro(); as m) {
                <b>{{ m.tarjetas.length }}</b> subgrupos, con sus pendientes y la cobertura del PDL
              } @else if (muroError()) {
                <span class="sin-dato">no disponible</span>
              } @else {
                <span class="sin-dato">midiendo…</span>
              }
            </span>
          </button>
        </h2>
        <div class="acc__cuerpo" id="acc-muro" role="region" aria-labelledby="acc-muro-bt">
          <div class="acc__inner">
            <app-muro-subgrupos [datos]="muro()" [error]="muroError()" [compacto]="true" />
          </div>
        </div>
      </section>
      </div>
      }
    </div>
  `,
  styleUrl: './presupuesto-dashboard.component.scss',
})
export class PresupuestoDashboardComponent implements OnInit, AfterViewInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);
  private auth = inject(AuthService);
  private router = inject(Router);

  @ViewChild('chartMetas') private chartMetasRef?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartMes') private chartMesRef?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartTipo') private chartTipoRef?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartSect') private chartSectRef?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartGenero') private chartGeneroRef?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartCategoria') private chartCategoriaRef?: ElementRef<HTMLCanvasElement>;

  Math = Math;
  formatNumero = formatNumero;
  loading = signal<boolean>(true);
  errorMsg = signal<string>('');
  resumen = signal<ResumenEjecutivo | null>(null);
  eventos = signal<EventosMesTipo | null>(null);
  sectores = signal<TopSectores | null>(null);
  metas = signal<MetasProgreso | null>(null);
  // Cockpit ejecutivo
  plata = signal<EjecucionFinanciera | null>(null);
  gente = signal<BeneficiariosPerfil | null>(null);
  vigencia = signal<number | null>(null);

  // ══ PRESENTACIÓN ═══════════════════════════════════════════════════
  //
  // Ya no hay pestañas: la página es una sola, todo apilado. Áreas y
  // Analítica quedan ocultas por ahora — el flag es lo único que hay que
  // voltear cuando se quieran reactivar.
  mostrarAreas = false;
  mostrarAnalitica = false;

  /** Fecha de corte para el encabezado — el mismo dato que ya usa el ledger. */
  corteTexto = computed<string | null>(() => {
    const c = this.muro()?.cabecera?.corte;
    return c ? this.fecha(c) : null;
  });

  cortePdlTexto = computed<string | null>(() => {
    const c = this.muro()?.cabecera?.corte_pdl_oficial;
    return c ? this.fecha(c) : null;
  });

  /** El corte de la Matriz de la ALK. Se prefiere el que la matriz DECLARA;
   *  a falta de él —los cortes que entraron por consola no lo registran— se
   *  muestra la fecha de carga con la palabra «cargada», para no hacer pasar
   *  una por la otra. */
  corteMatrizTexto = computed<string | null>(() => {
    const cm = this.muro()?.cabecera?.corte_matriz_pdl;
    if (!cm) return null;
    if (cm.corte_oficial) return this.fecha(cm.corte_oficial);
    return cm.cargado_at ? `${this.fecha(cm.cargado_at)} (cargada)` : null;
  });

  /**
   * Los 4 KPI ejecutivos. Programado/Comprometido/Girado salen del MISMO
   * ledger —misma fuente, mutuamente consistentes—, nunca mezclados con
   * `plata()`, que es una lente distinta con su propio universo. Avance
   * físico sí sale de `plata()` porque es la única fuente que lo calcula.
   */
  kpisEjecutivos = computed<StatItem[]>(() => {
    const prog = this.ledgerProgramado();
    const comp = this.ledgerComprometido();
    const gir = this.ledgerGirado();
    const p = this.plata();
    const ap = this.ledgerApropiacion();
    return [
      // Encabeza la APROPIACIÓN, no el proyectado: es el primer eslabón real
      // de la cadena (Apropiación → Comprometido → Girado) y es contra ella
      // que un «% de ejecución» significa algo. Si todavía no hay ninguna
      // matriz cargada, el tile cae al proyectado en vez de quedar vacío.
      ap
        ? {
            value: this.enMillones(ap.valor),
            label: 'Apropiación',
            sublabel: this.rangoApropiacion(),
          }
        : {
            value: prog.valor != null ? this.enMillones(prog.valor) : 'Sin dato',
            label: 'Proyectado', sublabel: this.coberturaDe('programado') ?? 'PDL oficial',
          },
      {
        value: comp.valor != null ? this.enMillones(comp.valor) : 'Sin dato',
        label: 'Comprometido', sublabel: this.coberturaDe('comprometido') ?? undefined,
      },
      {
        value: gir.valor != null ? this.enMillones(gir.valor) : 'Sin dato',
        label: 'Girado', sublabel: this.coberturaDe('girado') ?? undefined,
      },
      {
        value: p ? `${this.formatNumero(p.pct_ejecucion)} %` : 'Sin dato',
        label: 'Avance físico', sublabel: 'ponderado',
        variant: p ? this.varianteAvance(p.pct_ejecucion) : undefined,
      },
    ];
  });

  private varianteAvance(pct: number): 'ok' | 'warn' | undefined {
    if (pct >= 80) return 'ok';
    if (pct < 50) return 'warn';
    return undefined;
  }

  /**
   * Acordeón. Sólo queda «muro» (Áreas): «Seguimiento del Plan» y los dos de
   * Analítica dejaron de serlo — vivían solos dentro de su propia pestaña, así
   * que el clic para abrirlos era una segunda capa de plegado sobre la
   * primera (la pestaña), y esa doble ocultación era ilegible: dos clics para
   * ver un dato que ya se vino a buscar.
   */
  private abiertos = signal<ReadonlySet<Clave>>(new Set<Clave>());

  abierto(k: Clave): boolean { return this.abiertos().has(k); }

  alternar(k: Clave): void {
    const s = new Set(this.abiertos());
    const abriendo = !s.has(k);
    if (abriendo) s.add(k); else s.delete(k);
    this.abiertos.set(s);
  }

  // ── Muro de subgrupos (Fase 1) ──
  muro = signal<MuroSubgrupos | null>(null);
  muroError = signal<string | null>(null);

  // ══ EXPLORADOR MAESTRO / DETALLE ═══════════════════════════════════
  //
  // El resumen superior (cortes + ledger) reusa los MISMOS helpers del muro
  // en vez de escribir unos nuevos: un tercer formateador de plata en la
  // misma página es exactamente lo que no se quiere.
  fecha = fechaLegible;
  enMillones = enMillones;
  cifra = cifraLedger;
  /**
   * La procedencia de cada cifra del ledger, en una línea.
   *
   * No basta con `coberturaLedgerTexto` porque el payload guarda la cobertura
   * en DOS sitios distintos, y esa era la razón de que no se imprimiera nunca:
   *
   *   ledger.programado   → objeto, con su cobertura DENTRO y de otra forma
   *                         (proyectos_oficiales / ambito, no con/de)
   *   ledger.comprometido → número plano; su cobertura vive un nivel arriba,
   *   ledger.girado         en `ledger.cobertura.comprometido` / `.girado`
   *   ledger.saldo        → derivado, no tiene cobertura propia
   *
   * Decirlo importa: «$35.165 M» sin el «22 de 25 contratos» al lado se lee
   * como el total, y es el total DE LO QUE TIENE VALOR CARGADO.
   */
  coberturaTexto = coberturaLedgerTexto;

  coberturaDe(clave: 'programado' | 'comprometido' | 'girado' | 'saldo'): string | null {
    const led: any = this.muro()?.ledger;
    if (!led) return null;
    if (clave === 'programado') {
      const amb = led.programado?.cobertura?.ambito;
      return amb ? String(amb) : null;
    }
    if (clave === 'saldo') return null;          // derivado: no tiene cobertura propia
    const c = led.cobertura?.[clave];
    return (c && c.con != null && c.de != null) ? `${c.con} de ${c.de} contratos` : null;
  }

  pctTiempo = computed(() =>
    this.muro()?.cabecera?.ventana_pdl?.pct_tiempo_transcurrido ?? null);

  /**
   * Apropiación POAI: el PRIMER eslabón real de la ejecución. La cadena
   * correcta es Apropiación → Comprometido → Girado; «Proyectado PDL» es la
   * meta aspiracional del cuatrienio y por eso bajó a segunda barra en vez de
   * encabezar. Puede venir null si todavía no se ha cargado ninguna matriz,
   * y en ese caso la barra simplemente no se pinta.
   */
  ledgerApropiacion = computed(() => this.muro()?.ledger?.apropiacion ?? null);

  /**
   * El rango de vigencias sale del DATO, no escrito a mano. El POAI se apropia
   * año a año: hoy son 2025-2026 y 2027-2028 aún no existen. Rotular esto como
   * «2025-2028» haría ver la cifra como la mitad de lo que debería y se leería
   * como un retraso que no es tal.
   */
  rangoApropiacion = computed(() => {
    const ap = this.ledgerApropiacion();
    if (!ap) return '';
    return ap.vigencia_desde === ap.vigencia_hasta
      ? `${ap.vigencia_desde}`
      : `${ap.vigencia_desde}-${ap.vigencia_hasta}`;
  });

  ledgerProgramado = computed(() => this.cifra(this.muro()?.ledger?.programado));
  ledgerComprometido = computed(() => this.cifra(this.muro()?.ledger?.comprometido));
  ledgerGirado = computed(() => this.cifra(this.muro()?.ledger?.girado));

  // ── Objetivo Estratégico → Programa → Proyecto → Meta. El árbol
  // completo se pide una sola vez acá y se pasa por @Input a los dos
  // componentes que lo consumen —así el resumen y el explorador nunca
  // pueden mostrar números distintos del mismo dato. ──
  objetivos = signal<ObjetivoEstrategico[]>([]);

  private async cargarObjetivos(): Promise<void> {
    const data = await this.safeGet('/presupuesto/api/objetivos-estrategicos/');
    this.objetivos.set(aplanarObjetivos(data));
  }

  private charts: Chart[] = [];
  private cockpitCharts: Chart[] = [];

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Presupuesto', url: '/presupuesto' },
      { label: 'Dashboard de KPIs' },
    ]);
    this.cargar();
  }

  private intentos = 0;

  ngAfterViewInit(): void { /* charts se dibujan al recibir data */ }

  recargar(): void {
    this.errorMsg.set('');
    this.intentos = 0;
    this.cargar();
  }

  private async safeGet(url: string): Promise<any> {
    // HttpClient (no fetch) para que el jwtInterceptor añada el Bearer:
    // en full-Angular el endpoint es JWT-first y un fetch con solo cookies
    // de sesión daría 401.
    try {
      return await firstValueFrom(this.http.get(this.cfg.url(url)));
    } catch (e: any) {
      if (e?.status === 401 || e?.status === 403) {
        (this as any)._needLogin = true;
      }
      return null;
    }
  }

  private cargar(): void {
    const base = '/dashboard/api/presupuesto';
    (this as any)._needLogin = false;
    this.loading.set(false); // muestra el shell inmediatamente, NO el "Cargando…"

    // ── Cada endpoint dispara su propia actualización de signal ──
    // Resultado: las secciones aparecen progresivamente, no a la vez.

    // 1. KPIs cards (lo primero que se ve, lo más importante)
    this.safeGet(`${base}/resumen-ejecutivo/`).then(r => {
      if (r) this.resumen.set(r);
      else this.maybeRetry();
    });

    // 2. Eventos por mes + tipo (gráficos)
    this.safeGet(`${base}/eventos-mes-tipo/`).then(e => {
      if (e) {
        this.eventos.set(e);
        setTimeout(() => this.dibujarCharts(), 80);
      }
    });

    // 3. Top sectores.
    //
    // El endpoint responde `{ sectores: [...] }`, NO un array pelado, y acá se
    // guardaba el objeto entero. Consecuencia medida (2026-08-23): la tarjeta
    // pintaba SIEMPRE «sin datos de sectores» —porque `{}.length` es undefined
    // y `!undefined` es true— con 6 sectores reales del otro lado. Un vacío
    // falso es peor que un vacío: manda a llenar algo que ya está lleno.
    // Se desenvuelve acá, en el borde, para que el resto del componente vea
    // siempre un array (o null mientras carga).
    this.safeGet(`${base}/top-sectores/`).then(s => {
      const filas: TopSectores | null =
        Array.isArray(s) ? s : (Array.isArray(s?.sectores) ? s.sectores : null);
      if (filas) {
        this.sectores.set(filas);
        setTimeout(() => this.dibujarCharts(), 80);
      }
    });

    // 4. Metas del plan — solo la tarjeta liviana del resumen.
    this.safeGet(`${base}/metas-progreso/`).then(m => {
      if (m) { this.metas.set(m); setTimeout(() => this.dibujarMetasChart(), 80); }
    });

    // ── Cockpit ejecutivo (additivo) ──
    this.cargarCockpit();

    // ── Muro de subgrupos (Fase 1) — petición independiente: si falla,
    //    el resto del dashboard sigue en pie. ──
    this.cargarMuro();

    // ── Objetivo Estratégico → Programa → Proyecto → Meta — el árbol que
    //    alimenta el explorador jerárquico y su resumen. ──
    this.cargarObjetivos();
  }

  /**
   * Trae el payload del muro.
   *
   * Una sola ruta, la real. Antes probaba tres candidatas en orden porque el
   * muro y su vista DRF se escribieron en paralelo — y las tres daban 404, así
   * que el muro salía siempre con el aviso de «no disponible» aunque el
   * endpoint funcionara. Si esta falla NO se pinta nada inventado: se muestra
   * el aviso, que es la conducta correcta.
   */
  private async cargarMuro(): Promise<void> {
    const d = await this.safeGet('/presupuesto/api/muro-subgrupos/');
    if (d && Array.isArray(d.tarjetas)) {
      this.muro.set(d as MuroSubgrupos);
      this.muroError.set(null);
      return;
    }
    this.muroError.set(
      'El muro de áreas no está disponible: el endpoint no respondió. '
      + 'No se muestran cifras estimadas.',
    );
  }

  /** Carga las dos lentes del cockpit (plata / gente). */
  private cargarCockpit(): void {
    const base = '/dashboard/api/presupuesto';
    const vq = this.vigencia() ? `?vigencia=${this.vigencia()}` : '';

    this.safeGet(`${base}/ejecucion-financiera/${vq}`).then(d => {
      if (d) { this.plata.set(d); setTimeout(() => this.dibujarCockpitCharts(), 80); }
    });
    this.safeGet(`${base}/beneficiarios-perfil/`).then(d => {
      if (d) { this.gente.set(d); setTimeout(() => this.dibujarCockpitCharts(), 80); }
    });
  }

  /** SIEMPRE 2025/2026 en el chip — ni de menos (2026 puede no tener
   *  contratos todavía y aun así hay que poder elegirlo) ni de más
   *  (`plata()` trae años sueltos de contratos legacy, p.ej. 2015, que no
   *  son vigencias del PDL vigente). No depende de lo que traiga el
   *  backend en `p.vigencias`. */
  vigenciasVisibles(_traidas: number[]): number[] {
    return [2025, 2026];
  }

  /** Cambia la vigencia activa y recarga solo lo que depende de ella. */
  setVigencia(v: number | null): void {
    this.vigencia.set(v);
    const base = '/dashboard/api/presupuesto';
    const vq = v ? `?vigencia=${v}` : '';
    this.safeGet(`${base}/ejecucion-financiera/${vq}`).then(d => {
      if (d) { this.plata.set(d); setTimeout(() => this.dibujarCockpitCharts(), 80); }
    });
  }

  /**
   * Formatea pesos a millones legibles: 11283436256 → "$11.283 M".
   *
   * Delega en `enMillones` —el mismo del muro y del resumen superior— para que
   * la página tenga UN formateador de plata y no tres. Conserva su '…' propio
   * porque acá el null significa «todavía cargando», no «no hay dato».
   */
  plataMM(n?: number | null): string {
    return n == null ? '…' : enMillones(n);
  }

  private maybeRetry(): void {
    if ((this as any)._needLogin && this.intentos < 1) {
      this.intentos++;
      this.auth.fetchMe().subscribe({
        next: () => setTimeout(() => this.cargar(), 150),
        error: () => this.errorMsg.set('Sesión expirada. Logout + login.'),
      });
    } else if ((this as any)._needLogin) {
      this.errorMsg.set('Sesión Django no activa. Cerrá sesión y entrá otra vez.');
    }
  }

  private metasChart?: Chart;

  /** Donut chico de "Metas del plan" en la barra lateral — mismas 4
   *  categorías que ya muestra la tarjeta en texto, solo que visual. */
  private dibujarMetasChart(): void {
    const el = this.chartMetasRef?.nativeElement;
    const m = this.metas();
    if (!el || !m) return;
    this.metasChart?.destroy();
    const datos = [
      { etiqueta: 'Cumplidas', valor: m.stats.cumplidas, color: '#166534' },
      { etiqueta: 'En progreso', valor: m.stats.en_progreso, color: '#1D4ED8' },
      { etiqueta: 'En riesgo', valor: m.stats.en_riesgo, color: '#92400E' },
      { etiqueta: 'Sin avance', valor: m.stats.sin_avance, color: '#9CA3AF' },
    ].filter(d => d.valor > 0);
    if (!datos.length) return;
    this.metasChart = new Chart(el, {
      type: 'doughnut',
      data: {
        labels: datos.map(d => d.etiqueta),
        datasets: [{
          data: datos.map(d => d.valor),
          backgroundColor: datos.map(d => d.color),
          borderWidth: 2, borderColor: '#fff',
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        cutout: '68%',
        plugins: { legend: { display: false } },
      },
    });
  }

  private destruirCharts(): void {
    for (const c of this.charts) c.destroy();
    this.charts = [];
  }

  private dibujarCockpitCharts(): void {
    for (const c of this.cockpitCharts) c.destroy();
    this.cockpitCharts = [];

    const g = this.gente();
    const p = this.plata();
    const cg = this.chartGeneroRef?.nativeElement;
    const cc = this.chartCategoriaRef?.nativeElement;

    // Género (doughnut) — dato real: 62% mujeres
    if (g?.genero?.length && cg) {
      const colores: Record<string, string> = {
        'Femenino': '#EC4899', 'Masculino': '#0EA5E9', 'Prefiere no decirlo': '#94A3B8',
      };
      this.cockpitCharts.push(new Chart(cg, {
        type: 'doughnut',
        data: {
          labels: g.genero.map(x => x.nombre),
          datasets: [{
            data: g.genero.map(x => x.total),
            backgroundColor: g.genero.map(x => colores[x.nombre] || '#8B5CF6'),
            borderWidth: 2, borderColor: '#fff',
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, padding: 10 } } },
          cutout: '62%',
        },
      }));
    }

    // Contratación por categoría (barras horizontales, en millones)
    if (p?.por_categoria?.length && cc) {
      const cats = p.por_categoria.filter(x => x.valor > 0);
      this.cockpitCharts.push(new Chart(cc, {
        type: 'bar',
        data: {
          labels: cats.map(x => x.categoria),
          datasets: [{
            label: 'Valor (millones)',
            data: cats.map(x => Math.round(x.valor / 1e6)),
            backgroundColor: ['#0D9488', '#0EA5E9', '#F59E0B', '#8B5CF6', '#EC4899', '#6B7280'],
            borderRadius: 6,
          }],
        },
        options: {
          indexAxis: 'y',
          responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (ctx: any) =>
                  '$' + Number(ctx.raw).toLocaleString('es-CO') + ' millones',
              },
            },
          },
          scales: {
            x: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } },
            y: { grid: { display: false } },
          },
        },
      }));
    }
  }

  private dibujarCharts(): void {
    this.destruirCharts();
    const cMes = this.chartMesRef?.nativeElement;
    const cTipo = this.chartTipoRef?.nativeElement;
    const cSect = this.chartSectRef?.nativeElement;
    if (!cMes && !cTipo && !cSect) return;

    const e = this.eventos();
    const s = this.sectores();

    const accent = '#0D9488';
    const primary = '#D6001C';
    const secondary = '#FFC72C';

    // Eventos por mes (línea)
    if (e?.por_mes?.length && cMes) {
      this.charts.push(new Chart(cMes, {
        type: 'line',
        data: {
          labels: e.por_mes.map(p => p.mes),
          datasets: [{
            label: 'Eventos',
            data: e.por_mes.map(p => p.total),
            borderColor: primary,
            backgroundColor: 'rgba(214,0,28,0.15)',
            fill: true, tension: 0.35, borderWidth: 3,
            pointBackgroundColor: primary, pointRadius: 4, pointHoverRadius: 7,
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false }, tooltip: { mode: 'index' } },
          scales: {
            y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } },
            x: { grid: { display: false } },
          },
        },
      }));
    }

    // Eventos por tipo (doughnut)
    if (e?.por_tipo?.length && cTipo) {
      const palette = ['#D6001C', '#0D9488', '#0EA5E9', '#F59E0B',
                       '#8B5CF6', '#EC4899', '#22C55E', '#6B7280'];
      this.charts.push(new Chart(cTipo, {
        type: 'doughnut',
        data: {
          labels: e.por_tipo.map(t => tipoEventoNombre(t.tipo)),
          datasets: [{
            data: e.por_tipo.map(t => t.total),
            backgroundColor: e.por_tipo.map((_, i) => palette[i % palette.length]),
            borderWidth: 2, borderColor: '#fff',
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: { position: 'bottom', labels: { boxWidth: 12, padding: 12 } },
          },
          cutout: '60%',
        },
      }));
    }

    // Top sectores (horizontal bar) — backend devuelve array directo
    if (Array.isArray(s) && s.length && cSect) {
      this.charts.push(new Chart(cSect, {
        type: 'bar',
        data: {
          labels: s.map(x => x.sector),
          datasets: [{
            label: '% Avance',
            data: s.map(x => x.porcentaje),
            backgroundColor: s.map(x =>
              x.porcentaje >= 80 ? '#22C55E'
                : x.porcentaje >= 50 ? '#F59E0B'
                : '#DC2626'),
            borderRadius: 6,
          }],
        },
        options: {
          indexAxis: 'y',
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { beginAtZero: true, max: 100,
                 grid: { color: 'rgba(0,0,0,0.05)' } },
            y: { grid: { display: false } },
          },
        },
      }));
    }
  }
}
