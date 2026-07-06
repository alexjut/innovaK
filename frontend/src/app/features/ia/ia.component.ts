import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import {
  ChangeDetectionStrategy, Component, ElementRef, OnInit, ViewChild,
  computed, effect, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Chart, registerables } from 'chart.js';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';
import { EstadoKenny, MascotPresenterComponent } from '../onboarding/mascot-presenter/mascot-presenter.component';

Chart.register(...registerables);

interface QueryResult {
  ok: boolean;
  type?: 'count' | 'group';
  label?: string;
  description?: string;
  count?: number;
  rows?: { categoria: string; total: number }[];
  universo?: number;
  error?: string;
}

const EJEMPLOS = [
  '¿Cuántos beneficiarios hay?',
  'Beneficiarios por área',
  '¿Qué lugares se usan más?',
  '¿Cómo se reparten por estrato?',
  '¿Cuántos tienen discapacidad?',
  'Beneficiarios por nivel educativo',
  '¿Cuántos por sexo?',
  'Las 5 ocupaciones más comunes',
];

/**
 * Consulta IA — interfaz NATIVA Angular sobre el endpoint de lenguaje
 * natural `/dashboard/api/personas/query` (intent → query segura).
 * Reemplaza el iframe al Django legacy. Renderiza:
 *   count → tarjeta con número grande
 *   group/top → gráfico de barras Chart.js + tabla
 *   filter → tabla de resultados
 */
@Component({
  standalone: true,
  selector: 'app-ia',
  imports: [CommonModule, FormsModule, RouterLink, MascotPresenterComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="ia">
      <header class="ia__hero">
        <div class="ia__kenny">
          <app-mascot-presenter [estado]="estadoKenny()" />
          <span class="ia__kenny-txt">{{ mensajeKenny() }}</span>
        </div>
        <div class="ia__top">
          <h1><i class="fa fa-wand-magic-sparkles"></i> Consulta inteligente</h1>
          <a routerLink="/analitica" class="ui-btn ui-btn--light ui-btn--sm">
            <i class="fa fa-chart-line"></i> Tablero analítico
          </a>
        </div>
        <p>Pregunta en lenguaje natural sobre los <strong>beneficiarios de los productos de los proyectos</strong>
           (personas que participaron en eventos).</p>
        <div class="ia__search">
          <input type="text" [(ngModel)]="pregunta"
                 (keyup.enter)="consultar()"
                 placeholder="Ej. ¿cuántas personas hay por estrato?">
          <button class="ui-btn ui-btn--primary" (click)="consultar()"
                  [disabled]="cargando() || !pregunta.trim()">
            @if (cargando()) { <i class="fa fa-spinner fa-spin"></i> }
            @else { <i class="fa fa-magnifying-glass"></i> } Preguntar
          </button>
        </div>
        <div class="ia__chips">
          @for (ej of ejemplos; track ej) {
            <button class="chip" (click)="usarEjemplo(ej)">{{ ej }}</button>
          }
        </div>
      </header>

      @if (error()) {
        <div class="ui-info-bar ui-info-bar--danger">{{ error() }}</div>
      }

      @if (resultado(); as r) {
        @if (!r.ok) {
          <div class="ui-info-bar ui-info-bar--info">
            {{ r.error || 'No entendí la pregunta. Intenta reformularla.' }}
          </div>
        }
        <div class="res-head">
          @if (r.label) { <h2 class="res-title">{{ r.label }}</h2> }
          @if (r.universo) { <span class="res-univ"><i class="fa fa-users"></i> {{ r.universo | number }} beneficiarios</span> }
        </div>
        @if (r.description) { <p class="ia__desc"><i class="fa fa-circle-info"></i> {{ r.description }}</p> }

        @switch (r.type) {
          @case ('count') {
            <article class="count-card">
              <span class="count-card__num">{{ r.count | number }}</span>
              <span class="count-card__lbl">{{ r.label || 'resultados' }}</span>
            </article>
          }
          @case ('group') {
            @if (r.rows?.length) {
              <div class="ui-card">
                <div class="chart-box"><canvas #chartCanvas></canvas></div>
                <div class="tbl-wrap">
                  <table class="tbl">
                    <thead><tr><th>Categoría</th><th class="num">Beneficiarios</th></tr></thead>
                    <tbody>
                      @for (row of r.rows!; track $index) {
                        <tr><td>{{ row.categoria }}</td><td class="num">{{ row.total | number }}</td></tr>
                      }
                    </tbody>
                  </table>
                </div>
              </div>
            } @else {
              <div class="ui-info-bar ui-info-bar--info">
                No hay datos de «{{ r.label }}» en los beneficiarios. (Muchos participantes
                se registran sin caracterización completa.)
              </div>
            }
          }
        }
      }
    </div>
  `,
  styles: [`
    .ia__hero { position: relative; }
    .ia__kenny {
      position: absolute; top: 14px; right: 16px;
      display: flex; flex-direction: column; align-items: center; gap: 4px;
      --kenny-size: 68px; width: 96px; text-align: center; z-index: 2;
    }
    .ia__kenny-txt {
      font-size: 11px; font-weight: 700; color: #fff;
      background: rgba(0,0,0,.18); border-radius: 999px; padding: 2px 8px;
    }
    @media (max-width: 720px) { .ia__kenny { display: none; } }
`, `
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .ia { max-width: 1000px; margin: 0 auto; }
    .ia__hero {
      background: linear-gradient(135deg, $color-primary, $color-primary-dark);
      color: #fff; border-radius: $radius-lg; padding: $space-5 $space-4; margin-bottom: $space-4;
      h1 { margin: 0; display: flex; align-items: center; gap: $space-2; }
      p { margin: $space-1 0 $space-3; opacity: 0.9; }
    }
    .ia__top { display: flex; justify-content: space-between; align-items: center; gap: $space-3; flex-wrap: wrap;
      a { background: rgba(255,255,255,0.18); color: #fff; border: 0; }
      a:hover { background: rgba(255,255,255,0.30); } }
    .ia__search { display: flex; gap: $space-2; flex-wrap: wrap;
      input { flex: 1; min-width: 240px; padding: $space-2 $space-3; border: 0;
              border-radius: $radius-md; font: inherit; } }
    .ia__chips { display: flex; gap: $space-2; flex-wrap: wrap; margin-top: $space-3; }
    .chip { background: rgba(255,255,255,0.18); color: #fff; border: 0;
            padding: 4px 12px; border-radius: $radius-pill; font-size: $font-size-xs;
            cursor: pointer; &:hover { background: rgba(255,255,255,0.30); } }
    .ia__desc { color: $color-text-muted; font-size: $font-size-sm; margin: 0 0 $space-3; }

    .count-card {
      background: #fff; border: 1px solid $color-border; border-left: 6px solid $color-primary;
      border-radius: $radius-lg; padding: $space-5; display: flex; flex-direction: column; align-items: center;
      &__num { font-size: 3.5rem; font-weight: 800; color: $color-primary; line-height: 1; }
      &__lbl { font-size: $font-size-sm; color: $color-text-muted; }
    }
    .chart-box { height: 320px; margin-bottom: $space-3; }
    .tbl-wrap { overflow-x: auto; }
    .tbl { width: 100%; border-collapse: collapse;
      th, td { padding: $space-2; border-bottom: 1px solid $color-border; text-align: left; font-size: $font-size-sm; }
      th { color: $color-text-muted; font-size: $font-size-xs; }
      .num { text-align: right; font-variant-numeric: tabular-nums; } }
    .muted { color: $color-text-muted; }
    .res-head { display: flex; justify-content: space-between; align-items: center; gap: $space-3; flex-wrap: wrap; margin-bottom: $space-2; }
    .res-title { margin: 0; color: $color-primary; font-size: 1.2rem; }
    .res-univ { font-size: $font-size-sm; color: $color-text-muted; background: $color-bg-subtle; padding: 4px 12px; border-radius: $radius-pill; }
  `],
})
export class IaComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);

  @ViewChild('chartCanvas') private canvasRef?: ElementRef<HTMLCanvasElement>;
  private chart?: Chart;

  ejemplos = EJEMPLOS;
  pregunta = '';
  cargando = signal<boolean>(false);
  error = signal<string>('');
  resultado = signal<QueryResult | null>(null);

  /** Kenny reacciona a la consulta: escucha → celebra el resultado. */
  readonly estadoKenny = computed<EstadoKenny>(() => {
    if (this.cargando()) return 'senalando';
    const r = this.resultado();
    if (r?.ok) return 'celebrando';
    return 'saludo';
  });
  readonly mensajeKenny = computed<string>(() => {
    if (this.cargando()) return 'Buscando…';
    const r = this.resultado();
    if (r?.ok) return '¡Aquí está!';
    if (this.error()) return 'Reformula 🙂';
    return '¡Pregúntame!';
  });

  constructor() {
    effect(() => {
      const r = this.resultado();
      if (r && r.type === 'group' && r.rows?.length) {
        queueMicrotask(() => this.dibujar(r));
      }
    });
  }

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Consulta IA' },
    ]);
  }

  usarEjemplo(ej: string): void {
    this.pregunta = ej;
    this.consultar();
  }

  consultar(): void {
    const q = this.pregunta.trim();
    if (!q) return;
    this.cargando.set(true);
    this.error.set('');
    this.resultado.set(null);
    this.http.post<QueryResult>(
      this.cfg.url('/dashboard/api/ia/beneficiarios'), { query: q },
    ).subscribe({
      next: (r) => { this.resultado.set(r); this.cargando.set(false); },
      error: (e) => {
        this.cargando.set(false);
        this.error.set(e?.error?.error || 'No se pudo ejecutar la consulta. Intenta reformularla.');
      },
    });
  }

  columnas(rows: Record<string, any>[]): string[] {
    return rows.length ? Object.keys(rows[0]) : [];
  }

  private dibujar(r: QueryResult): void {
    const canvas = this.canvasRef?.nativeElement;
    if (!canvas || !r.rows) return;
    this.chart?.destroy();
    const palette = ['#D6001C', '#0D9488', '#2563eb', '#d97706', '#7c3aed', '#16a34a', '#db2777', '#64748b', '#0ea5e9', '#84cc16'];
    this.chart = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: r.rows.map(x => String(x['categoria'])),
        datasets: [{
          data: r.rows.map(x => x['total']),
          backgroundColor: r.rows.map((_, i) => palette[i % palette.length]),
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    });
  }
}
