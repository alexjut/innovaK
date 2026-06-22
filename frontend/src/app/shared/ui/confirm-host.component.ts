import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ConfirmService } from './confirm.service';

/** Modal de confirmación global. Va una sola vez en el layout root. */
@Component({
  standalone: true,
  selector: 'app-confirm-host',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (svc.pending(); as p) {
      <div class="confirm-overlay" (click)="svc.resolve(false)">
        <div class="confirm-box" role="alertdialog" aria-modal="true"
             (click)="$event.stopPropagation()">
          @if (p.title) { <h3 class="confirm-box__title">{{ p.title }}</h3> }
          <p class="confirm-box__msg">{{ p.message }}</p>
          <div class="confirm-box__actions">
            <button type="button" class="btn-cancel" (click)="svc.resolve(false)">
              {{ p.cancelText || 'Cancelar' }}
            </button>
            <button type="button" (click)="svc.resolve(true)"
                    [class.btn-danger]="p.danger" [class.btn-confirm]="!p.danger">
              {{ p.confirmText || 'Confirmar' }}
            </button>
          </div>
        </div>
      </div>
    }
  `,
  styles: [`
    .confirm-overlay {
      position: fixed; inset: 0; z-index: 1300;
      background: rgba(0,0,0,.45);
      display: flex; align-items: center; justify-content: center;
      animation: cf-fade .15s ease-out;
    }
    .confirm-box {
      background: #fff; border-radius: 10px; padding: 1.4rem 1.5rem;
      max-width: 420px; width: 90%; box-shadow: 0 14px 40px rgba(0,0,0,.25);
    }
    .confirm-box__title { margin: 0 0 .5rem; font-size: 1.1rem; color: #1f2937; }
    .confirm-box__msg { margin: 0 0 1.2rem; color: #374151; line-height: 1.45; }
    .confirm-box__actions { display: flex; justify-content: flex-end; gap: .6rem; }
    .confirm-box__actions button {
      padding: .5rem 1.1rem; border-radius: 7px; border: 0; cursor: pointer;
      font-weight: 600; font-size: .9rem;
    }
    .btn-cancel { background: #e5e7eb; color: #374151; }
    .btn-confirm { background: #0d9488; color: #fff; }
    .btn-danger { background: #dc2626; color: #fff; }
    @keyframes cf-fade { from { opacity: 0; } to { opacity: 1; } }
  `],
})
export class ConfirmHostComponent {
  protected svc = inject(ConfirmService);
}
