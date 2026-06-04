import { CommonModule, DecimalPipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { PresupuestoApi } from './presupuesto.api';
import { ENTIDADES, PresupEntidad, PresupItem } from './presupuesto.types';

/**
 * Lista genérica parametrizada por entidad de presupuesto. Las columnas
 * vienen del catálogo `ENTIDADES`.
 */
@Component({
  standalone: true,
  selector: 'app-presupuesto-list',
  imports: [CommonModule, RouterLink, DecimalPipe],
  template: `
    <div class="page">
      <header class="page__header">
        <h1>
          <i class="fa" [class]="meta()?.icon" aria-hidden="true"></i>
          {{ meta()?.label }}
        </h1>
        <p class="page__subtitle">{{ count() }} registros</p>
      </header>

      @if (loading()) {
        <div class="ui-info-bar ui-info-bar--info">Cargando…</div>
      }
      @if (!loading() && errorMsg()) {
        <div class="ui-info-bar ui-info-bar--danger">{{ errorMsg() }}</div>
      }
      @if (!loading() && !errorMsg() && rows().length === 0) {
        <div class="ui-empty-state">
          <i class="fa fa-folder-open" aria-hidden="true"></i>
          <p>Sin registros para mostrar.</p>
        </div>
      }
      @if (!loading() && !errorMsg() && rows().length > 0 && meta(); as m) {
        <div class="ui-table-responsive">
          <table class="ui-table">
            <thead>
              <tr>
                <th>#</th>
                @for (col of m.columnas; track col.key) {
                  <th>{{ col.label }}</th>
                }
                <th class="ui-table__cell--right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              @for (row of rows(); track row.id) {
                <tr>
                  <td>{{ row.id }}</td>
                  @for (col of m.columnas; track col.key) {
                    <td>{{ formatCell(row, col) }}</td>
                  }
                  <td class="ui-table__cell--right">
                    <a [routerLink]="['/presupuesto', entidad(), row.id]"
                       class="ui-btn ui-btn--outline ui-btn--sm">
                      <i class="fa fa-eye" aria-hidden="true"></i> Ver
                    </a>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>

        <nav class="pagination">
          <button class="ui-btn ui-btn--ghost ui-btn--sm"
                  (click)="prevPage()" [disabled]="page() === 1">
            ← Anterior
          </button>
          <span class="pagination__info">
            Página {{ page() }} · {{ count() }} total
          </span>
          <button class="ui-btn ui-btn--ghost ui-btn--sm"
                  (click)="nextPage()" [disabled]="!hasNext()">
            Siguiente →
          </button>
        </nav>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1200px; margin: 0 auto; }
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
export class PresupuestoListComponent implements OnInit {
  private api = inject(PresupuestoApi);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);

  entidad = signal<PresupEntidad>('proyectos');
  loading = signal<boolean>(false);
  errorMsg = signal<string>('');
  rows = signal<PresupItem[]>([]);
  count = signal<number>(0);
  page = signal<number>(1);
  next = signal<string | null>(null);

  hasNext = computed(() => !!this.next());
  meta = computed(() => ENTIDADES.find((e) => e.codigo === this.entidad()));

  ngOnInit(): void {
    this.route.paramMap.subscribe((pm) => {
      const e = (pm.get('entidad') || 'proyectos') as PresupEntidad;
      this.entidad.set(e);
      this.layout.setBreadcrumb([
        { label: 'Inicio', url: '/' },
        { label: 'Presupuesto', url: '/presupuesto' },
        { label: this.meta()?.label || e },
      ]);
      this.page.set(1);
      this.load();
    });
  }

  load(): void {
    this.loading.set(true);
    this.errorMsg.set('');
    this.api.list(this.entidad(), this.page()).subscribe({
      next: (r) => {
        this.rows.set(r.results);
        this.count.set(r.count);
        this.next.set(r.next);
        this.loading.set(false);
      },
      error: (e) => {
        this.loading.set(false);
        this.errorMsg.set(e.status === 403 ? 'Sin permiso.' : `Error ${e.status}.`);
      },
    });
  }

  nextPage(): void {
    if (this.hasNext()) { this.page.update((p) => p + 1); this.load(); }
  }
  prevPage(): void {
    if (this.page() > 1) { this.page.update((p) => p - 1); this.load(); }
  }

  formatCell(row: PresupItem, col: { key: string; type?: string }): string {
    const v = (row as Record<string, unknown>)[col.key];
    if (v === null || v === undefined || v === '') return '—';
    if (col.type === 'money' && typeof v === 'number') {
      return '$ ' + v.toLocaleString('es-CO');
    }
    if (col.type === 'money' && typeof v === 'string') {
      const n = Number(v);
      if (!isNaN(n)) return '$ ' + n.toLocaleString('es-CO');
    }
    if (col.type === 'percent') return `${v}%`;
    return String(v);
  }
}
