import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { CapturaApi, CapturaItem, CapturaDetalle } from './captura.api';
import { LayoutService } from '../../core/layout/layout.service';

const TIPOS: Record<string, string> = {
  CULTURA_ORG: 'Beneficio a organización',
  ESTIMULO_CULTURAL: 'Estímulo',
  PROYECTO_CULTURAL: 'Proyecto financiado',
};

@Component({
  standalone: true,
  selector: 'app-captura-list',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header" style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;">
        <div>
          <h1><i class="fa fa-clipboard-check"></i> {{ tituloTipo() }}</h1>
          <p class="page__subtitle">Registros capturados — validar/rechazar suma al KPI de la actividad.</p>
        </div>
        <a [routerLink]="['/captura/insights']" [queryParams]="{ tipo: tipo() }" class="ui-btn ui-btn--primary ui-btn--sm">
          <i class="fa fa-chart-pie"></i> Insights
        </a>
      </header>

      <div class="ui-filter-bar">
        <div class="ui-filter-bar__group">
          <label class="ui-filter-bar__label">Tipo</label>
          <select class="ui-filter-bar__field" [(ngModel)]="fTipo" (ngModelChange)="cargar()">
            <option value="">Todos</option>
            <option value="CULTURA_ORG">Beneficio a organización</option>
            <option value="ESTIMULO_CULTURAL">Estímulo</option>
            <option value="PROYECTO_CULTURAL">Proyecto financiado</option>
          </select>
        </div>
        <div class="ui-filter-bar__group">
          <label class="ui-filter-bar__label">Estado</label>
          <select class="ui-filter-bar__field" [(ngModel)]="fEstado" (ngModelChange)="cargar()">
            <option value="">Todos</option>
            <option value="enviada">Enviadas</option>
            <option value="validada">Validadas</option>
            <option value="rechazada">Rechazadas</option>
          </select>
        </div>
        <div class="ui-filter-bar__group">
          <label class="ui-filter-bar__label">Buscar</label>
          <input type="search" class="ui-filter-bar__field" placeholder="Nombre o documento…"
                 [(ngModel)]="fQ" (keyup.enter)="cargar()">
        </div>
        <div class="ui-filter-bar__actions">
          <button class="ui-btn ui-btn--sm ui-btn--primary" (click)="cargar()"><i class="fa fa-search"></i> Aplicar</button>
        </div>
      </div>

      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando…</div> }
      @else if (rows().length === 0) { <div class="ui-empty-state"><i class="fa fa-folder-open"></i><p>Sin registros para el filtro.</p></div> }
      @else {
        <div class="grid">
          <div class="ui-table-responsive">
            <table class="ui-table">
              <thead><tr><th>#</th><th>Tipo</th><th>Nombre</th><th>Documento</th><th>Estado</th><th></th></tr></thead>
              <tbody>
                @for (r of rows(); track r.id) {
                  <tr [class.sel]="sel()?.id === r.id">
                    <td>{{ r.id }}</td>
                    <td>{{ tipoLabel(r.tipo_codigo) }}</td>
                    <td>{{ r.nombre_legal || '—' }}</td>
                    <td>{{ r.numero_documento || '—' }}</td>
                    <td><span class="ui-badge" [class]="badge(r.estado)">{{ r.estado }}</span></td>
                    <td><button class="ui-btn ui-btn--sm ui-btn--ghost" (click)="abrir(r)"><i class="fa fa-eye"></i> Ver</button></td>
                  </tr>
                }
              </tbody>
            </table>
          </div>

          @if (sel(); as d) {
            <aside class="detalle">
              <header class="detalle__head">
                <h2>{{ d.titulo_tipo }} #{{ d.id }}</h2>
                <button class="ui-btn ui-btn--sm ui-btn--ghost" (click)="sel.set(null)"><i class="fa fa-times"></i></button>
              </header>
              <p class="muted">{{ d.evento_nombre }}</p>
              <span class="ui-badge" [class]="badge(d.estado)">{{ d.estado }}</span>

              <dl class="kv">
                @for (campo of d.campos; track campo.name) {
                  @if (d.datos[campo.name]) { <dt>{{ campo.label }}</dt><dd>{{ d.datos[campo.name] }}</dd> }
                }
              </dl>
              @if (d.firma_mongo_id) { <p class="muted"><i class="fa fa-pen-nib"></i> Firma registrada</p> }

              @if (msg()) { <p class="ui-info-bar" [class.ui-info-bar--success]="!err()" [class.ui-info-bar--danger]="err()">{{ msg() }}</p> }

              @if (d.estado !== 'validada') {
                <button class="ui-btn ui-btn--primary ui-btn--block" [disabled]="guardando()" (click)="accion(d,'validar')">
                  <i class="fa fa-check"></i> Validar (suma al KPI)
                </button>
              }
              @if (d.estado !== 'rechazada') {
                <button class="ui-btn ui-btn--ghost ui-btn--block" [disabled]="guardando()" (click)="accion(d,'rechazar')" style="margin-top:8px;">
                  <i class="fa fa-ban"></i> Rechazar
                </button>
              }
            </aside>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display:block; }
    .page { max-width:1300px; margin:0 auto; }
    .page__header h1 { margin:0; color:$color-primary; i{margin-right:$space-2;} }
    .page__subtitle { color:$color-text-muted; margin:$space-1 0 $space-3; }
    .grid { display:grid; grid-template-columns:1fr; gap:$space-3; @media (min-width:#{$bp-lg}) { grid-template-columns:1fr 360px; } }
    .ui-table tr.sel { background:rgba(214,0,28,.05); }
    .detalle { background:$color-bg; border:1.5px solid $color-border; border-radius:$radius-lg; padding:$space-4; align-self:start; position:sticky; top:$space-4; }
    .detalle__head { display:flex; justify-content:space-between; align-items:center; h2{margin:0;font-size:$font-size-md;color:$color-primary;} }
    .muted { color:$color-text-muted; font-size:$font-size-sm; }
    .kv { display:grid; grid-template-columns:max-content 1fr; gap:$space-1 $space-3; margin:$space-3 0; dt{font-weight:600;color:$color-text-muted;font-size:$font-size-xs;} dd{margin:0;font-size:$font-size-sm;word-break:break-word;} }
    .ui-btn--block { display:flex; width:100%; justify-content:center; }
  `],
})
export class CapturaListComponent implements OnInit {
  private api = inject(CapturaApi);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);

  loading = signal(false);
  rows = signal<CapturaItem[]>([]);
  sel = signal<CapturaDetalle | null>(null);
  guardando = signal(false);
  msg = signal(''); err = signal(false);

  fTipo = ''; fEstado = ''; fQ = '';
  tipo = signal('');

  ngOnInit(): void {
    this.layout.setBreadcrumb([{ label: 'Inicio', url: '/' }, { label: 'Actividades', url: '/actividades' }, { label: 'Registros capturados' }]);
    this.route.queryParamMap.subscribe(q => {
      this.fTipo = q.get('tipo') || ''; this.tipo.set(this.fTipo);
      const ev = q.get('evento'); if (ev) this.fEstado = this.fEstado;
      this.cargar();
    });
  }

  tituloTipo(): string { return this.fTipo ? (TIPOS[this.fTipo] || 'Registros') : 'Registros capturados'; }
  tipoLabel(c: string): string { return TIPOS[c] || c; }
  badge(e: string): string { return e === 'validada' ? 'ui-badge--success' : e === 'rechazada' ? 'ui-badge--danger' : 'ui-badge--info'; }

  cargar(): void {
    this.tipo.set(this.fTipo);
    this.loading.set(true);
    this.api.list({ estado: this.fEstado || undefined, q: this.fQ || undefined, evento: Number(this.route.snapshot.queryParamMap.get('evento')) || undefined }).subscribe({
      next: r => {
        let res = r.results;
        if (this.fTipo) res = res.filter(x => x.tipo_codigo === this.fTipo);
        this.rows.set(res); this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  abrir(r: CapturaItem): void {
    this.msg.set('');
    this.api.detalle(r.id).subscribe(d => this.sel.set(d));
  }

  accion(d: CapturaDetalle, accion: 'validar' | 'rechazar'): void {
    this.guardando.set(true); this.msg.set('');
    this.api.estado(d.id, accion).subscribe({
      next: r => {
        this.guardando.set(false); this.err.set(false);
        this.msg.set(`✓ ${r.detail}` + (accion === 'validar' ? ` (+${r.kpi_aportes} al KPI)` : ''));
        this.sel.set({ ...d, estado: r.estado });
        this.cargar();
      },
      error: e => { this.guardando.set(false); this.err.set(true); this.msg.set(e?.error?.detail || 'Error.'); },
    });
  }
}
