import { Component, inject } from '@angular/core';
import { MascotPresenterComponent } from './mascot-presenter/mascot-presenter.component';
import { MascotStateService } from './mascot-state.service';
import { TourService } from './tour.service';

/**
 * Launcher persistente de Kenny en el chrome autenticado. Kenny está SIEMPRE
 * visible en una esquina (moviéndose: bounce + su video en loop). Al hacer clic
 * relanza el tour (forzado, aunque ya se haya visto). Durante el tour muestra el
 * globo de diálogo. El motor de tour no toca este componente: lee del
 * MascotStateService.
 */
@Component({
  standalone: true,
  selector: 'app-onboarding-host',
  imports: [MascotPresenterComponent],
  template: `
    <button
      type="button"
      class="kenny-launcher"
      [class.kenny-launcher--activo]="mascot.visible()"
      (click)="lanzarTour()"
      [attr.aria-label]="mascot.visible() ? 'Kenny te está guiando' : 'Ver el tour guiado de KennedyConecta'"
    >
      <app-mascot-presenter [estado]="mascot.estado()" />
      @if (!mascot.visible()) {
        <span class="kenny-launcher__hint">¿Te muestro?</span>
      }
    </button>
  `,
  styles: [`
    .kenny-launcher {
      --kenny-size: 84px;
      position: fixed;
      right: 20px;
      bottom: 72px;
      z-index: 9000;
      border: 0;
      padding: 0;
      background: transparent;
      cursor: pointer;
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 6px;
      animation: kenny-bounce 2.6s ease-in-out infinite;
      transition: transform 0.15s ease;
    }
    .kenny-launcher:hover { transform: scale(1.06); }
    .kenny-launcher:focus-visible { outline: 3px solid #0d9488; outline-offset: 4px; border-radius: 20px; }

    /* Durante el tour se queda quieto (el globo hace el trabajo). */
    .kenny-launcher--activo { animation: none; cursor: default; }

    .kenny-launcher__hint {
      background: #0d9488;
      color: #fff;
      font-size: 0.72rem;
      font-weight: 600;
      padding: 3px 9px;
      border-radius: 999px;
      box-shadow: 0 3px 8px rgba(13, 148, 136, 0.35);
      opacity: 0;
      transform: translateY(4px);
      transition: opacity 0.2s ease, transform 0.2s ease;
      pointer-events: none;
      white-space: nowrap;
    }
    .kenny-launcher:hover .kenny-launcher__hint,
    .kenny-launcher:focus-visible .kenny-launcher__hint {
      opacity: 1;
      transform: translateY(0);
    }

    @keyframes kenny-bounce {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-9px); }
    }
    @media (prefers-reduced-motion: reduce) {
      .kenny-launcher { animation: none; }
    }
  `],
})
export class OnboardingHostComponent {
  readonly mascot = inject(MascotStateService);
  private readonly tour = inject(TourService);

  lanzarTour(): void {
    if (this.mascot.visible()) return; // ya hay un tour corriendo
    this.tour.relanzarPantalla();
  }
}
