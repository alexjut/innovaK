import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, ElementRef, OnDestroy, OnInit,
  ViewChild, inject, signal,
} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { Chart, registerables } from 'chart.js';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

Chart.register(...registerables);

const PALETTE = ['#D6001C', '#0D9488', '#2563eb', '#d97706', '#7c3aed',
  '#16a34a', '#db2777', '#0ea5e9', '#84cc16', '#64748b'];

interface Analitica {
  universo: number;
  kpis: { beneficiarios: number; eventos: number; areas: number; este_mes: number };
  por_area: { categoria: string; total: number }[];
  por_tipo: { categoria: string; total: number }[];
  tendencia: { mes: string; total: number }[];
  escenarios: { categoria: string; total: number }[];
  caracterizacion: Record<string, { categoria: any; total: number }[]>;
  caracterizados: number;
  geo: { eventos_con_ubicacion: number; beneficiarios_con_zona: number; por_zona: any[] };
}

@Component({
  standalone: true,
  selector: 'app-analitica',
  imports: [CommonModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
  <div class="an">
    <header class="an__hero">
      <div class="an__top">
        <div class="an__title-wrap">
          <span class="an__icon"><i class="fa fa-chart-line"></i></span>
          <div>
            <h1>Analítica de Beneficiarios</h1>
            <p>Tablero de los beneficiarios de los productos de los proyectos.</p>
          </div>
        </div>
        <a routerLink="/ia" class="ui-btn ui-btn--light ui-btn--sm">
          <i class="fa fa-wand-magic-sparkles"></i> Consulta IA
        </a>
      </div>
    </header>

    @if (loading()) {
      <div class="ui-info-bar ui-info-bar--info">Cargando tablero…</div>
    }
    @else if (errorMsg()) {
      <div class="ui-info-bar ui-info-bar--danger">{{ errorMsg() }}</div>
    }
    @else if (data()) {
    @if (data(); as d) {
      <div class="dash">

        <p class="section-label">Resumen general</p>
        <div class="kpi-strip">
          <article class="kpi-card kpi-card--a"><span class="kpi-card__v">{{ d.kpis.beneficiarios | number }}</span><span class="kpi-card__l">Beneficiarios</span></article>
          <article class="kpi-card kpi-card--b"><span class="kpi-card__v">{{ d.kpis.eventos | number }}</span><span class="kpi-card__l">Actividades</span></article>
          <article class="kpi-card kpi-card--c"><span class="kpi-card__v">{{ d.kpis.areas | number }}</span><span class="kpi-card__l">Áreas activas</span></article>
          <article class="kpi-card kpi-card--d"><span class="kpi-card__v">{{ d.caracterizados | number }}</span><span class="kpi-card__l">Caracterizados</span></article>
        </div>

        <p class="section-label">Beneficiarios por área</p>
        <div class="area-grid">
          @for (a of d.por_area; track a.categoria; let i = $index) {
            <article class="area-card">
              <div class="area-card__top">
                <span class="area-card__num">{{ i + 1 }}</span>
                <span class="area-card__name">{{ a.categoria }}</span>
                <span class="area-card__pct">{{ pctOfSum(a.total, d.por_area) }}%</span>
              </div>
              <div class="area-card__bar"><span [style.width.%]="pctOfSum(a.total, d.por_area)"></span></div>
              <span class="area-card__count">{{ a.total | number }} beneficiarios</span>
            </article>
          }
        </div>

        <p class="section-label">Tendencia mensual de beneficiarios</p>
        <article class="card card--wide">
          <div class="cbox cbox--tall"><canvas #chartTendencia></canvas></div>
        </article>

        <p class="section-label">Actividad y participación</p>
        <div class="grid2">
          <article class="card">
            <h3>Escenarios / actividades más usados</h3>
            @if (d.escenarios.length) {
              <div class="rank-list">
                @for (e of d.escenarios; track e.categoria; let i = $index) {
                  <div class="rank-row">
                    <span class="rank-row__i">{{ i + 1 }}</span>
                    <span class="rank-row__name">{{ e.categoria }}</span>
                    <div class="rank-row__bar"><span [style.width.%]="pct(e.total, maxOf(d.escenarios))"></span></div>
                    <span class="rank-row__v">{{ e.total | number }}</span>
                  </div>
                }
              </div>
            } @else {
              <p class="empty">Sin datos de escenarios.</p>
            }
          </article>
          <article class="card">
            <h3>Por sexo</h3>
            @if (d.caracterizacion['sexo'].length) { <div class="cbox"><canvas #chartSexo></canvas></div> }
            @else { <p class="empty">Sin caracterización de sexo.</p> }
          </article>
        </div>

        <p class="section-label">Caracterización de beneficiarios</p>
        <div class="grid2">
          <article class="card">
            <h3>Por estrato</h3>
            @if (d.caracterizacion['estrato'].length) {
              <div class="hbars">
                @for (c of d.caracterizacion['estrato']; track c.categoria) {
                  <div class="hbar-row">
                    <span class="hbar-row__l">{{ c.categoria }}</span>
                    <div class="hbar-row__bar"><span [style.width.%]="pct(c.total, maxOf(d.caracterizacion['estrato']))"></span></div>
                    <span class="hbar-row__v">{{ c.total | number }}</span>
                  </div>
                }
              </div>
            } @else { <p class="empty">Sin datos de estrato.</p> }
          </article>
          <article class="card">
            <h3>Por nivel educativo</h3>
            @if (d.caracterizacion['nivel_educativo'].length) {
              <div class="hbars">
                @for (c of d.caracterizacion['nivel_educativo']; track c.categoria) {
                  <div class="hbar-row">
                    <span class="hbar-row__l">{{ c.categoria }}</span>
                    <div class="hbar-row__bar"><span [style.width.%]="pct(c.total, maxOf(d.caracterizacion['nivel_educativo']))"></span></div>
                    <span class="hbar-row__v">{{ c.total | number }}</span>
                  </div>
                }
              </div>
            } @else { <p class="empty">Sin datos de educación.</p> }
          </article>
        </div>

        <p class="section-label">Cobertura geográfica</p>
        <article class="card card--wide geo">
          <h3><i class="fa fa-location-dot"></i> Ubicación</h3>
          <div class="geo-row">
            <div class="geo-stat"><span class="geo-stat__v">{{ d.geo.eventos_con_ubicacion | number }}</span><span class="geo-stat__l">Actividades georreferenciadas</span></div>
            <div class="geo-stat"><span class="geo-stat__v">{{ d.geo.beneficiarios_con_zona | number }}</span><span class="geo-stat__l">Beneficiarios con zona</span></div>
          </div>
          @if (!d.geo.beneficiarios_con_zona) {
            <p class="empty">
              <i class="fa fa-circle-info"></i> Los beneficiarios aún no tienen zona/UPL cargada.
              Se poblará cuando se caractericen (zona de residencia) o se georreferencien las actividades.
              Las {{ d.geo.eventos_con_ubicacion }} actividades georreferenciadas se ven en el
              <a routerLink="/mapa">Mapa de Kennedy</a>.
            </p>
          }
        </article>

      </div>
    }
    }
  </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .an { max-width: 1300px; margin: 0 auto; display: flex; flex-direction: column; gap: $space-4; }

    .an__hero { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-4; }
    .an__top { display: flex; justify-content: space-between; align-items: flex-start; gap: $space-3; flex-wrap: wrap; }
    .an__title-wrap { display: flex; align-items: flex-start; gap: $space-3; }
    .an__icon {
      width: 44px; height: 44px; border-radius: $radius-md;
      background: $color-primary; color: #fff;
      display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 1.1rem;
    }
    .an__hero h1 {
      margin: 0; color: $color-text; font-size: 32px; font-weight: $font-weight-semibold;
      &::after {
        content: ''; display: block; width: 48px; height: 4px;
        border-radius: $radius-pill; background: $color-secondary; margin-top: $space-2;
      }
    }
    .an__hero p { margin: $space-1 0 0; color: $color-text-muted; font-size: $font-size-sm; max-width: 620px; }

    .dash { background: #F5F1E8; border-radius: $radius-lg; padding: $space-4; display: flex; flex-direction: column; gap: $space-3; }
    .section-label {
      margin: $space-2 0 0; font-size: $font-size-xs; font-weight: $font-weight-semibold;
      letter-spacing: .06em; text-transform: uppercase; color: $color-text-muted;
    }

    .kpi-strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: $space-3; @media (max-width:700px) { grid-template-columns: repeat(2, 1fr); } }
    .kpi-card {
      background: #fff; border: 1px solid $color-border; border-top: 3px solid $color-primary;
      border-radius: $radius-md; padding: $space-3; display: flex; flex-direction: column; gap: 4px;
      &--b { border-top-color: #0D9488; } &--c { border-top-color: #2563eb; } &--d { border-top-color: #d97706; }
      &__v { font-size: 1.8rem; font-weight: 800; color: $color-text; line-height: 1; }
      &__l { font-size: $font-size-xs; color: $color-text-muted; }
    }

    .area-grid { display: grid; grid-template-columns: 1fr 1fr; gap: $space-3; @media (max-width:700px) { grid-template-columns: 1fr; } }
    .area-card {
      background: #fff; border: 1px solid $color-border; border-radius: $radius-md; padding: $space-3;
      display: flex; flex-direction: column; gap: 6px;
      &__top { display: flex; align-items: center; gap: $space-2; }
      &__num {
        width: 22px; height: 22px; border-radius: 50%; background: $color-bg-muted; color: $color-text;
        font-size: .75rem; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0;
      }
      &__name { flex: 1; font-weight: 600; color: $color-text; }
      &__pct { font-weight: 700; color: $color-primary; }
      &__bar {
        height: 8px; border-radius: $radius-pill; background: $color-bg-muted; overflow: hidden;
        span { display: block; height: 100%; background: $color-primary; border-radius: $radius-pill; }
      }
      &__count { font-size: $font-size-xs; color: $color-text-muted; }
    }

    .card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-4; }
    .card--wide { width: 100%; }
    h3 { margin: 0 0 $space-3; color: $color-primary; font-size: 1rem; }
    .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: $space-3; @media (max-width:900px){ grid-template-columns: 1fr; } }
    .cbox { height: 260px; } .cbox--tall { height: 300px; }
    .empty { color: $color-text-muted; font-size: $font-size-sm; padding: $space-3 0; }

    .rank-list { display: flex; flex-direction: column; gap: $space-2; }
    .rank-row {
      display: grid; grid-template-columns: 20px 1fr 2fr auto; align-items: center; gap: $space-2;
      &__i { font-size: $font-size-xs; color: $color-text-muted; font-weight: 700; }
      &__name { font-size: $font-size-sm; color: $color-text; }
      &__bar {
        height: 8px; border-radius: $radius-pill; background: $color-bg-muted; overflow: hidden;
        span { display: block; height: 100%; background: $color-primary; border-radius: $radius-pill; }
      }
      &__v { font-size: $font-size-sm; font-weight: 700; color: $color-text; min-width: 32px; text-align: right; }
    }

    .hbars { display: flex; flex-direction: column; gap: $space-2; }
    .hbar-row {
      display: grid; grid-template-columns: 1fr 2fr auto; align-items: center; gap: $space-2;
      &__l { font-size: $font-size-sm; color: $color-text; }
      &__bar {
        height: 8px; border-radius: $radius-pill; background: $color-bg-muted; overflow: hidden;
        span { display: block; height: 100%; background: #0D9488; border-radius: $radius-pill; }
      }
      &__v { font-size: $font-size-sm; font-weight: 700; color: $color-text; min-width: 32px; text-align: right; }
    }

    .geo-row { display: flex; gap: $space-5; margin-bottom: $space-2; }
    .geo-stat__v { display: block; font-size: 1.8rem; font-weight: 700; color: $color-primary; }
    .geo-stat__l { font-size: $font-size-xs; color: $color-text-muted; }
  `],
})
export class AnaliticaComponent implements OnInit, OnDestroy {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);

  @ViewChild('chartTendencia') private rTend?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartSexo') private rSexo?: ElementRef<HTMLCanvasElement>;
  private charts: Chart[] = [];

  maxOf(rows: { categoria: any; total: number }[]): number {
    return rows.length ? Math.max(...rows.map(r => r.total)) : 1;
  }

  pct(total: number, max: number): number {
    return max > 0 ? Math.round((total / max) * 100) : 0;
  }

  pctOfSum(total: number, rows: { categoria: any; total: number }[]): number {
    const sum = rows.reduce((s, r) => s + r.total, 0);
    return sum > 0 ? Math.round((total / sum) * 100) : 0;
  }

  loading = signal<boolean>(true);
  errorMsg = signal<string>('');
  data = signal<Analitica | null>(null);

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Consulta IA', url: '/ia' },
      { label: 'Analítica' },
    ]);
    this.http.get<Analitica>(this.cfg.url('/dashboard/api/ia/analitica')).subscribe({
      next: (d) => {
        this.data.set(d);
        this.loading.set(false);
        setTimeout(() => this.dibujar(d), 50);
      },
      error: () => { this.loading.set(false); this.errorMsg.set('No se pudo cargar el tablero.'); },
    });
  }

  ngOnDestroy(): void { this.charts.forEach(c => c.destroy()); }

  private doughnut(canvas: HTMLCanvasElement | undefined, rows: { categoria: any; total: number }[]): void {
    if (!canvas || !rows.length) return;
    this.charts.push(new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels: rows.map(r => String(r.categoria)),
        datasets: [{ data: rows.map(r => r.total), backgroundColor: rows.map((_, i) => PALETTE[i % PALETTE.length]), borderWidth: 2, borderColor: '#fff' }],
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } } } },
    }));
  }

  private dibujar(d: Analitica): void {
    this.charts.forEach(c => c.destroy());
    this.charts = [];
    // Tendencia (línea)
    if (this.rTend && d.tendencia.length) {
      this.charts.push(new Chart(this.rTend.nativeElement, {
        type: 'line',
        data: {
          labels: d.tendencia.map(t => t.mes),
          datasets: [{ data: d.tendencia.map(t => t.total), borderColor: '#D6001C', backgroundColor: 'rgba(214,0,28,0.12)', fill: true, tension: 0.3, pointRadius: 4 }],
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
      }));
    }
    this.doughnut(this.rSexo?.nativeElement, d.caracterizacion['sexo']);
  }
}
