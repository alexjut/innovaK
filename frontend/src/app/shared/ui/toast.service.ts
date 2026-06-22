import { Injectable, signal } from '@angular/core';

export type ToastKind = 'success' | 'error' | 'info';

export interface Toast {
  id: number;
  kind: ToastKind;
  text: string;
}

/**
 * Notificaciones efímeras (toast) compartidas en toda la app. Reemplaza los
 * `.ui-info-bar` inline dispersos. El host (`<app-toast-host/>`) vive en el
 * layout root y se suscribe a la señal `toasts`.
 *
 * Uso: `inject(ToastService).success('Festival creado correctamente')`.
 */
@Injectable({ providedIn: 'root' })
export class ToastService {
  readonly toasts = signal<Toast[]>([]);
  private seq = 0;

  success(text: string, ms = 3000): void { this.push('success', text, ms); }
  error(text: string, ms = 5000): void { this.push('error', text, ms); }
  info(text: string, ms = 3000): void { this.push('info', text, ms); }

  dismiss(id: number): void {
    this.toasts.update(list => list.filter(t => t.id !== id));
  }

  private push(kind: ToastKind, text: string, ms: number): void {
    const id = ++this.seq;
    this.toasts.update(list => [...list, { id, kind, text }]);
    if (ms > 0) {
      setTimeout(() => this.dismiss(id), ms);
    }
  }
}
