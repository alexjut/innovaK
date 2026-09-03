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
        <div class="ia__top">
          <div class="ia__title-wrap">
            <span class="ia__icon"><i class="fa fa-wand-magic-sparkles"></i></span>
            <div>
              <h1>Consulta inteligente</h1>
              <p>Pregunta en lenguaje natural sobre los <strong>beneficiarios de los productos de los proyectos</strong> (personas que participaron en eventos).</p>
            </div>
          </div>
          <a routerLink="/analitica" class="ui-btn ui-btn--light ui-btn--sm">
            <i class="fa fa-chart-line"></i> Tablero analítico
          </a>
        </div>
      </header>
      <div class="ia__layout">
        <aside class="ia__side">
          <div class="ia__side-title">Preguntas sugeridas</div>
          <div class="ia__sugg-list">
            @for (ej of ejemplos; track ej) {
              <button type="button" class="ia__sugg-item" [class.is-active]="pregunta === ej" (click)="usarEjemplo(ej)">
                <span class="ia__sugg-dot"></span>{{ ej }}
              </button>
            }
          </div>
        </aside>
        <div class="ia__main">
          <div class="ia__search">
            <span class="ia__kenny" [attr.title]="mensajeKenny()" aria-hidden="true">
              <app-mascot-presenter [estado]="estadoKenny()" />
            </span>
            <input type="text" [(ngModel)]="pregunta"
              (keyup.enter)="consultar()"
              placeholder="Ej. ¿cuántas personas hay por estrato?" />
            <button class="ia__send" (click)="consultar()"
              [disabled]="cargando() || !pregunta.trim()">
              @if (cargando()) { <i class="fa fa-spinner fa-spin"></i> }
              @else { <i class="fa fa-magnifying-glass"></i> }
            </button>
          </div>
          @if (error()) {
            <div class="ui-info-bar ui-info-bar--danger">{{ error() }}</div>
          }
          @if (resultado(); as r) {
            @if (!r.ok) {
              <div class="ui-info-bar ui-info-bar--info">
                {{ r.error || 'No entendí la pregunta. Intenta reformularla.' }}
              </div>
            }
            @if (r.ok) {
              <article class="a-card">
                <div class="a-head">
                  <span class="a-head-icon"><i [class]="'fa ' + (r.type === 'count' ? 'fa-hashtag' : 'fa-chart-simple')"></i></span>
                  <div class="a-head-txt">
                    @if (r.label) { <h2>{{ r.label }}</h2> }
                    @if (r.description) { <p>{{ r.description }}</p> }
                  </div>
                  @if (r.universo) {
                    <span class="a-badge"><i class="fa fa-users"></i> {{ r.universo | number }} beneficiarios</span>
                  }
                </div>
                @switch (r.type) {
                  @case ('count') {
                    <div class="a-body">
                      <article class="count-card">
                        <span class="count-card__num">{{ r.count | number }}</span>
                        <span class="count-card__lbl">{{ r.label || 'resultados' }}</span>
                      </article>
                    </div>
                  }
                  @case ('group') {
                    @if (r.rows?.length) {
                      <div class="a-body">
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
              </article>
            }
          }
        </div>
      </div>
    </div>
  `,
  styles: [`
    .ia__search { align-items: center; }
    .ia__kenny {
      --kenny-size: 44px;
      flex: none;
      line-height: 0;
      display: inline-flex;
      align-items: center;
    }
    @media (max-width: 520px) { .ia__kenny { display: none; } }
`, `
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .ia { max-width: 1000px; margin: 0 auto; }
    .ia__hero {
      background: linear-gradient(135deg, $color-primary, $color-primary-dark);
      color: #fff; border-radius: $radius-lg; padding: $space-5 $space-4; margin-bottom: $space-4;
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
    `, `
      @use '../../../styles/tokens' as *;
      /* Rediseño Consulta IA -- layout de dos columnas */
      .ia__hero {
        background: #fff;
        border: 1px solid $color-border;
        border-radius: $radius-lg;
        padding: $space-4;
        margin-bottom: $space-4;
        h1 {
          margin: 0;
          color: $color-text;
          font-size: 32px;
          font-weight: $font-weight-semibold;
          &::after {
            content: '';
            display: block;
            width: 48px;
            height: 4px;
            border-radius: $radius-pill;
            background: $color-secondary;
            margin-top: $space-2;
          }
        }
        p { margin: $space-1 0 0; opacity: 1; color: $color-text-muted; font-size: $font-size-sm; max-width: 620px; }
      }
      .ia__top { align-items: flex-start; }
      .ia__title-wrap { display: flex; align-items: flex-start; gap: $space-3; }
      .ia__icon {
        width: 44px; height: 44px; border-radius: $radius-md; background: $color-primary; color: #fff;
        display: flex; align-items: center; justify-content: center; font-size: 1.1rem; flex-shrink: 0;
      }
      .ia__hero .ui-btn--light { background: #fff; color: $color-primary; border: 1.5px solid $color-primary; }
      .ia__hero .ui-btn--light:hover { background: $color-bg-muted; }

      .ia__layout { display: grid; grid-template-columns: 260px 1fr; gap: $space-4; align-items: start;
        @media (max-width: 860px) { grid-template-columns: 1fr; } }

      .ia__side { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-3; }
      .ia__side-title {
        font-size: .72rem; letter-spacing: .06em; text-transform: uppercase; color: $color-text-muted;
        font-weight: 700; margin-bottom: $space-2;
      }
      .ia__sugg-list { display: flex; flex-direction: column; gap: 2px; }
      .ia__sugg-item {
        display: flex; align-items: center; gap: $space-2; text-align: left; width: 100%; background: none; border: 0;
        border-radius: $radius-md; padding: $space-2; font-size: $font-size-sm; color: $color-text; cursor: pointer;
      }
      .ia__sugg-item:hover { background: $color-bg-muted; }
      .ia__sugg-item.is-active { background: rgba(214,0,28,.08); color: $color-primary; font-weight: 600; }
      .ia__sugg-dot { width: 6px; height: 6px; border-radius: 50%; background: $color-border; flex-shrink: 0; }
      .ia__sugg-item.is-active .ia__sugg-dot { background: $color-primary; }

      .ia__main { min-width: 0; }
      .ia__search {
        display: flex; align-items: center; gap: $space-2; background: #fff; border: 1px solid $color-border;
        border-radius: $radius-pill; padding: $space-2 $space-2 $space-2 $space-3; margin-bottom: $space-4;
      }
      .ia__search input { flex: 1; min-width: 0; border: 0; background: transparent; font: inherit; padding: $space-2; }
      .ia__search input:focus { outline: none; }
      .ia__search .ia__kenny { --kenny-size: 34px; }
      .ia__send {
        width: 40px; height: 40px; border-radius: 50%; background: $color-primary; color: #fff; border: 0;
        display: flex; align-items: center; justify-content: center; cursor: pointer; flex-shrink: 0; font-size: .95rem;
      }
      .ia__send:hover:not(:disabled) { background: $color-primary-dark; }
      .ia__send:disabled { opacity: .5; cursor: default; }

      .a-card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-4; }
      .a-head { display: flex; align-items: flex-start; gap: $space-3; margin-bottom: $space-3; }
      .a-head-icon {
        width: 34px; height: 34px; border-radius: $radius-md; background: $color-primary; color: #fff;
        display: flex; align-items: center; justify-content: center; font-size: .9rem; flex-shrink: 0;
      }
      .a-head-txt { flex: 1; min-width: 0; }
      .a-head-txt h2 { margin: 0; font-size: 1.05rem; color: $color-text; }
      .a-head-txt p { margin: 4px 0 0; font-size: $font-size-sm; color: $color-text-muted; }
      .a-badge {
        display: flex; align-items: center; gap: 6px; background: rgba(214,0,28,.08); color: $color-primary;
        font-size: .78rem; font-weight: 700; padding: 6px 12px; border-radius: $radius-pill; white-space: nowrap;
      }
      .a-card .count-card { border: 0; padding: $space-3 0 0; }
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
