import { CommonModule } from '@angular/common';
import {
  AfterViewInit, Component, ElementRef, Input, OnChanges, OnDestroy,
  SimpleChanges, ViewChild, computed, signal,
} from '@angular/core';
import { Chart, registerables } from 'chart.js';
import { formatNumero } from '../../../shared/format/format.util';
import { enMillones } from '../muro/muro-subgrupos.component';
import { ALERTAS, ObjetivoEstrategico, ProyectoLista, comprometidoDe } from './objetivos.types';

Chart.register(...registerables);

/**
 * KPIs generales + donut de alertas — la cabecera del explorador jerárquico.
 * Vive ANTES del Nivel 1 (perspectivas) para responder de un vistazo «¿cómo
 * va la localidad?» antes de bajar a un eje puntual.
 *
 * No pide datos por su cuenta: recibe el mismo árbol que ya cargó el
 * padre (`/objetivos-estrategicos/`) y solo agrega. Las cifras de plata
 * reusan `resumen.apropiacion_total`/`comprometido_total` que el backend
 * ya sumó por objetivo — sumar OTRA vez desde cero sería una segunda
 * fuente de verdad sobre el mismo número.
 */
@Component({
  standalone: true,
  selector: 'app-objetivos-resumen',
  imports: [CommonModule],
  template: `
    @if (modoSidebar) {
      <!-- ── Barra lateral: mismos números, formato compacto de tarjetas
           de metric-row en vez del KPI grid + donut grande. ── -->
      <section class="panel" aria-labelledby="side-alertas-tit">
        <h3 id="side-alertas-tit">Alertas que requieren atención</h3>
        @if (totalConAlerta() > 0) {
          <div class="side-donut">
            <canvas #donut></canvas>
            <div class="side-donut__centro">
              <b>{{ totalConAlerta() }}</b>
              <span>metas</span>
            </div>
          </div>
          <div class="alert-card alert-card--danger">
            <div><strong>{{ conteoAlerta()['Crítico'] ?? 0 }}</strong><small>metas críticas</small></div>
          </div>
          <div class="alert-card alert-card--success">
            <div><strong>{{ conteoAlerta()['Ejecutada'] ?? 0 }}</strong><small>metas ejecutadas</small></div>
          </div>
          @for (a of ALERTAS_MEDIAS; track a.valor) {
            @if (conteoAlerta()[a.valor]) {
              <div class="metric-row"><span>{{ a.etiqueta }}</span><strong>{{ conteoAlerta()[a.valor] }}</strong></div>
            }
          }
        } @else {
          <p class="sin-dato">Sin alertas registradas.</p>
        }
      </section>

      <section class="panel" aria-labelledby="side-resumen-tit">
        <h3 id="side-resumen-tit">Resumen del plan</h3>
        <div class="metric-row"><span>Perspectivas · Programas</span><strong>{{ nObjetivos() }} · {{ nProgramas() }}</strong></div>
        <div class="metric-row"><span>Proyectos · Metas</span><strong>{{ nProyectos() }} · {{ nMetas() }}</strong></div>
        <div class="metric-row"><span>Presupuesto programado</span><strong>{{ enMillones(presupuestoProgramado()) }}</strong></div>
        <div class="metric-row">
          <span>Ejecución financiera</span>
          @if (pctEjecucion() != null) { <strong>{{ formatNumero(pctEjecucion()!) }}%</strong> }
          @else { <strong class="sin-dato">Sin dato</strong> }
        </div>
      </section>
    } @else {
      <section class="oresumen" aria-labelledby="oresumen-tit">
        <h2 id="oresumen-tit" class="ui-sr-only">Resumen general</h2>

        <div class="oresumen__kpis">
          <div class="okpi">
            <span class="okpi__label">Perspectivas · Programas</span>
            <span class="okpi__val">{{ nObjetivos() }} · {{ nProgramas() }}</span>
          </div>
          <div class="okpi">
            <span class="okpi__label">Proyectos · Metas</span>
            <span class="okpi__val">{{ nProyectos() }} · {{ nMetas() }}</span>
          </div>
          <div class="okpi">
            <span class="okpi__label">Presupuesto programado</span>
            <span class="okpi__val">{{ enMillones(presupuestoProgramado()) }}</span>
            <span class="okpi__sub">total PDL cargado</span>
          </div>
          <div class="okpi">
            <span class="okpi__label">Ejecución financiera</span>
            @if (pctEjecucion() != null) {
              <span class="okpi__val">{{ formatNumero(pctEjecucion()!) }}%</span>
              <span class="okpi__sub">comprometido / programado</span>
            } @else {
              <span class="okpi__val sin-dato">Sin dato</span>
            }
          </div>
        </div>

        @if (totalConAlerta() > 0) {
          <div class="oalertas">
            <div class="oalertas__donut">
              <canvas #donut></canvas>
              <div class="oalertas__centro">
                <b>{{ totalConAlerta() }}</b>
                <span>metas</span>
              </div>
            </div>
            <ul class="oalertas__leyenda">
              @for (a of ALERTAS; track a.valor) {
                @if (conteoAlerta()[a.valor]) {
                  <li>
                    <span class="oalertas__punto" [class]="'oalertas__punto--' + a.clase" aria-hidden="true"></span>
                    <span class="oalertas__nombre">{{ a.etiqueta }}</span>
                    <span class="oalertas__barra" aria-hidden="true">
                      <span [class]="'oalertas__fill oalertas__fill--' + a.clase"
                            [style.width.%]="(conteoAlerta()[a.valor] ?? 0) / totalConAlerta() * 100"></span>
                    </span>
                    <b class="oalertas__num">{{ conteoAlerta()[a.valor] }}</b>
                  </li>
                }
              }
            </ul>
          </div>
        }
      </section>
    }
  `,
  styleUrl: './objetivos-resumen.component.scss',
})
export class ObjetivosResumenComponent implements OnChanges, AfterViewInit, OnDestroy {
  @Input() objetivos: ObjetivoEstrategico[] = [];

  /** En la barra lateral (mockup): mismos números, formato compacto de
   *  tarjetas + metric-rows en vez del KPI grid + donut grande. */
  @Input() modoSidebar = false;

  @ViewChild('donut') private donutRef?: ElementRef<HTMLCanvasElement>;
  private chart?: Chart;

  readonly ALERTAS = ALERTAS;
  /** Las 3 del medio (sin Crítico ni Ejecutada, que en el sidebar van como
   *  tarjetas grandes aparte). */
  readonly ALERTAS_MEDIAS = ALERTAS.slice(1, -1);
  formatNumero = formatNumero;
  enMillones = enMillones;

  private datos = signal<ObjetivoEstrategico[]>([]);

  /** Proyectos únicos de todo el árbol — un proyecto puede listarse en más
   *  de un programa si sus metas tocan varios; acá se cuenta una sola vez. */
  private proyectosUnicos = computed<ProyectoLista[]>(() => {
    const vistos = new Map<number, ProyectoLista>();
    for (const obj of this.datos()) {
      for (const prog of obj.programas) {
        for (const p of prog.proyectos) vistos.set(p.id, p);
      }
    }
    return [...vistos.values()];
  });

  nObjetivos = computed(() => this.datos().length);
  nProgramas = computed(() => this.datos().reduce((s, o) => s + o.programas.length, 0));
  nProyectos = computed(() => this.proyectosUnicos().length);
  nMetas = computed(() => this.proyectosUnicos().reduce((s, p) => s + (p.n_metas ?? 0), 0));

  presupuestoProgramado = computed(() =>
    this.proyectosUnicos().reduce((s, p) => s + (p.programado_oficial ?? 0), 0));

  pctEjecucion = computed<number | null>(() => {
    const programado = this.presupuestoProgramado();
    if (!programado) return null;
    const comprometido = this.proyectosUnicos()
      .reduce((s, p) => s + (comprometidoDe(p).valor ?? 0), 0);
    return Math.round((comprometido / programado) * 1000) / 10;
  });

  /** Suma `alerta_conteo` (el desglose POR META que cada proyecto ya trae)
   *  de todos los proyectos únicos — es la única forma de llegar a un
   *  conteo real de metas sin que el backend tenga que exponer la lista
   *  completa de las 78. */
  conteoAlerta = computed<Partial<Record<string, number>>>(() => {
    const out: Partial<Record<string, number>> = {};
    for (const p of this.proyectosUnicos()) {
      for (const [alerta, n] of Object.entries(p.alerta_conteo ?? {})) {
        out[alerta] = (out[alerta] ?? 0) + n;
      }
    }
    return out;
  });
  totalConAlerta = computed(() =>
    Object.values(this.conteoAlerta()).reduce((s: number, n) => s + (n ?? 0), 0));

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['objetivos']) {
      this.datos.set(this.objetivos ?? []);
      this.dibujarDonut();
    }
  }

  ngAfterViewInit(): void { this.dibujarDonut(); }
  ngOnDestroy(): void { this.chart?.destroy(); }

  private dibujarDonut(): void {
    const el = this.donutRef?.nativeElement;
    if (!el || !this.totalConAlerta()) return;
    this.chart?.destroy();
    const colorPorClase: Record<string, string> = {
      critico: '#991B1B', desierta: '#374151', 'sin-magnitud': '#1D4ED8',
      cronograma: '#92400E', ejecutada: '#166534',
    };
    const entradas = this.ALERTAS.filter(a => this.conteoAlerta()[a.valor]);
    this.chart = new Chart(el, {
      type: 'doughnut',
      data: {
        labels: entradas.map(a => a.etiqueta),
        datasets: [{
          data: entradas.map(a => this.conteoAlerta()[a.valor] ?? 0),
          backgroundColor: entradas.map(a => colorPorClase[a.clase]),
          borderWidth: 2, borderColor: 'var(--sup-tarjeta, #fff)',
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        cutout: '68%',
        plugins: { legend: { display: false } },
      },
    });
  }
}
