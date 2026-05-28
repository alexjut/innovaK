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
      <div class="base-footer-row footer-copy">
        © {{ year }} {{ cfg.alcaldiaName }} — {{ cfg.appName }}
      </div>
      <div class="base-footer-row footer-links">
        <a class="link-web" href="https://www.alcaldiakennedy.gov.co" target="_blank" rel="noopener">
          alcaldiakennedy.gov.co
        </a>
        <span class="base-footer-sep">·</span>
        <span class="footer-text">v1.0</span>
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

    .base-footer-row {
      line-height: 1.3;

      & + .base-footer-row {
        margin-top: 4px;
      }
    }

    .footer-copy {
      font-weight: $font-weight-bold;
    }

    .footer-links {
      display: flex;
      gap: $space-3;
      align-items: center;
      justify-content: center;
      font-weight: $font-weight-medium;
    }

    .base-footer-sep {
      opacity: 0.85;
    }

    .link-web,
    .footer-text {
      color: $color-secondary;
      text-decoration: none;
    }

    .link-web:hover {
      text-decoration: underline;
    }

    @media (max-width: 520px) {
      .base-footer-sep { display: none; }
      .footer-links { flex-wrap: wrap; gap: $space-2; }
    }
  `],
})
export class FooterComponent {
  cfg = inject(ConfigService);
  year = new Date().getFullYear();
}
