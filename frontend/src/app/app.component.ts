import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

/**
 * Componente root. Layout completo (sidebar + topbar + breadcrumbs) llega en PR-3.
 * Por ahora solo aloja el router-outlet para que la landing renderice.
 */
@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  template: `<router-outlet />`,
})
export class AppComponent {}
