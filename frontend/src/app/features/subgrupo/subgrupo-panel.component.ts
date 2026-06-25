import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { SubgrupoApi } from './subgrupo.api';
import { SubgrupoLite } from './subgrupo.types';

/** Grupo de áreas de una misma dependencia (proyección de presentación). */
interface DepGrupo {
  nombre: string;          // nombre legible (sentence case) de la dependencia
  color: string;           // color de acento de la dependencia
  areas: SubgrupoLite[];   // ordenadas: más eventos primero, las 0 al final
  total: number;
  conEventos: number;
  todasCero: boolean;
}

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
 * grandes, y todas agrupadas por dependencia (las dependencias 100% sin
 * eventos colapsadas).
 */
@Component({
  standalone: true,
  selector: 'app-subgrupo-panel',
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page">
      <header class="page__header">
        <div>
          <h1>Áreas</h1>
          <p class="page__sub">Panel operativo · entra al área de la que eres responsable</p>
        </div>
        <div class="page__actions">
          <label class="search">
            <i class="fa fa-search"></i>
            <input type="text" [ngModel]="q()" (ngModelChange)="q.set($event)"
                   placeholder="Buscar área…" aria-label="Buscar área">
          </label>
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
        <!-- ── Con actividad (eventos > 0) ── -->
        @if (destacadas().length > 0) {
          <div class="sec-label">Con actividad
            <span class="muted">{{ destacadas().length }} área{{ destacadas().length === 1 ? '' : 's' }}</span>
          </div>
          <section class="featured">
            @for (a of destacadas(); track a.id) {
              <button class="card" (click)="abrir(a)"
                      [attr.aria-label]="'Abrir ' + (a.nombre || 'área')">
                <span class="card__dep">
                  <span class="dot" [style.background]="colorDe(a.dependencia)"></span>
                  <span class="card__dep-name">{{ depLegible(a.dependencia) }}</span>
                </span>
                <span class="card__num">{{ a.n_eventos }}</span>
                <span class="card__num-lbl">evento{{ a.n_eventos === 1 ? '' : 's' }}</span>
                <span class="card__name">{{ a.nombre || 'Área ' + a.id }}</span>
              </button>
            }
          </section>
        }

        <!-- ── Todas las áreas por dependencia ── -->
        <div class="sec-label">Todas las áreas por dependencia</div>

        @for (g of gruposVisibles(); track g.nombre) {
          @if (!g.todasCero) {
            <!-- dependencia con actividad: siempre expandida -->
            <div class="group">
              <div class="group-head">
                <span class="dot dot--lg" [style.background]="g.color"></span>
                <span class="group-title">{{ g.nombre }}</span>
                <span class="muted">{{ g.total }} áreas · {{ g.conEventos }} con eventos</span>
              </div>
              <div class="chips">
                @for (a of g.areas; track a.id) {
                  <button class="chip" [class.chip--zero]="a.n_eventos === 0" (click)="abrir(a)"
                          [attr.aria-label]="'Abrir ' + (a.nombre || 'área')">
                    <span class="chip-name">{{ a.nombre || 'Área ' + a.id }}</span>
                    <span class="chip-num">{{ a.n_eventos }}</span>
                  </button>
                }
              </div>
            </div>
          } @else {
            <!-- dependencia 100% sin eventos: colapsada por defecto -->
            <button class="empty-head" (click)="toggle(g.nombre)"
                    [attr.aria-expanded]="!colapsada(g.nombre)">
              <span class="dot dot--lg" [style.background]="g.color"></span>
              <span class="empty-name">{{ g.nombre }}</span>
              <span class="muted">{{ g.total }} áreas · sin eventos</span>
              <i class="fa fa-chevron-down chev" [class.chev--open]="!colapsada(g.nombre)"></i>
            </button>
            @if (!colapsada(g.nombre)) {
              <div class="chips chips--empty">
                @for (a of g.areas; track a.id) {
                  <button class="chip chip--zero" (click)="abrir(a)"
                          [attr.aria-label]="'Abrir ' + (a.nombre || 'área')">
                    <span class="chip-name">{{ a.nombre || 'Área ' + a.id }}</span>
                    <span class="chip-num">{{ a.n_eventos }}</span>
                  </button>
                }
              </div>
            }
          }
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
    .page__header { display: flex; align-items: flex-end; justify-content: space-between; gap: $space-3; flex-wrap: wrap; margin-bottom: $space-4; }
    .page__header h1 { margin: 0; font-weight: 500; color: $color-text; }
    .page__sub { color: $color-text-muted; margin: 3px 0 0; font-size: $font-size-sm; }
    .search { display: inline-flex; align-items: center; gap: $space-2; background: #fff; border: 1px solid $color-border; border-radius: $radius-md; padding: 0 $space-3; height: 38px; }
    .search:focus-within { border-color: $color-border-strong; }
    .search i { color: $color-text-muted; font-size: .85rem; }
    .search input { border: 0; outline: 0; height: 100%; background: transparent; font-size: $font-size-sm; width: 180px; color: $color-text; }

    .sec-label { font-size: $font-size-sm; font-weight: 500; color: $color-text-muted; margin: 0 0 $space-3; }
    .sec-label .muted { font-weight: 400; }
    .muted { font-size: $font-size-xs; color: $color-neutral-400; font-weight: 400; }
    .dot { width: 8px; height: 8px; border-radius: 50%; flex: none; display: inline-block; }
    .dot--lg { width: 10px; height: 10px; }

    /* ── Con actividad ── */
    .featured { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: $space-3; margin-bottom: $space-5; }
    .card { display: flex; flex-direction: column; align-items: flex-start; text-align: left; gap: 0; background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-3 $space-3 $space-3; cursor: pointer; transition: transform .12s, border-color .12s, box-shadow .12s; }
    .card:hover { transform: translateY(-2px); border-color: $color-border-strong; box-shadow: 0 6px 18px rgba(0,0,0,.06); }
    .card:focus-visible { outline: 2px solid $color-primary; outline-offset: 2px; }
    .card__dep { display: flex; align-items: center; gap: 6px; margin-bottom: $space-2; }
    .card__dep-name { font-size: $font-size-xs; color: $color-text-muted; }
    .card__num { font-size: 1.9rem; font-weight: 600; line-height: 1; color: $color-text; }
    .card__num-lbl { font-size: $font-size-xs; color: $color-neutral-400; margin-top: 2px; }
    .card__name { font-size: $font-size-base; font-weight: 500; margin-top: $space-2; line-height: 1.3; color: $color-text; }

    /* ── Por dependencia ── */
    .group { margin-bottom: $space-4; }
    .group-head { display: flex; align-items: center; gap: $space-2; padding-bottom: $space-2; border-bottom: 1px solid $color-border; margin-bottom: $space-3; }
    .group-title { font-size: $font-size-sm; font-weight: 500; color: $color-text; }
    .chips { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: $space-2; }
    .chips--empty { padding: $space-1 0 $space-3; }
    .chip { display: flex; align-items: center; justify-content: space-between; gap: $space-2; padding: $space-2 $space-3; border: 1px solid $color-border; border-radius: $radius-md; background: #fff; cursor: pointer; transition: border-color .12s, transform .12s; text-align: left; }
    .chip:hover { border-color: $color-border-strong; transform: translateY(-1px); }
    .chip:focus-visible { outline: 2px solid $color-primary; outline-offset: 1px; }
    .chip--zero { background: $color-bg-subtle; }
    .chip-name { font-size: $font-size-sm; color: $color-text; }
    .chip-num { font-size: $font-size-sm; font-weight: 600; color: $color-text; }
    .chip--zero .chip-name, .chip--zero .chip-num { color: $color-neutral-400; font-weight: 400; }

    /* ── Dependencias vacías (colapsables) ── */
    .empty-head { display: flex; align-items: center; gap: $space-2; width: 100%; padding: $space-2 $space-3; border: 1px solid $color-border; border-radius: $radius-md; background: $color-bg-subtle; margin-bottom: $space-2; cursor: pointer; transition: border-color .12s; }
    .empty-head:hover { border-color: $color-border-strong; }
    .empty-head:focus-visible { outline: 2px solid $color-primary; outline-offset: 1px; }
    .empty-name { font-size: $font-size-sm; color: $color-text-muted; flex: 1; text-align: left; }
    .chev { font-size: .8rem; color: $color-neutral-400; transition: transform .2s; }
    .chev--open { transform: rotate(180deg); }
    .vacio { color: $color-text-muted; font-size: $font-size-sm; }
  `],
})
export class SubgrupoPanelComponent implements OnInit {
  private api = inject(SubgrupoApi);
  private layout = inject(LayoutService);
  private router = inject(Router);

  loading = signal(false);
  error = signal('');
  areas = signal<SubgrupoLite[]>([]);
  q = signal('');
  private colapsadas = signal<Set<string>>(new Set());

  total = computed(() => this.areas().length);

  /** Áreas filtradas por el buscador. */
  private filtradas = computed(() => {
    const term = normaliza(this.q());
    if (!term) return this.areas();
    return this.areas().filter((a) =>
      normaliza(a.nombre || '').includes(term) ||
      normaliza(a.dependencia || '').includes(term));
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

  abrir(a: SubgrupoLite): void {
    this.router.navigate(['/subgrupo', a.id]);
  }

  colorDe(dep: string | null): string {
    const k = normaliza(dep || '');
    if (DEP_COLORS[k]) return DEP_COLORS[k];
    // fallback estable por nombre (hash simple → índice de paleta).
    let h = 0;
    for (let i = 0; i < k.length; i++) h = (h * 31 + k.charCodeAt(i)) >>> 0;
    return DEP_FALLBACK[h % DEP_FALLBACK.length];
  }

  depLegible(dep: string | null): string {
    return dep ? sentenceCase(dep) : 'Sin dependencia';
  }

  colapsada(nombre: string): boolean { return this.colapsadas().has(nombre); }
  toggle(nombre: string): void {
    const s = new Set(this.colapsadas());
    s.has(nombre) ? s.delete(nombre) : s.add(nombre);
    this.colapsadas.set(s);
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
          this.router.navigate(['/subgrupo', lista[0].id], { replaceUrl: true });
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
