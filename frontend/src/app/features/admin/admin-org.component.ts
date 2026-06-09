import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, OnInit, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AdminApi, OrgListaResponse } from './admin.api';
import { LayoutService } from '../../core/layout/layout.service';
import { ConfigService } from '../../core/config/config.service';

type Entidad = 'dependencias' | 'subgrupos' | 'funcionarios'
             | 'organizaciones' | 'proveedores' | 'beneficiarios';

const TABS: { id: Entidad; label: string; icon: string }[] = [
  { id: 'dependencias', label: 'Dependencias', icon: 'fa-sitemap' },
  { id: 'subgrupos', label: 'Subgrupos', icon: 'fa-layer-group' },
  { id: 'funcionarios', label: 'Funcionarios', icon: 'fa-user-tie' },
  { id: 'organizaciones', label: 'Organizaciones', icon: 'fa-building' },
  { id: 'proveedores', label: 'Proveedores', icon: 'fa-truck' },
  { id: 'beneficiarios', label: 'Beneficiarios', icon: 'fa-hands-helping' },
];

@Component({
  standalone: true,
  selector: 'app-admin-org',
  imports: [CommonModule, FormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      <header class="page__header">
        <h1><i class="fa fa-building"></i> Organización</h1>
        <p class="page__subtitle">
          Dependencias, subgrupos, funcionarios, organizaciones, proveedores y beneficiarios.
        </p>
      </header>

      <nav class="tabs">
        @for (t of TABS; track t.id) {
          <button type="button" class="tab"
                  [class.tab--active]="tab() === t.id"
                  (click)="setTab(t.id)">
            <i class="fa" [class]="t.icon"></i> {{ t.label }}
          </button>
        }
      </nav>

      <div class="ui-filter-bar">
        <input type="search" [(ngModel)]="q" (input)="buscar()"
               placeholder="Buscar por nombre…" class="filter-field">
        @if (tab() === 'beneficiarios') {
          <button class="ui-btn ui-btn--ghost ui-btn--sm" (click)="exportarBeneficiarios('csv')">
            <i class="fa fa-file-csv"></i> CSV
          </button>
          <button class="ui-btn ui-btn--ghost ui-btn--sm" (click)="exportarBeneficiarios('excel')">
            <i class="fa fa-file-excel"></i> Excel
          </button>
        }
        <button class="ui-btn ui-btn--primary ui-btn--sm"
                (click)="formAbierto.set(!formAbierto())">
          <i class="fa fa-plus-circle"></i> Crear {{ singular(tab()) }}
        </button>
      </div>

      @if (formAbierto()) {
        <div class="form-create">
          <h3>{{ editId() ? 'Editar' : 'Nuevo' }} {{ singular(tab()) }}</h3>
          <div class="form-grid">
            @for (f of camposCrear(); track f.key) {
              <label>
                <span>{{ f.label }}{{ f.required ? ' *' : '' }}</span>
                <input [type]="f.type"
                       [ngModel]="form[f.key]"
                       (ngModelChange)="form[f.key] = $event">
              </label>
            }
          </div>
          <div class="form-actions">
            <button class="ui-btn ui-btn--ghost"
                    (click)="cerrarForm()">Cancelar</button>
            <button class="ui-btn ui-btn--primary"
                    [disabled]="(!editId() && !validar()) || guardando()"
                    (click)="guardar()">
              @if (guardando()) { Guardando… } @else { {{ editId() ? 'Guardar cambios' : 'Crear' }} }
            </button>
          </div>
          @if (msgCrear()) {
            <p class="msg" [class.err]="errCrear()">{{ msgCrear() }}</p>
          }
        </div>
      }

      @if (loading()) { <div class="page__loading">Cargando…</div> }
      @else if (data()) {
        @let d = data()!;
        <p class="muted">{{ d.count }} resultado{{ d.count === 1 ? '' : 's' }}</p>
        @if (d.results.length) {
          <div class="ui-table-responsive">
            <table class="ui-table">
              <thead>
                <tr>
                  <th>#</th>
                  @for (col of cols(); track col) {
                    <th>{{ col }}</th>
                  }
                  <th></th>
                </tr>
              </thead>
              <tbody>
                @for (it of d.results; track it.id) {
                  <tr>
                    <td>{{ it.id }}</td>
                    @for (col of cols(); track col) {
                      <td>{{ it[col.toLowerCase()] || '—' }}</td>
                    }
                    <td class="r">
                      <button class="ui-btn ui-btn--ghost ui-btn--sm" (click)="editar(it)">
                        <i class="fa fa-edit"></i> Editar
                      </button>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        } @else { <div class="ui-empty-state">Sin resultados.</div> }
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1300px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-3; }
    .page__loading { padding: $space-4; text-align: center; }
    .tabs {
      display: flex; gap: 2px; margin: $space-3 0; border-bottom: 2px solid $color-border;
      overflow-x: auto;
    }
    .tab {
      background: transparent; border: 0; padding: $space-2 $space-3; cursor: pointer;
      font-size: $font-size-sm; color: $color-text-muted;
      border-bottom: 3px solid transparent; margin-bottom: -2px; white-space: nowrap;
      i { margin-right: $space-1; }
      &:hover { color: $color-primary; }
      &--active {
        color: $color-primary; border-bottom-color: $color-primary;
        font-weight: $font-weight-semibold;
      }
    }
    .filter-field {
      width: 100%; max-width: 460px;
      padding: $space-2; border: 1px solid $color-border; border-radius: $radius-md;
    }
    .muted { color: $color-text-muted; margin: $space-2 0; }
    .form-create {
      background: $color-bg-subtle; padding: $space-3;
      border-radius: $radius-md; margin-bottom: $space-3;
      h3 { margin: 0 0 $space-2; font-size: $font-size-md; color: $color-primary; }
    }
    .form-grid {
      display: grid; grid-template-columns: repeat(3, 1fr); gap: $space-2;
      @media (max-width: 720px) { grid-template-columns: 1fr; }
      label { display: block; font-size: $font-size-xs; color: $color-text-muted;
              input { width: 100%; padding: $space-1 $space-2;
                      border: 1px solid $color-border; border-radius: $radius-sm;
                      margin-top: 2px; } }
    }
    .form-actions { margin-top: $space-2; display: flex; gap: $space-2; justify-content: flex-end; }
    .msg {
      margin-top: $space-2; padding: $space-1 $space-2;
      border-radius: $radius-sm;
      background: rgba(22,163,74,0.10); color: $color-success;
      &.err { background: rgba(220,38,38,0.10); color: $color-danger; }
    }
  `],
})
export class AdminOrgComponent implements OnInit {
  private api = inject(AdminApi);
  private cfg = inject(ConfigService);

  /** Descarga el padrón de beneficiarios (abre el endpoint Django con la sesión). */
  exportarBeneficiarios(formato: 'csv' | 'excel'): void {
    const url = formato === 'excel'
      ? '/org/beneficiarios/exportar/excel/'
      : '/org/beneficiarios/exportar/';
    window.open(this.cfg.url(url), '_blank');
  }
  private layout = inject(LayoutService);

  readonly TABS = TABS;
  tab = signal<Entidad>('dependencias');
  data = signal<OrgListaResponse | null>(null);
  loading = signal<boolean>(true);
  q = '';
  private debounce: any;

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Administración', url: '/admin' },
      { label: 'Organización' },
    ]);
    this.cargar();
  }

  formAbierto = signal<boolean>(false);
  guardando = signal<boolean>(false);
  msgCrear = signal<string>('');
  errCrear = signal<boolean>(false);
  form: Record<string, any> = {};

  setTab(t: Entidad): void {
    if (this.tab() === t) return;
    this.tab.set(t);
    this.q = '';
    this.form = {};
    this.formAbierto.set(false);
    this.editId.set(null);
    this.msgCrear.set('');
    this.cargar();
  }

  singular(t: Entidad): string {
    const m: Record<Entidad, string> = {
      dependencias: 'dependencia', subgrupos: 'subgrupo',
      funcionarios: 'funcionario', organizaciones: 'organización',
      proveedores: 'proveedor', beneficiarios: 'beneficiario',
    };
    return m[t];
  }

  camposCrear(): { key: string; label: string; type: string; required?: boolean }[] {
    switch (this.tab()) {
      case 'dependencias':
        return [{ key: 'nombre', label: 'Nombre', type: 'text', required: true }];
      case 'subgrupos':
        return [
          { key: 'nombre', label: 'Nombre', type: 'text', required: true },
          { key: 'dependencia_id', label: 'Dependencia ID', type: 'number', required: true },
        ];
      case 'funcionarios':
        return [
          { key: 'persona_id', label: 'Persona ID', type: 'number', required: true },
          { key: 'subgrupo_id', label: 'Subgrupo ID', type: 'number' },
          { key: 'dependencia_id', label: 'Dependencia ID', type: 'number' },
          { key: 'tipo_funcionario_id', label: 'Tipo funcionario ID', type: 'number' },
        ];
      case 'organizaciones':
        return [
          { key: 'nombre', label: 'Nombre', type: 'text', required: true },
          { key: 'nit', label: 'NIT', type: 'text' },
          { key: 'correo', label: 'Correo', type: 'email' },
          { key: 'telefono', label: 'Teléfono', type: 'text' },
        ];
      case 'proveedores':
        return [
          { key: 'nombre', label: 'Nombre', type: 'text', required: true },
          { key: 'nit', label: 'NIT', type: 'text', required: true },
          { key: 'tipo_persona', label: 'Tipo (NATURAL/JURIDICA)', type: 'text' },
          { key: 'direccion', label: 'Dirección', type: 'text' },
        ];
      case 'beneficiarios':
        return [
          { key: 'tipo', label: 'Tipo (PERSONA/ORGANIZACION/PROVEEDOR)', type: 'text', required: true },
          { key: 'tipo_documento_codigo', label: 'Código tipo documento', type: 'text', required: true },
          { key: 'numero_documento', label: 'Número de documento', type: 'text', required: true },
          { key: 'nombre_legal', label: 'Nombre legal', type: 'text', required: true },
          { key: 'persona_id', label: 'Persona ID (si tipo=PERSONA)', type: 'number' },
          { key: 'proveedor_id', label: 'Proveedor ID (si tipo=PROVEEDOR)', type: 'number' },
          { key: 'organizacion_id', label: 'Organización ID (si tipo=ORGANIZACION)', type: 'number' },
          { key: 'correo', label: 'Correo', type: 'email' },
          { key: 'telefono', label: 'Teléfono', type: 'text' },
        ];
    }
  }

  validar(): boolean {
    return this.camposCrear().filter(f => f.required)
      .every(f => this.form[f.key] !== undefined && this.form[f.key] !== '');
  }

  editId = signal<number | null>(null);

  editar(it: any): void {
    this.editId.set(it.id);
    this.form = { ...it };
    this.msgCrear.set(''); this.errCrear.set(false);
    this.formAbierto.set(true);
  }

  cerrarForm(): void {
    this.formAbierto.set(false);
    this.editId.set(null);
    this.form = {};
  }

  guardar(): void {
    const id = this.editId();
    if (!id && !this.validar()) return;
    this.guardando.set(true);
    this.msgCrear.set(''); this.errCrear.set(false);
    const obs = id
      ? this.api.editarOrg(this.tab(), id, this.form)
      : this.api.crearOrg(this.tab(), this.form);
    obs.subscribe({
      next: () => {
        this.msgCrear.set(id ? '✓ Cambios guardados.' : '✓ Creado.');
        this.guardando.set(false);
        this.form = {};
        this.editId.set(null);
        this.formAbierto.set(false);
        this.cargar();
      },
      error: e => {
        this.errCrear.set(true);
        this.msgCrear.set(e?.error?.detail || 'Error.');
        this.guardando.set(false);
      },
    });
  }

  cols(): string[] {
    switch (this.tab()) {
      case 'subgrupos': return ['Nombre', 'Dependencia'];
      case 'funcionarios': return ['Nombre', 'Subgrupo'];
      case 'organizaciones':
      case 'proveedores': return ['Nombre', 'Nit'];
      case 'beneficiarios': return ['Tipo'];
      default: return ['Nombre'];
    }
  }

  cargar(): void {
    this.loading.set(true);
    this.api.orgLista(this.tab(), this.q, 1).subscribe({
      next: r => { this.data.set(r); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  buscar(): void {
    clearTimeout(this.debounce);
    this.debounce = setTimeout(() => this.cargar(), 300);
  }
}
