import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, OnInit, computed, effect, inject, signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';
import {
  ActividadesService, HubTiposResponse, SectorChip, TipoActividad,
} from '../../core/actividades/actividades.service';
import { LayoutService } from '../../core/layout/layout.service';
import { TourService } from '../onboarding/tour.service';

/**
 * Hub principal de Actividades — Angular nativo.
 *
 * Reemplaza el iframe al hub Django. Consume
 * `GET /api/actividades/tipos/` que ya filtra por módulos del usuario.
 */
@Component({
  standalone: true,
  selector: 'app-actividades-hub',
  imports: [CommonModule, RouterLink, LucideAngularModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="hub">
      <header class="hub__header" data-tour="actividades-titulo">
        <div class="hub__title-row">
          <div>
            <div class="hub__title-icon-row">
              <span class="hub__title-icon"><lucide-icon name="calendar-check" [size]="20"></lucide-icon></span>
              <h1>Actividades</h1>
            </div>
            <p class="hub__subtitle">
              Eventos, capacitaciones, cursos, inscripciones, caracterizaciones
              y entregas del territorio. Elige un área para ver su detalle.
            </p>
          </div>
          <div class="hub__actions">
            <a routerLink="/eventos" class="ui-btn">☰ Lista completa</a>
            <a routerLink="/eventos/nueva" class="ui-btn ui-btn--primary">+ Crear actividad</a>
          </div>
        </div>
      </header>

      @if (loading()) {
        <div class="hub__loading">Cargando…</div>
      } @else if (errorMsg()) {
        <div class="hub__error">⚠ {{ errorMsg() }}</div>
      } @else {

        <div class="hub__layout">
          <!-- SIDEBAR: áreas -->
          <aside class="hub-sidebar">
            <input
              class="hub-sidebar__search"
              type="text"
              placeholder="Buscar área…"
              [value]="busquedaArea()"
              (input)="busquedaArea.set($any($event.target).value)"
            />

            <button
              type="button"
              class="area-item area-item--todos"
              [class.area-item--active]="sectorFiltro() === null"
              (click)="filtrarSector(null)"
            >
              <span class="area-item__icon area-item__icon--neutral"><lucide-icon name="layout-grid" [size]="14"></lucide-icon></span>
              <span class="area-item__body">
                <span class="area-item__name">Todos · catálogo de tipos</span>
                <span class="area-item__count">{{ totalAreasCount() }} áreas · {{ totalEventosPorArea() }} eventos</span>
              </span>
            </button>

            @if (areasFiltradas().length) {
              <p class="hub-sidebar__label">ÁREAS</p>
              @for (a of areasFiltradas(); track a.subgrupo_id) {
                <button
                  type="button"
                  class="area-item"
                  [class.area-item--active]="sectorFiltro() === a.subgrupo_id"
                  [style.border-left-color]="sectorFiltro() === a.subgrupo_id ? a.color : 'transparent'"
                  [style.background]="sectorFiltro() === a.subgrupo_id ? areaTintBg(a.color) : null"
                  (click)="filtrarSector(a.subgrupo_id)"
                >
                  <span class="area-item__icon" [style.background]="a.color"><lucide-icon [name]="areaIcono(a.nombre)" [size]="14"></lucide-icon></span>
                  <span class="area-item__body">
                    <span class="area-item__name">{{ a.nombre }}</span>
                    <span class="area-item__count">{{ a.num_proyectos }} proyecto{{ a.num_proyectos === 1 ? '' : 's' }} · {{ a.num_eventos }} evento{{ a.num_eventos === 1 ? '' : 's' }}</span>
                  </span>
                </button>
              }
            }
          </aside>

          <!-- PANEL PRINCIPAL -->
          <div class="hub-main">
            @if (sectorFiltro() !== null && areaActiva(); as area) {
              <section class="hub-area-detail">
                <p class="hub-eyebrow">
                  Sector · {{ area.num_proyectos }} proyecto{{ area.num_proyectos === 1 ? '' : 's' }} ·
                  {{ area.num_eventos }} evento{{ area.num_eventos === 1 ? '' : 's' }}
                </p>
                <h2 class="hub-area-detail__name">{{ area.nombre }}</h2>

                <div class="kpi-row">
                  <div class="kpi-tile" [style.border-left-color]="area.color">
                    <strong>{{ area.num_proyectos }}</strong>
                    <span>proyecto{{ area.num_proyectos === 1 ? '' : 's' }}</span>
                  </div>
                  <div class="kpi-tile" [style.border-left-color]="area.color">
                    <strong>{{ area.num_eventos }}</strong>
                    <span>evento{{ area.num_eventos === 1 ? '' : 's' }}</span>
                  </div>
                </div>

                @if (tiposDeAreaActiva().length) {
                  <div class="tipo-acordeon">
                    @for (item of tiposDeAreaActiva(); track item.tipo.codigo) {
                      <div class="tipo-group">
                        <button
                          type="button"
                          class="tipo-group__header"
                          [attr.aria-expanded]="estaAbierto(item.tipo.codigo)"
                          (click)="toggleTipo(item.tipo.codigo)"
                        >
                          <lucide-icon [name]="lucideFa(item.tipo.icono)" [size]="18"></lucide-icon>
                          <span class="tipo-group__name">{{ item.tipo.nombre }}</span>
                          <span class="ui-badge">{{ item.chip!.count }} evento{{ item.chip!.count === 1 ? '' : 's' }}</span>
                          <span class="tipo-group__chev" [class.tipo-group__chev--open]="estaAbierto(item.tipo.codigo)">›</span>
                        </button>
                        @if (estaAbierto(item.tipo.codigo)) {
                          <div class="tipo-group__body">
                            <p>{{ item.tipo.descripcion || ('Actividades de tipo ' + item.tipo.codigo) }}</p>
                            <a [routerLink]="rutaTipo(item.tipo.codigo)" class="ui-btn ui-btn--sm">Ver actividades de este tipo</a>
                          </div>
                        }
                      </div>
                    }
                  </div>
                } @else {
                  <div class="ui-empty-state">
                    <i class="fa fa-info-circle"></i>
                    <p>Esta área no tiene tipos de actividad con eventos registrados todavía.</p>
                  </div>
                }
              </section>
            } @else {
              <section class="hub-catalogo">
                <p class="hub-eyebrow">Catálogo · {{ totalTiposCount() }} tipos · {{ totalEventosPorTipo() }} eventos</p>
                <h2 class="hub-catalogo__title">Todos los tipos de actividad</h2>
                <p class="hub-catalogo__hint">Un tipo puede usarse en más de un área.</p>

                @if (data()?.tipos?.length) {
                  <div class="catalogo-grid">
                    @for (t of data()!.tipos; track t.codigo) {
                      <a [routerLink]="rutaTipo(t.codigo)" class="catalogo-card">
                        <div class="catalogo-card__head">
                          <span class="catalogo-card__icon" [style.color]="t.color_hex">
                            <lucide-icon [name]="lucideFa(t.icono)" [size]="20"></lucide-icon>
                          </span>
                          <h3 class="catalogo-card__name">{{ t.nombre }}</h3>
                          <span class="ui-badge">{{ t.num_eventos }} evento{{ t.num_eventos === 1 ? '' : 's' }}</span>
                        </div>
                        <p class="catalogo-card__desc">
                          {{ t.descripcion || ('Actividades de tipo ' + t.codigo) }}
                        </p>
                        @if (t.por_sector?.length) {
                          <div class="catalogo-card__chips">
                            @for (c of t.por_sector!; track c.subgrupo_id) {
                              <span class="tipo-chip-inline" [attr.title]="c.nombre + ': ' + c.count">
                                <span class="tipo-chip-inline__dot" [style.background]="c.color"></span>
                                {{ c.nombre }} {{ c.count }}
                              </span>
                            }
                          </div>
                        } @else {
                          <p class="catalogo-card__empty">Sin eventos registrados todavía</p>
                        }
                      </a>
                    }
                  </div>
                } @else {
                  <div class="ui-empty-state">
                    <i class="fa fa-info-circle"></i>
                    <p>Tu rol no tiene acceso a ningún tipo de actividad.
                      Contacta al administrador.</p>
                  </div>
                }
              </section>
            }
          </div>
        </div>

        @if (data()?.cards_admin?.length) {
          <section class="hub-section">
            <h2 class="hub-section__title">Administrativo</h2>
            <div class="hub-grid">
              @for (c of data()!.cards_admin; track c.codigo) {
                <a [routerLink]="c.ruta"
                  class="ui-card ui-card--interactive"
                  [class]="'ui-card--' + c.color">
                  <div class="hub-card__icon">
                    <lucide-icon [name]="hubAdminIcon(c)" [size]="24"></lucide-icon>
                  </div>
                  <div class="ui-card__body">
                    <h3 class="ui-card__title">{{ c.nombre }}</h3>
                    <p class="ui-card__subtitle">{{ c.subtitulo }}</p>
                  </div>
                </a>
              }
            </div>
          </section>
        }
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .hub { max-width: 1200px; margin: 0 auto; }

    .hub__header {
      margin-bottom: $space-5;
      padding-top: $space-4;
      padding-bottom: $space-4;
      border-bottom: 1px solid $color-border;
    }
    .hub__title-row {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: $space-4;
      flex-wrap: wrap;
    }
    .hub__title-icon-row {
      display: flex;
      align-items: center;
      gap: $space-3;
    }
    .hub__title-icon {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 40px;
      height: 40px;
      border-radius: $radius-md;
      background: $color-primary;
      color: #fff;
      flex-shrink: 0;
    }
    .hub__title-row h1 {
      margin: 0;
      color: $color-text;
      font-size: 32px;
      font-weight: $font-weight-semibold;
    }
    .hub__subtitle {
      color: $color-text-muted;
      margin: $space-2 0 0;
      max-width: 640px;
    }
    .hub__actions {
      display: flex;
      gap: $space-2;
      flex-shrink: 0;
    }

    .hub__loading, .hub__error {
      padding: $space-4;
      text-align: center;
      color: $color-text-muted;
    }
    .hub__error { color: $color-danger; }

    .hub-section { margin-top: $space-5; }
    .hub-section__title {
      font-size: $font-size-md;
      color: $color-text-muted;
      letter-spacing: 0.01em;
      margin: 0 0 $space-3;
    }
    .hub-card__meta {
      display: block;
      margin-top: $space-1;
      color: $color-text-muted;
      font-size: $font-size-xs;
    }

    /* — Layout de dos columnas: sidebar + panel principal — */
    .hub__layout {
      display: grid;
      grid-template-columns: 290px 1fr;
      gap: $space-5;
      align-items: start;
      @media (max-width: #{$bp-md}) { grid-template-columns: 1fr; }
    }

    .hub-sidebar {
      display: flex;
      flex-direction: column;
      gap: $space-1;
      background: $color-bg;
      border: 1px solid $color-border;
      border-radius: $radius-lg;
      padding: $space-3;
    }
    .hub-sidebar__search {
      width: 100%;
      box-sizing: border-box;
      padding: $space-2 $space-3;
      margin-bottom: $space-2;
      border: 1px solid $color-border;
      border-radius: $radius-md;
      font-size: $font-size-sm;
      color: $color-text;
      &:focus-visible { outline: $focus-ring; outline-offset: $focus-ring-offset; }
    }
    .hub-sidebar__label {
      margin: $space-3 0 $space-1 $space-2;
      font-size: $font-size-xs;
      letter-spacing: 0.04em;
      color: $color-text-muted;
      font-weight: $font-weight-semibold;
    }

    .area-item {
      display: flex;
      align-items: center;
      gap: $space-2;
      width: 100%;
      box-sizing: border-box;
      padding: $space-2;
      border: 1px solid $color-border-strong;
      border-left: 3px solid transparent;
      border-radius: $radius-md;
      box-shadow: $shadow-xs;
      background: transparent;
      cursor: pointer;
      text-align: left;
      transition: background $transition-base;
      &:hover { background: $color-bg-muted; }
      &:focus-visible { outline: $focus-ring; outline-offset: $focus-ring-offset; }
      &--active { background: $color-bg-muted; }
    }
    .area-item__icon {
      width: 22px;
      height: 22px;
      border-radius: 6px;
      flex-shrink: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      &--neutral { background: $color-text-muted; }
    }
    .area-item__body {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }
    .area-item__name {
      font-size: $font-size-sm;
      font-weight: $font-weight-semibold;
      color: $color-text;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .area-item__count {
      font-size: $font-size-xs;
      color: $color-text-muted;
    }

    .hub-main { min-width: 0; }
    .hub-eyebrow {
      margin: 0 0 $space-1;
      font-size: $font-size-xs;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: $color-text-muted;
      font-weight: $font-weight-semibold;
    }
    .hub-area-detail__name {
      margin: 0 0 $space-4;
      color: $color-text;
    }
    .hub-catalogo__title {
      margin: 0 0 $space-1;
      color: $color-text;
    }
    .hub-catalogo__hint {
      margin: 0 0 $space-4;
      color: $color-text-muted;
      font-size: $font-size-sm;
    }

    .kpi-row {
      display: flex;
      gap: $space-3;
      margin-bottom: $space-5;
      flex-wrap: wrap;
    }
    .kpi-tile {
      flex: 1 1 140px;
      background: $color-bg;
      border: 1px solid $color-border;
      border-left: 4px solid $color-border;
      border-radius: $radius-lg;
      padding: $space-3 $space-4;
      strong { display: block; font-size: 28px; color: $color-text; line-height: 1.2; }
      span { font-size: $font-size-sm; color: $color-text-muted; }
    }

    .tipo-acordeon { display: flex; flex-direction: column; gap: $space-2; }
    .tipo-group {
      border: 1px solid $color-border;
      border-radius: $radius-lg;
      overflow: hidden;
    }
    .tipo-group__header {
      display: flex;
      align-items: center;
      gap: $space-2;
      width: 100%;
      box-sizing: border-box;
      padding: $space-3;
      border: none;
      background: $color-bg;
      cursor: pointer;
      text-align: left;
      font-size: $font-size-sm;
      font-weight: $font-weight-semibold;
      color: $color-text;
      &:focus-visible { outline: $focus-ring; outline-offset: $focus-ring-offset; }
    }
    .tipo-group__name { flex: 1; }
    .tipo-group__chev {
      display: inline-block;
      transition: transform $transition-base;
      color: $color-text-muted;
      &--open { transform: rotate(90deg); }
    }
    .tipo-group__body {
      padding: $space-3;
      border-top: 1px solid $color-border;
      background: $color-bg-muted;
      p { margin: 0 0 $space-2; color: $color-text-muted; font-size: $font-size-sm; }
    }

    .catalogo-grid {
      display: grid;
      gap: $space-3;
      grid-template-columns: 1fr;
      @media (min-width: #{$bp-md}) { grid-template-columns: repeat(2, 1fr); }
    }
    .catalogo-card {
      display: block;
      background: $color-bg;
      border: 1px solid $color-border-strong;
      border-radius: $radius-lg;
      box-shadow: $shadow-sm;
      padding: $space-4;
      text-decoration: none;
      color: inherit;
      transition: border-color $transition-base;
      &:hover { border-color: $color-text-muted; }
      &:focus-visible { outline: $focus-ring; outline-offset: $focus-ring-offset; }
    }
    .catalogo-card__head {
      display: flex;
      align-items: center;
      gap: $space-2;
      margin-bottom: $space-2;
    }
    .catalogo-card__icon { display: inline-flex; flex-shrink: 0; }
    .catalogo-card__name { flex: 1; margin: 0; font-size: $font-size-md; color: $color-text; }
    .catalogo-card__desc { margin: 0 0 $space-3; color: $color-text-muted; font-size: $font-size-sm; }
    .catalogo-card__empty { margin: 0; color: $color-text-muted; font-size: $font-size-xs; font-style: italic; }
    .catalogo-card__chips {
      display: flex;
      flex-wrap: wrap;
      gap: $space-2;
      padding-top: $space-3;
      border-top: 1px dashed $color-border;
    }
    .tipo-chip-inline {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: $font-size-xs;
      color: $color-text-muted;
    }
    .tipo-chip-inline__dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex-shrink: 0;
    }
  `],
})
export class ActividadesHubComponent implements OnInit {
  private svc = inject(ActividadesService);
  private layout = inject(LayoutService);
  private tour = inject(TourService);

  /** Mapea el icono fa-* (del backend) a un icono lucide por palabra clave. */
  /** Icono representativo por area (color se aplica aparte via a.color).
   * ResumenSector no trae icono desde el backend, solo nombre/color -- se mapea aqui,
   * autocontenido en este componente, sin depender de otros modulos. */
  private readonly AREA_ICONOS: Record<string, string> = {
    'Relacionamiento Interinstitucional': 'landmark',
    'Desarrollo Estratégico y Mejora': 'trending-up',
    'Seguridad': 'shield',
    'Cultura': 'music',
    'Deporte': 'target',
    'Educación': 'graduation-cap',
    'Infraestructura': 'building-2',
    'CPS y Planta': 'users',
    'Subsidio tipo C': 'coins',
  };

  areaIcono(nombre: string): string {
    return this.AREA_ICONOS[nombre] ?? 'layout-dashboard';
  }

  /** Tinte de fondo muy sutil (8% opacidad) del color reservado del area, para el
   * estado activo del sidebar. No modifica a.color en si -- solo lo usa para calcular
   * un rgba() de lectura, el hex original queda intacto donde ya se usaba. */
  areaTintBg(hex: string): string {
    const clean = (hex || '').replace('#', '');
    if (clean.length !== 6) return 'transparent';
    const r = parseInt(clean.substring(0, 2), 16);
    const g = parseInt(clean.substring(2, 4), 16);
    const b = parseInt(clean.substring(4, 6), 16);
    if (Number.isNaN(r) || Number.isNaN(g) || Number.isNaN(b)) return 'transparent';
    return `rgba(${r}, ${g}, ${b}, 0.08)`;
  }

  lucideFa(fa: string | null | undefined): string {
    const s = fa || '';
    if (/graduation|curso|educa|beca|joven/i.test(s)) return 'graduation-cap';
    if (/hand|heart|banco/i.test(s)) return 'hand-heart';
    if (/box|package|entrega|paquete/i.test(s)) return 'package';
    if (/clipboard|caracter|list-check/i.test(s)) return 'clipboard-list';
    if (/music|festival|party/i.test(s)) return 'party-popper';
    if (/vote/i.test(s)) return 'vote';
    if (/map|territor/i.test(s)) return 'map-pin';
    if (/user|persona|group/i.test(s)) return 'users';
    if (/file|document|certific/i.test(s)) return 'file-text';
    if (/plus|crear|nuev|add/i.test(s)) return 'plus';
    if (/tag/i.test(s)) return 'tags';
    if (/cog|gear|config|ajuste|settings/i.test(s)) return 'settings';
    if (/list/i.test(s)) return 'list';
    return 'calendar-check';
  }

  /** Icono fijo (frontend-only) para las tarjetas de acceso rapido de Administrativo. */
  hubAdminIcon(c: any): string {
    if (c?.nombre === 'Lista de actividades') return 'clipboard-list';
    if (c?.nombre === 'Crear actividad') return 'calendar-plus';
    if (c?.nombre === 'Tipos de actividad') return 'layout-grid';
    return this.lucideFa(c?.icono);
  }

  data = signal<HubTiposResponse | null>(null);
  loading = signal<boolean>(true);
  errorMsg = signal<string>('');

  /** Filtro de sector activo (subgrupo_id). Solo aplica a admin. */
  sectorFiltro = signal<number | null>(null);

  /** Las cards admin (Lista/Crear/Tipos) siguen apuntando al CRUD
   * Django mientras no haya editor de evento nativo. */
  djangoBase = '';

  /** Texto de búsqueda del sidebar (filtra la lista de áreas en cliente). */
  busquedaArea = signal('');

  /** Códigos de tipo con el acordeón abierto (solo UI, no persiste). */
  private tiposAbiertos = signal<Set<string>>(new Set());

  private tourArrancado = false;

  /** Entrada de resumen_sector correspondiente al área seleccionada. */
  areaActiva = computed(() => {
    const id = this.sectorFiltro();
    if (id === null) return null;
    return this.data()?.resumen_sector?.find((s) => s.subgrupo_id === id) ?? null;
  });

  /** Lista de áreas del sidebar, filtrada por el texto de búsqueda. */
  areasFiltradas = computed(() => {
    const areas = this.data()?.resumen_sector ?? [];
    const q = this.busquedaArea().trim().toLowerCase();
    return q ? areas.filter((a) => a.nombre.toLowerCase().includes(q)) : areas;
  });

  /** Tipos que tienen actividades dentro del área seleccionada, con su conteo por área
   * (cruce tipo × área que ya trae el propio catálogo en `por_sector`, sin inventar nada). */
  tiposDeAreaActiva = computed<{ tipo: TipoActividad; chip: SectorChip }[]>(() => {
    const id = this.sectorFiltro();
    if (id === null) return [];
    const out: { tipo: TipoActividad; chip: SectorChip }[] = [];
    for (const tipo of this.data()?.tipos ?? []) {
      const chip = tipo.por_sector?.find((c) => c.subgrupo_id === id);
      if (chip) out.push({ tipo, chip });
    }
    return out;
  });

  totalAreasCount = computed(() => this.data()?.resumen_sector?.length ?? 0);
  totalEventosPorArea = computed(() => (this.data()?.resumen_sector ?? [])
    .reduce((acc, s) => acc + (s.num_eventos || 0), 0));

  totalTiposCount = computed(() => this.data()?.tipos?.length ?? 0);
  totalEventosPorTipo = computed(() => (this.data()?.tipos ?? [])
    .reduce((acc, t) => acc + (t.num_eventos || 0), 0));

  constructor() {
    // Arranca el tour solo cuando los tipos ya están renderizados (data async),
    // así los pasos encuentran sus elementos y no quedan "cojos".
    effect(() => {
      if (this.data()?.tipos?.length && !this.tourArrancado) {
        this.tourArrancado = true;
        setTimeout(() => this.tour.iniciarSiProcede('actividades'), 400);
      }
    });
  }

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Actividades' },
    ]);
    this.cargar();
  }

  private cargar(): void {
    this.loading.set(true);
    this.svc.tipos(this.sectorFiltro()).subscribe({
      next: (r) => {
        this.data.set(r);
        this.loading.set(false);
      },
      error: () => {
        this.errorMsg.set('No se pudieron cargar los tipos de actividad.');
        this.loading.set(false);
      },
    });
  }

  /** Pulsar una pill: alterna el filtro por ese sector y recarga. */
  filtrarSector(id: number | null): void {
    this.sectorFiltro.set(this.sectorFiltro() === id ? null : id);
    this.cargar();
  }

  toggleTipo(codigo: string): void {
    const s = new Set(this.tiposAbiertos());
    if (s.has(codigo)) { s.delete(codigo); } else { s.add(codigo); }
    this.tiposAbiertos.set(s);
  }

  estaAbierto(codigo: string): boolean {
    return this.tiposAbiertos().has(codigo);
  }

  /** Caracterización tiene su hub propio; el resto va por /actividades/tipo. */
  rutaTipo(codigo: string): string[] {
    return codigo.toUpperCase() === 'CARACTERIZACION'
      ? ['/caracterizacion']
      : ['/actividades/tipo', codigo];
  }
}
