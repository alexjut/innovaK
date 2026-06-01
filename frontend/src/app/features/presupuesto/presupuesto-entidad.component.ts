import { CommonModule } from '@angular/common';
import { HttpClient, HttpParams } from '@angular/common/http';
import {
  ChangeDetectionStrategy, Component, OnInit, computed, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

interface ColDef { key: string; label: string; pipe?: 'money' | 'badge'; }
interface FieldDef { key: string; label: string; type: string; required?: boolean; }

interface EntidadConfig {
  titulo: string;
  endpoint: string;          // GET (lista) y POST (crear)
  itemKey: string;           // PK ('id' o 'codigo')
  cols: ColDef[];
  formFields: FieldDef[];
  detalleRuta?: (id: any) => string;  // si la fila navega a detalle
  paginated?: boolean;       // DRF paginator vs results plana
}

const CONFIGS: Record<string, EntidadConfig> = {
  proyectos: {
    titulo: 'Proyectos del plan',
    endpoint: '/presupuesto/api/proyectos/',
    itemKey: 'id',
    cols: [
      { key: 'codigo', label: 'Código' },
      { key: 'nombre', label: 'Nombre' },
      { key: 'subgrupo_nombre', label: 'Subgrupo' },
      { key: 'dependencia_nombre', label: 'Dependencia' },
    ],
    formFields: [],
    detalleRuta: id => `/presupuesto/proyectos/${id}`,
    paginated: true,
  },
  programas: {
    titulo: 'Programas',
    endpoint: '/presupuesto/api/programas/',
    itemKey: 'id',
    cols: [{ key: 'id', label: '#' }, { key: 'nombre', label: 'Nombre' }],
    formFields: [
      { key: 'nombre', label: 'Nombre', type: 'text', required: true },
      { key: 'descripcion', label: 'Descripción', type: 'text' },
    ],
  },
  objetivos: {
    titulo: 'Objetivos estratégicos',
    endpoint: '/presupuesto/api/objetivos/',
    itemKey: 'id',
    cols: [{ key: 'id', label: '#' }, { key: 'nombre', label: 'Nombre' }],
    formFields: [
      { key: 'nombre', label: 'Nombre', type: 'text', required: true },
    ],
  },
  metas: {
    titulo: 'Catálogo de Metas',
    endpoint: '/presupuesto/api/metas/',
    itemKey: 'codigo',
    cols: [{ key: 'codigo', label: 'Código' }, { key: 'nombre', label: 'Nombre' }],
    formFields: [
      { key: 'nombre', label: 'Nombre', type: 'text', required: true },
    ],
  },
  conceptos: {
    titulo: 'Conceptos de gasto',
    endpoint: '/presupuesto/api/conceptos-gasto/',
    itemKey: 'id',
    cols: [
      { key: 'codigo', label: 'Código' },
      { key: 'nombre', label: 'Nombre' },
      { key: 'tipo', label: 'Tipo' },
      { key: 'programa', label: 'Programa' },
    ],
    formFields: [
      { key: 'codigo', label: 'Código', type: 'text', required: true },
      { key: 'nombre', label: 'Nombre', type: 'text', required: true },
      { key: 'tipo', label: 'Tipo (INV/FUN/MIX)', type: 'text' },
      { key: 'programa_id', label: 'Programa ID', type: 'number', required: true },
      { key: 'vigencia_id', label: 'Vigencia ID', type: 'number', required: true },
    ],
  },
  cdps: {
    titulo: 'CDPs',
    endpoint: '/presupuesto/api/cdps/',
    itemKey: 'id',
    cols: [
      { key: 'numero', label: 'Número' },
      { key: 'fecha', label: 'Fecha' },
      { key: 'valor', label: 'Valor', pipe: 'money' },
      { key: 'saldo_libre', label: 'Saldo libre', pipe: 'money' },
      { key: 'proyecto_codigo', label: 'Proyecto' },
    ],
    formFields: [],
    paginated: true,
  },
  contratos: {
    titulo: 'Contratos',
    endpoint: '/presupuesto/api/contratos/',
    itemKey: 'id',
    cols: [
      { key: 'contrato_numero', label: 'Número' },
      { key: 'contrato_vigencia', label: 'Vigencia' },
      { key: 'valor', label: 'Valor', pipe: 'money' },
      { key: 'cdp_numero', label: 'CDP' },
    ],
    formFields: [],
    paginated: true,
  },
  indicadores: {
    titulo: 'Indicadores (KPIs)',
    endpoint: '/presupuesto/api/indicadores/',
    itemKey: 'id',
    cols: [
      { key: 'id', label: '#' },
      { key: 'nombre', label: 'Nombre' },
      { key: 'unidad_medida', label: 'Unidad' },
      { key: 'meta_magnitud', label: 'Meta' },
      { key: 'avance_acumulado', label: 'Avance' },
      { key: 'avance_pct', label: '%' },
    ],
    formFields: [],
    paginated: true,
  },
  avances: {
    titulo: 'Avances de KPIs',
    endpoint: '/presupuesto/api/avances/',
    itemKey: 'id',
    cols: [
      { key: 'indicador', label: 'KPI' },
      { key: 'magnitud_aportada', label: 'Magnitud' },
      { key: 'fecha_aporte', label: 'Fecha' },
      { key: 'periodo', label: 'Periodo' },
      { key: 'origen', label: 'Origen' },
    ],
    formFields: [],
    paginated: true,
  },
  'meta-proyecto': {
    titulo: 'Meta ↔ Proyecto',
    endpoint: '/presupuesto/api/metas-proyecto/',
    itemKey: 'id',
    cols: [
      { key: 'id', label: '#' },
      { key: 'meta_codigo', label: 'Meta' },
      { key: 'meta_nombre', label: 'Meta nombre' },
      { key: 'proyecto_id', label: 'Proyecto' },
    ],
    formFields: [
      { key: 'meta_id', label: 'Meta ID (codigo)', type: 'number', required: true },
      { key: 'proyecto_id', label: 'Proyecto ID', type: 'number', required: true },
    ],
  },
  'actividad-indicador': {
    titulo: 'Vinculación Actividad ↔ KPI',
    endpoint: '/presupuesto/api/actividad-indicador/',
    itemKey: 'id',
    cols: [
      { key: 'id', label: '#' },
      { key: 'actividad_plan_id', label: 'Actividad #' },
      { key: 'actividad_descripcion', label: 'Actividad' },
      { key: 'indicador_id', label: 'KPI #' },
      { key: 'indicador_nombre', label: 'KPI nombre' },
    ],
    formFields: [
      { key: 'actividad_plan_id', label: 'Actividad Plan ID', type: 'number', required: true },
      { key: 'indicador_id', label: 'Indicador (KPI) ID', type: 'number', required: true },
    ],
  },
};

@Component({
  standalone: true,
  selector: 'app-presupuesto-entidad',
  imports: [CommonModule, FormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      @if (!cfg()) {
        <div class="page__error">Entidad no soportada.</div>
      } @else {
        @let c = cfg()!;
        <header class="page__header">
          <div>
            <h1>{{ c.titulo }}</h1>
            @if (data()) {
              <p class="page__subtitle">{{ count() }} registro{{ count() === 1 ? '' : 's' }}</p>
            }
          </div>
          @if (c.formFields.length) {
            <button class="ui-btn ui-btn--primary"
                    (click)="formAbierto.set(!formAbierto())">
              <i class="fa fa-plus-circle"></i> Crear
            </button>
          }
        </header>

        @if (formAbierto() && c.formFields.length) {
          <div class="form-create">
            @for (f of c.formFields; track f.key) {
              <label>
                <span>{{ f.label }}{{ f.required ? ' *' : '' }}</span>
                <input [type]="f.type"
                       [ngModel]="form[f.key]"
                       (ngModelChange)="form[f.key] = $event">
              </label>
            }
            <div class="form-actions">
              <button class="ui-btn ui-btn--ghost"
                      (click)="formAbierto.set(false)">Cancelar</button>
              <button class="ui-btn ui-btn--primary"
                      [disabled]="!validar() || guardando()"
                      (click)="crear()">
                @if (guardando()) { Guardando… } @else { Crear }
              </button>
            </div>
            @if (msg()) { <p class="msg" [class.err]="errorCrear()">{{ msg() }}</p> }
          </div>
        }

        @if (loading()) { <div class="page__loading">Cargando…</div> }
        @else if (rows().length) {
          <div class="ui-table-responsive">
            <table class="ui-table">
              <thead>
                <tr>
                  @for (col of c.cols; track col.key) {
                    <th>{{ col.label }}</th>
                  }
                </tr>
              </thead>
              <tbody>
                @for (row of rows(); track $index) {
                  <tr [class.row--link]="!!c.detalleRuta"
                      (click)="navegar(row)">
                    @for (col of c.cols; track col.key) {
                      <td>{{ celda(row, col) }}</td>
                    }
                  </tr>
                }
              </tbody>
            </table>
          </div>
        } @else {
          <div class="ui-empty-state">Sin resultados.</div>
        }
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1300px; margin: 0 auto; }
    .page__header {
      display: flex; justify-content: space-between;
      align-items: flex-start; gap: $space-3; flex-wrap: wrap;
      h1 { margin: 0; color: $color-primary; }
    }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-3; }
    .page__loading, .page__error {
      padding: $space-4; text-align: center; color: $color-text-muted;
    }
    .form-create {
      background: $color-bg-subtle; padding: $space-3;
      border-radius: $radius-md; margin-bottom: $space-3;
      display: grid; grid-template-columns: repeat(3, 1fr); gap: $space-2;
      @media (max-width: 720px) { grid-template-columns: 1fr; }
      label {
        display: block;
        span { display: block; font-size: $font-size-xs; color: $color-text-muted; }
        input {
          width: 100%; padding: $space-1 $space-2;
          border: 1px solid $color-border; border-radius: $radius-sm;
          margin-top: 2px;
        }
      }
      .form-actions {
        grid-column: 1 / -1;
        display: flex; gap: $space-2; justify-content: flex-end;
        margin-top: $space-2;
      }
      .msg {
        grid-column: 1 / -1;
        padding: $space-1 $space-2; border-radius: $radius-sm;
        background: rgba(22,163,74,0.10); color: $color-success;
        &.err { background: rgba(220,38,38,0.10); color: $color-danger; }
      }
    }
    .row--link { cursor: pointer; }
    .row--link:hover { background: rgba(214,0,28,0.04); }
  `],
})
export class PresupuestoEntidadComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg2 = inject(ConfigService);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);
  private routerLink: any;

  cfg = signal<EntidadConfig | null>(null);
  data = signal<any | null>(null);
  loading = signal<boolean>(true);
  formAbierto = signal<boolean>(false);
  guardando = signal<boolean>(false);
  msg = signal<string>('');
  errorCrear = signal<boolean>(false);
  form: Record<string, any> = {};

  rows = computed<any[]>(() => {
    const d = this.data();
    if (!d) return [];
    return d.results || d.items || (Array.isArray(d) ? d : []);
  });
  count = computed<number>(() => {
    const d = this.data();
    return d?.count ?? this.rows().length;
  });

  ngOnInit(): void {
    this.route.paramMap.subscribe(p => {
      const entidad = p.get('entidad') || '';
      const cfg = CONFIGS[entidad] || null;
      this.cfg.set(cfg);
      this.form = {};
      this.formAbierto.set(false);
      this.msg.set('');
      this.layout.setBreadcrumb([
        { label: 'Inicio', url: '/' },
        { label: 'Presupuesto', url: '/presupuesto' },
        { label: cfg?.titulo || entidad },
      ]);
      if (cfg) this.cargar(cfg);
    });
  }

  cargar(cfg: EntidadConfig): void {
    this.loading.set(true);
    this.http.get<any>(this.cfg2.url(cfg.endpoint)).subscribe({
      next: r => { this.data.set(r); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  validar(): boolean {
    const c = this.cfg(); if (!c) return false;
    return c.formFields.filter(f => f.required)
      .every(f => this.form[f.key] !== undefined && this.form[f.key] !== '');
  }

  crear(): void {
    const c = this.cfg(); if (!c) return;
    this.guardando.set(true);
    this.msg.set(''); this.errorCrear.set(false);
    this.http.post(this.cfg2.url(c.endpoint), this.form).subscribe({
      next: () => {
        this.msg.set('✓ Creado.');
        this.guardando.set(false);
        this.form = {};
        this.formAbierto.set(false);
        this.cargar(c);
      },
      error: e => {
        this.errorCrear.set(true);
        this.msg.set(e?.error?.detail || 'Error.');
        this.guardando.set(false);
      },
    });
  }

  celda(row: any, col: ColDef): string {
    const v = row[col.key];
    if (v == null || v === '') return '—';
    if (col.pipe === 'money') {
      return '$' + Number(v).toLocaleString('es-CO', { maximumFractionDigits: 0 });
    }
    return String(v);
  }

  navegar(row: any): void {
    const c = this.cfg();
    if (!c?.detalleRuta) return;
    window.location.href = '/app' + c.detalleRuta(row[c.itemKey]);
  }
}
