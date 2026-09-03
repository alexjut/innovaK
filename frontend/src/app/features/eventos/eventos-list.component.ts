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
          <div class="page__title-row">
            <span class="page__title-icon"><i class="fa fa-list"></i></span>
            <h1>Lista de actividades</h1>
          </div>
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
      <div class="kpi-row">
        @if (stats()) {
          <div class="kpi-tile">
            <span class="kpi-tile__icon kpi-tile__icon--red"><i class="fa fa-calendar-check"></i></span>
            <div class="kpi-tile__body">
              <strong class="kpi-tile__value">{{ stats()!.total }}</strong>
              <span class="kpi-tile__label">actividades totales</span>
            </div>
          </div>
          <div class="kpi-tile">
            <span class="kpi-tile__icon kpi-tile__icon--green"><i class="fa fa-check-circle"></i></span>
            <div class="kpi-tile__body">
              <strong class="kpi-tile__value">{{ stats()!.activas }}</strong>
              <span class="kpi-tile__label">activas</span>
            </div>
          </div>
          <div class="kpi-tile">
            <span class="kpi-tile__icon kpi-tile__icon--purple"><i class="fa fa-tags"></i></span>
            <div class="kpi-tile__body">
              <strong class="kpi-tile__value">{{ stats()!.tipos }}</strong>
              <span class="kpi-tile__label">tipos de actividad</span>
            </div>
          </div>
        }
      </div>

      <div class="ui-filter-bar">
        <label class="ui-search">
          <i class="fa fa-search"></i>
          <input type="search" [(ngModel)]="q" (input)="buscar()" placeholder="Buscar nombre, tipo, subgrupo…">
          <kbd>⌘K</kbd>
        </label>
        <div class="filtros-wrap">
          <button type="button" class="btn-filtros" [class.btn-filtros--active]="filtrosActivosCount() > 0" (click)="toggleFiltrosPanel()">
            <i class="fa fa-filter"></i> Filtros
            @if (filtrosActivosCount() > 0) { <span class="filtros-count">{{ filtrosActivosCount() }}</span> }
          </button>
          @if (filtrosActivosCount() > 0) {
            <button type="button" class="btn-limpiar-filtros" (click)="limpiarFiltros()">
              <i class="fa fa-times"></i> Limpiar filtros
            </button>
          }
          @if (filtrosPanelAbierto()) {
            <div class="filtros-panel">
              <div class="filtros-panel__group">
                <label class="filtros-panel__label">Tipo</label>
                <select [(ngModel)]="tipo" (change)="cargar()" class="filter-field">
                  <option value="">Todos los tipos</option>
                  @for (t of tipos(); track t.codigo) {
                    <option [value]="t.codigo">{{ t.nombre }}</option>
                  }
                </select>
              </div>
              <div class="filtros-panel__group">
                <label class="filtros-panel__label">Dependencia</label>
                <select [(ngModel)]="dependencia" (change)="onDepChange()" class="filter-field">
                  <option [ngValue]="null">Todas las dependencias</option>
                  @for (d of dependencias(); track d.id) {
                    <option [ngValue]="d.id">{{ d.nombre }}</option>
                  }
                </select>
              </div>
              <div class="filtros-panel__group">
                <label class="filtros-panel__label">Subgrupo</label>
                <select [(ngModel)]="subgrupo" (change)="cargar()" class="filter-field">
                  <option [ngValue]="null">Todos los subgrupos</option>
                  @for (s of subgruposFiltrados(); track s.id) {
                    <option [ngValue]="s.id">{{ s.nombre }}</option>
                  }
                </select>
              </div>
              <div class="filtros-panel__group">
                <label class="filtros-panel__label">Estado</label>
                <select [(ngModel)]="activo" (change)="cargar()" class="filter-field">
                  <option value="">Activos e inactivos</option>
                  <option value="1">Solo activos</option>
                  <option value="0">Solo inactivos</option>
                </select>
              </div>
            </div>
          }
        </div>
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
                    <td>
                      @if (e.dependencia_nombre) {
                        <span class="dep-badge">
                          <span class="dep-badge__icon" [style.background]="depColor(e.dependencia_nombre)"><i class="fa {{ depIcon(e.dependencia_nombre) }}"></i></span>
                          <span>{{ e.dependencia_nombre }}</span>
                        </span>
                      } @else { — }
                    </td>
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
                         class="ui-btn ui-btn--sm ui-btn--ghost ui-btn--ghost-red">
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
    .page { max-width: 1200px; margin: 0 auto; }
    .ui-btn--ghost-red { color: $color-primary; }
    .ui-btn--ghost-red:hover:not(:disabled) { color: $color-primary-dark; background: $color-bg-muted; }
    .page__header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: $space-3;
      flex-wrap: wrap;
      margin-bottom: $space-5;
      padding-top: $space-4;
      padding-bottom: $space-4;
      border-bottom: 1px solid $color-border;
      h1 { margin: 0; font-size: 32px; font-weight: $font-weight-semibold; &::after { content: ''; display: block; width: 48px; height: 4px; border-radius: $radius-pill; background: $color-secondary; margin-top: $space-2; } }
    }
    .kpi-row { display: flex; gap: $space-3; flex-wrap: wrap; margin-bottom: $space-4; }
    .kpi-tile {
      display: flex; align-items: center; gap: $space-3;
      background: #fff; border: 1px solid $color-border; border-radius: $radius-md;
      padding: $space-3 $space-4; flex: 1 1 200px; min-width: 200px;
    }
    .kpi-tile__icon {
      display: flex; align-items: center; justify-content: center;
      width: 40px; height: 40px; border-radius: $radius-md; color: #fff; font-size: 16px; flex-shrink: 0;
    }
    .kpi-tile__icon--red { background: $color-primary; }
    .kpi-tile__icon--green { background: #16A34A; }
    .kpi-tile__icon--purple { background: #6366F1; }
    .kpi-tile__body { display: flex; flex-direction: column; }
    .kpi-tile__value { font-size: 22px; font-weight: 700; color: $color-text; line-height: 1.1; }
    .kpi-tile__label { font-size: 12px; color: $color-text-muted; }
    .page__title-row { display: flex; align-items: center; gap: $space-3; }
    .page__title-icon {
      display: flex; align-items: center; justify-content: center;
      width: 40px; height: 40px; border-radius: $radius-md;
      background: $color-primary; color: #fff; flex-shrink: 0;
    }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 0; }
    .filter-field {
      padding: $space-1 $space-2;
      border: 1px solid $color-border;
      border-radius: $radius-sm;
      margin-right: $space-2;
      min-width: 180px;
    }
    .ui-search {
      display: flex; align-items: center; gap: $space-2;
      width: 320px; height: 38px; padding: 0 $space-3;
      background: $color-bg; border: 1px solid $color-border;
      border-radius: $radius-sm;
    }
    .ui-search i { color: $color-text-muted; flex-shrink: 0; }
    .ui-search input {
      border: none; outline: none; background: transparent;
      font-size: $font-size-sm; color: $color-text; width: 100%;
    }
    .ui-search kbd {
      font-size: 11px; color: $color-text-muted; background: $color-bg-muted;
      border: 1px solid $color-border; border-radius: 4px; padding: 1px 6px;
      flex-shrink: 0;
    }
    .filtros-wrap { position: relative; }
    .btn-filtros {
      display: flex; align-items: center; gap: $space-2;
      height: 38px; padding: 0 $space-3;
      background: $color-bg; border: 1px solid $color-border;
      border-radius: $radius-sm; font-size: $font-size-sm; font-weight: 600;
      color: $color-text; cursor: pointer;
    }
    .btn-filtros--active { border-color: $color-primary; color: $color-primary; }
    .btn-limpiar-filtros {
      display: flex; align-items: center; gap: $space-2;
      height: 38px; padding: 0 $space-3;
      background: $color-bg; border: 1px solid $color-border;
      border-radius: $radius-sm; font-size: $font-size-sm; font-weight: 600;
      color: #DC2626; cursor: pointer;
    }
    .filtros-count {
      background: $color-primary; color: #fff; font-size: 11px; font-weight: 700;
      border-radius: 999px; min-width: 18px; height: 18px; padding: 0 4px;
      display: inline-flex; align-items: center; justify-content: center;
    }
    .filtros-panel {
      position: absolute; top: 44px; left: 0; z-index: 5;
      width: 260px; background: $color-bg; border: 1px solid $color-border;
      border-radius: $radius-md; box-shadow: $shadow-md; padding: $space-3;
    }
    .filtros-panel__group { margin-bottom: $space-3; }
    .filtros-panel__group:last-child { margin-bottom: 0; }
    .filtros-panel__label {
      display: block; font-size: 11px; font-weight: 700; text-transform: uppercase;
      letter-spacing: .03em; color: $color-text-muted; margin: 0 0 $space-1;
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
    .dep-badge { display: inline-flex; align-items: center; gap: $space-2; }
    .dep-badge__icon {
      display: flex; align-items: center; justify-content: center;
      width: 22px; height: 22px; border-radius: 4px;
      color: #fff; font-size: 11px; flex-shrink: 0;
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
  stats = signal<{ total: number; activas: number; tipos: number } | null>(null);
  errorMsg = signal<string>('');
  page = signal<number>(1);

  q = '';
  tipo = '';
  dependencia: number | null = null;
  subgrupo: number | null = null;
  activo: '1' | '0' | '' = '';
  filtrosPanelAbierto = signal<boolean>(false);
  toggleFiltrosPanel(): void { this.filtrosPanelAbierto.update(v => !v); }
  filtrosActivosCount(): number {
    let n = 0;
    if (this.tipo) n++;
    if (this.dependencia !== null) n++;
    if (this.subgrupo !== null) n++;
    if (this.activo !== '') n++;
    return n;
  }
  limpiarFiltros(): void {
    this.q = '';
    this.tipo = '';
    this.dependencia = null;
    this.subgrupo = null;
    this.activo = '';
    this.page.set(1);
    this.cargar();
  }
  depColor(nombre: string | null | undefined): string {
    const n = (nombre || '').toLowerCase();
    if (n.includes('despacho')) return '#534AB7';
    if (n.includes('inversión') || n.includes('inversion')) return '#185FA5';
    return '#6B7280';
  }
  depIcon(nombre: string | null | undefined): string {
    const n = (nombre || '').toLowerCase();
    if (n.includes('despacho')) return 'fa-building';
    if (n.includes('inversión') || n.includes('inversion')) return 'fa-landmark';
    return 'fa-building';
  }

  subgruposFiltrados = computed<SubgrupoLite[]>(() => {
    const all = this.subgrupos();
    if (this.dependencia == null) return all;
    return all.filter(s => s.dependencia_id === this.dependencia);
  });

  private debounce: any;

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Actividades', url: '/actividades' },
      { label: 'Lista de actividades' },
    ]);
    this.geo.catalogos().subscribe(c => {
      this.tipos.set(c.tipos_evento);
      this.dependencias.set(c.dependencias);
      this.subgrupos.set(c.subgrupos);
    });
    this.cargar();
    this.cargarStats();
  }

  cargarStats(): void {
    this.api.lista({ page: 1, page_size: 200 }).subscribe({
      next: r => {
        const activas = r.results.filter(e => e.activo).length;
        const tiposSet = new Set(r.results.map(e => e.tipo_codigo).filter(Boolean));
        this.stats.set({ total: r.count, activas, tipos: tiposSet.size });
      },
    });
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
