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
        <ol>
          @for (item of layout.breadcrumb(); track item.label; let last = $last) {
            <li [attr.aria-current]="last ? 'page' : null">
              @if (item.url && !last) {
                <a [routerLink]="item.url">{{ item.label }}</a>
              } @else {
                {{ item.label }}
              }
            </li>
          }
        </ol>
      </nav>
    }
  `,
  styles: [`
    :host { display: block; }
  `],
})
export class BreadcrumbComponent {
  layout = inject(LayoutService);
}
