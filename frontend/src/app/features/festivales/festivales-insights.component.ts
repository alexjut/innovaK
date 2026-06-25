import { CommonModule } from '@angular/common';
import {
  AfterViewInit, Component, ElementRef, OnDestroy, OnInit, ViewChild,
  inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Chart, registerables } from 'chart.js';
import { LayoutService } from '../../core/layout/layout.service';
import { FestivalesApi } from './festivales.api';
import { FestivalInsights } from './festivales.types';

Chart.register(...registerables);

/**
 * Tablero de seguimiento del módulo Festivales (PR-C). Conexión NO
 * decorativa con la Meta 4 del 2780: muestra el avance REAL de los KPIs
 * (presu_avance_ind_periodo), aforo y presupuesto ejecutado vs asignado.
 */
@Component({
  standalone: true,
  selector: 'app-festivales-insights',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <div>
          <h1><i class="fa fa-chart-line"></i> Seguimiento de Festivales</h1>
          <p class="page__sub">Avance a la Meta 4 del proyecto 2780 · aforo · presupuesto</p>
        </div>
        <div class="actions">
          @if (data(); as d) {
            <select [(ngModel)]="vigencia" (change)="recargar()">
              @for (v of d.vigencias; track v) { <option [ngValue]="v">Vigencia {{ v }}</option> }
            </select>
          }
          <a routerLink="/festivales" class="ui-btn ui-btn--ghost ui-btn--sm">
            <i class="fa fa-arrow-left"></i> Listado
          </a>
        </div>
      </header>

      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando tablero…</div> }
      @if (error()) { <div class="ui-info-bar ui-info-bar--danger">{{ error() }}</div> }

      @if (data(); as d) {
        <section class="tiles">
          <div class="tile">
            <span class="tile__n">{{ d.resumen.n_festivales }}</span>
            <span class="tile__l">Festivales {{ d.vigencia }}</span>
            <small>{{ d.resumen.ejecutados }} ejecutados · {{ d.resumen.planeados }} planeados</small>
          </div>
          <div class="tile">
            <span class="tile__n">{{ d.resumen.actos_contabilizados }}<small>/{{ d.resumen.total_actos }}</small></span>
            <span class="tile__l">Actos contabilizados</span>
            <small>suman al KPI de eventos</small>
          </div>
          <div class="tile">
            <span class="tile__n">{{ d.resumen.aforo_total }}</span>
            <span class="tile__l">Aforo total</span>
            <small>asistencia registrada (PR-D)</small>
          </div>
          <div class="tile tile--accent">
            <span class="tile__n">{{ pctPrincipal(d) }}<small>%</small></span>
            <span class="tile__l">Avance KPI principal</span>
            <small>{{ kpiPrincipal(d) }}</small>
          </div>
        </section>

        <!-- KPIs con avance real -->
        <section class="card">
          <h2>Indicadores (avance real)</h2>
          @if (d.kpis.length === 0) {
            <p class="muted">Aún no hay KPIs ligados a los actos de estos festivales.</p>
          }
          @for (k of d.kpis; track k.id) {
            <div class="kpi">
              <div class="kpi__head">
                <span class="kpi__name">{{ k.nombre }}</span>
                <span class="kpi__val">{{ k.avance_total }} / {{ k.meta_magnitud }} {{ k.unidad }}</span>
              </div>
              <div class="bar">
                <div class="bar__fill" [class.bar__fill--ok]="(k.pct || 0) >= 80"
                     [class.bar__fill--mid]="(k.pct || 0) >= 50 && (k.pct || 0) < 80"
                     [style.width.%]="barWidth(k.pct)"></div>
              </div>
              <div class="kpi__foot">
                <span>{{ k.pct !== null ? k.pct + '%' : '—' }}</span>
                <span class="muted">Aporte de festivales: {{ k.avance_festivales }}</span>
              </div>
            </div>
          }
        </section>

        <section class="charts">
          <div class="card">
            <h2>Festivales por estado</h2>
            <canvas #estado></canvas>
          </div>
          <div class="card">
            <h2>Presupuesto del 2780</h2>
            <canvas #presu></canvas>
            <div class="presu-cifras">
              <span>Asignado: <strong>{{ money(d.presupuesto.asignado) }}</strong></span>
              <span>Ejecutado: <strong>{{ money(d.presupuesto.ejecutado) }}</strong></span>
              <span>Disponible: <strong>{{ money(d.presupuesto.disponible) }}</strong></span>
            </div>
          </div>
        </section>

        <!-- Detalle por festival -->
        <section class="card">
          <h2>Detalle por festival</h2>
          <table class="tbl">
            <thead>
              <tr><th>Festival</th><th>Estado</th><th>Actos</th><th>Días</th><th>Evidencias</th><th>Aforo</th><th></th></tr>
            </thead>
            <tbody>
              @for (f of d.festivales; track f.id) {
                <tr>
                  <td>{{ f.nombre }}@if (f.tipo) { <small class="muted"> · {{ f.tipo }}</small> }</td>
                  <td><span class="badge badge--{{ f.estado }}">{{ f.estado_display }}</span></td>
                  <td>{{ f.n_actos }}</td>
                  <td>{{ f.n_dias }}</td>
                  <td>{{ f.n_archivos }}</td>
                  <td>{{ f.aforo }}</td>
                  <td><a [routerLink]="['/festivales', f.id]" class="link">Ver</a></td>
                </tr>
              }
              @if (d.festivales.length === 0) {
                <tr><td colspan="7" class="muted">Sin festivales en esta vigencia.</td></tr>
              }
            </tbody>
          </table>
        </section>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1100px; margin: 0 auto; padding-bottom: $space-6; }
    .page__header { display: flex; justify-content: space-between; align-items: flex-start; gap: $space-3; flex-wrap: wrap; }
    .page__header h1 { margin: 0; color: $color-primary; }
    .page__sub { color: $color-text-muted; font-size: $font-size-sm; margin: $space-1 0 0; }
    .actions { display: flex; gap: $space-2; align-items: center; }
    .actions select { padding: 6px 8px; border: 1px solid $color-border; border-radius: $radius-sm; }

    .tiles { display: grid; grid-template-columns: repeat(4, 1fr); gap: $space-3; margin: $space-3 0; }
    @media (max-width: 800px) { .tiles { grid-template-columns: repeat(2, 1fr); } }
    .tile { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-3; display: flex; flex-direction: column; gap: 2px; }
    .tile--accent { border-color: $color-primary; }
    .tile__n { font-size: 1.8rem; font-weight: 700; color: $color-primary; line-height: 1; }
    .tile__n small { font-size: .9rem; color: $color-text-muted; font-weight: 600; }
    .tile__l { font-weight: 600; font-size: $font-size-sm; }
    .tile small { color: $color-text-muted; font-size: .72rem; }

    .card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-4; margin-top: $space-3; }
    .card h2 { margin: 0 0 $space-3; color: $color-primary; font-size: 1.05rem; }
    .charts { display: grid; grid-template-columns: 1fr 1fr; gap: $space-3; }
    @media (max-width: 800px) { .charts { grid-template-columns: 1fr; } }
    canvas { max-height: 240px; }
    .presu-cifras { display: flex; gap: $space-3; flex-wrap: wrap; margin-top: $space-2; font-size: $font-size-sm; color: $color-text-muted; }

    .kpi { margin-bottom: $space-3; }
    .kpi__head, .kpi__foot { display: flex; justify-content: space-between; font-size: $font-size-sm; }
    .kpi__name { font-weight: 600; }
    .kpi__foot { margin-top: 4px; }
    .bar { height: 10px; background: #F1F5F9; border-radius: 99px; overflow: hidden; margin-top: 4px; }
    .bar__fill { height: 100%; background: #DC2626; border-radius: 99px; transition: width .4s; }
    .bar__fill--mid { background: #F59E0B; }
    .bar__fill--ok { background: #16A34A; }

    .tbl { width: 100%; border-collapse: collapse; font-size: $font-size-sm; }
    .tbl th, .tbl td { text-align: left; padding: 8px 10px; border-bottom: 1px solid $color-border; }
    .tbl th { color: $color-text-muted; font-weight: 600; }
    .badge { border-radius: 99px; padding: 3px 10px; font-size: .7rem; font-weight: 600; }
    .badge--planeado { background: #FEF3C7; color: #92400E; }
    .badge--ejecutado { background: #DCFCE7; color: #166534; }
    .badge--cerrado { background: #E5E7EB; color: #374151; }
    .muted { color: $color-text-muted; }
    .link { color: $color-primary; text-decoration: none; font-weight: 600; }
    .link:hover { text-decoration: underline; }
  `],
})
export class FestivalesInsightsComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('estado') estadoCanvas?: ElementRef<HTMLCanvasElement>;
  @ViewChild('presu') presuCanvas?: ElementRef<HTMLCanvasElement>;

  private api = inject(FestivalesApi);
  private layout = inject(LayoutService);

  loading = signal(true);
  error = signal('');
  data = signal<FestivalInsights | null>(null);
  vigencia: number | null = null;
  private charts: Chart[] = [];
  private viewReady = false;

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Festivales', url: '/festivales' },
      { label: 'Seguimiento' },
    ]);
    this.cargar();
  }

  ngAfterViewInit(): void { this.viewReady = true; this.render(); }

  ngOnDestroy(): void { this.charts.forEach((c) => c.destroy()); }

  recargar(): void { this.cargar(); }

  private cargar(): void {
    this.loading.set(true);
    this.error.set('');
    this.api.insights(this.vigencia ?? undefined).subscribe({
      next: (d) => {
        this.data.set(d);
        this.vigencia = d.vigencia;
        this.loading.set(false);
        setTimeout(() => this.render(), 0);
      },
      error: (e) => { this.loading.set(false); this.error.set(e?.error?.detail || 'No se pudo cargar el tablero.'); },
    });
  }

  private render(): void {
    const d = this.data();
    if (!this.viewReady || !d) return;
    this.charts.forEach((c) => c.destroy());
    this.charts = [];

    if (this.estadoCanvas) {
      this.charts.push(new Chart(this.estadoCanvas.nativeElement, {
        type: 'doughnut',
        data: {
          labels: ['Planeados', 'Ejecutados', 'Cerrados'],
          datasets: [{
            data: [d.resumen.planeados, d.resumen.ejecutados, d.resumen.cerrados],
            backgroundColor: ['#F59E0B', '#16A34A', '#9CA3AF'],
          }],
        },
        options: { responsive: true, plugins: { legend: { position: 'bottom' } } },
      }));
    }
    if (this.presuCanvas) {
      this.charts.push(new Chart(this.presuCanvas.nativeElement, {
        type: 'bar',
        data: {
          labels: ['Asignado', 'Ejecutado', 'Disponible'],
          datasets: [{
            data: [d.presupuesto.asignado, d.presupuesto.ejecutado, d.presupuesto.disponible],
            backgroundColor: ['#0D9488', '#DC2626', '#94A3B8'],
          }],
        },
        options: { responsive: true, plugins: { legend: { display: false } } },
      }));
    }
  }

  barWidth(pct: number | null): number { return Math.min(100, Math.max(0, pct || 0)); }

  pctPrincipal(d: FestivalInsights): number {
    const k = d.kpis[0];
    return k?.pct ?? 0;
  }

  kpiPrincipal(d: FestivalInsights): string {
    const k = d.kpis[0];
    return k ? `${k.avance_total}/${k.meta_magnitud} ${k.unidad}` : 'sin KPI';
  }

  money(v: number): string {
    return v ? '$' + v.toLocaleString('es-CO', { maximumFractionDigits: 0 }) : '$0';
  }
}
