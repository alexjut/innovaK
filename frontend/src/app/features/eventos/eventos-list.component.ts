import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, ElementRef, OnInit, QueryList,
  ViewChildren, computed, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import {
  DependenciaLite, GeoService, SubgrupoLite, TipoEventoLite,
} from '../../core/geo/geo.service';
import { LayoutService } from '../../core/layout/layout.service';
import { ConfirmService } from '../../shared/ui/confirm.service';
import { ToastService } from '../../shared/ui/toast.service';
import { EventosApi, EventosListaResponse } from './eventos.api';

@Component({
  standalone: true,
  selector: 'app-eventos-list',
  imports: [CommonModule, FormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      <header class="page__header">
        <div>
          <h1><i class="fa fa-list"></i> Lista de actividades</h1>
          <p class="page__subtitle">
            Todas las actividades del territorio.
            @if (data()) { <strong>{{ data()!.count }}</strong> total }
          </p>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          <a routerLink="/eventos/insights" class="ui-btn ui-btn--ghost">
            <i class="fa fa-chart-line"></i> Insights
          </a>
          <a routerLink="/eventos/nueva" class="ui-btn ui-btn--primary">
            <i class="fa fa-plus-circle"></i> Crear actividad
          </a>
        </div>
      </header>

      <div class="ui-filter-bar">
        <input type="search" [(ngModel)]="q"
               (input)="buscar()"
               placeholder="Buscar nombre, tipo, subgrupo…"
               class="filter-field">
        <select [(ngModel)]="tipo" (change)="cargar()" class="filter-field">
          <option value="">Todos los tipos</option>
          @for (t of tipos(); track t.codigo) {
            <option [value]="t.codigo">{{ t.nombre }}</option>
          }
        </select>
        <select [(ngModel)]="dependencia"
                (change)="onDepChange()" class="filter-field">
          <option [ngValue]="null">Todas las dependencias</option>
          @for (d of dependencias(); track d.id) {
            <option [ngValue]="d.id">{{ d.nombre }}</option>
          }
        </select>
        <select [(ngModel)]="subgrupo" (change)="cargar()" class="filter-field">
          <option [ngValue]="null">Todos los subgrupos</option>
          @for (s of subgruposFiltrados(); track s.id) {
            <option [ngValue]="s.id">{{ s.nombre }}</option>
          }
        </select>
        <select [(ngModel)]="activo" (change)="cargar()" class="filter-field">
          <option value="">Activos e inactivos</option>
          <option value="1">Solo activos</option>
          <option value="0">Solo inactivos</option>
        </select>
      </div>

      @if (loading()) {
        <div class="page__loading">Cargando…</div>
      } @else if (errorMsg()) {
        <div class="page__error">⚠ {{ errorMsg() }}</div>
      } @else if (data()) {
        @let d = data()!;
        @if (d.results.length) {
          <div class="table-scroll">
          <div class="ui-table-responsive" #scrollWrap (scroll)="onTableScroll($event)">
            <table class="ui-table">
              <thead>
                <tr>
                  <th>#</th><th>Nombre</th><th>Tipo</th>
                  <th>Dependencia</th><th>Subgrupo</th>
                  <th>Fechas</th><th>Funcionario</th><th>Activo</th><th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                @for (e of d.results; track e.id) {
                  <tr>
                    <td>{{ e.id }}</td>
                    <td><strong>{{ e.nombre || '—' }}</strong></td>
                    <td><span class="ui-badge ui-badge--info">{{ e.tipo_nombre || e.tipo_codigo }}</span></td>
                    <td>{{ e.dependencia_nombre || '—' }}</td>
                    <td>{{ e.subgrupo_nombre || '—' }}</td>
                    <td>
                      @if (e.fecha_inicio) {
                        <small>{{ e.fecha_inicio }} → {{ e.fecha_fin || '—' }}</small>
                      } @else { — }
                    </td>
                    <td>{{ e.funcionario_nombre || '—' }}</td>
                    <td>
                      <button (click)="toggle(e)" class="toggle-btn"
                              [class.is-active]="e.activo">
                        {{ e.activo ? 'Activo' : 'Inactivo' }}
                      </button>
                    </td>
                    <td>
                      <a [routerLink]="['/eventos', e.id, 'editar']"
                         class="ui-btn ui-btn--sm ui-btn--ghost">
                        <i class="fa fa-edit"></i> Editar
                      </a>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
            <span class="table-scroll__fade" [class.is-hidden]="scrollAtEnd()"
                  aria-hidden="true"></span>
          </div>

          @if (d.count > d.page_size) {
            <div class="pagination">
              <button (click)="prev()" [disabled]="page() <= 1">‹ Anterior</button>
              <span>Página {{ d.page }} / {{ totalPages() }}</span>
              <button (click)="next()" [disabled]="page() >= totalPages()">Siguiente ›</button>
            </div>
          }
        } @else {
          <div class="ui-empty-state">
            <i class="fa fa-folder-open"></i>
            <p>Sin actividades con los filtros actuales.</p>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1300px; margin: 0 auto; }
    .page__header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: $space-3;
      flex-wrap: wrap;
      margin-bottom: $space-3;
      h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 0; }
    .filter-field {
      padding: $space-1 $space-2;
      border: 1px solid $color-border;
      border-radius: $radius-sm;
      margin-right: $space-2;
      min-width: 180px;
    }
    .toggle-btn {
      background: $color-bg-subtle;
      border: 1px solid $color-border;
      padding: 2px 10px;
      border-radius: $radius-pill;
      font-size: $font-size-xs;
      cursor: pointer;
      &.is-active { background: rgba(22,163,74,0.12); border-color: $color-success; color: $color-success; }
    }
    .pagination {
      margin-top: $space-3;
      display: flex;
      gap: $space-2;
      align-items: center;
      justify-content: center;
      button {
        background: $color-bg;
        border: 1px solid $color-border;
        padding: $space-1 $space-3;
        border-radius: $radius-md;
        cursor: pointer;
        &:disabled { opacity: 0.4; cursor: not-allowed; }
      }
    }
    .page__loading, .page__error { padding: $space-4; text-align: center; color: $color-text-muted; }
    .page__error { color: $color-danger; }
    /* Indicador de scroll horizontal: sombra-fade en el borde derecho
       cuando hay más columnas fuera del viewport (GEN-UX-01). */
    .table-scroll { position: relative; }
    .table-scroll .ui-table-responsive { overflow-x: auto; }
    .table-scroll__fade {
      position: absolute;
      top: 0; right: 0; bottom: 0;
      width: 36px;
      pointer-events: none;
      background: linear-gradient(to right, rgba(255,255,255,0), rgba(0,0,0,0.10));
      transition: opacity 0.2s;
      &.is-hidden { opacity: 0; }
    }
  `],
})
export class EventosListComponent implements OnInit {
  private api = inject(EventosApi);
  private geo = inject(GeoService);
  private layout = inject(LayoutService);
  private confirm = inject(ConfirmService);
  private toast = inject(ToastService);
  scrollAtEnd = signal<boolean>(true);
  @ViewChildren('scrollWrap') private scrollWraps!: QueryList<ElementRef<HTMLElement>>;

  data = signal<EventosListaResponse | null>(null);
  tipos = signal<TipoEventoLite[]>([]);
  dependencias = signal<DependenciaLite[]>([]);
  subgrupos = signal<SubgrupoLite[]>([]);
  loading = signal<boolean>(true);
  errorMsg = signal<string>('');
  page = signal<number>(1);

  q = '';
  tipo = '';
  dependencia: number | null = null;
  subgrupo: number | null = null;
  activo: '1' | '0' | '' = '';

  subgruposFiltrados = computed<SubgrupoLite[]>(() => {
    const all = this.subgrupos();
    if (this.dependencia == null) return all;
    return all.filter(s => s.dependencia_id === this.dependencia);
  });

  private debounce: any;

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Lista de actividades' },
    ]);
    this.geo.catalogos().subscribe(c => {
      this.tipos.set(c.tipos_evento);
      this.dependencias.set(c.dependencias);
      this.subgrupos.set(c.subgrupos);
    });
    this.cargar();
  }

  onDepChange(): void {
    this.subgrupo = null;
    this.cargar();
  }

  cargar(): void {
    this.loading.set(true);
    this.api.lista({
      q: this.q || undefined,
      tipo: this.tipo || undefined,
      dependencia_id: this.dependencia ?? undefined,
      subgrupo_id: this.subgrupo ?? undefined,
      activo: this.activo || undefined,
      page: this.page(),
      page_size: 50,
    }).subscribe({
      next: r => {
        this.data.set(r); this.loading.set(false);
        // Tras render, decide si mostrar el fade (hay overflow horizontal).
        setTimeout(() => this.recomputarFade(), 0);
      },
      error: () => {
        this.errorMsg.set('No se pudieron cargar las actividades.');
        this.loading.set(false);
      },
    });
  }

  buscar(): void {
    clearTimeout(this.debounce);
    this.debounce = setTimeout(() => {
      this.page.set(1);
      this.cargar();
    }, 300);
  }

  async toggle(e: { id: number; nombre: string | null; activo: boolean }): Promise<void> {
    // Desactivar es de alto impacto (saca del mapa y de los KPIs): confirma.
    if (e.activo) {
      const ok = await this.confirm.ask({
        title: 'Desactivar actividad',
        message: `¿Desactivar «${e.nombre || 'esta actividad'}»? Saldrá del mapa `
          + 'y dejará de sumar a los KPIs.',
        danger: true,
        confirmText: 'Desactivar',
        cancelText: 'Cancelar',
      });
      if (!ok) return;
    }
    this.api.toggleActivo(e.id).subscribe({
      next: r => {
        this.toast.success(r.activo ? 'Actividad activada.' : 'Actividad desactivada.');
        this.cargar();
      },
      error: () => this.toast.error('No se pudo cambiar el estado.'),
    });
  }

  /** Oculta el fade del scroll cuando la tabla llega al borde derecho. */
  onTableScroll(ev: Event): void {
    const el = ev.target as HTMLElement;
    const atEnd = el.scrollLeft + el.clientWidth >= el.scrollWidth - 2;
    this.scrollAtEnd.set(atEnd);
  }

  /** Muestra el fade solo si hay columnas fuera del viewport. */
  private recomputarFade(): void {
    const el = this.scrollWraps?.first?.nativeElement;
    if (!el) { this.scrollAtEnd.set(true); return; }
    const overflow = el.scrollWidth > el.clientWidth + 2;
    const atEnd = el.scrollLeft + el.clientWidth >= el.scrollWidth - 2;
    this.scrollAtEnd.set(!overflow || atEnd);
  }

  totalPages(): number {
    const d = this.data();
    if (!d) return 1;
    return Math.max(1, Math.ceil(d.count / d.page_size));
  }
  prev(): void { if (this.page() > 1) { this.page.update(v => v - 1); this.cargar(); } }
  next(): void {
    if (this.page() < this.totalPages()) { this.page.update(v => v + 1); this.cargar(); }
  }
}
