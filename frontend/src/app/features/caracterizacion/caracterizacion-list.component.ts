import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { CaracterizacionApi } from './caracterizacion.api';
import {
  CaractListItem,
  CaractSector,
  PaginatedResponse,
  SECTORES,
} from './caracterizacion.types';

/**
 * Lista paginada de caracterizaciones de un sector. El sector viene
 * por param `:sector` de la URL.
 */
@Component({
  standalone: true,
  selector: 'app-caracterizacion-list',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <div class="page__header-row">
          <div>
            <h1>
              <i class="fa" [class]="meta()?.icon" aria-hidden="true"></i>
              {{ meta()?.label || sector() }}
            </h1>
            <p class="page__subtitle">Caracterizaciones registradas en el sector.</p>
          </div>
          <a [routerLink]="['/caracterizacion', 'registrar', sector()]"
             class="ui-btn ui-btn--primary">
            <i class="fa fa-plus" aria-hidden="true"></i> Registrar caracterización
          </a>
        </div>
      </header>

      @if (loading()) {
        <div class="ui-info-bar ui-info-bar--info">Cargando…</div>
      }
      @if (!loading() && errorMsg()) {
        <div class="ui-info-bar ui-info-bar--danger">
          <strong>Error:</strong> {{ errorMsg() }}
        </div>
      }
      @if (!loading() && !errorMsg() && rows().length === 0) {
        <div class="ui-empty-state">
          <i class="fa fa-folder-open" aria-hidden="true"></i>
          <p>No hay registros para este sector aún.</p>
        </div>
      }
      @if (!loading() && !errorMsg() && rows().length > 0) {
        <div class="ui-table-responsive">
          <table class="ui-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Persona</th>
                <th>Evento</th>
                <th class="ui-table__cell--right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              @for (row of rows(); track row.id) {
                <tr>
                  <td>{{ row.id }}</td>
                  <td>{{ row.persona_nombre || ('Persona #' + row.persona_id) }}</td>
                  <td>{{ row.evento_nombre || '—' }}</td>
                  <td class="ui-table__cell--right">
                    <a [routerLink]="['/caracterizacion', sector(), row.id]"
                       class="ui-btn ui-btn--outline ui-btn--sm">
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
    .page__header-row {
      display: flex; justify-content: space-between; align-items: flex-start;
      gap: $space-3; flex-wrap: wrap;
    }
    .page__header h1 { margin: 0; color: $color-primary; }
    .page__header h1 i { margin-right: $space-2; }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-4; }
    .pagination {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: $space-4;
      gap: $space-3;
    }
    .pagination__info { color: $color-text-muted; font-size: $font-size-sm; }
  `],
})
export class CaracterizacionListComponent implements OnInit {
  private api = inject(CaracterizacionApi);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);

  sector = signal<CaractSector>('cultura');
  loading = signal<boolean>(false);
  errorMsg = signal<string>('');
  rows = signal<CaractListItem[]>([]);
  count = signal<number>(0);
  page = signal<number>(1);
  next = signal<string | null>(null);

  hasNext = computed(() => !!this.next());
  meta = computed(() => SECTORES.find((s) => s.codigo === this.sector()));

  ngOnInit(): void {
    this.route.paramMap.subscribe((pm) => {
      const s = (pm.get('sector') || 'cultura') as CaractSector;
      this.sector.set(s);
      this.layout.setBreadcrumb([
        { label: 'Inicio', url: '/' },
        { label: 'Caracterización', url: '/caracterizacion' },
        { label: this.meta()?.label || s },
      ]);
      this.page.set(1);
      this.load();
    });
  }

  load(): void {
    this.loading.set(true);
    this.errorMsg.set('');
    this.api.list(this.sector(), { page: this.page() }).subscribe({
      next: (r: PaginatedResponse<CaractListItem>) => {
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

  private parseError(err: { status?: number; message?: string }): string {
    if (err?.status === 403) return 'No tienes permiso para ver caracterizaciones.';
    if (err?.status === 401) return 'Sesión expirada.';
    if (err?.status === 0) return 'No se pudo conectar.';
    return err?.message || 'Error inesperado.';
  }
}
