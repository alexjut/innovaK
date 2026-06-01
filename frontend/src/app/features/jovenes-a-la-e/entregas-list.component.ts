import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { JovenesApi } from './jovenes.api';
import {
  EntregaEstado,
  EntregaFilters,
  EntregaListItem,
  JovenesInsights,
  PaginatedResponse,
} from './jovenes.types';

/**
 * Lista paginada de entregas Jóvenes a la E (organizador).
 *
 * Datos: `apps/jovenes_a_la_e/api/views.py::EntregaListView`.
 * Convenios visibles en columnas + filtro por convenio_codigo si se
 * quisiera (hoy solo estado/búsqueda — replica el HTML Django).
 */
@Component({
  standalone: true,
  selector: 'app-jovenes-entregas-list',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <h1>Jóvenes a la E</h1>
        <p class="page__subtitle">Entrega de becas (convenios 773-2025 y 955-2025).</p>
      </header>

      <!-- Insights KPIs -->
      @if (insights(); as ins) {
        <div class="kpi-grid">
          <article class="ui-card ui-card--primary">
            <div class="ui-card__body kpi">
              <span class="kpi__label">Total entregas</span>
              <span class="kpi__value">{{ ins.total }}</span>
            </div>
          </article>
          @if (ins.cumplimiento_acceso_count !== undefined) {
            <article class="ui-card ui-card--info">
              <div class="ui-card__body kpi">
                <span class="kpi__label">Acceso (23771)</span>
                <span class="kpi__value">
                  {{ ins.cumplimiento_acceso_count }}
                  @if (ins.meta_acceso) {
                    <small> / {{ ins.meta_acceso }}</small>
                  }
                </span>
              </div>
            </article>
          }
          @if (ins.cumplimiento_permanencia_count !== undefined) {
            <article class="ui-card ui-card--success">
              <div class="ui-card__body kpi">
                <span class="kpi__label">Permanencia (23772)</span>
                <span class="kpi__value">
                  {{ ins.cumplimiento_permanencia_count }}
                  @if (ins.meta_permanencia) {
                    <small> / {{ ins.meta_permanencia }}</small>
                  }
                </span>
              </div>
            </article>
          }
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
                 placeholder="Documento o nombre…"
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
        <div class="ui-info-bar ui-info-bar--info">Cargando entregas…</div>
      }
      @if (!loading() && errorMsg()) {
        <div class="ui-info-bar ui-info-bar--danger">
          <strong>Error:</strong> {{ errorMsg() }}
        </div>
      }
      @if (!loading() && !errorMsg() && rows().length === 0) {
        <div class="ui-empty-state">
          <i class="fa fa-folder-open" aria-hidden="true"></i>
          <p>No hay entregas para los filtros aplicados.</p>
        </div>
      }
      @if (!loading() && !errorMsg() && rows().length > 0) {
        <div class="ui-table-responsive">
          <table class="ui-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Documento</th>
                <th>Nombre</th>
                <th>Convenio</th>
                <th class="ui-table__cell--center">Acceso</th>
                <th class="ui-table__cell--center">Permanencia</th>
                <th class="ui-table__cell--center">Estado</th>
                <th class="ui-table__cell--right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              @for (row of rows(); track row.id) {
                <tr>
                  <td>{{ row.id }}</td>
                  <td>
                    <code class="small">{{ row.numero_documento }}</code>
                    <small class="muted d-block">{{ row.tipo_doc_codigo }}</small>
                  </td>
                  <td>
                    {{ row.nombre_completo || '—' }}
                    @if (row.nivel_formacion) {
                      <small class="muted d-block">{{ row.nivel_formacion }}</small>
                    }
                  </td>
                  <td>
                    @if (row.convenio_codigo) {
                      <span class="ui-badge ui-badge--neutral">{{ row.convenio_codigo }}</span>
                    } @else { — }
                  </td>
                  <td class="ui-table__cell--center">
                    @if (row.cumplimiento_acceso) {
                      <i class="fa fa-check text-success" aria-label="Sí"></i>
                    } @else {
                      <span class="muted">—</span>
                    }
                  </td>
                  <td class="ui-table__cell--center">
                    @if (row.cumplimiento_permanencia) {
                      <i class="fa fa-check text-success" aria-label="Sí"></i>
                    } @else {
                      <span class="muted">—</span>
                    }
                  </td>
                  <td class="ui-table__cell--center">
                    <span class="ui-badge" [class]="badgeClass(row.estado)">
                      {{ estadoLabel(row.estado) }}
                    </span>
                  </td>
                  <td class="ui-table__cell--right">
                    <a [routerLink]="['/jovenes', row.id]" class="ui-btn ui-btn--outline ui-btn--sm">
                      <i class="fa fa-eye" aria-hidden="true"></i> Ver
                    </a>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>

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
    .page__header h1 { margin: 0; color: $color-primary; }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 0; }

    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
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
    .kpi__value small {
      font-size: $font-size-md;
      color: $color-text-muted;
      font-weight: $font-weight-medium;
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
    .text-success { color: $color-success; }
  `],
})
export class EntregasListComponent implements OnInit {
  private api = inject(JovenesApi);
  private layout = inject(LayoutService);

  loading = signal<boolean>(false);
  errorMsg = signal<string>('');
  rows = signal<EntregaListItem[]>([]);
  count = signal<number>(0);
  page = signal<number>(1);
  next = signal<string | null>(null);
  insights = signal<JovenesInsights | null>(null);

  filterEstado: EntregaEstado | '' = '';
  filterQ = '';

  hasNext = computed(() => !!this.next());

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Jóvenes a la E' },
    ]);
    this.loadInsights();
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.errorMsg.set('');
    this.api.list(this.currentFilters()).subscribe({
      next: (r: PaginatedResponse<EntregaListItem>) => {
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

  private currentFilters(): EntregaFilters {
    return {
      estado: this.filterEstado || undefined,
      q: this.filterQ || undefined,
      page: this.page(),
    };
  }

  estadoLabel(e: EntregaEstado): string {
    return e === 'enviada' ? 'Enviada' : e === 'validada' ? 'Validada' : 'Rechazada';
  }

  badgeClass(e: EntregaEstado): string {
    return e === 'validada'
      ? 'ui-badge--success'
      : e === 'rechazada'
        ? 'ui-badge--danger'
        : 'ui-badge--warning';
  }

  private parseError(err: { status?: number; message?: string }): string {
    if (err?.status === 403) return 'No tienes permiso para ver Jóvenes a la E.';
    if (err?.status === 401) return 'Sesión expirada. Vuelve a iniciar sesión.';
    if (err?.status === 0) return 'No se pudo conectar con el servidor.';
    return err?.message || 'Error inesperado al cargar.';
  }
}
