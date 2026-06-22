import { Injectable, signal } from '@angular/core';

export interface ConfirmOptions {
  title?: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  danger?: boolean;
}

interface PendingConfirm extends ConfirmOptions {
  resolve: (ok: boolean) => void;
}

/**
 * Diálogo de confirmación compartido (reemplaza `window.confirm`, que congela
 * el render). Promise-based: `await confirm.ask({message, danger:true})`.
 * El host (`<app-confirm-host/>`) vive en el layout root.
 */
@Injectable({ providedIn: 'root' })
export class ConfirmService {
  readonly pending = signal<PendingConfirm | null>(null);

  ask(opts: ConfirmOptions): Promise<boolean> {
    return new Promise<boolean>(resolve => {
      this.pending.set({ ...opts, resolve });
    });
  }

  resolve(ok: boolean): void {
    const p = this.pending();
    if (p) {
      p.resolve(ok);
      this.pending.set(null);
    }
  }
}
