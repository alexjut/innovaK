import { CommonModule, isPlatformBrowser } from '@angular/common';
import { Component, Input, PLATFORM_ID, computed, inject, signal } from '@angular/core';

export type EstadoKenny = 'idle' | 'saludo' | 'senalando' | 'celebrando';

/**
 * Presenta a la mascota Kenny. Aislado del motor de tour: el exterior solo
 * cambia el estado (por binding [estado] o por setEstado()), nunca sabe si
 * Kenny es video, Lottie o 3D. Fase 1: un <video> por estado dentro de una
 * tarjeta con fondo (los .mp4 no tienen canal alfa).
 */
@Component({
  standalone: true,
  selector: 'app-mascot-presenter',
  imports: [CommonModule],
  templateUrl: './mascot-presenter.component.html',
  styleUrl: './mascot-presenter.component.scss',
})
export class MascotPresenterComponent {
  private readonly platformId = inject(PLATFORM_ID);
  readonly esBrowser = isPlatformBrowser(this.platformId);

  readonly estado = signal<EstadoKenny>('idle');
  readonly texto = signal<string>('');

  @Input('estado') set estadoInput(v: EstadoKenny | null | undefined) {
    if (v) this.estado.set(v);
  }
  @Input('texto') set textoInput(v: string | null | undefined) {
    this.texto.set(v ?? '');
  }

  /** Única API imperativa expuesta al motor de tour. */
  setEstado(estado: EstadoKenny): void {
    this.estado.set(estado);
  }

  // Fase 1: hoy solo existe un asset; los 4 estados apuntan al mismo video
  // hasta producir idle/saludo/senalando/celebrando. Ruta relativa para
  // resolver contra <base href> (dev '/' y prod '/app/').
  private readonly VIDEOS: Record<EstadoKenny, string> = {
    idle: 'kenny/mascota-innovak.mp4',
    saludo: 'kenny/mascota-innovak.mp4',
    senalando: 'kenny/mascota-innovak.mp4',
    celebrando: 'kenny/mascota-innovak.mp4',
  };

  readonly videoSrc = computed(() => this.VIDEOS[this.estado()]);
}
