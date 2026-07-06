import { Component, inject } from '@angular/core';
import { MascotPresenterComponent } from './mascot-presenter/mascot-presenter.component';
import { MascotStateService } from './mascot-state.service';

/**
 * Ancla flotante de la mascota Kenny en el chrome autenticado. Solo renderiza
 * cuando el MascotStateService la marca visible (durante un tour). El motor de
 * tour no toca este componente: escribe en el service, y aquí se refleja.
 */
@Component({
  standalone: true,
  selector: 'app-onboarding-host',
  imports: [MascotPresenterComponent],
  template: `
    @if (mascot.visible()) {
      <div class="kenny-host">
        <app-mascot-presenter [estado]="mascot.estado()" [texto]="mascot.texto()" />
      </div>
    }
  `,
  styles: [`
    .kenny-host {
      position: fixed;
      right: 20px;
      bottom: 64px;
      z-index: 9000;
      pointer-events: none;
    }
  `],
})
export class OnboardingHostComponent {
  readonly mascot = inject(MascotStateService);
}
