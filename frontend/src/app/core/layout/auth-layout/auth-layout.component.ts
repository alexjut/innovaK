import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ConfigService } from '../../config/config.service';

/**
 * Layout para páginas no-autenticadas (login, reset password, 404).
 *
 * SIN topbar/sidebar — el invitado no debe ver menús que no puede usar.
 *
 * Diseño institucional: gradiente diagonal rojo/amarillo/blanco
 * (mismas franjas del Django legacy `body.auth-page`).
 */
@Component({
  standalone: true,
  selector: 'app-auth-layout',
  imports: [RouterOutlet],
  template: `
    <div class="auth-layout">
      <header class="auth-layout__header">
        <h1 class="auth-layout__title">{{ cfg.appName }}</h1>
        <p class="auth-layout__subtitle">{{ cfg.alcaldiaName }}</p>
      </header>

      <main class="auth-layout__main" id="main-content" tabindex="-1">
        <router-outlet />
      </main>

      <footer class="auth-layout__footer">
        © {{ year }} {{ cfg.alcaldiaName }}
      </footer>
    </div>
  `,
  styles: [`
    @use '../../../../styles/tokens' as *;

    :host { display: block; min-height: 100vh; }

    .auth-layout {
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: $space-6 $space-4;
      background: linear-gradient(
        70deg,
        $color-primary 0%,
        $color-primary 48%,
        $color-secondary 48%,
        $color-secondary 52%,
        #ffffff 52%,
        #ffffff 100%
      );
      background-attachment: fixed;
    }

    .auth-layout__header {
      text-align: center;
      margin-bottom: $space-6;
      color: $color-text-inverse;
      text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
    }

    .auth-layout__title {
      margin: 0;
      font-size: $font-size-3xl;
      font-weight: $font-weight-bold;
      letter-spacing: 1px;
    }

    .auth-layout__subtitle {
      margin: $space-1 0 0;
      font-size: $font-size-md;
      font-weight: $font-weight-medium;
      opacity: 0.95;
    }

    .auth-layout__main {
      width: 100%;
      max-width: 460px;
      outline: 0;
    }

    .auth-layout__footer {
      margin-top: $space-8;
      color: $color-text;
      font-size: $font-size-xs;
      opacity: 0.7;
    }

    @media (max-width: 600px) {
      .auth-layout__title { font-size: $font-size-2xl; }
      .auth-layout__subtitle { font-size: $font-size-base; }
    }
  `],
})
export class AuthLayoutComponent {
  cfg = inject(ConfigService);
  year = new Date().getFullYear();
}
