import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { LayoutService } from '../../core/layout/layout.service';
import { FestivalesApi } from './festivales.api';
import { EstadoFestival, Festival, FestivalCatalogos, FestivalInput } from './festivales.types';

const META_ANUAL = 15;

@Component({
  standalone: true,
  selector: 'app-festivales-list',
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page">
      <header class="page__header">
        <div>
          <h1><i class="fa fa-music" aria-hidden="true"></i> Festivales de Cultura</h1>
          <p class="page__sub">Proyecto 2780 · Meta 4 — realizar eventos de promoción y circulación cultural.</p>
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
        <div class="kpi kpi--ok">
          <span class="kpi__val">{{ ejecutados() }}</span>
          <span class="kpi__lbl">Ejecutados</span>
        </div>
        <div class="kpi kpi--prog">
          <span class="kpi__val">{{ ejecutados() }}/{{ metaAnual }}</span>
          <span class="kpi__lbl">Avance meta anual</span>
          <div class="bar"><div class="bar__fill" [style.width.%]="pctAnual()"></div></div>
        </div>
      </section>

      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando…</div> }
      @if (error()) { <div class="ui-info-bar ui-info-bar--danger">{{ error() }}</div> }

      <!-- Grid de tarjetas -->
      <section class="grid">
        @for (f of festivales(); track f.id) {
          <article class="card" [attr.data-estado]="f.estado">
            <div class="card__top">
              <span class="badge badge--{{ f.estado }}">{{ f.estado_display }}</span>
              @if (f.tipo_festival_nombre) { <span class="chip">{{ f.tipo_festival_nombre }}</span> }
            </div>
            <h3 class="card__nombre">{{ f.nombre }}</h3>
            @if (f.descripcion) { <p class="card__desc">{{ f.descripcion }}</p> }
            <div class="card__meta">
              <span><i class="fa fa-calendar"></i> {{ f.fecha_inicio || 'Sin fecha' }}</span>
              <span><i class="fa fa-list-ul"></i> {{ f.n_eventos }} acto(s)</span>
              @if (f.documentado) { <span class="ok"><i class="fa fa-images"></i> documentado</span> }
              @if (f.publicado) { <span class="ok"><i class="fa fa-globe"></i> publicado</span> }
            </div>
            <div class="card__acc">
              <button class="ui-btn ui-btn--ghost ui-btn--sm" (click)="editar(f)">
                <i class="fa fa-pen"></i> Editar
              </button>
              <button class="ui-btn ui-btn--ghost ui-btn--sm danger" (click)="eliminar(f)"
                      [disabled]="f.n_eventos > 0" [title]="f.n_eventos > 0 ? 'Tiene actos asociados' : 'Eliminar'">
                <i class="fa fa-trash"></i>
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
          <label>Nombre *<input class="ui-input" [(ngModel)]="form()!.nombre"></label>
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
            <label>Edición<input type="number" class="ui-input" [(ngModel)]="form()!.numero_edicion"></label>
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
          <label>Lugar<input class="ui-input" [(ngModel)]="form()!.lugar_texto"></label>
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
    .page { max-width: 1200px; margin: 0 auto; }
    .page__header { display: flex; justify-content: space-between; align-items: flex-start; gap: $space-3; flex-wrap: wrap; }
    .page__header h1 { margin: 0; color: $color-primary; }
    .page__header h1 i { margin-right: $space-2; }
    .page__sub { color: $color-text-muted; margin: $space-1 0 $space-3; }
    .page__actions { display: flex; gap: $space-2; align-items: center; }
    .kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: $space-3; margin-bottom: $space-4; }
    @media (max-width: 600px) { .kpis { grid-template-columns: 1fr; } }
    .kpi { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-3; display: flex; flex-direction: column; }
    .kpi--ok { border-left: 4px solid #16A34A; }
    .kpi--prog { border-left: 4px solid #8B5CF6; }
    .kpi__val { font-size: 1.8rem; font-weight: 700; color: $color-primary; }
    .kpi__lbl { color: $color-text-muted; font-size: $font-size-sm; }
    .bar { height: 8px; background: #eee; border-radius: 99px; margin-top: $space-2; overflow: hidden; }
    .bar__fill { height: 100%; background: linear-gradient(90deg, #8B5CF6, #6366F1); transition: width .4s; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: $space-3; }
    .card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-3; display: flex; flex-direction: column; gap: $space-2; transition: box-shadow .2s; }
    .card:hover { box-shadow: 0 6px 20px rgba(0,0,0,.08); }
    .card__top { display: flex; justify-content: space-between; align-items: center; gap: $space-2; }
    .card__nombre { margin: 0; font-size: 1.05rem; color: $color-text; }
    .card__desc { color: $color-text-muted; font-size: $font-size-sm; margin: 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
    .card__meta { display: flex; flex-wrap: wrap; gap: $space-2; font-size: $font-size-sm; color: $color-text-muted; }
    .card__meta .ok { color: #16A34A; }
    .card__acc { display: flex; justify-content: flex-end; gap: $space-2; margin-top: auto; }
    .danger { color: #DC2626; }
    .chip { background: #F3F4F6; color: #374151; border-radius: 99px; padding: 2px 10px; font-size: .75rem; }
    .badge { border-radius: 99px; padding: 3px 12px; font-size: .72rem; font-weight: 600; text-transform: uppercase; }
    .badge--planeado { background: #FEF3C7; color: #92400E; }
    .badge--ejecutado { background: #DCFCE7; color: #166534; }
    .badge--cerrado { background: #E5E7EB; color: #374151; }
    .modal { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; padding: $space-3; z-index: 1000; }
    .modal__box { background: #fff; border-radius: $radius-lg; padding: $space-4; width: 100%; max-width: 560px; max-height: 90vh; overflow: auto; display: flex; flex-direction: column; gap: $space-2; }
    .modal__box h2 { margin: 0 0 $space-2; color: $color-primary; }
    .modal__box label { display: flex; flex-direction: column; font-size: $font-size-sm; color: $color-text; gap: 4px; }
    .modal__box .row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: $space-2; }
    @media (max-width: 600px) { .modal__box .row { grid-template-columns: 1fr; } }
    .modal__acc { display: flex; justify-content: flex-end; gap: $space-2; margin-top: $space-2; }
  `],
})
export class FestivalesListComponent implements OnInit {
  private api = inject(FestivalesApi);
  private layout = inject(LayoutService);

  loading = signal(false);
  error = signal('');
  festivales = signal<Festival[]>([]);
  catalogos = signal<FestivalCatalogos | null>(null);
  vigencia = signal<number>(2026);

  form = signal<FestivalInput | null>(null);
  editId = signal<number | null>(null);
  formError = signal('');
  saving = signal(false);

  ejecutados = computed(() => this.festivales().filter((f) => f.estado === 'ejecutado').length);
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
    this.api.catalogos().subscribe({ next: (c) => this.catalogos.set(c) });
    this.cargar();
  }

  cargar(): void {
    this.loading.set(true);
    this.error.set('');
    this.api.list({ vigencia: this.vigencia() }).subscribe({
      next: (data) => { this.festivales.set(data); this.loading.set(false); },
      error: (e) => { this.loading.set(false); this.error.set(this.msg(e)); },
    });
  }

  nuevo(): void {
    this.editId.set(null);
    this.formError.set('');
    this.form.set({ nombre: '', vigencia: this.vigencia(), estado: 'planeado', tipo_festival: null });
  }

  editar(f: Festival): void {
    this.editId.set(f.id);
    this.formError.set('');
    this.form.set({
      nombre: f.nombre, tipo_festival: f.tipo_festival, vigencia: f.vigencia,
      numero_edicion: f.numero_edicion, estado: f.estado,
      fecha_inicio: f.fecha_inicio, fecha_fin: f.fecha_fin,
      lugar_texto: f.lugar_texto, descripcion: f.descripcion,
    });
  }

  cerrar(): void { this.form.set(null); }

  guardar(): void {
    const data = this.form();
    if (!data) return;
    if (!data.nombre?.trim()) { this.formError.set('El nombre es obligatorio.'); return; }
    this.saving.set(true);
    this.formError.set('');
    const id = this.editId();
    const obs = id ? this.api.editar(id, data) : this.api.crear(data);
    obs.subscribe({
      next: () => { this.saving.set(false); this.cerrar(); this.cargar(); },
      error: (e) => { this.saving.set(false); this.formError.set(this.msg(e)); },
    });
  }

  eliminar(f: Festival): void {
    if (f.n_eventos > 0) return;
    if (!confirm(`¿Eliminar el festival "${f.nombre}"?`)) return;
    this.api.eliminar(f.id).subscribe({
      next: () => this.cargar(),
      error: (e) => this.error.set(this.msg(e)),
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
