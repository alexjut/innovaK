import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

@Component({
  standalone: true,
  selector: 'app-perfil',
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page">
      <header class="page__header">
        <h1><i class="fa fa-user-circle"></i> Mi perfil</h1>
      </header>

      @if (me(); as u) {
        <div class="cols">
          <article class="ui-card">
            <header class="ui-card__header"><h2 class="ui-card__title"><i class="fa fa-id-card" aria-hidden="true"></i> Datos de la cuenta</h2></header>
            <dl class="kv">
              <dt>Usuario</dt><dd>{{ u.username }}</dd>
              <dt>Nombre</dt><dd>{{ (u.first_name + ' ' + u.last_name).trim() || '—' }}</dd>
              <dt>Correo</dt><dd>{{ u.email || '—' }}</dd>
              <dt>Roles</dt><dd>
                @for (g of u.groups; track g) { <span class="ui-badge ui-badge--neutral">{{ g }}</span> }
                @if (u.is_superuser) { <span class="ui-badge ui-badge--danger">superusuario</span> }
              </dd>
              <dt>Módulos</dt><dd>{{ u.modules?.length || 0 }} con acceso</dd>
            </dl>
          </article>

          <article class="ui-card">
            <header class="ui-card__header"><h2 class="ui-card__title"><i class="fa fa-lock" aria-hidden="true"></i> Cambiar contraseña</h2></header>
            <div class="form">
              <label><span>Contraseña actual</span>
                <input type="password" [(ngModel)]="actual"></label>
              <label><span>Nueva contraseña</span>
                <input type="password" [(ngModel)]="nueva"></label>
              <label><span>Confirmar nueva</span>
                <input type="password" [(ngModel)]="confirmar"></label>
              <button class="ui-btn ui-btn--primary" [disabled]="guardando()" (click)="cambiar()">
                @if (guardando()) { Guardando… } @else { Cambiar contraseña }
              </button>
              @if (msg()) { <p class="msg" [class.err]="err()">{{ msg() }}</p> }
            </div>
          </article>
        </div>
      } @else { <div class="ui-info-bar ui-info-bar--info">Cargando…</div> }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1000px; margin: 0 auto; }
    .page__header h1 { margin: 0 0 $space-4; color: $color-primary; }
    .cols { display: grid; grid-template-columns: 1fr 1fr; gap: $space-4; @media (max-width: 800px) { grid-template-columns: 1fr; } }
    .kv { display: grid; grid-template-columns: max-content 1fr; gap: $space-2 $space-4; margin: 0;
      dt { font-weight: 600; color: $color-text-muted; font-size: $font-size-sm; } dd { margin: 0; } }
    .form { display: flex; flex-direction: column; gap: $space-2;
      label { display: flex; flex-direction: column; span { font-size: $font-size-xs; color: $color-text-muted; }
        input { padding: $space-2; border: 1px solid $color-border; border-radius: $radius-sm; font: inherit; } } }
    .msg { color: $color-success; &.err { color: $color-danger; } }
  `],
})
export class PerfilComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);

  me = signal<any | null>(null);
  actual = ''; nueva = ''; confirmar = '';
  guardando = signal<boolean>(false);
  msg = signal<string>(''); err = signal<boolean>(false);

  ngOnInit(): void {
    this.layout.setBreadcrumb([{ label: 'Inicio', url: '/' }, { label: 'Mi perfil' }]);
    this.http.get<any>(this.cfg.url('/api/me/')).subscribe(u => this.me.set(u));
  }

  cambiar(): void {
    this.msg.set(''); this.err.set(false);
    if (this.nueva.length < 6) { this.err.set(true); this.msg.set('La nueva contraseña debe tener al menos 6 caracteres.'); return; }
    if (this.nueva !== this.confirmar) { this.err.set(true); this.msg.set('Las contraseñas no coinciden.'); return; }
    this.guardando.set(true);
    this.http.post(this.cfg.url('/api/perfil/cambiar-password/'), { actual: this.actual, nueva: this.nueva }).subscribe({
      next: (r: any) => { this.guardando.set(false); this.msg.set(r.detail || '✓ Contraseña actualizada.'); this.actual = this.nueva = this.confirmar = ''; },
      error: (e) => { this.guardando.set(false); this.err.set(true); this.msg.set(e?.error?.detail || 'No se pudo cambiar.'); },
    });
  }
}
