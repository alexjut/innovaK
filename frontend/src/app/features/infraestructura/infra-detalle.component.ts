import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { formatMoneda } from '../../shared/format/format.util';
import { ConfirmService } from '../../shared/ui/confirm.service';
import { ToastService } from '../../shared/ui/toast.service';
import { InfraestructuraApi } from './infraestructura.api';
import {
  ContratoInfraDetalle,
  EstadoAvance,
  InfraCatalogos,
  ParqueCatalogo,
  ParqueInput,
  ParqueIntervencion,
  TramoInput,
  TramoVial,
} from './infraestructura.types';

const ESTADO_LBL: Record<EstadoAvance, string> = {
  sin_iniciar: 'Sin iniciar', parcial: 'En ejecución', terminado: 'Terminado',
};

/**
 * Detalle de un contrato de infraestructura. DATA-DRIVEN por categoría:
 *  - VIAS  → tabla de tramos (eje/desde/hasta/CIV/valor/avance), edición inline
 *            del % avance, estado geo, y form "Agregar vía" (geometría auto).
 *  - PARQUES → tabla de parques con selector de catálogo (554) que autocompleta
 *            nombre + dirección, edición inline del % avance.
 *  - INTERVENTORIA → solo nota de seguimiento (no captura geo).
 * Tras agregar algo se sugiere refrescar la capa del Mapa Kennedy.
 */
@Component({
  standalone: true,
  selector: 'app-infra-detalle',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando contrato…</div> }
      @if (!loading() && error()) {
        <div class="ui-info-bar ui-info-bar--danger"><strong>Error:</strong> {{ error() }}</div>
        <a routerLink="/infraestructura" class="ui-btn ui-btn--ghost"><i class="fa fa-arrow-left"></i> Volver</a>
      }

      @if (!loading() && !error() && contrato(); as c) {
        <header class="page__header">
          <div>
            <h1><i class="fa fa-file-contract" aria-hidden="true"></i> {{ c.numero }}</h1>
            <p class="page__sub">
              <span class="badge badge--{{ c.categoria }}">{{ catLabel(c.categoria) }}</span>
              @if (c.proyecto_codigo) {
                <a [routerLink]="['/presupuesto/proyectos']" class="chip chip--link">
                  <i class="fa fa-coins"></i> {{ c.proyecto_codigo }}
                </a>
              }
            </p>
          </div>
          <div class="actions">
            <a routerLink="/infraestructura" class="ui-btn ui-btn--ghost ui-btn--sm">
              <i class="fa fa-arrow-left"></i> Listado
            </a>
            <a routerLink="/mapa" class="ui-btn ui-btn--ghost ui-btn--sm">
              <i class="fa fa-map-marked-alt"></i> Ver en el Mapa Kennedy
            </a>
          </div>
        </header>

        <!-- Cabecera del contrato -->
        <section class="cab">
          <dl>
            <div><dt>Objeto</dt><dd>{{ c.objeto || '—' }}</dd></div>
            <div><dt>Proyecto</dt><dd>{{ c.proyecto_nombre || '—' }}</dd></div>
            <div><dt>Valor</dt><dd>{{ moneda(c.valor) }}</dd></div>
            <div><dt>Vigencia</dt><dd>{{ c.fecha_inicio || '—' }} → {{ c.fecha_fin || '—' }}</dd></div>
            <div><dt>Interventoría</dt>
              <dd>
                {{ c.interventoria_contrato || '—' }}
                @if (c.interventoria_valor != null) { · {{ moneda(c.interventoria_valor) }} }
              </dd>
            </div>
            <div class="ejc-block"><dt>Ejecución</dt>
              <dd>
                <div class="ejc">
                  <div class="ejc__bar"><div class="ejc__fill" [class]="ejecClase(c.ejecucion)" [style.width.%]="c.ejecucion || 0"></div></div>
                  <b>{{ c.ejecucion || 0 }}%</b>
                </div>
              </dd>
            </div>
          </dl>
        </section>

        <!-- ── VIAS ──────────────────────────────────────────────── -->
        @if (c.categoria === 'VIAS') {
          <section class="block">
            <div class="block__head">
              <h2><i class="fa fa-road"></i> Tramos viales ({{ c.tramos.length }})</h2>
              <button class="ui-btn ui-btn--primary ui-btn--sm" (click)="abrirTramo()">
                <i class="fa fa-plus"></i> Agregar vía
              </button>
            </div>

            @if (c.tramos.length === 0) {
              <div class="ui-empty-state ui-empty-state--sm">
                <i class="fa fa-road"></i>
                <p>Este contrato aún no tiene tramos. Agrega una vía por su CIV; la geometría se ubica en el mapa automáticamente.</p>
              </div>
            } @else {
              <div class="tabla-wrap">
                <table class="tabla">
                  <thead>
                    <tr>
                      <th>Eje Vial</th><th>Desde</th><th>Hasta</th><th>CIV</th>
                      <th class="num">Valor Intervención</th>
                      <th class="avc">% Avance</th><th>Geo</th><th></th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (t of c.tramos; track t.id) {
                      <tr>
                        <td><strong>{{ t.eje_vial || '—' }}</strong></td>
                        <td>{{ t.desde || '—' }}</td>
                        <td>{{ t.hasta || '—' }}</td>
                        <td>{{ t.civ }}</td>
                        <td class="num">{{ moneda(t.valor_intervencion) }}</td>
                        <td class="avc">
                          <div class="inline-edit">
                            <input type="number" min="0" max="100" class="ui-input ui-input--sm"
                                   [ngModel]="t.pct_avance"
                                   (ngModelChange)="setTramoAvance(t, $event)"
                                   (blur)="guardarTramoAvance(t)"
                                   (keyup.enter)="guardarTramoAvance(t)">
                            <span class="badge badge--{{ t.estado }}">{{ estadoLbl(t.estado) }}</span>
                          </div>
                        </td>
                        <td>
                          @if (t.geo_status === 'OK') {
                            <span class="geo geo--ok" title="Ubicado en el mapa"><i class="fa fa-map-pin"></i> en mapa</span>
                          } @else {
                            <span class="geo geo--no" title="Sin geometría resuelta"><i class="fa fa-triangle-exclamation"></i> sin geo</span>
                          }
                        </td>
                        <td class="acc">
                          <button class="ui-btn ui-btn--ghost ui-btn--sm danger" (click)="eliminarTramo(t)"
                                  [disabled]="eliminando() === 't' + t.id" title="Quitar tramo">
                            @if (eliminando() === 't' + t.id) { <i class="fa fa-spinner fa-spin"></i> }
                            @else { <i class="fa fa-trash"></i> }
                          </button>
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            }
          </section>
        }

        <!-- ── PARQUES ───────────────────────────────────────────── -->
        @else if (c.categoria === 'PARQUES') {
          <section class="block">
            <div class="block__head">
              <h2><i class="fa fa-tree"></i> Parques intervenidos ({{ c.parques.length }})</h2>
              <button class="ui-btn ui-btn--primary ui-btn--sm" (click)="abrirParque()">
                <i class="fa fa-plus"></i> Agregar parque
              </button>
            </div>

            @if (c.parques.length === 0) {
              <div class="ui-empty-state ui-empty-state--sm">
                <i class="fa fa-tree"></i>
                <p>Este contrato aún no tiene parques. Vincula uno del catálogo; ya trae su ubicación para el mapa.</p>
              </div>
            } @else {
              <div class="tabla-wrap">
                <table class="tabla">
                  <thead>
                    <tr><th>Código Parque</th><th>Nombre</th><th>Dirección</th><th class="avc">% Avance</th><th></th></tr>
                  </thead>
                  <tbody>
                    @for (p of c.parques; track p.id) {
                      <tr>
                        <td><strong>{{ p.codigo_parque ?? '—' }}</strong></td>
                        <td>{{ p.nombre || '—' }}</td>
                        <td class="dir">{{ p.direccion || '—' }}</td>
                        <td class="avc">
                          <div class="inline-edit">
                            <input type="number" min="0" max="100" class="ui-input ui-input--sm"
                                   [ngModel]="p.pct_avance"
                                   (ngModelChange)="setParqueAvance(p, $event)"
                                   (blur)="guardarParqueAvance(p)"
                                   (keyup.enter)="guardarParqueAvance(p)">
                            <span class="badge badge--{{ p.estado }}">{{ estadoLbl(p.estado) }}</span>
                          </div>
                        </td>
                        <td class="acc">
                          <button class="ui-btn ui-btn--ghost ui-btn--sm danger" (click)="eliminarParque(p)"
                                  [disabled]="eliminando() === 'p' + p.id" title="Quitar parque">
                            @if (eliminando() === 'p' + p.id) { <i class="fa fa-spinner fa-spin"></i> }
                            @else { <i class="fa fa-trash"></i> }
                          </button>
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            }
          </section>
        }

        <!-- ── INTERVENTORIA ─────────────────────────────────────── -->
        @else {
          <section class="block">
            <div class="ui-info-bar ui-info-bar--info">
              <i class="fa fa-clipboard-check"></i>
              Contrato de interventoría: hace seguimiento, no registra vías ni parques.
            </div>
          </section>
        }
      }
    </div>

    <!-- Modal: agregar vía -->
    @if (tramoForm()) {
      <div class="modal" (click)="cerrarTramo()">
        <div class="modal__box" (click)="$event.stopPropagation()">
          <h2><i class="fa fa-road"></i> Agregar vía (tramo)</h2>
          <p class="modal__hint">El sistema ubica la vía en el mapa automáticamente usando el CIV.</p>
          @if (tramoError()) { <div class="ui-info-bar ui-info-bar--danger">{{ tramoError() }}</div> }

          <label>Valor Intervención ($)
            <input type="number" min="0" class="ui-input" [(ngModel)]="tramoForm()!.valor_intervencion"
                   placeholder="Ej: 85000000">
          </label>
          <div class="row">
            <label>CIV *
              <input type="number" class="ui-input" [(ngModel)]="tramoForm()!.civ" placeholder="Ej: 8004567">
              <small class="hint">Código de Identificación Vial (malla vial de Bogotá).</small>
            </label>
            <label>PK ID
              <input type="number" class="ui-input" [(ngModel)]="tramoForm()!.pk_id" placeholder="Opcional">
            </label>
          </div>
          <label>Eje Vial
            <input class="ui-input" [(ngModel)]="tramoForm()!.eje_vial" placeholder="Ej: Carrera 80">
          </label>
          <div class="row">
            <label>Desde<input class="ui-input" [(ngModel)]="tramoForm()!.desde" placeholder="Ej: Calle 38 Sur"></label>
            <label>Hasta<input class="ui-input" [(ngModel)]="tramoForm()!.hasta" placeholder="Ej: Calle 42 Sur"></label>
          </div>
          <label>% Avance Intervención
            <input type="number" min="0" max="100" class="ui-input" [(ngModel)]="tramoForm()!.pct_avance" placeholder="0">
          </label>

          <div class="modal__acc">
            <button class="ui-btn ui-btn--ghost" (click)="cerrarTramo()">Cancelar</button>
            <button class="ui-btn ui-btn--primary" (click)="guardarTramo()" [disabled]="saving()">
              {{ saving() ? 'Guardando…' : 'Agregar vía' }}
            </button>
          </div>
        </div>
      </div>
    }

    <!-- Modal: agregar parque -->
    @if (parqueForm()) {
      <div class="modal" (click)="cerrarParque()">
        <div class="modal__box" (click)="$event.stopPropagation()">
          <h2><i class="fa fa-tree"></i> Agregar parque</h2>
          <p class="modal__hint">El parque ya trae su ubicación; aparecerá en el mapa al guardar.</p>
          @if (parqueError()) { <div class="ui-info-bar ui-info-bar--danger">{{ parqueError() }}</div> }

          <label>Código Parque *
            <input class="ui-input" [(ngModel)]="busquedaParque" (ngModelChange)="filtrarParques($event)"
                   placeholder="Busca por código o nombre… (ej. 08-001 o Cayetano)">
          </label>
          @if (busquedaParque && parquesFiltrados().length > 0) {
            <ul class="picker">
              @for (p of parquesFiltrados(); track p.id) {
                <li class="picker__opt" [class.picker__opt--on]="parqueForm()!.parque_id === p.id"
                    role="button" tabindex="0"
                    (click)="elegirParque(p)" (keyup.enter)="elegirParque(p)">
                  <strong>{{ p.codigo_parque }}</strong> · {{ p.nombre }}
                </li>
              }
            </ul>
          } @else if (busquedaParque && parqueForm()!.parque_id === null) {
            <small class="hint">Sin coincidencias. Escribe parte del código o nombre del parque.</small>
          }

          <label>Nombre del parque
            <input class="ui-input" [ngModel]="parqueNombre()" readonly placeholder="Se autocompleta al elegir">
          </label>
          <label>Dirección
            <input class="ui-input" [(ngModel)]="parqueForm()!.direccion" placeholder="Ej: Calle 40 Sur # 79-20">
          </label>
          <label>% Avance Intervención
            <input type="number" min="0" max="100" class="ui-input" [(ngModel)]="parqueForm()!.pct_avance" placeholder="0">
          </label>

          <div class="modal__acc">
            <button class="ui-btn ui-btn--ghost" (click)="cerrarParque()">Cancelar</button>
            <button class="ui-btn ui-btn--primary" (click)="guardarParque()" [disabled]="saving()">
              {{ saving() ? 'Guardando…' : 'Vincular parque' }}
            </button>
          </div>
        </div>
      </div>
    }
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1200px; margin: 0 auto; padding-bottom: $space-6; }
    .page__header { display: flex; justify-content: space-between; align-items: flex-start; gap: $space-3; flex-wrap: wrap; }
    .page__header h1 { margin: 0; color: $color-primary; }
    .page__header h1 i { margin-right: $space-2; }
    .page__sub { margin: $space-1 0 $space-3; display: flex; gap: $space-2; align-items: center; flex-wrap: wrap; }
    .actions { display: flex; gap: $space-2; flex-wrap: wrap; }
    .chip { background: #F3F4F6; color: #374151; border-radius: 99px; padding: 3px 12px; font-size: .75rem; }
    .chip--link { text-decoration: none; background: #EEF2FF; color: #4338CA; font-weight: 600; }

    .cab { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-4; margin-bottom: $space-4; }
    .cab dl { display: grid; grid-template-columns: repeat(3, 1fr); gap: $space-3; margin: 0; }
    @media (max-width: 760px) { .cab dl { grid-template-columns: 1fr 1fr; } }
    @media (max-width: 480px) { .cab dl { grid-template-columns: 1fr; } }
    .cab dt { font-size: $font-size-xs; color: $color-text-muted; text-transform: uppercase; letter-spacing: .03em; margin-bottom: 2px; }
    .cab dd { margin: 0; color: $color-text; font-weight: 600; }
    .ejc-block dd { font-weight: 400; }

    .block { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-4; margin-bottom: $space-4; }
    .block__head { display: flex; justify-content: space-between; align-items: center; gap: $space-3; margin-bottom: $space-3; flex-wrap: wrap; }
    .block__head h2 { margin: 0; color: $color-primary; font-size: 1.05rem; }
    .block__head h2 i { margin-right: $space-2; }

    .tabla-wrap { overflow: auto; border: 1px solid $color-border; border-radius: $radius-md; }
    .tabla { width: 100%; border-collapse: collapse; font-size: $font-size-sm; }
    .tabla thead th { text-align: left; padding: $space-2 $space-3; color: $color-text-muted; font-weight: 600; border-bottom: 2px solid $color-border; white-space: nowrap; background: #F9FAFB; }
    .tabla th.num, .tabla td.num { text-align: right; }
    .tabla th.avc { width: 200px; }
    .tabla td { padding: $space-2 $space-3; border-bottom: 1px solid $color-border; vertical-align: middle; }
    .tabla tbody tr:last-child td { border-bottom: none; }
    .dir { color: $color-text-muted; max-width: 220px; }
    .acc { text-align: right; }
    .danger { color: #DC2626; }

    .inline-edit { display: flex; align-items: center; gap: $space-2; }
    .ui-input--sm { width: 70px; padding: 4px 8px; }

    .ejc { display: flex; align-items: center; gap: $space-2; }
    .ejc__bar { flex: 1; height: 8px; background: #eee; border-radius: 99px; overflow: hidden; min-width: 80px; max-width: 220px; }
    .ejc__fill { height: 100%; transition: width .4s; }
    .ejc__fill.ok { background: #16A34A; } .ejc__fill.warn { background: #F59E0B; } .ejc__fill.low { background: #DC2626; }

    .geo { font-size: .72rem; font-weight: 600; white-space: nowrap; }
    .geo--ok { color: #15803D; } .geo--no { color: #B45309; }
    .geo i { margin-right: 3px; }

    .badge { border-radius: 99px; padding: 3px 10px; font-size: .7rem; font-weight: 600; white-space: nowrap; }
    .badge--VIAS { background: #DBEAFE; color: #1E40AF; }
    .badge--PARQUES { background: #CCFBF1; color: #0F766E; }
    .badge--INTERVENTORIA { background: #FEF3C7; color: #92400E; }
    .badge--sin_iniciar { background: #FEE2E2; color: #991B1B; }
    .badge--parcial { background: #FEF3C7; color: #92400E; }
    .badge--terminado { background: #DCFCE7; color: #166534; }

    .hint { color: $color-text-muted; font-size: .72rem; font-weight: 400; margin-top: 2px; }
    .modal { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; padding: $space-3; z-index: 1000; }
    .modal__box { background: #fff; border-radius: $radius-lg; padding: $space-4; width: 100%; max-width: 540px; max-height: 90vh; overflow: auto; display: flex; flex-direction: column; gap: $space-2; }
    .modal__box h2 { margin: 0 0 4px; color: $color-primary; }
    .modal__box h2 i { margin-right: $space-2; }
    .modal__hint { color: $color-text-muted; font-size: $font-size-sm; margin: 0 0 $space-2; }
    .modal__box label { display: flex; flex-direction: column; font-size: $font-size-sm; color: $color-text; gap: 4px; }
    .modal__box .row { display: grid; grid-template-columns: 1fr 1fr; gap: $space-2; }
    @media (max-width: 600px) { .modal__box .row { grid-template-columns: 1fr; } }
    .modal__acc { display: flex; justify-content: flex-end; gap: $space-2; margin-top: $space-2; }

    .picker { list-style: none; margin: 0; padding: 0; max-height: 200px; overflow: auto; border: 1px solid $color-border; border-radius: $radius-md; }
    .picker__opt { padding: $space-2 $space-3; cursor: pointer; border-bottom: 1px solid $color-border; font-size: $font-size-sm; }
    .picker__opt:last-child { border-bottom: none; }
    .picker__opt:hover, .picker__opt--on { background: #EEF2FF; }
    .picker__opt:focus-visible { outline: 2px solid $color-primary; outline-offset: -2px; }
  `],
})
export class InfraDetalleComponent implements OnInit {
  private api = inject(InfraestructuraApi);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);
  private toast = inject(ToastService);
  private confirm = inject(ConfirmService);

  contratoId = 0;
  loading = signal(false);
  error = signal('');
  contrato = signal<ContratoInfraDetalle | null>(null);
  catalogos = signal<InfraCatalogos | null>(null);

  // Form: agregar tramo.
  tramoForm = signal<TramoInput | null>(null);
  tramoError = signal('');

  // Form: agregar parque (con selector de catálogo).
  parqueForm = signal<ParqueInput | null>(null);
  parqueError = signal('');
  busquedaParque = '';
  parquesFiltrados = signal<ParqueCatalogo[]>([]);
  private parqueElegido = signal<ParqueCatalogo | null>(null);
  parqueNombre = computed(() => this.parqueElegido()?.nombre ?? '');

  saving = signal(false);
  /** Marcador del borrado en curso: 't<id>' tramo o 'p<id>' parque. */
  eliminando = signal<string | null>(null);

  ngOnInit(): void {
    this.contratoId = Number(this.route.snapshot.paramMap.get('id'));
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Infraestructura', url: '/infraestructura' },
      { label: 'Contrato' },
    ]);
    this.api.catalogos().subscribe({ next: (c) => this.catalogos.set(c) });
    this.cargar();
  }

  moneda(v: unknown): string { return formatMoneda(v); }
  estadoLbl(e: EstadoAvance): string { return ESTADO_LBL[e] ?? e; }
  catLabel(cod: string): string {
    return this.catalogos()?.categorias.find((c) => c.codigo === cod)?.label ?? cod;
  }
  ejecClase(ejec: number | null): string {
    const e = ejec || 0;
    return e >= 80 ? 'ok' : e >= 50 ? 'warn' : 'low';
  }

  cargar(): void {
    this.loading.set(true);
    this.error.set('');
    this.api.detalle(this.contratoId).subscribe({
      next: (c) => { this.contrato.set(c); this.loading.set(false); },
      error: (e) => { this.loading.set(false); this.error.set(this.msg(e)); },
    });
  }

  // ── Tramos: edición inline del avance ──────────────────────────
  setTramoAvance(t: TramoVial, val: number): void {
    t.pct_avance = Math.max(0, Math.min(100, Number(val) || 0));
  }

  guardarTramoAvance(t: TramoVial): void {
    this.api.actualizarTramo(t.id, t.pct_avance).subscribe({
      next: (r) => {
        this.aplicarEjecucion(r.ejecucion_contrato);
        this.cargar();
      },
      error: (e) => this.toast.error(this.msg(e)),
    });
  }

  async eliminarTramo(t: TramoVial): Promise<void> {
    if (this.eliminando()) return;
    const ok = await this.confirm.ask({
      title: 'Quitar tramo', danger: true, confirmText: 'Quitar',
      message: `¿Quitar el tramo CIV ${t.civ}? Saldrá del mapa.`,
    });
    if (!ok) return;
    this.eliminando.set('t' + t.id);
    this.api.quitarTramo(t.id).subscribe({
      next: () => { this.eliminando.set(null); this.toast.success('Tramo quitado ✓'); this.cargar(); },
      error: (e) => { this.eliminando.set(null); this.toast.error(this.msg(e)); },
    });
  }

  // ── Parques: edición inline del avance ─────────────────────────
  setParqueAvance(p: ParqueIntervencion, val: number): void {
    p.pct_avance = Math.max(0, Math.min(100, Number(val) || 0));
  }

  guardarParqueAvance(p: ParqueIntervencion): void {
    this.api.actualizarParque(p.id, p.pct_avance).subscribe({
      next: (r) => { this.aplicarEjecucion(r.ejecucion_contrato); this.cargar(); },
      error: (e) => this.toast.error(this.msg(e)),
    });
  }

  async eliminarParque(p: ParqueIntervencion): Promise<void> {
    if (this.eliminando()) return;
    const ok = await this.confirm.ask({
      title: 'Quitar parque', danger: true, confirmText: 'Quitar',
      message: `¿Quitar el parque "${p.nombre || p.codigo_parque}" de este contrato?`,
    });
    if (!ok) return;
    this.eliminando.set('p' + p.id);
    this.api.quitarParque(p.id).subscribe({
      next: () => { this.eliminando.set(null); this.toast.success('Parque quitado ✓'); this.cargar(); },
      error: (e) => { this.eliminando.set(null); this.toast.error(this.msg(e)); },
    });
  }

  private aplicarEjecucion(ejec: number): void {
    this.contrato.update((c) => c ? { ...c, ejecucion: ejec } : c);
  }

  // ── Agregar tramo ──────────────────────────────────────────────
  abrirTramo(): void {
    this.tramoError.set('');
    this.tramoForm.set({
      valor_intervencion: null, civ: null, pk_id: null,
      eje_vial: null, desde: null, hasta: null, pct_avance: 0,
    });
  }
  cerrarTramo(): void { this.tramoForm.set(null); }

  guardarTramo(): void {
    const data = this.tramoForm();
    if (!data) return;
    if (!data.civ) { this.tramoError.set('El CIV es obligatorio.'); return; }
    this.saving.set(true);
    this.tramoError.set('');
    this.api.agregarTramo(this.contratoId, data).subscribe({
      next: (r) => {
        this.saving.set(false);
        this.cerrarTramo();
        if (r.en_mapa) {
          this.toast.success('Tramo agregado y ubicado en el mapa ✓ Refresca la capa del Mapa Kennedy.');
        } else {
          this.toast.info('Tramo agregado. La geometría no se resolvió aún (revisión).');
        }
        this.cargar();
      },
      error: (e) => { this.saving.set(false); this.tramoError.set(this.msg(e)); },
    });
  }

  // ── Agregar parque ─────────────────────────────────────────────
  abrirParque(): void {
    this.parqueError.set('');
    this.busquedaParque = '';
    this.parquesFiltrados.set([]);
    this.parqueElegido.set(null);
    this.parqueForm.set({ parque_id: null, direccion: null, pct_avance: 0 });
  }
  cerrarParque(): void { this.parqueForm.set(null); }

  filtrarParques(q: string): void {
    this.parqueForm.update((f) => f ? { ...f, parque_id: null } : f);
    this.parqueElegido.set(null);
    const term = (q || '').trim().toLowerCase();
    if (term.length < 2) { this.parquesFiltrados.set([]); return; }
    const todos = this.catalogos()?.parques ?? [];
    this.parquesFiltrados.set(
      todos.filter((p) =>
        String(p.codigo_parque).toLowerCase().includes(term)
        || (p.nombre || '').toLowerCase().includes(term),
      ).slice(0, 30),
    );
  }

  elegirParque(p: ParqueCatalogo): void {
    this.parqueElegido.set(p);
    this.busquedaParque = `${p.codigo_parque} · ${p.nombre}`;
    this.parquesFiltrados.set([]);
    this.parqueForm.update((f) => f ? { ...f, parque_id: p.id } : f);
  }

  guardarParque(): void {
    const data = this.parqueForm();
    if (!data) return;
    if (!data.parque_id) { this.parqueError.set('Selecciona un parque del catálogo.'); return; }
    this.saving.set(true);
    this.parqueError.set('');
    this.api.vincularParque(this.contratoId, data).subscribe({
      next: () => {
        this.saving.set(false);
        this.cerrarParque();
        this.toast.success('Parque vinculado ✓ Refresca la capa del Mapa Kennedy.');
        this.cargar();
      },
      error: (e) => { this.saving.set(false); this.parqueError.set(this.msg(e)); },
    });
  }

  private msg(e: { error?: { detail?: string }; status?: number; message?: string }): string {
    const b = e?.error;
    if (b?.detail) return b.detail;
    if (e?.status === 401 || e?.status === 403) return 'No tienes permiso para gestionar infraestructura.';
    return e?.message || 'Error inesperado.';
  }
}
