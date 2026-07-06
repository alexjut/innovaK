import { CommonModule } from '@angular/common';
import { Component, Input, computed, signal } from '@angular/core';

export type EstadoKenny = 'idle' | 'saludo' | 'senalando' | 'celebrando';

/**
 * Presenta a la mascota Kenny por estado. Aislado del motor de tour/chat: el
 * exterior solo cambia el estado (binding [estado] o setEstado()), nunca sabe
 * si Kenny es imagen, video, Lottie o 3D. Hoy: imágenes de expresión oficiales
 * (nítidas) en un círculo con borde de marca.
 */
@Component({
  standalone: true,
  selector: 'app-mascot-presenter',
  imports: [CommonModule],
  templateUrl: './mascot-presenter.component.html',
  styleUrl: './mascot-presenter.component.scss',
})
export class MascotPresenterComponent {
  readonly estado = signal<EstadoKenny>('idle');
  readonly texto = signal<string>('');

  @Input('estado') set estadoInput(v: EstadoKenny | null | undefined) {
    if (v) this.estado.set(v);
  }
  @Input('texto') set textoInput(v: string | null | undefined) {
    this.texto.set(v ?? '');
  }

  /** Única API imperativa expuesta al motor de tour/chat. */
  setEstado(estado: EstadoKenny): void {
    this.estado.set(estado);
  }

  // 4 estados → 3 expresiones oficiales de marca (alegre/atento/orgulloso).
  // Ruta relativa para resolver contra <base href> (dev '/' y prod '/app/').
  private readonly EXPR: Record<EstadoKenny, string> = {
    idle: 'kenny/exp-alegre.png',
    saludo: 'kenny/exp-alegre.png',
    senalando: 'kenny/exp-atento.png',
    celebrando: 'kenny/exp-orgulloso.png',
  };

  readonly imgSrc = computed(() => this.EXPR[this.estado()]);
}
