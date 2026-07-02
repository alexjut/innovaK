import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, ElementRef, OnDestroy, OnInit,
  ViewChild, inject, signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { Chart, registerables } from 'chart.js';
import { LayoutService } from '../../core/layout/layout.service';
import { BancoApi } from './banco.api';

Chart.register(...registerables);
const PAL = ['#D6001C', '#0D9488', '#2563eb', '#d97706', '#7c3aed', '#16a34a', '#db2777', '#0ea5e9'];

@Component({
  standalone: true,
  selector: 'app-banco-insights',
  imports: [CommonModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      <header class="page__header">
        <div><h1><i class="fa fa-chart-pie"></i> Insights — Banco de Iniciativas</h1></div>
        <a routerLink="/banco" class="ui-btn ui-btn--ghost ui-btn--sm"><i class="fa fa-arrow-left"></i> Listado</a>
      </header>

      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando…</div> }
      @else if (d()) { @if (d(); as i) {
        <div class="kpis">
          <article class="kpi"><span class="kpi__v">{{ i.total | number }}</span><span class="kpi__l">Inscripciones</span></article>
          <article class="kpi kpi--b"><span class="kpi__v">{{ i.meta | number }}</span><span class="kpi__l">Meta convocatoria</span></article>
          <article class="kpi kpi--c"><span class="kpi__v">{{ i.avance_pct | number:'1.0-1' }}%</span><span class="kpi__l">Avance</span></article>
          <article class="kpi kpi--d"><span class="kpi__v">{{ i.pct_validacion | number:'1.0-1' }}%</span><span class="kpi__l">Validación</span></article>
        </div>
        <div class="grid2">
          <article class="card"><h3>Estado (embudo)</h3><div class="cbox"><canvas #chartFunnel></canvas></div></article>
          <article class="card"><h3>Por UPL</h3><div class="cbox"><canvas #chartUpl></canvas></div></article>
        </div>
        <div class="grid2">
          <article class="card"><h3>Top disciplinas</h3><div class="cbox"><canvas #chartDisc></canvas></div></article>
          <article class="card"><h3>Top enfoques diferenciales</h3><div class="cbox"><canvas #chartEnf></canvas></div></article>
        </div>

        <!-- ── Puntaje y ranking (motor v3) ───────────────────────────── -->
        @if (i.puntaje; as p) {
          <h2 class="section-title"><i class="fa fa-ranking-star"></i> Puntaje y ranking</h2>
          <div class="kpis">
            <article class="kpi kpi--score"><span class="kpi__v">{{ p.n_puntuadas | number }}<small>/ {{ i.total | number }}</small></span><span class="kpi__l">Calificadas por comité</span></article>
            <article class="kpi kpi--score"><span class="kpi__v">{{ p.promedio_total | number:'1.0-1' }}<small>/105</small></span><span class="kpi__l">Promedio</span></article>
            <article class="kpi kpi--score"><span class="kpi__v">{{ p.max_total | number:'1.0-1' }}<small>/105</small></span><span class="kpi__l">Mayor puntaje</span></article>
            <article class="kpi kpi--score"><span class="kpi__v">{{ p.min_total | number:'1.0-1' }}<small>/105</small></span><span class="kpi__l">Menor puntaje</span></article>
          </div>
          <div class="grid2">
            <article class="card"><h3>Distribución de puntajes</h3><div class="cbox"><canvas #chartDist></canvas></div></article>
            <article class="card"><h3>Calificadas vs pendientes</h3><div class="cbox"><canvas #chartPend></canvas></div></article>
          </div>
          <div class="grid1">
            <article class="card"><h3>Top 10 ranking</h3><div class="cbox cbox--tall"><canvas #chartTop></canvas></div></article>
          </div>
        }
      } }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1200px; margin: 0 auto; }
    .page__header { display: flex; justify-content: space-between; align-items: center; gap: $space-3; flex-wrap: wrap; margin-bottom: $space-4;
      h1 { margin: 0; color: $color-primary; } }
    .kpis { display: grid; grid-template-columns: repeat(4,1fr); gap: $space-3; margin-bottom: $space-4; @media (max-width: 700px){ grid-template-columns: repeat(2,1fr); } }
    .kpi { background: #fff; border: 1px solid $color-border; border-left: 5px solid $color-primary; border-radius: $radius-md; padding: $space-3; display: flex; flex-direction: column;
      &--b { border-left-color: #0D9488; } &--c { border-left-color: #2563eb; } &--d { border-left-color: #d97706; } &--score { border-left-color: #7c3aed; }
      &__v { font-size: 1.8rem; font-weight: 700; line-height: 1; small { font-size: .9rem; font-weight: 600; color: $color-text-muted; margin-left: 4px; } } &__l { font-size: $font-size-xs; color: $color-text-muted; } }
    .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: $space-4; margin-bottom: $space-4; @media (max-width: 800px){ grid-template-columns: 1fr; } }
    .grid1 { display: grid; grid-template-columns: 1fr; gap: $space-4; margin-bottom: $space-4; }
    .card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-4; h3 { margin: 0 0 $space-3; color: $color-primary; font-size: 1rem; } }
    .cbox { height: 250px; }
    .cbox--tall { height: 360px; }
    .section-title { margin: $space-4 0 $space-3; color: $color-primary; font-size: 1.15rem; display: flex; align-items: center; gap: $space-2; i { color: #7c3aed; } }
  `],
})
export class BancoInsightsComponent implements OnInit, OnDestroy {
  private api = inject(BancoApi);
  private layout = inject(LayoutService);
  @ViewChild('chartFunnel') private rF?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartUpl') private rU?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartDisc') private rD?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartEnf') private rE?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartDist') private rDist?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartPend') private rPend?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartTop') private rTop?: ElementRef<HTMLCanvasElement>;
  private charts: Chart[] = [];

  loading = signal<boolean>(true);
  d = signal<any | null>(null);

  ngOnInit(): void {
    this.layout.setBreadcrumb([{ label: 'Inicio', url: '/' }, { label: 'Banco de Iniciativas', url: '/banco' }, { label: 'Insights' }]);
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
    this.bar(this.rU?.nativeElement, (i.por_upl || []).map((x: any) => x.upl__nombre || x.upl__codigo), (i.por_upl || []).map((x: any) => x.c));
    this.bar(this.rD?.nativeElement, (i.top_disciplinas || []).map((x: any) => x.disciplina_principal__nombre), (i.top_disciplinas || []).map((x: any) => x.c));
    this.bar(this.rE?.nativeElement, (i.top_enfoques || []).map((x: any) => x.enfoque__nombre), (i.top_enfoques || []).map((x: any) => x.c));

    // ── Puntaje / ranking ──────────────────────────────────────────────
    const dist = i.distribucion_puntaje || [];
    if (this.rDist && dist.length) this.charts.push(new Chart(this.rDist.nativeElement, {
      type: 'bar',
      data: { labels: dist.map((x: any) => x.rango), datasets: [{ label: 'Inscripciones', data: dist.map((x: any) => x.n), backgroundColor: dist.map((_: any, k: number) => PAL[k % PAL.length]), borderRadius: 4 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } }, x: { title: { display: true, text: 'Rango de puntaje (0–105)' } } } },
    }));

    const p = i.puntaje || { n_puntuadas: 0, n_pendientes: 0 };
    if (this.rPend) this.charts.push(new Chart(this.rPend.nativeElement, {
      type: 'doughnut',
      data: { labels: ['Calificadas', 'Pendientes'], datasets: [{ data: [p.n_puntuadas || 0, p.n_pendientes || 0], backgroundColor: ['#16a34a', '#94a3b8'], borderWidth: 2, borderColor: '#fff' }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } } } },
    }));

    const top = i.top_ranking || [];
    if (this.rTop && top.length) this.charts.push(new Chart(this.rTop.nativeElement, {
      type: 'bar',
      data: {
        labels: top.map((x: any) => `#${x.pos} ${x.organizacion}`),
        datasets: [{ label: 'Puntaje total', data: top.map((x: any) => x.total ?? 0), backgroundColor: '#7c3aed', borderRadius: 4 }],
      },
      options: {
        indexAxis: 'y', responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx: any) => { const r = top[ctx.dataIndex]; return `Total ${r.total ?? 0} (auto ${r.auto ?? 0} · comité ${r.comite ?? 0} · bono ${r.bono ?? 0})`; } } } },
        scales: { x: { beginAtZero: true, max: 105, ticks: { precision: 0 } } },
      },
    }));
  }
}
