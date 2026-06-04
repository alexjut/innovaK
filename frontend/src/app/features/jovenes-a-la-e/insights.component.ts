import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, ElementRef, OnDestroy, OnInit,
  ViewChild, inject, signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { Chart, registerables } from 'chart.js';
import { LayoutService } from '../../core/layout/layout.service';
import { JovenesApi } from './jovenes.api';

Chart.register(...registerables);
const PAL = ['#D6001C', '#0D9488', '#2563eb', '#d97706', '#7c3aed', '#16a34a', '#db2777', '#0ea5e9'];

@Component({
  standalone: true,
  selector: 'app-jovenes-insights',
  imports: [CommonModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      <header class="page__header">
        <div><h1><i class="fa fa-chart-pie"></i> Insights — Jóvenes a la E</h1></div>
        <a routerLink="/jovenes" class="ui-btn ui-btn--ghost ui-btn--sm"><i class="fa fa-arrow-left"></i> Listado</a>
      </header>

      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando…</div> }
      @else if (d()) { @if (d(); as i) {
        <div class="kpis">
          <article class="kpi"><span class="kpi__v">{{ i.total | number }}</span><span class="kpi__l">Entregas</span></article>
          <article class="kpi kpi--c"><span class="kpi__v">{{ i.cumplimiento?.acceso | number }}<small> / {{ i.meta_acceso }}</small></span><span class="kpi__l">Acceso (23771)</span></article>
          <article class="kpi kpi--b"><span class="kpi__v">{{ i.cumplimiento?.permanencia | number }}<small> / {{ i.meta_permanencia }}</small></span><span class="kpi__l">Permanencia (23772)</span></article>
          <article class="kpi kpi--d"><span class="kpi__v">{{ i.pct_validacion | number:'1.0-1' }}%</span><span class="kpi__l">Validación</span></article>
        </div>
        <div class="grid2">
          <article class="card"><h3>Estado (embudo)</h3><div class="cbox"><canvas #chartFunnel></canvas></div></article>
          <article class="card"><h3>Por nivel de formación</h3><div class="cbox"><canvas #chartNivel></canvas></div></article>
        </div>
        <div class="grid2">
          <article class="card"><h3>Por UPL</h3><div class="cbox"><canvas #chartUpl></canvas></div></article>
          <article class="card"><h3>Top elementos entregados</h3><div class="cbox"><canvas #chartElem></canvas></div></article>
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
      &--b { border-left-color: #0D9488; } &--c { border-left-color: #2563eb; } &--d { border-left-color: #d97706; }
      &__v { font-size: 1.7rem; font-weight: 700; line-height: 1; small { font-size: .9rem; color: $color-text-muted; } } &__l { font-size: $font-size-xs; color: $color-text-muted; text-transform: uppercase; } }
    .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: $space-4; margin-bottom: $space-4; @media (max-width: 800px){ grid-template-columns: 1fr; } }
    .card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-4; h3 { margin: 0 0 $space-3; color: $color-primary; font-size: 1rem; } }
    .cbox { height: 250px; }
  `],
})
export class JovenesInsightsComponent implements OnInit, OnDestroy {
  private api = inject(JovenesApi);
  private layout = inject(LayoutService);
  @ViewChild('chartFunnel') private rF?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartNivel') private rN?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartUpl') private rU?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartElem') private rE?: ElementRef<HTMLCanvasElement>;
  private charts: Chart[] = [];

  loading = signal<boolean>(true);
  d = signal<any | null>(null);

  ngOnInit(): void {
    this.layout.setBreadcrumb([{ label: 'Inicio', url: '/' }, { label: 'Jóvenes a la E', url: '/jovenes' }, { label: 'Insights' }]);
    this.api.insights().subscribe({
      next: (i: any) => { this.d.set(i); this.loading.set(false); setTimeout(() => this.draw(i), 60); },
      error: () => this.loading.set(false),
    });
  }
  ngOnDestroy(): void { this.charts.forEach(c => c.destroy()); }

  private bar(c: HTMLCanvasElement | undefined, labels: string[], vals: number[], horiz = true): void {
    if (!c || !labels.length) return;
    this.charts.push(new Chart(c, {
      type: 'bar',
      data: { labels, datasets: [{ data: vals, backgroundColor: labels.map((_, i) => PAL[i % PAL.length]), borderRadius: 4 }] },
      options: { indexAxis: horiz ? 'y' : 'x', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { [horiz ? 'x' : 'y']: { beginAtZero: true, ticks: { precision: 0 } } } },
    }));
  }

  private draw(i: any): void {
    this.charts.forEach(c => c.destroy()); this.charts = [];
    const f = i.funnel || {};
    if (this.rF) this.charts.push(new Chart(this.rF.nativeElement, {
      type: 'doughnut',
      data: { labels: ['Borrador', 'Enviada', 'Validada', 'Rechazada'], datasets: [{ data: [f.borrador || 0, f.enviada || 0, f.validada || 0, f.rechazada || 0], backgroundColor: ['#94a3b8', '#2563eb', '#16a34a', '#dc2626'], borderWidth: 2, borderColor: '#fff' }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } } } },
    }));
    this.bar(this.rN?.nativeElement, (i.por_nivel || []).map((x: any) => x.nivel_formacion || x.categoria || '—'), (i.por_nivel || []).map((x: any) => x.c ?? x.total));
    this.bar(this.rU?.nativeElement, (i.por_upl || []).map((x: any) => x.upl__nombre || x.upl__codigo || '—'), (i.por_upl || []).map((x: any) => x.c ?? x.total));
    this.bar(this.rE?.nativeElement, (i.top_elementos || []).map((x: any) => x.elemento__nombre || x.nombre || '—'), (i.top_elementos || []).map((x: any) => x.c ?? x.total));
  }
}
