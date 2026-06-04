import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LayoutService } from '../layout.service';

/**
 * Breadcrumb global. Lee del LayoutService — cada feature/componente
 * llama `layout.setBreadcrumb([...])` al mount.
 *
 * Convención: el último item NO debe llevar URL (es la posición actual).
 */
@Component({
  standalone: true,
  selector: 'app-breadcrumb',
  imports: [CommonModule, RouterLink],
  template: `
    @if (layout.hasBreadcrumb()) {
      <nav class="ui-breadcrumb" aria-label="Migas de pan">
        <ol class="crumbs">
          @for (item of layout.breadcrumb(); track item.label; let last = $last; let first = $first) {
            <li class="crumb" [class.crumb--last]="last"
                [attr.aria-current]="last ? 'page' : null">
              @if (first) {
                <i class="fa fa-home crumb__icon" aria-hidden="true"></i>
              }
              @if (item.url && !last) {
                <a [routerLink]="item.url" class="crumb__link">{{ item.label }}</a>
              } @else {
                <span class="crumb__current">{{ item.label }}</span>
              }
              @if (!last) {
                <i class="fa fa-chevron-right crumb__sep" aria-hidden="true"></i>
              }
            </li>
          }
        </ol>
      </nav>
    }
  `,
  styles: [`
    @use '../../../../styles/tokens' as *;
    :host {
      display: block;
      padding: $space-2 $space-4;
      background: $color-bg-subtle;
      border-bottom: 1px solid $color-border;
    }
    .ui-breadcrumb { font-size: $font-size-sm; }
    .crumbs {
      list-style: none;
      padding: 0;
      margin: 0;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: $space-1;
    }
    .crumb {
      display: inline-flex;
      align-items: center;
      gap: $space-1;
      &__icon {
        color: $color-primary;
        margin-right: $space-1;
      }
      &__link {
        color: $color-text-muted;
        text-decoration: none;
        padding: 2px 6px;
        border-radius: $radius-sm;
        transition: background 0.15s, color 0.15s;
        &:hover {
          color: $color-primary;
          background: rgba(214, 0, 28, 0.08);
        }
      }
      &__current {
        color: $color-text;
        font-weight: $font-weight-semibold;
        padding: 2px 6px;
      }
      &__sep {
        color: $color-neutral-400;
        font-size: 10px;
        margin: 0 $space-1;
      }
    }
  `],
})
export class BreadcrumbComponent {
  layout = inject(LayoutService);
}
