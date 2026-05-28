import { Component } from '@angular/core';
import { LayoutComponent } from './core/layout/layout.component';

/**
 * Root component. Toda la app vive dentro del LayoutComponent
 * (topbar + sidebar + breadcrumb + content + footer).
 *
 * En PR-4 cuando llegue el login, la ruta `/login` renderizará un
 * AuthLayout SIN sidebar/topbar para no exponer menús al no
 * autenticado.
 */
@Component({
  selector: 'app-root',
  standalone: true,
  imports: [LayoutComponent],
  template: `<app-layout />`,
})
export class AppComponent {}
