import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, OnInit, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AdminApi, RolDetalle } from './admin.api';
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
            <h2>Módulos asignados</h2>
            <ul class="lista">
              @for (m of d.modulos; track m.id) {
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
            <h2>Usuarios ({{ d.usuarios.length }})</h2>
            @if (d.usuarios.length) {
              <ul class="lista">
                @for (u of d.usuarios; track u.id) {
                  <li>
                    <i class="fa fa-user"></i>
                    <strong>{{ u.username }}</strong>
                    <small>{{ u.nombre }}</small>
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
      h2 { margin: 0 0 $space-2; font-size: $font-size-md; color: $color-text-muted; }
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
}
