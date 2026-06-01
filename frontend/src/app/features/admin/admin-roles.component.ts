import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, OnInit, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AdminApi, RolItem } from './admin.api';
import { LayoutService } from '../../core/layout/layout.service';

@Component({
  standalone: true,
  selector: 'app-admin-roles',
  imports: [CommonModule, FormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      <header class="page__header">
        <div>
          <h1><i class="fa fa-user-shield"></i> Roles y permisos</h1>
          <p class="page__subtitle">
            Grupos del sistema con conteo de usuarios y módulos asignados.
          </p>
        </div>
        <button type="button" class="ui-btn ui-btn--primary"
                (click)="abrirCrear.set(!abrirCrear())">
          <i class="fa fa-plus-circle"></i> Crear rol
        </button>
      </header>

      @if (abrirCrear()) {
        <div class="form-create">
          <label>Nombre del nuevo rol:
            <input type="text" [(ngModel)]="nuevoNombre" placeholder="Ej. CoordinadorEducacion">
          </label>
          <button class="ui-btn ui-btn--primary"
                  [disabled]="!nuevoNombre.trim() || guardando()"
                  (click)="crear()">
            @if (guardando()) { Creando… } @else { Crear }
          </button>
          @if (msg()) { <span class="msg">{{ msg() }}</span> }
        </div>
      }

      @if (loading()) { <div class="page__loading">Cargando…</div> }
      @else if (roles().length) {
        <div class="ui-table-responsive">
          <table class="ui-table">
            <thead>
              <tr>
                <th>#</th><th>Rol</th><th>Usuarios</th>
                <th>Módulos</th><th>Estado</th><th></th>
              </tr>
            </thead>
            <tbody>
              @for (r of roles(); track r.id) {
                <tr [class.row--inactive]="!r.activo">
                  <td>{{ r.id }}</td>
                  <td>
                    <strong>{{ r.name }}</strong>
                    @if (r.es_protegido) {
                      <span class="ui-badge ui-badge--danger">protegido</span>
                    }
                  </td>
                  <td>{{ r.num_users }}</td>
                  <td>{{ r.num_modulos }}</td>
                  <td>
                    <button (click)="toggle(r)" class="toggle-btn"
                            [class.is-active]="r.activo"
                            [disabled]="r.es_protegido">
                      {{ r.activo ? 'Activo' : 'Inactivo' }}
                    </button>
                  </td>
                  <td>
                    <a [routerLink]="['/admin/roles', r.id]"
                       class="ui-btn ui-btn--sm ui-btn--primary">
                      <i class="fa fa-eye"></i> Ver
                    </a>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      } @else { <div class="ui-empty-state">Sin roles registrados.</div> }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1100px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-3; }
    .page__loading { padding: $space-4; text-align: center; color: $color-text-muted; }
    .row--inactive { opacity: 0.55; }
    .page__header {
      display: flex; justify-content: space-between;
      align-items: flex-start; gap: $space-3; flex-wrap: wrap;
    }
    .form-create {
      background: $color-bg-subtle;
      padding: $space-3;
      border-radius: $radius-md;
      margin-bottom: $space-3;
      display: flex; gap: $space-2; align-items: center; flex-wrap: wrap;
      label { display: flex; flex-direction: column; flex: 1; min-width: 200px;
              font-size: $font-size-xs; color: $color-text-muted; }
      input { padding: $space-2; border: 1px solid $color-border; border-radius: $radius-sm; }
      .msg { color: $color-success; font-size: $font-size-sm; }
    }
    .toggle-btn {
      background: $color-bg-subtle; border: 1px solid $color-border;
      padding: 2px 10px; border-radius: $radius-pill; font-size: $font-size-xs;
      cursor: pointer;
      &.is-active { background: rgba(22,163,74,0.12); border-color: $color-success; color: $color-success; }
      &:disabled { opacity: 0.45; cursor: not-allowed; }
    }
  `],
})
export class AdminRolesComponent implements OnInit {
  private api = inject(AdminApi);
  private layout = inject(LayoutService);

  roles = signal<RolItem[]>([]);
  loading = signal<boolean>(true);
  abrirCrear = signal<boolean>(false);
  guardando = signal<boolean>(false);
  msg = signal<string>('');
  nuevoNombre = '';

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Administración', url: '/admin' },
      { label: 'Roles' },
    ]);
    this.cargar();
  }

  cargar(): void {
    this.loading.set(true);
    this.api.listarRoles().subscribe({
      next: r => { this.roles.set(r.results); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  crear(): void {
    const name = this.nuevoNombre.trim();
    if (!name) return;
    this.guardando.set(true);
    this.msg.set('');
    this.api.crearRol(name).subscribe({
      next: r => {
        this.msg.set('✓ ' + r.detail);
        this.guardando.set(false);
        this.nuevoNombre = '';
        this.abrirCrear.set(false);
        this.cargar();
      },
      error: e => {
        this.msg.set(e?.error?.detail || 'Error creando rol.');
        this.guardando.set(false);
      },
    });
  }

  toggle(r: RolItem): void {
    if (r.es_protegido) return;
    this.api.toggleActivoRol(r.id).subscribe(() => this.cargar());
  }
}
