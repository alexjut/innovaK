import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, ElementRef, OnDestroy, OnInit,
  ViewChild, inject, signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { Chart, registerables } from 'chart.js';
import { CursosApi } from './cursos.api';
import { CursosInsights } from './cursos.types';
import { LayoutService } from '../../core/layout/layout.service';

Chart.register(...registerables);
const PAL = ['#D6001C', '#0D9488', '#2563eb', '#d97706', '#7c3aed', '#16a34a', '#db2777', '#0ea5e9', '#84cc16', '#64748b'];

@Component({
  standalone: true,
  selector: 'app-cursos-insights',
  imports: [CommonModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      <header class="page__header">
        <div><h1><i class="fa fa-chart-line"></i> Insights — Cursos y capacitaciones</h1></div>
        <a routerLink="/cursos" class="ui-btn ui-btn--ghost ui-btn--sm"><i class="fa fa-arrow-left"></i> Mis cursos</a>
      </header>

      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando…</div> }
      @else if (d()) { @if (d(); as i) {
        <div class="kpis">
          <article class="kpi"><span class="kpi__v">{{ i.kpis.total_cursos | number }}</span><span class="kpi__l">Cursos activos</span></article>
          <article class="kpi kpi--b"><span class="kpi__v">{{ i.kpis.inscritos | number }}</span><span class="kpi__l">Inscritos</span></article>
          <article class="kpi kpi--c"><span class="kpi__v">{{ i.kpis.en_espera | number }}</span><span class="kpi__l">En lista de espera</span></article>
          <article class="kpi kpi--d"><span class="kpi__v">{{ i.kpis.sesiones_total | number }}</span><span class="kpi__l">Sesiones planeadas</span></article>
          <article class="kpi kpi--e"><span class="kpi__v">{{ i.kpis.pct_asistencia == null ? '—' : i.kpis.pct_asistencia + '%' }}</span><span class="kpi__l">Asistencia promedio</span></article>
          <article class="kpi kpi--f"><span class="kpi__v">{{ i.kpis.suplencias | number }}</span><span class="kpi__l">Sesiones con suplente</span></article>
        </div>

        @if (i.kpis.cursos_sin_docente > 0) {
          <div class="ui-info-bar ui-info-bar--warning">
            <i class="fa fa-triangle-exclamation"></i>
            {{ i.kpis.cursos_sin_docente }} curso(s) sin docente asignado.
          </div>
        }

        <article class="card"><h3>Cursos iniciados por mes</h3><div class="cbox cbox--tall"><canvas #chartMes></canvas></div></article>

        <div class="grid2">
          <article class="card"><h3>Cursos por área (subgrupo)</h3><div class="cbox"><canvas #chartSub></canvas></div></article>
          <article class="card"><h3>Estado de los cursos</h3><div class="cbox"><canvas #chartEstado></canvas></div></article>
        </div>

        <div class="grid2">
          <article class="card"><h3>Top docentes (carga)</h3>
            @if (i.top_docentes?.length) {
              <div class="cbox"><canvas #chartDoc></canvas></div>
            } @else {
              <div class="ui-empty-state">Sin datos de docentes aún.</div>
            }
          </article>
          <article class="card"><h3>Distribución de notas (escala 0–5 SED)</h3><div class="cbox"><canvas #chartNotas></canvas></div></article>
        </div>

        <article class="card">
          <h3>Calidad del dato</h3>
          <div class="cal"><span>Con docente</span><div class="bar"><div class="bar__fill" [style.width.%]="i.calidad.pct_con_docente"></div></div><b>{{ i.calidad.pct_con_docente }}%</b></div>
          <div class="cal"><span>Con sesiones</span><div class="bar"><div class="bar__fill" [style.width.%]="i.calidad.pct_con_sesiones"></div></div><b>{{ i.calidad.pct_con_sesiones }}%</b></div>
          <div class="cal"><span>Con cupo</span><div class="bar"><div class="bar__fill" [style.width.%]="i.calidad.pct_con_cupo"></div></div><b>{{ i.calidad.pct_con_cupo }}%</b></div>
        </article>
      } }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1200px; margin: 0 auto; }
    .page__header { display: flex; justify-content: space-between; align-items: center; gap: $space-3; flex-wrap: wrap; margin-bottom: $space-4; h1 { margin: 0; color: $color-primary; } }
    .kpis { display: grid; grid-template-columns: repeat(6,1fr); gap: $space-3; margin-bottom: $space-4; @media (max-width: 900px){ grid-template-columns: repeat(3,1fr); } @media (max-width: 560px){ grid-template-columns: repeat(2,1fr); } }
    .kpi { background: #fff; border: 1px solid $color-border; border-left: 5px solid $color-primary; border-radius: $radius-md; padding: $space-3; display: flex; flex-direction: column;
      &--b { border-left-color: #2563eb; } &--c { border-left-color: #d97706; } &--d { border-left-color: #0D9488; } &--e { border-left-color: #16a34a; } &--f { border-left-color: #7c3aed; }
      &__v { font-size: 1.6rem; font-weight: 700; line-height: 1; } &__l { font-size: $font-size-xs; color: $color-text-muted; margin-top: 2px; } }
    .card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-4; margin-bottom: $space-4; h3 { margin: 0 0 $space-3; color: $color-primary; font-size: 1rem; } }
    .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: $space-4; @media (max-width: 800px){ grid-template-columns: 1fr; } }
    .cbox { height: 250px; } .cbox--tall { height: 300px; }
    .cal { display: flex; align-items: center; gap: $space-2; margin-bottom: $space-2; span { width: 110px; font-size: $font-size-sm; color: $color-text-muted; } b { width: 48px; text-align: right; } }
    .bar { flex: 1; height: 10px; background: $color-bg-muted; border-radius: $radius-pill; overflow: hidden; }
    .bar__fill { height: 100%; background: $color-primary; transition: width .6s; }
  `],
})
export class CursosInsightsComponent implements OnInit, OnDestroy {
  private api = inject(CursosApi);
  private layout = inject(LayoutService);
  @ViewChild('chartMes') private rMes?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartSub') private rSub?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartEstado') private rEstado?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartDoc') private rDoc?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartNotas') private rNotas?: ElementRef<HTMLCanvasElement>;
  private charts: Chart[] = [];

  loading = signal<boolean>(true);
  d = signal<CursosInsights | null>(null);

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Mis cursos', url: '/cursos' },
      { label: 'Insights' },
    ]);
    this.api.insights().subscribe({
      next: (i) => { this.d.set(i); this.loading.set(false); setTimeout(() => this.draw(i), 60); },
      error: () => this.loading.set(false),
    });
  }
  ngOnDestroy(): void { this.charts.forEach((c) => c.destroy()); }

  private barH(c: HTMLCanvasElement | undefined, labels: string[], vals: number[]): void {
    if (!c || !labels.length) return;
    this.charts.push(new Chart(c, {
      type: 'bar',
      data: { labels, datasets: [{ data: vals, backgroundColor: labels.map((_, i) => PAL[i % PAL.length]), borderRadius: 4 }] },
      options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { precision: 0 } } } },
    }));
  }

  private draw(i: CursosInsights): void {
    this.charts.forEach((c) => c.destroy()); this.charts = [];

    if (this.rMes && i.timeline?.length) {
      this.charts.push(new Chart(this.rMes.nativeElement, {
        type: 'line',
        data: { labels: i.timeline.map((t) => t.mes), datasets: [{ data: i.timeline.map((t) => t.cursos), borderColor: '#D6001C', backgroundColor: 'rgba(214,0,28,0.12)', fill: true, tension: 0.3, pointRadius: 3 }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
      }));
    }

    this.barH(this.rSub?.nativeElement, (i.por_subgrupo || []).map((x) => x.subgrupo), (i.por_subgrupo || []).map((x) => x.cursos));
    this.barH(this.rDoc?.nativeElement, (i.top_docentes || []).map((x) => x.nombre), (i.top_docentes || []).map((x) => x.cursos));

    if (this.rEstado) {
      const e = i.por_estado;
      this.charts.push(new Chart(this.rEstado.nativeElement, {
        type: 'doughnut',
        data: {
          labels: ['Próximos', 'En curso', 'Finalizados', 'Sin fecha'],
          datasets: [{ data: [e.proximos, e.en_curso, e.finalizados, e.sin_fecha], backgroundColor: ['#2563eb', '#16a34a', '#64748b', '#d97706'], borderWidth: 2, borderColor: '#fff' }],
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 11 } } } } },
      }));
    }

    if (this.rNotas) {
      const n = i.notas;
      this.charts.push(new Chart(this.rNotas.nativeElement, {
        type: 'bar',
        data: {
          labels: ['Reprobado (0–2.9)', 'Básico (3–3.9)', 'Alto (4–4.4)', 'Superior (4.5–5)', 'Sin nota'],
          datasets: [{ data: [n.reprobado_0_2_9, n.basico_3_3_9, n.alto_4_4_4, n.superior_4_5_5, n.sin_nota], backgroundColor: ['#D6001C', '#d97706', '#0D9488', '#16a34a', '#cbd5e1'], borderRadius: 4 }],
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
      }));
    }
  }
}
