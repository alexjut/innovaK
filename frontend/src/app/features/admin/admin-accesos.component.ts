import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AdminApi, AuditoriaRow, SubgrupoCat, UsuarioAcceso } from './admin.api';
import { LayoutService } from '../../core/layout/layout.service';

/**
 * Panel de Usuarios y accesos (RBAC PR-5a). Para que el admin asigne a cada
 * usuario su SUBGRUPO (de qué datos ve) sin tocar BD ni comandos. El rol
 * (qué puede hacer) se sigue gestionando en Roles. Muestra el log de
 * auditoría (Ley 1581).
 */
@Component({
  standalone: true,
  selector: 'app-admin-accesos',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <div>
          <h1><i class="fa fa-users-gear"></i> Usuarios y accesos</h1>
          <p class="page__subtitle">
            El <strong>subgrupo</strong> define qué datos ve cada usuario. Los
            <strong>roles</strong> (qué puede hacer) se gestionan en
            <a routerLink="/admin/roles">Roles y permisos</a>. Los administradores
            ven todo.
          </p>
        </div>
      </header>

      @if (flash()) { <div class="ui-info-bar ui-info-bar--success">{{ flash() }}</div> }
      @if (error()) { <div class="ui-info-bar ui-info-bar--danger">{{ error() }}</div> }

      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando…</div> }

      @if (!loading()) {
        <table class="tbl">
          <thead>
            <tr><th>Usuario</th><th>Roles</th><th>Subgrupo (qué datos ve)</th></tr>
          </thead>
          <tbody>
            @for (u of usuarios(); track u.id) {
              <tr>
                <td>
                  <strong>{{ u.nombre }}</strong>
                  <small class="muted">{{ u.username }}</small>
                </td>
                <td>
                  @for (r of u.roles; track r) { <span class="chip">{{ r }}</span> }
                  @if (u.roles.length === 0) { <span class="muted">—</span> }
                </td>
                <td>
                  @if (u.is_superuser) {
                    <span class="badge badge--admin"><i class="fa fa-crown"></i> Todo (administrador)</span>
                  } @else {
                    <select [ngModel]="u.subgrupo_id" (ngModelChange)="cambiar(u, $event)"
                            [disabled]="guardando() === u.id">
                      <option [ngValue]="null">— Sin subgrupo (no ve nada) —</option>
                      @for (s of subgrupos(); track s.id) {
                        <option [ngValue]="s.id">{{ s.nombre }}</option>
                      }
                    </select>
                    @if (guardando() === u.id) { <i class="fa fa-spinner fa-spin"></i> }
                  }
                </td>
              </tr>
            }
          </tbody>
        </table>

        <section class="audit">
          <h2><i class="fa fa-clock-rotate-left"></i> Auditoría de cambios (Ley 1581)</h2>
          @if (auditoria().length === 0) {
            <p class="muted">Sin registros aún.</p>
          } @else {
            <table class="tbl tbl--sm">
              <thead><tr><th>Fecha</th><th>Acción</th><th>Quién</th><th>Detalle</th></tr></thead>
              <tbody>
                @for (a of auditoria(); track a.id) {
                  <tr>
                    <td>{{ a.ts | date:'short' }}</td>
                    <td><span class="chip">{{ a.accion }}</span></td>
                    <td>{{ a.actor }}</td>
                    <td>{{ a.detalle || (a.usuario + (a.rol ? ' · ' + a.rol : '')) }}</td>
                  </tr>
                }
              </tbody>
            </table>
          }
        </section>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1000px; margin: 0 auto; padding-bottom: $space-6; }
    .page__header h1 { margin: 0; color: $color-primary; }
    .page__subtitle { color: $color-text-muted; font-size: $font-size-sm; margin: $space-1 0 $space-3; }
    .tbl { width: 100%; border-collapse: collapse; font-size: $font-size-sm; background: #fff;
           border: 1px solid $color-border; border-radius: $radius-lg; overflow: hidden; }
    .tbl th, .tbl td { text-align: left; padding: 10px 12px; border-bottom: 1px solid $color-border; vertical-align: middle; }
    .tbl th { color: $color-text-muted; font-weight: 600; background: #F8FAFC; }
    .tbl td small { display: block; }
    .tbl select { padding: 6px 8px; border: 1px solid $color-border; border-radius: $radius-sm; min-width: 240px; }
    .chip { background: #EEF2FF; color: #3730A3; border-radius: 99px; padding: 2px 10px; font-size: .72rem; margin-right: 4px; }
    .badge--admin { background: #FEF3C7; color: #92400E; border-radius: 99px; padding: 3px 12px; font-size: .72rem; font-weight: 600; }
    .muted { color: $color-text-muted; }
    .audit { margin-top: $space-5; }
    .audit h2 { font-size: 1.05rem; color: $color-primary; }
    .tbl--sm { margin-top: $space-2; }
    .tbl--sm th, .tbl--sm td { padding: 6px 10px; font-size: .8rem; }
  `],
})
export class AdminAccesosComponent implements OnInit {
  private api = inject(AdminApi);
  private layout = inject(LayoutService);

  loading = signal(true);
  guardando = signal<number | null>(null);
  error = signal('');
  flash = signal('');
  usuarios = signal<UsuarioAcceso[]>([]);
  subgrupos = signal<SubgrupoCat[]>([]);
  auditoria = signal<AuditoriaRow[]>([]);

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Administración', url: '/admin' },
      { label: 'Usuarios y accesos' },
    ]);
    this.api.subgruposCatalogo().subscribe({ next: (s) => this.subgrupos.set(s), error: () => {} });
    this.cargar();
    this.cargarAuditoria();
  }

  private cargar(): void {
    this.loading.set(true);
    this.api.usuariosAcceso().subscribe({
      next: (u) => { this.usuarios.set(u); this.loading.set(false); },
      error: (e) => { this.loading.set(false); this.error.set(this.msg(e)); },
    });
  }

  private cargarAuditoria(): void {
    this.api.auditoriaRoles().subscribe({ next: (a) => this.auditoria.set(a), error: () => {} });
  }

  cambiar(u: UsuarioAcceso, subgrupoId: number | null): void {
    this.guardando.set(u.id);
    this.error.set('');
    this.api.asignarSubgrupo(u.id, subgrupoId).subscribe({
      next: (r) => {
        this.guardando.set(null);
        u.subgrupo_id = r.subgrupo_id;
        u.subgrupo_nombre = r.subgrupo_nombre;
        this.flash.set(`Subgrupo de ${u.username} actualizado.`);
        setTimeout(() => this.flash.set(''), 2500);
        this.cargarAuditoria();
      },
      error: (e) => { this.guardando.set(null); this.error.set(this.msg(e)); this.cargar(); },
    });
  }

  private msg(e: { error?: { detail?: string }; message?: string }): string {
    return e?.error?.detail || e?.message || 'Error inesperado.';
  }
}
