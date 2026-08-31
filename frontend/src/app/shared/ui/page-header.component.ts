import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

/**
 * Cabecera estándar de pantalla: título + descripción + acciones.
 *
 * Envuelve `.page__header`/`.page__sub` (globales en `_page.scss`, ya
 * usados por 20+ pantallas) — no agrega clases nuevas al sistema, así que
 * cualquier pantalla que hoy las escriba a mano puede migrar sin tocar CSS.
 *
 * Las acciones se proyectan con el atributo `header-actions`:
 *   <app-page-header title="..." description="...">
 *     <a header-actions class="ui-btn ui-btn--ghost" routerLink="...">Ver más</a>
 *   </app-page-header>
 */
@Component({
  standalone: true,
  selector: 'app-page-header',
  imports: [CommonModule],
  template: `
    <header class="page__header">
      <div>
        @if (eyebrow) { <div class="page-header__eyebrow">{{ eyebrow }}</div> }
        <h1>
          @if (icon) { <i class="fa" [class]="icon" aria-hidden="true"></i> }
          {{ title }}
        </h1>
        @if (description) { <p class="page__sub">{{ description }}</p> }
      </div>
      <div class="page__actions">
        <ng-content select="[header-actions]" />
      </div>
    </header>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    .page-header__eyebrow {
      font-size: $font-size-xs;
      font-weight: $font-weight-semibold;
      letter-spacing: .06em;
      text-transform: uppercase;
      color: $color-text-muted;
      margin-bottom: $space-1;
    }
    h1 .fa { margin-right: $space-2; color: $color-text-muted; font-size: .85em; }
  `],
})
export class PageHeaderComponent {
  @Input({ required: true }) title = '';
  @Input() description?: string | null;
  @Input() eyebrow?: string | null;
  /** Clase fa-* completa, ej. "fa-graduation-cap". Decorativo, siempre aria-hidden. */
  @Input() icon?: string;
}
