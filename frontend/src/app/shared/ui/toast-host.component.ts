import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ToastService } from './toast.service';

/** Renderiza la pila de toasts (esquina inferior derecha). Va una sola vez
 *  en el layout root. */
@Component({
  standalone: true,
  selector: 'app-toast-host',
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="toast-stack" aria-live="polite" aria-atomic="true">
      @for (t of toast.toasts(); track t.id) {
        <div class="toast" [class.toast--success]="t.kind === 'success'"
             [class.toast--error]="t.kind === 'error'"
             [class.toast--info]="t.kind === 'info'" role="status">
          <i class="fa toast__icon" aria-hidden="true"
             [class.fa-circle-check]="t.kind === 'success'"
             [class.fa-circle-exclamation]="t.kind === 'error'"
             [class.fa-circle-info]="t.kind === 'info'"></i>
          <span class="toast__text">{{ t.text }}</span>
          <button type="button" class="toast__close" (click)="toast.dismiss(t.id)"
                  aria-label="Cerrar notificación">×</button>
        </div>
      }
    </div>
  `,
  styles: [`
    .toast-stack {
      position: fixed; right: 1rem; bottom: 1rem; z-index: 1200;
      display: flex; flex-direction: column; gap: .5rem; max-width: 360px;
    }
    .toast {
      display: flex; align-items: center; gap: .6rem;
      padding: .7rem .9rem; border-radius: 8px; color: #fff;
      box-shadow: 0 6px 20px rgba(0,0,0,.18);
      animation: toast-in .18s ease-out;
    }
    .toast--success { background: #0d9488; }
    .toast--error   { background: #dc2626; }
    .toast--info    { background: #2563eb; }
    .toast__icon { font-size: 1.1rem; }
    .toast__text { flex: 1; font-size: .9rem; line-height: 1.3; }
    .toast__close {
      background: none; border: 0; color: #fff; font-size: 1.2rem;
      cursor: pointer; opacity: .8; line-height: 1;
    }
    .toast__close:hover { opacity: 1; }
    @keyframes toast-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
  `],
})
export class ToastHostComponent {
  protected toast = inject(ToastService);
}
