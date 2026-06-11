import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { ConfigService } from '../../core/config/config.service';
import { DescargasService } from '../../core/descargas.service';
import { BancoApi } from './banco.api';
import {
  BancoInsights,
  InscripcionEstado,
  InscripcionFilters,
  InscripcionListItem,
  PaginatedResponse,
} from './banco.types';

/**
 * Lista paginada del Banco de Iniciativas (organizador).
 *
 * Réplica del HTML Django `templates/banco_iniciativas/inscripciones_list.html`.
 * Filtros por estado, evento y búsqueda libre. Cada fila linkea al
 * detalle 360°.
 *
 * Datos del backend Etapa B: `apps/banco_iniciativas/api/views.py::InscripcionListView`.
 */
@Component({
  standalone: true,
  selector: 'app-banco-inscripciones-list',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header" style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;">
        <div>
          <h1><i class="fa fa-hand-holding-heart" aria-hidden="true"></i> Banco de Iniciativas</h1>
          <p class="page__subtitle">Validar/rechazar inscripciones de colectivos recreodeportivos.</p>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          <button class="ui-btn ui-btn--ghost ui-btn--sm" (click)="exportarCsv()">
            <i class="fa fa-file-csv"></i> Exportar CSV
          </button>
          <a routerLink="/banco/insights" class="ui-btn ui-btn--primary ui-btn--sm">
            <i class="fa fa-chart-pie"></i> Insights
          </a>
        </div>
      </header>

      <!-- Insights cards -->
      @if (insights(); as ins) {
        <div class="kpi-grid">
          <article class="ui-card ui-card--primary">
            <div class="ui-card__body kpi">
              <span class="kpi__label">Total</span>
              <span class="kpi__value">{{ ins.total }}</span>
            </div>
          </article>
          <article class="ui-card ui-card--accent">
            <div class="ui-card__body kpi">
              <span class="kpi__label">Meta convocatoria</span>
              <span class="kpi__value">{{ ins.meta }}</span>
            </div>
          </article>
          <article class="ui-card ui-card--success">
            <div class="ui-card__body kpi">
              <span class="kpi__label">Avance</span>
              <span class="kpi__value">{{ ins.avance_pct | number:'1.0-1' }}%</span>
            </div>
          </article>
        </div>
      }

      <!-- Filter bar -->
      <div class="ui-filter-bar">
        <div class="ui-filter-bar__group">
          <label class="ui-filter-bar__label" for="f-estado">Estado</label>
          <select id="f-estado" class="ui-filter-bar__field"
                  [(ngModel)]="filterEstado" (ngModelChange)="applyFilters()">
            <option value="">Todos</option>
            <option value="enviada">Enviadas</option>
            <option value="validada">Validadas</option>
            <option value="rechazada">Rechazadas</option>
          </select>
        </div>
        <div class="ui-filter-bar__group">
          <label class="ui-filter-bar__label" for="f-q">Buscar</label>
          <input id="f-q" type="search" class="ui-filter-bar__field"
                 placeholder="Documento, nombre, organización…"
                 [(ngModel)]="filterQ" (keyup.enter)="applyFilters()" />
        </div>
        <div class="ui-filter-bar__actions">
          <button class="ui-btn ui-btn--primary ui-btn--sm" (click)="applyFilters()">
            <i class="fa fa-search" aria-hidden="true"></i> Aplicar
          </button>
          <button class="ui-btn ui-btn--ghost ui-btn--sm" (click)="clearFilters()">
            Limpiar
          </button>
        </div>
      </div>

      <!-- State -->
      @if (loading()) {
        <div class="ui-info-bar ui-info-bar--info">Cargando inscripciones…</div>
      } @else if (errorMsg()) {
        <div class="ui-info-bar ui-info-bar--danger">
          <strong>Error:</strong> {{ errorMsg() }}
        </div>
      } @else if (rows().length === 0) {
        <div class="ui-empty-state">
          <i class="fa fa-folder-open" aria-hidden="true"></i>
          <p>No hay inscripciones para los filtros aplicados.</p>
        </div>
      } @else {
        <!-- Table -->
        <div class="ui-table-responsive">
          <table class="ui-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Documento</th>
                <th>Representante</th>
                <th>Organización</th>
                <th>Disciplina</th>
                <th class="ui-table__cell--center">Estado</th>
                <th class="ui-table__cell--right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              @for (row of rows(); track row.id) {
                <tr>
                  <td>{{ row.id }}</td>
                  <td><code class="small">{{ row.rep_numero_doc || '—' }}</code></td>
                  <td>{{ row.rep_nombre || '—' }}</td>
                  <td>
                    {{ row.organizacion_nombre || '—' }}
                    @if (row.upl) {
                      <small class="muted d-block">{{ row.upl }}</small>
                    }
                  </td>
                  <td>{{ row.disciplina_principal || '—' }}</td>
                  <td class="ui-table__cell--center">
                    <span class="ui-badge" [class]="badgeClass(row.estado)">
                      {{ estadoLabel(row.estado) }}
                    </span>
                  </td>
                  <td class="ui-table__cell--right">
                    <a [routerLink]="['/banco', row.id]" class="ui-btn ui-btn--outline ui-btn--sm">
                      <i class="fa fa-eye" aria-hidden="true"></i> Ver
                    </a>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <nav class="pagination" aria-label="Paginación">
          <button class="ui-btn ui-btn--ghost ui-btn--sm"
                  (click)="prevPage()" [disabled]="page() === 1">
            <i class="fa fa-chevron-left" aria-hidden="true"></i> Anterior
          </button>
          <span class="pagination__info">
            Página {{ page() }} · {{ count() }} total
          </span>
          <button class="ui-btn ui-btn--ghost ui-btn--sm"
                  (click)="nextPage()" [disabled]="!hasNext()">
            Siguiente <i class="fa fa-chevron-right" aria-hidden="true"></i>
          </button>
        </nav>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;

    :host { display: block; }
    .page { max-width: 1200px; margin: 0 auto; }
    .page__header { margin-bottom: $space-4; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 0; }

    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: $space-3;
      margin-bottom: $space-4;
    }
    .kpi {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: $space-1;
    }
    .kpi__label {
      font-size: $font-size-xs;
      color: $color-text-muted;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: $font-weight-semibold;
    }
    .kpi__value {
      font-size: $font-size-2xl;
      font-weight: $font-weight-bold;
      color: $color-text;
    }

    .pagination {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: $space-4;
      gap: $space-3;
    }
    .pagination__info {
      color: $color-text-muted;
      font-size: $font-size-sm;
    }
    .muted { color: $color-text-muted; }
    .small { font-size: $font-size-xs; }
    .d-block { display: block; }
  `],
})
export class InscripcionesListComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private api = inject(BancoApi);
  private layout = inject(LayoutService);
  private cfg = inject(ConfigService);
  private descargas = inject(DescargasService);

  /** Exporta la lista filtrada a CSV (abre el endpoint Django con la sesión). */
  exportarCsv(): void {
    const params = new URLSearchParams();
    if (this.filterEstado) params.set('estado', this.filterEstado);
    if (this.filterEvento) params.set('evento', String(this.filterEvento));
    const qs = params.toString();
    this.descargas.descargar(
      '/banco-iniciativas/inscripciones/exportar/' + (qs ? '?' + qs : ''),
    );
  }

  // Estado reactivo
  loading = signal<boolean>(false);
  errorMsg = signal<string>('');
  rows = signal<InscripcionListItem[]>([]);
  count = signal<number>(0);
  page = signal<number>(1);
  next = signal<string | null>(null);
  insights = signal<BancoInsights | null>(null);

  // Filtros (bound al form)
  filterEstado: InscripcionEstado | '' = '';
  filterQ = '';
  filterEvento: number | null = null;

  hasNext = computed(() => !!this.next());

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Banco de Iniciativas' },
    ]);
    // Si llega ?evento=<id> (desde Actividades → Beneficiarios), filtra.
    const ev = this.route.snapshot.queryParamMap.get('evento');
    this.filterEvento = ev ? Number(ev) : null;
    this.loadInsights();
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.errorMsg.set('');
    this.api.list(this.currentFilters()).subscribe({
      next: (r: PaginatedResponse<InscripcionListItem>) => {
        this.rows.set(r.results);
        this.count.set(r.count);
        this.next.set(r.next);
        this.loading.set(false);
      },
      error: (e) => {
        this.loading.set(false);
        this.errorMsg.set(this.parseError(e));
      },
    });
  }

  loadInsights(): void {
    this.api.insights().subscribe({
      next: (i) => this.insights.set(i),
      error: () => this.insights.set(null),
    });
  }

  applyFilters(): void {
    this.page.set(1);
    this.load();
  }

  clearFilters(): void {
    this.filterEstado = '';
    this.filterQ = '';
    this.page.set(1);
    this.load();
  }

  nextPage(): void {
    if (!this.hasNext()) return;
    this.page.update((p) => p + 1);
    this.load();
  }

  prevPage(): void {
    if (this.page() === 1) return;
    this.page.update((p) => p - 1);
    this.load();
  }

  private currentFilters(): InscripcionFilters {
    return {
      estado: this.filterEstado || undefined,
      evento: this.filterEvento || undefined,
      q: this.filterQ || undefined,
      page: this.page(),
    };
  }

  estadoLabel(e: InscripcionEstado): string {
    const map: Record<InscripcionEstado, string> = {
      borrador: 'Borrador', enviada: 'Enviada',
      validada: 'Validada', rechazada: 'Rechazada',
    };
    return map[e] ?? e;
  }

  badgeClass(e: InscripcionEstado): string {
    return e === 'validada'
      ? 'ui-badge--success'
      : e === 'rechazada'
        ? 'ui-badge--danger'
        : 'ui-badge--warning';
  }

  private parseError(err: { status?: number; message?: string }): string {
    if (err?.status === 403) return 'No tienes permiso para ver el Banco de Iniciativas.';
    if (err?.status === 401) return 'Sesión expirada. Vuelve a iniciar sesión.';
    if (err?.status === 0) return 'No se pudo conectar con el servidor.';
    return err?.message || 'Error inesperado al cargar.';
  }
}
