import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import {
  AfterViewInit, Component, ElementRef,
  OnInit, ViewChild, inject, signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { Chart, registerables } from 'chart.js';
import { forkJoin, of, timer } from 'rxjs';
import { catchError, timeout } from 'rxjs/operators';
import { AuthService } from '../../core/auth/auth.service';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';
import { formatNumero, tipoEventoNombre } from '../../shared/format/format.util';

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
interface KpisAvance {
  total_kpis: number; en_riesgo: number; pct_promedio_cumplimiento: number;
  kpis: Array<{
    id: number; nombre: string; unidad?: string; meta?: number;
    avance?: number; porcentaje: number; en_riesgo?: boolean;
    fecha_fin?: string; num_avances?: number;
  }>;
}
interface ObjetivosProy {
  rows: Array<{ proyecto: string; objetivos: number; programas?: number }>;
}

@Component({
  standalone: true,
  selector: 'app-presupuesto-dashboard',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page">
      <header class="hero">
        <div>
          <h1>
            <i class="fa fa-chart-pie"></i> Dashboard Presupuesto
          </h1>
          <p class="hero__subtitle">
            Visión 360° del Plan de Desarrollo: planeación, ejecución y seguimiento.
          </p>
        </div>
        <div class="hero__badges">
          <span class="badge"><i class="fa fa-layer-group"></i> PDD activo</span>
          <span class="badge"><i class="fa fa-diagram-project"></i> 12 entidades operativas</span>
        </div>
      </header>

      @if (errorMsg()) {
        <div class="error-card">
          <i class="fa fa-exclamation-triangle"></i>
          <strong>{{ errorMsg() }}</strong>
          <button class="ui-btn ui-btn--sm" (click)="recargar()">
            <i class="fa fa-rotate"></i> Reintentar
          </button>
        </div>
      }
      <!-- Layout siempre visible — secciones aparecen progresivamente -->
      @if (true) {
        @let r = resumen();
        <div class="kpi-grid" [class.skeleton]="!r">
          <a class="kpi-card kpi-card--primary kpi-card--link" routerLink="/presupuesto/proyectos"
             aria-label="Ver listado de proyectos del plan">
            <div class="kpi-card__icon"><i class="fa fa-folder-open"></i></div>
            <div class="kpi-card__body">
              <div class="kpi-card__value">{{ r?.proyectos ?? '…' }}</div>
              <div class="kpi-card__label">Proyectos del Plan</div>
            </div>
          </a>
          <a class="kpi-card kpi-card--accent kpi-card--link" routerLink="/presupuesto/metas"
             aria-label="Ver listado de metas">
            <div class="kpi-card__icon"><i class="fa fa-bullseye"></i></div>
            <div class="kpi-card__body">
              <div class="kpi-card__value">{{ r?.metas_pdd ?? '…' }}</div>
              <div class="kpi-card__label">Metas PDD</div>
            </div>
          </a>
          <a class="kpi-card kpi-card--info kpi-card--link" routerLink="/presupuesto/indicadores"
             aria-label="Ver listado de indicadores (KPIs)">
            <div class="kpi-card__icon"><i class="fa fa-chart-line"></i></div>
            <div class="kpi-card__body">
              <div class="kpi-card__value">{{ r?.indicadores ?? '…' }}</div>
              <div class="kpi-card__label">Indicadores (KPIs)</div>
            </div>
          </a>
          <article class="kpi-card kpi-card--secondary kpi-card--static"
                   title="Solo contador (eventos del mes en curso)">
            <div class="kpi-card__icon"><i class="fa fa-calendar-alt"></i></div>
            <div class="kpi-card__body">
              <div class="kpi-card__value">{{ r?.eventos_mes ?? '…' }}</div>
              <div class="kpi-card__label">Eventos del mes</div>
            </div>
          </article>
          <a class="kpi-card kpi-card--success kpi-card--link" routerLink="/presupuesto/avances"
             aria-label="Ver listado de avances a KPIs">
            <div class="kpi-card__icon"><i class="fa fa-check-circle"></i></div>
            <div class="kpi-card__body">
              <div class="kpi-card__value">{{ r?.avances ?? '…' }}</div>
              <div class="kpi-card__label">Avances a KPIs</div>
            </div>
          </a>
          <article class="kpi-card kpi-card--danger kpi-card--static"
                   title="Solo contador (KPIs en riesgo de incumplimiento)">
            <div class="kpi-card__icon"><i class="fa fa-exclamation-triangle"></i></div>
            <div class="kpi-card__body">
              <div class="kpi-card__value">{{ r?.en_riesgo ?? '…' }}</div>
              <div class="kpi-card__label">KPIs en riesgo</div>
            </div>
          </article>
        </div>

        <!-- 3 GRÁFICOS -->
        <div class="charts-row">
          <article class="chart-card">
            <header><h2><i class="fa fa-chart-line"></i> Eventos por mes</h2></header>
            <canvas #chartMes></canvas>
          </article>
          <article class="chart-card">
            <header><h2><i class="fa fa-chart-pie"></i> Eventos por tipo</h2></header>
            <canvas #chartTipo></canvas>
          </article>
          <article class="chart-card">
            <header>
              <h2><i class="fa fa-trophy" style="color:#f59e0b"></i> Top sectores</h2>
            </header>
            @if (sectores() && !sectores()!.length) {
              <div class="ui-empty-state">Sin datos de sectores aún.</div>
            } @else {
              <canvas #chartSect></canvas>
            }
          </article>
        </div>

        <!-- METAS + KPIs lado a lado -->
        <div class="dos-cols">
          @if (metas()) {
            @let m = metas()!;
            <section class="seccion">
              <header class="seccion__header">
                <h2><i class="fa fa-flag" style="color:#8b5cf6"></i> Metas del Plan</h2>
                <div class="stats-strip">
                  <span class="stat stat--ok">{{ m.stats.cumplidas }} ✓</span>
                  <span class="stat stat--prog">{{ m.stats.en_progreso }} ↗</span>
                  <span class="stat stat--warn">{{ m.stats.en_riesgo }} ⚠</span>
                  <span class="stat stat--none">{{ m.stats.sin_avance }} —</span>
                </div>
              </header>
              <div class="seccion__scroll">
                <div class="metas-grid">
                  @for (mt of m.metas; track mt.codigo) {
                    <article class="meta-card" [class]="'meta-card--' + mt.estado">
                      <div class="meta-card__head">
                        <strong>{{ mt.codigo }}</strong>
                        <span class="meta-card__badge"
                              [class]="'badge-' + mt.estado">
                          {{ etiquetaEstado(mt.estado) }}
                        </span>
                      </div>
                      <p class="meta-card__nombre">{{ mt.nombre }}</p>
                      <div class="meta-card__foot">
                        @if (mt.sector) { <span>{{ mt.sector }}</span> }
                        @if (mt.num_indicadores) {
                          <span><i class="fa fa-chart-line"></i> {{ mt.num_indicadores }} KPI</span>
                        }
                        @if (mt.fecha_fin) {
                          <span><i class="fa fa-calendar-alt"></i> {{ mt.fecha_fin }}</span>
                        }
                      </div>
                      <div class="barra">
                        <div class="barra__fill"
                             [class]="claseBarra(mt.porcentaje)"
                             [style.width.%]="Math.min(mt.porcentaje, 100)">
                        </div>
                        <span class="barra__label">{{ formatNumero(mt.porcentaje) }}%</span>
                      </div>
                    </article>
                  }
                </div>
              </div>
            </section>
          }

          @if (kpisData()) {
            @let kd = kpisData()!;
            <section class="seccion">
              <header class="seccion__header">
                <h2><i class="fa fa-bullseye"></i> Avance de KPIs</h2>
                <div class="stats-strip">
                  <span class="stat">{{ kd.total_kpis }}</span>
                  <span class="stat stat--warn">{{ kd.en_riesgo }} riesgo</span>
                  <span class="stat stat--ok">{{ formatNumero(kd.pct_promedio_cumplimiento) }}% prom.</span>
                </div>
              </header>
              <div class="seccion__scroll">
                <div class="kpis-table">
                  @for (k of kpisOrdenados(); track k.id) {
                    <article class="kpi-item">
                      <div class="kpi-item__head">
                        <strong>{{ k.nombre }}</strong>
                        <span class="kpi-item__pct"
                              [class]="claseTexto(k.porcentaje)">
                          {{ formatNumero(k.porcentaje) }}%
                        </span>
                      </div>
                      <div class="barra">
                        <div class="barra__fill"
                             [class]="claseBarra(k.porcentaje)"
                             [style.width.%]="Math.min(k.porcentaje, 100)"></div>
                      </div>
                    </article>
                  }
                </div>
              </div>
            </section>
          }
        </div>

        <!-- OBJETIVOS POR PROYECTO -->
        @if (objetivos(); as o) {
          @if (o.rows.length) {
            <section class="seccion">
              <header class="seccion__header">
                <h2><i class="fa fa-bullseye" style="color:#0EA5E9"></i>
                    Objetivos por Proyecto</h2>
              </header>
              <div class="ui-table-responsive">
                <table class="ui-table">
                  <thead>
                    <tr><th>Proyecto</th><th>Objetivos</th><th>Programas</th></tr>
                  </thead>
                  <tbody>
                    @for (r of o.rows; track r.proyecto) {
                      <tr>
                        <td>{{ r.proyecto }}</td>
                        <td><span class="badge-pill">{{ r.objetivos }}</span></td>
                        <td>
                          @if (r.programas) {
                            <span class="badge-pill">{{ r.programas }}</span>
                          } @else { — }
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            </section>
          }
        }
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

  @ViewChild('chartMes') private chartMesRef?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartTipo') private chartTipoRef?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartSect') private chartSectRef?: ElementRef<HTMLCanvasElement>;

  Math = Math;
  formatNumero = formatNumero;
  loading = signal<boolean>(true);
  errorMsg = signal<string>('');
  resumen = signal<ResumenEjecutivo | null>(null);
  eventos = signal<EventosMesTipo | null>(null);
  sectores = signal<TopSectores | null>(null);
  metas = signal<MetasProgreso | null>(null);
  kpisData = signal<KpisAvance | null>(null);
  objetivos = signal<ObjetivosProy | null>(null);

  private charts: Chart[] = [];

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
    try {
      const res = await fetch(this.cfg.url(url), {
        credentials: 'same-origin',
        redirect: 'manual',
        headers: { 'Accept': 'application/json' },
      });
      if (res.type === 'opaqueredirect' || res.status === 0
          || res.status === 401 || res.status === 403) {
        (this as any)._needLogin = true;
        return null;
      }
      if (!res.ok) return null;
      return await res.json();
    } catch { return null; }
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

    // 3. Top sectores
    this.safeGet(`${base}/top-sectores/`).then(s => {
      if (s) {
        this.sectores.set(s);
        setTimeout(() => this.dibujarCharts(), 80);
      }
    });

    // 4. Metas
    this.safeGet(`${base}/metas-progreso/`).then(m => {
      if (m) this.metas.set(m);
    });

    // 5. KPIs lista
    this.safeGet(`${base}/kpis-avance/`).then(k => {
      if (k) this.kpisData.set(k);
    });

    // 6. Objetivos / cascada
    this.safeGet(`${base}/cascada-resumen`).then(o => {
      if (o) this.objetivos.set(this.adaptarObjetivos(o));
    });
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

  private adaptarObjetivos(raw: any): ObjetivosProy {
    if (raw?.rows) return raw;
    const rows = (raw?.proyectos || raw || []).map((p: any) => ({
      proyecto: p.codigo ? `${p.codigo} ${p.nombre || ''}`.trim()
                          : (p.nombre || `#${p.id || '?'}`),
      objetivos: p.n_objetivos ?? p.objetivos ?? 0,
      programas: p.n_programas ?? p.programas ?? 0,
    }));
    return { rows };
  }

  kpisOrdenados(): KpisAvance['kpis'] {
    const k = this.kpisData();
    if (!k) return [];
    return [...k.kpis].sort((a, b) => a.porcentaje - b.porcentaje).slice(0, 25);
  }

  etiquetaEstado(e: string): string {
    return ({
      cumplida: 'Cumplida',
      en_progreso: 'En progreso',
      en_riesgo: 'En riesgo',
      sin_avance: 'Sin avance',
    } as any)[e] || e;
  }

  claseBarra(pct: number): string {
    if (pct >= 80) return 'green';
    if (pct >= 50) return 'yellow';
    if (pct > 0) return 'red';
    return 'gray';
  }
  claseTexto(pct: number): string {
    if (pct >= 80) return 'pct-ok';
    if (pct >= 50) return 'pct-warn';
    return 'pct-bad';
  }

  private destruirCharts(): void {
    for (const c of this.charts) c.destroy();
    this.charts = [];
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
