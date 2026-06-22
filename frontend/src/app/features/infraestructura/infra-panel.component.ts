import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { formatMoneda } from '../../shared/format/format.util';
import { ToastService } from '../../shared/ui/toast.service';
import { InfraestructuraApi } from './infraestructura.api';
import {
  CategoriaInfra,
  CategoriaOpcion,
  ContratoInfraInput,
  ContratoInfraLite,
  InfraCatalogos,
  InfraTiles,
} from './infraestructura.types';

/**
 * Panel principal de Infraestructura: tiles agregados + tabla de contratos de
 * obra (vías / parques / interventoría) con badge de categoría y barra de
 * ejecución. Botón "Nuevo contrato" (modal) y acceso a Insights. Cada fila
 * navega al detalle data-driven por categoría.
 */
@Component({
  standalone: true,
  selector: 'app-infra-panel',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <div>
          <h1><i class="fa fa-road" aria-hidden="true"></i> Infraestructura</h1>
          <p class="page__sub">
            Contratos de obra de Kennedy: vías y parques.
            Lo que registres aquí <strong>aparece automáticamente en el Mapa Kennedy</strong>.
          </p>
        </div>
        <div class="page__actions">
          <a routerLink="/infraestructura/insights" class="ui-btn ui-btn--outline ui-btn--sm">
            <i class="fa fa-chart-line"></i> Insights
          </a>
          <button class="ui-btn ui-btn--primary" (click)="nuevo()">
            <i class="fa fa-plus"></i> Nuevo contrato
          </button>
        </div>
      </header>

      <!-- Tiles -->
      <section class="kpis">
        <div class="kpi">
          <span class="kpi__val">{{ tiles().n_contratos }}</span>
          <span class="kpi__lbl">Contratos</span>
        </div>
        <div class="kpi kpi--money">
          <span class="kpi__val">{{ moneda(tiles().valor_total) }}</span>
          <span class="kpi__lbl">Valor total</span>
        </div>
        <div class="kpi kpi--prog">
          <span class="kpi__val">{{ tiles().avance_global }}%</span>
          <span class="kpi__lbl">Avance global</span>
          <div class="bar"><div class="bar__fill" [style.width.%]="tiles().avance_global"></div></div>
        </div>
        <div class="kpi kpi--vias">
          <span class="kpi__val">{{ tiles().n_tramos }}</span>
          <span class="kpi__lbl">Tramos viales</span>
        </div>
        <div class="kpi kpi--parq">
          <span class="kpi__val">{{ tiles().n_parques }}</span>
          <span class="kpi__lbl">Parques</span>
        </div>
      </section>

      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando…</div> }
      @if (error()) { <div class="ui-info-bar ui-info-bar--danger">{{ error() }}</div> }

      <!-- Tabla de contratos -->
      @if (!loading() && contratos().length > 0) {
        <section class="tabla-wrap">
          <table class="tabla">
            <thead>
              <tr>
                <th>Contrato</th>
                <th>Categoría</th>
                <th>Objeto</th>
                <th>Proyecto</th>
                <th class="num">Valor</th>
                <th class="ejc">% Ejecución</th>
                <th class="num">Capturas</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              @for (c of contratos(); track c.id) {
                <tr role="button" tabindex="0"
                    [attr.aria-label]="'Ver detalle del contrato ' + c.numero"
                    (click)="abrir(c)" (keyup.enter)="abrir(c)">
                  <td><strong>{{ c.numero }}</strong></td>
                  <td>
                    <span class="badge badge--{{ c.categoria }}">{{ catLabel(c.categoria) }}</span>
                  </td>
                  <td class="objeto" [title]="c.objeto || ''">{{ c.objeto || '—' }}</td>
                  <td>
                    @if (c.proyecto_codigo) {
                      <span class="proj">{{ c.proyecto_codigo }}</span>
                    } @else { — }
                  </td>
                  <td class="num">{{ moneda(c.valor) }}</td>
                  <td class="ejc">
                    <div class="ejc__bar">
                      <div class="ejc__fill" [class]="ejecClase(c.ejecucion)"
                           [style.width.%]="c.ejecucion || 0"></div>
                    </div>
                    <span class="ejc__num">{{ c.ejecucion || 0 }}%</span>
                  </td>
                  <td class="num caps">
                    @if (c.categoria === 'VIAS') {
                      <span title="Tramos viales"><i class="fa fa-road"></i> {{ c.n_tramos }}</span>
                    } @else if (c.categoria === 'PARQUES') {
                      <span title="Parques"><i class="fa fa-tree"></i> {{ c.n_parques }}</span>
                    } @else { — }
                  </td>
                  <td class="go"><i class="fa fa-chevron-right"></i></td>
                </tr>
              }
            </tbody>
          </table>
        </section>
      }

      @if (!loading() && contratos().length === 0 && !error()) {
        <div class="ui-empty-state">
          <i class="fa fa-road"></i>
          <p>Aún no hay contratos de infraestructura. Crea el primero con "Nuevo contrato".</p>
        </div>
      }
    </div>

    <!-- Modal: nuevo contrato -->
    @if (form()) {
      <div class="modal" (click)="cerrar()">
        <div class="modal__box" (click)="$event.stopPropagation()">
          <h2><i class="fa fa-file-contract"></i> Nuevo contrato de obra</h2>
          @if (formError()) { <div class="ui-info-bar ui-info-bar--danger">{{ formError() }}</div> }

          <label>Número de contrato *
            <input class="ui-input" [(ngModel)]="form()!.numero"
                   placeholder="Ej: CIA-807-2025">
            <small class="hint">Formato TIPO-NÚMERO-AÑO (p. ej. <b>CIA-807-2025</b>).</small>
          </label>

          <label>Categoría *
            <select class="ui-input" [(ngModel)]="form()!.categoria">
              <option value="" disabled>— seleccione —</option>
              @for (cat of categorias(); track cat.codigo) {
                <option [ngValue]="cat.codigo">{{ cat.label }}</option>
              }
            </select>
            <small class="hint">
              Define qué se captura: <b>Vías</b> → tramos por CIV ·
              <b>Parques</b> → parques del catálogo ·
              <b>Interventoría</b> → solo seguimiento.
            </small>
          </label>

          <label>Proyecto (cadena presupuestal)
            <select class="ui-input" [(ngModel)]="form()!.proyecto_id">
              <option [ngValue]="null">— sin proyecto —</option>
              @for (p of catalogos()?.proyectos || []; track p.id) {
                <option [ngValue]="p.id">{{ p.codigo }} · {{ p.nombre }}</option>
              }
            </select>
          </label>

          <label>Objeto del contrato
            <textarea class="ui-input" rows="2" [(ngModel)]="form()!.objeto"
                      placeholder="Ej: Rehabilitación de la malla vial local en la UPL Patio Bonito"></textarea>
          </label>

          <div class="row">
            <label>Valor del contrato ($)
              <input type="number" min="0" class="ui-input" [(ngModel)]="form()!.valor"
                     placeholder="Ej: 1500000000">
            </label>
            <label>% Ejecución inicial
              <input type="number" min="0" max="100" class="ui-input" [(ngModel)]="form()!.ejecucion"
                     placeholder="0">
            </label>
          </div>

          <div class="row">
            <label>Fecha de inicio<input type="date" class="ui-input" [(ngModel)]="form()!.fecha_inicio"></label>
            <label>Fecha de fin<input type="date" class="ui-input" [(ngModel)]="form()!.fecha_fin"></label>
          </div>

          <div class="row">
            <label>Contrato de interventoría
              <input class="ui-input" [(ngModel)]="form()!.interventoria_contrato"
                     placeholder="Ej: CIN-810-2025">
            </label>
            <label>Valor interventoría ($)
              <input type="number" min="0" class="ui-input" [(ngModel)]="form()!.interventoria_valor"
                     placeholder="Ej: 120000000">
            </label>
          </div>

          <div class="modal__acc">
            <button class="ui-btn ui-btn--ghost" (click)="cerrar()">Cancelar</button>
            <button class="ui-btn ui-btn--primary" (click)="guardar()" [disabled]="saving()">
              {{ saving() ? 'Guardando…' : 'Crear contrato' }}
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
    .page__sub { color: $color-text-muted; margin: $space-1 0 $space-3; max-width: 720px; }
    .page__actions { display: flex; gap: $space-2; align-items: center; }

    .kpis { display: grid; grid-template-columns: repeat(5, 1fr); gap: $space-3; margin-bottom: $space-4; }
    @media (max-width: 900px) { .kpis { grid-template-columns: repeat(3, 1fr); } }
    @media (max-width: 560px) { .kpis { grid-template-columns: 1fr 1fr; } }
    .kpi { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-3; display: flex; flex-direction: column; border-left: 4px solid $color-primary; }
    .kpi--money { border-left-color: #16A34A; }
    .kpi--prog { border-left-color: #8B5CF6; }
    .kpi--vias { border-left-color: #2563eb; }
    .kpi--parq { border-left-color: #0D9488; }
    .kpi__val { font-size: 1.5rem; font-weight: 700; color: $color-primary; line-height: 1.1; }
    .kpi__lbl { color: $color-text-muted; font-size: $font-size-sm; }
    .bar { height: 8px; background: #eee; border-radius: 99px; margin-top: $space-2; overflow: hidden; }
    .bar__fill { height: 100%; background: linear-gradient(90deg, #8B5CF6, #6366F1); transition: width .4s; }

    .tabla-wrap { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; overflow: auto; }
    .tabla { width: 100%; border-collapse: collapse; font-size: $font-size-sm; }
    .tabla thead th { text-align: left; padding: $space-3; color: $color-text-muted; font-weight: 600; border-bottom: 2px solid $color-border; white-space: nowrap; }
    .tabla th.num, .tabla td.num { text-align: right; }
    .tabla th.ejc { width: 160px; }
    .tabla tbody tr { cursor: pointer; transition: background .12s; }
    .tabla tbody tr:hover { background: #F9FAFB; }
    .tabla tbody tr:focus-visible { outline: 2px solid $color-primary; outline-offset: -2px; }
    .tabla td { padding: $space-3; border-bottom: 1px solid $color-border; vertical-align: middle; }
    .objeto { max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: $color-text-muted; }
    .proj { background: #EEF2FF; color: #4338CA; border-radius: 6px; padding: 2px 8px; font-weight: 600; }
    .caps i { margin-right: 3px; color: $color-text-muted; }
    .go { color: $color-text-muted; text-align: right; }

    .badge { border-radius: 99px; padding: 3px 12px; font-size: .72rem; font-weight: 600; white-space: nowrap; }
    .badge--VIAS { background: #DBEAFE; color: #1E40AF; }
    .badge--PARQUES { background: #CCFBF1; color: #0F766E; }
    .badge--INTERVENTORIA { background: #FEF3C7; color: #92400E; }

    .ejc { display: flex; align-items: center; gap: $space-2; }
    .ejc__bar { flex: 1; height: 8px; background: #eee; border-radius: 99px; overflow: hidden; min-width: 60px; }
    .ejc__fill { height: 100%; transition: width .4s; }
    .ejc__fill.ok { background: #16A34A; }
    .ejc__fill.warn { background: #F59E0B; }
    .ejc__fill.low { background: #DC2626; }
    .ejc__num { width: 40px; text-align: right; font-variant-numeric: tabular-nums; }

    .hint { color: $color-text-muted; font-size: .72rem; font-weight: 400; margin-top: 2px; }
    .modal { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; padding: $space-3; z-index: 1000; }
    .modal__box { background: #fff; border-radius: $radius-lg; padding: $space-4; width: 100%; max-width: 580px; max-height: 90vh; overflow: auto; display: flex; flex-direction: column; gap: $space-2; }
    .modal__box h2 { margin: 0 0 $space-2; color: $color-primary; }
    .modal__box h2 i { margin-right: $space-2; }
    .modal__box label { display: flex; flex-direction: column; font-size: $font-size-sm; color: $color-text; gap: 4px; }
    .modal__box .row { display: grid; grid-template-columns: 1fr 1fr; gap: $space-2; }
    @media (max-width: 600px) { .modal__box .row { grid-template-columns: 1fr; } }
    .modal__acc { display: flex; justify-content: flex-end; gap: $space-2; margin-top: $space-2; }
  `],
})
export class InfraPanelComponent implements OnInit {
  private api = inject(InfraestructuraApi);
  private layout = inject(LayoutService);
  private router = inject(Router);
  private toast = inject(ToastService);

  loading = signal(false);
  error = signal('');
  contratos = signal<ContratoInfraLite[]>([]);
  tiles = signal<InfraTiles>({ n_contratos: 0, valor_total: 0, avance_global: 0, n_tramos: 0, n_parques: 0 });
  catalogos = signal<InfraCatalogos | null>(null);

  form = signal<ContratoInfraInput | null>(null);
  formError = signal('');
  saving = signal(false);

  categorias = computed<CategoriaOpcion[]>(() => this.catalogos()?.categorias ?? []);

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Infraestructura' },
    ]);
    this.cargarCatalogos();
    this.cargar();
  }

  moneda(v: unknown): string { return formatMoneda(v); }

  catLabel(cod: CategoriaInfra): string {
    return this.categorias().find((c) => c.codigo === cod)?.label ?? cod;
  }

  ejecClase(ejec: number | null): string {
    const e = ejec || 0;
    return e >= 80 ? 'ok' : e >= 50 ? 'warn' : 'low';
  }

  private cargarCatalogos(): void {
    this.api.catalogos().subscribe({ next: (c) => this.catalogos.set(c) });
  }

  cargar(): void {
    this.loading.set(true);
    this.error.set('');
    this.api.panel().subscribe({
      next: (p) => { this.tiles.set(p.tiles); this.contratos.set(p.contratos); this.loading.set(false); },
      error: (e) => { this.loading.set(false); this.error.set(this.msg(e)); },
    });
  }

  abrir(c: ContratoInfraLite): void {
    this.router.navigate(['/infraestructura', c.id]);
  }

  nuevo(): void {
    this.formError.set('');
    this.form.set({
      numero: '', categoria: '', proyecto_id: null, objeto: '',
      valor: null, fecha_inicio: null, fecha_fin: null, ejecucion: 0,
      interventoria_contrato: null, interventoria_valor: null,
    });
  }

  cerrar(): void { this.form.set(null); }

  guardar(): void {
    const data = this.form();
    if (!data) return;
    if (!data.numero?.trim() || !data.numero.includes('-')) {
      this.formError.set('El número de contrato es obligatorio (formato TIPO-NÚMERO-AÑO).');
      return;
    }
    if (!data.categoria) { this.formError.set('Selecciona una categoría.'); return; }
    this.saving.set(true);
    this.formError.set('');
    this.api.crearContrato(data).subscribe({
      next: (r) => {
        this.saving.set(false);
        this.toast.success('Contrato creado correctamente ✓');
        this.cerrar();
        this.router.navigate(['/infraestructura', r.id]);
      },
      error: (e) => { this.saving.set(false); this.formError.set(this.msg(e)); },
    });
  }

  private msg(e: { error?: { detail?: string }; status?: number; message?: string }): string {
    const b = e?.error;
    if (b?.detail) return b.detail;
    if (e?.status === 401 || e?.status === 403) return 'No tienes permiso para gestionar infraestructura.';
    return e?.message || 'Error inesperado.';
  }
}
