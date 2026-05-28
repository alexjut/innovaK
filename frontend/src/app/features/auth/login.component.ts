import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';

/**
 * Login form que llama `/api/token/` (JWT obtain pair).
 *
 * Comportamiento:
 *   - Si ya hay sesión: redirige a /.
 *   - Submit válido → POST username/password → guarda tokens →
 *     redirige a la ruta que pidió originalmente (queryParam `next`)
 *     o a / por default.
 *   - Errores DRF: 400 (credenciales faltantes) / 401 (credenciales
 *     inválidas) / 5xx (backend caído).
 */
@Component({
  standalone: true,
  selector: 'app-login',
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <div class="ui-card ui-card--elevated login-card">
      <header class="ui-card__header">
        <h2 class="ui-card__title">Iniciar sesión</h2>
        <p class="ui-card__subtitle">
          Acceso para funcionarios y operadores del sistema.
        </p>
      </header>

      <form [formGroup]="form" (ngSubmit)="submit()" class="login-form" novalidate>
        @if (errorMsg()) {
          <div class="ui-info-bar ui-info-bar--danger" role="alert">
            <strong>Error:</strong> {{ errorMsg() }}
          </div>
        }

        <div class="field">
          <label for="username">Usuario</label>
          <input
            id="username"
            type="text"
            autocomplete="username"
            formControlName="username"
            placeholder="ej. alex.jut"
            [class.invalid]="isInvalid('username')"
          />
          @if (isInvalid('username')) {
            <small class="field-error">El usuario es obligatorio.</small>
          }
        </div>

        <div class="field">
          <label for="password">Contraseña</label>
          <input
            id="password"
            type="password"
            autocomplete="current-password"
            formControlName="password"
            [class.invalid]="isInvalid('password')"
          />
          @if (isInvalid('password')) {
            <small class="field-error">La contraseña es obligatoria.</small>
          }
        </div>

        <button
          type="submit"
          class="ui-btn ui-btn--primary ui-btn--block"
          [disabled]="form.invalid || loading()"
        >
          @if (loading()) {
            Ingresando…
          } @else {
            <i class="fa fa-sign-in-alt" aria-hidden="true"></i>
            Ingresar
          }
        </button>
      </form>
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;

    :host { display: block; }

    .login-card { padding: $space-6; }

    .login-form {
      display: flex;
      flex-direction: column;
      gap: $space-4;
    }

    .field {
      display: flex;
      flex-direction: column;
      gap: $space-1;
    }

    .field label {
      font-size: $font-size-sm;
      font-weight: $font-weight-semibold;
      color: $color-text;
    }

    .field input {
      padding: $space-3 $space-4;
      border: 1px solid $color-border;
      border-radius: $radius-md;
      font-size: $font-size-base;
      font-family: inherit;
      transition: border-color $transition-fast, box-shadow $transition-fast;
      min-height: $touch-target-min;

      &:focus {
        outline: none;
        border-color: $color-primary;
        box-shadow: 0 0 0 3px rgba(214, 0, 28, 0.15);
      }

      &.invalid {
        border-color: $color-danger;
      }
    }

    .field-error {
      color: $color-danger;
      font-size: $font-size-xs;
      font-weight: $font-weight-medium;
    }
  `],
})
export class LoginComponent {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private router = inject(Router);

  loading = signal<boolean>(false);
  errorMsg = signal<string>('');

  form = this.fb.nonNullable.group({
    username: ['', [Validators.required]],
    password: ['', [Validators.required]],
  });

  constructor() {
    if (this.auth.isAuthenticated()) {
      this.router.navigateByUrl('/');
    }
  }

  isInvalid(field: 'username' | 'password'): boolean {
    const c = this.form.controls[field];
    return c.invalid && (c.dirty || c.touched);
  }

  submit(): void {
    this.errorMsg.set('');
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.loading.set(true);
    this.auth.login(this.form.getRawValue()).subscribe({
      next: () => {
        this.loading.set(false);
        const next = new URLSearchParams(window.location.search).get('next') || '/';
        this.router.navigateByUrl(next);
      },
      error: (err: HttpErrorResponse) => {
        this.loading.set(false);
        if (err.status === 401) {
          this.errorMsg.set('Usuario o contraseña incorrectos.');
        } else if (err.status === 400) {
          this.errorMsg.set('Datos incompletos. Revisa los campos.');
        } else if (err.status === 0) {
          this.errorMsg.set('No se pudo conectar con el servidor.');
        } else {
          this.errorMsg.set(`Error del servidor (${err.status}). Intenta más tarde.`);
        }
      },
    });
  }
}
