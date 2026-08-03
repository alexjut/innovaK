import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { ToastHostComponent } from '../../../shared/ui/toast-host.component';

/**
 * Chrome de las páginas PÚBLICAS (visitante sin sesión).
 *
 * Por qué existe: el mapa se abría sin ninguna barra —ni marca, ni forma de
 * volver, ni de entrar—, así que quien llegaba desde un enlace compartido caía
 * en una página huérfana: no había pista de que fuera de la Alcaldía ni de que
 * hubiera algo más. `LayoutComponent` no sirve acá porque su topbar y su
 * sidebar asumen sesión (menú de usuario, módulos por rol).
 *
 * Es el equivalente público de `LayoutComponent` y comparte su estructura de
 * accesibilidad, que es lo que hace que las dos mitades de la app se sientan
 * una sola: skip-link primero en el DOM, `<main id="main-content">` como
 * destino, landmarks (`banner` / `navigation` / `contentinfo`) y `aria-current`
 * en el enlace de la página actual.
 *
 * La barra va ESTÁTICA, no fija ni `sticky`: Leaflet monta sus panes y sus
 * controles con z-index propios (400–1000) y una barra flotante encima de un
 * mapa termina tapada por un control o tapando un popup. El costo de que se
 * vaya con el scroll es mucho menor que el de un menú que pelea con el mapa.
 */
@Component({
  standalone: true,
  selector: 'app-public-layout',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, ToastHostComponent],
  template: `
    <a class="ui-skip-link" href="#main-content">Saltar al contenido principal</a>

    <header class="pub-top">
      <div class="pub-top__inner">
        <a routerLink="/" class="pub-marca">
          <!-- Ruta RELATIVA: resuelve contra <base href="/app/">. Con "/kenny/…"
               el navegador la pide en la raíz del dominio y da 404. -->
          <img src="kenny/exp-atento.png" alt="" width="36" height="36" aria-hidden="true" />
          <span class="pub-marca__texto">
            <strong>Alcaldía Local de Kennedy</strong>
            <small>Bogotá D.C.</small>
          </span>
        </a>

        <nav class="pub-nav" aria-label="Navegación pública">
          <a
            routerLink="/"
            routerLinkActive="is-activa"
            [routerLinkActiveOptions]="{ exact: true }"
            #inicio="routerLinkActive"
            [attr.aria-current]="inicio.isActive ? 'page' : null"
            >Inicio</a
          >
          <a
            routerLink="/mapa"
            routerLinkActive="is-activa"
            #mapa="routerLinkActive"
            [attr.aria-current]="mapa.isActive ? 'page' : null"
            >Mapa de Kennedy</a
          >
          <a routerLink="/auth/login" class="pub-nav__entrar">Ingresar</a>
        </nav>
      </div>
    </header>

    <main id="main-content" class="pub-main" tabindex="-1">
      <router-outlet />
    </main>

    <footer class="pub-pie">
      <span>Alcaldía Local de Kennedy · Bogotá D.C.</span>
      <span class="pub-pie__nota">
        Información pública. No necesitas usuario ni contraseña para verla.
      </span>
    </footer>

    <app-toast-host />
  `,
  styles: [
    `
      @use '../../../../styles/tokens' as *;

      $rojo: #d6001c;
      $rojo-osc: #b50015;
      $amarillo: #ffc72c;

      :host {
        display: flex;
        flex-direction: column;
        min-height: 100vh;
      }

      .pub-top {
        background: linear-gradient(135deg, #{$rojo-osc} 0%, #{$rojo} 100%);
        color: #fff;
      }

      .pub-top__inner {
        max-width: 1400px;
        margin: 0 auto;
        padding: $space-2 $space-4;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: $space-3;
        flex-wrap: wrap;
      }

      .pub-marca {
        display: flex;
        align-items: center;
        gap: $space-2;
        color: inherit;
        text-decoration: none;
        min-height: $touch-target-min;
        border-radius: 6px;

        img { border-radius: 50%; background: rgba(255, 255, 255, 0.15); }
      }

      .pub-marca__texto {
        display: flex;
        flex-direction: column;
        line-height: 1.15;

        strong { font-size: 0.98rem; }
        small { font-size: 0.76rem; opacity: 0.85; }
      }

      .pub-nav {
        display: flex;
        align-items: center;
        gap: $space-1;
        flex-wrap: wrap;

        a {
          display: inline-flex;
          align-items: center;
          min-height: $touch-target-min;   // WCAG 2.5.5
          padding: 0 $space-3;
          border-radius: 6px;
          color: #fff;
          text-decoration: none;
          font-size: 0.94rem;
          // El subrayado al pasar el cursor no basta: la página actual tiene
          // que distinguirse también sin color (ver .is-activa).
          &:hover { background: rgba(255, 255, 255, 0.14); }
        }

        // Página actual: fondo + borde inferior amarillo. Dos señales, no una,
        // para que no dependa de percibir el cambio de fondo.
        a.is-activa {
          background: rgba(255, 255, 255, 0.18);
          box-shadow: inset 0 -3px 0 $amarillo;
          font-weight: 600;
        }
      }

      .pub-nav__entrar {
        background: $amarillo;
        color: #1f2937 !important;
        font-weight: 700;
        margin-left: $space-2;

        &:hover { background: #ffd75e; }
      }

      // Foco visible sobre fondo rojo: el anillo del token puede no contrastar,
      // así que acá se fuerza blanco con halo oscuro.
      .pub-marca:focus-visible,
      .pub-nav a:focus-visible {
        outline: 3px solid #fff;
        outline-offset: 2px;
      }

      .pub-main {
        flex: 1 1 auto;
        width: 100%;
        box-sizing: border-box;
        padding: $space-4;
        outline: 0;
      }

      .pub-pie {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: $space-2;
        flex-wrap: wrap;
        padding: $space-3 $space-4;
        background: #1f2937;
        color: #e5e7eb;
        font-size: 0.85rem;
      }

      .pub-pie__nota { opacity: 0.8; }

      @media (max-width: 720px) {
        .pub-top__inner { padding: $space-2; }
        .pub-marca__texto small { display: none; }
        .pub-nav { width: 100%; justify-content: flex-start; }
        .pub-nav__entrar { margin-left: auto; }
        .pub-main { padding: $space-2; }
      }

      @media (prefers-reduced-motion: reduce) {
        .pub-nav a { transition: none; }
      }
    `,
  ],
})
export class PublicLayoutComponent {}
