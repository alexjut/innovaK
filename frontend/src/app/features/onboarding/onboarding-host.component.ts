import { Component, inject } from '@angular/core';
import { KennyPanelComponent } from '../asistente/kenny-panel.component';
import { KennyChatService } from '../asistente/kenny-chat.service';
import { MascotPresenterComponent } from './mascot-presenter/mascot-presenter.component';
import { MascotStateService } from './mascot-state.service';

/**
 * Host ÚNICO de KENNY en el chrome autenticado: una sola presencia flotante que
 * hace onboarding (tours) y asistente (chat). El botón abre el panel de chat;
 * los tours siguen disparándose (auto la 1ª vez, o desde el flujo "Navegar").
 * La mascota refleja el estado publicado en MascotStateService.
 */
@Component({
  standalone: true,
  selector: 'app-onboarding-host',
  imports: [KennyPanelComponent, MascotPresenterComponent],
  template: `
    @if (chat.open()) {
      <app-kenny-panel />
    } @else {
      <div class="kenny-launcher">
        @if (chat.showGreeting()) {
          <div class="kenny-greeting">
            <button type="button" class="kenny-greeting__x" (click)="chat.descartarSaludo()" aria-label="Cerrar saludo">×</button>
            <strong>¡Hola! Soy KENNY</strong>
            <span>¿Te ayudo con algún trámite?</span>
          </div>
        }
        <button type="button" class="kenny-fab" (click)="chat.abrir()" aria-label="Abrir el asistente KENNY">
          <span class="kenny-fab__ring" aria-hidden="true"></span>
          <span class="kenny-fab__avatar"><app-mascot-presenter [estado]="mascot.estado()" /></span>
        </button>
      </div>
    }
  `,
  styles: [`
    .kenny-launcher {
      position: fixed;
      right: 24px;
      bottom: 24px;
      z-index: 9000;
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 12px;
    }

    .kenny-greeting {
      position: relative;
      max-width: 230px;
      background: #fff;
      border: 1px solid #ececef;
      border-radius: 16px;
      border-bottom-right-radius: 4px;
      padding: 13px 34px 13px 15px;
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.14);
      display: flex;
      flex-direction: column;
      gap: 2px;
      animation: kfade 0.4s ease;
    }
    .kenny-greeting strong { font-size: 13.5px; font-weight: 700; color: #1a1a1a; }
    .kenny-greeting span { font-size: 12.5px; font-weight: 600; color: #6b7280; }
    .kenny-greeting__x {
      position: absolute; top: 8px; right: 8px;
      width: 20px; height: 20px; border-radius: 50%;
      border: 0; background: #f0f0f2; color: #6b7280;
      cursor: pointer; font-size: 13px; line-height: 1;
    }

    .kenny-fab {
      position: relative;
      width: 66px; height: 66px;
      border: 0; border-radius: 50%;
      background: #e41e26;
      box-shadow: 0 12px 28px rgba(228, 30, 38, 0.4);
      cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      transition: transform 0.15s ease;
    }
    .kenny-fab:hover { transform: scale(1.05); }
    .kenny-fab:focus-visible { outline: 3px solid #ffc20e; outline-offset: 3px; }
    .kenny-fab__avatar { --kenny-size: 54px; line-height: 0; }
    .kenny-fab__ring {
      position: absolute; inset: 0; border-radius: 50%;
      box-shadow: 0 0 0 0 rgba(228, 30, 38, 0.45);
      animation: kpulse 2.4s infinite ease-out;
    }

    @keyframes kfade { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
    @keyframes kpulse {
      0% { box-shadow: 0 0 0 0 rgba(228, 30, 38, 0.4); }
      70% { box-shadow: 0 0 0 16px rgba(228, 30, 38, 0); }
      100% { box-shadow: 0 0 0 0 rgba(228, 30, 38, 0); }
    }
    @media (prefers-reduced-motion: reduce) {
      .kenny-fab__ring, .kenny-greeting { animation: none; }
    }
  `],
})
export class OnboardingHostComponent {
  readonly mascot = inject(MascotStateService);
  readonly chat = inject(KennyChatService);
}
