import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

/**
 * Root component. El router-outlet aquí monta el layout que
 * corresponda según la ruta:
 *   - LayoutComponent  → topbar + sidebar + breadcrumb + content + footer.
 *   - AuthLayoutComponent → gradiente institucional sin menú (login).
 *
 * NO renderizar `<app-layout />` aquí: causaría doble layout anidado
 * (porque app.routes ya pone `component: LayoutComponent` en la ruta '').
 */
@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  template: `<router-outlet />`,
})
export class AppComponent {}
