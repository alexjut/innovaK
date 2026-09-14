import { CommonModule } from '@angular/common';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

interface ItemActividad {
  name: string;
  catalog_id: number | null;
  count: number;
  ids: number[];
}
interface GrupoSubgrupo {
  subgrupo_id: number;
  subgrupo: string;
  dependencia: string | null;
  actividades: ItemActividad[];
}
interface Catalogos {
  dependencias: { id: number; nombre: string }[];
  subgrupos: { id: number; nombre: string; dependencia_id: number | null }[];
  programas: { id: number; nombre: string }[];
  vigencias: { id: number; anio: number }[];
  conceptos: { id: number; codigo: string; nombre: string }[];
  proyectos: { id: number; codigo: string; nombre: string }[];
}
interface KpiOpcion {
  id: number;
  nombre: string;
  unidad_medida: string | null;
}
interface RespuestaAgregada {
  grupos: GrupoSubgrupo[];
  catalogos: Catalogos;
}

@Component({
  standalone: true,
  selector: 'app-actividades-subgrupo',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <h1><i class="fa fa-list-check" aria-hidden="true"></i> Actividades SIPSE</h1>
        <p class="page__subtitle">
          Actividades de plan agrupadas por subgrupo; consolida catálogo y texto libre.
        </p>
      </header>

      <!-- Tiles resumen -->
      <div class="tiles">
        <div class="ui-card tile">
          <span class="tile__num">{{ grupos().length }}</span>
          <span class="tile__label">Subgrupos</span>
        </div>
        <div class="ui-card tile">
          <span class="tile__num">{{ totalActividades() }}</span>
          <span class="tile__label">Actividades únicas</span>
        </div>
        <div class="ui-card tile">
          <span class="tile__num">{{ totalUsos() }}</span>
          <span class="tile__label">Usos en planes</span>
        </div>
        <div class="ui-card tile" [class.tile--warn]="pctCatalogo() < 100">
          <span class="tile__num">{{ pctCatalogo() }}%</span>
          <span class="tile__label">En catálogo</span>
        </div>
      </div>

      <!-- Filtros -->
      <div class="ui-card filtros">
        <div class="filtros__grid">
          <label>Dependencia
            <select [(ngModel)]="fDependencia" (ngModelChange)="onDependencia()">
              <option value="">Todas</option>
              @for (d of cat()?.dependencias ?? []; track d.id) {
                <option [value]="d.id">{{ d.nombre }}</option>
              }
            </select>
          </label>
          <label>Subgrupo
            <select [(ngModel)]="fSubgrupo" (ngModelChange)="recargar()">
              <option value="">Todos</option>
              @for (s of subgruposFiltrados(); track s.id) {
                <option [value]="s.id">{{ s.nombre }}</option>
              }
            </select>
          </label>
          <label>Programa
            <select [(ngModel)]="fPrograma" (ngModelChange)="recargar()">
              <option value="">Todos</option>
              @for (p of cat()?.programas ?? []; track p.id) {
                <option [value]="p.id">{{ p.nombre }}</option>
              }
            </select>
          </label>
          <label>Vigencia
            <select [(ngModel)]="fVigencia" (ngModelChange)="recargar()">
              <option value="">Todas</option>
              @for (v of cat()?.vigencias ?? []; track v.id) {
                <option [value]="v.id">{{ v.anio }}</option>
              }
            </select>
          </label>
          <label>Concepto de gasto
            <select [(ngModel)]="fConcepto" (ngModelChange)="recargar()">
              <option value="">Todos</option>
              @for (c of cat()?.conceptos ?? []; track c.id) {
                <option [value]="c.id">{{ c.codigo }} — {{ c.nombre }}</option>
              }
            </select>
          </label>
          <label>Proyecto
            <select [(ngModel)]="fProyecto" (ngModelChange)="recargar()">
              <option value="">Todos</option>
              @for (p of cat()?.proyectos ?? []; track p.id) {
                <option [value]="p.id">{{ p.codigo }} — {{ p.nombre }}</option>
              }
            </select>
          </label>
        </div>
        <label class="filtros__check">
          <input type="checkbox" [(ngModel)]="fSoloCatalogo" (ngModelChange)="recargar()" />
          Solo actividades de catálogo
        </label>
      </div>

      @if (cargando()) {
        <div class="ui-empty-state"><i class="fa fa-spinner fa-spin" aria-hidden="true"></i> Cargando…</div>
      } @else if (error()) {
        <p class="msg err">{{ error() }}</p>
      } @else if (!grupos().length) {
        <div class="ui-empty-state">
          <i class="fa fa-inbox" aria-hidden="true"></i>
          No hay actividades con los filtros seleccionados.
        </div>
      }

      @for (g of grupos(); track g.subgrupo_id) {
        <section class="ui-card grupo">
          <header class="grupo__header">
            <h2>
              <i class="fa fa-people-group" aria-hidden="true"></i>
              {{ g.subgrupo }}
            </h2>
            <span class="grupo__dep">{{ g.dependencia || '—' }}</span>
          </header>
          <table class="ui-table">
            <thead>
              <tr>
                <th>Actividad</th>
                <th class="num"># usos</th>
                <th class="acciones">Acciones</th>
              </tr>
            </thead>
            <tbody>
              @for (a of g.actividades; track a.name) {
                <tr>
                  <td>
                    @if (a.catalog_id) {
                      <span class="badge badge--cat" title="Actividad de catálogo">catálogo</span>
                    } @else {
                      <span class="badge badge--txt" title="Texto libre, sin catálogo">texto</span>
                    }
                    {{ a.name }}
                  </td>
                  <td class="num">{{ a.count }}</td>
                  <td class="acciones">
                    <button class="ui-btn ui-btn--ghost" (click)="toggleDetalle(a)">
                      <i class="fa" [class]="estaExpandida(a) ? 'fa-chevron-up' : 'fa-chevron-down'" aria-hidden="true"></i>
                      Detalle
                    </button>
                    @if (!a.catalog_id) {
                      <button class="ui-btn ui-btn--ghost migrar"
                              [disabled]="migrando() === claveDe(a)"
                              (click)="migrar(g, a)"
                              title="Crear la actividad en el catálogo y ligar estos planes">
                        <i class="fa" [class]="migrando() === claveDe(a) ? 'fa-spinner fa-spin' : 'fa-arrow-up-from-bracket'" aria-hidden="true"></i>
                        Migrar a catálogo
                      </button>
                    }
                  </td>
                </tr>
                @if (msgDe(a); as m) {
                  <tr><td colspan="3">
                    <p class="msg" [class.err]="m.err">{{ m.texto }}</p>
                  </td></tr>
                }
                @if (estaExpandida(a)) {
                  <tr class="detalle"><td colspan="3">
                    @if (!detalles()[claveDe(a)]) {
                      <i class="fa fa-spinner fa-spin" aria-hidden="true"></i> Cargando planes…
                    } @else {
                      <table class="ui-table tabla-inner">
                        <thead>
                          <tr>
                            <th>Plan</th><th>Proyecto</th>
                            <th class="kpis-col">Metas a las que le suma</th>
                            <th class="num">Eventos</th><th class="num">Contratos</th><th></th>
                          </tr>
                        </thead>
                        <tbody>
                          @for (d of detalles()[claveDe(a)]; track d.id) {
                            <tr>
                              <td>#{{ d.id }}</td>
                              <td>{{ d.proyecto_nombre || '—' }}</td>
                              <!--
                                Acá vivía un número —«2»— y la única forma de
                                cambiarlo era la pantalla /plan/actividad-indicador,
                                que era la tabla puente cruda: «Actividad #»,
                                «KPI #». Ahora el vínculo se ve y se edita donde
                                está la actividad.
                              -->
                              <td class="kpis-col">
                                @if (!d.indicadores?.length) {
                                  <span class="muted">Sin meta vinculada</span>
                                }
                                @for (k of d.indicadores ?? []; track k.id) {
                                  <span class="chip">
                                    {{ k.nombre || ('KPI #' + k.id) }}
                                    <button type="button" class="chip__x"
                                            [disabled]="ocupado() === claveVinc(d.id)"
                                            (click)="desvincular(a, d, k)"
                                            [attr.title]="'Quitar «' + (k.nombre || k.id) + '»'"
                                            aria-label="Quitar meta">×</button>
                                  </span>
                                }

                                @if (vinculando() === d.id) {
                                  <div class="vinc">
                                    @if (!kpisDe(d).length) {
                                      <span class="muted">
                                        {{ cargandoKpis() === d.proyecto_id
                                           ? 'Cargando metas del proyecto…'
                                           : 'El proyecto no tiene metas con KPI.' }}
                                      </span>
                                    } @else {
                                      <select [(ngModel)]="kpiElegido" class="vinc__select">
                                        <option value="">Elija la meta…</option>
                                        @for (o of kpisDe(d); track o.id) {
                                          <option [value]="o.id">
                                            {{ o.nombre }}{{ o.unidad_medida ? ' (' + o.unidad_medida + ')' : '' }}
                                          </option>
                                        }
                                      </select>
                                      <button class="ui-btn ui-btn--primary"
                                              [disabled]="!kpiElegido || ocupado() === claveVinc(d.id)"
                                              (click)="vincular(a, d)">
                                        <i class="fa" [class]="ocupado() === claveVinc(d.id)
                                             ? 'fa-spinner fa-spin' : 'fa-check'" aria-hidden="true"></i>
                                        Vincular
                                      </button>
                                    }
                                    <button class="ui-btn ui-btn--ghost" (click)="cerrarVinculador()">
                                      Cancelar
                                    </button>
                                  </div>
                                } @else {
                                  <button class="ui-btn ui-btn--ghost vinc__abrir"
                                          (click)="abrirVinculador(d)"
                                          title="Vincular esta actividad a una meta del proyecto">
                                    <i class="fa fa-link" aria-hidden="true"></i> Vincular meta
                                  </button>
                                }

                                @if (msgVinc()[claveVinc(d.id)]; as mv) {
                                  <p class="msg" [class.err]="mv.err">{{ mv.texto }}</p>
                                }
                              </td>
                              <td class="num">{{ d.eventos_count ?? 0 }}</td>
                              <td class="num">{{ d.contratos?.length ?? 0 }}</td>
                              <td>
                                @if (d.proyecto_id) {
                                  <a [routerLink]="['/plan/proyectos', d.proyecto_id]"
                                     class="ui-btn ui-btn--ghost">
                                    <i class="fa fa-up-right-from-square" aria-hidden="true"></i> Ver proyecto
                                  </a>
                                }
                              </td>
                            </tr>
                          }
                        </tbody>
                      </table>
                    }
                  </td></tr>
                }
              }
            </tbody>
          </table>
        </section>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1200px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-3; }
    .tiles {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: $space-3; margin-bottom: $space-3;
    }
    .tile {
      display: flex; flex-direction: column; align-items: center;
      padding: $space-3;
      &__num { font-size: 1.6rem; font-weight: 700; color: $color-primary; }
      &__label { color: $color-text-muted; font-size: $font-size-sm; }
      &--warn .tile__num { color: $color-warning; }
    }
    .filtros { padding: $space-3; margin-bottom: $space-3; }
    .filtros__grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: $space-2;
      label { display: flex; flex-direction: column; font-size: $font-size-sm; gap: 4px; }
      select { padding: 6px; border: 1px solid $color-border; border-radius: $radius-sm; }
    }
    .filtros__check {
      display: inline-flex; align-items: center; gap: $space-1;
      margin-top: $space-2; font-size: $font-size-sm;
    }
    .grupo { margin-bottom: $space-3; padding: $space-3; }
    .grupo__header {
      display: flex; align-items: baseline; gap: $space-2; margin-bottom: $space-2;
      h2 { margin: 0; font-size: $font-size-lg; i { color: $color-primary; margin-right: $space-1; } }
    }
    .grupo__dep { color: $color-text-muted; font-size: $font-size-sm; }
    .num { text-align: right; }
    .acciones { white-space: nowrap; text-align: right; }
    .badge {
      display: inline-block; padding: 1px 8px; border-radius: 999px;
      font-size: 0.72rem; font-weight: 600; margin-right: $space-1;
      &--cat { background: rgba(13, 148, 136, .12); color: #0D9488; }
      &--txt { background: rgba(217, 119, 6, .12); color: #d97706; }
    }
    .migrar { margin-left: $space-1; }
    .muted { color: $color-text-muted; font-size: $font-size-sm; }
    .kpis-col { min-width: 320px; }
    .chip {
      display: inline-flex; align-items: center; gap: 6px;
      padding: 2px 6px 2px 10px; margin: 2px 4px 2px 0;
      border-radius: 999px; font-size: 0.78rem;
      background: rgba(13, 148, 136, .12); color: #0D9488;
      &__x {
        border: 0; background: none; cursor: pointer; padding: 0 2px;
        font-size: 1rem; line-height: 1; color: inherit; opacity: .65;
        &:hover:not(:disabled) { opacity: 1; }
        &:disabled { cursor: default; opacity: .3; }
      }
    }
    .vinc {
      display: flex; flex-wrap: wrap; align-items: center;
      gap: $space-1; margin-top: $space-1;
      &__select {
        padding: 6px; border: 1px solid $color-border;
        border-radius: $radius-sm; max-width: 320px;
      }
      &__abrir { margin-top: $space-1; }
    }
    .detalle td { background: $color-bg-subtle; }
    .tabla-inner { margin: $space-1 0; }
    .msg {
      margin: $space-1 0; padding: $space-1 $space-2;
      border-radius: $radius-sm;
      background: rgba(22, 163, 74, 0.10); color: #16a34a;
      &.err { background: rgba(214, 0, 28, 0.08); color: $color-primary; }
    }
  `],
})
export class ActividadesSubgrupoComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);

  grupos = signal<GrupoSubgrupo[]>([]);
  cat = signal<Catalogos | null>(null);
  cargando = signal<boolean>(true);
  error = signal<string>('');

  fDependencia = '';
  fSubgrupo = '';
  fPrograma = '';
  fVigencia = '';
  fConcepto = '';
  fProyecto = '';
  fSoloCatalogo = false;

  expandidas = signal<Set<string>>(new Set());
  detalles = signal<Record<string, any[]>>({});
  migrando = signal<string | null>(null);
  mensajes = signal<Record<string, { texto: string; err: boolean }>>({});

  // ── Vinculación actividad ↔ meta (KPI) ────────────────────────────
  //
  // Se fundió acá el 2026-09-14 desde `/plan/actividad-indicador`, que era la
  // tabla puente expuesta tal cual —«Actividad #», «KPI #»— y obligaba a
  // conocer los ids de memoria. Esta pantalla ya mostraba los KPIs de cada
  // actividad; lo que le faltaba era dejar tocarlos.
  /** id de la ActividadPlan cuyo selector está abierto. */
  vinculando = signal<number | null>(null);
  /** Clave `plan:<id>` en curso: bloquea los botones de ESA fila, no de todas. */
  ocupado = signal<string | null>(null);
  /** proyecto_id cuyas metas se están pidiendo. */
  cargandoKpis = signal<number | null>(null);
  /** Metas por proyecto: se piden una vez y se reutilizan entre filas. */
  kpisPorProyecto = signal<Record<number, KpiOpcion[]>>({});
  msgVinc = signal<Record<string, { texto: string; err: boolean }>>({});
  kpiElegido = '';

  totalActividades = computed(() =>
    this.grupos().reduce((n, g) => n + g.actividades.length, 0));
  totalUsos = computed(() =>
    this.grupos().reduce((n, g) => n + g.actividades.reduce((m, a) => m + a.count, 0), 0));
  pctCatalogo = computed(() => {
    const total = this.totalActividades();
    if (!total) return 100;
    const cat = this.grupos().reduce(
      (n, g) => n + g.actividades.filter(a => !!a.catalog_id).length, 0);
    return Math.round((100 * cat) / total);
  });

  subgruposFiltrados = computed(() => {
    const subs = this.cat()?.subgrupos ?? [];
    if (!this.fDependencia) return subs;
    return subs.filter(s => String(s.dependencia_id) === this.fDependencia);
  });

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Plan de Desarrollo', url: '/plan' },
      { label: 'Actividades SIPSE' },
    ]);
    this.recargar();
  }

  onDependencia(): void {
    this.fSubgrupo = '';
    this.recargar();
  }

  recargar(): void {
    this.cargando.set(true);
    this.error.set('');
    this.expandidas.set(new Set());
    let params = new HttpParams();
    const filtros: Record<string, string> = {
      dependencia: this.fDependencia, subgrupo: this.fSubgrupo,
      programa: this.fPrograma, vigencia: this.fVigencia,
      concepto: this.fConcepto, proyecto: this.fProyecto,
    };
    for (const [k, v] of Object.entries(filtros)) {
      if (v) params = params.set(k, v);
    }
    if (this.fSoloCatalogo) params = params.set('solo_catalogo', '1');
    this.http.get<RespuestaAgregada>(
      this.cfg.url('/presupuesto/api/actividades/por-subgrupo/'), { params },
    ).subscribe({
      next: r => {
        this.grupos.set(r.grupos);
        this.cat.set(r.catalogos);
        this.cargando.set(false);
      },
      error: e => {
        this.cargando.set(false);
        this.error.set(e?.error?.detail || 'No se pudieron cargar las actividades.');
      },
    });
  }

  claveDe(a: ItemActividad): string {
    return a.catalog_id ? `cat:${a.catalog_id}` : `txt:${a.name.toLowerCase()}`;
  }

  estaExpandida(a: ItemActividad): boolean {
    return this.expandidas().has(this.claveDe(a));
  }

  msgDe(a: ItemActividad): { texto: string; err: boolean } | null {
    return this.mensajes()[this.claveDe(a)] ?? null;
  }

  toggleDetalle(a: ItemActividad): void {
    const clave = this.claveDe(a);
    const set = new Set(this.expandidas());
    if (set.has(clave)) {
      set.delete(clave);
      this.expandidas.set(set);
      return;
    }
    set.add(clave);
    this.expandidas.set(set);
    if (this.detalles()[clave]) return;
    const cargados: any[] = [];
    for (const id of a.ids) {
      this.http.get<any>(this.cfg.url(`/presupuesto/api/actividades-plan/${id}/`))
        .subscribe(d => {
          cargados.push(d);
          if (cargados.length === a.ids.length) {
            cargados.sort((x, y) => x.id - y.id);
            this.detalles.set({ ...this.detalles(), [clave]: cargados });
          }
        });
    }
  }

  // ── Vinculación actividad ↔ meta ──────────────────────────────────

  claveVinc(planId: number): string {
    return `plan:${planId}`;
  }

  kpisDe(d: any): KpiOpcion[] {
    return d?.proyecto_id ? (this.kpisPorProyecto()[d.proyecto_id] ?? []) : [];
  }

  abrirVinculador(d: any): void {
    this.kpiElegido = '';
    this.vinculando.set(d.id);
    this.msgVinc.set({ ...this.msgVinc(), [this.claveVinc(d.id)]: undefined as any });
    if (!d.proyecto_id || this.kpisPorProyecto()[d.proyecto_id]) return;
    // Solo las metas DEL PROYECTO de la actividad. La pantalla anterior
    // ofrecía los 77 KPIs de la localidad en un único select, sin filtrar:
    // nada impedía colgarle a una actividad de Cultura una meta de Ambiente.
    this.cargandoKpis.set(d.proyecto_id);
    this.http.get<any>(
      this.cfg.url('/presupuesto/api/indicadores/'),
      { params: new HttpParams()
          .set('proyecto_id', String(d.proyecto_id))
          .set('page_size', '100') },
    ).subscribe({
      next: r => {
        this.cargandoKpis.set(null);
        this.kpisPorProyecto.set({
          ...this.kpisPorProyecto(),
          [d.proyecto_id]: (r?.results ?? r ?? []) as KpiOpcion[],
        });
      },
      error: () => {
        this.cargandoKpis.set(null);
        this.kpisPorProyecto.set({ ...this.kpisPorProyecto(), [d.proyecto_id]: [] });
      },
    });
  }

  cerrarVinculador(): void {
    this.vinculando.set(null);
    this.kpiElegido = '';
  }

  vincular(a: ItemActividad, d: any): void {
    if (!this.kpiElegido) return;
    const clave = this.claveVinc(d.id);
    this.ocupado.set(clave);
    this.http.post<any>(this.cfg.url('/presupuesto/api/actividad-indicador/'), {
      actividad_plan_id: d.id,
      indicador_id: Number(this.kpiElegido),
    }).subscribe({
      next: r => {
        this.ocupado.set(null);
        this.cerrarVinculador();
        this.avisoVinc(clave, r?.detail || 'Vinculación creada.', false);
        this.recargarDetalle(a, d.id);
      },
      error: e => {
        this.ocupado.set(null);
        this.avisoVinc(clave, e?.error?.detail || 'No se pudo vincular.', true);
      },
    });
  }

  desvincular(a: ItemActividad, d: any, k: { id: number; nombre?: string }): void {
    if (!confirm(
      `¿Quitar la meta "${k.nombre || k.id}" de la actividad #${d.id}?\n` +
      'La actividad deja de contarle a esa meta.',
    )) return;
    const clave = this.claveVinc(d.id);
    this.ocupado.set(clave);
    this.http.delete<any>(this.cfg.url('/presupuesto/api/actividad-indicador/'), {
      params: new HttpParams()
        .set('actividad_plan_id', String(d.id))
        .set('indicador_id', String(k.id)),
    }).subscribe({
      next: r => {
        this.ocupado.set(null);
        this.avisoVinc(clave, r?.detail || 'Vinculación retirada.', false);
        this.recargarDetalle(a, d.id);
      },
      error: e => {
        this.ocupado.set(null);
        this.avisoVinc(clave, e?.error?.detail || 'No se pudo quitar.', true);
      },
    });
  }

  private avisoVinc(clave: string, texto: string, err: boolean): void {
    this.msgVinc.set({ ...this.msgVinc(), [clave]: { texto, err } });
  }

  /** Repinta UNA fila del detalle sin cerrar el acordeón ni recargar la página. */
  private recargarDetalle(a: ItemActividad, planId: number): void {
    const clave = this.claveDe(a);
    this.http.get<any>(this.cfg.url(`/presupuesto/api/actividades-plan/${planId}/`))
      .subscribe(nuevo => {
        const filas = this.detalles()[clave];
        if (!filas) return;
        this.detalles.set({
          ...this.detalles(),
          [clave]: filas.map(f => (f.id === planId ? nuevo : f)),
        });
      });
  }

  migrar(g: GrupoSubgrupo, a: ItemActividad): void {
    if (!confirm(
      `¿Crear "${a.name}" en el catálogo y ligar sus ${a.count} plan(es) del subgrupo ${g.subgrupo}?`,
    )) return;
    const clave = this.claveDe(a);
    this.migrando.set(clave);
    this.http.post<any>(this.cfg.url('/presupuesto/api/actividades/migrar/'), {
      name: a.name, subgrupo_id: g.subgrupo_id,
    }).subscribe({
      next: r => {
        this.migrando.set(null);
        this.mensajes.set({ ...this.mensajes(), [clave]: { texto: r.detail, err: false } });
        this.recargar();
      },
      error: e => {
        this.migrando.set(null);
        this.mensajes.set({
          ...this.mensajes(),
          [clave]: { texto: e?.error?.detail || 'No se pudo migrar.', err: true },
        });
      },
    });
  }
}
