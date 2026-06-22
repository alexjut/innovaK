import { CommonModule } from '@angular/common';
import {
  AfterViewChecked, Component, ElementRef, OnDestroy, OnInit,
  ViewChild, computed, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import * as L from 'leaflet';
import { LayoutService } from '../../core/layout/layout.service';
import { ConfirmService } from '../../shared/ui/confirm.service';
import { ToastService } from '../../shared/ui/toast.service';
import { FestivalesApi } from './festivales.api';
import { Festival, FestivalCatalogos, FestivalInput } from './festivales.types';

const META_ANUAL = 15;

@Component({
  standalone: true,
  selector: 'app-festivales-list',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <div>
          <h1><i class="fa fa-music" aria-hidden="true"></i> Festivales de Cultura</h1>
          <p class="page__sub">
            <a [routerLink]="['/presupuesto/proyectos', 2780]" class="proj-link">
              Proyecto 2780 · Meta 4
            </a>
            — realizar eventos de promoción y circulación cultural.
          </p>
        </div>
        <div class="page__actions">
          <select class="ui-input" [(ngModel)]="vigencia" (ngModelChange)="cargar()">
            @for (v of vigencias(); track v) { <option [value]="v">Vigencia {{ v }}</option> }
          </select>
          <button class="ui-btn ui-btn--primary" (click)="nuevo()">
            <i class="fa fa-plus"></i> Nuevo festival
          </button>
        </div>
      </header>

      <!-- KPIs -->
      <section class="kpis">
        <div class="kpi">
          <span class="kpi__val">{{ festivales().length }}</span>
          <span class="kpi__lbl">Festivales {{ vigencia() }}</span>
        </div>
        <div class="kpi kpi--plan">
          <span class="kpi__val">{{ planeados() }}</span>
          <span class="kpi__lbl">Planeados</span>
        </div>
        <div class="kpi kpi--ok">
          <span class="kpi__val">{{ ejecutados() }}</span>
          <span class="kpi__lbl">Ejecutados</span>
        </div>
        <div class="kpi kpi--prog">
          <span class="kpi__val">{{ planeados() }} · {{ ejecutados() }} / {{ metaAnual }}</span>
          <span class="kpi__lbl">{{ planeados() }} planeados · {{ ejecutados() }} ejecutados · meta {{ metaAnual }}</span>
          <div class="bar"><div class="bar__fill" [style.width.%]="pctAnual()"></div></div>
        </div>
      </section>

      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando…</div> }
      @if (error()) { <div class="ui-info-bar ui-info-bar--danger">{{ error() }}</div> }

      <!-- Grid de tarjetas -->
      <section class="grid">
        @for (f of festivales(); track f.id) {
          <article class="card" [attr.data-estado]="f.estado"
                   role="button" tabindex="0"
                   [attr.aria-label]="'Ver detalle del festival ' + f.nombre"
                   (click)="abrir(f)" (keyup.enter)="abrir(f)">
            <div class="card__top">
              <span class="badge badge--{{ f.estado }}">{{ f.estado_display }}</span>
              @if (incompleto(f)) {
                <span class="badge badge--warn" title="Falta fecha de inicio o no tiene actos asociados">
                  <i class="fa fa-triangle-exclamation"></i> Incompleto
                </span>
              }
              @if (f.tipo_festival_nombre) { <span class="chip">{{ f.tipo_festival_nombre }}</span> }
            </div>
            <h3 class="card__nombre">{{ f.nombre }}</h3>
            @if (f.descripcion) {
              <p class="card__desc" [title]="f.descripcion">{{ f.descripcion }}</p>
            }
            <div class="card__meta">
              <span [class.miss]="!f.fecha_inicio">
                <i class="fa fa-calendar"></i> {{ f.fecha_inicio || 'Sin fecha' }}
              </span>
              <span [class.miss]="f.n_eventos === 0">
                <i class="fa fa-list-ul"></i> {{ f.n_eventos }} acto(s)
              </span>
              @if (f.lugar_texto) { <span><i class="fa fa-location-dot"></i> {{ f.lugar_texto }}</span> }
              @if (f.documentado) { <span class="ok"><i class="fa fa-images"></i> documentado</span> }
              @if (f.publicado) { <span class="ok"><i class="fa fa-globe"></i> publicado</span> }
            </div>
            <div class="card__acc" (click)="$event.stopPropagation()">
              <button class="ui-btn ui-btn--ghost ui-btn--sm" (click)="editar(f)">
                <i class="fa fa-pen"></i> Editar
              </button>
              <button class="ui-btn ui-btn--ghost ui-btn--sm danger" (click)="eliminar(f)"
                      [disabled]="f.n_eventos > 0 || eliminando() === f.id"
                      [title]="f.n_eventos > 0 ? 'Tiene actos asociados' : 'Eliminar'">
                @if (eliminando() === f.id) {
                  <i class="fa fa-spinner fa-spin"></i>
                } @else {
                  <i class="fa fa-trash"></i>
                }
              </button>
            </div>
          </article>
        }
        @if (!loading() && festivales().length === 0) {
          <div class="ui-empty-state"><i class="fa fa-music"></i><p>No hay festivales en {{ vigencia() }}.</p></div>
        }
      </section>
    </div>

    <!-- Form crear/editar -->
    @if (form()) {
      <div class="modal" (click)="cerrar()">
        <div class="modal__box" (click)="$event.stopPropagation()">
          <h2>{{ editId() ? 'Editar festival' : 'Nuevo festival' }}</h2>
          @if (formError()) { <div class="ui-info-bar ui-info-bar--danger">{{ formError() }}</div> }
          <label>Nombre *
            <input class="ui-input" [(ngModel)]="form()!.nombre"
                   [class.is-invalid]="nombreError()"
                   (input)="nombreError.set('')">
            @if (nombreError()) { <span class="field-error">{{ nombreError() }}</span> }
          </label>
          <label>Tipo
            <select class="ui-input" [(ngModel)]="form()!.tipo_festival">
              <option [ngValue]="null">—</option>
              @for (t of catalogos()?.tipos_festival || []; track t.codigo) {
                <option [ngValue]="t.codigo">{{ t.nombre }}</option>
              }
            </select>
          </label>
          <div class="row">
            <label>Vigencia *<input type="number" class="ui-input" [(ngModel)]="form()!.vigencia"></label>
            <label>
              Edición
              <input type="number" min="1" class="ui-input" placeholder="Ej: 3 para la 3ª edición"
                     [(ngModel)]="form()!.numero_edicion">
              <small class="hint">Número de edición del festival (1ª, 2ª, 3ª…). Déjalo vacío si no aplica.</small>
            </label>
            <label>Estado
              <select class="ui-input" [(ngModel)]="form()!.estado">
                @for (e of catalogos()?.estados || []; track e.value) {
                  <option [ngValue]="e.value">{{ e.label }}</option>
                }
              </select>
            </label>
          </div>
          <div class="row">
            <label>Fecha inicio<input type="date" class="ui-input" [(ngModel)]="form()!.fecha_inicio"></label>
            <label>Fecha fin<input type="date" class="ui-input" [(ngModel)]="form()!.fecha_fin"></label>
          </div>
          @if ((catalogos()?.upls?.length || 0) > 0) {
            <label>
              UPL (localización)
              <select class="ui-input" [(ngModel)]="form()!.upl_codigo">
                <option [ngValue]="null">— sin UPL —</option>
                @for (u of catalogos()?.upls || []; track u.value) {
                  <option [ngValue]="u.value">{{ u.label }}</option>
                }
              </select>
              <small class="hint">Ubica el festival en una UPL de Kennedy para el mapa.</small>
            </label>
          }
          <label>Lugar (dirección / escenario)<input class="ui-input" [(ngModel)]="form()!.lugar_texto"
                  placeholder="Ej: Plaza Fundacional de Kennedy"></label>

          <!-- FEST-F-11: punto exacto para el marcador del Mapa Kennedy -->
          <div class="geo">
            <span class="geo__lbl">Punto en el mapa</span>
            <small class="hint">Click en el mapa para ubicar el festival; sin punto no aparece en el mapa.</small>
            <div #mapEl class="geo__map"></div>
            <div class="geo__coords">
              <label>Latitud<input class="ui-input" [ngModel]="form()!.latitud" readonly placeholder="—"></label>
              <label>Longitud<input class="ui-input" [ngModel]="form()!.longitud" readonly placeholder="—"></label>
            </div>
          </div>

          <label>Descripción<textarea class="ui-input" rows="3" [(ngModel)]="form()!.descripcion"></textarea></label>
          <div class="modal__acc">
            <button class="ui-btn ui-btn--ghost" (click)="cerrar()">Cancelar</button>
            <button class="ui-btn ui-btn--primary" (click)="guardar()" [disabled]="saving()">
              {{ saving() ? 'Guardando…' : 'Guardar' }}
            </button>
          </div>
        </div>
      </div>
    }
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    /* FEST-F-08: el footer fijo del layout tapaba la última fila; reservamos
       espacio al final del contenedor para que los botones queden alcanzables. */
    .page { max-width: 1200px; margin: 0 auto; padding-bottom: $space-6; }
    .page__header { display: flex; justify-content: space-between; align-items: flex-start; gap: $space-3; flex-wrap: wrap; }
    .page__header h1 { margin: 0; color: $color-primary; }
    .page__header h1 i { margin-right: $space-2; }
    .page__sub { color: $color-text-muted; margin: $space-1 0 $space-3; }
    .proj-link { color: $color-primary; font-weight: 600; text-decoration: none; }
    .proj-link:hover { text-decoration: underline; }
    .page__actions { display: flex; gap: $space-2; align-items: center; }
    .kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: $space-3; margin-bottom: $space-4; }
    @media (max-width: 860px) { .kpis { grid-template-columns: 1fr 1fr; } }
    @media (max-width: 520px) { .kpis { grid-template-columns: 1fr; } }
    .kpi { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-3; display: flex; flex-direction: column; }
    .kpi--plan { border-left: 4px solid #F59E0B; }
    .kpi--ok { border-left: 4px solid #16A34A; }
    .kpi--prog { border-left: 4px solid #8B5CF6; }
    .kpi__val { font-size: 1.6rem; font-weight: 700; color: $color-primary; }
    .kpi__lbl { color: $color-text-muted; font-size: $font-size-sm; }
    .bar { height: 8px; background: #eee; border-radius: 99px; margin-top: $space-2; overflow: hidden; }
    .bar__fill { height: 100%; background: linear-gradient(90deg, #8B5CF6, #6366F1); transition: width .4s; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: $space-3; }
    .card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-3; display: flex; flex-direction: column; gap: $space-2; transition: box-shadow .2s, transform .15s; cursor: pointer; }
    .card:hover { box-shadow: 0 6px 20px rgba(0,0,0,.08); transform: translateY(-2px); }
    .card:focus-visible { outline: 2px solid $color-primary; outline-offset: 2px; }
    .card__top { display: flex; justify-content: flex-start; align-items: center; gap: $space-2; flex-wrap: wrap; }
    .card__nombre { margin: 0; font-size: 1.05rem; color: $color-text; }
    .card__desc { color: $color-text-muted; font-size: $font-size-sm; margin: 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; cursor: help; }
    .card__meta { display: flex; flex-wrap: wrap; gap: $space-2; font-size: $font-size-sm; color: $color-text-muted; }
    .card__meta .ok { color: #16A34A; }
    .card__meta .miss { color: #B45309; }
    .card__acc { display: flex; justify-content: flex-end; gap: $space-2; margin-top: auto; }
    .danger { color: #DC2626; }
    .chip { background: #F3F4F6; color: #374151; border-radius: 99px; padding: 2px 10px; font-size: .75rem; }
    .badge { border-radius: 99px; padding: 3px 12px; font-size: .72rem; font-weight: 600; }
    .badge--planeado { background: #FEF3C7; color: #92400E; }
    .badge--ejecutado { background: #DCFCE7; color: #166534; }
    .badge--cerrado { background: #E5E7EB; color: #374151; }
    .badge--warn { background: #FEE2E2; color: #991B1B; }
    .badge--warn i { margin-right: 4px; }
    .hint { color: $color-text-muted; font-size: .72rem; font-weight: 400; margin-top: 2px; }
    .modal { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; padding: $space-3; z-index: 1000; }
    .modal__box { background: #fff; border-radius: $radius-lg; padding: $space-4; width: 100%; max-width: 560px; max-height: 90vh; overflow: auto; display: flex; flex-direction: column; gap: $space-2; }
    .modal__box h2 { margin: 0 0 $space-2; color: $color-primary; }
    .modal__box label { display: flex; flex-direction: column; font-size: $font-size-sm; color: $color-text; gap: 4px; }
    .modal__box .row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: $space-2; }
    @media (max-width: 600px) { .modal__box .row { grid-template-columns: 1fr; } }
    .modal__acc { display: flex; justify-content: flex-end; gap: $space-2; margin-top: $space-2; }
    .geo { display: flex; flex-direction: column; gap: 4px; }
    .geo__lbl { font-size: $font-size-sm; color: $color-text; }
    .geo__map { height: 220px; border: 1px solid $color-border; border-radius: $radius-md; }
    .geo__coords { display: grid; grid-template-columns: 1fr 1fr; gap: $space-2; }
    .geo__coords input[readonly] { background: #F9FAFB; color: $color-text-muted; }
  `],
})
export class FestivalesListComponent implements OnInit, AfterViewChecked, OnDestroy {
  private api = inject(FestivalesApi);
  private layout = inject(LayoutService);
  private router = inject(Router);
  private toast = inject(ToastService);
  private confirm = inject(ConfirmService);

  @ViewChild('mapEl') private mapEl?: ElementRef<HTMLDivElement>;
  private map?: L.Map;
  private marker?: L.Marker;

  loading = signal(false);
  error = signal('');
  festivales = signal<Festival[]>([]);
  catalogos = signal<FestivalCatalogos | null>(null);
  vigencia = signal<number>(2026);

  form = signal<FestivalInput | null>(null);
  editId = signal<number | null>(null);
  formError = signal('');
  nombreError = signal('');
  saving = signal(false);
  /** Id del festival cuyo DELETE está en curso (deshabilita el botón). */
  eliminando = signal<number | null>(null);

  // FEST-F-07: el resumen del backend (planeados/ejecutados por vigencia)
  // es la fuente de verdad; si no llegó, se calcula de la lista cargada.
  planeados = computed(() =>
    this.catalogos()?.resumen?.planeados
      ?? this.festivales().filter((f) => f.estado === 'planeado').length,
  );
  ejecutados = computed(() =>
    this.catalogos()?.resumen?.ejecutados
      ?? this.festivales().filter((f) => f.estado === 'ejecutado').length,
  );
  pctAnual = computed(() => Math.min(100, Math.round((this.ejecutados() / META_ANUAL) * 100)));
  metaAnual = META_ANUAL;
  vigencias = computed(() => {
    const vs = this.catalogos()?.vigencias ?? [];
    return vs.length ? vs : [2026];
  });

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Festivales' },
    ]);
    this.cargarCatalogos();
    this.cargar();
  }

  /** FEST-F-05: el festival está incompleto si le falta fecha o no tiene actos. */
  incompleto(f: Festival): boolean {
    return !f.fecha_inicio || f.n_eventos === 0;
  }

  private cargarCatalogos(): void {
    this.api.catalogos(this.vigencia()).subscribe({ next: (c) => this.catalogos.set(c) });
  }

  cargar(): void {
    this.loading.set(true);
    this.error.set('');
    this.cargarCatalogos();
    this.api.list({ vigencia: this.vigencia() }).subscribe({
      next: (data) => { this.festivales.set(data); this.loading.set(false); },
      error: (e) => { this.loading.set(false); this.error.set(this.msg(e)); },
    });
  }

  /** FEST-F-09: la tarjeta es clicable → vista de detalle del festival. */
  abrir(f: Festival): void {
    this.router.navigate(['/festivales', f.id]);
  }

  nuevo(): void {
    this.editId.set(null);
    this.formError.set('');
    this.nombreError.set('');
    this.form.set({
      nombre: '', vigencia: this.vigencia(), estado: 'planeado', tipo_festival: null,
      upl_codigo: null, latitud: null, longitud: null,
    });
  }

  editar(f: Festival): void {
    this.editId.set(f.id);
    this.formError.set('');
    this.nombreError.set('');
    this.form.set({
      nombre: f.nombre, tipo_festival: f.tipo_festival, vigencia: f.vigencia,
      numero_edicion: f.numero_edicion, estado: f.estado,
      fecha_inicio: f.fecha_inicio, fecha_fin: f.fecha_fin,
      lugar_texto: f.lugar_texto, descripcion: f.descripcion,
      upl_codigo: f.upl_codigo ?? null,
      latitud: f.latitud ?? null, longitud: f.longitud ?? null,
    });
  }

  cerrar(): void {
    this.destroyMap();
    this.form.set(null);
  }

  /** El minimapa se crea cuando el modal entra al DOM (form() != null). */
  ngAfterViewChecked(): void {
    if (this.form() && this.mapEl?.nativeElement && !this.map) {
      this.initMap();
    }
  }

  ngOnDestroy(): void {
    this.destroyMap();
  }

  private initMap(): void {
    const el = this.mapEl!.nativeElement;
    const data = this.form();
    const lat = data?.latitud != null ? Number(data.latitud) : null;
    const lon = data?.longitud != null ? Number(data.longitud) : null;
    this.map = L.map(el, {
      center: [lat ?? 4.628, lon ?? -74.153],
      zoom: lat != null && lon != null ? 15 : 13,
    });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OpenStreetMap &copy; CARTO',
      subdomains: 'abcd', maxZoom: 19,
    }).addTo(this.map);
    if (lat != null && lon != null && !isNaN(lat) && !isNaN(lon)) {
      this.marker = L.marker([lat, lon]).addTo(this.map);
    }
    this.map.on('click', (e: L.LeafletMouseEvent) => {
      const la = Math.round(e.latlng.lat * 1e6) / 1e6;
      const lo = Math.round(e.latlng.lng * 1e6) / 1e6;
      this.form.update((f) => f ? { ...f, latitud: la, longitud: lo } : f);
      if (this.marker) this.marker.setLatLng([la, lo]);
      else this.marker = L.marker([la, lo]).addTo(this.map!);
    });
    // Leaflet necesita recalcular el tamaño tras renderizar el modal.
    setTimeout(() => this.map?.invalidateSize(), 0);
  }

  private destroyMap(): void {
    this.map?.remove();
    this.map = undefined;
    this.marker = undefined;
  }

  guardar(): void {
    const data = this.form();
    if (!data) return;
    if (!data.nombre?.trim()) { this.nombreError.set('El nombre es obligatorio.'); return; }
    this.saving.set(true);
    this.formError.set('');
    this.nombreError.set('');
    const id = this.editId();
    const obs = id ? this.api.editar(id, data) : this.api.crear(data);
    obs.subscribe({
      next: () => {
        this.saving.set(false);
        this.toast.success(id ? 'Festival actualizado ✓' : 'Festival creado correctamente ✓');
        this.cerrar();
        this.cargar();
      },
      error: (e) => { this.saving.set(false); this.formError.set(this.msg(e)); },
    });
  }

  async eliminar(f: Festival): Promise<void> {
    if (f.n_eventos > 0 || this.eliminando() !== null) return;
    const ok = await this.confirm.ask({
      title: 'Eliminar festival',
      message: `¿Eliminar el festival "${f.nombre}"? Esta acción no se puede deshacer.`,
      danger: true,
      confirmText: 'Eliminar',
    });
    if (!ok) return;
    this.eliminando.set(f.id);
    this.error.set('');
    this.api.eliminar(f.id).subscribe({
      next: () => {
        this.eliminando.set(null);
        this.toast.success('Festival eliminado ✓');
        this.cargar();
      },
      error: (e) => { this.eliminando.set(null); this.error.set(this.msg(e)); },
    });
  }

  private msg(e: { error?: { detail?: string; nombre?: string[]; non_field_errors?: string[] }; status?: number; message?: string }): string {
    const b = e?.error;
    if (b?.detail) return b.detail;
    if (b?.non_field_errors?.length) return b.non_field_errors[0];
    if (b?.nombre?.length) return `Nombre: ${b.nombre[0]}`;
    if (e?.status === 401 || e?.status === 403) return 'No tienes permiso para gestionar festivales.';
    return e?.message || 'Error inesperado.';
  }
}
