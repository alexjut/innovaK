import { CommonModule } from '@angular/common';
import {
  Component, ElementRef, HostListener, OnInit, ViewChild, computed, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';
import { LayoutService } from '../../core/layout/layout.service';
import { SubgrupoApi } from './subgrupo.api';
import { SubgrupoLite } from './subgrupo.types';

/** Grupo de áreas de una misma dependencia (proyección de presentación). */
interface DepGrupo {
  nombre: string;          // nombre legible (sentence case) de la dependencia
  color: string;           // color de acento de la dependencia
  icono: string;            // ícono lucide (kebab-case) de la dependencia
  areas: SubgrupoLite[];   // ordenadas: más eventos primero, las 0 al final
  total: number;
  conEventos: number;
  todasCero: boolean;
}

type Vista = 'tarjetas' | 'compacta';
type FiltroActividad = 'todas' | 'con' | 'sin';

// Color de acento POR DEPENDENCIA (no por área). Distinto del rojo
// institucional. Clave normalizada (minúsculas, sin tildes).
const DEP_COLORS: Record<string, string> = {
  'inversion local': '#185fa5',
  'despacho': '#534ab7',
  'administrativo y financiero': '#ba7517',
  'inspecciones de policia': '#5f5e5a',
  'gestion policiva y juridica': '#0f6e56',
};
const DEP_FALLBACK = ['#185fa5', '#534ab7', '#ba7517', '#0f6e56', '#5f5e5a', '#9b59b6'];

// Ícono lucide (kebab-case) POR DEPENDENCIA, mismo criterio que DEP_COLORS.
const DEP_ICONS: Record<string, string> = {
  'inversion local': 'landmark',
  'despacho': 'building-2',
  'administrativo y financiero': 'wallet',
  'inspecciones de policia': 'shield',
  'gestion policiva y juridica': 'scale',
};
const DEP_ICON_FALLBACK = 'building-2';

function normaliza(s: string): string {
  return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
}
function sentenceCase(s: string): string {
  const t = (s || '').trim();
  return t ? t.charAt(0).toUpperCase() + t.slice(1).toLowerCase() : t;
}

/**
 * Entrada del panel operativo por ÁREA (RBAC B4 · rediseño UX hub de Áreas).
 *
 * NOTA: "Área" es solo la etiqueta visible. Por dentro el modelo, las rutas
 * (`/subgrupo`), el endpoint y el RBAC siguen llamándose `subgrupo`.
 *
 * Lista las áreas visibles del usuario (`/subgrupos/mios/`). Si solo tiene
 * una, entra directo a su detalle (landing operativo). Si tiene varias
 * (admin/superuser), muestra: las áreas con actividad arriba como tarjetas
 * hero, y todas agrupadas por dependencia en un acordeón (las 100% sin
 * eventos colapsadas por defecto).
 */
@Component({
  standalone: true,
  selector: 'app-subgrupo-panel',
  imports: [CommonModule, FormsModule, LucideAngularModule],
  template: `
    <div class="page">
      <header class="page__header">
        <div class="page__title">
          <h1>Áreas</h1>
          <p class="page__sub">Gestiona y accede a las áreas y dependencias a tu cargo</p>
        </div>
        <div class="page__actions">
          <label class="search">
            <lucide-icon name="search" [size]="15"></lucide-icon>
            <input #buscador type="text" [ngModel]="q()" (ngModelChange)="q.set($event)"
                   placeholder="Buscar área, dependencia o evento…"
                   aria-label="Buscar área, dependencia o evento">
            <kbd class="kbd">⌘K</kbd>
          </label>
          <div class="filtros">
            <button type="button" class="filtros-btn" [class.filtros-btn--activo]="filtroActividad() !== 'todas'"
                    (click)="toggleFiltros()" [attr.aria-expanded]="filtrosAbiertos()">
              <lucide-icon name="filter" [size]="15"></lucide-icon>
              <span>Filtros</span>
            </button>
            @if (filtrosAbiertos()) {
              <div class="filtros-panel" role="menu">
                <button type="button" [class.activo]="filtroActividad() === 'todas'" (click)="setFiltro('todas')">Todas</button>
                <button type="button" [class.activo]="filtroActividad() === 'con'" (click)="setFiltro('con')">Con actividad</button>
                <button type="button" [class.activo]="filtroActividad() === 'sin'" (click)="setFiltro('sin')">Sin actividad</button>
              </div>
            }
          </div>
        </div>
      </header>

      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando…</div> }
      @if (error()) { <div class="ui-info-bar ui-info-bar--danger">{{ error() }}</div> }

      @if (!loading() && total() === 0 && !error()) {
        <div class="ui-empty-state">
          <i class="fa fa-sitemap"></i>
          <p>No tienes ningún área asignada. Pide a un administrador que te
            vincule a un área para ver tu panel operativo.</p>
        </div>
      }

      @if (!loading() && total() > 0) {
        <div class="summary-row">
          <span class="summary-label">Resumen de actividad</span>
          <span class="summary-pill">{{ destacadas().length }} área{{ destacadas().length === 1 ? '' : 's' }} con actividad</span>
        </div>

        <!-- ── Con actividad (eventos > 0) ── -->
        @if (destacadas().length > 0) {
          <section class="featured">
            @for (a of destacadas(); track a.id) {
              <button class="card" (click)="abrir(a)"
                      [attr.aria-label]="'Abrir ' + (a.nombre || 'área')">
                <span class="card__dep">
                  <span class="icon-badge" [style.background]="colorDe(a.dependencia)">
                    <lucide-icon [name]="iconoDe(a.dependencia)" [size]="15" color="#fff"></lucide-icon>
                  </span>
                  <span class="card__dep-name">{{ depLegible(a.dependencia) }}</span>
                </span>
                <span class="card__metric" [style.color]="colorDe(a.dependencia)">
                  <span class="card__num-group">
                    <span class="card__num">{{ a.n_eventos }}</span>
                    <span class="card__num-lbl">evento{{ a.n_eventos === 1 ? '' : 's' }}</span>
                  </span>
                  <svg class="spark" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
                    <polyline [attr.points]="sparklinePuntos(a)"></polyline>
                  </svg>
                </span>
                <span class="card__name">{{ a.nombre || 'Área ' + a.id }}</span>
              </button>
            }
          </section>
        }

        <!-- ── Todas las áreas por dependencia ── -->
        <div class="sec-row">
          <div class="sec-label">Todas las áreas por dependencia
            <span class="muted">{{ total() }} área{{ total() === 1 ? '' : 's' }} · {{ destacadas().length }} con eventos</span>
          </div>
          <div class="view-toggle" role="group" aria-label="Tipo de vista">
            <button type="button" [class.activo]="vista() === 'tarjetas'" (click)="vista.set('tarjetas')"
                    aria-label="Vista por tarjetas">
              <lucide-icon name="layout-grid" [size]="14"></lucide-icon>
              <span>Vista por tarjetas</span>
            </button>
            <button type="button" [class.activo]="vista() === 'compacta'" (click)="vista.set('compacta')"
                    aria-label="Vista compacta">
              <lucide-icon name="list" [size]="14"></lucide-icon>
              <span>Vista compacta</span>
            </button>
          </div>
        </div>

        @for (g of gruposVisibles(); track g.nombre) {
          <div class="group">
            <button type="button" class="accordion-head" (click)="toggle(g.nombre)"
                    [attr.aria-expanded]="!colapsada(g.nombre)">
              <span class="dot dot--lg" [style.background]="g.color"></span>
              <span class="group-title">{{ g.nombre }}</span>
              <span class="muted">{{ g.total }} área{{ g.total === 1 ? '' : 's' }} · {{ g.conEventos }} con eventos</span>
              <span class="accordion-pill" [class.accordion-pill--vacio]="g.conEventos === 0">{{ g.conEventos }} con eventos</span>
              <lucide-icon name="chevron-down" [size]="16" class="chev" [class.chev--open]="!colapsada(g.nombre)"></lucide-icon>
            </button>

            @if (!colapsada(g.nombre)) {
              <div class="group-body">
                @if (vista() === 'tarjetas') {
                  @if (activasDe(g).length > 0) {
                    <div class="subgroup-title">Con eventos</div>
                    <div class="chips chips--activas">
                      @for (a of activasDe(g); track a.id) {
                        <button class="mini-card" (click)="abrir(a)"
                                [attr.aria-label]="'Abrir ' + (a.nombre || 'área')" [style.color]="g.color">
                          <span class="icon-badge icon-badge--sm" [style.background]="g.color">
                            <lucide-icon [name]="g.icono" [size]="13" color="#fff"></lucide-icon>
                          </span>
                          <span class="mini-card__body">
                            <span class="mini-card__name">{{ a.nombre || 'Área ' + a.id }}</span>
                            <span class="mini-card__num">{{ a.n_eventos }} evento{{ a.n_eventos === 1 ? '' : 's' }}</span>
                          </span>
                          <svg class="spark spark--sm" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
                            <polyline [attr.points]="sparklinePuntos(a)"></polyline>
                          </svg>
                        </button>
                      }
                    </div>
                  }
                  @if (inactivasDe(g).length > 0) {
                    <div class="subgroup-title subgroup-title--muted">Sin eventos</div>
                    <div class="chips chips--inactivas">
                      @for (a of inactivasDe(g); track a.id) {
                        <button class="chip chip--zero" (click)="abrir(a)"
                                [attr.aria-label]="'Abrir ' + (a.nombre || 'área')">
                          <lucide-icon [name]="g.icono" [size]="12"></lucide-icon>
                          <span class="chip-name">{{ a.nombre || 'Área ' + a.id }}</span>
                          <span class="chip-num">0 eventos</span>
                        </button>
                      }
                    </div>
                  }
                } @else {
                  <div class="compact-list">
                    @for (a of g.areas; track a.id) {
                      <button class="compact-row" [class.compact-row--zero]="a.n_eventos === 0" (click)="abrir(a)"
                              [attr.aria-label]="'Abrir ' + (a.nombre || 'área')">
                        <lucide-icon [name]="g.icono" [size]="13"></lucide-icon>
                        <span class="compact-row__name">{{ a.nombre || 'Área ' + a.id }}</span>
                        <span class="compact-row__num">{{ a.n_eventos }} evento{{ a.n_eventos === 1 ? '' : 's' }}</span>
                      </button>
                    }
                  </div>
                }
              </div>
            }
          </div>
        }

        @if (gruposVisibles().length === 0) {
          <p class="vacio">Ningún área coincide con “{{ q() }}”.</p>
        }
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1000px; margin: 0 auto; padding-bottom: $space-6; }

    /* ── Encabezado ── */
    .page__header { display: flex; align-items: flex-start; justify-content: space-between; gap: $space-4; flex-wrap: wrap; margin-bottom: $space-4; }
    .page__title h1 { margin: 0; font-weight: 500; color: $color-text; }
    .page__sub { color: $color-text-muted; margin: 3px 0 0; font-size: $font-size-sm; }
    .page__actions { display: flex; align-items: center; gap: $space-2; flex-wrap: wrap; }

    .search { position: relative; display: inline-flex; align-items: center; gap: $space-2; background: #fff; border: 1px solid $color-border; border-radius: $radius-md; padding: 0 $space-3; height: 38px; }
    .search :is(lucide-icon) { color: $color-text-muted; flex: none; }
    .search:focus-within { border-color: $color-border-strong; }
    .search input { border: 0; outline: 0; height: 100%; background: transparent; font-size: $font-size-sm; width: 240px; color: $color-text; padding-right: $space-6; }
    .kbd {
      position: absolute; right: $space-2; top: 50%; transform: translateY(-50%);
      font-family: $font-family-mono; font-size: 10.5px; color: $color-text-muted;
      background: $color-bg-subtle; border: 1px solid $color-border; border-radius: $radius-sm;
      padding: 2px 6px; line-height: 1; pointer-events: none;
    }

    .filtros { position: relative; }
    .filtros-btn { display: inline-flex; align-items: center; gap: 6px; height: 38px; padding: 0 $space-3; background: #fff; border: 1px solid $color-border; border-radius: $radius-md; color: $color-text; font-size: $font-size-sm; cursor: pointer; transition: border-color .12s; }
    .filtros-btn:hover { border-color: $color-border-strong; }
    .filtros-btn--activo { border-color: $color-primary; color: $color-primary; }
    .filtros-btn:focus-visible { outline: $focus-ring; outline-offset: $focus-ring-offset; }
    .filtros-panel {
      position: absolute; top: calc(100% + 6px); right: 0; z-index: $z-dropdown; min-width: 168px;
      background: #fff; border: 1px solid $color-border; border-radius: $radius-md; box-shadow: $shadow-md;
      padding: $space-1; display: flex; flex-direction: column; gap: 2px;
    }
    .filtros-panel button { text-align: left; border: 0; background: transparent; padding: $space-2 $space-2; border-radius: $radius-sm; font-size: $font-size-sm; color: $color-text; cursor: pointer; }
    .filtros-panel button:hover { background: $color-bg-subtle; }
    .filtros-panel button.activo { color: $color-primary; font-weight: 500; background: $color-primary-bg; }

    /* ── Resumen de actividad ── */
    .summary-row { display: flex; align-items: center; gap: $space-3; margin-bottom: $space-4; }
    .summary-label { font-size: $font-size-sm; font-weight: 500; color: $color-text; }
    .summary-pill { font-size: $font-size-xs; font-weight: 500; color: $color-primary; background: $color-primary-bg; border-radius: $radius-pill; padding: 3px $space-3; }

    .sec-row { display: flex; align-items: center; justify-content: space-between; gap: $space-3; flex-wrap: wrap; margin: $space-5 0 $space-3; }
    .sec-label { font-size: $font-size-sm; font-weight: 500; color: $color-text-muted; }
    .sec-label .muted { font-weight: 400; margin-left: 6px; }
    .muted { font-size: $font-size-xs; color: $color-neutral-400; font-weight: 400; }
    .dot { width: 8px; height: 8px; border-radius: 50%; flex: none; display: inline-block; }
    .dot--lg { width: 10px; height: 10px; }

    .view-toggle { display: inline-flex; border: 1px solid $color-border; border-radius: $radius-md; overflow: hidden; }
    .view-toggle button { display: inline-flex; align-items: center; gap: 6px; padding: $space-2 $space-3; background: #fff; border: 0; color: $color-text-muted; font-size: $font-size-xs; cursor: pointer; }
    .view-toggle button + button { border-left: 1px solid $color-border; }
    .view-toggle button.activo { background: $color-bg-subtle; color: $color-text; font-weight: 500; }
    .view-toggle button:focus-visible { outline: $focus-ring; outline-offset: -2px; }
    .view-toggle button span { white-space: nowrap; }
    @media (max-width: $bp-sm) { .view-toggle button span { display: none; } }

    /* ── Insignia de ícono ── */
    .icon-badge { display: inline-flex; align-items: center; justify-content: center; width: 26px; height: 26px; border-radius: $radius-md; flex: none; }
    .icon-badge--sm { width: 22px; height: 22px; border-radius: $radius-sm; }

    /* ── Sparkline ── */
    .spark { width: 60px; height: 26px; flex: none; }
    .spark polyline { fill: none; stroke: currentColor; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; opacity: .8; }
    .spark--sm { width: 44px; height: 20px; }

    /* ── Con actividad (tarjetas hero) ── */
    .featured { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: $space-3; margin-bottom: $space-2; }
    .card { display: flex; flex-direction: column; align-items: flex-start; text-align: left; gap: 0; background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-3; cursor: pointer; transition: transform .12s, border-color .12s, box-shadow .12s; }
    .card:hover { transform: translateY(-2px); border-color: $color-border-strong; box-shadow: 0 6px 18px rgba(0,0,0,.06); }
    .card:focus-visible { outline: $focus-ring; outline-offset: $focus-ring-offset; }
    .card__dep { display: flex; align-items: center; gap: $space-2; margin-bottom: $space-3; }
    .card__dep-name { font-size: 10.5px; font-weight: 500; letter-spacing: .05em; text-transform: uppercase; color: $color-text-muted; }
    .card__metric { display: flex; align-items: center; justify-content: space-between; width: 100%; gap: $space-2; }
    .card__num-group { display: flex; align-items: baseline; gap: 6px; }
    .card__num { font-size: 1.9rem; font-weight: 600; line-height: 1; color: $color-text; }
    .card__num-lbl { font-size: $font-size-xs; color: $color-neutral-400; }
    .card__name { font-size: $font-size-base; font-weight: 600; margin-top: $space-3; line-height: 1.3; color: $color-text; }

    /* ── Acordeón por dependencia ── */
    .group { margin-bottom: $space-3; border: 1px solid $color-border; border-radius: $radius-lg; overflow: hidden; }
    .accordion-head { display: flex; align-items: center; gap: $space-2; width: 100%; padding: $space-3; border: 0; background: #fff; cursor: pointer; text-align: left; transition: background .12s; }
    .accordion-head:hover { background: $color-bg-subtle; }
    .accordion-head:focus-visible { outline: $focus-ring; outline-offset: -2px; }
    .group-title { font-size: $font-size-sm; font-weight: 500; color: $color-text; }
    .accordion-pill { margin-left: auto; font-size: $font-size-xs; font-weight: 500; color: $color-success-hondo; background: $color-success-bg; border-radius: $radius-pill; padding: 2px $space-3; white-space: nowrap; }
    .accordion-pill--vacio { color: $color-neutral-500; background: $color-neutral-100; }
    .chev { color: $color-neutral-400; transition: transform .2s; flex: none; }
    .chev--open { transform: rotate(180deg); }

    .group-body { padding: 0 $space-3 $space-3; background: $color-bg-subtle; }
    .subgroup-title { font-size: $font-size-xs; font-weight: 500; color: $color-text-muted; padding: $space-3 0 $space-2; }
    .subgroup-title--muted { color: $color-neutral-400; }

    .chips { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: $space-2; }

    .mini-card { display: flex; align-items: center; gap: $space-2; text-align: left; padding: $space-2 $space-3; border: 1px solid $color-border; border-radius: $radius-md; background: #fff; cursor: pointer; transition: border-color .12s, transform .12s; }
    .mini-card:hover { border-color: $color-border-strong; transform: translateY(-1px); }
    .mini-card:focus-visible { outline: $focus-ring; outline-offset: 1px; }
    .mini-card__body { display: flex; flex-direction: column; gap: 1px; min-width: 0; flex: 1; }
    .mini-card__name { font-size: $font-size-sm; font-weight: 500; color: $color-text; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .mini-card__num { font-size: 11px; color: $color-text-muted; }

    .chip { display: flex; align-items: center; gap: $space-2; padding: $space-2 $space-3; border: 1px solid $color-border; border-radius: $radius-md; background: $color-bg-subtle; cursor: pointer; transition: border-color .12s, transform .12s; text-align: left; }
    .chip:hover { border-color: $color-border-strong; transform: translateY(-1px); }
    .chip:focus-visible { outline: $focus-ring; outline-offset: 1px; }
    .chip lucide-icon { color: $color-neutral-400; flex: none; }
    .chip-name { font-size: $font-size-sm; color: $color-neutral-500; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .chip-num { font-size: $font-size-xs; color: $color-neutral-400; white-space: nowrap; }

    /* ── Vista compacta ── */
    .compact-list { display: flex; flex-direction: column; gap: 1px; background: $color-border; border-radius: $radius-md; overflow: hidden; margin-top: $space-2; }
    .compact-row { display: flex; align-items: center; gap: $space-2; padding: $space-2 $space-3; background: #fff; border: 0; cursor: pointer; text-align: left; color: $color-text; }
    .compact-row:hover { background: $color-bg-subtle; }
    .compact-row:focus-visible { outline: $focus-ring; outline-offset: -2px; }
    .compact-row lucide-icon { color: $color-neutral-400; flex: none; }
    .compact-row__name { font-size: $font-size-sm; flex: 1; }
    .compact-row__num { font-size: $font-size-xs; color: $color-text-muted; }
    .compact-row--zero .compact-row__name, .compact-row--zero .compact-row__num { color: $color-neutral-400; }

    .vacio { color: $color-text-muted; font-size: $font-size-sm; }
  `],
})
export class SubgrupoPanelComponent implements OnInit {
  private api = inject(SubgrupoApi);
  private layout = inject(LayoutService);
  private router = inject(Router);

  @ViewChild('buscador') private buscadorRef?: ElementRef<HTMLInputElement>;

  loading = signal(false);
  error = signal('');
  areas = signal<SubgrupoLite[]>([]);
  q = signal('');
  vista = signal<Vista>('tarjetas');
  filtroActividad = signal<FiltroActividad>('todas');
  filtrosAbiertos = signal(false);
  private colapsadas = signal<Set<string>>(new Set());

  total = computed(() => this.areas().length);

  /** Áreas filtradas por buscador + filtro de actividad. */
  private filtradas = computed(() => {
    const term = normaliza(this.q());
    const filtro = this.filtroActividad();
    return this.areas().filter((a) => {
      if (filtro === 'con' && a.n_eventos === 0) return false;
      if (filtro === 'sin' && a.n_eventos > 0) return false;
      if (!term) return true;
      return normaliza(a.nombre || '').includes(term) ||
        normaliza(a.dependencia || '').includes(term);
    });
  });

  /** Con actividad (eventos > 0), más eventos primero. */
  destacadas = computed(() =>
    this.filtradas().filter((a) => a.n_eventos > 0)
      .sort((x, y) => y.n_eventos - x.n_eventos));

  /** Agrupadas por dependencia: las que tienen actividad primero. */
  gruposVisibles = computed<DepGrupo[]>(() => {
    const porDep = new Map<string, SubgrupoLite[]>();
    for (const a of this.filtradas()) {
      const k = a.dependencia || 'Sin dependencia';
      let arr = porDep.get(k);
      if (!arr) { arr = []; porDep.set(k, arr); }
      arr.push(a);
    }
    const grupos: DepGrupo[] = [];
    for (const [dep, lista] of porDep) {
      const areas = [...lista].sort((x, y) => y.n_eventos - x.n_eventos);
      const conEventos = areas.filter((a) => a.n_eventos > 0).length;
      grupos.push({
        nombre: sentenceCase(dep),
        color: this.colorDe(dep),
        icono: this.iconoDe(dep),
        areas,
        total: areas.length,
        conEventos,
        todasCero: conEventos === 0,
      });
    }
    // Dependencias con actividad primero (por nº de eventos), luego las vacías.
    return grupos.sort((a, b) => {
      if (a.todasCero !== b.todasCero) return a.todasCero ? 1 : -1;
      const ea = a.areas.reduce((s, x) => s + x.n_eventos, 0);
      const eb = b.areas.reduce((s, x) => s + x.n_eventos, 0);
      return eb - ea || a.nombre.localeCompare(b.nombre);
    });
  });

  ngOnInit(): void {
    this.layout.setBreadcrumb([{ label: 'Inicio', url: '/' }, { label: 'Áreas' }]);
    this.cargar();
  }

  /** Atajo ⌘K / Ctrl+K: foco directo al buscador, como cualquier command palette. */
  @HostListener('window:keydown', ['$event'])
  onKeydown(ev: KeyboardEvent): void {
    if (!(ev.metaKey || ev.ctrlKey) || ev.key.toLowerCase() !== 'k') return;
    ev.preventDefault();
    this.buscadorRef?.nativeElement.focus();
  }

  abrir(a: SubgrupoLite): void {
    // Va al panel de ÁREA, no al de subgrupo. El viejo se ancla en
    // `evento.subgrupo_id` y deja en blanco a las áreas que planean y
    // contratan sin haber capturado eventos todavía (Educación,
    // Infraestructura); el nuevo se ancla en el plan y siempre tiene qué
    // mostrar. `/subgrupo/:id` sigue existiendo mientras se migran sus
    // funciones propias (crear actividad, mini-mapa).
    // Por slug, no por id: la URL queda legible y alineada con la miga.
    this.router.navigate(['/mi-area', a.slug || a.id]);
  }

  colorDe(dep: string | null): string {
    const k = normaliza(dep || '');
    if (DEP_COLORS[k]) return DEP_COLORS[k];
    // fallback estable por nombre (hash simple → índice de paleta).
    let h = 0;
    for (let i = 0; i < k.length; i++) h = (h * 31 + k.charCodeAt(i)) >>> 0;
    return DEP_FALLBACK[h % DEP_FALLBACK.length];
  }

  iconoDe(dep: string | null): string {
    const k = normaliza(dep || '');
    return DEP_ICONS[k] || DEP_ICON_FALLBACK;
  }

  depLegible(dep: string | null): string {
    return dep ? sentenceCase(dep) : 'Sin dependencia';
  }

  activasDe(g: DepGrupo): SubgrupoLite[] { return g.areas.filter((a) => a.n_eventos > 0); }
  inactivasDe(g: DepGrupo): SubgrupoLite[] { return g.areas.filter((a) => a.n_eventos === 0); }

  colapsada(nombre: string): boolean { return this.colapsadas().has(nombre); }
  toggle(nombre: string): void {
    const s = new Set(this.colapsadas());
    s.has(nombre) ? s.delete(nombre) : s.add(nombre);
    this.colapsadas.set(s);
  }

  setFiltro(f: FiltroActividad): void {
    this.filtroActividad.set(f);
    this.filtrosAbiertos.set(false);
  }
  toggleFiltros(): void { this.filtrosAbiertos.set(!this.filtrosAbiertos()); }

  /**
   * Curva decorativa determinística — NO es una serie histórica real: el
   * endpoint `/subgrupos/mios/` solo trae el conteo actual de eventos, sin
   * fecha. Da lectura visual de "hay movimiento" sin fingir una tendencia
   * medida. Reemplazar por datos reales si algún día existe un endpoint con
   * historial semanal/mensual por área.
   */
  sparklinePuntos(a: SubgrupoLite): string {
    let s = ((a.id * 31 + a.n_eventos * 7) >>> 0) || 1;
    const siguiente = () => {
      s = (s * 1103515245 + 12345) >>> 0;
      return (s % 1000) / 1000;
    };
    const pasos = 8;
    const puntos: string[] = [];
    for (let i = 0; i < pasos; i++) {
      const x = (i / (pasos - 1)) * 100;
      const tendencia = 30 + (i / (pasos - 1)) * 40;
      const ruido = (siguiente() - 0.5) * 30;
      const y = Math.min(92, Math.max(8, 100 - (tendencia + ruido)));
      puntos.push(`${x.toFixed(1)},${y.toFixed(1)}`);
    }
    return puntos.join(' ');
  }

  private cargar(): void {
    this.loading.set(true);
    this.error.set('');
    this.api.mios().subscribe({
      next: (r) => {
        const lista = r.results ?? [];
        this.areas.set(lista);
        this.loading.set(false);
        // Un solo área → entra directo (landing operativo).
        if (lista.length === 1) {
          this.router.navigate(['/mi-area', lista[0].slug || lista[0].id], { replaceUrl: true });
          return;
        }
        // Dependencias 100% sin eventos arrancan colapsadas.
        const cero = new Set<string>();
        for (const g of this.gruposVisibles()) if (g.todasCero) cero.add(g.nombre);
        this.colapsadas.set(cero);
      },
      error: (e) => { this.loading.set(false); this.error.set(this.msg(e)); },
    });
  }

  private msg(e: { error?: { detail?: string }; status?: number; message?: string }): string {
    if (e?.error?.detail) return e.error.detail;
    if (e?.status === 401 || e?.status === 403) return 'No tienes permiso para ver áreas.';
    return e?.message || 'Error inesperado al cargar tus áreas.';
  }
}
