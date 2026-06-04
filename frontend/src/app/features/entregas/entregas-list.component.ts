import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { EntregasService } from './entregas.service';
import {
  EntregaEstado,
  EntregaFilters,
  EntregaInsumoListItem,
  PaginatedResponse,
} from './entregas.types';

/**
 * Lista paginada de entregas de insumos (organizador autenticado).
 *
 * Datos: `apps/entregas/api/views.py::EntregaListView`.
 * Lee `?evento=` del queryParam para filtrar por evento de captura
 * cuando se llega desde el hub de Actividades.
 */
@Component({
  standalone: true,
  selector: 'app-entregas-list',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <div>
          <h1>
            <i class="fa fa-box-open" aria-hidden="true"></i>
            Entrega de insumos
          </h1>
          <p class="page__subtitle">
            Registro de insumos entregados a beneficiarios.
            @if (eventoFiltrado()) {
              Filtrado por evento #{{ eventoFiltrado() }}.
            }
          </p>
        </div>
      </header>

      <!-- KPI chips por estado -->
      <div class="estado-chips" role="group" aria-label="Filtrar por estado">
        @for (chip of estadoChips; track chip.value) {
          <button
            class="ui-chip"
            [class.ui-chip--active]="filterEstado === chip.value"
            [class]="'ui-chip ' + chip.cls + (filterEstado === chip.value ? ' ui-chip--active' : '')"
            (click)="setEstado(chip.value)"
          >
            {{ chip.label }}
            @if (chip.count !== null) {
              <span class="ui-chip__count">{{ chip.count }}</span>
            }
          </button>
        }
      </div>

      <!-- Barra de filtros -->
      <div class="ui-filter-bar">
        <div class="ui-filter-bar__group">
          <label class="ui-filter-bar__label" for="f-q">Buscar</label>
          <input
            id="f-q"
            type="search"
            class="ui-filter-bar__field"
            placeholder="Documento o nombre…"
            [(ngModel)]="filterQ"
            (keyup.enter)="applyFilters()"
          />
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

      <!-- Estados de carga / error -->
      @if (loading()) {
        <div class="ui-info-bar ui-info-bar--info">
          <i class="fa fa-spinner fa-spin" aria-hidden="true"></i>
          Cargando entregas…
        </div>
      }
      @if (!loading() && errorMsg()) {
        <div class="ui-info-bar ui-info-bar--danger">
          <strong>Error:</strong> {{ errorMsg() }}
        </div>
      }

      <!-- Empty state -->
      @if (!loading() && !errorMsg() && rows().length === 0) {
        <div class="ui-empty-state">
          <i class="fa fa-box-open fa-2x" aria-hidden="true"></i>
          <p>No hay entregas para los filtros aplicados.</p>
          @if (filterEstado || filterQ) {
            <button class="ui-btn ui-btn--outline ui-btn--sm" (click)="clearFilters()">
              Quitar filtros
            </button>
          }
        </div>
      }

      <!-- Tabla -->
      @if (!loading() && !errorMsg() && rows().length > 0) {
        <div class="ui-table-responsive">
          <table class="ui-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Documento</th>
                <th>Nombre</th>
                <th>Evento</th>
                <th class="ui-table__cell--center">Estado</th>
                <th class="ui-table__cell--right">Fecha</th>
                <th class="ui-table__cell--right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              @for (row of rows(); track row.id) {
                <tr [class.row--validada]="row.estado === 'validada'"
                    [class.row--rechazada]="row.estado === 'rechazada'">
                  <td class="row__id">{{ row.id }}</td>
                  <td>
                    <code class="small">{{ row.numero_documento }}</code>
                    @if (row.tipo_doc_codigo) {
                      <small class="muted d-block">{{ row.tipo_doc_codigo }}</small>
                    }
                  </td>
                  <td>{{ row.nombre_completo || '—' }}</td>
                  <td>
                    @if (row.evento_nombre) {
                      <span class="evento-nombre">{{ row.evento_nombre }}</span>
                      @if (row.evento_id) {
                        <small class="muted d-block">#{{ row.evento_id }}</small>
                      }
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
                    <small class="muted">{{ row.created_at | date: 'dd/MM/yy' }}</small>
                  </td>
                  <td class="ui-table__cell--right">
                    <a [routerLink]="['/entregas', row.id]"
                       class="ui-btn ui-btn--outline ui-btn--sm"
                       [attr.aria-label]="'Ver entrega #' + row.id">
                      <i class="fa fa-eye" aria-hidden="true"></i> Ver
                    </a>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>

        <!-- Paginación -->
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

    .page__header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: $space-3;
      flex-wrap: wrap;
      margin-bottom: $space-4;
    }
    .page__header h1 {
      margin: 0;
      color: $color-primary;
      i { margin-right: $space-2; }
    }
    .page__subtitle {
      color: $color-text-muted;
      margin: $space-1 0 0;
    }

    /* Chips de estado */
    .estado-chips {
      display: flex;
      flex-wrap: wrap;
      gap: $space-2;
      margin-bottom: $space-4;
    }
    .ui-chip {
      display: inline-flex;
      align-items: center;
      gap: $space-1;
      padding: $space-1 $space-3;
      border-radius: $radius-pill;
      border: 1.5px solid $color-border;
      background: $color-bg-subtle;
      color: $color-text-muted;
      font-size: $font-size-sm;
      font-weight: $font-weight-medium;
      cursor: pointer;
      transition: all 0.15s ease;

      &:hover { border-color: $color-primary; color: $color-primary; }

      &--active {
        border-color: $color-primary;
        background: $color-primary;
        color: #fff;

        .ui-chip__count { background: rgba(255,255,255,.25); }
      }

      &--warning.ui-chip--active  { border-color: $color-warning; background: $color-warning; color: #000; }
      &--success.ui-chip--active  { border-color: $color-success; background: $color-success; color: #fff; }
      &--danger.ui-chip--active   { border-color: $color-danger;  background: $color-danger;  color: #fff; }
    }
    .ui-chip__count {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 20px;
      height: 20px;
      padding: 0 $space-1;
      border-radius: $radius-pill;
      background: rgba(0,0,0,.08);
      font-size: $font-size-xs;
      font-weight: $font-weight-bold;
      line-height: 1;
    }

    /* Tabla */
    .row__id { color: $color-text-muted; font-size: $font-size-sm; }
    .row--validada td:first-child { border-left: 3px solid $color-success; }
    .row--rechazada td:first-child { border-left: 3px solid $color-danger; }
    .evento-nombre {
      font-size: $font-size-sm;
      max-width: 200px;
      display: block;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .pagination {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: $space-4;
      gap: $space-3;
    }
    .pagination__info { color: $color-text-muted; font-size: $font-size-sm; }

    .muted { color: $color-text-muted; }
    .small { font-size: $font-size-xs; }
    .d-block { display: block; }
  `],
})
export class EntregasListComponent implements OnInit {
  private svc = inject(EntregasService);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);

  loading = signal<boolean>(false);
  errorMsg = signal<string>('');
  rows = signal<EntregaInsumoListItem[]>([]);
  count = signal<number>(0);
  page = signal<number>(1);
  nextUrl = signal<string | null>(null);
  eventoFiltrado = signal<number | null>(null);

  filterEstado: EntregaEstado | '' = '';
  filterQ = '';

  hasNext = computed(() => !!this.nextUrl());

  readonly estadoChips: Array<{
    value: EntregaEstado | '';
    label: string;
    cls: string;
    count: number | null;
  }> = [
    { value: '',          label: 'Todas',     cls: '',                count: null },
    { value: 'enviada',   label: 'Enviadas',  cls: 'ui-chip--warning', count: null },
    { value: 'validada',  label: 'Validadas', cls: 'ui-chip--success', count: null },
    { value: 'rechazada', label: 'Rechazadas',cls: 'ui-chip--danger',  count: null },
  ];

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Entrega de insumos' },
    ]);

    // Lee ?evento= del queryParam para filtrar por evento de captura.
    const eventoParam = this.route.snapshot.queryParamMap.get('evento');
    if (eventoParam && !isNaN(Number(eventoParam))) {
      this.eventoFiltrado.set(Number(eventoParam));
    }

    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.errorMsg.set('');
    this.svc.list(this.currentFilters()).subscribe({
      next: (r: PaginatedResponse<EntregaInsumoListItem>) => {
        this.rows.set(r.results);
        this.count.set(r.count);
        this.nextUrl.set(r.next);
        this.loading.set(false);
      },
      error: (e) => {
        this.loading.set(false);
        this.errorMsg.set(this.parseError(e));
      },
    });
  }

  setEstado(value: EntregaEstado | ''): void {
    this.filterEstado = value;
    this.applyFilters();
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
      evento: this.eventoFiltrado() ?? undefined,
      q: this.filterQ || undefined,
      page: this.page(),
    };
  }

  estadoLabel(e: EntregaEstado): string {
    const map: Record<EntregaEstado, string> = {
      enviada: 'Enviada',
      validada: 'Validada',
      rechazada: 'Rechazada',
    };
    return map[e] ?? e;
  }

  badgeClass(e: EntregaEstado): string {
    return e === 'validada'
      ? 'ui-badge--success'
      : e === 'rechazada'
        ? 'ui-badge--danger'
        : 'ui-badge--warning';
  }

  private parseError(err: { status?: number; message?: string }): string {
    if (err?.status === 403) return 'No tienes permiso para ver las entregas de insumos.';
    if (err?.status === 401) return 'Sesión expirada. Vuelve a iniciar sesión.';
    if (err?.status === 0) return 'No se pudo conectar con el servidor.';
    return err?.message || 'Error inesperado al cargar.';
  }
}
