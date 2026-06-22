import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, ElementRef, OnDestroy, OnInit,
  ViewChild, inject, signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { Chart, registerables } from 'chart.js';
import { LayoutService } from '../../core/layout/layout.service';
import { formatMoneda } from '../../shared/format/format.util';
import { InfraestructuraApi } from './infraestructura.api';
import { InfraInsights } from './infraestructura.types';

Chart.register(...registerables);
const PAL = ['#2563eb', '#0D9488', '#d97706', '#7c3aed', '#16a34a', '#db2777', '#0ea5e9', '#84cc16', '#64748b', '#D6001C'];

/**
 * Dashboard de insights de Infraestructura (Chart.js): KPIs + doughnut de
 * tramos por estado, barras de avance por contrato y valor por categoría.
 * Empty states cuando no hay datos.
 */
@Component({
  standalone: true,
  selector: 'app-infra-insights',
  imports: [CommonModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      <header class="page__header">
        <div><h1><i class="fa fa-chart-line"></i> Insights — Infraestructura</h1></div>
        <a routerLink="/infraestructura" class="ui-btn ui-btn--ghost ui-btn--sm">
          <i class="fa fa-arrow-left"></i> Contratos
        </a>
      </header>

      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando…</div> }
      @else {
        @if (d(); as i) {
        <div class="kpis">
          <article class="kpi"><span class="kpi__v">{{ i.kpis.n_contratos | number }}</span><span class="kpi__l">Contratos</span></article>
          <article class="kpi kpi--b"><span class="kpi__v">{{ moneda(i.kpis.valor_total) }}</span><span class="kpi__l">Valor total</span></article>
          <article class="kpi kpi--c"><span class="kpi__v">{{ i.kpis.n_tramos | number }}</span><span class="kpi__l">Tramos viales</span></article>
          <article class="kpi kpi--d"><span class="kpi__v">{{ i.kpis.tramos_terminados | number }}</span><span class="kpi__l">Tramos terminados</span></article>
          <article class="kpi kpi--e"><span class="kpi__v">{{ i.kpis.pct_tramos_terminados }}%</span><span class="kpi__l">% Tramos terminados</span></article>
          <article class="kpi kpi--f"><span class="kpi__v">{{ i.kpis.n_parques | number }}</span><span class="kpi__l">Parques</span></article>
        </div>

        @if (i.kpis.geo_pendientes > 0) {
          <div class="ui-info-bar ui-info-bar--warning">
            <i class="fa fa-triangle-exclamation"></i>
            {{ i.kpis.geo_pendientes }} tramo(s) sin geometría resuelta — no salen en el mapa todavía.
          </div>
        }

        <div class="grid2">
          <article class="card">
            <h3>Tramos por estado de avance</h3>
            @if (i.kpis.n_tramos > 0) {
              <div class="cbox"><canvas #chartEstado></canvas></div>
            } @else {
              <div class="ui-empty-state ui-empty-state--sm"><i class="fa fa-road"></i><p>Aún no hay tramos viales.</p></div>
            }
          </article>
          <article class="card">
            <h3>Valor por categoría</h3>
            @if (i.valor_por_categoria.length > 0) {
              <div class="cbox"><canvas #chartCat></canvas></div>
            } @else {
              <div class="ui-empty-state ui-empty-state--sm"><i class="fa fa-coins"></i><p>Sin valores registrados.</p></div>
            }
          </article>
        </div>

        <article class="card">
          <h3>Avance por contrato</h3>
          @if (i.avance_por_contrato.length > 0) {
            <div class="cbox cbox--tall"><canvas #chartAvance></canvas></div>
          } @else {
            <div class="ui-empty-state ui-empty-state--sm"><i class="fa fa-file-contract"></i><p>No hay contratos para graficar.</p></div>
          }
        </article>
        } @else {
          <div class="ui-info-bar ui-info-bar--danger">No se pudieron cargar los insights.</div>
        }
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1200px; margin: 0 auto; }
    .page__header { display: flex; justify-content: space-between; align-items: center; gap: $space-3; flex-wrap: wrap; margin-bottom: $space-4; h1 { margin: 0; color: $color-primary; } }
    .kpis { display: grid; grid-template-columns: repeat(6,1fr); gap: $space-3; margin-bottom: $space-4; @media (max-width: 900px){ grid-template-columns: repeat(3,1fr); } @media (max-width: 560px){ grid-template-columns: repeat(2,1fr); } }
    .kpi { background: #fff; border: 1px solid $color-border; border-left: 5px solid $color-primary; border-radius: $radius-md; padding: $space-3; display: flex; flex-direction: column;
      &--b { border-left-color: #16a34a; } &--c { border-left-color: #2563eb; } &--d { border-left-color: #0D9488; } &--e { border-left-color: #7c3aed; } &--f { border-left-color: #d97706; }
      &__v { font-size: 1.4rem; font-weight: 700; line-height: 1.1; } &__l { font-size: $font-size-xs; color: $color-text-muted; margin-top: 2px; } }
    .card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-4; margin-bottom: $space-4; h3 { margin: 0 0 $space-3; color: $color-primary; font-size: 1rem; } }
    .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: $space-4; @media (max-width: 800px){ grid-template-columns: 1fr; } }
    .cbox { height: 260px; } .cbox--tall { height: 320px; }
  `],
})
export class InfraInsightsComponent implements OnInit, OnDestroy {
  private api = inject(InfraestructuraApi);
  private layout = inject(LayoutService);
  @ViewChild('chartEstado') private rEstado?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartCat') private rCat?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartAvance') private rAvance?: ElementRef<HTMLCanvasElement>;
  private charts: Chart[] = [];

  loading = signal<boolean>(true);
  d = signal<InfraInsights | null>(null);

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Infraestructura', url: '/infraestructura' },
      { label: 'Insights' },
    ]);
    this.api.insights().subscribe({
      next: (i) => { this.d.set(i); this.loading.set(false); setTimeout(() => this.draw(i), 60); },
      error: () => this.loading.set(false),
    });
  }

  ngOnDestroy(): void { this.charts.forEach((c) => c.destroy()); }

  moneda(v: unknown): string { return formatMoneda(v); }

  private draw(i: InfraInsights): void {
    this.charts.forEach((c) => c.destroy()); this.charts = [];

    // Doughnut: tramos por estado (rojo / naranja / verde).
    if (this.rEstado && i.kpis.n_tramos > 0) {
      const e = i.tramos_por_estado;
      this.charts.push(new Chart(this.rEstado.nativeElement, {
        type: 'doughnut',
        data: {
          labels: ['Sin iniciar', 'En ejecución', 'Terminado'],
          datasets: [{
            data: [e.sin_iniciar, e.parcial, e.terminado],
            backgroundColor: ['#dc2626', '#f59e0b', '#16a34a'],
            borderWidth: 2, borderColor: '#fff',
          }],
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 11 } } } } },
      }));
    }

    // Barras horizontales: valor por categoría.
    if (this.rCat && i.valor_por_categoria.length) {
      this.charts.push(new Chart(this.rCat.nativeElement, {
        type: 'bar',
        data: {
          labels: i.valor_por_categoria.map((x) => x.categoria),
          datasets: [{ data: i.valor_por_categoria.map((x) => x.valor), backgroundColor: i.valor_por_categoria.map((_, k) => PAL[k % PAL.length]), borderRadius: 4 }],
        },
        options: {
          indexAxis: 'y', responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx) => this.moneda(ctx.parsed.x) } } },
          scales: { x: { beginAtZero: true, ticks: { callback: (v) => this.moneda(v) } } },
        },
      }));
    }

    // Barras: % ejecución por contrato.
    if (this.rAvance && i.avance_por_contrato.length) {
      this.charts.push(new Chart(this.rAvance.nativeElement, {
        type: 'bar',
        data: {
          labels: i.avance_por_contrato.map((x) => x.contrato),
          datasets: [{ data: i.avance_por_contrato.map((x) => x.ejecucion), backgroundColor: i.avance_por_contrato.map((x) => this.colorEjec(x.ejecucion)), borderRadius: 4 }],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx) => `${ctx.parsed.y}% ejecutado` } } },
          scales: { y: { beginAtZero: true, max: 100, ticks: { callback: (v) => `${v}%` } } },
        },
      }));
    }
  }

  private colorEjec(e: number): string {
    return e >= 80 ? '#16a34a' : e >= 50 ? '#f59e0b' : '#dc2626';
  }
}
