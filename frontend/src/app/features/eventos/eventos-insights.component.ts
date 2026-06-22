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
const PAL = ['#D6001C', '#0D9488', '#2563eb', '#d97706', '#7c3aed', '#16a34a', '#db2777', '#0ea5e9', '#84cc16', '#64748b'];

@Component({
  standalone: true,
  selector: 'app-eventos-insights',
  imports: [CommonModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      <header class="page__header">
        <div><h1><i class="fa fa-chart-line"></i> Insights — Actividades</h1></div>
        <a routerLink="/eventos" class="ui-btn ui-btn--ghost ui-btn--sm"><i class="fa fa-arrow-left"></i> Ver lista</a>
      </header>

      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando…</div> }
      @else if (d()) { @if (d(); as i) {
        <div class="kpis">
          <article class="kpi"><span class="kpi__v">{{ i.total | number }}</span><span class="kpi__l">Actividades activas</span></article>
          <article class="kpi kpi--b"><span class="kpi__v">{{ i.proximos | number }}</span><span class="kpi__l">Próximas</span></article>
          <article class="kpi kpi--c"><span class="kpi__v">{{ i.en_curso | number }}</span><span class="kpi__l">En curso</span></article>
          <article class="kpi kpi--d"><span class="kpi__v">{{ i.ejecutados | number }}</span><span class="kpi__l">Ejecutadas</span></article>
        </div>

        <article class="card"><h3>Evolución mensual</h3><div class="cbox cbox--tall"><canvas #chartMes></canvas></div></article>

        <div class="grid2">
          <article class="card"><h3>Por tipo</h3><div class="cbox"><canvas #chartTipo></canvas></div></article>
          <article class="card"><h3>Por subgrupo</h3><div class="cbox"><canvas #chartSub></canvas></div></article>
        </div>

        <div class="grid2">
          <article class="card"><h3>Top funcionarios (carga)</h3><div class="cbox"><canvas #chartFunc></canvas></div></article>
          <article class="card">
            <h3>Calidad del dato</h3>
            <div class="cal"><span>Con KPI</span><div class="bar"><div class="bar__fill" [style.width.%]="i.pct_kpi"></div></div><b>{{ i.pct_kpi }}%</b></div>
            <div class="cal"><span>Con ubicación</span><div class="bar"><div class="bar__fill" [style.width.%]="i.pct_lugar"></div></div><b>{{ i.pct_lugar }}%</b></div>
            <div class="cal"><span>Caracterización</span><div class="bar"><div class="bar__fill" [style.width.%]="i.pct_caract"></div></div><b>{{ i.pct_caract }}%</b></div>
            @if (i.subgrupos_sin_proximos?.length) {
              <div class="alerta"><i class="fa fa-triangle-exclamation"></i> Sin actividades próximas:
                @for (s of i.subgrupos_sin_proximos; track s) { <span class="ui-badge ui-badge--warning">{{ s }}</span> }
              </div>
            }
          </article>
        </div>
      } }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1200px; margin: 0 auto; }
    .page__header { display: flex; justify-content: space-between; align-items: center; gap: $space-3; flex-wrap: wrap; margin-bottom: $space-4; h1 { margin: 0; color: $color-primary; } }
    .kpis { display: grid; grid-template-columns: repeat(4,1fr); gap: $space-3; margin-bottom: $space-4; @media (max-width: 700px){ grid-template-columns: repeat(2,1fr); } }
    .kpi { background: #fff; border: 1px solid $color-border; border-left: 5px solid $color-primary; border-radius: $radius-md; padding: $space-3; display: flex; flex-direction: column;
      &--b { border-left-color: #2563eb; } &--c { border-left-color: #16a34a; } &--d { border-left-color: #6b7280; }
      &__v { font-size: 1.8rem; font-weight: 700; line-height: 1; } &__l { font-size: $font-size-xs; color: $color-text-muted; } }
    .card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-4; margin-bottom: $space-4; h3 { margin: 0 0 $space-3; color: $color-primary; font-size: 1rem; } }
    .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: $space-4; margin-bottom: 0; @media (max-width: 800px){ grid-template-columns: 1fr; } }
    .grid2 .card { margin-bottom: $space-4; }
    .cbox { height: 250px; } .cbox--tall { height: 300px; }
    .cal { display: flex; align-items: center; gap: $space-2; margin-bottom: $space-2; span { width: 110px; font-size: $font-size-sm; color: $color-text-muted; } b { width: 48px; text-align: right; } }
    .bar { flex: 1; height: 10px; background: $color-bg-muted; border-radius: $radius-pill; overflow: hidden; }
    .bar__fill { height: 100%; background: $color-primary; transition: width .6s; }
    .alerta { margin-top: $space-3; display: flex; flex-wrap: wrap; gap: $space-1; align-items: center; color: $color-text-muted; font-size: $font-size-sm; i { color: #d97706; } }
  `],
})
export class EventosInsightsComponent implements OnInit, OnDestroy {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);
  @ViewChild('chartMes') private rM?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartTipo') private rT?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartSub') private rS?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartFunc') private rF?: ElementRef<HTMLCanvasElement>;
  private charts: Chart[] = [];

  loading = signal<boolean>(true);
  d = signal<any | null>(null);

  ngOnInit(): void {
    this.layout.setBreadcrumb([{ label: 'Inicio', url: '/' }, { label: 'Actividades', url: '/eventos' }, { label: 'Insights' }]);
    this.http.get<any>(this.cfg.url('/api/eventos/insights/')).subscribe({
      next: i => { this.d.set(i); this.loading.set(false); setTimeout(() => this.draw(i), 60); },
      error: () => this.loading.set(false),
    });
  }
  ngOnDestroy(): void { this.charts.forEach(c => c.destroy()); }

  private bar(c: HTMLCanvasElement | undefined, labels: string[], vals: number[]): void {
    if (!c || !labels.length) return;
    this.charts.push(new Chart(c, {
      type: 'bar',
      data: { labels, datasets: [{ data: vals, backgroundColor: labels.map((_, i) => PAL[i % PAL.length]), borderRadius: 4 }] },
      options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { precision: 0 } } } },
    }));
  }

  private draw(i: any): void {
    this.charts.forEach(c => c.destroy()); this.charts = [];
    if (this.rM && i.timeline?.length) this.charts.push(new Chart(this.rM.nativeElement, {
      type: 'line',
      data: { labels: i.timeline.map((t: any) => t.mes), datasets: [{ data: i.timeline.map((t: any) => t.c), borderColor: '#D6001C', backgroundColor: 'rgba(214,0,28,0.12)', fill: true, tension: 0.3, pointRadius: 3 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
    }));
    // por tipo con color del catálogo
    const pt = i.por_tipo || [];
    if (this.rT && pt.length) this.charts.push(new Chart(this.rT.nativeElement, {
      type: 'doughnut',
      data: { labels: pt.map((x: any) => x.tipo_evento__nombre || '—'), datasets: [{ data: pt.map((x: any) => x.c), backgroundColor: pt.map((x: any, idx: number) => x.tipo_evento__color || PAL[idx % PAL.length]), borderWidth: 2, borderColor: '#fff' }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } } } },
    }));
    this.bar(this.rS?.nativeElement, (i.por_subgrupo || []).map((x: any) => x.subgrupo__nombre || '—'), (i.por_subgrupo || []).map((x: any) => x.c));
    this.bar(this.rF?.nativeElement, (i.top_funcionarios || []).map((x: any) => x.nombre || '—'), (i.top_funcionarios || []).map((x: any) => x.c));
  }
}
