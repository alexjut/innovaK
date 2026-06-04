import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, OnInit, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AdminApi, PersonasResponse } from './admin.api';
import { LayoutService } from '../../core/layout/layout.service';

@Component({
  standalone: true,
  selector: 'app-admin-personas',
  imports: [CommonModule, FormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      <header class="page__header">
        <h1><i class="fa fa-user-plus"></i> Personas</h1>
        <p class="page__subtitle">
          Buscador de personas (participantes, beneficiarios, contratistas, funcionarios).
        </p>
      </header>

      <div class="ui-filter-bar">
        <input type="search" [(ngModel)]="q" (input)="buscar()"
               placeholder="Buscar por nombre, apellido o documento…"
               class="filter-field">
        <button class="ui-btn ui-btn--primary ui-btn--sm" (click)="abrirCrear.set(!abrirCrear())">
          <i class="fa fa-user-plus"></i> Crear persona
        </button>
      </div>

      @if (abrirCrear()) {
        <div class="form-create">
          <h3>Nueva persona</h3>
          <div class="grid">
            <label><span>Tipo documento</span>
              <select [(ngModel)]="nueva.tipo_documento_codigo">
                @for (t of tipos(); track t.codigo) { <option [value]="t.codigo">{{ t.nombre }}</option> }
              </select></label>
            <label><span>Documento *</span><input type="text" [(ngModel)]="nueva.numero_documento"></label>
            <label><span>Primer nombre *</span><input type="text" [(ngModel)]="nueva.nombre1"></label>
            <label><span>Segundo nombre</span><input type="text" [(ngModel)]="nueva.nombre2"></label>
            <label><span>Primer apellido *</span><input type="text" [(ngModel)]="nueva.apellido1"></label>
            <label><span>Segundo apellido</span><input type="text" [(ngModel)]="nueva.apellido2"></label>
            <label><span>Fecha nacimiento</span><input type="date" [(ngModel)]="nueva.fecha_nacimiento"></label>
          </div>
          <div class="form-actions">
            <button class="ui-btn ui-btn--ghost" (click)="abrirCrear.set(false)">Cancelar</button>
            <button class="ui-btn ui-btn--primary" [disabled]="guardando()" (click)="crearPersona()">
              @if (guardando()) { Guardando… } @else { Crear persona }
            </button>
          </div>
          @if (msg()) { <p class="msg" [class.err]="err()">{{ msg() }}</p> }
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
                <tr><th>#</th><th>Documento</th><th>Nombre</th></tr>
              </thead>
              <tbody>
                @for (p of d.results; track p.id) {
                  <tr>
                    <td>{{ p.id }}</td>
                    <td>{{ p.documento || '—' }}</td>
                    <td>{{ p.nombre }}</td>
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
    .page { max-width: 1200px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-3; }
    .page__loading { padding: $space-4; text-align: center; }
    .filter-field {
      width: 100%; max-width: 460px;
      padding: $space-2; border: 1px solid $color-border;
      border-radius: $radius-md;
    }
    .muted { color: $color-text-muted; margin: $space-2 0; }
    .form-create { background: $color-bg-subtle; border: 1px solid $color-border; border-radius: $radius-md; padding: $space-4; margin-bottom: $space-3;
      h3 { margin: 0 0 $space-3; color: $color-primary; } }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: $space-2; @media (max-width: 600px) { grid-template-columns: 1fr; } }
    .form-create label { display: block; span { display: block; font-size: $font-size-xs; color: $color-text-muted; }
      input, select { width: 100%; padding: 6px 8px; border: 1px solid $color-border; border-radius: $radius-sm; font: inherit; } }
    .form-actions { display: flex; gap: $space-2; justify-content: flex-end; margin-top: $space-2; }
    .msg { color: $color-success; &.err { color: $color-danger; } }
  `],
})
export class AdminPersonasComponent implements OnInit {
  private api = inject(AdminApi);
  private layout = inject(LayoutService);

  data = signal<PersonasResponse | null>(null);
  loading = signal<boolean>(false);
  q = '';
  private debounce: any;
  abrirCrear = signal<boolean>(false);
  guardando = signal<boolean>(false);
  msg = signal<string>(''); err = signal<boolean>(false);
  tipos = signal<{ codigo: number; nombre: string }[]>([]);
  nueva: any = {};

  crearPersona(): void {
    if (!this.nueva.numero_documento?.trim() || !this.nueva.nombre1?.trim() || !this.nueva.apellido1?.trim()) {
      this.err.set(true); this.msg.set('Documento, primer nombre y primer apellido son obligatorios.'); return;
    }
    this.guardando.set(true); this.msg.set(''); this.err.set(false);
    this.api.crearPersona(this.nueva).subscribe({
      next: (r) => {
        this.guardando.set(false);
        this.msg.set(`✓ ${r.ya_existia ? 'La persona ya existía' : 'Persona creada'} (#${r.id}).`);
        this.nueva = {}; this.cargar();
      },
      error: (e) => { this.guardando.set(false); this.err.set(true); this.msg.set(e?.error?.detail || 'Error al crear.'); },
    });
  }

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Administración', url: '/admin' },
      { label: 'Personas' },
    ]);
    this.api.tiposDocumento().subscribe(r => this.tipos.set(r.tipos_documento));
    this.cargar();
  }

  cargar(): void {
    this.loading.set(true);
    this.api.buscarPersonas(this.q, 1).subscribe({
      next: r => { this.data.set(r); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  buscar(): void {
    clearTimeout(this.debounce);
    this.debounce = setTimeout(() => this.cargar(), 300);
  }
}
