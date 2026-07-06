import { CommonModule } from '@angular/common';
import {
  AfterViewInit, Component, ElementRef, OnDestroy, OnInit,
  ViewChild, computed, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import * as L from 'leaflet';
import { AuthService } from '../../core/auth/auth.service';
import { LayoutService } from '../../core/layout/layout.service';
import { formatMoneda } from '../../shared/format/format.util';
import { EventoQrFormComponent } from '../../shared/evento-qr-form/evento-qr-form.component';
import { SubgrupoApi } from './subgrupo.api';
import {
  ContratoSubgrupo,
  EventoGeoFeatureCollection,
  EventoSubgrupo,
  GrupoGeneral,
  IndicadorLite,
  ProyectoArea,
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
  imports: [CommonModule, RouterLink, FormsModule, EventoQrFormComponent],
  template: `
    <div class="page">
      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando…</div> }
      @if (error()) { <div class="ui-info-bar ui-info-bar--danger">{{ error() }}</div> }

      @if (!loading() && cargado()) {
        <header class="page__header">
          <div>
            <a routerLink="/subgrupo" class="ui-back-link">
              <i class="fa fa-arrow-left"></i> Mis áreas
            </a>
            <h1><i class="fa fa-sitemap" aria-hidden="true"></i>
              {{ subgrupo().nombre || 'Área ' + subgrupoId }}</h1>
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

        <!-- ── Mini-mapa contextual de los eventos del subgrupo (B5) ── -->
        @if (tieneGeo()) {
          <section class="mapa-card">
            <div class="mapa-card__head">
              <h2 class="sec__title"><i class="fa fa-map-location-dot"></i> Eventos en el territorio</h2>
              <span class="chip">{{ nGeo() }} ubicado{{ nGeo() === 1 ? '' : 's' }}</span>
            </div>
            <div #mapa class="mapa"></div>
          </section>
        }

        <div class="layout">
          <!-- ── Tronco "General": eventos por actividad_plan ── -->
          <main class="general">
            <div class="general__banner">
              <i class="fa fa-star"></i>
              <div>
                <strong>General del área</strong>
                <p>Es el tronco operativo: la mayoría de los eventos del área
                  (≈75%) <em>no tienen contrato</em> y cuelgan directamente de
                  una actividad del plan. Esto es lo que se gestiona a diario.</p>
              </div>
            </div>
            <div class="general__head">
              <h2 class="sec__title"><i class="fa fa-folder-tree"></i> Actividades del área</h2>
              @if (esCoordinador()) {
                <button class="ui-btn ui-btn--sm ui-btn--primary" (click)="toggleCrear()">
                  <i class="fa fa-plus"></i> Crear actividad
                </button>
              }
            </div>

            @if (crearAbierto()) {
              <form class="crear" (ngSubmit)="guardarActividad()">
                @if (crearError()) {
                  <div class="ui-info-bar ui-info-bar--danger">{{ crearError() }}</div>
                }
                <label class="crear__field">Proyecto / meta del área *
                  <select [ngModel]="proyectoSel()" (ngModelChange)="onProyecto($event)"
                          name="proyecto" required>
                    <option [ngValue]="null" disabled>Elige un proyecto…</option>
                    @for (p of proyectos(); track p.id) {
                      <option [ngValue]="p.id">{{ p.codigo ? p.codigo + ' · ' : '' }}{{ p.nombre || ('Proyecto ' + p.id) }}</option>
                    }
                  </select>
                </label>
                <label class="crear__field">Descripción de la actividad *
                  <input type="text" [ngModel]="descripcion()" (ngModelChange)="descripcion.set($event)"
                         name="descripcion" required maxlength="500"
                         placeholder="Qué actividad del plan se ejecutará…">
                </label>
                <label class="crear__field">Indicador / KPI (opcional)
                  <select [ngModel]="indicadorSel()" (ngModelChange)="indicadorSel.set($event)" name="indicador">
                    <option [ngValue]="null">— Sin vincular —</option>
                    @for (i of indicadoresDisponibles(); track i.id) {
                      <option [ngValue]="i.id">{{ i.nombre }}{{ i.unidad ? ' (' + i.unidad + ')' : '' }}</option>
                    }
                  </select>
                </label>
                <div class="crear__actions">
                  <button type="submit" class="ui-btn ui-btn--sm ui-btn--primary"
                          [disabled]="guardando() || !proyectoSel() || !descripcion().trim()">
                    <i class="fa fa-save"></i> {{ guardando() ? 'Guardando…' : 'Crear actividad' }}
                  </button>
                  <button type="button" class="ui-btn ui-btn--sm ui-btn--ghost" (click)="toggleCrear()">
                    Cancelar
                  </button>
                </div>
              </form>
            }

            @if (general().length === 0) {
              <div class="ui-empty-state">
                <i class="fa fa-folder-open"></i>
                <p>Esta área aún no tiene eventos registrados.</p>
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
                              @if (ev.url_publica) {
                                <app-evento-qr-form [eventoId]="ev.id" [urlPublica]="ev.url_publica" />
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
              <p class="vacio">Sin contratos vinculados a los proyectos del área.</p>
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

    .mapa-card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-3; margin-bottom: $space-4; }
    .mapa-card__head { display: flex; align-items: center; gap: $space-2; justify-content: space-between; margin-bottom: $space-2; }
    .mapa-card__head .sec__title { margin: 0; }
    .mapa { height: 320px; width: 100%; border-radius: $radius-md; overflow: hidden; z-index: 0; }

    .layout { display: grid; grid-template-columns: 1fr 320px; gap: $space-4; align-items: start; }
    @media (max-width: 980px) { .layout { grid-template-columns: 1fr; } }
    .sec__title { color: $color-primary; font-size: 1.05rem; margin: 0 0 $space-2; }
    .sec__title i { margin-right: $space-2; }

    .general__banner { display: flex; gap: $space-2; align-items: flex-start; background: linear-gradient(90deg, #ECFDF5, #fff); border: 1px solid #A7F3D0; border-left: 4px solid #16A34A; border-radius: $radius-md; padding: $space-2 $space-3; margin-bottom: $space-3; }
    .general__banner i { color: #16A34A; margin-top: 3px; }
    .general__banner strong { color: #065F46; }
    .general__banner p { color: $color-text-muted; font-size: .8rem; margin: 2px 0 0; }

    .general__head { display: flex; align-items: center; justify-content: space-between; gap: $space-2; flex-wrap: wrap; }
    .general__head .sec__title { margin: 0; }
    .crear { background: #fff; border: 1px solid $color-border; border-left: 4px solid $color-primary; border-radius: $radius-lg; padding: $space-3; margin-bottom: $space-3; display: flex; flex-direction: column; gap: $space-2; }
    .crear__field { display: flex; flex-direction: column; gap: 4px; font-size: $font-size-sm; color: $color-text; }
    .crear__field select, .crear__field input { height: 36px; border: 1px solid $color-border; border-radius: $radius-md; padding: 0 $space-2; font-size: $font-size-sm; background: #fff; color: $color-text; }
    .crear__field select:focus, .crear__field input:focus { border-color: $color-border-strong; outline: none; }
    .crear__actions { display: flex; gap: $space-2; margin-top: $space-1; }

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
export class SubgrupoDetalleComponent implements OnInit, AfterViewInit, OnDestroy {
  private api = inject(SubgrupoApi);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private layout = inject(LayoutService);
  private auth = inject(AuthService);

  @ViewChild('mapa') mapEl?: ElementRef<HTMLDivElement>;

  subgrupoId = 0;
  loading = signal(false);
  error = signal('');
  cargado = signal(false);
  subgrupo = signal<SubgrupoRef>({ id: 0, nombre: null, dependencia: null });
  tiles = signal<SubgrupoTiles>(TILES_VACIO);
  general = signal<GrupoGeneral[]>([]);
  contratos = signal<ContratoSubgrupo[]>([]);

  // ── PR-A · Crear actividad (solo Coordinador; el gate real está en backend) ──
  /** Familia Coordinador (o superuser). Solo decide si SE MUESTRA el botón;
   *  la seguridad la impone CoordinadorPermission en el endpoint. */
  esCoordinador = computed<boolean>(() => {
    const u = this.auth.user();
    return !!u && (u.is_superuser || (u.groups ?? []).some((g) => g.startsWith('Coordinador')));
  });
  crearAbierto = signal(false);
  proyectos = signal<ProyectoArea[]>([]);
  proyectoSel = signal<number | null>(null);
  descripcion = signal('');
  indicadorSel = signal<number | null>(null);
  guardando = signal(false);
  crearError = signal('');
  indicadoresDisponibles = computed<IndicadorLite[]>(() => {
    const p = this.proyectos().find((x) => x.id === this.proyectoSel());
    return p?.indicadores ?? [];
  });

  // ── Mini-mapa contextual (B5) ───────────────────────────────────
  private map?: L.Map;
  private geo = signal<EventoGeoFeatureCollection | null>(null);
  tieneGeo = computed(() => (this.geo()?.features?.length ?? 0) > 0);
  nGeo = computed(() => this.geo()?.features?.length ?? 0);

  ngOnInit(): void {
    this.route.paramMap.subscribe((p) => {
      this.subgrupoId = Number(p.get('id') || '0');
      this.cargar();
    });
  }

  ngAfterViewInit(): void {
    // El contenedor del mapa solo existe cuando hay eventos georreferenciados.
    const tryInit = () => {
      if (this.map) return;
      if (this.tieneGeo() && this.mapEl?.nativeElement) { this.initMap(); }
      else if (this.loading() || (this.geo() === null && !this.error())) { setTimeout(tryInit, 150); }
    };
    setTimeout(tryInit, 200);
  }

  ngOnDestroy(): void { this.map?.remove(); }

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

  // ── PR-A · Crear actividad ──────────────────────────────────────
  toggleCrear(): void {
    const abrir = !this.crearAbierto();
    this.crearAbierto.set(abrir);
    this.crearError.set('');
    if (abrir && this.proyectos().length === 0) {
      this.api.proyectosDelArea(this.subgrupoId).subscribe({
        next: (r) => this.proyectos.set(r.results ?? []),
        error: (e) => this.crearError.set(this.msg(e)),
      });
    }
  }

  onProyecto(id: number | null): void {
    this.proyectoSel.set(id);
    this.indicadorSel.set(null);  // el indicador depende del proyecto
  }

  guardarActividad(): void {
    const pid = this.proyectoSel();
    const desc = this.descripcion().trim();
    if (!pid || !desc || this.guardando()) return;
    this.guardando.set(true);
    this.crearError.set('');
    this.api.crearActividad(this.subgrupoId, {
      proyecto_id: pid, descripcion: desc, indicador_id: this.indicadorSel(),
    }).subscribe({
      next: () => {
        this.guardando.set(false);
        this.crearAbierto.set(false);
        this.proyectoSel.set(null);
        this.descripcion.set('');
        this.indicadorSel.set(null);
        this.cargar();  // recarga el panel → la actividad nueva aparece en "General"
      },
      error: (e) => { this.guardando.set(false); this.crearError.set(this.msg(e)); },
    });
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
          { label: 'Áreas', url: '/subgrupo' },
          { label: p.subgrupo.nombre || `Área ${this.subgrupoId}` },
        ]);
        this.cargarGeo();
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

  // ── Mini-mapa contextual (B5) ───────────────────────────────────
  private cargarGeo(): void {
    this.api.eventosGeo(this.subgrupoId).subscribe({
      next: (fc) => { this.geo.set(fc); this.pintarMapa(); },
      error: () => { this.geo.set({ type: 'FeatureCollection', features: [] }); },
    });
  }

  private initMap(): void {
    if (this.map || !this.mapEl?.nativeElement) return;
    this.map = L.map(this.mapEl.nativeElement, { center: [4.628, -74.153], zoom: 12 });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      attribution: '© OpenStreetMap © CARTO', subdomains: 'abcd', maxZoom: 19,
    }).addTo(this.map);
    this.pintarMapa();
  }

  private pintarMapa(): void {
    if (!this.map) { setTimeout(() => this.initMap(), 100); return; }
    this.map.eachLayer((layer) => {
      if (!(layer instanceof L.TileLayer)) this.map!.removeLayer(layer);
    });
    const fc = this.geo();
    if (!fc) return;
    const bounds: L.LatLngExpression[] = [];
    for (const f of fc.features) {
      if (!f.geometry || f.geometry.type !== 'Point') continue;
      const [lng, lat] = f.geometry.coordinates;
      const pt = [lat, lng] as L.LatLngExpression;
      const color = f.properties.activo ? '#16A34A' : '#9CA3AF';
      L.circleMarker(pt, { radius: 8, color: '#fff', weight: 2, fillColor: color, fillOpacity: 0.95 })
        .bindPopup(this.popup(f.properties)).addTo(this.map);
      bounds.push(pt);
    }
    if (bounds.length) this.map.fitBounds(L.latLngBounds(bounds).pad(0.2));
    setTimeout(() => this.map?.invalidateSize(), 60);
  }

  private popup(p: EventoGeoFeatureCollection['features'][number]['properties']): string {
    const esc = (s: string | null) => (s ?? '').replace(/[<>&"]/g, (c) =>
      ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c] || c));
    const lineas = [
      `<strong>${esc(p.nombre) || 'Evento ' + p.id}</strong>`,
      p.tipo_evento_nombre ? `<span>${esc(p.tipo_evento_nombre)}</span>` : '',
      p.fecha_inicio ? `<small>📅 ${esc(p.fecha_inicio)}</small>` : '',
      p.direccion ? `<small>📍 ${esc(p.direccion)}</small>` : '',
      p.funcionario ? `<small>👤 ${esc(p.funcionario)}</small>` : '',
    ].filter(Boolean);
    return `<div style="display:flex;flex-direction:column;gap:2px">${lineas.join('')}</div>`;
  }

  private msg(e: { error?: { detail?: string }; status?: number; message?: string }): string {
    if (e?.error?.detail) return e.error.detail;
    if (e?.status === 401 || e?.status === 403) return 'No tienes acceso a esta área.';
    return e?.message || 'Error inesperado al cargar el panel del área.';
  }
}
