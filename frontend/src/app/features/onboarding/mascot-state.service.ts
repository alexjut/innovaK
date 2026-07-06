import { Injectable, signal } from '@angular/core';
import { EstadoKenny } from './mascot-presenter/mascot-presenter.component';

/**
 * Estado de la mascota, desacoplado de su render. El TourService escribe aquí;
 * el componente que monta a Kenny lo lee. Así el motor de tour nunca conoce la
 * tecnología de render (video/Lottie/3D).
 */
@Injectable({ providedIn: 'root' })
export class MascotStateService {
  readonly estado = signal<EstadoKenny>('idle');
  readonly texto = signal<string>('');
  readonly visible = signal<boolean>(false);

  setEstado(estado: EstadoKenny): void {
    this.estado.set(estado);
  }

  setTexto(texto: string): void {
    this.texto.set(texto);
  }

  mostrar(estado: EstadoKenny = 'saludo', texto = ''): void {
    this.estado.set(estado);
    this.texto.set(texto);
    this.visible.set(true);
  }

  ocultar(): void {
    this.visible.set(false);
  }
}
