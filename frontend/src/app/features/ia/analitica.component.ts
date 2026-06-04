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
        <div>
          <h1><i class="fa fa-chart-line"></i> Analítica de Beneficiarios</h1>
          <p>Tablero de los beneficiarios de los productos de los proyectos.</p>
        </div>
        <a routerLink="/ia" class="ui-btn ui-btn--ghost ui-btn--sm">
          <i class="fa fa-wand-magic-sparkles"></i> Consulta IA
        </a>
      </header>

      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando tablero…</div> }
      @else if (errorMsg()) { <div class="ui-info-bar ui-info-bar--danger">{{ errorMsg() }}</div> }
      @else if (data()) {
        @if (data(); as d) {
        <!-- KPIs -->
        <div class="kpis">
          <article class="kpi kpi--a"><span class="kpi__v">{{ d.kpis.beneficiarios | number }}</span><span class="kpi__l">Beneficiarios</span></article>
          <article class="kpi kpi--b"><span class="kpi__v">{{ d.kpis.eventos | number }}</span><span class="kpi__l">Actividades</span></article>
          <article class="kpi kpi--c"><span class="kpi__v">{{ d.kpis.areas | number }}</span><span class="kpi__l">Áreas activas</span></article>
          <article class="kpi kpi--d"><span class="kpi__v">{{ d.caracterizados | number }}</span><span class="kpi__l">Caracterizados</span></article>
        </div>

        <!-- Tendencia (ancho completo) -->
        <article class="card card--wide">
          <h3>Tendencia mensual de beneficiarios</h3>
          <div class="cbox cbox--tall"><canvas #chartTendencia></canvas></div>
        </article>

        <div class="grid2">
          <article class="card">
            <h3>Beneficiarios por área</h3>
            <div class="cbox"><canvas #chartArea></canvas></div>
          </article>
          <article class="card">
            <h3>Escenarios / actividades más usados</h3>
            <div class="cbox"><canvas #chartEscenarios></canvas></div>
          </article>
        </div>

        <div class="grid3">
          <article class="card">
            <h3>Por sexo</h3>
            @if (d.caracterizacion['sexo'].length) { <div class="cbox"><canvas #chartSexo></canvas></div> }
            @else { <p class="empty">Sin caracterización de sexo.</p> }
          </article>
          <article class="card">
            <h3>Por estrato</h3>
            @if (d.caracterizacion['estrato'].length) { <div class="cbox"><canvas #chartEstrato></canvas></div> }
            @else { <p class="empty">Sin datos de estrato.</p> }
          </article>
          <article class="card">
            <h3>Por nivel educativo</h3>
            @if (d.caracterizacion['nivel_educativo'].length) { <div class="cbox"><canvas #chartNivel></canvas></div> }
            @else { <p class="empty">Sin datos de educación.</p> }
          </article>
        </div>

        <!-- Geo / ubicación -->
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
        }
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .an { max-width: 1300px; margin: 0 auto; display: flex; flex-direction: column; gap: $space-4; }
    .an__hero {
      background: linear-gradient(135deg, $color-primary, $color-primary-dark);
      color: #fff; border-radius: $radius-lg; padding: $space-4;
      display: flex; justify-content: space-between; align-items: center; gap: $space-3; flex-wrap: wrap;
      h1 { margin: 0; display: flex; align-items: center; gap: $space-2; }
      p { margin: $space-1 0 0; opacity: 0.9; }
    }
    .kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: $space-3;
      @media (max-width: 700px) { grid-template-columns: repeat(2, 1fr); } }
    .kpi { background: #fff; border: 1px solid $color-border; border-left: 5px solid $color-primary;
      border-radius: $radius-md; padding: $space-3; display: flex; flex-direction: column;
      transition: transform .15s; &:hover { transform: translateY(-2px); }
      &--b { border-left-color: #0D9488; } &--c { border-left-color: #2563eb; } &--d { border-left-color: #d97706; }
      &__v { font-size: 2rem; font-weight: 800; color: $color-text; line-height: 1; }
      &__l { font-size: $font-size-xs; color: $color-text-muted; text-transform: uppercase; letter-spacing: .04em; } }
    .card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-4;
      h3 { margin: 0 0 $space-3; color: $color-primary; font-size: 1rem; } }
    .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: $space-4; @media (max-width: 900px) { grid-template-columns: 1fr; } }
    .grid3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: $space-4; @media (max-width: 900px) { grid-template-columns: 1fr; } }
    .cbox { height: 260px; } .cbox--tall { height: 300px; }
    .empty { color: $color-text-muted; font-size: $font-size-sm; padding: $space-3 0; }
    .geo-row { display: flex; gap: $space-5; margin-bottom: $space-2; }
    .geo-stat__v { display: block; font-size: 1.8rem; font-weight: 700; color: $color-primary; }
    .geo-stat__l { font-size: $font-size-xs; color: $color-text-muted; text-transform: uppercase; }
  `],
})
export class AnaliticaComponent implements OnInit, OnDestroy {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);

  @ViewChild('chartTendencia') private rTend?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartArea') private rArea?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartEscenarios') private rEsc?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartSexo') private rSexo?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartEstrato') private rEstr?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartNivel') private rNivel?: ElementRef<HTMLCanvasElement>;
  private charts: Chart[] = [];

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

  private bar(canvas: HTMLCanvasElement | undefined, rows: { categoria: any; total: number }[], horizontal = false): void {
    if (!canvas || !rows.length) return;
    this.charts.push(new Chart(canvas, {
      type: 'bar',
      data: {
        labels: rows.map(r => String(r.categoria)),
        datasets: [{ data: rows.map(r => r.total), backgroundColor: rows.map((_, i) => PALETTE[i % PALETTE.length]), borderRadius: 4 }],
      },
      options: {
        indexAxis: horizontal ? 'y' : 'x', responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { [horizontal ? 'x' : 'y']: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    }));
  }

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
    this.bar(this.rArea?.nativeElement, d.por_area, true);
    this.bar(this.rEsc?.nativeElement, d.escenarios, true);
    this.doughnut(this.rSexo?.nativeElement, d.caracterizacion['sexo']);
    this.bar(this.rEstr?.nativeElement, d.caracterizacion['estrato']);
    this.bar(this.rNivel?.nativeElement, d.caracterizacion['nivel_educativo'], true);
  }
}
