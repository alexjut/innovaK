import { CommonModule } from '@angular/common';
import { AfterViewChecked, Component, ElementRef, ViewChild, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { LucideAngularModule } from 'lucide-angular';
import { MascotPresenterComponent } from '../onboarding/mascot-presenter/mascot-presenter.component';
import { MascotStateService } from '../onboarding/mascot-state.service';
import { KennyChatService } from './kenny-chat.service';
import { Expr } from './kenny-chat.types';

const EXPR_IMG: Record<Expr, string> = {
  alegre: 'kenny/exp-alegre.png',
  atento: 'kenny/exp-atento.png',
  orgulloso: 'kenny/exp-orgulloso.png',
};

/**
 * Panel de chat del asistente KENNY (hi-fi). Solo render: lee del
 * KennyChatService. El avatar refleja la expresión actual de la mascota.
 */
@Component({
  standalone: true,
  selector: 'app-kenny-panel',
  imports: [CommonModule, FormsModule, LucideAngularModule, MascotPresenterComponent],
  templateUrl: './kenny-panel.component.html',
  styleUrl: './kenny-panel.component.scss',
})
export class KennyPanelComponent implements AfterViewChecked {
  readonly chat = inject(KennyChatService);
  readonly mascot = inject(MascotStateService);

  @ViewChild('scroller') private scroller?: ElementRef<HTMLDivElement>;
  private lastCount = -1;

  exprImg(expr?: Expr): string {
    return EXPR_IMG[expr ?? 'alegre'];
  }

  onKey(e: KeyboardEvent): void {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      this.chat.enviarTexto();
    }
  }

  ngAfterViewChecked(): void {
    // Auto-scroll al fondo cuando llega algo nuevo (scrollTop, no scrollIntoView).
    const n = this.chat.messages().length + (this.chat.typing() ? 1 : 0);
    if (n !== this.lastCount && this.scroller) {
      this.scroller.nativeElement.scrollTop = this.scroller.nativeElement.scrollHeight;
      this.lastCount = n;
    }
  }
}
