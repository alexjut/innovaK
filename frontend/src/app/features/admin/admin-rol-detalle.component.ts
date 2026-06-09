import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, OnInit, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AdminApi, RolDetalle, UsuarioLite } from './admin.api';
import { LayoutService } from '../../core/layout/layout.service';

@Component({
  standalone: true,
  selector: 'app-admin-rol-detalle',
  imports: [CommonModule, FormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      @if (loading()) { <div class="page__loading">Cargando…</div> }
      @else if (data()) {
        @let d = data()!;
        <header class="page__header">
          <h1>
            <i class="fa fa-user-shield"></i> {{ d.name }}
            @if (d.es_protegido) {
              <span class="ui-badge ui-badge--danger">Protegido</span>
            }
          </h1>
        </header>

        <div class="grid">
          <section class="card">
            <h2><i class="fa fa-puzzle-piece" aria-hidden="true"></i> Módulos asignados</h2>
            <ul class="lista">
              @for (m of d.modulos; track m.codigo) {
                <li>
                  <label class="row-modulo" [class.is-on]="m.asignado">
                    <input type="checkbox" [(ngModel)]="m.asignado"
                           [disabled]="d.es_protegido && m.codigo === 'roles'">
                    <code>{{ m.codigo }}</code>
                    <small>{{ m.nombre }}</small>
                  </label>
                </li>
              }
            </ul>
            <small class="muted">
              {{ countAsignados(d) }} de {{ d.modulos.length }} módulos asignados.
            </small>
            <div class="acciones">
              <button class="ui-btn ui-btn--primary"
                      [disabled]="guardando()"
                      (click)="guardarModulos(d)">
                @if (guardando()) { Guardando… } @else { Guardar módulos }
              </button>
              @if (msg()) {
                <span class="ui-info-bar ui-info-bar--success">{{ msg() }}</span>
              }
            </div>
          </section>

          <section class="card">
            <h2><i class="fa fa-users" aria-hidden="true"></i> Usuarios ({{ d.usuarios.length }})</h2>

            <!-- Buscar y agregar usuario -->
            <div class="add-user">
              <div class="add-user__search">
                <i class="fa fa-search" aria-hidden="true"></i>
                <input type="text" [(ngModel)]="busqueda"
                       (ngModelChange)="onBuscar($event)"
                       placeholder="Buscar usuario por nombre o usuario…">
                @if (buscando()) { <span class="add-user__spin" aria-hidden="true"></span> }
              </div>
              @if (resultados().length) {
                <ul class="add-user__results">
                  @for (u of resultados(); track u.id) {
                    <li>
                      <span><strong>{{ u.username }}</strong> <small>{{ u.nombre }}</small></span>
                      <button class="ui-btn ui-btn--sm ui-btn--primary"
                              [disabled]="agregandoId() === u.id"
                              (click)="agregar(d, u)">
                        <i class="fa fa-plus"></i> Agregar
                      </button>
                    </li>
                  }
                </ul>
              } @else if (busqueda.length >= 2 && !buscando()) {
                <p class="muted add-user__empty">Sin coincidencias (o ya tienen el rol).</p>
              }
            </div>

            @if (umsg()) {
              <span class="ui-info-bar"
                    [class.ui-info-bar--success]="!uerror()"
                    [class.ui-info-bar--danger]="uerror()">{{ umsg() }}</span>
            }

            @if (d.usuarios.length) {
              <ul class="lista">
                @for (u of d.usuarios; track u.id) {
                  <li class="row-user">
                    <i class="fa fa-user"></i>
                    <strong>{{ u.username }}</strong>
                    <small>{{ u.nombre }}</small>
                    <button class="ui-btn ui-btn--sm ui-btn--ghost row-user__del"
                            [disabled]="quitandoId() === u.id"
                            (click)="quitar(d, u)"
                            [attr.aria-label]="'Quitar a ' + u.username + ' del rol'">
                      <i class="fa fa-times"></i>
                    </button>
                  </li>
                }
              </ul>
            } @else {
              <p class="muted">Sin usuarios asignados al rol.</p>
            }
          </section>
        </div>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1200px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .page__loading { padding: $space-4; text-align: center; }
    .grid {
      display: grid; grid-template-columns: 1fr 1fr; gap: $space-3;
      @media (max-width: 720px) { grid-template-columns: 1fr; }
    }
    .card {
      background: $color-bg; border: 1px solid $color-border;
      border-radius: $radius-lg; padding: $space-3;
      h2 { margin: 0 0 $space-2; font-size: $font-size-md; color: $color-text-muted; i { margin-right: $space-1; } }
    }
    .lista { list-style: none; padding: 0; margin: 0; max-height: 480px; overflow-y: auto; }
    .lista li { padding: $space-1 0; border-bottom: 1px dashed $color-border; }
    .row-modulo {
      display: flex; align-items: center; gap: $space-2; cursor: pointer;
      input { margin: 0; }
      code { background: $color-bg-subtle; padding: 1px 6px; border-radius: 3px; }
      small { color: $color-text-muted; margin-left: auto; font-size: $font-size-xs; }
      &.is-on code { background: rgba(22,163,74,0.15); color: $color-success; }
    }
    .acciones {
      margin-top: $space-2; display: flex; gap: $space-2; align-items: center;
    }
    .muted { color: $color-text-muted; }

    .add-user { margin-bottom: $space-3; }
    .add-user__search {
      position: relative; display: flex; align-items: center;
      i { position: absolute; left: $space-2; color: $color-text-muted; }
      input {
        width: 100%; padding: $space-2 $space-2 $space-2 $space-6;
        border: 1px solid $color-border; border-radius: $radius-md;
        font-family: $font-family-base; font-size: $font-size-sm;
        &:focus { outline: none; border-color: $color-primary; }
      }
    }
    .add-user__spin {
      position: absolute; right: $space-2; width: 14px; height: 14px;
      border: 2px solid $color-border; border-top-color: $color-primary;
      border-radius: 50%; animation: spin 0.7s linear infinite;
    }
    .add-user__results {
      list-style: none; padding: 0; margin: $space-2 0 0; max-height: 220px; overflow-y: auto;
      border: 1px solid $color-border; border-radius: $radius-md;
      li {
        display: flex; align-items: center; justify-content: space-between; gap: $space-2;
        padding: $space-1 $space-2; border-bottom: 1px dashed $color-border;
        small { color: $color-text-muted; margin-left: $space-1; }
        &:last-child { border-bottom: none; }
      }
    }
    .add-user__empty { font-size: $font-size-xs; margin: $space-2 0 0; }
    .row-user { display: flex; align-items: center; gap: $space-2;
      small { color: $color-text-muted; }
      &__del { margin-left: auto; }
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  `],
})
export class AdminRolDetalleComponent implements OnInit {
  private api = inject(AdminApi);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);

  data = signal<RolDetalle | null>(null);
  loading = signal<boolean>(true);
  guardando = signal<boolean>(false);
  msg = signal<string>('');

  // Gestión de usuarios del rol
  busqueda = '';
  resultados = signal<UsuarioLite[]>([]);
  buscando = signal<boolean>(false);
  agregandoId = signal<number | null>(null);
  quitandoId = signal<number | null>(null);
  umsg = signal<string>('');
  uerror = signal<boolean>(false);
  private buscarTimer: ReturnType<typeof setTimeout> | null = null;

  ngOnInit(): void {
    this.route.paramMap.subscribe(p => {
      const id = Number(p.get('id') || 0);
      this.api.rolDetalle(id).subscribe({
        next: r => {
          this.data.set(r);
          this.loading.set(false);
          this.layout.setBreadcrumb([
            { label: 'Inicio', url: '/' },
            { label: 'Administración', url: '/admin' },
            { label: 'Roles', url: '/admin/roles' },
            { label: r.name },
          ]);
        },
        error: () => this.loading.set(false),
      });
    });
  }

  countAsignados(d: RolDetalle): number {
    return d.modulos.filter(m => m.asignado).length;
  }

  guardarModulos(d: RolDetalle): void {
    const codigos = d.modulos.filter(m => m.asignado).map(m => m.codigo);
    this.guardando.set(true);
    this.msg.set('');
    this.api.guardarModulos(d.id, codigos).subscribe({
      next: r => {
        this.msg.set('✓ ' + r.detail);
        this.guardando.set(false);
        setTimeout(() => this.msg.set(''), 2000);
      },
      error: e => {
        this.msg.set(e?.error?.detail || 'Error guardando.');
        this.guardando.set(false);
      },
    });
  }

  // ── Gestión de usuarios del rol ──────────────────────────────────
  onBuscar(valor: string): void {
    this.busqueda = valor;
    if (this.buscarTimer) clearTimeout(this.buscarTimer);
    const q = valor.trim();
    if (q.length < 2) {
      this.resultados.set([]);
      this.buscando.set(false);
      return;
    }
    this.buscando.set(true);
    this.buscarTimer = setTimeout(() => {
      const rol = this.data();
      this.api.buscarUsuarios(q, rol?.id, 1).subscribe({
        next: r => { this.resultados.set(r.results); this.buscando.set(false); },
        error: () => { this.resultados.set([]); this.buscando.set(false); },
      });
    }, 300);
  }

  agregar(d: RolDetalle, u: UsuarioLite): void {
    this.agregandoId.set(u.id);
    this.api.agregarUsuarioRol(d.id, u.id).subscribe({
      next: r => {
        // Reflejar en la lista local sin recargar.
        this.data.set({ ...d, usuarios: [...d.usuarios, r.usuario] });
        this.resultados.set(this.resultados().filter(x => x.id !== u.id));
        this.agregandoId.set(null);
        this.flashUsuario(r.detail, false);
      },
      error: e => {
        this.agregandoId.set(null);
        this.flashUsuario(e?.error?.detail || 'No se pudo agregar.', true);
      },
    });
  }

  quitar(d: RolDetalle, u: UsuarioLite): void {
    this.quitandoId.set(u.id);
    this.api.quitarUsuarioRol(d.id, u.id).subscribe({
      next: r => {
        this.data.set({ ...d, usuarios: d.usuarios.filter(x => x.id !== u.id) });
        this.quitandoId.set(null);
        this.flashUsuario(r.detail, false);
      },
      error: e => {
        this.quitandoId.set(null);
        this.flashUsuario(e?.error?.detail || 'No se pudo quitar.', true);
      },
    });
  }

  private flashUsuario(texto: string, esError: boolean): void {
    this.uerror.set(esError);
    this.umsg.set((esError ? '⚠ ' : '✓ ') + texto);
    setTimeout(() => this.umsg.set(''), 2500);
  }
}
