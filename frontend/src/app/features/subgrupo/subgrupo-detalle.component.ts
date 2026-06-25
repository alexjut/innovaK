import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { formatMoneda } from '../../shared/format/format.util';
import { SubgrupoApi } from './subgrupo.api';
import {
  ContratoSubgrupo,
  EventoSubgrupo,
  GrupoGeneral,
  SubgrupoPanel,
  SubgrupoRef,
  SubgrupoTiles,
} from './subgrupo.types';

/** Destino del organizador de un evento, según su tipo_evento. */
interface OrganizadorLink {
  route: unknown[];
  query?: Record<string, unknown>;
  label: string;
  icon: string;
}

const TILES_VACIO: SubgrupoTiles = {
  n_proyectos: 0, n_actividades: 0, n_eventos: 0, n_contratos: 0, valor_contratado: 0,
};

/**
 * Detalle operativo de UN subgrupo (RBAC B4).
 *
 *   - Tiles agregados (proyectos / actividades / eventos / contratos / $).
 *   - Tronco "General": eventos agrupados por ActividadPlan → Proyecto.
 *   - Lateral: contratos del subgrupo.
 *
 * Cada evento abre su organizador real (banco/cursos/caracterización/captura/
 * jóvenes/entregas) — el MISMO destino que despacha
 * `actividades-eventos.component`. La navegación es pura proyección: no toca
 * la cadena de conteo del KPI.
 */
@Component({
  standalone: true,
  selector: 'app-subgrupo-detalle',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page">
      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando…</div> }
      @if (error()) { <div class="ui-info-bar ui-info-bar--danger">{{ error() }}</div> }

      @if (!loading() && cargado()) {
        <header class="page__header">
          <div>
            <a routerLink="/subgrupo" class="ui-back-link">
              <i class="fa fa-arrow-left"></i> Mis subgrupos
            </a>
            <h1><i class="fa fa-sitemap" aria-hidden="true"></i>
              {{ subgrupo().nombre || 'Subgrupo ' + subgrupoId }}</h1>
            @if (subgrupo().dependencia) {
              <p class="page__sub">{{ subgrupo().dependencia }}</p>
            }
          </div>
        </header>

        <!-- Tiles -->
        <section class="kpis">
          <div class="kpi"><span class="kpi__val">{{ tiles().n_proyectos }}</span><span class="kpi__lbl">Proyectos</span></div>
          <div class="kpi kpi--act"><span class="kpi__val">{{ tiles().n_actividades }}</span><span class="kpi__lbl">Actividades</span></div>
          <div class="kpi kpi--evt"><span class="kpi__val">{{ tiles().n_eventos }}</span><span class="kpi__lbl">Eventos</span></div>
          <div class="kpi kpi--ctr"><span class="kpi__val">{{ tiles().n_contratos }}</span><span class="kpi__lbl">Contratos</span></div>
          <div class="kpi kpi--money"><span class="kpi__val">{{ moneda(tiles().valor_contratado) }}</span><span class="kpi__lbl">Valor contratado</span></div>
        </section>

        <div class="layout">
          <!-- ── Tronco "General": eventos por actividad_plan ── -->
          <main class="general">
            <h2 class="sec__title"><i class="fa fa-folder-tree"></i> General · actividades del subgrupo</h2>

            @if (general().length === 0) {
              <div class="ui-empty-state">
                <i class="fa fa-folder-open"></i>
                <p>Este subgrupo aún no tiene eventos registrados.</p>
              </div>
            }

            @for (g of general(); track g.actividad_plan_id) {
              <article class="grupo" [class.grupo--suelto]="g.actividad_plan_id === null">
                <header class="grupo__head">
                  <div class="grupo__title">
                    @if (g.actividad_plan_id !== null) {
                      <i class="fa fa-diagram-project"></i>
                      <strong>{{ g.actividad_plan_descripcion || 'Actividad ' + g.actividad_plan_id }}</strong>
                    } @else {
                      <i class="fa fa-inbox"></i>
                      <strong>Eventos sin actividad de plan</strong>
                    }
                  </div>
                  <div class="grupo__meta">
                    @if (g.proyecto_codigo) {
                      <span class="proj" [title]="g.proyecto_nombre || ''">
                        {{ g.proyecto_codigo }}{{ g.proyecto_nombre ? ' · ' + g.proyecto_nombre : '' }}
                      </span>
                    }
                    <span class="chip">{{ g.n_eventos }} evento{{ g.n_eventos === 1 ? '' : 's' }}</span>
                  </div>
                </header>

                <div class="ui-table-responsive">
                  <table class="ui-table">
                    <thead>
                      <tr>
                        <th>#</th><th>Nombre</th><th>Tipo</th>
                        <th>Inicio</th><th>Fin</th><th>Estado</th><th>Acciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (ev of g.eventos; track ev.id) {
                        <tr>
                          <td>{{ ev.id }}</td>
                          <td>{{ ev.nombre || '—' }}</td>
                          <td><span class="ui-badge ui-badge--info">{{ ev.tipo_nombre || ev.tipo_codigo || '—' }}</span></td>
                          <td>{{ ev.fecha_inicio || '—' }}</td>
                          <td>{{ ev.fecha_fin || '—' }}</td>
                          <td>
                            @if (ev.activo) { <span class="ui-badge ui-badge--success">Activo</span> }
                            @else { <span class="ui-badge ui-badge--muted">Inactivo</span> }
                          </td>
                          <td>
                            <div class="acciones">
                              @if (organizador(ev); as org) {
                                <a [routerLink]="org.route" [queryParams]="org.query || {}"
                                   class="ui-btn ui-btn--sm ui-btn--primary">
                                  <i class="fa" [ngClass]="org.icon"></i> {{ org.label }}
                                </a>
                              }
                              <a [routerLink]="['/eventos', ev.id, 'editar']"
                                 class="ui-btn ui-btn--sm ui-btn--ghost">
                                <i class="fa fa-edit"></i> Editar
                              </a>
                            </div>
                          </td>
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              </article>
            }
          </main>

          <!-- ── Lateral: contratos del subgrupo ── -->
          <aside class="contratos">
            <h2 class="sec__title"><i class="fa fa-file-contract"></i> Contratos</h2>
            @if (contratos().length === 0) {
              <p class="vacio">Sin contratos vinculados a los proyectos del subgrupo.</p>
            } @else {
              @for (c of contratos(); track c.id) {
                <article class="ctr">
                  <strong class="ctr__num">{{ c.numero }}</strong>
                  @if (c.objeto) { <p class="ctr__obj" [title]="c.objeto">{{ c.objeto }}</p> }
                  <div class="ctr__foot">
                    <span class="ctr__val">{{ moneda(c.valor) }}</span>
                    <span class="ctr__ejc" [class]="ejecClase(c.ejecucion)">{{ c.ejecucion || 0 }}%</span>
                  </div>
                  <div class="bar"><div class="bar__fill" [class]="ejecClase(c.ejecucion)"
                       [style.width.%]="c.ejecucion || 0"></div></div>
                </article>
              }
            }
          </aside>
        </div>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1300px; margin: 0 auto; padding-bottom: $space-6; }
    .page__header h1 { margin: $space-1 0 0; color: $color-primary; }
    .page__header h1 i { margin-right: $space-2; }
    .page__sub { color: $color-text-muted; margin: $space-1 0 0; }
    .ui-back-link { font-size: $font-size-sm; color: $color-text-muted; text-decoration: none; }
    .ui-back-link:hover { color: $color-primary; }

    .kpis { display: grid; grid-template-columns: repeat(5, 1fr); gap: $space-3; margin: $space-3 0 $space-4; }
    @media (max-width: 900px) { .kpis { grid-template-columns: repeat(3, 1fr); } }
    @media (max-width: 560px) { .kpis { grid-template-columns: 1fr 1fr; } }
    .kpi { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-3; display: flex; flex-direction: column; border-left: 4px solid $color-primary; }
    .kpi--act { border-left-color: #2563eb; }
    .kpi--evt { border-left-color: #8B5CF6; }
    .kpi--ctr { border-left-color: #F59E0B; }
    .kpi--money { border-left-color: #16A34A; }
    .kpi__val { font-size: 1.4rem; font-weight: 700; color: $color-primary; line-height: 1.1; }
    .kpi__lbl { color: $color-text-muted; font-size: $font-size-sm; }

    .layout { display: grid; grid-template-columns: 1fr 320px; gap: $space-4; align-items: start; }
    @media (max-width: 980px) { .layout { grid-template-columns: 1fr; } }
    .sec__title { color: $color-primary; font-size: 1.05rem; margin: 0 0 $space-2; }
    .sec__title i { margin-right: $space-2; }

    .grupo { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-3; margin-bottom: $space-3; }
    .grupo--suelto { border-style: dashed; }
    .grupo__head { display: flex; justify-content: space-between; align-items: flex-start; gap: $space-2; flex-wrap: wrap; margin-bottom: $space-2; }
    .grupo__title { color: $color-text; }
    .grupo__title i { margin-right: 6px; color: $color-text-muted; }
    .grupo__meta { display: flex; align-items: center; gap: $space-2; flex-wrap: wrap; }
    .proj { background: #EEF2FF; color: #4338CA; border-radius: 6px; padding: 2px 8px; font-weight: 600; font-size: .76rem; max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .chip { background: #F3F4F6; color: $color-text-muted; border-radius: 99px; padding: 2px 10px; font-size: .74rem; }
    .acciones { display: flex; gap: $space-1; flex-wrap: wrap; }

    .contratos { background: transparent; }
    .ctr { background: #fff; border: 1px solid $color-border; border-radius: $radius-md; padding: $space-2 $space-3; margin-bottom: $space-2; border-left: 4px solid #F59E0B; }
    .ctr__num { color: $color-primary; font-size: $font-size-sm; }
    .ctr__obj { color: $color-text-muted; font-size: .76rem; margin: 2px 0 $space-1; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
    .ctr__foot { display: flex; justify-content: space-between; align-items: baseline; }
    .ctr__val { font-weight: 600; font-size: $font-size-sm; }
    .ctr__ejc { font-size: .76rem; font-weight: 600; }
    .ctr__ejc.ok { color: #16A34A; } .ctr__ejc.warn { color: #F59E0B; } .ctr__ejc.low { color: #DC2626; }
    .bar { height: 6px; background: #eee; border-radius: 99px; margin-top: 6px; overflow: hidden; }
    .bar__fill { height: 100%; transition: width .4s; }
    .bar__fill.ok { background: #16A34A; } .bar__fill.warn { background: #F59E0B; } .bar__fill.low { background: #DC2626; }
    .vacio { color: $color-text-muted; font-size: $font-size-sm; }
  `],
})
export class SubgrupoDetalleComponent implements OnInit {
  private api = inject(SubgrupoApi);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private layout = inject(LayoutService);

  subgrupoId = 0;
  loading = signal(false);
  error = signal('');
  cargado = signal(false);
  subgrupo = signal<SubgrupoRef>({ id: 0, nombre: null, dependencia: null });
  tiles = signal<SubgrupoTiles>(TILES_VACIO);
  general = signal<GrupoGeneral[]>([]);
  contratos = signal<ContratoSubgrupo[]>([]);

  ngOnInit(): void {
    this.route.paramMap.subscribe((p) => {
      this.subgrupoId = Number(p.get('id') || '0');
      this.cargar();
    });
  }

  moneda(v: unknown): string { return formatMoneda(v); }

  ejecClase(ejec: number | null): string {
    const e = ejec || 0;
    return e >= 80 ? 'ok' : e >= 50 ? 'warn' : 'low';
  }

  /**
   * Destino del organizador de un evento según su tipo_evento. Mismo árbol de
   * despacho que `actividades-eventos.component` (banco/cursos/caracterización/
   * captura/jóvenes/entregas). Si el tipo no es conocido, solo queda "Editar".
   */
  organizador(ev: EventoSubgrupo): OrganizadorLink | null {
    const c = ev.tipo_codigo || '';
    if (c === 'CURSO' || c === 'CAPACITACION') {
      return { route: ['/cursos', ev.id], label: 'Panel del curso', icon: 'fa-chalkboard-teacher' };
    }
    if (c === 'ENTREGA') {
      return { route: ['/entregas'], query: { evento: ev.id }, label: 'Beneficiarios', icon: 'fa-users' };
    }
    if (c === 'CULTURA_ORG' || c === 'ESTIMULO_CULTURAL' || c === 'PROYECTO_CULTURAL') {
      return { route: ['/captura'], query: { evento: ev.id, tipo: c }, label: 'Registros', icon: 'fa-users' };
    }
    if (c === 'JOVENES_BECA') {
      return { route: ['/jovenes'], query: { evento_id: ev.id }, label: 'Entregas', icon: 'fa-users' };
    }
    if (c === 'CARACTERIZACION') {
      return { route: ['/caracterizacion/evento', ev.id], label: 'Caracterizaciones', icon: 'fa-clipboard-list' };
    }
    if (c === 'BANCO_INICIATIVAS') {
      return { route: ['/banco'], query: { evento: ev.id }, label: 'Beneficiarios', icon: 'fa-users' };
    }
    return null;
  }

  private cargar(): void {
    if (!this.subgrupoId) return;
    this.loading.set(true);
    this.error.set('');
    this.cargado.set(false);
    this.api.panel(this.subgrupoId).subscribe({
      next: (p) => {
        this.subgrupo.set(p.subgrupo);
        this.tiles.set(p.tiles);
        this.general.set(p.general);
        this.contratos.set(p.contratos);
        this.cargado.set(true);
        this.loading.set(false);
        this.layout.setBreadcrumb([
          { label: 'Inicio', url: '/' },
          { label: 'Mi subgrupo', url: '/subgrupo' },
          { label: p.subgrupo.nombre || `Subgrupo ${this.subgrupoId}` },
        ]);
      },
      error: (e) => {
        this.loading.set(false);
        this.error.set(this.msg(e));
        if (e?.status === 403) {
          // Sin acceso a este subgrupo → de vuelta al picker.
          setTimeout(() => this.router.navigate(['/subgrupo']), 1500);
        }
      },
    });
  }

  private msg(e: { error?: { detail?: string }; status?: number; message?: string }): string {
    if (e?.error?.detail) return e.error.detail;
    if (e?.status === 401 || e?.status === 403) return 'No tienes acceso a este subgrupo.';
    return e?.message || 'Error inesperado al cargar el panel del subgrupo.';
  }
}
