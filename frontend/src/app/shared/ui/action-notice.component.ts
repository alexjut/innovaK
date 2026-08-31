import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';

export type NoticeVariant = 'info' | 'success' | 'warning' | 'danger';

/**
 * Aviso accionable: título opcional + descripción + botón opcional.
 *
 * Envuelve `.ui-info-bar` (global en `_polish.scss`, 4 variantes semánticas
 * ya medidas en contraste: success/warning/danger/info) — agrega la acción,
 * que el `.ui-info-bar` de solo lectura no tenía.
 *
 * Sin `actionLabel` funciona como un aviso informativo simple (sin botón).
 */
@Component({
  standalone: true,
  selector: 'app-action-notice',
  imports: [CommonModule],
  template: `
    <div class="ui-info-bar" [class]="'ui-info-bar--' + variant" role="status">
      <div class="action-notice__body">
        @if (title) { <strong>{{ title }}</strong> }
        <span>{{ description }}</span>
      </div>
      @if (actionLabel) {
        <button type="button" class="ui-btn ui-btn--sm ui-btn--primary" (click)="action.emit()">
          {{ actionLabel }}
        </button>
      }
    </div>
  `,
  styles: [`
    .action-notice__body { display: flex; flex-direction: column; gap: 2px; flex: 1; min-width: 200px; }
  `],
})
export class ActionNoticeComponent {
  @Input() variant: NoticeVariant = 'info';
  @Input() title?: string;
  @Input({ required: true }) description = '';
  @Input() actionLabel?: string;
  @Output() action = new EventEmitter<void>();
}
