import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { ConfigService } from '../../config/config.service';

/**
 * Footer institucional fijo en parte inferior. Replica `.base-footer`
 * del Django legacy.
 */
@Component({
  standalone: true,
  selector: 'app-footer',
  imports: [CommonModule],
  template: `
    <footer class="base-footer" role="contentinfo">
      <div class="base-footer-row footer-linea">
        <span class="footer-copy">© {{ year }} {{ cfg.alcaldiaName }} — {{ cfg.appName }}</span>
        <span class="footer-redes">
          <a href="https://www.kennedy.gov.co/" target="_blank" rel="noopener"
             aria-label="Sitio web de la Alcaldía Local de Kennedy">
            <i class="fa fa-globe" aria-hidden="true"></i>
          </a>
          <a href="https://www.instagram.com/alcaldiakennedy/" target="_blank" rel="noopener"
             aria-label="Instagram de la Alcaldía Local de Kennedy">
            <!-- Instagram es un icono de marca (fa-brands): el subset de
                 Font Awesome del proyecto solo trae solid/regular, así que
                 en vez de sumar toda la fuente de marcas por un solo icono
                 va en SVG propio, mismo trazo que el resto (currentColor). -->
            <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">
              <rect x="2.5" y="2.5" width="19" height="19" rx="5" fill="none" stroke="currentColor" stroke-width="2"/>
              <circle cx="12" cy="12" r="4.5" fill="none" stroke="currentColor" stroke-width="2"/>
              <circle cx="17.2" cy="6.8" r="1.15" fill="currentColor"/>
            </svg>
          </a>
        </span>
      </div>
    </footer>
  `,
  styles: [`
    @use '../../../../styles/tokens' as *;

    :host { display: contents; }

    .base-footer {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      z-index: $z-sticky;
      background: $color-primary;
      color: $color-text-inverse;
      border-top: 3px solid $color-secondary;
      padding: $space-2 $space-4;
      text-align: center;
      box-shadow: 0 -2px 6px rgba(0, 0, 0, 0.12);
      font-size: $font-size-xs;
    }

    // Una sola línea: copyright + redes, centrados y con wrap solo si el
    // ancho no alcanza (celular angosto), no por diseño.
    .footer-linea {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: center;
      gap: $space-1 $space-3;
      line-height: 1.3;
    }

    .footer-copy {
      font-weight: $font-weight-bold;
    }

    .footer-redes {
      display: flex;
      align-items: center;
      gap: $space-2;

      a {
        display: inline-flex;
        color: $color-secondary;

        &:hover, &:focus-visible { opacity: 0.8; }
        &:focus-visible { outline: $focus-ring-width solid $color-secondary; outline-offset: 2px; }
      }
    }
  `],
})
export class FooterComponent {
  cfg = inject(ConfigService);
  year = new Date().getFullYear();
}
