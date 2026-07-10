import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { FestivalBibliotecaComponent } from './festival-biblioteca.component';
import { FestivalEvaluacionComponent } from './festival-evaluacion.component';
import { FestivalesApi } from './festivales.api';
import {
  FestivalCatalogos, FestivalDetalle, FestivalDia, FestivalDiaInput, FestivalEvento,
  FestivalInput,
} from './festivales.types';

/**
 * Vista de detalle de un festival (FEST-F-09 + PR-A): datos generales +
 * **agenda multi-día** (Festival → Días → Actos). Cada día se gestiona
 * (crear/editar/eliminar) y los actos se ubican en su día desde la bandeja
 * "Actos sin día".
 */
@Component({
  standalone: true,
  selector: 'app-festival-detalle',
  imports: [CommonModule, FormsModule, RouterLink, FestivalBibliotecaComponent, FestivalEvaluacionComponent],
  template: `
    <div class="page">
      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando festival…</div> }
      @if (!loading() && error()) {
        <div class="ui-info-bar ui-info-bar--danger"><strong>Error:</strong> {{ error() }}</div>
        <a routerLink="/festivales" class="ui-btn ui-btn--ghost"><i class="fa fa-arrow-left"></i> Volver</a>
      }

      @if (!loading() && !error() && festival(); as f) {
        <header class="page__header">
          <div>
            <h1><i class="fa fa-music" aria-hidden="true"></i> {{ f.nombre }}</h1>
            <p class="page__sub">
              <span class="badge badge--{{ f.estado }}">{{ f.estado_display }}</span>
              @if (f.tipo_festival_nombre) { <span class="chip">{{ f.tipo_festival_nombre }}</span> }
              @if (f.numero_edicion) { <span class="chip">{{ f.numero_edicion }}ª edición</span> }
              <span class="chip">Vigencia {{ f.vigencia }}</span>
            </p>
          </div>
          <div class="actions">
            <a routerLink="/festivales" class="ui-btn ui-btn--ghost ui-btn--sm">
              <i class="fa fa-arrow-left"></i> Listado
            </a>
            <a [routerLink]="['/presupuesto/proyectos', 2780]" class="ui-btn ui-btn--ghost ui-btn--sm">
              <i class="fa fa-coins"></i> Ver en presupuesto
            </a>
            <button class="ui-btn ui-btn--sm" [class.ui-btn--primary]="!f.publicado" [class.ui-btn--ghost]="f.publicado"
                    (click)="togglePublicar(f)">
              <i class="fa" [class.fa-globe]="!f.publicado" [class.fa-eye-slash]="f.publicado"></i>
              {{ f.publicado ? 'Despublicar' : 'Publicar' }}
            </button>
            @if (f.publicado && f.slug) {
              <a [href]="'/app/p/festival/' + f.slug" target="_blank" class="ui-btn ui-btn--ghost ui-btn--sm">
                <i class="fa fa-arrow-up-right-from-square"></i> Ver ficha pública
              </a>
            }
          </div>
        </header>

        @if (flash()) { <div class="ui-info-bar ui-info-bar--success">{{ flash() }}</div> }

        <section class="info">
          <div class="info__head">
            <h2>Datos generales</h2>
            @if (!showEdit()) {
              <button class="ui-btn ui-btn--sm ui-btn--ghost" (click)="abrirEditar(f)">
                <i class="fa fa-pen"></i> Editar
              </button>
            }
          </div>

          @if (!showEdit()) {
            <dl>
              <dt>Tipo</dt>
              <dd>{{ f.tipo_festival_nombre || '—' }}@if (f.numero_edicion) { · Edición {{ f.numero_edicion }} } · Vigencia {{ f.vigencia }}</dd>
              <dt>Fechas</dt>
              <dd>
                {{ f.fecha_inicio || 'Sin fecha de inicio' }}
                @if (f.fecha_fin) { — {{ f.fecha_fin }} }
              </dd>
              <dt>Responsable</dt>
              <dd>{{ f.responsable_nombre || '—' }}</dd>
              <dt>Lugar</dt>
              <dd>{{ f.lugar_texto || '—' }}</dd>
              <dt>Agenda</dt>
              <dd>{{ f.n_dias }} día(s) · {{ f.n_eventos }} acto(s)</dd>
              <dt>Estado documental</dt>
              <dd>
                <span [class.ok]="f.documentado">{{ f.documentado ? 'Documentado' : 'Sin documentar' }}</span>
                ·
                <span [class.ok]="f.publicado">{{ f.publicado ? 'Publicado' : 'No publicado' }}</span>
              </dd>
            </dl>
            @if (f.descripcion) { <p class="desc">{{ f.descripcion }}</p> }
          } @else {
            <form class="edit-form" (ngSubmit)="guardarFestival(f.id)">
              @if (editErr()) { <div class="ui-info-bar ui-info-bar--error">{{ editErr() }}</div> }
              <div class="edit-grid">
                <label class="edit-field edit-field--wide">Nombre
                  <input type="text" [(ngModel)]="editForm.nombre" name="nombre" required>
                </label>
                <label class="edit-field">Tipo de festival
                  <select [(ngModel)]="editForm.tipo_festival" name="tipo_festival">
                    <option [ngValue]="null">— Sin tipo —</option>
                    @for (t of tiposFestival(); track t.codigo) { <option [ngValue]="t.codigo">{{ t.nombre }}</option> }
                  </select>
                </label>
                <label class="edit-field">Estado
                  <select [(ngModel)]="editForm.estado" name="estado">
                    @for (e of estados(); track e.value) { <option [ngValue]="e.value">{{ e.label }}</option> }
                  </select>
                </label>
                <label class="edit-field">Vigencia
                  <input type="number" [(ngModel)]="editForm.vigencia" name="vigencia" min="2020" max="2040">
                </label>
                <label class="edit-field">N.º de edición
                  <input type="number" [(ngModel)]="editForm.numero_edicion" name="numero_edicion" min="1">
                </label>
                <label class="edit-field">Fecha de inicio
                  <input type="date" [(ngModel)]="editForm.fecha_inicio" name="fecha_inicio">
                </label>
                <label class="edit-field">Fecha de fin
                  <input type="date" [(ngModel)]="editForm.fecha_fin" name="fecha_fin">
                </label>
                <label class="edit-field">Responsable
                  <select [(ngModel)]="editForm.responsable" name="responsable">
                    <option [ngValue]="null">— Sin responsable —</option>
                    @for (r of responsables(); track r.value) { <option [ngValue]="r.value">{{ r.label }}</option> }
                  </select>
                </label>
                <label class="edit-field">UPL (área)
                  <select [(ngModel)]="editForm.upl_codigo" name="upl_codigo">
                    <option [ngValue]="null">— Sin UPL —</option>
                    @for (u of upls(); track u.value) { <option [ngValue]="u.value">{{ u.label }}</option> }
                  </select>
                </label>
                <label class="edit-field edit-field--wide">Lugar
                  <input type="text" [(ngModel)]="editForm.lugar_texto" name="lugar_texto" placeholder="Parque, escenario, dirección…">
                </label>
                <label class="edit-field edit-field--wide">Descripción
                  <textarea [(ngModel)]="editForm.descripcion" name="descripcion" rows="3"></textarea>
                </label>
              </div>
              <div class="edit-actions">
                <button type="submit" class="ui-btn ui-btn--primary ui-btn--sm" [disabled]="savingFest()">
                  <i class="fa fa-floppy-disk"></i> {{ savingFest() ? 'Guardando…' : 'Guardar cambios' }}
                </button>
                <button type="button" class="ui-btn ui-btn--ghost ui-btn--sm" (click)="cancelarEditar()" [disabled]="savingFest()">
                  Cancelar
                </button>
              </div>
            </form>
          }
        </section>

        <!-- ── Agenda multi-día ─────────────────────────────────────── -->
        <section class="agenda">
          <div class="agenda__head">
            <h2><i class="fa fa-calendar-days"></i> Programación por días</h2>
            @if (!showDiaForm()) {
              <button class="ui-btn ui-btn--primary ui-btn--sm" (click)="nuevoDia()">
                <i class="fa fa-plus"></i> Agregar día
              </button>
            }
          </div>

          @if (showDiaForm()) {
            <form class="dia-form" (ngSubmit)="guardarDia(f.id)">
              <h3>{{ editId() ? 'Editar día' : 'Nuevo día' }}</h3>
              <div class="grid">
                <label>Fecha *
                  <input type="date" [(ngModel)]="form.fecha" name="fecha" required
                         [min]="f.fecha_inicio || null" [max]="f.fecha_fin || null">
                </label>
                <label>Título del día
                  <input type="text" [(ngModel)]="form.nombre" name="nombre"
                         placeholder="Ej. Día de apertura">
                </label>
                <label>Escenario
                  <input type="text" [(ngModel)]="form.escenario_texto" name="escenario"
                         placeholder="Parque, plaza, tarima…">
                </label>
                <label>Responsable del día
                  <select [(ngModel)]="form.responsable" name="responsable">
                    <option [ngValue]="null">— Sin asignar —</option>
                    @for (r of responsables(); track r.value) {
                      <option [ngValue]="r.value">{{ r.label }}</option>
                    }
                  </select>
                </label>
              </div>
              <label class="full">Notas del día
                <textarea [(ngModel)]="form.descripcion" name="descripcion" rows="2"></textarea>
              </label>
              @if (formError()) { <div class="ui-info-bar ui-info-bar--danger">{{ formError() }}</div> }
              <div class="dia-form__actions">
                <button type="submit" class="ui-btn ui-btn--primary ui-btn--sm" [disabled]="saving()">
                  <i class="fa fa-check"></i> {{ saving() ? 'Guardando…' : 'Guardar día' }}
                </button>
                <button type="button" class="ui-btn ui-btn--ghost ui-btn--sm" (click)="cancelarDia()">
                  Cancelar
                </button>
              </div>
            </form>
          }

          @if (f.dias.length === 0 && !showDiaForm()) {
            <div class="ui-empty-state ui-empty-state--sm">
              <i class="fa fa-calendar-plus"></i>
              <p>Aún no hay días en la agenda. Agrega el primer día del festival.</p>
            </div>
          }

          <div class="timeline">
            @for (d of f.dias; track d.id) {
              <article class="dia">
                <div class="dia__rail"><span class="dia__dot"></span></div>
                <div class="dia__body">
                  <header class="dia__head">
                    <div>
                      <span class="dia__fecha">{{ d.fecha }}</span>
                      @if (d.nombre) { <span class="dia__nombre">{{ d.nombre }}</span> }
                    </div>
                    <div class="dia__tools">
                      <button class=" link" (click)="editarDia(d)" title="Editar día"><i class="fa fa-pen"></i></button>
                      <button class="link link--danger" (click)="eliminarDia(d)" title="Eliminar día"><i class="fa fa-trash"></i></button>
                    </div>
                  </header>
                  <p class="dia__meta">
                    @if (d.escenario_texto) { <span><i class="fa fa-location-dot"></i> {{ d.escenario_texto }}</span> }
                    @if (d.responsable_nombre) { <span><i class="fa fa-user"></i> {{ d.responsable_nombre }}</span> }
                    <span><i class="fa fa-list-check"></i> {{ d.actos.length }} acto(s)</span>
                  </p>
                  @if (d.descripcion) { <p class="dia__desc">{{ d.descripcion }}</p> }

                  @if (d.actos.length === 0) {
                    <p class="dia__vacio">Sin actos en este día. Asígnalos desde la bandeja de abajo.</p>
                  } @else {
                    <ul class="acto-list">
                      @for (e of d.actos; track e.id) {
                        <li class="acto">
                          <a [routerLink]="['/eventos', e.id, 'editar']" class="acto__name">{{ e.nombre || 'Acto #' + e.id }}</a>
                          <div class="acto__meta">
                            @if (e.tipo_evento_nombre) { <span class="chip">{{ e.tipo_evento_nombre }}</span> }
                            @if (e.funcionario_nombre) { <span><i class="fa fa-user"></i> {{ e.funcionario_nombre }}</span> }
                            <span><i class="fa fa-clock"></i> {{ e.fecha_inicio || 'sin fecha' }}</span>
                            <span class="aforo" (click)="editarAforo(e)" title="Editar meta de aforo">
                              <i class="fa fa-users"></i> {{ e.aforo }}@if (e.aforo_proyectado) { /{{ e.aforo_proyectado }} } <i class="fa fa-pen pen"></i>
                            </span>
                            <button class="link link--danger" (click)="sacarActo(e)" title="Sacar de la agenda">
                              <i class="fa fa-xmark"></i>
                            </button>
                          </div>
                        </li>
                      }
                    </ul>
                  }
                </div>
              </article>
            }
          </div>

          <!-- Bandeja de actos sin ubicar -->
          @if (f.actos_sin_dia.length > 0) {
            <div class="sin-dia">
              <h3><i class="fa fa-inbox"></i> Actos sin día ({{ f.actos_sin_dia.length }})</h3>
              <p class="sin-dia__hint">Estos actos pertenecen al festival pero no están en ningún día. Asígnalos a una jornada.</p>
              <ul class="acto-list">
                @for (e of f.actos_sin_dia; track e.id) {
                  <li class="acto acto--sin">
                    <a [routerLink]="['/eventos', e.id, 'editar']" class="acto__name">{{ e.nombre || 'Acto #' + e.id }}</a>
                    <div class="acto__meta">
                      @if (e.tipo_evento_nombre) { <span class="chip">{{ e.tipo_evento_nombre }}</span> }
                      <span><i class="fa fa-clock"></i> {{ e.fecha_inicio || 'sin fecha' }}</span>
                      @if (f.dias.length > 0) {
                        <select class="asignar" (change)="asignarActo(e, $event)">
                          <option value="">Asignar a día…</option>
                          @for (d of f.dias; track d.id) {
                            <option [value]="d.id">{{ d.fecha }}{{ d.nombre ? ' · ' + d.nombre : '' }}</option>
                          }
                        </select>
                      }
                    </div>
                  </li>
                }
              </ul>
              @if (f.dias.length === 0) {
                <p class="sin-dia__hint">Crea al menos un día para poder asignar estos actos.</p>
              }
            </div>
          }
        </section>

        <!-- ── Biblioteca / evidencias ──────────────────────────────── -->
        <app-festival-biblioteca [festivalId]="f.id" [dias]="f.dias" [maxFotos]="maxFotos()" />

        <!-- ── Lineup + jurados + evaluación ────────────────────────── -->
        <app-festival-evaluacion [festivalId]="f.id" [dias]="f.dias" />
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1100px; margin: 0 auto; padding-bottom: $space-6; }
    .page__header { display: flex; justify-content: space-between; align-items: flex-start; gap: $space-3; flex-wrap: wrap; }
    .page__header h1 { margin: 0; color: $color-primary; }
    .page__header h1 i { margin-right: $space-2; }
    .page__sub { display: flex; gap: $space-2; flex-wrap: wrap; align-items: center; margin: $space-2 0 $space-3; }
    .actions { display: flex; gap: $space-2; align-items: center; flex-wrap: wrap; }
    .info, .agenda { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-4; margin-top: $space-3; }
    .info h2, .agenda h2 { margin: 0 0 $space-3; color: $color-primary; font-size: 1.1rem; }
    dl { display: grid; grid-template-columns: auto 1fr; gap: $space-1 $space-3; margin: 0; }
    dt { color: $color-text-muted; font-size: $font-size-sm; font-weight: 600; }
    dd { margin: 0; font-size: $font-size-sm; color: $color-text; }
    .ok { color: #16A34A; font-weight: 600; }
    .desc { color: $color-text-muted; font-size: $font-size-sm; white-space: pre-wrap; margin-top: $space-2; }
    .info__head { display: flex; align-items: center; justify-content: space-between; gap: $space-2; }
    .edit-form { margin-top: $space-2; }
    .edit-grid { display: grid; grid-template-columns: 1fr 1fr; gap: $space-3; }
    .edit-field { display: flex; flex-direction: column; gap: 4px; font-size: $font-size-sm; color: $color-text-muted; }
    .edit-field--wide { grid-column: 1 / -1; }
    .edit-field input, .edit-field select, .edit-field textarea {
      font-size: $font-size-sm; padding: 6px 8px; border: 1px solid $color-border;
      border-radius: $radius-sm; font-family: inherit; color: $color-text;
    }
    .edit-actions { display: flex; gap: $space-2; margin-top: $space-3; }
    @media (max-width: 640px) { .edit-grid { grid-template-columns: 1fr; } }

    .agenda__head { display: flex; justify-content: space-between; align-items: center; gap: $space-2; }
    .agenda__head h2 { margin: 0; }

    .dia-form { border: 1px dashed $color-border; border-radius: $radius-md; padding: $space-3; margin: $space-3 0; background: #FAFAFA; }
    .dia-form h3 { margin: 0 0 $space-2; font-size: .95rem; color: $color-text; }
    .dia-form .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: $space-2 $space-3; }
    @media (max-width: 700px) { .dia-form .grid { grid-template-columns: 1fr; } }
    .dia-form label { display: flex; flex-direction: column; gap: 4px; font-size: $font-size-sm; color: $color-text-muted; font-weight: 600; }
    .dia-form label.full { margin-top: $space-2; }
    .dia-form input, .dia-form select, .dia-form textarea { font-size: $font-size-sm; padding: 6px 8px; border: 1px solid $color-border; border-radius: $radius-sm; font-family: inherit; }
    .dia-form__actions { display: flex; gap: $space-2; margin-top: $space-3; }

    .timeline { margin-top: $space-3; display: flex; flex-direction: column; }
    .dia { display: grid; grid-template-columns: 24px 1fr; gap: $space-2; }
    .dia__rail { display: flex; flex-direction: column; align-items: center; }
    .dia__dot { width: 12px; height: 12px; border-radius: 50%; background: $color-primary; margin-top: 6px; }
    .dia__rail::after { content: ''; flex: 1; width: 2px; background: $color-border; margin-top: 2px; }
    .dia:last-child .dia__rail::after { display: none; }
    .dia__body { border: 1px solid $color-border; border-radius: $radius-md; padding: $space-3; margin-bottom: $space-3; }
    .dia__head { display: flex; justify-content: space-between; align-items: center; gap: $space-2; }
    .dia__fecha { font-weight: 700; color: $color-primary; }
    .dia__nombre { margin-left: $space-2; color: $color-text; }
    .dia__tools { display: flex; gap: $space-1; }
    .dia__meta { display: flex; gap: $space-3; flex-wrap: wrap; font-size: $font-size-sm; color: $color-text-muted; margin: $space-1 0; }
    .dia__desc { font-size: $font-size-sm; color: $color-text-muted; white-space: pre-wrap; }
    .dia__vacio { font-size: $font-size-sm; color: $color-text-muted; font-style: italic; }

    .acto-list { list-style: none; margin: $space-2 0 0; padding: 0; display: flex; flex-direction: column; gap: $space-2; }
    .acto { border: 1px solid $color-border; border-radius: $radius-sm; padding: $space-2 $space-3; }
    .acto--sin { background: #FFFBEB; }
    .acto__name { font-weight: 600; color: $color-primary; text-decoration: none; }
    .acto__name:hover { text-decoration: underline; }
    .acto__meta { display: flex; gap: $space-2; flex-wrap: wrap; font-size: $font-size-sm; color: $color-text-muted; margin-top: 4px; align-items: center; }
    .asignar { font-size: .72rem; padding: 2px 6px; border: 1px solid $color-border; border-radius: $radius-sm; }
    .chip { background: #F3F4F6; color: #374151; border-radius: 99px; padding: 2px 10px; font-size: .72rem; }
    .aforo { cursor: pointer; color: #0D9488; font-weight: 600; }
    .aforo .pen { opacity: .4; font-size: .62rem; margin-left: 2px; }
    .badge { border-radius: 99px; padding: 3px 12px; font-size: .72rem; font-weight: 600; }
    .badge--planeado { background: #FEF3C7; color: #92400E; }
    .badge--ejecutado { background: #DCFCE7; color: #166534; }
    .badge--cerrado { background: #E5E7EB; color: #374151; }
    .link { background: none; border: none; cursor: pointer; color: $color-text-muted; padding: 2px 4px; font-size: .8rem; }
    .link:hover { color: $color-primary; }
    .link--danger:hover { color: #DC2626; }

    .sin-dia { margin-top: $space-4; border-top: 1px solid $color-border; padding-top: $space-3; }
    .sin-dia h3 { margin: 0 0 $space-1; font-size: .95rem; color: $color-text; }
    .sin-dia__hint { font-size: $font-size-sm; color: $color-text-muted; margin: 0 0 $space-2; }
  `],
})
export class FestivalDetalleComponent implements OnInit {
  private api = inject(FestivalesApi);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);

  loading = signal(true);
  error = signal('');
  flash = signal('');
  festival = signal<FestivalDetalle | null>(null);
  responsables = signal<{ value: number; label: string }[]>([]);
  tiposFestival = signal<FestivalCatalogos['tipos_festival']>([]);
  upls = signal<NonNullable<FestivalCatalogos['upls']>>([]);
  estados = signal<FestivalCatalogos['estados']>([]);
  maxFotos = signal(3);

  // Edición de datos generales del festival (PATCH /festivales/api/festivales/<id>/).
  showEdit = signal(false);
  savingFest = signal(false);
  editErr = signal('');
  editForm: FestivalInput = {};

  showDiaForm = signal(false);
  editId = signal<number | null>(null);
  saving = signal(false);
  formError = signal('');
  form: FestivalDiaInput = {};

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Festivales', url: '/festivales' },
      { label: 'Detalle' },
    ]);
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (!id) { this.error.set('Festival no válido.'); this.loading.set(false); return; }
    this.api.catalogos().subscribe({
      next: (c: FestivalCatalogos) => {
        this.responsables.set(c.responsables ?? []);
        this.tiposFestival.set(c.tipos_festival ?? []);
        this.upls.set(c.upls ?? []);
        this.estados.set(c.estados ?? []);
        if (c.max_fotos) this.maxFotos.set(c.max_fotos);
      },
      error: () => this.responsables.set([]),
    });
    this.cargar(id);
  }

  private cargar(id: number): void {
    this.api.detalle(id).subscribe({
      next: (f) => {
        this.festival.set(f);
        this.loading.set(false);
        this.layout.setBreadcrumb([
          { label: 'Inicio', url: '/' },
          { label: 'Festivales', url: '/festivales' },
          { label: f.nombre },
        ]);
      },
      error: (e) => { this.loading.set(false); this.error.set(this.msg(e)); },
    });
  }

  abrirEditar(f: FestivalDetalle): void {
    this.editErr.set('');
    this.editForm = {
      nombre: f.nombre,
      tipo_festival: f.tipo_festival ?? null,
      estado: f.estado,
      vigencia: f.vigencia,
      numero_edicion: f.numero_edicion ?? null,
      fecha_inicio: f.fecha_inicio ?? null,
      fecha_fin: f.fecha_fin ?? null,
      responsable: f.responsable ?? null,
      upl_codigo: f.upl_codigo ?? null,
      lugar_texto: f.lugar_texto ?? '',
      descripcion: f.descripcion ?? '',
    };
    this.showEdit.set(true);
  }

  cancelarEditar(): void {
    this.showEdit.set(false);
    this.editErr.set('');
  }

  guardarFestival(id: number): void {
    if (!this.editForm.nombre || !this.editForm.nombre.trim()) {
      this.editErr.set('El nombre es obligatorio.');
      return;
    }
    this.savingFest.set(true);
    this.editErr.set('');
    this.api.editar(id, this.editForm).subscribe({
      next: () => {
        this.savingFest.set(false);
        this.showEdit.set(false);
        this.flash.set('Datos del festival actualizados.');
        this.cargar(id);
      },
      error: (e) => { this.savingFest.set(false); this.editErr.set(this.msg(e)); },
    });
  }

  nuevoDia(): void {
    this.editId.set(null);
    this.form = { fecha: this.festival()?.fecha_inicio ?? '', responsable: null };
    this.formError.set('');
    this.showDiaForm.set(true);
  }

  editarDia(d: FestivalDia): void {
    this.editId.set(d.id);
    this.form = {
      fecha: d.fecha, nombre: d.nombre ?? '', escenario_texto: d.escenario_texto ?? '',
      responsable: d.responsable, descripcion: d.descripcion ?? '',
    };
    this.formError.set('');
    this.showDiaForm.set(true);
  }

  cancelarDia(): void {
    this.showDiaForm.set(false);
    this.formError.set('');
  }

  guardarDia(festivalId: number): void {
    if (!this.form.fecha) { this.formError.set('La fecha del día es obligatoria.'); return; }
    this.saving.set(true);
    this.formError.set('');
    const editId = this.editId();
    const obs = editId
      ? this.api.editarDia(editId, this.form)
      : this.api.crearDia(festivalId, this.form);
    obs.subscribe({
      next: () => {
        this.saving.set(false);
        this.showDiaForm.set(false);
        this.notify(editId ? 'Día actualizado.' : 'Día agregado a la agenda.');
        this.cargar(festivalId);
      },
      error: (e) => { this.saving.set(false); this.formError.set(this.msg(e)); },
    });
  }

  eliminarDia(d: FestivalDia): void {
    const f = this.festival();
    if (!f) return;
    const aviso = d.actos.length
      ? `El día ${d.fecha} tiene ${d.actos.length} acto(s). Se eliminará el día y los actos quedarán sin día (no se borran). ¿Continuar?`
      : `¿Eliminar el día ${d.fecha}?`;
    if (!confirm(aviso)) return;
    this.api.eliminarDia(d.id).subscribe({
      next: () => { this.notify('Día eliminado.'); this.cargar(f.id); },
      error: (e) => this.error.set(this.msg(e)),
    });
  }

  asignarActo(e: FestivalEvento, ev: Event): void {
    const sel = ev.target as HTMLSelectElement;
    const diaId = sel.value ? Number(sel.value) : null;
    if (!diaId) return;
    const f = this.festival();
    if (!f) return;
    this.api.asignarActoDia(e.id, diaId).subscribe({
      next: () => { this.notify('Acto ubicado en la agenda.'); this.cargar(f.id); },
      error: (err) => this.error.set(this.msg(err)),
    });
  }

  sacarActo(e: FestivalEvento): void {
    const f = this.festival();
    if (!f) return;
    this.api.asignarActoDia(e.id, null).subscribe({
      next: () => { this.notify('Acto retirado del día.'); this.cargar(f.id); },
      error: (err) => this.error.set(this.msg(err)),
    });
  }

  togglePublicar(f: FestivalDetalle): void {
    const accion = f.publicado ? 'despublicar' : 'publicar';
    if (!confirm(`¿Seguro que deseas ${accion} la ficha pública de "${f.nombre}"?`)) return;
    this.api.publicar(f.id, !f.publicado).subscribe({
      next: (r) => {
        this.notify(r.publicado ? 'Ficha pública publicada.' : 'Ficha despublicada.');
        this.cargar(f.id);
      },
      error: (e) => this.error.set(this.msg(e)),
    });
  }

  editarAforo(e: FestivalEvento): void {
    const f = this.festival();
    if (!f) return;
    const actual = e.aforo_proyectado != null ? String(e.aforo_proyectado) : '';
    const v = prompt(`Aforo proyectado de "${e.nombre || 'acto'}" (vacío = sin meta):`, actual);
    if (v === null) return;
    const valor = v.trim() === '' ? null : Math.max(0, Number(v));
    if (valor !== null && isNaN(valor)) { this.error.set('Valor inválido.'); return; }
    this.api.setAforoProyectado(e.id, valor).subscribe({
      next: () => { this.notify('Meta de aforo actualizada.'); this.cargar(f.id); },
      error: (err) => this.error.set(this.msg(err)),
    });
  }

  private notify(m: string): void {
    this.flash.set(m);
    setTimeout(() => this.flash.set(''), 3000);
  }

  private msg(e: { error?: { detail?: string }; status?: number; message?: string }): string {
    if (e?.error?.detail) return e.error.detail;
    if (typeof e?.error === 'object' && e?.error) {
      const first = Object.values(e.error)[0];
      if (Array.isArray(first)) return String(first[0]);
      if (typeof first === 'string') return first;
    }
    if (e?.status === 404) return 'Festival no encontrado.';
    if (e?.status === 401 || e?.status === 403) return 'No tienes permiso para ver festivales.';
    return e?.message || 'Error inesperado.';
  }
}
