import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

/**
 * Detalle de entidad de presupuesto. Render rico para KPI (barra+avances),
 * CDP (saldos+contratos) y Contrato (vinculaciones). Otras entidades → kv plano.
 */
@Component({
  standalone: true,
  selector: 'app-presupuesto-detail',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando…</div> }
      @else if (errorMsg()) {
        <div class="ui-info-bar ui-info-bar--danger">{{ errorMsg() }}</div>
        <a [routerLink]="['/presupuesto', entidad()]" class="ui-btn ui-btn--ghost">↩ Volver</a>
      }
      @else if (data()) {
        @if (data(); as d) {
        <header class="page__header">
          <h1>
            <i class="fa" [class]="iconoDetalle()" aria-hidden="true"></i>
            {{ titulo(d) }}
          </h1>
          <a [routerLink]="['/presupuesto', entidad()]" class="ui-btn ui-btn--ghost ui-btn--sm">
            <i class="fa fa-arrow-left"></i> Listado
          </a>
        </header>

        @switch (entidad()) {
          @case ('indicadores') {
            <div class="tiles">
              <article class="tile"><span class="tile__v">{{ d.meta_magnitud | number }}</span><span class="tile__l">Meta</span></article>
              <article class="tile tile--ok"><span class="tile__v">{{ d.avance_acumulado | number }}</span><span class="tile__l">Avance acumulado</span></article>
              <article class="tile" [class]="pctClass(d.avance_pct)"><span class="tile__v">{{ d.avance_pct ?? 0 }}%</span><span class="tile__l">Cumplimiento</span></article>
            </div>
            <div class="bar"><div class="bar__fill" [style.width.%]="clamp(d.avance_pct)" [class]="pctClass(d.avance_pct)"></div></div>
            <article class="ui-card">
              <h2><i class="fa fa-gauge-high" aria-hidden="true"></i> Información del KPI</h2>
              <dl class="kv">
                <dt>Proyecto</dt><dd>{{ d.proyecto_codigo || '—' }}</dd>
                <dt>Meta</dt><dd>{{ d.meta_codigo }} — {{ d.meta_nombre || '' }}</dd>
                <dt>Unidad</dt><dd>{{ d.unidad_medida }}</dd>
                <dt>Agregación</dt><dd>{{ d.tipo_agregacion }}</dd>
                <dt>Descripción</dt><dd>{{ d.descripcion || '—' }}</dd>
              </dl>
            </article>
            <article class="ui-card">
              <h2><i class="fa fa-arrow-trend-up" aria-hidden="true"></i> Avances ({{ d.avances?.length || 0 }})</h2>
              @if (d.avances?.length) {
                <table class="tbl"><thead><tr><th>Fecha</th><th>Periodo</th><th class="num">Magnitud</th><th>Origen</th><th>Observación</th></tr></thead>
                  <tbody>@for (a of d.avances; track $index) {
                    <tr><td>{{ a.fecha_aporte || a.fecha }}</td><td>{{ a.periodo }}</td><td class="num">{{ a.magnitud_aportada | number }}</td>
                      <td><span class="ui-badge" [class]="origenBadge(a.origen)">{{ a.origen }}</span></td><td>{{ a.observaciones || '—' }}</td></tr>
                  }</tbody></table>
              } @else { <p class="muted">Sin avances registrados.</p> }
            </article>
          }
          @case ('cdps') {
            <div class="tiles">
              <article class="tile"><span class="tile__v">{{ d.valor | currency:'COP':'symbol-narrow':'1.0-0' }}</span><span class="tile__l">Valor CDP</span></article>
              <article class="tile tile--warn"><span class="tile__v">{{ d.saldo_comprometido | currency:'COP':'symbol-narrow':'1.0-0' }}</span><span class="tile__l">Comprometido</span></article>
              <article class="tile tile--ok"><span class="tile__v">{{ d.saldo_disponible | currency:'COP':'symbol-narrow':'1.0-0' }}</span><span class="tile__l">Saldo disponible</span></article>
            </div>
            <article class="ui-card">
              <h2><i class="fa fa-file-invoice-dollar" aria-hidden="true"></i> CDP {{ d.numero }}</h2>
              <dl class="kv">
                <dt>Proyecto</dt><dd>{{ d.proyecto_codigo || '—' }}</dd>
                <dt>Fecha</dt><dd>{{ d.fecha || '—' }}</dd>
                <dt>Descripción</dt><dd>{{ d.descripcion || d.objeto || '—' }}</dd>
              </dl>
            </article>
            <article class="ui-card">
              <h2><i class="fa fa-file-signature" aria-hidden="true"></i> Contratos ({{ d.contratos?.length || 0 }})</h2>
              @if (d.contratos?.length) {
                <table class="tbl"><thead><tr><th>Número</th><th class="num">Valor</th><th>Inicio</th><th>Fin</th></tr></thead>
                  <tbody>@for (ct of d.contratos; track $index) {
                    <tr><td>{{ ct.numero || ct.contrato_numero }}</td><td class="num">{{ ct.valor | currency:'COP':'symbol-narrow':'1.0-0' }}</td><td>{{ ct.fecha_inicio || '—' }}</td><td>{{ ct.fecha_fin || '—' }}</td></tr>
                  }</tbody></table>
              } @else { <p class="muted">Sin contratos en este CDP.</p> }
            </article>
          }
          @case ('contratos') {
            <div class="tiles">
              <article class="tile"><span class="tile__v">{{ d.valor | currency:'COP':'symbol-narrow':'1.0-0' }}</span><span class="tile__l">Valor contrato</span></article>
              <article class="tile tile--ok"><span class="tile__v">{{ d.saldo_vinculado | currency:'COP':'symbol-narrow':'1.0-0' }}</span><span class="tile__l">Vinculado a actividades</span></article>
            </div>
            <article class="ui-card">
              <h2><i class="fa fa-file-signature" aria-hidden="true"></i> Contrato {{ d.contrato_numero }}/{{ d.contrato_vigencia }}</h2>
              <dl class="kv">
                <dt>Tipo</dt><dd>{{ d.contrato_tipo }}</dd>
                <dt>CDP</dt><dd>{{ d.cdp_numero || '—' }}</dd>
                <dt>Objeto</dt><dd>{{ d.objeto || '—' }}</dd>
                <dt>Fechas</dt><dd>{{ d.fecha_inicio || '—' }} → {{ d.fecha_fin || '—' }}</dd>
              </dl>
            </article>
            <article class="ui-card">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <h2><i class="fa fa-calendar-check" aria-hidden="true"></i> Vinculaciones con actividades ({{ d.vinculaciones_actividad?.length || 0 }})</h2>
                <button class="ui-btn ui-btn--primary ui-btn--sm" (click)="abrirVinc(d)"><i class="fa fa-plus"></i> Vincular</button>
              </div>
              @if (vincAbierto()) {
                <div class="vinc-form">
                  <label><span>Proyecto</span>
                    <select [ngModel]="vincForm.proyecto_id" (ngModelChange)="onVincProyecto($event)">
                      <option [ngValue]="null">— elegir —</option>
                      @for (p of proyectos(); track p.id) { <option [ngValue]="p.id">{{ p.codigo }} — {{ p.nombre }}</option> }
                    </select></label>
                  <label><span>Actividad del plan</span>
                    <select [ngModel]="vincForm.actividad_plan_id" (ngModelChange)="vincForm.actividad_plan_id = $event">
                      <option [ngValue]="null">— elegir —</option>
                      @for (a of actividades(); track a.id) { <option [ngValue]="a.id">{{ a.nombre || a.descripcion }}</option> }
                    </select></label>
                  <label><span>Monto</span><input type="number" [ngModel]="vincForm.monto" (ngModelChange)="vincForm.monto = $event"></label>
                  <div class="vinc-acts">
                    <button class="ui-btn ui-btn--ghost ui-btn--sm" (click)="vincAbierto.set(false)">Cancelar</button>
                    <button class="ui-btn ui-btn--primary ui-btn--sm" [disabled]="!vincForm.actividad_plan_id" (click)="guardarVinc(d)">Guardar</button>
                  </div>
                  @if (vincMsg()) { <p class="muted">{{ vincMsg() }}</p> }
                </div>
              }
              @if (d.vinculaciones_actividad?.length) {
                <table class="tbl"><thead><tr><th>Actividad</th><th class="num">Monto</th></tr></thead>
                  <tbody>@for (v of d.vinculaciones_actividad; track $index) {
                    <tr><td>{{ v.actividad_descripcion || v.actividad_plan_id }}</td><td class="num">{{ v.monto | currency:'COP':'symbol-narrow':'1.0-0' }}</td></tr>
                  }</tbody></table>
              } @else { <p class="muted">Sin actividades vinculadas.</p> }
            </article>
          }
          @default {
            <article class="ui-card">
              <dl class="kv">@for (e of entries(d); track e[0]) { <dt>{{ formatKey(e[0]) }}</dt><dd>{{ formatValue(e[1]) }}</dd> }</dl>
            </article>
          }
        }
        }
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1100px; margin: 0 auto; }
    .page__header { display: flex; justify-content: space-between; align-items: flex-start; gap: $space-3; flex-wrap: wrap; margin-bottom: $space-4; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: $space-3; margin-bottom: $space-3; }
    .tile { background: #fff; border: 1px solid $color-border; border-left: 5px solid $color-primary; border-radius: $radius-md; padding: $space-3; display: flex; flex-direction: column;
      &--ok { border-left-color: #16a34a; } &--warn { border-left-color: #d97706; } &--rojo { border-left-color: #dc2626; } &--amar { border-left-color: #d97706; } &--verde { border-left-color: #16a34a; }
      &__v { font-size: 1.5rem; font-weight: 700; color: $color-text; line-height: 1; } &__l { font-size: $font-size-xs; color: $color-text-muted; text-transform: uppercase; } }
    .bar { height: 14px; background: $color-bg-muted; border-radius: $radius-pill; overflow: hidden; margin-bottom: $space-4; }
    .bar__fill { height: 100%; background: $color-primary; transition: width .6s ease;
      &.tile--verde, &.verde { background: #16a34a; } &.tile--amar, &.amar { background: #d97706; } &.tile--rojo, &.rojo { background: #dc2626; } }
    .ui-card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-4; margin-bottom: $space-4;
      h2 { margin: 0 0 $space-3; color: $color-primary; font-size: 1rem; } }
    .kv { display: grid; grid-template-columns: max-content 1fr; gap: $space-2 $space-4; margin: 0;
      dt { font-weight: 600; color: $color-text-muted; font-size: $font-size-sm; } dd { margin: 0; word-break: break-word; } }
    .tbl { width: 100%; border-collapse: collapse;
      th, td { padding: $space-2; border-bottom: 1px solid $color-border; text-align: left; font-size: $font-size-sm; }
      th { color: $color-text-muted; text-transform: uppercase; font-size: $font-size-xs; } .num { text-align: right; } }
    .muted { color: $color-text-muted; }
    .vinc-form { background: $color-bg-subtle; border: 1px solid $color-border; border-radius: $radius-md; padding: $space-3; margin: $space-2 0;
      display: grid; grid-template-columns: 1fr 1fr 120px; gap: $space-2; @media (max-width: 600px){ grid-template-columns: 1fr; }
      label { display: flex; flex-direction: column; span { font-size: $font-size-xs; color: $color-text-muted; }
        input, select { padding: 6px 8px; border: 1px solid $color-border; border-radius: $radius-sm; font: inherit; } }
      .vinc-acts { grid-column: 1 / -1; display: flex; gap: $space-2; justify-content: flex-end; } }
  `],
})
export class PresupuestoDetailComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);

  entidad = signal<string>('proyectos');
  loading = signal<boolean>(true);
  errorMsg = signal<string>('');
  data = signal<any | null>(null);

  // Vinculación contrato↔actividad-plan.
  vincAbierto = signal<boolean>(false);
  proyectos = signal<any[]>([]);
  actividades = signal<any[]>([]);
  vincMsg = signal<string>('');
  vincForm: any = { proyecto_id: null, actividad_plan_id: null, monto: 0 };

  abrirVinc(d: any): void {
    this.vincAbierto.set(!this.vincAbierto());
    this.vincMsg.set('');
    if (this.vincAbierto() && !this.proyectos().length) {
      this.http.get<any>(this.cfg.url('/presupuesto/api/proyectos/')).subscribe(r =>
        this.proyectos.set((r?.results || r || []).map((p: any) => ({ id: p.id, codigo: p.codigo, nombre: p.nombre }))));
    }
  }
  onVincProyecto(pid: number): void {
    this.vincForm.proyecto_id = pid;
    this.vincForm.actividad_plan_id = null;
    this.actividades.set([]);
    if (!pid) return;
    this.http.get<any>(this.cfg.url(`/presupuesto/api/plan-actividades-por-proyecto/${pid}/`))
      .subscribe(r => this.actividades.set(r?.items || r?.results || r || []));
  }
  guardarVinc(d: any): void {
    this.vincMsg.set('Guardando…');
    this.http.post(this.cfg.url('/presupuesto/api/vinculaciones/'),
      { contrato_id: d.id, actividad_plan_id: this.vincForm.actividad_plan_id, monto: this.vincForm.monto || 0 }).subscribe({
      next: () => {
        this.vincMsg.set('✓ Vinculada.');
        this.vincAbierto.set(false);
        this.vincForm = { proyecto_id: null, actividad_plan_id: null, monto: 0 };
        // recargar detalle
        this.http.get<any>(this.cfg.url(`/presupuesto/api/contratos/${d.id}/`)).subscribe(j => this.data.set(j));
      },
      error: e => this.vincMsg.set(e?.error?.detail || 'Error al vincular.'),
    });
  }

  private endpoints: Record<string, (id: string) => string> = {
    indicadores: id => `/presupuesto/api/indicadores/${id}/`,
    cdps: id => `/presupuesto/api/cdps/${id}/`,
    contratos: id => `/presupuesto/api/contratos/${id}/`,
  };

  ngOnInit(): void {
    this.route.paramMap.subscribe(pm => {
      const e = pm.get('entidad') || 'proyectos';
      const id = pm.get('id') || '';
      this.entidad.set(e);
      this.layout.setBreadcrumb([
        { label: 'Inicio', url: '/' },
        { label: 'Presupuesto', url: '/presupuesto' },
        { label: e, url: `/presupuesto/${e}` },
        { label: `#${id}` },
      ]);
      const builder = this.endpoints[e];
      if (!builder) { this.errorMsg.set('Detalle no disponible para esta entidad.'); this.loading.set(false); return; }
      this.loading.set(true);
      this.http.get<any>(this.cfg.url(builder(id))).subscribe({
        next: d => { this.data.set(d); this.loading.set(false); },
        error: err => { this.loading.set(false); this.errorMsg.set(err.status === 404 ? 'No encontrado.' : `Error ${err.status}.`); },
      });
    });
  }

  iconoDetalle(): string {
    const m: Record<string, string> = {
      indicadores: 'fa-gauge-high',
      cdps: 'fa-file-invoice-dollar',
      contratos: 'fa-file-signature',
    };
    return m[this.entidad()] || 'fa-table-list';
  }

  titulo(d: any): string {
    switch (this.entidad()) {
      case 'indicadores': return d.nombre || `KPI #${d.id}`;
      case 'cdps': return `CDP ${d.numero || d.id}`;
      case 'contratos': return `Contrato ${d.contrato_numero || d.id}`;
      default: return `#${d.id}`;
    }
  }
  clamp(v: any): number { const n = Number(v) || 0; return Math.max(0, Math.min(100, n)); }
  pctClass(v: any): string { const n = Number(v) || 0; return n >= 80 ? 'tile--verde' : n >= 50 ? 'tile--amar' : 'tile--rojo'; }
  origenBadge(o: string): string { return o === 'EVENTO' ? 'ui-badge--success' : o === 'AJUSTE' ? 'ui-badge--warning' : 'ui-badge--info'; }
  entries(d: any): [string, unknown][] { return Object.entries(d).filter(([k]) => k !== 'id'); }
  formatKey(k: string): string { return k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()); }
  formatValue(v: unknown): string {
    if (v === null || v === undefined || v === '') return '—';
    if (typeof v === 'boolean') return v ? 'Sí' : 'No';
    if (Array.isArray(v)) return v.length ? `${v.length} items` : '—';
    if (typeof v === 'object') return JSON.stringify(v);
    return String(v);
  }
}
