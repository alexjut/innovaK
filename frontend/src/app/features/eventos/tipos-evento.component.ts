import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import {
  ChangeDetectionStrategy, Component, OnInit, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

interface TipoEvento {
  codigo: string;
  nombre: string;
  descripcion: string;
  icono: string;
  color_hex: string;
  activo: boolean;
  orden: number;
  permite_caracterizacion: boolean;
  permite_inscripcion: boolean;
  permite_qr: boolean;
  requiere_actividad_plan: boolean;
  eventos_count: number;
}

@Component({
  standalone: true,
  selector: 'app-tipos-evento',
  imports: [CommonModule, FormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      <header class="page__header">
        <div>
          <h1><i class="fa fa-tags"></i> Tipos de actividad</h1>
          <p class="page__subtitle">
            Catálogo de tipos. Los inactivos aparecen al final.
          </p>
        </div>
      </header>

      @if (loading()) { <div class="page__loading">Cargando…</div> }
      @else {
        <details class="form-create" [open]="!tipos().length">
          <summary>+ Crear nuevo tipo</summary>
          <div class="form-grid">
            <label>Código *
              <input type="text" [(ngModel)]="nuevo.codigo" placeholder="EJ: TALLER">
            </label>
            <label>Nombre *
              <input type="text" [(ngModel)]="nuevo.nombre">
            </label>
            <label>Icono FA
              <input type="text" [(ngModel)]="nuevo.icono" placeholder="fa-folder">
            </label>
            <label>Color hex
              <input type="color" [(ngModel)]="nuevo.color_hex">
            </label>
            <label>Orden
              <input type="number" [(ngModel)]="nuevo.orden">
            </label>
          </div>
          <div class="checks">
            <label><input type="checkbox" [(ngModel)]="nuevo.activo"> Activo</label>
            <label><input type="checkbox" [(ngModel)]="nuevo.permite_caracterizacion"> Caracterización</label>
            <label><input type="checkbox" [(ngModel)]="nuevo.permite_inscripcion"> Inscripción</label>
            <label><input type="checkbox" [(ngModel)]="nuevo.permite_qr"> QR</label>
            <label><input type="checkbox" [(ngModel)]="nuevo.requiere_actividad_plan"> Requiere act. plan</label>
          </div>
          <button class="ui-btn ui-btn--primary"
                  [disabled]="!nuevo.codigo || !nuevo.nombre || guardando()"
                  (click)="crear()">
            @if (guardando()) { Creando… } @else { Crear tipo }
          </button>
          @if (msg()) { <p class="ui-info-bar">{{ msg() }}</p> }
        </details>

        @if (tipos().length) {
          <div class="ui-table-responsive" style="margin-top: 16px;">
            <table class="ui-table">
              <thead>
                <tr>
                  <th>Código</th><th>Nombre</th><th>Icono</th><th>Color</th>
                  <th>Flags</th><th>Eventos</th><th>Activo</th><th></th>
                </tr>
              </thead>
              <tbody>
                @for (t of tipos(); track t.codigo) {
                  <tr [class.row--inactive]="!t.activo">
                    <td><code>{{ t.codigo }}</code></td>
                    <td>{{ t.nombre }}</td>
                    <td><i class="fa" [class]="t.icono"></i> {{ t.icono }}</td>
                    <td>
                      <span class="color-dot" [style.background]="t.color_hex"></span>
                      {{ t.color_hex }}
                    </td>
                    <td>
                      @if (t.permite_caracterizacion) { <span class="flag flag--acc">Caract</span> }
                      @if (t.permite_inscripcion) { <span class="flag flag--ins">Inscrip</span> }
                      @if (t.permite_qr) { <span class="flag flag--qr">QR</span> }
                      @if (t.requiere_actividad_plan) { <span class="flag flag--ap">AP</span> }
                    </td>
                    <td>{{ t.eventos_count }}</td>
                    <td>
                      <button (click)="toggleActivo(t)" class="toggle-btn"
                              [class.is-active]="t.activo">
                        {{ t.activo ? 'Activo' : 'Inactivo' }}
                      </button>
                    </td>
                    <td>
                      <button class="ui-btn ui-btn--sm ui-btn--ghost"
                              (click)="abrirEdicion(t)">
                        <i class="fa fa-pencil"></i> Editar
                      </button>
                    </td>
                  </tr>
                  @if (editandoCodigo() === t.codigo) {
                    <tr class="edit-row">
                      <td colspan="8">
                        <div class="edit-panel">
                          <div class="form-grid">
                            <label>Código
                              <input type="text" [value]="t.codigo" disabled>
                            </label>
                            <label>Nombre *
                              <input type="text" [(ngModel)]="editForm.nombre">
                            </label>
                            <label>Icono FA
                              <input type="text" [(ngModel)]="editForm.icono" placeholder="fa-folder">
                            </label>
                            <label>Color hex
                              <input type="color" [(ngModel)]="editForm.color_hex">
                            </label>
                            <label>Orden
                              <input type="number" [(ngModel)]="editForm.orden">
                            </label>
                          </div>
                          <label class="edit-desc">Descripción
                            <textarea rows="2" [(ngModel)]="editForm.descripcion"></textarea>
                          </label>
                          <div class="checks">
                            <label><input type="checkbox" [(ngModel)]="editForm.permite_caracterizacion"> Caracterización</label>
                            <label><input type="checkbox" [(ngModel)]="editForm.permite_inscripcion"> Inscripción</label>
                            <label><input type="checkbox" [(ngModel)]="editForm.permite_qr"> QR</label>
                            <label><input type="checkbox" [(ngModel)]="editForm.requiere_actividad_plan"> Requiere act. plan</label>
                          </div>
                          <div class="edit-actions">
                            <button class="ui-btn ui-btn--primary ui-btn--sm"
                                    [disabled]="!editForm.nombre || editGuardando()"
                                    (click)="guardarEdicion(t)">
                              @if (editGuardando()) { Guardando… } @else { Guardar cambios }
                            </button>
                            <button class="ui-btn ui-btn--ghost ui-btn--sm" (click)="cancelarEdicion()">
                              Cancelar
                            </button>
                            @if (editMsg()) {
                              <span class="ui-info-bar"
                                    [class.ui-info-bar--success]="!editError()"
                                    [class.ui-info-bar--danger]="editError()">{{ editMsg() }}</span>
                            }
                          </div>
                        </div>
                      </td>
                    </tr>
                  }
                }
              </tbody>
            </table>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1300px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-3; }
    .page__loading { padding: $space-4; text-align: center; color: $color-text-muted; }
    .form-create {
      background: $color-bg-subtle;
      border-radius: $radius-md;
      padding: $space-3;
      summary { cursor: pointer; font-weight: $font-weight-semibold; }
    }
    .form-grid {
      display: grid; grid-template-columns: repeat(5, 1fr); gap: $space-2;
      margin: $space-2 0;
      @media (max-width: 720px) { grid-template-columns: 1fr 1fr; }
      label { display: block; font-size: $font-size-xs; color: $color-text-muted; }
      input { width: 100%; padding: $space-1 $space-2;
              border: 1px solid $color-border; border-radius: $radius-sm; margin-top: 2px; }
    }
    .checks {
      display: flex; gap: $space-3; flex-wrap: wrap; margin: $space-2 0;
      label { display: flex; align-items: center; gap: $space-1; font-size: $font-size-sm; }
    }
    .row--inactive { opacity: 0.55; }
    .color-dot { display:inline-block; width: 12px; height: 12px; border-radius: 3px;
                 vertical-align: middle; margin-right: 4px;
                 border: 1px solid rgba(0,0,0,0.2); }
    .flag {
      display: inline-block; padding: 1px 6px; border-radius: $radius-pill;
      font-size: 10px; margin-right: 2px; background: $color-bg-subtle; color: $color-text-muted;
      &--acc { background: rgba(168,85,247,0.15); color: #7E22CE; }
      &--ins { background: rgba(214,0,28,0.10); color: $color-primary; }
      &--qr  { background: rgba(13,148,136,0.12); color: #0D9488; }
      &--ap  { background: rgba(245,158,11,0.12); color: #B45309; }
    }
    .toggle-btn {
      background: $color-bg-subtle; border: 1px solid $color-border;
      padding: 2px 10px; border-radius: $radius-pill; font-size: $font-size-xs;
      cursor: pointer;
      &.is-active { background: rgba(22,163,74,0.12); border-color: $color-success; color: $color-success; }
    }
    .edit-row td { background: $color-bg-subtle; padding: 0; }
    .edit-panel { padding: $space-3; border-left: 3px solid $color-primary; }
    .edit-desc {
      display: block; font-size: $font-size-xs; color: $color-text-muted; margin: $space-2 0;
      textarea { width: 100%; padding: $space-1 $space-2; border: 1px solid $color-border;
                 border-radius: $radius-sm; margin-top: 2px; font-family: $font-family-base; resize: vertical; }
    }
    .edit-actions { display: flex; gap: $space-2; align-items: center; margin-top: $space-2; }
  `],
})
export class TiposEventoComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);

  tipos = signal<TipoEvento[]>([]);
  loading = signal<boolean>(true);
  guardando = signal<boolean>(false);
  msg = signal<string>('');

  // Edición inline de un tipo existente
  editandoCodigo = signal<string | null>(null);
  editGuardando = signal<boolean>(false);
  editMsg = signal<string>('');
  editError = signal<boolean>(false);
  editForm: Partial<TipoEvento> = {};

  nuevo: Partial<TipoEvento> = {
    codigo: '', nombre: '', descripcion: '', icono: 'fa-folder',
    color_hex: '#6B7280', activo: true, orden: 100,
    permite_caracterizacion: false, permite_inscripcion: false,
    permite_qr: false, requiere_actividad_plan: false,
  };

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Lista de actividades', url: '/eventos' },
      { label: 'Tipos de actividad' },
    ]);
    this.cargar();
  }

  cargar(): void {
    this.loading.set(true);
    this.http.get<{ results: TipoEvento[] }>(
      this.cfg.url('/api/tipos-evento/'),
    ).subscribe({
      next: r => { this.tipos.set(r.results); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  crear(): void {
    if (!this.nuevo.codigo || !this.nuevo.nombre) return;
    this.nuevo.codigo = this.nuevo.codigo.toUpperCase();
    this.guardando.set(true);
    this.http.post<{ detail: string }>(
      this.cfg.url('/api/tipos-evento/'), this.nuevo,
    ).subscribe({
      next: r => {
        this.msg.set('✓ ' + r.detail);
        this.guardando.set(false);
        this.nuevo = {
          codigo: '', nombre: '', descripcion: '', icono: 'fa-folder',
          color_hex: '#6B7280', activo: true, orden: 100,
          permite_caracterizacion: false, permite_inscripcion: false,
          permite_qr: false, requiere_actividad_plan: false,
        };
        this.cargar();
      },
      error: e => {
        this.msg.set(e?.error?.detail || 'Error creando tipo.');
        this.guardando.set(false);
      },
    });
  }

  toggleActivo(t: TipoEvento): void {
    this.http.patch(
      this.cfg.url(`/api/tipos-evento/${t.codigo}/`),
      { activo: !t.activo },
    ).subscribe(() => this.cargar());
  }

  // ── Edición inline ───────────────────────────────────────────────
  abrirEdicion(t: TipoEvento): void {
    if (this.editandoCodigo() === t.codigo) { this.cancelarEdicion(); return; }
    this.editandoCodigo.set(t.codigo);
    this.editMsg.set('');
    this.editError.set(false);
    this.editForm = {
      nombre: t.nombre, descripcion: t.descripcion, icono: t.icono,
      color_hex: t.color_hex, orden: t.orden,
      permite_caracterizacion: t.permite_caracterizacion,
      permite_inscripcion: t.permite_inscripcion,
      permite_qr: t.permite_qr,
      requiere_actividad_plan: t.requiere_actividad_plan,
    };
  }

  cancelarEdicion(): void {
    this.editandoCodigo.set(null);
    this.editForm = {};
    this.editMsg.set('');
  }

  guardarEdicion(t: TipoEvento): void {
    if (!this.editForm.nombre) return;
    this.editGuardando.set(true);
    this.editMsg.set('');
    this.http.patch<{ detail: string }>(
      this.cfg.url(`/api/tipos-evento/${t.codigo}/`), this.editForm,
    ).subscribe({
      next: () => {
        this.editGuardando.set(false);
        this.cancelarEdicion();
        this.cargar();
      },
      error: e => {
        this.editGuardando.set(false);
        this.editError.set(true);
        this.editMsg.set('⚠ ' + (e?.error?.detail || 'Error guardando.'));
      },
    });
  }
}
