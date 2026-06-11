import { CommonModule } from '@angular/common';
import {
  AfterViewInit, Component, ElementRef, OnDestroy, QueryList, ViewChildren,
  inject, signal,
} from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Chart, registerables } from 'chart.js';
import { CapturaApi, CapturaInsights } from './captura.api';
import { LayoutService } from '../../core/layout/layout.service';

Chart.register(...registerables);
const PALETA = ['#D6001C', '#0D9488', '#B45309', '#7E22CE', '#2563EB', '#16A34A', '#DB2777', '#EA580C', '#0891B2', '#65A30D', '#9333EA', '#DC2626'];

@Component({
  standalone: true,
  selector: 'app-captura-insights',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header" style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;">
        <div>
          <h1><i class="fa fa-chart-pie"></i> Insights — {{ data()?.titulo || 'Capturas' }}</h1>
          <p class="page__subtitle">Distribución de registros capturados.</p>
        </div>
        <a [routerLink]="['/captura']" [queryParams]="{ tipo: tipo() }" class="ui-btn ui-btn--ghost ui-btn--sm"><i class="fa fa-arrow-left"></i> Registros</a>
      </header>

      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando…</div> }
      @else if (data()) {
        @let d = data()!;
        <div class="kpis">
          <article class="kpi kpi--primary"><span class="kpi__v">{{ d.total }}</span><span class="kpi__l">Total capturas</span></article>
          <article class="kpi kpi--ok"><span class="kpi__v">{{ d.validadas }}</span><span class="kpi__l">Validadas (suman al KPI)</span></article>
        </div>

        <div class="charts">
          <article class="card">
            <h2>Por estado</h2>
            <canvas #cv></canvas>
          </article>
          @for (dist of d.distribuciones; track dist.campo) {
            <article class="card">
              <h2>{{ dist.label }}</h2>
              <canvas #cv></canvas>
            </article>
          }
        </div>
        @if (!d.distribuciones.length && d.total === 0) {
          <div class="ui-empty-state"><i class="fa fa-chart-simple"></i><p>Aún no hay capturas para graficar.</p></div>
        }
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display:block; }
    .page { max-width:1200px; margin:0 auto; }
    .page__header h1 { margin:0; color:$color-primary; i{margin-right:$space-2;} }
    .page__subtitle { color:$color-text-muted; margin:$space-1 0 $space-3; }
    .kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:$space-3; margin-bottom:$space-4; }
    .kpi { background:$color-bg; border:1px solid $color-border; border-left:5px solid $color-primary; border-radius:$radius-md; padding:$space-4; display:flex; flex-direction:column;
      &--ok { border-left-color:#16a34a; } &__v{font-size:2rem;font-weight:700;line-height:1;} &__l{font-size:$font-size-xs;color:$color-text-muted;text-transform:uppercase;} }
    .charts { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:$space-3; }
    .card { background:$color-bg; border:1px solid $color-border; border-radius:$radius-lg; padding:$space-4; h2{margin:0 0 $space-3;font-size:$font-size-md;color:$color-primary;} canvas{max-height:280px;} }
  `],
})
export class CapturaInsightsComponent implements AfterViewInit, OnDestroy {
  private api = inject(CapturaApi);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);

  @ViewChildren('cv') canvases!: QueryList<ElementRef<HTMLCanvasElement>>;
  loading = signal(true);
  data = signal<CapturaInsights | null>(null);
  tipo = signal('');
  private charts: Chart[] = [];

  ngAfterViewInit(): void {
    this.layout.setBreadcrumb([{ label: 'Inicio', url: '/' }, { label: 'Actividades', url: '/actividades' }, { label: 'Insights capturas' }]);
    const tipo = this.route.snapshot.queryParamMap.get('tipo') || '';
    this.tipo.set(tipo);
    this.api.insights(tipo || undefined).subscribe({
      next: d => { this.data.set(d); this.loading.set(false); setTimeout(() => this.render(d), 0); },
      error: () => this.loading.set(false),
    });
    this.canvases.changes.subscribe(() => { const d = this.data(); if (d) this.render(d); });
  }

  private render(d: CapturaInsights): void {
    this.charts.forEach(c => c.destroy()); this.charts = [];
    const cvs = this.canvases.toArray();
    if (!cvs.length) return;
    // 0 = por estado (doughnut); resto = distribuciones (bar)
    const estados = d.por_estado;
    if (cvs[0]) {
      this.charts.push(new Chart(cvs[0].nativeElement, {
        type: 'doughnut',
        data: { labels: estados.map(e => e.label), datasets: [{ data: estados.map(e => e.valor), backgroundColor: PALETA }] },
        options: { responsive: true, plugins: { legend: { position: 'bottom' } } },
      }));
    }
    d.distribuciones.forEach((dist, i) => {
      const cv = cvs[i + 1];
      if (!cv) return;
      this.charts.push(new Chart(cv.nativeElement, {
        type: 'bar',
        data: { labels: dist.datos.map(x => x.label), datasets: [{ data: dist.datos.map(x => x.valor), backgroundColor: PALETA[i % PALETA.length] }] },
        options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
      }));
    });
  }

  ngOnDestroy(): void { this.charts.forEach(c => c.destroy()); }
}
